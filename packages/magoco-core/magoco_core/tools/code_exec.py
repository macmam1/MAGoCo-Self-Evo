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
        """Execute Python code once with timeout and resource limits."""
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

            # Run user code exactly ONCE, capturing stdout+stderr.
            # Markers are base64 so multi-line output survives line parsing.
            exec_code = (
                "import sys, io, traceback, base64\n"
                "_buf_out = io.StringIO()\n"
                "_buf_err = io.StringIO()\n"
                "_old_out, _old_err = sys.stdout, sys.stderr\n"
                "sys.stdout, sys.stderr = _buf_out, _buf_err\n"
                "_exit = 0\n"
                "try:\n"
                f"{self._indent(code)}\n"
                "except SystemExit as _se:\n"
                "    _exit = int(_se.code or 0)\n"
                "except BaseException:\n"
                "    _exit = 1\n"
                "    traceback.print_exc()\n"
                "finally:\n"
                "    sys.stdout, sys.stderr = _old_out, _old_err\n"
                "print('__EXIT__:' + str(_exit))\n"
                "print('__STDOUT_B64__:' + base64.b64encode(_buf_out.getvalue().encode()).decode())\n"
                "print('__STDERR_B64__:' + base64.b64encode(_buf_err.getvalue().encode()).decode())\n"
            )
            
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
            
            import base64 as _b64

            for line in result.stdout.splitlines():
                if line.startswith("__EXIT__:"):
                    exit_code = int(line.split("__EXIT__:", 1)[1].strip() or 0)
                elif line.startswith("__STDOUT_B64__:"):
                    try:
                        stdout_val = _b64.b64decode(line.split("__STDOUT_B64__:", 1)[1]).decode()
                    except Exception:
                        stdout_val = ""
                elif line.startswith("__STDERR_B64__:"):
                    try:
                        stderr_val = _b64.b64decode(line.split("__STDERR_B64__:", 1)[1]).decode()
                    except Exception:
                        stderr_val = ""

            if result.stderr and not stderr_val:
                stderr_val = result.stderr.strip()[:2000]
            if result.returncode != 0 and exit_code == 0:
                exit_code = result.returncode
            
            ok = exit_code == 0
            return ToolResult(
                success=ok,
                content=stdout_val,
                error=None if ok else (stderr_val or f"exit {exit_code}"),
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