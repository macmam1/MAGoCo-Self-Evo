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
"""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
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
    """Coordinates multiple AgentWorkers through a pipeline."""

    def __init__(self, registry: ToolRegistry | None = None):
        self.registry = registry or tool_registry
        self.agents: dict[str, AgentWorker] = {}
        self.messages: list[AgentMessage] = []
        self.llm: Callable[..., Coroutine[Any, Any, str]] | None = None

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

        # 2. Architect designs
        design = await architect.run(
            f"Produce a design for: {user_goal}\nContext:\n{plan}"
        )
        self.send("architect_1", "coder_1", f"Design:\n{design}")
        steps.append({"agent": "architect_1", "role": "architect", "output": design})

        # 3. (optional) Researcher gathers info
        research = ""
        if researcher:
            research = await researcher.run(
                f"Gather background info for: {user_goal}\nDesign:\n{design}"
            )
            self.send("researcher_1", "coder_1", f"Research:\n{research}")
            steps.append({"agent": "researcher_1", "role": "researcher", "output": research})

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
