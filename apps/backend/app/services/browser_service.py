"""Browser Agent Service - Playwright-based browser automation with screenshot streaming."""

import asyncio
import base64
import json
import uuid
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
import logging

logger = logging.getLogger(__name__)


@dataclass
class BrowserSession:
    """Represents a single browser session with its state."""
    id: str
    page: Page
    context: BrowserContext
    url: str = "about:blank"
    title: str = "New Tab"
    screenshot: str = ""  # base64 JPEG
    status: str = "idle"  # idle, loading, running, paused
    actions_pending: int = 0
    pending_click: Optional[Dict[str, int]] = None
    created_at: float = field(default_factory=lambda: asyncio.get_event_loop().time())


class BrowserAgentService:
    """
    Manages browser sessions for AI agents.
    Uses Playwright to control headless Chromium and streams screenshots via WebSocket.
    """

    def __init__(self):
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.sessions: Dict[str, BrowserSession] = {}
        self._screenshot_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Initialize Playwright and launch browser.

        Fault-tolerant: if browsers aren't downloaded (e.g. `playwright install`
        never ran), the service stays DOWN instead of crashing the whole
        backend. Browser endpoints return 503 until browsers are installed.
        """
        if self._running:
            return

        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
        except Exception as e:
            logger.warning(f"BrowserAgentService unavailable (run `playwright install`): {e}")
            self.playwright = None
            self.browser = None
            self._running = False
            return
        self._running = True
        logger.info("BrowserAgentService started")

    async def stop(self):
        """Clean up all sessions and browser."""
        for session in self.sessions.values():
            await session.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self._running = False
        logger.info("BrowserAgentService stopped")

    async def create_session(self, initial_url: str = "about:blank") -> BrowserSession:
        """Create a new browser session with its own context."""
        if not self._running:
            await self.start()
        if not self._running or not self.browser:
            raise RuntimeError("Browser unavailable: run `playwright install` on the server")

        context = await self.browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        page = await context.new_page()
        session_id = str(uuid.uuid4())[:8]

        session = BrowserSession(
            id=session_id,
            page=page,
            context=context,
            url=initial_url,
        )

        # Navigate to initial URL
        if initial_url != "about:blank":
            await self.navigate(session, initial_url)

        self.sessions[session_id] = session
        logger.info(f"Created browser session: {session_id}")

        return session

    async def close_session(self, session_id: str) -> bool:
        """Close a browser session."""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            await session.context.close()
            del self.sessions[session_id]
            logger.info(f"Closed browser session: {session_id}")
            return True
        return False

    async def navigate(self, session: BrowserSession, url: str) -> bool:
        """Navigate to a URL."""
        try:
            session.status = "loading"
            session.url = url

            # Ensure URL has a scheme
            if not url.startswith(("http://", "https://", "file://", "about:")):
                url = "https://" + url

            await session.page.goto(url, wait_until="networkidle", timeout=30000)
            session.title = await session.page.title()
            session.status = "idle"

            # Capture screenshot after navigation
            await self._capture_screenshot(session)
            return True

        except Exception as e:
            logger.error(f"Navigation failed for {url}: {e}")
            session.status = "idle"
            await self._capture_screenshot(session)
            return False

    async def click(self, session: BrowserSession, x: int, y: int) -> bool:
        """Click at coordinates (x, y)."""
        try:
            session.status = "running"
            await session.page.mouse.click(x, y)
            await session.page.wait_for_load_state("networkidle", timeout=10000)
            session.title = await session.page.title()
            await self._capture_screenshot(session)
            session.status = "idle"
            return True
        except Exception as e:
            logger.error(f"Click failed at ({x}, {y}): {e}")
            session.status = "idle"
            return False

    async def type(self, session: BrowserSession, text: str) -> bool:
        """Type text into focused element."""
        try:
            session.status = "running"
            await session.page.keyboard.type(text)
            await self._capture_screenshot(session)
            session.status = "idle"
            return True
        except Exception as e:
            logger.error(f"Type failed: {e}")
            session.status = "idle"
            return False

    async def _capture_screenshot(self, session: BrowserSession) -> str:
        """Capture and return base64 JPEG screenshot."""
        try:
            screenshot_bytes = await session.page.screenshot(
                type="jpeg",
                quality=75,
                full_page=False,
            )
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
            session.screenshot = f"data:image/jpeg;base64,{screenshot_b64}"
            return session.screenshot
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            return ""

    async def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current session state for WebSocket broadcast."""
        session = self.sessions.get(session_id)
        if not session:
            return None

        return {
            "id": session.id,
            "url": session.url,
            "title": session.title,
            "screenshot": session.screenshot,
            "status": session.status,
            "actions_pending": session.actions_pending,
        }


# Global service instance
browser_service = BrowserAgentService()