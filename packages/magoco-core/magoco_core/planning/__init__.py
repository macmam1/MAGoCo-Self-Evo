"""Planning System - Core OS Feature.

Two-layer planning architecture:
1. OS-Level Planning: System-wide task decomposition, dependency resolution, execution orchestration
2. Project-Level Planning: User-defined project plans with milestones, resources, and custom workflows

Professional contract (taskflow/PlanDB lessons):
- Plans are durable (SQLite) and validated (acyclic, known deps) BEFORE commit.
- Plans freeze on execution; mid-flight edits create a new version.
- Execution is dependency-aware, budgeted, receipt-logged, resumable.
"""

from __future__ import annotations

import asyncio
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

    # Professional fields (Atom oracle / cuddlytoddly QualityGate lessons)
    definition_of_done: str = ""   # verifiable success predicate for this task
    timeout_seconds: float = 300.0
    max_attempts: int = 2
    attempts: int = 0

    # Execution context
    assigned_provider: Optional[str] = None
    assigned_model: Optional[str] = None

    def is_ready(self, completed_tasks: Set[str]) -> bool:
        """Check if all dependencies are completed."""
        return all(dep in completed_tasks for dep in self.dependencies)

    def can_retry(self) -> bool:
        return self.status in (TaskStatus.FAILED, TaskStatus.BLOCKED) and self.attempts < self.max_attempts

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "agent_role": self.agent_role, "tool_requirements": self.tool_requirements,
            "dependencies": self.dependencies, "status": self.status.value,
            "result": str(self.result) if self.result else None, "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata, "definition_of_done": self.definition_of_done,
            "timeout_seconds": self.timeout_seconds, "max_attempts": self.max_attempts,
            "attempts": self.attempts, "assigned_provider": self.assigned_provider,
            "assigned_model": self.assigned_model,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlanTask":
        def _dt(v):
            return datetime.fromisoformat(v) if v else None
        return cls(
            id=data.get("id", uuid.uuid4().hex[:8]),
            name=data.get("name", ""), description=data.get("description", ""),
            agent_role=data.get("agent_role", "general"),
            tool_requirements=data.get("tool_requirements", []),
            dependencies=data.get("dependencies", []),
            status=TaskStatus(data.get("status", "pending")),
            result=data.get("result"), error=data.get("error"),
            started_at=_dt(data.get("started_at")), completed_at=_dt(data.get("completed_at")),
            metadata=data.get("metadata", {}),
            definition_of_done=data.get("definition_of_done", ""),
            timeout_seconds=float(data.get("timeout_seconds", 300.0)),
            max_attempts=int(data.get("max_attempts", 2)),
            attempts=int(data.get("attempts", 0)),
            assigned_provider=data.get("assigned_provider"),
            assigned_model=data.get("assigned_model"),
        )


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

    # Professional contract fields (taskflow freeze lesson)
    frozen: bool = False       # True once execution starts; edits require new version
    version: int = 1
    budget_tokens: int = 0     # 0 = unlimited
    budget_seconds: float = 0.0  # 0 = unlimited

    def add_task(self, task: PlanTask) -> None:
        if self.frozen:
            raise ValueError("Plan is frozen (executing/executed); create a new version to edit")
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
            "frozen": self.frozen,
            "version": self.version,
            "budget_tokens": self.budget_tokens,
            "budget_seconds": self.budget_seconds,
            "tasks": [t.to_dict() for t in self.tasks],
            "completed_task_ids": sorted(self.completed_task_ids),
            "failed_task_ids": sorted(self.failed_task_ids),
            "progress": self.progress(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Plan":
        def _dt(v):
            return datetime.fromisoformat(v) if v else None
        plan = cls(
            id=data.get("id", uuid.uuid4().hex[:8]),
            name=data.get("name", ""), description=data.get("description", ""),
            layer=PlanLayer(data.get("layer", "os")),
            project_id=data.get("project_id"),
            status=PlanStatus(data.get("status", "draft")),
            created_at=_dt(data.get("created_at")) or datetime.utcnow(),
            updated_at=_dt(data.get("updated_at")) or datetime.utcnow(),
            started_at=_dt(data.get("started_at")), completed_at=_dt(data.get("completed_at")),
            metadata=data.get("metadata", {}),
        )
        plan.frozen = bool(data.get("frozen", False))
        plan.version = int(data.get("version", 1))
        plan.budget_tokens = int(data.get("budget_tokens", 0))
        plan.budget_seconds = float(data.get("budget_seconds", 0.0))
        for td in data.get("tasks", []):
            plan.tasks.append(PlanTask.from_dict(td))
        plan.completed_task_ids = set(data.get("completed_task_ids", []))
        plan.failed_task_ids = set(data.get("failed_task_ids", []))
        return plan

    def validate(self) -> List[str]:
        """Verify the plan as an executable contract (taskflow lesson).

        Checks: non-empty, unique IDs, known deps, no self-deps, acyclic.
        Returns list of error strings (empty = valid).
        """
        errors: List[str] = []
        if not self.tasks:
            return ["plan has no tasks"]
        ids = [t.id for t in self.tasks]
        if len(set(ids)) != len(ids):
            errors.append("duplicate task ids")
        idset = set(ids)
        for t in self.tasks:
            for dep in t.dependencies:
                if dep == t.id:
                    errors.append(f"task {t.id} depends on itself")
                elif dep not in idset:
                    errors.append(f"task {t.id} depends on unknown {dep}")
        # Cycle detection (DFS)
        visiting: Set[str] = set()
        visited: Set[str] = set()

        def visit(nid: str, stack: List[str]) -> None:
            if nid in visited:
                return
            if nid in visiting:
                errors.append("dependency cycle: " + " -> ".join(stack + [nid]))
                return
            visiting.add(nid)
            node = next((x for x in self.tasks if x.id == nid), None)
            if node:
                for dep in node.dependencies:
                    visit(dep, stack + [nid])
            visiting.discard(nid)
            visited.add(nid)

        for tid in ids:
            visit(tid, [])
        return errors

    # ---------- Mid-flight editing (PlanDB/cuddlytoddly: living hypothesis) ----------
    # All three preserve completed unrelated work; only the affected branch re-runs.

    def split_task(self, task_id: str, subtasks: List["PlanTask"]) -> List["PlanTask"]:
        """Replace one task with finer subtasks; dependents rewire to the LAST subtask.

        The original becomes a skipped parent record (audit trail preserved).
        """
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        if self.frozen and task.status in (TaskStatus.RUNNING, TaskStatus.COMPLETED):
            raise ValueError("Cannot split a running/completed task on a frozen plan")
        if not subtasks:
            raise ValueError("split requires at least one subtask")
        # Chain subtasks sequentially, inheriting the original's dependencies
        prev_id: Optional[str] = None
        for sub in subtasks:
            sub.dependencies = list(task.dependencies) if prev_id is None else [prev_id]
            self.tasks.append(sub)
            prev_id = sub.id
        last_id = subtasks[-1].id
        # Rewire dependents of the original to the last subtask
        for t in self.tasks:
            if t.id != task_id and task_id in t.dependencies:
                t.dependencies = [last_id if d == task_id else d for d in t.dependencies]
        task.status = TaskStatus.SKIPPED
        task.metadata["split_into"] = [s.id for s in subtasks]
        task.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        return subtasks

    def insert_task_after(self, task_id: str, task: "PlanTask") -> "PlanTask":
        """Insert a missed step between a task and its current dependents."""
        anchor = self.get_task(task_id)
        if not anchor:
            raise ValueError(f"Task not found: {task_id}")
        if self.frozen and anchor.status in (TaskStatus.RUNNING, TaskStatus.COMPLETED):
            raise ValueError("Cannot insert after a running/completed task on a frozen plan")
        task.dependencies = [task_id]
        self.tasks.append(task)
        for t in self.tasks:
            if t.id not in (task_id, task.id) and task_id in t.dependencies:
                # Only rewire PENDING dependents (running/completed history stays intact)
                if t.status == TaskStatus.PENDING:
                    t.dependencies = [task.id if d == task_id else d for d in t.dependencies]
        self.updated_at = datetime.utcnow()
        return task

    def pivot_subtree(self, task_id: str, new_description: str = "") -> List[str]:
        """Abandon an approach: reset the task + all downstream to pending.

        Completed unrelated branches are preserved; only the affected
        downstream re-runs (forgeplan causal-invalidation lesson).
        """
        root = self.get_task(task_id)
        if not root:
            raise ValueError(f"Task not found: {task_id}")
        # Collect downstream closure
        affected = {task_id}
        changed = True
        while changed:
            changed = False
            for t in self.tasks:
                if t.id not in affected and any(d in affected for d in t.dependencies):
                    affected.add(t.id)
                    changed = True
        reset: List[str] = []
        for t in self.tasks:
            if t.id in affected and t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED,
                                                 TaskStatus.BLOCKED, TaskStatus.SKIPPED,
                                                 TaskStatus.READY):
                t.status = TaskStatus.PENDING
                t.result = None
                t.error = None
                t.completed_at = None
                self.completed_task_ids.discard(t.id)
                self.failed_task_ids.discard(t.id)
                reset.append(t.id)
        if new_description:
            root.description = new_description
        # Un-freeze for re-execution of the branch (version bump records the pivot)
        self.version += 1
        self.frozen = False
        self.status = PlanStatus.DRAFT
        self.updated_at = datetime.utcnow()
        return reset

    def critical_path(self) -> List[str]:
        """Longest dependency chain (PlanDB lesson) — focus where it matters."""
        memo: Dict[str, List[str]] = {}

        def longest(nid: str) -> List[str]:
            if nid in memo:
                return memo[nid]
            node = next((x for x in self.tasks if x.id == nid), None)
            if not node or not node.dependencies:
                memo[nid] = [nid]
                return memo[nid]
            best: List[str] = []
            for dep in node.dependencies:
                cand = longest(dep)
                if len(cand) > len(best):
                    best = cand
            memo[nid] = best + [nid]
            return memo[nid]

        best: List[str] = []
        for t in self.tasks:
            cand = longest(t.id)
            if len(cand) > len(best):
                best = cand
        return best


