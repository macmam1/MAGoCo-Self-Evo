"""Web tools: search (no key) + fetch with limits. Uses httpx (already a dependency)."""

from __future__ import annotations

import re
from typing import Any

import httpx

from magoco_core.tools.registry import Tool, ToolResult, tool_registry

TAG_RE = re.compile(r"<[^>]+>")


def _html_to_text(html: str, limit: int = 8000) -> str:
    text = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S | re.I)
    text = TAG_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


class WebSearchTool(Tool):
    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Web search via DuckDuckGo (no API key). Returns titles+urls+snippets."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"query": {"type": "string"}, "count": {"type": "integer", "default": 5}},
            "required": ["query"],
        }

    async def execute(self, query: str, count: int = 5) -> ToolResult:
        try:
            async with httpx.AsyncClient(timeout=12, headers={"User-Agent": "MAGoCo/1.0"}) as c:
                r = await c.get("https://lite.duckduckgo.com/lite/", params={"q": query})
                r.raise_for_status()
                links = re.findall(r'<a rel="nofollow" href="([^"]+)">([^<]+)</a>', r.text)
                out = []
                for url, title in links[: max(1, min(count, 10))]:
                    out.append(f"- {title.strip()} — {url.strip()}")
                if not out:
                    return ToolResult(success=False, content="", error="no results")
                return ToolResult(success=True, content="\n".join(out), metadata={"count": len(out)})
        except Exception as e:
            return ToolResult(success=False, content="", error=f"search failed: {e}")


class WebFetchTool(Tool):
    @property
    def name(self) -> str:
        return "web_fetch"

    @property
    def description(self) -> str:
        return "Fetch a URL and return text (max ~100KB, 15s timeout)."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"url": {"type": "string"}, "max_chars": {"type": "integer", "default": 8000}},
            "required": ["url"],
        }

    async def execute(self, url: str, max_chars: int = 8000) -> ToolResult:
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True,
                                         headers={"User-Agent": "MAGoCo/1.0"}) as c:
                r = await c.get(url)
                r.raise_for_status()
                ctype = r.headers.get("content-type", "")
                if "text" not in ctype and "html" not in ctype and "json" not in ctype and "xml" not in ctype:
                    return ToolResult(success=False, content="", error=f"unsupported type: {ctype}")
                body = r.text[:100_000]
                text = _html_to_text(body, max_chars) if "<" in body[:500] else body[:max_chars]
                return ToolResult(success=True, content=text, metadata={"status": r.status_code})
        except Exception as e:
            return ToolResult(success=False, content="", error=f"fetch failed: {e}")


tool_registry.register(WebSearchTool())
tool_registry.register(WebFetchTool())
