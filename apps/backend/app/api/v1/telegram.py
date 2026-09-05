"""Telegram Gateway API - Manage Telegram bot integrations."""

from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel
from typing import Dict, List, Optional, Any

from magoco_core.integrations.telegram import (
    telegram_gateway, TelegramBotConfig, TelegramMode,
)

router = APIRouter(prefix="/telegram", tags=["telegram"])


class BotCreate(BaseModel):
    name: str
    token: str
    mode: str = "polling"  # polling | webhook
    webhook_url: str = ""
    allowed_chat_ids: List[str] = []
    admin_chat_ids: List[str] = []
    default_provider_id: Optional[str] = None
    default_model: Optional[str] = None
    system_prompt: str = ""
    max_history: int = 20


class BotUpdate(BaseModel):
    name: Optional[str] = None
    token: Optional[str] = None
    mode: Optional[str] = None
    webhook_url: Optional[str] = None
    allowed_chat_ids: Optional[List[str]] = None
    admin_chat_ids: Optional[List[str]] = None
    default_provider_id: Optional[str] = None
    default_model: Optional[str] = None
    system_prompt: Optional[str] = None
    max_history: Optional[int] = None
    enabled: Optional[bool] = None


class MessageRequest(BaseModel):
    chat_id: str
    text: str
    reply_markup: Optional[Dict] = None


@router.get("/status")
async def get_status():
    """Get Telegram gateway status."""
    return telegram_gateway.get_stats()


@router.post("/bots")
async def create_bot(req: BotCreate):
    """Register a new Telegram bot."""
    bot_id = req.name.lower().strip().replace(" ", "-")

    mode = TelegramMode(req.mode) if req.mode in ("polling", "webhook") else TelegramMode.POLLING

    config = TelegramBotConfig(
        bot_id=bot_id,
        token=req.token,
        name=req.name,
        mode=mode,
        webhook_url=req.webhook_url,
        allowed_chat_ids=req.allowed_chat_ids,
        admin_chat_ids=req.admin_chat_ids,
        default_provider_id=req.default_provider_id,
        default_model=req.default_model,
        system_prompt=req.system_prompt,
        max_history=req.max_history,
    )

    telegram_gateway.add_bot(config)

    # Auto-start if polling mode
    if mode == TelegramMode.POLLING:
        import asyncio
        asyncio.create_task(telegram_gateway.start_polling(bot_id))

    return {
        "success": True,
        "bot_id": bot_id,
        "name": req.name,
        "mode": mode.value,
        "message": "Bot registered. Use /start in your Telegram chat to begin."
    }


@router.get("/bots")
async def list_bots():
    """List all registered bots."""
    return [
        {
            "bot_id": b.bot_id,
            "name": b.name,
            "mode": b.mode.value,
            "enabled": b.enabled,
            "default_provider_id": b.default_provider_id,
            "default_model": b.default_model,
            "allowed_chats": len(b.allowed_chat_ids),
            "has_token": bool(b.token),
        }
        for b in telegram_gateway.bots.values()
    ]


@router.get("/bots/{bot_id}")
async def get_bot(bot_id: str):
    """Get bot details."""
    bot = telegram_gateway.bots.get(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return {
        "bot_id": bot.bot_id,
        "name": bot.name,
        "mode": bot.mode.value,
        "webhook_url": bot.webhook_url,
        "enabled": bot.enabled,
        "default_provider_id": bot.default_provider_id,
        "default_model": bot.default_model,
        "system_prompt": bot.system_prompt,
        "max_history": bot.max_history,
        "allowed_chat_ids": bot.allowed_chat_ids,
        "admin_chat_ids": bot.admin_chat_ids,
    }


@router.patch("/bots/{bot_id}")
async def update_bot(bot_id: str, req: BotUpdate):
    """Update bot configuration."""
    bot = telegram_gateway.bots.get(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    if req.name:
        bot.name = req.name
    if req.token:
        bot.token = req.token
    if req.mode and req.mode in ("polling", "webhook"):
        bot.mode = TelegramMode(req.mode)
    if req.webhook_url is not None:
        bot.webhook_url = req.webhook_url
    if req.allowed_chat_ids is not None:
        bot.allowed_chat_ids = req.allowed_chat_ids
    if req.admin_chat_ids is not None:
        bot.admin_chat_ids = req.admin_chat_ids
    if req.default_provider_id is not None:
        bot.default_provider_id = req.default_provider_id
    if req.default_model is not None:
        bot.default_model = req.default_model
    if req.system_prompt is not None:
        bot.system_prompt = req.system_prompt
    if req.max_history is not None:
        bot.max_history = req.max_history
    if req.enabled is not None:
        bot.enabled = req.enabled

    return {"success": True, "bot_id": bot_id}


@router.delete("/bots/{bot_id}")
async def delete_bot(bot_id: str):
    """Remove a bot."""
    telegram_gateway.remove_bot(bot_id)
    return {"success": True}


@router.get("/bots/{bot_id}/sessions")
async def get_bot_sessions(bot_id: str):
    """Get all chat sessions for a bot."""
    sessions = []
    for key, session in telegram_gateway.sessions.items():
        if key.startswith(f"{bot_id}:"):
            sessions.append({
                "chat_id": session.chat_id,
                "provider_id": session.provider_id,
                "model": session.model,
                "history_length": len(session.history),
                "is_active": session.is_active,
                "last_activity": session.last_activity.isoformat(),
            })
    return sessions


@router.post("/bots/{bot_id}/send")
async def send_message(bot_id: str, req: MessageRequest):
    """Send a message to a Telegram chat (admin/testing)."""
    try:
        await telegram_gateway.send_message(bot_id, req.chat_id, req.text, req.reply_markup)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)[:300])


@router.post("/webhook/{bot_id}")
async def telegram_webhook(bot_id: str, request: Request,
                            x_telegram_bot_api_secret_token: Optional[str] = Header(None)):
    """Telegram webhook endpoint."""
    update = await request.json()
    ok = await telegram_gateway.handle_webhook(bot_id, x_telegram_bot_api_secret_token or "", update)
    if not ok:
        raise HTTPException(status_code=404, detail="Bot not found or invalid secret")
    return {"ok": True}


@router.post("/start")
async def start_all():
    """Start all polling bots."""
    await telegram_gateway.start()
    return telegram_gateway.get_stats()


@router.post("/stop")
async def stop_all():
    """Stop all bots."""
    await telegram_gateway.stop()
    return telegram_gateway.get_stats()


@router.post("/test-token")
async def test_token(token: str):
    """Verify a Telegram bot token."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"https://api.telegram.org/bot{token}/getMe")
            r.raise_for_status()
            data = r.json()
        if data.get("ok"):
            me = data["result"]
            return {
                "valid": True,
                "username": me.get("username"),
                "first_name": me.get("first_name"),
                "can_join_groups": me.get("can_join_groups"),
            }
        return {"valid": False, "error": "Telegram returned ok=false"}
    except Exception as e:
        return {"valid": False, "error": str(e)[:300]}
