"""REST API v1 endpoints for chat."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from magoco_core.agents.react_agent import ReActAgent
from magoco_core import tools

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    success: bool


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Run an agent on a single message (non-streaming)."""
    try:
        agent = ReActAgent()
        result = await agent.run(request.message)
        return ChatResponse(
            response=result.content,
            success=result.success,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools")
async def list_tools():
    """List all available tools."""
    return {
        "tools": [
            {"name": t.name, "description": t.description}
            for t in tools.tool_registry.list_tools()
        ]
    }
