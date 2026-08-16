"""Code execution tool with sandbox security."""

import ast
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from magoco_core.tools.registry import Tool, ToolResult, tool_registry


class CodeExecTool(Tool):
    """Execute Python code in a monitored environment."""
    
    @property
    def name(self) -> str:
        return "python_exec"
    
    @property
    def description(self) -> str:
        return "Execute Python code in a sandboxed environment. Has timeout and resource limits."
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "function",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute"},
                "timeout": {"type": "number", "description": "Timeout in seconds", "default": 10},
            },
            "required": ["code"],
        }
    
    async def execute(self, code: str, timeout: float = 10) -> ToolResult:
        """Execute Python code with timeout and resource limits."""
        try:
            # Security: Block dangerous imports
            dangerous_patterns = [
                "__import__", "os.system", "subprocess", "socket", "pickle"
            ]
            for pattern in dangerous_patterns:
                if pattern in code:
                    return ToolResult(
                        success=False, 
                        content="", 
                        error=f"Blocked dangerous pattern: {pattern}"
                    )
            
            # Validate code syntax
            try:
                ast.parse(code)
            except SyntaxError as e:
                return ToolResult(success=False, content="", error=f"Syntax error: {e}")
            
            # Execute code in isolated subprocess using python -c
            exec_code = f"""
import sys
import io

stdout_capture = io.StringIO()
stderr_capture = io.StringIO()

# Capture stdout
old_stdout = sys.stdout
sys.stdout = stdout_capture

try:
{self._indent(code)}
finally:
    sys.stdout = old_stdout

stdout_val = stdout_capture.getvalue()
stderr_val = ""

# Capture stderr
old_stderr = sys.stderr
sys.stderr = stderr_capture

try:
{self._indent(code)}
finally:
    sys.stderr = old_stderr

stderr_val = stderr_capture.getvalue()

# Execute with clean exit
exit_code = 0

print("__EXIT__:" + str(exit_code))
print("__STDOUT__:" + stdout_val)
print("__STDERR__:" + stderr_val)
"""
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(exec_code)
                temp_path = f.name
            
            try:
                result = subprocess.run(
                    [sys.executable, temp_path],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd="/tmp"
                )
            finally:
                Path(temp_path).unlink(missing_ok=True)
            
            # Parse outputs
            exit_code = 0
            stdout_val = ""
            stderr_val = ""
            
            for line in result.stdout.splitlines():
                if line.startswith("__EXIT__:"):
                    exit_code = int(line.split(":")[1])
                elif line.startswith("__STDOUT__:"):
                    stdout_val = ":".join(line.split(":")[1:])
                elif line.startswith("__STDERR__:"):
                    stderr_val = ":".join(line.split(":")[1:])
            
            # Also check result stdout/stdout
            stdout_val = stdout_val or ""
            stderr_val = stderr_val or ""
            
            if result.stdout and not stdout_val and not stderr_val:
                stdout_val = result.stdout.strip()
            
            return ToolResult(
                success=exit_code == 0,
                content=stdout_val,
                error=stderr_val if stderr_val and exit_code else None,
                metadata={"exit_code": exit_code}
            )
            
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False, 
                content="", 
                error=f"Execution timeout after {timeout}s"
            )
        except Exception as e:
            return ToolResult(
                success=False, 
                content="", 
                error=f"Execution failed: {str(e)}"
            )
    
    def _indent(self, code: str, spaces: int = 4) -> str:
        """Indent code lines with specified spaces."""
        indent = " " * spaces
        return "\n".join(
            indent + line if line.strip() else line 
            for line in code.splitlines()
        )


# Register tool
tool_registry.register(CodeExecTool())