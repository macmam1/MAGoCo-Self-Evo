"""Telegram Bot Gateway for MAGoCo-Self-Evo."""

import os
import asyncio
import logging
import httpx
from typing import Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telegram_gateway")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


class TelegramGateway:
    """Telegram Bot Gateway that routes messages to Backend API."""

    def __init__(self, token: str = TELEGRAM_BOT_TOKEN):
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{token}"

    async def get_me() -> dict[str, Any]:
        """Check bot identity."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.api_url}/getMe")
            return resp.json()

    async def send_message(self, chat_id: int | str, text: str) -> dict[str, Any]:
        """Send message back to user via Telegram API."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.api_url}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
            )
            return resp.json()

    async def handle_update(self, update: dict[str, Any]) -> None:
        """Handle incoming update from Telegram webhook or long polling."""
        message = update.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")

        if not chat_id or not text:
            return

        logger.info(f"Received from Telegram [{chat_id}]: {text}")

        # Route to MAGoCo Backend Chat API
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{BACKEND_URL}/api/v1/chat",
                    json={"message": text}
                )
                if response.status_code == 200:
                    reply = response.json().get("response", "پاسخی دریافت نشد.")
                else:
                    reply = f"⚠️ خطا در سرویس بک‌اند: {response.status_code}"
        except Exception as e:
            reply = f"❌ خطای ارتباطی: {e}"

        await self.send_message(chat_id, reply)


if __name__ == "__main__":
    print("Telegram Gateway initialized. Pass TELEGRAM_BOT_TOKEN env to run.")
