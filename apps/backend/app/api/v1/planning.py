"""Planning API - OS-Level and Project-Level Planning."""

from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Any

from magoco_core.planning import (
    planning_engine, Plan, PlanTask, PlanStatus, TaskStatus, PlanLayer,
)

router = APIRouter(prefix="/planning", tags=["planning"])


# ===== Request/Response Models =====

class TaskCreate(BaseModel):
    name: str
    description: str = ""
    agent_role: str = "general"
    tool_requirements: List[str] = []
    dependencies: List[str] = []  # Task IDs
    metadata: Dict[str, Any] = {}
    definition_of_done: str = ""
    timeout_seconds: float = 300.0
    max_attempts: int = 2


def _make_task(tc: TaskCreate) -> PlanTask:
    return PlanTask(
        name=tc.name,
        description=tc.description,
        agent_role=tc.agent_role,
        tool_requirements=tc.tool_requirements,
        dependencies=tc.dependencies,
        metadata=tc.metadata,
        definition_of_done=tc.definition_of_done,
        timeout_seconds=tc.timeout_seconds,
        max_attempts=tc.max_attempts,
    )


class PlanCreate(BaseModel):
    name: str
    description: str = ""
    layer: str = "os"  # "os" or "project"
    project_id: Optional[str] = None
    tasks: List[TaskCreate] = []
    budget_tokens: int = 0
    budget_seconds: float = 0.0


class PlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    tasks: Optional[List[TaskCreate]] = None
    budget_tokens: Optional[int] = None
    budget_seconds: Optional[float] = None


class DecomposeRequest(BaseModel):
    goal: str
    context: str = ""
    layer: str = "os"
    project_id: Optional[str] = None


class ExecuteRequest(BaseModel):
    plan_id: str
    max_parallel: int = 3


# ===== Helper =====

def _plan_to_dict(plan: Plan) -> Dict[str, Any]:
    return plan.to_dict()


def _task_to_dict(task: PlanTask) -> Dict[str, Any]:
    return {
        "id": task.id,
        "name": task.name,
        "description": task.description,
        "agent_role": task.agent_role,
        "tool_requirements": task.tool_requirements,
        "dependencies": task.dependencies,
        "status": task.status.value,
        "result": str(task.result) if task.result else None,
        "error": task.error,
        "metadata": task.metadata,
        "definition_of_done": task.definition_of_done,
        "timeout_seconds": task.timeout_seconds,
        "max_attempts": task.max_attempts,
        "attempts": task.attempts,
    }


# ===== Plan CRUD =====

