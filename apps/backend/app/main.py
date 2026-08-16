"""Main FastAPI application entry point.

Supports both SQLite (default, zero-dependency) and PostgreSQL (production).
Database tables are auto-created on first startup.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json

from magoco_core.agents.react_agent import ReActAgent
from magoco_core.memory.three_layer import ThreeLayerMemory
from magoco_core import tools  # Ensure all tools are registered

from app.api.v1.chat import router as chat_router
from app.core.config import settings
from app.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create DB tables. Shutdown: nothing special."""
    print(f"[MAGoCo] Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")
    await init_db()
    print("[MAGoCo] Database initialized ✓")
    yield
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


@app.get("/health")
async def health_check():
    db_type = "postgresql" if "postgresql" in settings.DATABASE_URL else "sqlite"
    return {
        "status": "ok",
        "version": "0.3.0",
        "database": db_type,
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)