"""Workflow management endpoints - create, execute, monitor DAGs (ReactFlow graph format)."""

import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db import get_db
from app.models.user import User
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowExecuteRequest,
    WorkflowExecutionResponse,
    WorkflowResponse,
)
from app.services.workflows import WorkflowService

from magoco_workflows.engine import WorkflowEngine, WorkflowNode as WNode

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/", response_model=WorkflowResponse)
async def create_workflow(
    workflow: WorkflowCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new workflow definition (graph in ReactFlow format)."""
    svc = WorkflowService(db)
    return await svc.create(
        name=workflow.name,
        description=workflow.description,
        graph={"nodes": [], "edges": []},
        owner_id=current_user.id,
        workspace_id=workflow.workspace_id,
        is_public=workflow.is_public,
    )


def _build_engine(graph: dict[str, Any]) -> WorkflowEngine:
    """Translate a ReactFlow graph into an executable engine."""
    engine = WorkflowEngine()
    nodes = graph.get("nodes", []) if isinstance(graph, dict) else []
    edges = graph.get("edges", []) if isinstance(graph, dict) else []
    deps: dict[str, set] = {n.get("id"): set() for n in nodes if n.get("id")}
    for e in edges:
        if e.get("target") in deps and e.get("source"):
            deps[e["target"]].add(e["source"])
    for n in nodes:
        if not n.get("id"):
            continue
        data = n.get("data", {}) or {}
        engine.add_node(WNode(
            node_id=n["id"],
            name=str(data.get("label", n["id"])),
            node_type=str(n.get("type", "agent")),
            config=dict(data),
            dependencies=deps.get(n["id"], set()),
        ))
    return engine


@router.post("/{workflow_id}/execute", response_model=WorkflowExecutionResponse)
async def execute_workflow(
    workflow_id: uuid.UUID,
    request: WorkflowExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Execute an existing workflow with optional input context."""
    svc = WorkflowService(db)
    wf = await svc.get(workflow_id)
    if not wf or wf.owner_id != current_user.id:
        raise HTTPException(404, "Workflow not found")

    engine = _build_engine(wf.graph or {})
    started = time.monotonic()
    try:
        results = await engine.execute(context=request.context)
        status = "completed"
    except Exception as e:
        raise HTTPException(500, f"Workflow failed: {e}")
    return WorkflowExecutionResponse(
        workflow_id=workflow_id,
        status=status,
        results=results or {},
        duration_seconds=time.monotonic() - started,
    )


@router.get("/", response_model=list[WorkflowResponse])
async def list_workflows(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all workflows for the current user."""
    return await WorkflowService(db).list_for_owner(current_user.id)
