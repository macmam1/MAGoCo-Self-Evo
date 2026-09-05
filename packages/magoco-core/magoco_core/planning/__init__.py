"""Planning System - Core OS Feature.

Two-layer planning architecture:
1. OS-Level Planning: System-wide task decomposition, dependency resolution, execution orchestration
2. Project-Level Planning: User-defined project plans with milestones, resources, and custom workflows
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set

from magoco_core.tools.registry import ToolRegistry, tool_registry


class PlanStatus(str, Enum):
    """Plan execution status."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    """Individual task status."""
    PENDING = "pending"
    READY = "ready"          # Dependencies met, ready to execute
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"      # Waiting for dependency


class PlanLayer(str, Enum):
    """Planning layer."""
    OS = "os"           # System-wide, automatic
    PROJECT = "project" # User-defined project plan


@dataclass
class PlanTask:
    """A single task in a plan."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    agent_role: str = "general"  # Which agent should execute
    tool_requirements: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # Task IDs this depends on
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Execution context
    assigned_provider: Optional[str] = None
    assigned_model: Optional[str] = None
    
    def is_ready(self, completed_tasks: Set[str]) -> bool:
        """Check if all dependencies are completed."""
        return all(dep in completed_tasks for dep in self.dependencies)
    
    def can_retry(self) -> bool:
        return self.status in (TaskStatus.FAILED, TaskStatus.BLOCKED)


@dataclass
class Plan:
    """A plan containing multiple tasks with dependencies."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    layer: PlanLayer = PlanLayer.OS
    project_id: Optional[str] = None  # For project-level plans
    tasks: List[PlanTask] = field(default_factory=list)
    status: PlanStatus = PlanStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Execution tracking
    current_task_index: int = 0
    completed_task_ids: Set[str] = field(default_factory=set)
    failed_task_ids: Set[str] = field(default_factory=set)
    
    def add_task(self, task: PlanTask) -> None:
        self.tasks.append(task)
        self.updated_at = datetime.utcnow()
    
    def get_task(self, task_id: str) -> Optional[PlanTask]:
        for t in self.tasks:
            if t.id == task_id:
                return t
        return None
    
    def get_ready_tasks(self) -> List[PlanTask]:
        """Get all tasks that are ready to execute (dependencies met)."""
        ready = []
        for task in self.tasks:
            if task.status == TaskStatus.PENDING and task.is_ready(self.completed_task_ids):
                task.status = TaskStatus.READY
                ready.append(task)
        return ready
    
    def get_running_tasks(self) -> List[PlanTask]:
        return [t for t in self.tasks if t.status == TaskStatus.RUNNING]
    
    def is_complete(self) -> bool:
        return all(t.status in (TaskStatus.COMPLETED, TaskStatus.SKIPPED) for t in self.tasks)
    
    def has_failures(self) -> bool:
        return any(t.status == TaskStatus.FAILED for t in self.tasks)
    
    def progress(self) -> Dict[str, Any]:
        total = len(self.tasks)
        completed = len([t for t in self.tasks if t.status == TaskStatus.COMPLETED])
        failed = len([t for t in self.tasks if t.status == TaskStatus.FAILED])
        running = len([t for t in self.tasks if t.status == TaskStatus.RUNNING])
        pending = len([t for t in self.tasks if t.status in (TaskStatus.PENDING, TaskStatus.READY)])
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "pending": pending,
            "percent": (completed / total * 100) if total > 0 else 0
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "layer": self.layer.value,
            "project_id": self.project_id,
            "status": self.status.value,
            "tasks": [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "agent_role": t.agent_role,
                    "tool_requirements": t.tool_requirements,
                    "dependencies": t.dependencies,
                    "status": t.status.value,
                    "result": str(t.result) if t.result else None,
                    "error": t.error,
                    "metadata": t.metadata,
                }
                for t in self.tasks
            ],
            "progress": self.progress(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class PlanningEngine:
    """Core planning engine - handles task decomposition, dependency resolution, and execution."""
    
    def __init__(self, llm_callable: Optional[Callable[..., Coroutine[Any, Any, str]]] = None):
        self.llm = llm_callable
        self.plans: Dict[str, Plan] = {}
        self.registry = tool_registry
    
    def create_plan(self, name: str, description: str, layer: PlanLayer = PlanLayer.OS, 
                    project_id: Optional[str] = None) -> Plan:
        """Create a new empty plan."""
        plan = Plan(name=name, description=description, layer=layer, project_id=project_id)
        self.plans[plan.id] = plan
        return plan
    
    async def decompose_goal(self, goal: str, context: str = "", 
                              layer: PlanLayer = PlanLayer.OS,
                              project_id: Optional[str] = None) -> Plan:
        """Decompose a high-level goal into a structured plan with tasks."""
        plan = self.create_plan(
            name=f"Plan: {goal[:50]}",
            description=goal,
            layer=layer,
            project_id=project_id
        )
        
        if not self.llm:
            # Fallback: create basic task structure
            return self._create_fallback_plan(plan, goal)
        
        # Use LLM to decompose the goal
        decomposition_prompt = f"""
