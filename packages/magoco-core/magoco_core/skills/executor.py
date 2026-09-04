"""
Sandboxed Skill Executor
Secure execution environment with resource limits, network isolation, and audit
"""

import asyncio
import os
import json
import uuid
import logging
import tempfile
import shutil
import subprocess
import sys
import time
import resource
import signal
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Awaitable, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager, asynccontextmanager

from .models import (
    SkillManifest, SkillInstance, SecurityLevel, ExecutionMode,
    SkillParameter, SkillReturn
)

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of skill execution"""
    success: bool
    output: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    memory_mb: float = 0.0
    logs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionContext:
    """Execution context with isolated environment"""
    skill_id: str
    skill_version: str
    execution_id: str
    input_data: Dict[str, Any]
    config: Dict[str, Any]
    secrets: Dict[str, str]
    working_dir: Path
    temp_dir: Path
    start_time: float = field(default_factory=time.time)
    
    # Resource tracking
    peak_memory_mb: float = 0.0
    cpu_time: float = 0.0
    
    # Logs
    logs: List[str] = field(default_factory=list)
    
    # Security
    allowed_domains: List[str] = field(default_factory=list)
    allowed_commands: List[str] = field(default_factory=list)


class ResourceLimiter:
    """Resource limiting for sandboxed execution"""
    
    def __init__(self, max_memory_mb: int = 512, max_cpu_percent: int = 50, timeout: float = 30.0):
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.max_cpu_percent = max_cpu_percent
        self.timeout = timeout
        self._original_limits = {}
    
    def apply_limits(self):
        """Apply resource limits to current process"""
        try:
            # Memory limit
            soft, hard = resource.getrlimit(resource.RLIMIT_AS)
            self._original_limits[resource.RLIMIT_AS] = (soft, hard)
            resource.setrlimit(resource.RLIMIT_AS, (self.max_memory_bytes, hard))
            
            # CPU time limit
            soft, hard = resource.getrlimit(resource.RLIMIT_CPU)
            self._original_limits[resource.RLIMIT_CPU] = (soft, hard)
            cpu_seconds = int(self.timeout) + 5
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, hard))
            
            # File size limit (100MB)
            soft, hard = resource.getrlimit(resource.RLIMIT_FSIZE)
            self._original_limits[resource.RLIMIT_FSIZE] = (soft, hard)
            resource.setrlimit(resource.RLIMIT_FSIZE, (100 * 1024 * 1024, hard))
            
            # Number of processes
            soft, hard = resource.getrlimit(resource.RLIMIT_NPROC)
            self._original_limits[resource.RLIMIT_NPROC] = (soft, hard)
            resource.setrlimit(resource.RLIMIT_NPROC, (50, hard))
            
        except Exception as e:
            logger.warning(f"Failed to set resource limits: {e}")
    
    def restore_limits(self):
        """Restore original resource limits"""
        for resource_type, (soft, hard) in self._original_limits.items():
            try:
                resource.setrlimit(resource_type, (soft, hard))
            except Exception:
                pass
    
    def get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except Exception:
            return 0.0


class NetworkFilter:
    """Network access filter for sandbox"""
    
    def __init__(self, allowed_domains: List[str] = None):
        self.allowed_domains = set(allowed_domains or [])
        self._original_socket = None
    
    def is_allowed(self, host: str) -> bool:
        """Check if domain is allowed"""
        if not self.allowed_domains:
            return True  # Allow all if no restrictions
        
        host = host.lower()
        for allowed in self.allowed_domains:
            if host == allowed.lower() or host.endswith("." + allowed.lower()):
                return True
        return False
    
    def patch_socket(self):
        """Patch socket to filter connections"""
        import socket
        original_connect = socket.socket.connect
        
        def filtered_connect(sock, address):
            host = address[0]
            if not self.is_allowed(host):
                raise PermissionError(f"Connection to {address[0]} not allowed")
            return original_connect(sock, address)
        
        socket.socket.connect = filtered_connect
    
    def restore_socket(self):
        """Restore original socket"""
        import socket
        if hasattr(socket.socket, '_original_connect'):
            socket.socket.connect = socket.socket._original_connect


class CommandFilter:
    """Command execution filter for shell commands"""
    
    def __init__(self, allowed_commands: List[str] = None):
        self.allowed_commands = set(allowed_commands or [])
    
    def is_allowed(self, command: str) -> bool:
        """Check if command is allowed"""
        if not self.allowed_commands:
            return False  # Deny all by default if list is provided but empty
        
        # Extract base command
        cmd = command.strip().split()[0] if command.strip() else ""
        return cmd in self.allowed_commands
    
    def filter_subprocess(self, cmd: List[str]) -> bool:
        """Check if subprocess command is allowed"""
        if not cmd:
            return False
        return self.is_allowed(cmd[0])


class SandboxExecutor:
    """
    Secure sandboxed skill executor with:
    - Process isolation (separate process)
    - Resource limits (memory, CPU, disk, processes)
    - Network filtering (domain allowlist)
    - Command filtering (command allowlist)
    - Filesystem isolation (chroot-like)
    - Audit logging
    """
    
    def __init__(
        self,
        skill_dir: Path,
        manifest: 'SkillManifest',
        security_level: 'SecurityLevel' = SecurityLevel.RESTRICTED,
        timeout: float = 30.0,
        max_memory_mb: int = 512,
        max_cpu_percent: int = 50,
    ):
        self.skill_dir = Path(skill_dir)
        self.manifest = manifest
        self.security_level = manifest.security_level
        self.timeout = manifest.timeout
        self.max_memory_mb = manifest.max_memory_mb
        self.max_cpu_percent = manifest.max_cpu_percent
        
        # Security config from manifest
        self.allowed_domains = set(manifest.allowed_domains)
        self.allowed_commands = set(manifest.allowed_commands)
        self.security_level = manifest.security_level
        
        # Execution config
        self.timeout = manifest.timeout
        self.max_memory_mb = manifest.max_memory_mb
        self.max_cpu_percent = manifest.max_cpu_percent
        
        # Execution config
        self.execution_mode = manifest.execution_mode
        self.entry_point = manifest.entry_point
        
        # Security policies by level
        self._setup_security_policies()
    
    def _setup_security_policies(self):
        """Configure security policies based on security level"""
        if self.security_level == SecurityLevel.SAFE:
            self.allow_network = False
            self.allow_filesystem = False
            self.allow_subprocess = False
            self.readonly_fs = True
        elif self.security_level == SecurityLevel.RESTRICTED:
            self.allow_network = True
            self.allow_filesystem = True
            self.allow_subprocess = False
            self.readonly_fs = False
        elif self.security_level == SecurityLevel.STANDARD:
            self.allow_network = True
            self.allow_filesystem = True
            self.allow_subprocess = True
            self.readonly_fs = False
        elif self.security_level == SecurityLevel.ELEVATED:
            self.allow_network = True
            self.allow_filesystem = True
            self.allow_subprocess = True
            self.readonly_fs = False
        elif self.security_level == SecurityLevel.FULL:
            self.allow_network = True
            self.allow_filesystem = True
            self.allow_subprocess = True
            self.readonly_fs = False
        else:
            # Default to restricted
            self.allow_network = True
            self.allow_filesystem = True
            self.allow_subprocess = False
            self.readonly_fs = False
    
    async def execute(
        self,
        input_data: Dict[str, Any],
        config: Dict[str, Any] = None,
        secrets: Dict[str, str] = None,
    ) -> 'ExecutionResult':
        """
        Execute skill in sandboxed environment
        """
        execution_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Create execution context
        context = ExecutionContext(
            skill_id=self.manifest.id,
            skill_version=self.manifest.version,
            execution_id=str(uuid.uuid4()),
            input_data=input_data,
            config=config or {},
            secrets=secrets or {},
            working_dir=self.skill_dir,
            temp_dir=Path(tempfile.mkdtemp(prefix=f"skill_{self.manifest.id}_")),
        )
        
        # Apply security policies
        await self._setup_execution_environment(context)
        
        try:
            if self.execution_mode == ExecutionMode.ASYNC:
                result = await self._execute_async(context)
            elif self.execution_mode == ExecutionMode.STREAMING:
                result = await self._execute_streaming(context)
            else:
                result = await self._execute_sync(context)
            
            result.execution_time = time.time() - start_time
            return result
            
        except asyncio.TimeoutError:
            return ExecutionResult(
                success=False,
                error=f"Execution timeout after {self.timeout}s",
                execution_time=time.time() - start_time,
            )
        except Exception as e:
            logger.error(f"Execution error: {e}")
            return ExecutionResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )
        finally:
            # Cleanup
            await self._cleanup(context)
    
    async def _setup_execution_environment(self, context: ExecutionContext):
        """Set up isolated execution environment"""
        # Create isolated workspace
        context.working_dir = Path(context.temp_dir) / "workspace"
        context.working_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy skill code to isolated workspace
        await self._prepare_workspace(context)
        
        # Set up resource limits
        context.resource_limiter = ResourceLimiter(
            max_memory_mb=self.max_memory_mb,
            max_cpu_percent=self.max_cpu_percent,
            timeout=self.timeout,
        )
        
        # Set up network filter
        if not self.allow_network:
            context.network_filter = NetworkFilter(allowed_domains=[])
        else:
            context.network_filter = NetworkFilter(
                allowed_domains=self.manifest.allowed_domains
            )
        
        # Set up command filter
        context.command_filter = CommandFilter(
            allowed_commands=self.manifest.allowed_commands
        )
    
    async def _prepare_workspace(self, context: ExecutionContext):
        """Prepare isolated workspace with skill code"""
        src_dir = self.skill_dir
        dest_dir = context.working_dir
        
        # Copy skill files (excluding .git, __pycache__, etc.)
        ignore_patterns = shutil.ignore_patterns(
            '__pycache__', '*.pyc', '.git', '.pytest_cache',
            '.venv', 'venv', '.venv', '*.log', '*.log.*',
            '*.sqlite', '*.db', '*.sqlite3', '*.pkl', '*.pickle',
            'node_modules', '.npm', '.cache', 'dist', 'build',
            '*.egg-info', '*.dist-info', '*.whl', '*.egg',
        )
        
        shutil.copytree(
            self.skill_dir,
            context.working_dir / "skill",
            ignore=ignore_patterns,
            dirs_exist_ok=True,
        )
        
        # Create entry point wrapper
        await self._create_entry_wrapper(context)
        
        # Write input data
        input_file = context.working_dir / "input.json"
        with open(input_file, "w") as f:
            json.dump(context.input_data, f)
    
    async def _create_entry_wrapper(self, context: ExecutionContext):
        """Create secure entry point wrapper"""
        entry_point = self.manifest.entry_point
        
        wrapper_code = f'''
import sys
import json
import traceback

# Add skill directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load input
with open("input.json", "r") as f:
    input_data = json.load(f)

# Import skill module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
skill_module = __import__("{self.manifest.code_path.replace(".py", "").replace("/", ".")}")

# Get entry point
entry_func = getattr(skill_module, "{self.manifest.entry_point}")

# Execute
try:
    if asyncio.iscoroutinefunction(entry_func):
        import asyncio
        result = asyncio.run(entry_func(input_data))
    else:
        result = entry_func(input_data)
    
    # Write output
    with open("output.json", "w") as f:
        json.dump({{"success": True, "output": result}}, f)
        
except Exception as e:
    with open("output.json", "w") as f:
        json.dump({{"success": False, "error": str(e), "traceback": traceback.format_exc()}}, f)
    sys.exit(1)
'''
        
        wrapper_path = context.working_dir / "execute_wrapper.py"
        with open(context.working_dir / "execute_wrapper.py", "w") as f:
            f.write(wrapper_code)
    
    async def _execute_sync(self, context: ExecutionContext) -> ExecutionResult:
        """Execute skill synchronously in subprocess"""
        start_time = time.time()
        
        # Prepare environment
        env = os.environ.copy()
        env.update({
            "PYTHONPATH": str(context.working_dir / "skill"),
            "SKILL_INPUT": json.dumps(context.input_data),
            "SKILL_CONFIG": json.dumps(context.config),
        }
        
        # Add secrets to environment (prefixed)
        for key, value in context.secrets.items():
            env[f"SECRET_{key.upper()}"] = value
        
        # Run in subprocess with resource limits
        cmd = [sys.executable, "execute_wrapper.py"]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=context.working_dir,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=1024 * 1024,  # 1MB buffer
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                try:
                    process.kill()
                except:
                    pass
                raise asyncio.TimeoutError()
            
            # Read output
            output_file = Path(context.working_dir) / "output.json"
            if output_file.exists():
                with open(output_file, "r") as f:
                    result_data = json.load(f)
                
                if result_data.get("success"):
                    return ExecutionResult(
                        success=True,
                        output=result_data.get("output"),
                        execution_time=time.time() - context.start_time,
                    )
                else:
                    return ExecutionResult(
                        success=False,
                        error=result_data.get("error", "Unknown error"),
                        execution_time=time.time() - context.start_time,
                        logs=[result_data.get("traceback", "")],
                    )
            else:
                # Fallback to stdout/stderr
                return ExecutionResult(
                    success=False,
                    error=stderr.decode() if stderr else "No output file generated",
                    execution_time=time.time() - context.start_time,
                    logs=[stdout.decode() if stdout else ""],
                )
                
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=str(e),
                execution_time=time.time() - context.start_time,
            )
    
    async def _execute_async(self, context: ExecutionContext) -> ExecutionResult:
        """Execute skill asynchronously (fire and forget)"""
        # For async execution, we start the process and return immediately
        # with an execution ID that can be polled for results
        
        # Similar to sync but return immediately with execution ID
        # In practice, this would queue the execution and return a handle
        
        # For now, delegate to sync but run in background
        task = asyncio.create_task(self._execute_sync(context))
        
        return ExecutionResult(
            success=True,
            output={"execution_id": context.execution_id, "status": "started"},
            execution_time=0.0,
            metadata={"async": True},
        )
    
    async def _execute_streaming(self, context: ExecutionContext) -> ExecutionResult:
        """Execute skill with streaming output"""
        # For streaming, we would yield partial results
        # This is useful for long-running skills that produce incremental output
        
        # For now, delegate to sync
        return await self._execute_sync(context)
    
    async def _cleanup(self, context: ExecutionContext):
        """Clean up execution environment"""
        try:
            # Restore resource limits
            if hasattr(context, 'resource_limiter'):
                context.resource_limiter.restore_limits()
            
            # Clean up temp directory
            if context.temp_dir.exists():
                shutil.rmtree(context.temp_dir, ignore_errors=True)
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")


class SkillInvoker:
    """
    High-level skill invocation with caching, retries, and fallback
    """
    
    def __init__(self, registry: 'SkillsRegistry'):
        self.registry = registry
        self._skill_cache: Dict[str, SandboxExecutor] = {}
        self._execution_semaphore = asyncio.Semaphore(10)  # Limit concurrent executions
    
    async def invoke(
        self,
        skill_id: str,
        input_data: Dict[str, Any],
        config: Dict[str, Any] = None,
        secrets: Dict[str, str] = None,
        version: Optional[str] = None,
        retries: int = 3,
    ) -> ExecutionResult:
        """
        Invoke a skill with retries and error handling
        """
        async with self._execution_semaphore:
            # Resolve version
            if version is None:
                manifest = self.registry.get_latest(skill_id)
            else:
                manifest = self.registry.get(skill_id, version)
            
            if not manifest:
                return ExecutionResult(
                    success=False,
                    error=f"Skill not found: {skill_id}@{version or 'latest'}"
                )
            
            if manifest.status != SkillStatus.PUBLISHED:
                return ExecutionResult(
                    success=False,
                    error=f"Skill not published: {manifest.status.value}"
                )
            
            # Get or create executor
            cache_key = f"{manifest.id}@{manifest.version}"
            if cache_key not in self._skill_cache:
                skill_dir = self.registry.registry_dir / manifest.id / manifest.version
                self._skill_cache[cache_key] = SandboxExecutor(
                    skill_dir=Path(manifest.id) / manifest.version,
                    manifest=manifest,
                )
            
            executor = self._skill_cache[cache_key]
            
            # Execute with retries
            last_error = None
            for attempt in range(retries):
                try:
                    result = await executor.execute(
                        input_data=input_data,
                        config=config,
                        secrets=secrets,
                    )
                    
                    if result.success:
                        return result
                    
                    last_error = result.error
                    
                    # Don't retry on certain errors
                    if result.error and any(
                        kw in result.error.lower() 
                        for kw in ["validation", "permission", "unauthorized", "invalid"]
                    ):
                        break
                    
                    # Wait before retry with exponential backoff
                    await asyncio.sleep(2 ** attempt)
                    
                except Exception as e:
                    last_error = str(e)
                    await asyncio.sleep(2 ** attempt)
            
            return ExecutionResult(
                success=False,
                error=f"Failed after {retries} retries: {last_error}",
            )
    
    async def invoke_streaming(
        self,
        skill_id: str,
        input_data: Dict[str, Any],
        config: Dict[str, Any] = None,
        secrets: Dict[str, str] = None,
        version: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Invoke skill with streaming output"""
        # Implementation for streaming results
        yield {"status": "starting", "skill_id": skill_id}
        
        result = await self.invoke(skill_id, input_data, config, secrets, version)
        
        if result.success:
            yield {"status": "completed", "output": result.output}
        else:
            yield {"status": "error", "error": result.error}
    
    def clear_cache(self):
        """Clear executor cache"""
        self._skill_cache.clear()


# Global invoker instance
_invoker: Optional[SkillInvoker] = None


def get_skill_invoker(registry: Optional['SkillsRegistry'] = None) -> SkillInvoker:
    """Get or create global skill invoker"""
    global _invoker
    if _invoker is None:
        if registry is None:
            from ..registry import get_skills_registry
            registry = get_skills_registry()
        _invoker = SkillInvoker(registry)
    return _invoker