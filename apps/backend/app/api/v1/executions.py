"""Execution History endpoints — audit trail of workflow runs."""

from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.workflow import Workflow
from app.models.integration import WorkflowExecution

router = APIRouter(prefix="/executions", tags=["executions"])


class ExecutionOut(BaseModel):
    id: UUID
    workflow_id: UUID
    status: str
    duration_ms: Optional[int]
    error_message: Optional[str]
    started_at: str
    completed_at: Optional[str]

    class Config:
        from_attributes = True


class ExecutionDetail(ExecutionOut):
    input_context: Dict[str, Any]
    output: Optional[Dict[str, Any]]
    execution_log: List[Dict[str, Any]]


@router.get("/", response_model=List[ExecutionOut])
async def list_executions(
    workflow_id: Optional[UUID] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(WorkflowExecution)
        .where(WorkflowExecution.workflow_id.in_(
            select(Workflow.id).where(Workflow.owner_id == current_user.id)
        ))
    )
    
    if workflow_id:
        query = query.where(WorkflowExecution.workflow_id == workflow_id)
    
    query = query.order_by(desc(WorkflowExecution.started_at)).limit(limit).offset(offset)
    
    result = await db.execute(query)
    items = result.scalars().all()
    return [
        ExecutionOut(
            id=i.id,
            workflow_id=i.workflow_id,
            status=i.status,
            duration_ms=i.duration_ms,
            error_message=i.error_message,
            started_at=i.started_at.isoformat() if i.started_at else "",
            completed_at=i.completed_at.isoformat() if i.completed_at else None,
        )
        for i in items
    ]


@router.get("/{execution_id}", response_model=ExecutionDetail)
async def get_execution(
    execution_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    exec = await db.get(WorkflowExecution, execution_id)
    if not exec:
        raise HTTPException(404, "Execution not found")
    
    # Verify ownership via workflow
    workflow = await db.get(exec.workflow, exec.workflow_id) if exec.workflow_id else None
    if not workflow or workflow.owner_id != current_user.id:
        raise HTTPException(403, "Not authorized")
    
    return ExecutionDetail(
        id=exec.id,
        workflow_id=exec.workflow_id,
        status=exec.status,
        duration_ms=exec.duration_ms,
        error_message=exec.error_message,
        started_at=exec.started_at.isoformat() if exec.started_at else "",
        completed_at=exec.completed_at.isoformat() if exec.completed_at else None,
        input_context=exec.input_context,
        output=exec.output,
        execution_log=exec.execution_log,
    )