Decompose this goal into 3-7 concrete, executable tasks with clear dependencies.

Goal: {goal}
Context: {context}

For each task, specify:
1. name: Short descriptive name
2. description: What needs to be done
3. agent_role: Which specialist (coordinator, architect, coder, reviewer, researcher, general)
4. tool_requirements: List of tools needed (file_read, file_write, file_list, python_exec, web_search, etc.)
5. dependencies: List of task names this depends on (empty if none)

Return as JSON array of tasks.
"""
        try:
            response = await self.llm([{"role": "user", "content": decomposition_prompt}])
            import json
            tasks_data = json.loads(response)
            
            # Create tasks with dependency resolution
            name_to_id = {}
            for i, td in enumerate(tasks_data):
                task = PlanTask(
                    name=td.get("name", f"Task {i+1}"),
                    description=td.get("description", ""),
                    agent_role=td.get("agent_role", "general"),
                    tool_requirements=td.get("tool_requirements", []),
                    dependencies=[],  # Will resolve after all created
                )
                plan.add_task(task)
                name_to_id[td.get("name", f"Task {i+1}")] = task.id
            
            # Resolve dependencies by name -> ID
            for i, td in enumerate(tasks_data):
                task = plan.tasks[i]
                deps = td.get("dependencies", [])
                task.dependencies = [name_to_id.get(d, d) for d in deps if d in name_to_id]
            
            return plan
        except Exception as e:
            return self._create_fallback_plan(plan, goal)
    
    def _create_fallback_plan(self, plan: Plan, goal: str) -> Plan:
        """Create a basic fallback plan when LLM is not available."""
        tasks = [
            PlanTask(name="Analyze Goal", description=f"Understand and break down: {goal}", 
                     agent_role="coordinator", tool_requirements=[]),
            PlanTask(name="Research", description="Gather necessary information",
                     agent_role="researcher", tool_requirements=["web_search"],
                     dependencies=[]),
            PlanTask(name="Design Solution", description="Create implementation approach",
                     agent_role="architect", tool_requirements=[],
                     dependencies=["Analyze Goal"]),
            PlanTask(name="Implement", description="Execute the implementation",
                     agent_role="coder", tool_requirements=["file_write", "python_exec"],
                     dependencies=["Design Solution", "Research"]),
            PlanTask(name="Review & Test", description="Verify implementation works",
                     agent_role="reviewer", tool_requirements=["file_read", "python_exec"],
                     dependencies=["Implement"]),
        ]
        for t in tasks:
            plan.add_task(t)
        return plan
    
    async def execute_plan(self, plan_id: str, 
                           agent_executor: Callable[[PlanTask], Coroutine[Any, Any, Any]],
                           max_parallel: int = 3) -> Plan:
        """Execute a plan with dependency-aware parallel execution."""
        plan = self.plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        
        plan.status = PlanStatus.ACTIVE
        plan.started_at = datetime.utcnow()
        
        while not plan.is_complete():
            # Get ready tasks
            ready = plan.get_ready_tasks()
            
            # Limit parallel execution
            running = plan.get_running_tasks()
            available_slots = max_parallel - len(running)
            
            if available_slots <= 0:
                await asyncio.sleep(0.5)
                continue
            
            # Start new tasks
            for task in ready[:available_slots]:
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.utcnow()
                asyncio.create_task(self._execute_task(plan, task, agent_executor))
            
            await asyncio.sleep(0.2)
        
        plan.status = PlanStatus.COMPLETED if not plan.has_failures() else PlanStatus.FAILED
        plan.completed_at = datetime.utcnow()
        return plan
    
    async def _execute_task(self, plan: Plan, task: PlanTask, 
                            agent_executor: Callable[[PlanTask], Coroutine[Any, Any, Any]]) -> None:
        try:
            result = await agent_executor(task)
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            plan.completed_task_ids.add(task.id)
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.utcnow()
            plan.failed_task_ids.add(task.id)
    
    def get_plan(self, plan_id: str) -> Optional[Plan]:
        return self.plans.get(plan_id)
    
    def list_plans(self, layer: Optional[PlanLayer] = None, 
                   project_id: Optional[str] = None) -> List[Plan]:
        plans = list(self.plans.values())
        if layer:
            plans = [p for p in plans if p.layer == layer]
        if project_id:
            plans = [p for p in plans if p.project_id == project_id]
        return sorted(plans, key=lambda p: p.created_at, reverse=True)


# Global planning engine instance
planning_engine = PlanningEngine()