@router.post("/", response_model=Dict[str, Any])
async def create_plan(req: PlanCreate):
    """Create a new plan (OS or Project level)."""
    try:
        layer = PlanLayer(req.layer)
    except ValueError:
        raise HTTPException(status_code=400, detail="layer must be 'os' or 'project'")
    
    plan = planning_engine.create_plan(
        name=req.name,
        description=req.description,
        layer=layer,
        project_id=req.project_id
    )
    plan.budget_tokens = req.budget_tokens
    plan.budget_seconds = req.budget_seconds

    try:
        for tc in req.tasks:
            plan.add_task(_make_task(tc))
        errors = plan.validate()
        if errors:
            raise HTTPException(status_code=400, detail=f"Plan invalid: {errors[0]}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    planning_engine.save(plan, "created", f"{len(req.tasks)} tasks")

    return _plan_to_dict(plan)


@router.get("/", response_model=List[Dict[str, Any]])
async def list_plans(layer: Optional[str] = None, project_id: Optional[str] = None):
    """List all plans, optionally filtered by layer or project."""
    plan_layer = PlanLayer(layer) if layer else None
    plans = planning_engine.list_plans(layer=plan_layer, project_id=project_id)
    return [_plan_to_dict(p) for p in plans]


# NOTE: static GETs (/projects/..., /os/active) must stay ABOVE /{plan_id}.

@router.get("/projects/{project_id}/plans", response_model=List[Dict[str, Any]])
async def get_project_plans(project_id: str):
    """Get all plans for a specific project."""
    plans = planning_engine.list_plans(layer=PlanLayer.PROJECT, project_id=project_id)
    return [_plan_to_dict(p) for p in plans]


@router.get("/os/active", response_model=List[Dict[str, Any]])
async def get_active_os_plans():
    """Get all active OS-level plans (system-wide)."""
    plans = planning_engine.list_plans(layer=PlanLayer.OS)
    active = [p for p in plans if p.status in (PlanStatus.ACTIVE, PlanStatus.DRAFT)]
    return [_plan_to_dict(p) for p in active]


@router.get("/{plan_id}", response_model=Dict[str, Any])
async def get_plan(plan_id: str):
    """Get a specific plan with all tasks."""
    plan = planning_engine.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return _plan_to_dict(plan)


@router.patch("/{plan_id}", response_model=Dict[str, Any])
async def update_plan(plan_id: str, req: PlanUpdate):
    """Update a plan."""
    plan = planning_engine.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    if req.name:
        plan.name = req.name
    if req.description:
        plan.description = req.description
    if req.budget_tokens is not None:
        plan.budget_tokens = req.budget_tokens
    if req.budget_seconds is not None:
        plan.budget_seconds = req.budget_seconds
    if req.status:
        try:
            plan.status = PlanStatus(req.status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    
    if req.tasks is not None:
        if plan.frozen:
            raise HTTPException(status_code=400, detail="Plan is frozen; create a new version to edit")
        plan.tasks = []
        for tc in req.tasks:
            plan.add_task(_make_task(tc))
        errors = plan.validate()
        if errors:
            raise HTTPException(status_code=400, detail=f"Plan invalid: {errors[0]}")

    plan.updated_at = datetime.utcnow()
    planning_engine.save(plan, "updated", "")
    return _plan_to_dict(plan)


@router.delete("/{plan_id}")
async def delete_plan(plan_id: str):
    """Delete a plan."""
    if planning_engine.delete_plan(plan_id):
        return {"success": True}
    raise HTTPException(status_code=404, detail="Plan not found")


# ===== Task Management =====

@router.post("/{plan_id}/tasks", response_model=Dict[str, Any])
async def add_task(plan_id: str, req: TaskCreate):
    """Add a task to a plan (rejected when frozen or invalid)."""
    plan = planning_engine.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    try:
        task = _make_task(req)
        plan.add_task(task)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    errors = plan.validate()
    if errors:
        raise HTTPException(status_code=400, detail=f"Plan invalid: {errors[0]}")
    planning_engine.save(plan, "task_added", task.id)
    return _task_to_dict(task)


@router.patch("/{plan_id}/tasks/{task_id}", response_model=Dict[str, Any])
async def update_task(plan_id: str, task_id: str, req: TaskCreate):
    """Update a task in a plan."""
    plan = planning_engine.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    task = plan.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if plan.frozen:
        raise HTTPException(status_code=400, detail="Plan is frozen; create a new version to edit")
    task.name = req.name
    task.description = req.description
    task.agent_role = req.agent_role
    task.tool_requirements = req.tool_requirements
    task.dependencies = req.dependencies
    task.metadata = req.metadata
    task.definition_of_done = req.definition_of_done
    task.timeout_seconds = req.timeout_seconds
    task.max_attempts = req.max_attempts
    errors = plan.validate()
    if errors:
        raise HTTPException(status_code=400, detail=f"Plan invalid: {errors[0]}")
    plan.updated_at = datetime.utcnow()
    planning_engine.save(plan, "task_updated", task.id)

    return _task_to_dict(task)


@router.delete("/{plan_id}/tasks/{task_id}")
async def delete_task(plan_id: str, task_id: str):
    """Delete a task from a plan."""
    plan = planning_engine.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.frozen:
        raise HTTPException(status_code=400, detail="Plan is frozen; create a new version to edit")

    plan.tasks = [t for t in plan.tasks if t.id != task_id]
    plan.updated_at = datetime.utcnow()
    planning_engine.save(plan, "task_deleted", task_id)
    return {"success": True}


@router.post("/{plan_id}/pause")
async def pause_plan(plan_id: str):
    """Pause a running plan (resumable)."""
    plan = planning_engine.pause(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return _plan_to_dict(plan)


@router.get("/{plan_id}/critical-path", response_model=List[str])
async def plan_critical_path(plan_id: str):
    """Longest dependency chain — focus where it matters."""
    plan = planning_engine.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan.critical_path()


@router.get("/{plan_id}/events", response_model=List[Dict[str, Any]])
async def plan_events(plan_id: str, limit: int = 200):
    """Execution receipts / event log (audit + replay)."""
    plan = planning_engine.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return planning_engine.plan_events(plan_id, limit)


@router.get("/{plan_id}/validate", response_model=Dict[str, Any])
async def validate_plan(plan_id: str):
    """Verify the plan contract (acyclic, known deps) before execution."""
    plan = planning_engine.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    errors = plan.validate()
    return {"valid": not errors, "errors": errors,
            "critical_path": plan.critical_path() if not errors else []}


# ===== AI-Powered Decomposition =====

@router.post("/decompose", response_model=Dict[str, Any])
async def decompose_goal(req: DecomposeRequest):
    """Decompose a high-level goal into a structured plan using AI."""
    try:
        layer = PlanLayer(req.layer)
    except ValueError:
        raise HTTPException(status_code=400, detail="layer must be 'os' or 'project'")
    
    plan = await planning_engine.decompose_goal(
        goal=req.goal,
        context=req.context,
        layer=layer,
        project_id=req.project_id
    )
    return _plan_to_dict(plan)


# ===== Execution =====

@router.post("/execute", response_model=Dict[str, Any])
async def execute_plan(req: ExecuteRequest):
    """Execute a plan with the default agent executor."""
    plan = planning_engine.get_plan(req.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Default executor using ReActAgent
    from magoco_core.agents.react_agent import ReActAgent
    agent = ReActAgent()
    
    async def executor(task: PlanTask):
        prompt = f"""
Task: {task.name}
Description: {task.description}
Agent Role: {task.agent_role}
Tools Available: {', '.join(task.tool_requirements) or 'none'}
Dependencies Results: {plan.completed_task_ids}
"""
        result = await agent.run(prompt)
        return result.content
    
    executed_plan = await planning_engine.execute_plan(req.plan_id, executor, req.max_parallel)
    return _plan_to_dict(executed_plan)


# ===== Orchestrator Execution (Planning → Multi-Agent Team) =====

class OrchestratedExecuteRequest(BaseModel):
    max_parallel: int = 3
    ensure_team: bool = True


@router.post("/{plan_id}/execute-orchestrated", response_model=Dict[str, Any])
async def execute_plan_orchestrated(plan_id: str, req: OrchestratedExecuteRequest = OrchestratedExecuteRequest()):
    """Execute a plan via MultiAgentOrchestrator (role-based team execution)."""
    from magoco_core.agents.orchestrator import MultiAgentOrchestrator
    plan = planning_engine.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    orch = MultiAgentOrchestrator()
    if req.ensure_team:
        orch.add_default_team()
    try:
        results = await orch.execute_plan(plan_id, max_parallel=req.max_parallel)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Orchestrated execution failed: {str(e)[:300]}")
    return {
        "plan": _plan_to_dict(plan),
        "execution": results,
    }


# ===== Project-Level Planning Helpers (POST only — GETs moved above /{plan_id}) =====

@router.post("/projects/{project_id}/plans", response_model=Dict[str, Any])
async def create_project_plan(project_id: str, req: PlanCreate):
    """Create a plan specifically for a project."""
    req.layer = "project"
    req.project_id = project_id
    return await create_plan(req)