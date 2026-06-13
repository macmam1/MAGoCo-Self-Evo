"""Built-in tools for agents."""
import datetime
import re
from typing import Any

from app.services.agents.tool import Tool, ToolParameter, ToolRegistry


class CalculatorTool(Tool):
    """Evaluate basic math expressions. SAFE: فقط اعداد و operators."""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Evaluate a basic math expression. Example: '2 + 2 * 3'. Supports +, -, *, /, **, parentheses."

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="expression",
                type="string",
                description="The math expression to evaluate",
                required=True,
            ),
        ]

    async def execute(self, **kwargs: Any) -> str:
        expression: str = kwargs.get("expression", "")
        # فقط اعداد، operators و پرانتز مجاز
        if not re.match(r"^[\d\s\+\-\*\/\.\(\)]+$", expression):
            return f"❌ Invalid expression: {expression}. Only numbers and basic operators allowed."
        try:
            # eval امن چون regex محدود شده
            result = eval(expression, {"__builtins__": {}}, {})  # noqa: S307
            return f"= {result}"
        except Exception as e:
            return f"❌ Error: {e}"


class CurrentTimeTool(Tool):
    """Get the current date/time."""

    @property
    def name(self) -> str:
        return "current_time"

    @property
    def description(self) -> str:
        return "Get the current date and time in ISO format. Optionally specify a timezone."

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="timezone",
                type="string",
                description="Timezone (e.g., 'UTC', 'Asia/Tehran'). Defaults to UTC.",
                required=False,
            ),
        ]

    async def execute(self, **kwargs: Any) -> str:
        tz = kwargs.get("timezone", "UTC")
        try:
            from zoneinfo import ZoneInfo
            now = datetime.datetime.now(ZoneInfo(tz))
        except Exception:
            now = datetime.datetime.utcnow()
        return now.isoformat()


class TextSummarizerTool(Tool):
    """Simple text summarizer (placeholder — uses word frequency)."""

    @property
    def name(self) -> str:
        return "text_summarizer"

    @property
    def description(self) -> str:
        return "Summarize a long text by extracting key sentences. Input: 'text' (the text), 'max_sentences' (optional, default 3)."

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="text",
                type="string",
                description="The text to summarize",
                required=True,
            ),
            ToolParameter(
                name="max_sentences",
                type="number",
                description="Max sentences in summary (default 3)",
                required=False,
            ),
        ]

    async def execute(self, **kwargs: Any) -> str:
        text: str = kwargs.get("text", "")
        max_sentences: int = int(kwargs.get("max_sentences", 3))

        if not text.strip():
            return "❌ Empty text"

        # Simple sentence splitter
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        if len(sentences) <= max_sentences:
            return text

        # Score sentences by word frequency
        words = re.findall(r"\w+", text.lower())
        freq: dict[str, int] = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1

        scored = []
        for i, s in enumerate(sentences):
            score = sum(freq.get(w.lower(), 0) for w in re.findall(r"\w+", s))
            scored.append((score, i, s))
        scored.sort(reverse=True)

        top = sorted(scored[:max_sentences], key=lambda x: x[1])
        return " ".join(s for _, _, s in top)


def register_builtin_tools() -> None:
    """ثبت همه ابزارهای داخلی."""
    ToolRegistry.register(CalculatorTool())
    ToolRegistry.register(CurrentTimeTool())
    ToolRegistry.register(TextSummarizerTool())
