"""File operation tools - read, write, list files."""

import os
import json
from pathlib import Path
from typing import Any
from magoco_core.tools.registry import Tool, ToolResult, tool_registry


class FileReadTool(Tool):
    @property
    def name(self) -> str:
        return "file_read"
    
    @property
    def description(self) -> str:
        return "Read contents of a file. Returns the file content as text."
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to read"},
                "offset": {"type": "integer", "description": "Line offset (0-indexed)", "default": 0},
                "limit": {"type": "integer", "description": "Max lines to read", "default": 200},
            },
            "required": ["path"],
        }
    
    async def execute(self, path: str, offset: int = 0, limit: int = 200) -> ToolResult:
        try:
            p = Path(path).resolve()
            if not p.exists():
                return ToolResult(success=False, content="", error=f"File not found: {path}")
            if not p.is_file():
                return ToolResult(success=False, content="", error=f"Path is not a file: {path}")
            
            content = p.read_text(encoding="utf-8")
            lines = content.splitlines()
            
            start = max(0, offset)
            end = min(len(lines), offset + limit)
            result_lines = lines[start:end]
            
            return ToolResult(
                success=True,
                content="\n".join(result_lines),
                metadata={"total_lines": len(lines), "offset": offset, "limit": limit}
            )
        except Exception as e:
            return ToolResult(success=False, content="", error=str(e))


class FileWriteTool(Tool):
    @property
    def name(self) -> str:
        return "file_write"
    
    @property
    def description(self) -> str:
        return "Write content to a file. Creates parent directories if needed."
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to write"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["path", "content"],
        }
    
    async def execute(self, path: str, content: str) -> ToolResult:
        try:
            p = Path(path).resolve()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return ToolResult(success=True, content=f"Written to {path}", metadata={"size": len(content)})
        except Exception as e:
            return ToolResult(success=False, content="", error=str(e))


class FileListTool(Tool):
    @property
    def name(self) -> str:
        return "file_list"
    
    @property
    def description(self) -> str:
        return "List files in a directory."
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path", "default": "."},
                "recursive": {"type": "boolean", "description": "List recursively", "default": False},
                "pattern": {"type": "string", "description": "Glob pattern", "default": "*"},
            },
            "required": [],
        }
    
    async def execute(self, path: str = ".", recursive: bool = False, pattern: str = "*") -> ToolResult:
        try:
            p = Path(path).resolve()
            if not p.exists():
                return ToolResult(success=False, content="", error=f"Path not found: {path}")
            if not p.is_dir():
                return ToolResult(success=False, content="", error=f"Path is not a directory: {path}")
            
            if recursive:
                files = list(p.rglob(pattern))
            else:
                files = list(p.glob(pattern))
            
            result = [str(f.relative_to(p)) for f in files if f.is_file()]
            return ToolResult(success=True, content="\n".join(result), metadata={"count": len(result)})
        except Exception as e:
            return ToolResult(success=False, content="", error=str(e))


# Register tools
tool_registry.register(FileReadTool())
tool_registry.register(FileWriteTool())
tool_registry.register(FileListTool())