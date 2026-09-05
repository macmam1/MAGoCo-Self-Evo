"""
Workflow Execution API Routes
REST API for executing and managing workflow runs
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime

from magoco_core.features import get_registry

from app.services.workflow_executor import (
    WorkflowExecutor,
    WorkflowExecution,
    execute_workflow,
    WORKFLOW_TEMPLATES,
)

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])


class WorkflowExecuteRequest(BaseModel):
    workflow_id: str
    input_data: Optional[Dict[str, Any]] = None


class WorkflowTemplateResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    workflow: Dict[str, Any]


class ExecutionResponse(BaseModel):
    execution_id: str
    workflow_id: str
    workflow_name: str
    status: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    error: Optional[str]
    nodes: Dict[str, Any]
    started_at: Optional[str]
    completed_at: Optional[str]


# In-memory execution storage (in production, use DB)
_executions: Dict[str, WorkflowExecution] = {}


@router.get("/templates", response_model=List[WorkflowTemplateResponse])
async def list_templates(category: Optional[str] = None):
    """List available workflow templates"""
    templates = WORKFLOW_TEMPLATES
    if category:
        templates = [t for t in templates if t["category"] == category]
    
    return [
        WorkflowTemplateResponse(
            id=t["id"],
            name=t["name"],
            description=t["description"],
            category=t["category"],
            workflow=t["workflow"],
        )
        for t in templates
    ]


@router.get("/templates/{template_id}")
async def get_template(template_id: str):
    """Get a specific template"""
    for t in WORKFLOW_TEMPLATES:
        if t["id"] == template_id:
            return t
    raise HTTPException(status_code=404, detail="Template not found")


@router.post("/execute", response_model=ExecutionResponse)
async def execute_workflow_endpoint(request: WorkflowExecuteRequest):
    """Execute a workflow"""
    # Find workflow definition
    workflow_def = None
    
    # First check templates
    for t in WORKFLOW_TEMPLATES:
        if t["id"] == request.workflow_id:
            workflow_def = t["workflow"]
            break
    
    # If not found in templates, could check DB or feature registry
    if not workflow_def:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Execute
    result = await execute_workflow(workflow_def, request.input_data or {})
    try:
        from magoco_core.growth import get_growth_engine
        from magoco_core.growth.models import UsageEvent
        get_growth_engine().record(UsageEvent(agent_id="default", action="workflow", target=request.workflow_id, params={}))
    except Exception:
        pass
    
    return ExecutionResponse(
        execution_id=result["execution_id"],
        workflow_id=request.workflow_id,
        workflow_name=next((t["name"] for t in WORKFLOW_TEMPLATES if t["id"] == request.workflow_id), "Unknown"),
        status=result["status"],
        input_data=request.input_data or {},
        output_data=result["output"],
        error=result.get("error"),
        nodes=result["nodes"],
        started_at=datetime.utcnow().isoformat(),
        completed_at=datetime.utcnow().isoformat(),
    )


@router.get("/executions", response_model=List[ExecutionResponse])
async def list_executions(
    workflow_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
):
    """List workflow executions"""
    executions = list(_executions.values())
    
    if workflow_id:
        executions = [e for e in executions if e.workflow_id == workflow_id]
    if status:
        executions = [e for e in executions if e.status.value == status]
    
    executions.sort(key=lambda e: e.started_at or datetime.min, reverse=True)
    
    return [
        ExecutionResponse(
            execution_id=e.id,
            workflow_id=e.workflow_id,
            workflow_name=e.workflow_name,
            status=e.status.value,
            input_data=e.input_data,
            output_data=e.output_data,
            error=e.error,
            nodes={nid: {"status": r.status.value, "output": r.output, "error": r.error} for nid, r in e.nodes.items()},
            started_at=e.started_at.isoformat() if e.started_at else None,
            completed_at=e.completed_at.isoformat() if e.completed_at else None,
        )
        for e in executions[:limit]
    ]


@router.get("/executions/{execution_id}", response_model=ExecutionResponse)
async def get_execution(execution_id: str):
    """Get execution details"""
    execution = _executions.get(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    return ExecutionResponse(
        execution_id=execution.id,
        workflow_id=execution.workflow_id,
        workflow_name=execution.workflow_name,
        status=execution.status.value,
        input_data=execution.input_data,
        output_data=execution.output_data,
        error=execution.error,
        nodes={nid: {"status": r.status.value, "output": r.output, "error": r.error} for nid, r in execution.nodes.items()},
        started_at=execution.started_at.isoformat() if execution.started_at else None,
        completed_at=execution.completed_at.isoformat() if execution.completed_at else None,
    )


@router.delete("/executions/{execution_id}")
async def delete_execution(execution_id: str):
    """Delete an execution record"""
    if execution_id not in _executions:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    del _executions[execution_id]
    return {"success": True}