class PlanningEngine:
    """Core planning engine - handles task decomposition, dependency resolution, and execution.

    Durable (SQLite via PlanStore); validates every plan as an executable
    contract before commit; freezes plans on execution.
    """

    def __init__(self, llm_callable: Optional[Callable[..., Coroutine[Any, Any, str]]] = None,
                 db_path: Optional[str] = None):
        from magoco_core.planning.store import get_plan_store
        self.llm = llm_callable
        self.store = get_plan_store(db_path)
        self.registry = tool_registry

    def _persist(self, plan: Plan, event: str = "", detail: str = "") -> None:
        plan.updated_at = datetime.utcnow()
        self.store.save(plan.to_dict())
        if event:
            self.store.log_event(plan.id, event, detail)

    def create_plan(self, name: str, description: str, layer: PlanLayer = PlanLayer.OS,
                    project_id: Optional[str] = None) -> Plan:
        """Create a new empty plan (validated + persisted)."""
        plan = Plan(name=name, description=description, layer=layer, project_id=project_id)
        self._persist(plan, "created", name)
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
            plan = self._create_fallback_plan(plan, goal)
            self._persist(plan, "decomposed", "fallback (no LLM)")
            return plan
        
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
                task.definition_of_done = td.get("definition_of_done", "")

            errors = plan.validate()
            if errors:
                # Keep the plan but mark the problem explicitly (never silently broken)
                plan.metadata["validation_errors"] = errors
            self._persist(plan, "decomposed", f"llm ({len(plan.tasks)} tasks)")
            return plan
        except Exception:
            plan = self._create_fallback_plan(plan, goal)
            self._persist(plan, "decomposed", "fallback (LLM error)")
            return plan

    def _create_fallback_plan(self, plan: Plan, goal: str) -> Plan:
        """Create a basic fallback plan when LLM is not available (ID-based deps)."""
        analyze = PlanTask(name="Analyze Goal", description=f"Understand and break down: {goal}",
                           agent_role="coordinator", tool_requirements=[],
                           definition_of_done="Goal restated in one line with 2-4 subtasks listed")
        research = PlanTask(name="Research", description="Gather necessary information",
                            agent_role="researcher", tool_requirements=["web_search"],
                            definition_of_done="Key facts collected with sources")
        design = PlanTask(name="Design Solution", description="Create implementation approach",
                          agent_role="architect", tool_requirements=[],
                          definition_of_done="Approach documented with file/module list")
        implement = PlanTask(name="Implement", description="Execute the implementation",
                             agent_role="coder", tool_requirements=["file_write", "python_exec"],
                             definition_of_done="Implementation complete and runnable")
        review = PlanTask(name="Review & Test", description="Verify implementation works",
                          agent_role="reviewer", tool_requirements=["file_read", "python_exec"],
                          definition_of_done="Tests pass or issues listed explicitly")
        for t in (analyze, research, design, implement, review):
            plan.add_task(t)
        design.dependencies = [analyze.id]
        implement.dependencies = [design.id, research.id]
        review.dependencies = [implement.id]
        return plan
    
    async def execute_plan(self, plan_id: str,
                           agent_executor: Callable[[PlanTask], Coroutine[Any, Any, Any]],
                           max_parallel: int = 3) -> Plan:
        """Execute a plan with dependency-aware parallel execution.

        Contract: validates first, freezes, runs ready batches with asyncio.gather
        (bounded iterations — never hangs), persists + logs receipts per batch.
        PAUSED plans resume from persisted state.
        """
        import time
        plan = self.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        errors = plan.validate()
        if errors:
            raise ValueError(f"Plan invalid: {errors[0]}")

        plan.frozen = True
        if plan.status != PlanStatus.PAUSED:
            plan.status = PlanStatus.ACTIVE
            plan.started_at = plan.started_at or datetime.utcnow()
        self._persist(plan, "execution_started", f"max_parallel={max_parallel}")
        start = time.time()

        max_iterations = max(1, len(plan.tasks) * (max(t.max_attempts for t in plan.tasks) + 2) + 10)
        for _ in range(max_iterations):
            if plan.status == PlanStatus.PAUSED:
                self._persist(plan, "execution_paused", "")
                return plan
            if plan.budget_seconds and (time.time() - start) > plan.budget_seconds:
                plan.status = PlanStatus.FAILED
                self._persist(plan, "budget_exceeded", f"{plan.budget_seconds}s")
                return plan
            if plan.is_complete():
                break
            ready = plan.get_ready_tasks()
            if not ready:
                # Deadlock: nothing ready, nothing running, not complete -> failed deps
                if not plan.get_running_tasks():
                    for t in plan.tasks:
                        if t.status == TaskStatus.PENDING and not t.is_ready(plan.completed_task_ids):
                            t.status = TaskStatus.BLOCKED
                    self._persist(plan, "deadlock_blocked", "")
                    break
                await asyncio.sleep(0.2)
                continue
            batch = ready[:max(1, max_parallel)]
            # Human approval gates (Mike-style team leadership): a task flagged
            # requires_approval pauses the whole plan BEFORE it runs. The human
            # approves in the Approvals tab, then re-runs execute to resume.
            gated = [t for t in batch if t.metadata.get("requires_approval")]
            if gated:
                # Already approved since pausing? Consume the approval and proceed.
                gated = [t for t in gated if not self.consume_gate_approval(plan, t)]
            if gated:
                from magoco_core.evolution.approvals_store import get_approvals_store
                for t in gated:
                    get_approvals_store().create(
                        agent_name="team-leader",
                        action_description=f"Phase gate: {t.name} — {t.metadata.get('approval_prompt', t.description)}",
                        proposed_input={"plan_id": plan.id, "task_id": t.id,
                                        "phase": "ship-gate"},
                        session_id=plan.project_id or "",
                    )
                plan.status = PlanStatus.PAUSED
                self._persist(plan, "phase_gate_waiting",
                              f"{len(gated)} task(s) awaiting human approval")
                return plan
            results = await asyncio.gather(
                *(self._execute_task(plan, task, agent_executor) for t in batch),
                return_exceptions=True,
            )
            for task, res in zip(batch, results):
                if isinstance(res, Exception):
                    task.error = str(res)
                    task.status = TaskStatus.FAILED
                    task.completed_at = datetime.utcnow()
                    plan.failed_task_ids.add(task.id)
            self._persist(plan, "batch_done", f"{len(batch)} tasks")

        plan.status = PlanStatus.COMPLETED if not plan.has_failures() else PlanStatus.FAILED
        plan.completed_at = datetime.utcnow()
        self._persist(plan, "execution_finished", plan.status.value)
        return plan

    async def _execute_task(self, plan: Plan, task: PlanTask,
                            agent_executor: Callable[[PlanTask], Coroutine[Any, Any, Any]]) -> None:
        from magoco_core.planning.quality import (
            check_dod, judge_with_llm, bridging_task_spec, new_task_id,
        )
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        task.attempts += 1
        try:
            result = await asyncio.wait_for(agent_executor(task), timeout=task.timeout_seconds)
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            plan.completed_task_ids.add(task.id)
            # QualityGate: verify output vs DoD; auto-inject bridging task on miss.
            try:
                if self.llm and task.metadata.get("llm_judge"):
                    verdict = await judge_with_llm(task.name, task.definition_of_done, result, self.llm)
                else:
                    verdict = check_dod(task.name, task.definition_of_done, result)
                task.metadata["quality"] = {"passed": verdict.passed, "score": verdict.score,
                                            "missing": verdict.missing, "method": verdict.method}
                if not verdict.passed and task.metadata.get("auto_bridge", True):
                    spec = bridging_task_spec(task.name, task.id, verdict)
                    bridge = PlanTask(id=new_task_id(), name=spec["name"],
                                      description=spec["description"],
                                      agent_role=spec["agent_role"],
                                      tool_requirements=spec["tool_requirements"],
                                      dependencies=spec["dependencies"],
                                      metadata=spec["metadata"],
                                      definition_of_done=spec["definition_of_done"])
                    plan.tasks.append(bridge)  # direct append: plan is frozen, injection is the exception
                    plan.updated_at = datetime.utcnow()
                    self.store.log_event(plan.id, "bridging_injected",
                                         f"{bridge.id} for {task.id}: {verdict.notes[:200]}")
            except Exception as qe:
                self.store.log_event(plan.id, "quality_check_error", str(qe)[:200])
            self.store.log_event(plan.id, "task_completed", f"{task.id} {task.name}")
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.utcnow()
            plan.failed_task_ids.add(task.id)
            self.store.log_event(plan.id, "task_failed", f"{task.id} {task.error[:200]}")

    def pause(self, plan_id: str) -> Optional[Plan]:
        plan = self.get_plan(plan_id)
        if not plan:
            return None
        plan.status = PlanStatus.PAUSED
        self._persist(plan, "paused", "")
        return plan

    def consume_gate_approval(self, plan: "Plan", task: "PlanTask") -> bool:
        """One-shot gate pass: if a human approved this (plan_id, task_id),
        clear the flag so re-execution proceeds past the gate exactly once."""
        try:
            from magoco_core.evolution.approvals_store import get_approvals_store
            store = get_approvals_store()
            hits = [a for a in store.find_by_ref("task_id", task.id)
                    if a.get("status") == "approved"
                    and str((a.get("proposed_input") or {}).get("plan_id")) == plan.id]
            if hits:
                task.metadata.pop("requires_approval", None)
                self._persist(plan, "gate_passed", task.id)
                return True
        except Exception:
            pass
        return False

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        data = self.store.load(plan_id)
        return Plan.from_dict(data) if data else None

    def list_plans(self, layer: Optional[PlanLayer] = None,
                   project_id: Optional[str] = None) -> List[Plan]:
        rows = self.store.list(layer.value if layer else None, project_id)
        plans = [Plan.from_dict(d) for d in rows]
        return sorted(plans, key=lambda p: p.created_at, reverse=True)

    def delete_plan(self, plan_id: str) -> bool:
        return self.store.delete(plan_id)

    def save(self, plan: Plan, event: str = "", detail: str = "") -> None:
        """Persist a mutated plan (call after any direct mutation)."""
        self._persist(plan, event, detail)

    def split(self, plan_id: str, task_id: str, subtasks: List[PlanTask]) -> Plan:
        plan = self.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        plan.split_task(task_id, subtasks)
        errors = plan.validate()
        if errors:
            raise ValueError(f"Split broke the plan: {errors[0]}")
        self._persist(plan, "task_split", f"{task_id} -> {[s.id for s in subtasks]}")
        return plan

    def insert_after(self, plan_id: str, task_id: str, task: PlanTask) -> Plan:
        plan = self.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        plan.insert_task_after(task_id, task)
        errors = plan.validate()
        if errors:
            raise ValueError(f"Insert broke the plan: {errors[0]}")
        self._persist(plan, "task_inserted", f"after {task_id}: {task.id}")
        return plan

    def pivot(self, plan_id: str, task_id: str, new_description: str = "") -> Plan:
        plan = self.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        reset = plan.pivot_subtree(task_id, new_description)
        self._persist(plan, "subtree_pivot", f"{task_id} reset {len(reset)} tasks")
        return plan

    def plan_events(self, plan_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        return self.store.events(plan_id, limit)


# Global planning engine instance
planning_engine = PlanningEngine()