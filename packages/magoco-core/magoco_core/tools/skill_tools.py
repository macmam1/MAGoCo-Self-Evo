"""Skill discovery tool — agents find skills mid-run (ToolSearchTool lesson)."""

from typing import Any

from magoco_core.tools.registry import Tool, ToolResult, tool_registry


class SkillSearchTool(Tool):
    @property
    def name(self) -> str:
        return "skill_search"

    @property
    def description(self) -> str:
        return ("Search the skill bank for the current task. "
                "Call BEFORE improvising multi-step work (testing, review, debugging, docs). "
                "Returns matching skills with ids; use skill id in your plan.")

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Task description to match skills against"},
                "top_k": {"type": "integer", "description": "Max results", "default": 5},
            },
            "required": ["query"],
        }

    async def execute(self, query: str, top_k: int = 5) -> ToolResult:
        try:
            from magoco_core.skills.detect import suggest_for_text
            suggestions = suggest_for_text(query, top_k=top_k)
            if not suggestions:
                return ToolResult(success=True, content="(no matching skills)",
                                  metadata={"count": 0})
            lines = [f"- {s.skill_id} [{s.category}] (score {s.score}): {s.display_name} — {s.reason}"
                     for s in suggestions]
            return ToolResult(success=True, content="\n".join(lines),
                              metadata={"count": len(suggestions),
                                        "ids": [s.skill_id for s in suggestions]})
        except Exception as e:
            return ToolResult(success=False, content="", error=str(e))


tool_registry.register(SkillSearchTool())
