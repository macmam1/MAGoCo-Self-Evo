"""Multi-Agent Orchestration — specialized roles, task delegation, message passing.

Inspired by MetaGPT (software company simulation), OpenHands (orchestration),
and Hermes-Agent (self-improvement).

Roles:
- Coordinator: plans, splits tasks, collects results
- Architect:  designs solutions / file structures
- Coder:      writes implementation code
- Reviewer:   critiques and validates outputs
- Researcher: gathers information via tools

Each agent is a thin wrapper around a reasoning loop (ReActAgent or a simple
LLM call) with role-specific system instructions and tool scoping.

Integration with Planning System:
- Plans from PlanningEngine can be executed by the orchestrator
- Task dependencies are resolved automatically
- Parallel execution with configurable max_parallel
"""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine

from magoco_core.tools.registry import ToolRegistry, ToolResult, tool_registry


class AgentRole(str, Enum):
    COORDINATOR = "coordinator"
    ARCHITECT = "architect"
    CODER = "coder"
    REVIEWER = "reviewer"
    RESEARCHER = "researcher"


@dataclass
class AgentMessage:
    """A message passed between agents."""

    sender: str
    recipient: str  # "*" = broadcast
    role: AgentRole | None = None
    content: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sender": self.sender,
            "recipient": self.recipient,
            "role": self.role.value if self.role else None,
            "content": self.content,
            "tool_calls": self.tool_calls,
            "metadata": self.metadata,
        }


@dataclass
class AgentConfig:
    """Configuration for a single agent instance."""

    name: str
    role: AgentRole
    system_prompt: str = ""
    model: str = "default"
    allowed_tools: list[str] | None = None  # None = all tools
    max_steps: int = 5
    temperature: float = 0.2


# ── Role system prompts ──────────────────────────────────────────────────────

ROLE_PROMPTS: dict[AgentRole, str] = {
    AgentRole.COORDINATOR: (
        "You are the Coordinator agent. You decompose the user's goal into "
        "concrete subtasks, assign them to specialist agents (Architect, Coder, "
        "Reviewer, Researcher), collect their outputs, and synthesize a final "
        "answer. You never implement code yourself; you delegate."
    ),
    AgentRole.ARCHITECT: (
        "You are the Architect agent. You design system architectures, file "
        "structures, module boundaries, and data models. You think before "
        "coding and produce clear, reviewable design documents."
    ),
    AgentRole.CODER: (
        "You are the Coder agent. You write clean, tested, production-grade "
        "code. You use file tools to inspect the workspace, implement changes, "
        "and run tests to verify your work."
    ),
    AgentRole.REVIEWER: (
        "You are the Reviewer agent. You critique code and designs for bugs, "
        "security issues, style violations, and missed edge cases. You provide "
        "actionable, prioritized feedback."
    ),
    AgentRole.RESEARCHER: (
        "You are the Researcher agent. You gather information using web search "
        "and other tools, summarize findings with citations, and report back "
        "facts only — no speculation."
    ),
}


class AgentWorker:
    """A single agent with a role, prompt, and tool scope."""

    def __init__(
        self,
        config: AgentConfig,
        registry: ToolRegistry | None = None,
        llm: Callable[..., Coroutine[Any, Any, str]] | None = None,
    ):
        self.config = config
        self.registry = registry or tool_registry
        self.llm = llm  # async fn(messages: list[dict]) -> str
        self.history: list[dict] = []
        self.inbox: list[AgentMessage] = []

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def role(self) -> AgentRole:
        return self.config.role

    async def _call_llm(self, prompt: str) -> str:
        if self.llm:
            return await self.llm([{"role": "user", "content": prompt}])
        # Fallback: no LLM configured — return a deterministic stub so the
        # orchestration flow remains testable without network access.
        return f"[{self.config.name} ({self.config.role.value})] simulated response to: {prompt[:120]}..."

    async def run(self, task: str, context: list[AgentMessage] | None = None) -> str:
        """Execute one task for this agent."""
        ctx_lines = "\n".join(f"[{m.sender} -> {m.recipient}]: {m.content}" for m in (context or []))
        prompt = (
            f"{self.config.system_prompt}\n\n"
            f"CONTEXT:\n{ctx_lines or '(none)'}\n\n"
            f"TASK: {task}\n\n"
            f"Respond with your result only."
        )
        self.history.append({"role": "user", "content": prompt})
        result = await self._call_llm(prompt)
        self.history.append({"role": "assistant", "content": result})
        return result

    def deliver(self, msg: AgentMessage) -> None:
        """Queue an incoming message."""
        self.inbox.append(msg)

    def drain_inbox(self) -> list[AgentMessage]:
        msgs = self.inbox
        self.inbox = []
        return msgs


