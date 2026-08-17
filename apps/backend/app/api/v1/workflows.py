"""Workflow management endpoints - create, execute, monitor DAGs."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uuid

from app.api.deps import get_current_user
from app.models.user import User
from app.models.workflow import Workflow, WorkflowStatus, WorkflowNode, WorkflowEdge
from app.schemas.workflow import WorkflowCreate, WorkflowResponse, WorkflowExecuteRequest, WorkflowExecutionResponse
from app.db import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from magoco_workflows.engine import WorkflowEngine, WorkflowNode as WNode
from magoco_workflows import engine as workflow_engine

from app.services.workflows import WorkflowService

router = APIRouter(prefix="/workflows", tags=["workflows"])

@router.post("/", response_model=WorkflowResponse)
async def create_workflow(
    workflow: WorkflowCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new workflow definition."""
    wf = WorkflowModel(
        name=workflow.name,
        description=workflow.description,
        owner_id=current_user.id,
        owner=current_user,
        nodes=workflow.nodes,
        edges=workflow.edges,
    )
    db.add(wf)
    await db.commit()
    await db.refresh(wf)
    return wf

@router.post("/{workflow_id}/execute", response_model=WorkflowExecutionResponse)
async def execute_workflow(
    workflow_id: uuid.UUID,
    request: WorkflowExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Execute an existing workflow with optional input context."""
    wf = await db.get(WorkflowModel, workflow_id)
    if not wf:
        raise HTTPException(404, "Workflow not found")

    engine = WorkflowEngine()
    for node_def in wf.nodes:
        node = WNode(
            node_id=node_def.id,
            name=node_def.label,
            node_type=node_def.type,
            config=node_def.config,
            dependencies=set(node_def.dependencies),
        )
        engine.add_node(node)

    results = await engine.execute(context=request.context)
    return WorkflowExecutionResponse(
        workflow_id=workflow_id,
        status="completed",
        results=results,
        duration_seconds=0.0,
    )

@router.get("/", response_model=List[WorkflowResponse])
async def list_workflows(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all workflows for the current user."""
    result = await db.execute(
        select(WorkflowModel).where(WorkflowModel.owner_id == current_user.id)
    )
    workflows = result.scalars().all()
    return workflows