"""Telegram Gateway - Professional integration for MAGoCo AI OS.

Features:
- Multi-bot support (multiple agents on multiple chats)
- Session-based conversation management per chat
- Provider/model routing per chat
- Webhook and polling modes
- Message queue for concurrent processing
- Inline keyboards and commands
- Media handling (photos, documents)
- Admin controls and access control
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"


class TelegramMode(str, Enum):
    POLLING = "polling"
    WEBHOOK = "webhook"


@dataclass
class TelegramChatSession:
    """Per-chat conversation state."""
    chat_id: str
    agent_id: str = "default"
    provider_id: Optional[str] = None
    model: Optional[str] = None
    history: List[Dict[str, str]] = field(default_factory=list)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TelegramBotConfig:
    """Configuration for a Telegram bot instance."""
    bot_id: str
    token: str
    name: str = "MAGoCo Bot"
    mode: TelegramMode = TelegramMode.POLLING
    webhook_url: str = ""
    allowed_chat_ids: List[str] = field(default_factory=list)  # empty = all allowed
    admin_chat_ids: List[str] = field(default_factory=list)
    default_provider_id: Optional[str] = None
    default_model: Optional[str] = None
    system_prompt: str = ""
    max_history: int = 20
    enabled: bool = True


class TelegramGateway:
    """Manages multiple Telegram bots with per-chat agent sessions.

    Bots persist to SQLite (survive restarts); sessions stay in memory
    (conversation state is rebuilt from history on demand).
    """

    def __init__(self, db_path: str = "./data/telegram/bots.db"):
        self.bots: Dict[str, TelegramBotConfig] = {}
        self.sessions: Dict[str, TelegramChatSession] = {}  # key: bot_id:chat_id
        self.agent_executor: Optional[Callable[..., Coroutine[Any, Any, str]]] = None
        self._polling_tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        self._db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        from pathlib import Path
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        cur = self._conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS telegram_bots
            (bot_id TEXT PRIMARY KEY, name TEXT, token TEXT, mode TEXT,
             webhook_url TEXT, allowed_chat_ids TEXT, admin_chat_ids TEXT,
             default_provider_id TEXT, default_model TEXT, system_prompt TEXT,
             max_history INTEGER, enabled INTEGER, created_at TEXT)""")
        self._conn.commit()

    def _persist_bot(self, config: TelegramBotConfig) -> None:
        cur = self._conn.cursor()
        cur.execute("""INSERT OR REPLACE INTO telegram_bots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (config.bot_id, config.name, config.token, config.mode.value,
                     config.webhook_url, json.dumps(config.allowed_chat_ids),
                     json.dumps(config.admin_chat_ids), config.default_provider_id or "",
                     config.default_model or "", config.system_prompt,
                     config.max_history, int(config.enabled), datetime.utcnow().isoformat()))
        self._conn.commit()

    def _delete_bot_row(self, bot_id: str) -> None:
        cur = self._conn.cursor()
        cur.execute("DELETE FROM telegram_bots WHERE bot_id=?", (bot_id,))
        self._conn.commit()

    def load_bots(self) -> int:
        """Load persisted bots into memory. Returns count loaded."""
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM telegram_bots")
        count = 0
        for row in cur.fetchall():
            try:
                cfg = TelegramBotConfig(
                    bot_id=row["bot_id"], token=row["token"], name=row["name"],
                    mode=TelegramMode(row["mode"]), webhook_url=row["webhook_url"] or "",
                    allowed_chat_ids=json.loads(row["allowed_chat_ids"] or "[]"),
                    admin_chat_ids=json.loads(row["admin_chat_ids"] or "[]"),
                    default_provider_id=row["default_provider_id"] or None,
                    default_model=row["default_model"] or None,
                    system_prompt=row["system_prompt"] or "",
                    max_history=row["max_history"] or 20,
                    enabled=bool(row["enabled"]),
                )
                self.bots[cfg.bot_id] = cfg
                count += 1
            except Exception as e:
                logger.warning(f"[Telegram] failed to load bot {row['bot_id']}: {e}")
        return count

    def register_agent_executor(
        self, executor: Callable[..., Coroutine[Any, Any, str]]
    ) -> None:
        """Register the agent executor (async fn(chat_id, message, provider_id, model) -> str)."""
        self.agent_executor = executor

    def add_bot(self, config: TelegramBotConfig) -> None:
        """Register a bot configuration (persisted)."""
        self.bots[config.bot_id] = config
        self._persist_bot(config)

    def remove_bot(self, bot_id: str) -> None:
        """Remove a bot (also deletes from storage)."""
        self.bots.pop(bot_id, None)
        self._delete_bot_row(bot_id)
        task = self._polling_tasks.pop(bot_id, None)
        if task and not task.done():
            task.cancel()

    def _session_key(self, bot_id: str, chat_id: str) -> str:
        return f"{bot_id}:{chat_id}"

    def get_session(self, bot_id: str, chat_id: str) -> TelegramChatSession:
        """Get or create a session for a chat."""
        key = self._session_key(bot_id, chat_id)
        if key not in self.sessions:
            bot = self.bots.get(bot_id, TelegramBotConfig(bot_id=bot_id, token=""))
            self.sessions[key] = TelegramChatSession(
                chat_id=chat_id,
                provider_id=bot.default_provider_id,
                model=bot.default_model,
            )
        return self.sessions[key]

    def _is_allowed(self, bot_id: str, chat_id: str) -> bool:
        bot = self.bots.get(bot_id)
        if not bot:
            return False
        if not bot.allowed_chat_ids:
            return True
        return chat_id in bot.allowed_chat_ids

    # ---------- Telegram API ----------

    async def _api_call(self, token: str, method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(f"{TELEGRAM_API}/bot{token}/{method}", json=payload)
            r.raise_for_status()
            data = r.json()
            if not data.get("ok"):
                raise RuntimeError(f"Telegram API error: {data}")
            return data["result"]

    async def send_message(self, bot_id: str, chat_id: str, text: str, reply_markup: Optional[Dict] = None) -> None:
        bot = self.bots.get(bot_id)
        if not bot:
            return
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": text[:4096],
            "parse_mode": "Markdown",
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        await self._api_call(bot.token, "sendMessage", payload)

    async def send_typing(self, bot_id: str, chat_id: str) -> None:
        bot = self.bots.get(bot_id)
        if not bot:
            return
        try:
            await self._api_call(bot.token, "sendChatAction", {"chat_id": chat_id, "action": "typing"})
        except Exception:
            pass

    # ---------- Message Handling ----------

    async def handle_update(self, bot_id: str, update: Dict[str, Any]) -> None:
        """Process an incoming Telegram update."""
        message = update.get("message") or update.get("edited_message")
        if not message:
            return

        chat = message.get("chat", {})
        chat_id = str(chat.get("id", ""))
        text = message.get("text", "")
        user = message.get("from", {})

        if not text or not chat_id:
            return

        bot = self.bots.get(bot_id)
        if not bot or not bot.enabled:
            return

        if not self._is_allowed(bot_id, chat_id):
            await self.send_message(bot_id, chat_id, "⛔ Access denied.")
            return

        session = self.get_session(bot_id, chat_id)
        session.last_activity = datetime.utcnow()

        # Command handling
        if text.startswith("/"):
            await self._handle_command(bot_id, chat_id, session, text, user)
            return

        # Regular message → agent
        await self.send_typing(bot_id, chat_id)
        try:
            if not self.agent_executor:
                await self.send_message(bot_id, chat_id, "⚠️ Agent not configured.")
                return

            response = await self.agent_executor(
                chat_id=chat_id,
                message=text,
                provider_id=session.provider_id,
                model=session.model,
                history=session.history[-bot.max_history:],
            )

            session.history.append({"role": "user", "content": text})
            session.history.append({"role": "assistant", "content": response})

            await self.send_message(bot_id, chat_id, response)
        except Exception as e:
            logger.error(f"Telegram message handling error: {e}")
            await self.send_message(bot_id, chat_id, f"⚠️ Error: {str(e)[:200]}")

    async def _handle_command(self, bot_id: str, chat_id: str, session: TelegramChatSession,
                              text: str, user: Dict[str, Any]) -> None:
        """Handle Telegram bot commands."""
        bot = self.bots.get(bot_id)
        if not bot:
            return

        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        is_admin = chat_id in bot.admin_chat_ids

        if cmd == "/start":
            await self.send_message(
                bot_id, chat_id,
                f"👋 *{bot.name}*\n\nI'm your MAGoCo agent. Send me any message or use:\n"
                f"/model - Show/switch current model\n"
                f"/status - Session status\n"
                f"/clear - Clear conversation history"
            )
        elif cmd == "/model":
            current = f"{session.model or 'auto'} on {session.provider_id or 'default'}"
            await self.send_message(
                bot_id, chat_id,
                f"🤖 Current model: *{current}*\n\n"
                f"Switch with: `/model <provider_id> <model>`"
            )
        elif cmd == "/model" and args and is_admin:
            try:
                provider_id, model = args.split(maxsplit=1)
                session.provider_id = provider_id
                session.model = model
                await self.send_message(bot_id, chat_id, f"✅ Switched to {model} on {provider_id}")
            except ValueError:
                await self.send_message(bot_id, chat_id, "⚠️ Usage: /model <provider_id> <model>")
        elif cmd == "/status":
            await self.send_message(
                bot_id, chat_id,
                f"📊 *Session Status*\n"
                f"Messages: {len(session.history)}\n"
                f"Provider: {session.provider_id or 'default'}\n"
                f"Model: {session.model or 'auto'}\n"
                f"Active: {session.is_active}"
            )
        elif cmd == "/clear":
            session.history.clear()
            await self.send_message(bot_id, chat_id, "🗑️ History cleared.")
        elif cmd == "/help":
            await self.send_message(
                bot_id, chat_id,
                "📋 *Commands*\n"
                "/start - Introduction\n"
                "/model - Show current model\n"
                "/status - Session info\n"
                "/clear - Clear history\n"
                "/help - This message"
            )
        else:
            await self.send_message(bot_id, chat_id, "Unknown command. Try /help")

    # ---------- Polling ----------

    async def start_polling(self, bot_id: str) -> None:
        """Start long-polling for a bot."""
        bot = self.bots.get(bot_id)
        if not bot:
            return

        offset = 0
        logger.info(f"[Telegram] Starting polling for bot {bot_id}")

        while self._running:
            try:
                async with httpx.AsyncClient(timeout=35.0) as client:
                    r = await client.get(
                        f"{TELEGRAM_API}/bot{bot.token}/getUpdates",
                        params={"offset": offset, "timeout": 30, "allowed_updates": ["message"]}
                    )
                    r.raise_for_status()
                    data = r.json()

                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    asyncio.create_task(self.handle_update(bot_id, update))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Telegram] Polling error for {bot_id}: {e}")
                await asyncio.sleep(5)

    async def start(self) -> None:
        """Start all enabled bots."""
        self._running = True
        # Load from config file first
        self.load_from_config_file()

        for bot_id, bot in self.bots.items():
            if bot.enabled and bot.mode == TelegramMode.POLLING:
                task = asyncio.create_task(self.start_polling(bot_id))
                self._polling_tasks[bot_id] = task
        logger.info(f"[Telegram] Started {len(self._polling_tasks)} bots")

    async def stop(self) -> None:
        """Stop all bots."""
        self._running = False
        for task in self._polling_tasks.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._polling_tasks.clear()
        logger.info("[Telegram] All bots stopped")

    # ---------- Webhook ----------

    async def handle_webhook(self, bot_id: str, secret_token: str, update: Dict[str, Any]) -> bool:
        """Handle an incoming webhook update."""
        bot = self.bots.get(bot_id)
        if not bot:
            return False
        # Verify secret token if configured
        expected = bot.metadata.get("webhook_secret", "")
        if expected and secret_token != expected:
            return False
        await self.handle_update(bot_id, update)
        return True

    def get_stats(self) -> Dict[str, Any]:
        return {
            "bots": len(self.bots),
            "active_sessions": len(self.sessions),
            "polling_bots": len(self._polling_tasks),
            "running": self._running,
        }

    def load_from_config_file(self, config_path: str = "./data/telegram/telegram.json") -> int:
        """Load Telegram bots from a JSON config file.

        Format:
        {
            "version": "1.0",
            "bots": [
                {
                    "name": "My Assistant Bot",
                    "token": "123456789:AAF...",
                    "mode": "polling",
                    "webhook_url": "",
                    "allowed_chat_ids": [],
                    "admin_chat_ids": [],
                    "default_provider_id": "openai",
                    "default_model": "gpt-4o",
                    "system_prompt": "",
                    "max_history": 20,
                    "enabled": true
                }
            ]
        }
        """
        from pathlib import Path
        path = Path(config_path)
        if not path.exists():
            logger.info(f"Telegram config file not found: {config_path}")
            return 0

        try:
            data = json.loads(path.read_text())
            bots_data = data.get("bots", [])
            if not bots_data:
                return 0

            loaded = 0
            for b in bots_data:
                bot_id = b.get("name", "").lower().strip().replace(" ", "-") or str(uuid.uuid4())[:8]
                mode_str = b.get("mode", "polling")
                mode = TelegramMode(mode_str) if mode_str in ("polling", "webhook") else TelegramMode.POLLING

                config = TelegramBotConfig(
                    bot_id=bot_id,
                    token=b.get("token", ""),
                    name=b.get("name", "MAGoCo Bot"),
                    mode=mode,
                    webhook_url=b.get("webhook_url", ""),
                    allowed_chat_ids=b.get("allowed_chat_ids", []),
                    admin_chat_ids=b.get("admin_chat_ids", []),
                    default_provider_id=b.get("default_provider_id"),
                    default_model=b.get("default_model"),
                    system_prompt=b.get("system_prompt", ""),
                    max_history=b.get("max_history", 20),
                    enabled=b.get("enabled", True),
                )
                self.add_bot(config)
                loaded += 1
                logger.info(f"[Telegram] Loaded bot from config: {config.name}")

            return loaded
        except Exception as e:
            logger.error(f"[Telegram] Error loading config {config_path}: {e}")
            return 0


# Global instance
telegram_gateway = TelegramGateway()