class MultiAgentOrchestrator:
    """Coordinates multiple AgentWorkers through a pipeline.

    Supports:
    - Classic software-team pipeline (Coordinator → Architect → Coder → Reviewer → Coord)
    - Parallel specialist execution (Architect, Coder, Researcher run concurrently)
    - Background agents (run while user works on other things)
    - Scheduled agents (cron-triggered tasks)
    """

    def __init__(self, registry: ToolRegistry | None = None):
        self.registry = registry or tool_registry
        self.agents: dict[str, AgentWorker] = {}
        self.messages: list[AgentMessage] = []
        self.llm: Callable[..., Coroutine[Any, Any, str]] | None = None
        self.background_tasks: dict[str, asyncio.Task] = {}
        self.scheduler_interval: float | None = None

    def set_llm(self, llm: Callable[..., Coroutine[Any, Any, str]]) -> None:
        self.llm = llm

    def add_agent(self, config: AgentConfig) -> AgentWorker:
        worker = AgentWorker(config, registry=self.registry, llm=self.llm)
        self.agents[config.name] = worker
        return worker

    def add_default_team(self) -> None:
        """Add the standard five-role team."""
        for role in AgentRole:
            name = f"{role.value}_1"
            self.add_agent(
                AgentConfig(
                    name=name,
                    role=role,
                    system_prompt=ROLE_PROMPTS[role],
                )
            )

    def send(self, sender: str, recipient: str, content: str, **meta: Any) -> AgentMessage:
        msg = AgentMessage(sender=sender, recipient=recipient, content=content, metadata=meta)
        self.messages.append(msg)
        for agent in self.agents.values():
            if agent.name == recipient or recipient == "*":
                agent.deliver(msg)
        return msg

    async def run_pipeline(self, user_goal: str) -> dict:
        """Classic software-team pipeline:

        Coordinator plans -> Architect designs -> Coder implements ->
        Reviewer critiques -> Coordinator synthesizes final answer.
        """
        if "coordinator_1" not in self.agents:
            self.add_default_team()

        coordinator = self.agents["coordinator_1"]
        architect = self.agents["architect_1"]
        coder = self.agents["coder_1"]
        reviewer = self.agents["reviewer_1"]
        researcher = self.agents.get("researcher_1")

        steps: list[dict] = []

        # 1. Coordinator plans
        plan = await coordinator.run(
            f"Decompose this goal into 2-4 subtasks and name which specialist "
            f"should own each: {user_goal}"
        )
        self.send("coordinator_1", "architect_1", f"Goal: {user_goal}\nPlan: {plan}")
        steps.append({"agent": "coordinator_1", "role": "coordinator", "output": plan})

        # 2. Architect designs (parallel with researcher)
        research = ""
        if researcher:
            research_task = asyncio.create_task(
                researcher.run(
                    f"Gather background info for: {user_goal}\nDesign:\n{plan}"
                )
            )
            design = await architect.run(
                f"Produce a design for: {user_goal}\nContext:\n{plan}"
            )
            research = await research_task
            self.send("researcher_1", "coder_1", f"Research:\n{research}")
            steps.append({"agent": "researcher_1", "role": "researcher", "output": research})
        else:
            design = await architect.run(
                f"Produce a design for: {user_goal}\nContext:\n{plan}"
            )

        steps.append({"agent": "architect_1", "role": "architect", "output": design})

        # 4. Coder implements
        code = await coder.run(
            f"Implement the design:\n{design}\n\nResearch:\n{research}"
        )
        self.send("coder_1", "reviewer_1", f"Implementation:\n{code}")
        steps.append({"agent": "coder_1", "role": "coder", "output": code})

        # 5. Reviewer critiques
        review = await reviewer.run(f"Critique this implementation:\n{code}")
        steps.append({"agent": "reviewer_1", "role": "reviewer", "output": review})

        # 6. Coordinator synthesizes
        final = await coordinator.run(
            f"Synthesize a final answer from:\n"
            f"PLAN:\n{plan}\nDESIGN:\n{design}\nCODE:\n{code}\nREVIEW:\n{review}"
        )
        steps.append({"agent": "coordinator_1", "role": "coordinator", "output": final})

        return {
            "goal": user_goal,
            "steps": steps,
            "final": final,
            "messages": [m.to_dict() for m in self.messages],
        }

    async def run_background(self, agent_name: str, task: str, timeout: int = 30) -> str:
        """Run an agent task in background while user continues.

        Returns immediately with task ID; user can check status later.
        """
        if agent_name not in self.agents:
            raise ValueError(f"Agent {agent_name} not found")

        agent = self.agents[agent_name]

        async def _run():
            try:
                result = await agent.run(task, max_steps=5)
                return result
            except Exception as e:
                return f"ERROR: {e}"

        task = asyncio.create_task(_run())
        self.background_tasks[task.get_name() if task.get_name() else task.get_id()] = task
        return f"background_task_{len(self.background_tasks)}"

    async def check_background(self, task_id: str) -> dict:
        """Check status of a background task."""
        task = self.background_tasks.get(task_id)
        if not task:
            return {"status": "not_found", "result": None}

        if task.done():
            result = task.result()
            del self.background_tasks[task_id]
            return {"status": "completed", "result": result}
        return {"status": "running", "result": None}

    async def schedule_agent(self, agent_name: str, task: str, cron_expr: str = "*/5 * * * *") -> str:
        """Schedule an agent to run on a cron-like interval.

        In production: use APScheduler or cron. Simulated here with interval.
        """
        if agent_name not in self.agents:
            raise ValueError(f"Agent {agent_name} not found")

        agent = self.agents[agent_name]

        async def _scheduled_run():
            while True:
                try:
                    await asyncio.sleep(30)  # Simulate cron interval
                    result = await agent.run(task, max_steps=3)
                    # Log result somewhere (db, file, etc.)
                    print(f"[SCHEDULED] {agent_name}: {result[:100]}")
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"[SCHEDULED ERROR] {agent_name}: {e}")

        task = asyncio.create_task(_scheduled_run(), name=f"scheduled_{agent_name}")
        self.background_tasks[task.get_name()] = task
        return f"scheduled_{agent_name}"

    async def stop_scheduled(self, agent_name: str) -> None:
        """Stop a scheduled agent task."""
        task = self.background_tasks.get(agent_name)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.background_tasks[agent_name]

    async def execute_plan(self, plan_id: str, max_parallel: int = 3) -> dict:
        """Execute a plan from the Planning Engine using the agent team.

        This is the core OS integration: Planning → Orchestration → Execution.
        Validates + freezes + persists every step (durable, resumable, pausable).
        """
        from magoco_core.planning import planning_engine, PlanStatus, TaskStatus

        plan = planning_engine.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        errors = plan.validate()
        if errors:
            raise ValueError(f"Plan invalid: {errors[0]}")

        plan.frozen = True
        plan.status = PlanStatus.ACTIVE
        plan.started_at = plan.started_at or datetime.utcnow()
        planning_engine.save(plan, "orchestrated_start", f"max_parallel={max_parallel}")

        results = {
            "plan_id": plan_id,
            "tasks_executed": 0,
            "tasks_failed": 0,
            "task_results": [],
        }

        max_iterations = max(1, len(plan.tasks) * 4 + 10)
        for _ in range(max_iterations):
            if plan.status == PlanStatus.PAUSED:
                planning_engine.save(plan, "orchestrated_paused", "")
                break
            if plan.is_complete():
                break
            ready = plan.get_ready_tasks()
            if not ready:
                if not plan.get_running_tasks():
                    for t in plan.tasks:
                        if t.status == TaskStatus.PENDING and not t.is_ready(plan.completed_task_ids):
                            t.status = TaskStatus.BLOCKED
                    planning_engine.save(plan, "orchestrated_blocked", "")
                    break
                await asyncio.sleep(0.2)
                continue

            for task in ready[:max(1, max_parallel)]:
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.utcnow()
                task.attempts += 1

                agent = self._find_agent_for_task(task)
                if not agent:
                    task.status = TaskStatus.FAILED
                    task.error = f"No agent available for role: {task.agent_role}"
                    task.completed_at = datetime.utcnow()
                    plan.failed_task_ids.add(task.id)
                    results["tasks_failed"] += 1
                    continue

                try:
                    context = self._build_task_context(plan, task)
                    prompt = f"{task.name}: {task.description}\n\nContext:\n{context}"
                    if task.definition_of_done:
                        prompt += f"\n\nDefinition of done (must satisfy): {task.definition_of_done}"
                    result = await asyncio.wait_for(agent.run(prompt), timeout=task.timeout_seconds)

                    task.result = result
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = datetime.utcnow()
                    plan.completed_task_ids.add(task.id)
                    results["tasks_executed"] += 1
                    results["task_results"].append({
                        "task_id": task.id,
                        "task_name": task.name,
                        "agent": agent.name,
                        "result": str(result)[:500],
                    })
                except Exception as e:
                    task.error = str(e)
                    task.status = TaskStatus.FAILED
                    task.completed_at = datetime.utcnow()
                    plan.failed_task_ids.add(task.id)
                    results["tasks_failed"] += 1
            planning_engine.save(plan, "orchestrated_batch", f"+{len(ready)} tasks")

            await asyncio.sleep(0.2)

        if plan.status != PlanStatus.PAUSED:
            plan.status = PlanStatus.COMPLETED if not plan.has_failures() else PlanStatus.FAILED
            plan.completed_at = datetime.utcnow()
        planning_engine.save(plan, "orchestrated_finished", plan.status.value)

        return results
    
    def _find_agent_for_task(self, task) -> AgentWorker | None:
        """Find the best agent for a task based on role."""
        role_map = {
            "coordinator": "coordinator",
            "architect": "architect",
            "coder": "coder",
            "reviewer": "reviewer",
            "researcher": "researcher",
            "general": "coordinator",  # Default to coordinator
        }
        
        target_role = role_map.get(task.agent_role, "coordinator")
        
        # Find agent with matching role
        for agent in self.agents.values():
            if agent.role.value == target_role:
                return agent
        
        # Fallback to any available agent
        return next(iter(self.agents.values()), None)
    
    def _build_task_context(self, plan, task) -> str:
        """Build context from completed dependency tasks."""
        context_parts = []
        for dep_id in task.dependencies:
            dep_task = plan.get_task(dep_id)
            if dep_task and dep_task.status.value == "completed" and dep_task.result:
                context_parts.append(f"[{dep_task.name}]: {str(dep_task.result)[:300]}")
        
        return "\n".join(context_parts) if context_parts else "(no prior context)"

    def to_dict(self) -> dict:
        return {
            "agents": {
                name: {
                    "name": a.name,
                    "role": a.role.value,
                    "history_len": len(a.history),
                }
                for name, a in self.agents.items()
            },
            "message_count": len(self.messages),
        }
