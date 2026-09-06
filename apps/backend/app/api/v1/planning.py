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


class PlanCreate(BaseModel):
    name: str
    description: str = ""
    layer: str = "os"  # "os" or "project"
    project_id: Optional[str] = None
    tasks: List[TaskCreate] = []


class PlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    tasks: Optional[List[TaskCreate]] = None


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
    
    for tc in req.tasks:
        task = PlanTask(
            name=tc.name,
            description=tc.description,
            agent_role=tc.agent_role,
            tool_requirements=tc.tool_requirements,
            dependencies=tc.dependencies,
            metadata=tc.metadata,
        )
        plan.add_task(task)
    
    return _plan_to_dict(plan)


@router.get("/", response_model=List[Dict[str, Any]])
async def list_plans(layer: Optional[str] = None, project_id: Optional[str] = None):
    """List all plans, optionally filtered by layer or project."""
    plan_layer = PlanLayer(layer) if layer else None
    plans = planning_engine.list_plans(layer=plan_layer, project_id=project_id)
    return [_plan_to_dict(p) for p in plans]


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
    if req.status:
        try:
            plan.status = PlanStatus(req.status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    
    if req.tasks is not None:
        plan.tasks = []
        for tc in req.tasks:
            task = PlanTask(
                name=tc.name,
                description=tc.description,
                agent_role=tc.agent_role,
                tool_requirements=tc.tool_requirements,
                dependencies=tc.dependencies,
                metadata=tc.metadata,
            )
            plan.add_task(task)
    
    plan.updated_at = datetime.utcnow()
    return _plan_to_dict(plan)


@router.delete("/{plan_id}")
async def delete_plan(plan_id: str):
    """Delete a plan."""
    if plan_id in planning_engine.plans:
        del planning_engine.plans[plan_id]
        return {"success": True}
    raise HTTPException(status_code=404, detail="Plan not found")


# ===== Task Management =====

@router.post("/{plan_id}/tasks", response_model=Dict[str, Any])
async def add_task(plan_id: str, req: TaskCreate):
    """Add a task to a plan."""
    plan = planning_engine.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    task = PlanTask(
        name=req.name,
        description=req.description,
        agent_role=req.agent_role,
        tool_requirements=req.tool_requirements,
        dependencies=req.dependencies,
        metadata=req.metadata,
    )
    plan.add_task(task)
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
    
    task.name = req.name
    task.description = req.description
    task.agent_role = req.agent_role
    task.tool_requirements = req.tool_requirements
    task.dependencies = req.dependencies
    task.metadata = req.metadata
    plan.updated_at = datetime.utcnow()
    
    return _task_to_dict(task)


@router.delete("/{plan_id}/tasks/{task_id}")
async def delete_task(plan_id: str, task_id: str):
    """Delete a task from a plan."""
    plan = planning_engine.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    plan.tasks = [t for t in plan.tasks if t.id != task_id]
    plan.updated_at = datetime.utcnow()
    return {"success": True}


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


# ===== Project-Level Planning Helpers =====

@router.get("/projects/{project_id}/plans", response_model=List[Dict[str, Any]])
async def get_project_plans(project_id: str):
    """Get all plans for a specific project."""
    plans = planning_engine.list_plans(layer=PlanLayer.PROJECT, project_id=project_id)
    return [_plan_to_dict(p) for p in plans]


@router.post("/projects/{project_id}/plans", response_model=Dict[str, Any])
async def create_project_plan(project_id: str, req: PlanCreate):
    """Create a plan specifically for a project."""
    req.layer = "project"
    req.project_id = project_id
    return await create_plan(req)


@router.get("/os/active", response_model=List[Dict[str, Any]])
async def get_active_os_plans():
    """Get all active OS-level plans (system-wide)."""
    plans = planning_engine.list_plans(layer=PlanLayer.OS)
    active = [p for p in plans if p.status in (PlanStatus.ACTIVE, PlanStatus.DRAFT)]
    return [_plan_to_dict(p) for p in active]