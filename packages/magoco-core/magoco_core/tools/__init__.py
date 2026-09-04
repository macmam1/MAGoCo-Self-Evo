"""Magoco Core Tools package.

Importing this package auto-registers all built-in tools.
"""

from magoco_core.tools.registry import tool_registry, Tool, ToolResult
from magoco_core.tools.file_tools import FileReadTool, FileWriteTool, FileListTool
from magoco_core.tools.code_exec import CodeExecTool
from magoco_core.tools.bash_tool import BashExecTool
from magoco_core.tools.web_tool import WebSearchTool, WebFetchTool

# Auto-register all tools on import
__all__ = [
    "tool_registry",
    "Tool",
    "ToolResult",
    "FileReadTool",
    "FileWriteTool",
    "FileListTool",
    "CodeExecTool",
    "BashExecTool",
    "WebSearchTool",
    "WebFetchTool",
]
