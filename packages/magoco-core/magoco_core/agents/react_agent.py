"""ReAct (Reasoning + Acting) Agent Loop.

The agent thinks (Reason), chooses an action (Act), 
observes the result (Observe), and loops until completion.
"""

import json
import asyncio
from typing import Any
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
    """ReAct (Reasoning + Acting) agent with tool execution loop."""
    
    def __init__(self, llm_provider: str = "openai", model: str = "gpt-4o-mini"):
        self.llm_provider = llm_provider
        self.model = model
        self.steps: list[ReActStep] = []
        self.memory = []
    
    def _get_tool_schemas(self) -> str:
        """Get tool schemas for LLM prompt."""
        tools = tool_registry.list_tools()
        return json.dumps([t.parameters for t in tools], indent=2)
    
    def _get_tool_names(self) -> str:
        """Get tool names for LLM."""
        return ", ".join(t.name for t in tool_registry.list_tools())
    
    async def think(self, user_input: str) -> str:
        """Plan next action based on input."""
        self.memory.append({"role": "user", "content": user_input})
        
        # Simulate thinking (in real version this calls LLM)
        thought = f"I need to analyze '{user_input}' with available tools"
        self.memory.append({"role": "assistant", "content": thought})
        return thought
    
    async def act(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool action."""
        tool = tool_registry.get(tool_name)
        if not tool:
            return ToolResult(
                success=False, 
                content="", 
                error=f"Tool '{tool_name}' not found"
            )
        
        result = await tool.execute(**kwargs)
        self.memory.append({"role": "tool", "content": result.content})
        return result
    
    async def run(self, user_input: str, max_steps: int = 3) -> ToolResult:
        """Run the ReAct loop on user input."""
        
        # Step 1: Think about input
        thought = await self.think(user_input)
        
        # Parse tool commands
        parts = user_input.strip().split()
        if not parts:
            return ToolResult(success=True, content="No input provided")
        
        cmd = parts[0].lower()
        
        # Check if it's a tool call
        if cmd in ("read", "write", "list"):
            if cmd == "read" and len(parts) >= 2:
                result = await self.act("file_read", path=parts[1])
            elif cmd == "write" and len(parts) >= 3:
                path = parts[1]
                content = " ".join(parts[2:])
                result = await self.act("file_write", path=path, content=content)
            elif cmd == "list":
                path = parts[1] if len(parts) >= 2 else "."
                result = await self.act("file_list", path=path)
            else:
                result = ToolResult(success=False, content="", error=f"Invalid usage for {cmd}")
        
        elif cmd == "exec":
            code = " ".join(parts[1:]) if len(parts) > 1 else ""
            result = await self.act("python_exec", code=code)
        
        else:
            result = ToolResult(success=True, content=f"Simulated: Processed '{user_input}'")
        
        return ToolResult(
            success=True,
            content=result.content,
            metadata={"memory": self.memory, "steps": len(self.steps)}
        )
    
    def get_trace(self) -> list[dict[str, Any]]:
        """Get full ReAct trace."""
        return [
            {
                "step": i,
                "thought": step.thought,
                "observation": step.observation,
            }
            for i, step in enumerate(self.steps)
        ]