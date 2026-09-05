"""Main FastAPI application entry point.

Supports both SQLite (default, zero-dependency) and PostgreSQL (production).
Database tables are auto-created on first startup.
Includes: Chat REST API, WebSocket, Workflow Engine, Integrations, and Audit Trail APIs.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import logging

logger = logging.getLogger(__name__)


def _track_growth(action: str, target: str, params: dict | None = None, session_id: str | None = None):
    try:
        from magoco_core.growth import get_growth_engine
        from magoco_core.growth.models import UsageEvent
        eng = get_growth_engine()
        eng.record(UsageEvent(agent_id="default", action=action, target=target, params=params or {}, session_id=session_id))
    except Exception as e:
        logger.debug(f"growth track skip: {e}")

from magoco_core.agents.react_agent import ReActAgent
from magoco_core.agents.orchestrator import MultiAgentOrchestrator
from magoco_core.memory.three_layer import ThreeLayerMemory
from magoco_core import tools  # Ensure all tools are registered
from magoco_core.evolution.engine import init_evolution_engine
from magoco_core.evolution.hitl import init_hitl_manager

from app.api.v1.chat import router as chat_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.executions import router as executions_router
from app.api.v1.workflows import router as workflows_router
from app.api.v1.skills import router as skills_router
from app.api.v1.features import router as features_router
from app.api.v1.workflow_executions import router as workflow_executions_router
from app.api.v1.memory import router as memory_router
from app.api.v1.integrations_registry import router as integrations_registry_router
from app.api.v1.growth import router as growth_router
from app.core.config import settings
from app.db import init_db
from app.services.browser_service import browser_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create DB tables, seed default orchestrator. Shutdown: nothing special."""
    print(f"[MAGoCo] Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")
    await init_db()
    print("[MAGoCo] Database initialized ✓")

    # Initialize evolution + HITL engines
    init_evolution_engine(ThreeLayerMemory())
    init_hitl_manager()

    # Initialize browser service
    await browser_service.start()
    print("[MAGoCo] Browser service started ✓")

    yield

    # Cleanup
    await browser_service.stop()
    print("[MAGoCo] Shutdown complete")


app = FastAPI(
    title="MAGoCo-Self-Evo Backend",
    description="Multi-Agent Go-Coordinator with Self-Evolution & Multi-Interface",
    version="0.3.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(chat_router, prefix="/api/v1")
app.include_router(workflows_router, prefix="/api/v1")
app.include_router(integrations_router, prefix="/api/v1")
app.include_router(executions_router, prefix="/api/v1")
app.include_router(skills_router, prefix="/api/v1")
app.include_router(features_router, prefix="/api/v1")
app.include_router(workflow_executions_router, prefix="/api/v1")
app.include_router(memory_router, prefix="/api/v1")
app.include_router(integrations_registry_router, prefix="/api/v1")
app.include_router(growth_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    db_type = "postgresql" if "postgresql" in settings.DATABASE_URL else "sqlite"
    return {
        "status": "ok",
        "version": "0.3.0",
        "database": db_type,
        "tools_available": len(tools.__dict__.get('tool_registry', {}).list_tools()) if hasattr(tools, '__dict__') else 0,
    }


# Simple Chat WebSocket
@app.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    await websocket.accept()

    agent = ReActAgent()
    memory = ThreeLayerMemory()

    try:
        while True:
            data = await websocket.receive_text()
            user_input = json.loads(data).get("message", "")

            memory.add_turn("user", user_input)
            await websocket.send_json({"type": "status", "content": "thinking"})

            result = await agent.run(user_input)
            memory.add_turn("assistant", result.content)
            _track_growth("chat", "send", {"len": len(user_input)})

            await websocket.send_json({
                "type": "message",
                "role": "assistant",
                "content": result.content,
                "metadata": result.metadata
            })

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        await websocket.send_json({"type": "error", "content": str(e)})
        await websocket.close()


# Browser Agent WebSocket
@app.websocket("/ws/browser")
async def websocket_browser_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")

            if msg_type == "new_session":
                session = await browser_service.create_session()
                await websocket.send_json({
                    "type": "session_created",
                    "sessionId": session.id,
                    "sessionData": await browser_service.get_session_state(session.id),
                })

            elif msg_type == "navigate":
                session_id = message.get("sessionId")
                url = message.get("url")
                session = browser_service.sessions.get(session_id)
                if session:
                    success = await browser_service.navigate(session, url)
                    _track_growth("browser", "navigate", {"url": (url or "")[:120]}, session_id)
                    await websocket.send_json({
                        "type": "session_updated",
                        "sessionId": session_id,
                        "sessionData": await browser_service.get_session_state(session_id),
                    })

            elif msg_type == "click":
                session_id = message.get("sessionId")
                x = message.get("x")
                y = message.get("y")
                session = browser_service.sessions.get(session_id)
                if session:
                    await browser_service.click(session, x, y)
                    _track_growth("browser", "click", {}, session_id)
                    await websocket.send_json({
                        "type": "session_updated",
                        "sessionId": session_id,
                        "sessionData": await browser_service.get_session_state(session_id),
                    })

            elif msg_type == "type":
                session_id = message.get("sessionId")
                text = message.get("text")
                session = browser_service.sessions.get(session_id)
                if session:
                    await browser_service.type(session, text)
                    _track_growth("browser", "type", {"len": len(text or "")}, session_id)
                    await websocket.send_json({
                        "type": "session_updated",
                        "sessionId": session_id,
                        "sessionData": await browser_service.get_session_state(session_id),
                    })

            elif msg_type == "close_session":
                session_id = message.get("sessionId")
                await browser_service.close_session(session_id)
                await websocket.send_json({
                    "type": "session_closed",
                    "sessionId": session_id,
                })

            elif msg_type == "pause":
                session_id = message.get("sessionId")
                session = browser_service.sessions.get(session_id)
                if session:
                    session.status = "paused"
                    await websocket.send_json({
                        "type": "session_updated",
                        "sessionId": session_id,
                        "sessionData": await browser_service.get_session_state(session_id),
                    })

            elif msg_type == "approve":
                session_id = message.get("sessionId")
                session = browser_service.sessions.get(session_id)
                if session and session.pending_click:
                    x = session.pending_click["x"]
                    y = session.pending_click["y"]
                    await browser_service.click(session, x, y)
                    session.pending_click = None
                    await websocket.send_json({
                        "type": "session_updated",
                        "sessionId": session_id,
                        "sessionData": await browser_service.get_session_state(session_id),
                    })

            # Periodic screenshot streaming for active sessions
            elif msg_type == "request_screenshot":
                session_id = message.get("sessionId")
                session = browser_service.sessions.get(session_id)
                if session:
                    await browser_service._capture_screenshot(session)
                    await websocket.send_json({
                        "type": "screenshot_frame",
                        "sessionId": session_id,
                        "screenshot": session.screenshot,
                        "status": session.status,
                    })

    except WebSocketDisconnect:
        logger.info("Browser WebSocket client disconnected")
    except Exception as e:
        logger.error(f"Browser WebSocket error: {e}")
        await websocket.send_json({"type": "error", "content": str(e)})
        await websocket.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
