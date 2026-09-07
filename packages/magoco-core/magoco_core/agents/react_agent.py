"""ReAct (Reasoning + Acting) Agent Loop with real LLM integration.

Uses LLM Gateway for intelligent reasoning. Falls back to rule-based
parsing when no LLM provider is available.
"""

import json
import asyncio
from typing import Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field

from magoco_core.tools.registry import tool_registry, Tool, ToolResult


@dataclass
class ReActStep:
    thought: str
    action: str
    action_input: dict[str, Any]
    observation: str
    success: bool = True


class ReActAgent:
    """ReAct (Reasoning + Acting) agent with tool execution loop.

    - When LLM is available: uses real reasoning via LLM Gateway
    - When LLM is NOT available: falls back to rule-based tool parsing
    """

    def __init__(self, llm_callable: Optional[Callable] = None):
        self.llm = llm_callable
        self.steps: list[ReActStep] = []
        self.memory: list[dict] = []

    def _get_tool_schemas(self) -> str:
        tools = tool_registry.list_tools()
        return json.dumps([t.parameters for t in tools], indent=2)

    def _get_tool_names(self) -> str:
        return ", ".join(t.name for t in tool_registry.list_tools())

    async def _call_llm(self, user_input: str, provider_id: Optional[str] = None,
                          model: Optional[str] = None) -> str:
        """Try user-configured providers first, then env gateway, then rules."""
        if self.llm:
            try:
                return await self.llm(user_input)
            except Exception:
                pass

        # 1. User-configured providers (Settings -> Providers, encrypted keys)
        try:
            from magoco_core.llm.registry import get_provider_registry
            from magoco_core.llm import LLMMessage
            reg = get_provider_registry()
            configs = reg.list(enabled_only=True)
            if provider_id:
                configs = [c for c in configs if c.id == provider_id] or configs
            for cfg in configs:
                try:
                    runtime = reg.to_runtime(cfg)
                    if not await runtime.is_available():
                        continue
                    resp = await runtime.complete(
                        [LLMMessage(role="user", content=user_input)],
                        model=model or cfg.default_model or (cfg.models[0] if cfg.models else ""),
                    )
                    return resp.content
                except Exception:
                    continue
        except Exception:
            pass

        # 2. Legacy env-based gateway (OPENAI_API_KEY / Ollama env)
        try:
            from magoco_core.llm import llm_gateway, LLMMessage
            messages = [LLMMessage(role="user", content=user_input)]
            response = await llm_gateway.complete(messages)
            return response.content
        except Exception:
            pass

        # Rule-based fallback: parse tool commands and generate thought
        parts = user_input.strip().split()
        if parts:
            cmd = parts[0].lower()
            if cmd in ("read", "write", "list", "exec"):
                return f"Detected tool command: {cmd}. I will execute it using the available tools."
            return f"I received the input: '{user_input}'. I'll process it with available tools."
        return "No input provided."

    async def run(self, user_input: str, max_steps: int = 3,
                    provider_id: Optional[str] = None, model: Optional[str] = None) -> ToolResult:
        """Run the ReAct loop on user input."""
        self.memory.append({"role": "user", "content": user_input})

        # Step 1: Think
        thought = await self._call_llm(user_input, provider_id=provider_id, model=model)
        self.memory.append({"role": "assistant", "content": thought})

        # Step 2: Parse and Act
        parts = user_input.strip().split()
        if not parts:
            return ToolResult(success=True, content="No input provided")

        cmd = parts[0].lower()
        result = None

        if cmd in ("read", "write", "list"):
            if cmd == "read" and len(parts) >= 2:
                result = await self._act("file_read", path=parts[1])
            elif cmd == "write" and len(parts) >= 3:
                path = parts[1]
                content = " ".join(parts[2:])
                result = await self._act("file_write", path=path, content=content)
            elif cmd == "list":
                path = parts[1] if len(parts) >= 2 else "."
                result = await self._act("file_list", path=path)
            else:
                result = ToolResult(success=False, content="", error=f"Invalid usage for {cmd}")
        elif cmd == "exec":
            code = " ".join(parts[1:]) if len(parts) > 1 else ""
            result = await self._act("python_exec", code=code)
        else:
            # Plain message (no tool command): return the LLM's own response
            # instead of a canned placeholder, so chat works end-to-end.
            result = ToolResult(success=True, content=thought)

        # Record step
        self.steps.append(
            ReActStep(
                thought=thought,
                action=cmd,
                action_input={"raw_input": user_input},
                observation=result.content or "",
                success=result.success,
            )
        )

        # Step 3: Observe and respond
        return ToolResult(
            success=result.success,
            content=result.content,
            metadata={
                "memory": self.memory,
                "steps": len(self.steps),
                "thought": thought,
            },
        )

    async def _act(self, tool_name: str, require_approval: bool = False,
                   session_id: str = "", approval_timeout: float = 600.0,
                   purpose: str = "", lang: str = "en",
                   **kwargs) -> ToolResult:
        """Execute a tool action via the guarded executor (policy + hooks + audit).

        require_approval=False (default): legacy non-blocking run — unchanged behavior.
        require_approval=True: run_gated — ASK pauses for human approval in the
        Approvals tab (with plain-language explanation + the model's purpose
        statement), then resumes or aborts. Nothing executes while pending.
        """
        from magoco_core.security import default_executor

        if require_approval:
            result = await default_executor.run_gated(
                tool_name, kwargs, session_id=session_id, timeout=approval_timeout,
                purpose=purpose, lang=lang)
        else:
            result = await default_executor.run(tool_name, kwargs)
        self.memory.append({"role": "tool", "content": result.content})
        return result

    def get_trace(self) -> list[dict[str, Any]]:
        """Get full ReAct trace."""
        return [
            {"step": i, "thought": step.thought, "observation": step.observation}
            for i, step in enumerate(self.steps)
        ]
