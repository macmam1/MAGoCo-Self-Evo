"""Agent API endpoints."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db import get_db
from app.models.agent import Agent as AgentModel
from app.models.user import User
from app.schemas.agent import AgentCreate, AgentResponse, AgentUpdate
from app.services.agents import Agent, AgentConfig, AgentRunResult
from app.services.llm import get_provider
from pydantic import BaseModel

router = APIRouter()


class RunRequest(BaseModel):
    """Request to run an agent."""

    message: str
    reset_memory: bool = False


class RunResponse(BaseModel):
    """Result of running an agent."""

    content: str
    model: str
    provider: str
    tokens_input: int
    tokens_output: int


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: AgentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AgentModel:
    """ساخت agent جدید."""
    agent = AgentModel(
        name=payload.name,
        role=payload.role,
        description=payload.description,
        system_prompt=payload.system_prompt,
        llm_provider=payload.llm_provider,
        model_name=payload.model_name,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        tools=payload.tools,
        config=payload.config,
        is_public=payload.is_public,
        owner_id=current_user.id,
        workspace_id=payload.workspace_id,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    workspace_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AgentModel]:
    """لیست agent های کاربر."""
    query = select(AgentModel).where(
        (AgentModel.owner_id == current_user.id) | (AgentModel.is_public)
    )
    if workspace_id:
        query = query.where(AgentModel.workspace_id == workspace_id)
    query = query.offset(skip).limit(limit).order_by(AgentModel.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AgentModel:
    """دریافت agent با ID."""
    result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.owner_id != current_user.id and not agent.is_public:
        raise HTTPException(status_code=403, detail="Not allowed")
    return agent


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: uuid.UUID,
    payload: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AgentModel:
    """به‌روزرسانی agent."""
    result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    for field_, value in payload.model_dump(exclude_unset=True).items():
        setattr(agent, field_, value)

    await db.commit()
    await db.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """حذف agent."""
    result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    await db.delete(agent)
    await db.commit()


@router.post("/{agent_id}/run", response_model=RunResponse)
async def run_agent(
    agent_id: uuid.UUID,
    payload: RunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunResponse:
    """اجرای agent با یه پیام."""
    # دریافت agent
    result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
    agent_db = result.scalar_one_or_none()
    if not agent_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent_db.owner_id != current_user.id and not agent_db.is_public:
        raise HTTPException(status_code=403, detail="Not allowed")
    if not agent_db.is_active:
        raise HTTPException(status_code=400, detail="Agent is inactive")

    # ساخت Agent service
    try:
        llm = get_provider(agent_db.llm_provider)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"LLM provider unavailable: {e}") from e

    config = AgentConfig(
        name=agent_db.name,
        role=agent_db.role,
        system_prompt=agent_db.system_prompt,
        llm_provider=agent_db.llm_provider,
        model_name=agent_db.model_name,
        temperature=agent_db.temperature,
        max_tokens=agent_db.max_tokens,
        tool_names=agent_db.tools,
        config=agent_db.config,
    )
    agent = Agent(config=config, llm=llm)
    if payload.reset_memory:
        agent.reset_memory()

    try:
        result_run: AgentRunResult = await agent.run(payload.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent run failed: {e}") from e

    return RunResponse(
        content=result_run.content,
        model=result_run.model,
        provider=result_run.provider,
        tokens_input=result_run.tokens_input,
        tokens_output=result_run.tokens_output,
    )
