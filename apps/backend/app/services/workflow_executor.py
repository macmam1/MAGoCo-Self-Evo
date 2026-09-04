"""
Workflow Execution Engine
Executes DAG workflows with support for:
- Sequential/parallel execution
- Conditional branching
- Sub-workflow calls
- Retry logic with exponential backoff
- Timeout handling
- State persistence
"""

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class NodeResult:
    node_id: str
    status: NodeStatus
    output: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retries: int = 0


@dataclass
class WorkflowExecution:
    id: str
    workflow_id: str
    workflow_name: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    nodes: Dict[str, NodeResult] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    current_node: Optional[str] = None


class WorkflowExecutor:
    """
    DAG Workflow Executor with support for:
    - Sequential execution (default)
    - Parallel execution (parallel nodes)
    - Conditional branching (condition nodes)
    - Sub-workflow calls
    - Retry with exponential backoff
    - Timeout per node
    """
    
    def __init__(
        self,
        default_timeout: float = 300.0,
        max_retries: int = 3,
        base_retry_delay: float = 1.0,
        max_retry_delay: float = 60.0,
    ):
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.base_retry_delay = base_retry_delay
        self.max_retry_delay = max_retry_delay
        
        # Node handlers registry
        self._node_handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[Any]]] = {}
        
        # Built-in node handlers
        self._register_builtin_handlers()
    
    def _register_builtin_handlers(self):
        """Register built-in node type handlers"""
        self._node_handlers.update({
            "task": self._execute_task_node,
            "condition": self._execute_condition_node,
            "parallel": self._execute_parallel_node,
            "subworkflow": self._execute_subworkflow_node,
            "start": self._execute_start_node,
            "end": self._execute_end_node,
        })
    
    def register_handler(self, node_type: str, handler: Callable[[Dict[str, Any]], Awaitable[Any]]):
        """Register a custom node handler"""
        self._node_handlers[node_type] = handler
    
    async def execute(
        self,
        workflow: Dict[str, Any],
        input_data: Dict[str, Any] = None,
        execution_id: Optional[str] = None,
    ) -> WorkflowExecution:
        """
        Execute a workflow DAG
        
        Args:
            workflow: Workflow definition with nodes and edges
            input_data: Initial input data
            execution_id: Optional execution ID
            
        Returns:
            WorkflowExecution with results
        """
        execution = WorkflowExecution(
            id=execution_id or str(uuid.uuid4()),
            workflow_id=workflow.get("id", "unknown"),
            workflow_name=workflow.get("name", "Untitled"),
            input_data=input_data or {},
            started_at=datetime.utcnow(),
        )
        
        # Build adjacency list
        nodes = {n["id"]: n for n in workflow.get("nodes", [])}
        edges = workflow.get("edges", [])
        
        # Build adjacency for forward traversal
        adjacency: Dict[str, List[str]] = defaultdict(list)
        reverse_adjacency: Dict[str, List[str]] = defaultdict(list)
        edge_map: Dict[str, Dict] = {}
        
        for edge in edges:
            source = edge["source"]
            target = edge["target"]
            adjacency[source].append(target)
            reverse_adjacency[target].append(source)
            edge_map[f"{source}->{target}"] = edge
        
        # Find start nodes (no incoming edges)
        start_nodes = [nid for nid in nodes if not reverse_adjacency[nid]]
        if not start_nodes:
            # If no explicit start, use nodes with type "start"
            start_nodes = [nid for nid, n in nodes.items() if n.get("type") == "start"]
        
        if not start_nodes:
            # Fallback: first node
            start_nodes = [list(nodes.keys())[0]] if nodes else []
        
        logger.info(f"Starting workflow execution {execution.id} with {len(nodes)} nodes")
        
        try:
            execution.status = WorkflowStatus.RUNNING
            
            # Execute using topological order with parallel support
            await self._execute_dag(
                execution, nodes, adjacency, reverse_adjacency, edge_map, start_nodes
            )
            
            # Collect outputs from end nodes
            end_nodes = [nid for nid, n in nodes.items() if n.get("type") == "end"]
            if not end_nodes:
                end_nodes = [nid for nid in nodes if not adjacency[nid]]
            
            for end_id in end_nodes:
                if end_id in execution.nodes:
                    result = execution.nodes[end_id]
                    if result.status == NodeStatus.COMPLETED:
                        execution.output_data[end_id] = result.output
            
            execution.status = WorkflowStatus.COMPLETED
            logger.info(f"Workflow {execution.id} completed successfully")
            
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error = str(e)
            logger.error(f"Workflow {execution.id} failed: {e}")
        
        finally:
            execution.completed_at = datetime.utcnow()
        
        return execution
    
    async def _execute_dag(
        self,
        execution: WorkflowExecution,
        nodes: Dict[str, Dict],
        adjacency: Dict[str, List[str]],
        reverse_adjacency: Dict[str, List[str]],
        edge_map: Dict[str, Dict],
        ready_nodes: List[str],
    ):
        """Execute DAG with support for parallel and conditional nodes"""
        
        completed = set()
        running = set()
        
        while ready_nodes:
            # Find nodes that can run (all dependencies completed)
            runnable = []
            for node_id in ready_nodes:
                if node_id in completed or node_id in running:
                    continue
                
                deps = reverse_adjacency.get(node_id, [])
                if all(dep in completed for dep in deps):
                    runnable.append(node_id)
            
            if not runnable:
                # Check if any running
                if running:
                    await asyncio.sleep(0.1)
                    continue
                else:
                    # Deadlock or circular dependency
                    remaining = set(ready_nodes) - completed - running
                    for nid in remaining:
                        execution.nodes[nid] = NodeResult(
                            node_id=nid,
                            status=NodeStatus.FAILED,
                            error="Circular dependency or deadlock detected"
                        )
                    break
            
            # Execute runnable nodes in parallel
            tasks = []
            for node_id in runnable:
                running.add(node_id)
                task = asyncio.create_task(
                    self._execute_node(execution, nodes, adjacency, reverse_adjacency, edge_map, node_id)
                )
                tasks.append((node_id, task))
            
            # Wait for all running tasks
            for node_id, task in tasks:
                try:
                    result = await task
                    execution.nodes[node_id] = result
                    completed.add(node_id)
                    running.discard(node_id)
                    
                    # Add downstream nodes to ready if all their deps are done
                    for next_id in adjacency.get(node_id, []):
                        if next_id not in ready_nodes:
                            deps = reverse_adjacency.get(next_id, [])
                            if all(dep in completed for dep in deps):
                                ready_nodes.append(next_id)
                                
                except Exception as e:
                    logger.error(f"Node {node_id} failed: {e}")
                    execution.nodes[node_id] = NodeResult(
                        node_id=node_id,
                        status=NodeStatus.FAILED,
                        error=str(e)
                    )
                    running.discard(node_id)
                    completed.add(node_id)
            
            # Check for early termination on failure
            failed_nodes = [nid for nid, r in execution.nodes.items() if r.status == NodeStatus.FAILED]
            if failed_nodes:
                # Check if any condition node failed - might be handled by condition logic
                for fid in failed_nodes:
                    node = nodes.get(fid)
                    if node and node.get("type") != "condition":
                        # Propagate failure to dependents
                        self._propagate_failure(execution, nodes, adjacency, fid, completed)
        
        # Check for incomplete nodes
        for node_id in nodes:
            if node_id not in completed:
                if node_id not in execution.nodes:
                    execution.nodes[node_id] = NodeResult(
                        node_id=node_id,
                        status=NodeStatus.SKIPPED,
                        error="Not reached"
                    )
    
    def _propagate_failure(
        self,
        execution: WorkflowExecution,
        nodes: Dict[str, Dict],
        adjacency: Dict[str, List[str]],
        failed_id: str,
        completed: set,
    ):
        """Propagate failure to dependent nodes"""
        queue = [failed_id]
        visited = set()
        
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            
            for next_id in adjacency.get(current, []):
                if next_id not in completed:
                    if next_id not in execution.nodes:
                        execution.nodes[next_id] = NodeResult(
                            node_id=next_id,
                            status=NodeStatus.SKIPPED,
                            error=f"Upstream node {failed_id} failed"
                        )
                    queue.append(next_id)
    
    async def _execute_node(
        self,
        execution: WorkflowExecution,
        nodes: Dict[str, Dict],
        adjacency: Dict[str, List[str]],
        reverse_adjacency: Dict[str, List[str]],
        edge_map: Dict[str, Dict],
        node_id: str,
    ) -> NodeResult:
        """Execute a single node"""
        node = nodes[node_id]
        node_type = node.get("type", "task")
        
        result = NodeResult(
            node_id=node_id,
            status=NodeStatus.RUNNING,
            started_at=datetime.utcnow(),
        )
        
        execution.current_node = node_id
        logger.info(f"Executing node {node_id} ({node.get('type')})")
        
        # Get input data from upstream nodes
        input_data = self._gather_inputs(execution, nodes, reverse_adjacency, node_id)
        
        # Merge with node config
        node_config = node.get("data", {}).get("config", {})
        merged_input = {**input_data, **node_config}
        
        retries = 0
        last_error = None
        
        while retries <= self.max_retries:
            try:
                handler = self._node_handlers.get(node.get("type", "task"))
                if not handler:
                    raise ValueError(f"No handler for node type: {node.get('type')}")
                
                output = await asyncio.wait_for(
                    handler(merged_input),
                    timeout=node.get("data", {}).get("config", {}).get("timeout", self.default_timeout)
                )
                
                return NodeResult(
                    node_id=node_id,
                    status=NodeStatus.COMPLETED,
                    output=output,
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow(),
                    retries=retries,
                )
                
            except asyncio.TimeoutError:
                last_error = f"Timeout after {self.default_timeout}s"
                logger.warning(f"Node {node_id} timeout (attempt {retries + 1})")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Node {node_id} error (attempt {retries + 1}): {e}")
            
            retries += 1
            if retries <= self.max_retries:
                delay = min(self.base_retry_delay * (2 ** (retries - 1)), self.max_retry_delay)
                await asyncio.sleep(delay)
        
        # All retries exhausted
        return NodeResult(
            node_id=node_id,
            status=NodeStatus.FAILED,
            error=last_error or "Max retries exceeded",
            retries=retries,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
    
    def _gather_inputs(
        self,
        execution: WorkflowExecution,
        nodes: Dict[str, Dict],
        reverse_adjacency: Dict[str, List[str]],
        node_id: str,
    ) -> Dict[str, Any]:
        """Gather input data from upstream nodes"""
        inputs = {}
        
        for dep_id in reverse_adjacency.get(node_id, []):
            if dep_id in execution.nodes:
                dep_result = execution.nodes[dep_id]
                if dep_result.status == NodeStatus.COMPLETED and dep_result.output is not None:
                    # Use node ID as key
                    inputs[dep_id] = dep_result.output
        
        return inputs
    
    # Built-in node handlers
    
    async def _execute_task_node(self, input_data: Dict[str, Any]) -> Any:
        """Execute a task node - runs configured action"""
        action = input_data.get("action", "echo")
        params = input_data.get("params", {})
        
        if action == "echo":
            return params.get("message", "Task executed")
        elif action == "python":
            # Execute Python code (sandboxed)
            code = params.get("code", "")
            # In production, use sandboxed executor
            return {"result": f"Executed: {code[:50]}..."}
        elif action == "http":
            # HTTP request
            return {"status": "ok", "url": params.get("url")}
        else:
            return {"action": action, "params": params}
    
    async def _execute_condition_node(self, input_data: Dict[str, Any]) -> Any:
        """Execute a condition node - evaluates expression"""
        condition = input_data.get("condition", "true")
        true_path = input_data.get("true_path", [])
        false_path = input_data.get("false_path", [])
        
        # Simple condition evaluation (in production, use safe eval)
        try:
            # Very basic condition evaluation - replace with safe evaluator
            result = eval(condition, {"__builtins__": {}}, input_data.get("context", {}))
        except Exception:
            result = False
        
        return {
            "condition_result": bool(result),
            "path": true_path if result else false_path,
        }
    
    async def _execute_parallel_node(self, input_data: Dict[str, Any]) -> Any:
        """Execute parallel node - returns branch outputs"""
        branches = input_data.get("branches", [])
        results = {}
        
        for i, branch in enumerate(branches):
            branch_input = input_data.get("branch_inputs", {}).get(str(i), {})
            # In real implementation, execute sub-workflow
            results[f"branch_{i}"] = {"status": "completed", "output": branch_input}
        
        return {"branches": results}
    
    async def _execute_subworkflow_node(self, input_data: Dict[str, Any]) -> Any:
        """Execute a sub-workflow"""
        workflow_id = input_data.get("workflow_id")
        sub_input = input_data.get("input", {})
        
        # In production, load and execute sub-workflow
        return {"subworkflow": workflow_id, "status": "completed"}
    
    async def _execute_start_node(self, input_data: Dict[str, Any]) -> Any:
        """Start node - passes through input"""
        return input_data
    
    async def _execute_end_node(self, input_data: Dict[str, Any]) -> Any:
        """End node - collects final output"""
        return input_data


# Workflow templates
WORKFLOW_TEMPLATES = [
    {
        "id": "agent-chain",
        "name": "Agent Chain",
        "description": "Sequential agent pipeline with coordination",
        "category": "agent",
        "workflow": {
            "nodes": [
                {"id": "start", "type": "start", "position": {"x": 400, "y": 50}, "data": {"label": "Start"}},
                {"id": "coordinator", "type": "task", "position": {"x": 400, "y": 150}, "data": {"label": "Coordinator Agent", "config": {"action": "coordinate", "params": {}}}},
                {"id": "worker1", "type": "task", "position": {"x": 200, "y": 250}, "data": {"label": "Worker 1", "config": {"action": "process", "params": {}}}},
                {"id": "worker2", "type": "task", "position": {"x": 600, "y": 250}, "data": {"label": "Worker 2", "config": {"action": "process", "params": {}}}},
                {"id": "merge", "type": "parallel", "position": {"x": 400, "y": 350}, "data": {"label": "Merge Results", "config": {}}},
                {"id": "end", "type": "end", "position": {"x": 400, "y": 450}, "data": {"label": "End"}},
            ],
            "edges": [
                {"id": "e1", "source": "start", "target": "coordinator"},
                {"id": "e2", "source": "coordinator", "target": "worker1"},
                {"id": "e3", "source": "coordinator", "target": "worker2"},
                {"id": "e4", "source": "worker1", "target": "merge"},
                {"id": "e5", "source": "worker2", "target": "merge"},
                {"id": "e6", "source": "merge", "target": "end"},
            ],
        },
    },
    {
        "id": "conditional-flow",
        "name": "Conditional Flow",
        "description": "Branch based on condition evaluation",
        "category": "logic",
        "workflow": {
            "nodes": [
                {"id": "start", "type": "start", "position": {"x": 400, "y": 50}, "data": {"label": "Start"}},
                {"id": "check", "type": "condition", "position": {"x": 400, "y": 150}, "data": {"label": "Check Condition", "config": {"condition": "input.value > 10", "true_path": ["high"], "false_path": ["low"]}}},
                {"id": "high", "type": "task", "position": {"x": 200, "y": 250}, "data": {"label": "High Value Path", "config": {"action": "echo", "params": {"message": "Value is high"}}}},
                {"id": "low", "type": "task", "position": {"x": 600, "y": 250}, "data": {"label": "Low Value Path", "config": {"action": "echo", "params": {"message": "Value is low"}}}},
                {"id": "end", "type": "end", "position": {"x": 400, "y": 350}, "data": {"label": "End"}},
            ],
            "edges": [
                {"id": "e1", "source": "start", "target": "check"},
                {"id": "e2", "source": "check", "target": "high", "type": "conditional", "condition": "input.value > 10"},
                {"id": "e3", "source": "check", "target": "low", "type": "conditional", "condition": "input.value <= 10"},
                {"id": "e4", "source": "high", "target": "end"},
                {"id": "e5", "source": "low", "target": "end"},
            ],
        },
    },
    {
        "id": "parallel-processing",
        "name": "Parallel Processing",
        "description": "Run multiple tasks in parallel and merge results",
        "category": "parallel",
        "workflow": {
            "nodes": [
                {"id": "start", "type": "start", "position": {"x": 400, "y": 50}, "data": {"label": "Start"}},
                {"id": "split", "type": "parallel", "position": {"x": 400, "y": 150}, "data": {"label": "Parallel Split", "config": {"branches": ["task1", "task2", "task3"]}}},
                {"id": "task1", "type": "task", "position": {"x": 100, "y": 250}, "data": {"label": "Task 1", "config": {"action": "process", "params": {"id": 1}}}},
                {"id": "task2", "type": "task", "position": {"x": 400, "y": 250}, "data": {"label": "Task 2", "config": {"action": "process", "params": {"id": 2}}}},
                {"id": "task3", "type": "task", "position": {"x": 700, "y": 250}, "data": {"label": "Task 3", "config": {"action": "process", "params": {"id": 3}}}},
                {"id": "merge", "type": "task", "position": {"x": 400, "y": 350}, "data": {"label": "Merge Results", "config": {"action": "merge", "params": {}}}},
                {"id": "end", "type": "end", "position": {"x": 400, "y": 450}, "data": {"label": "End"}},
            ],
            "edges": [
                {"id": "e1", "source": "start", "target": "split"},
                {"id": "e2", "source": "split", "target": "task1", "type": "parallel"},
                {"id": "e3", "source": "split", "target": "task2", "type": "parallel"},
                {"id": "e4", "source": "split", "target": "task3", "type": "parallel"},
                {"id": "e5", "source": "task1", "target": "merge"},
                {"id": "e6", "source": "task2", "target": "merge"},
                {"id": "e7", "source": "task3", "target": "merge"},
                {"id": "e8", "source": "merge", "target": "end"},
            ],
        },
    },
    {
        "id": "ci-cd-pipeline",
        "name": "CI/CD Pipeline",
        "description": "Complete CI/CD pipeline with build, test, deploy stages",
        "category": "devops",
        "workflow": {
            "nodes": [
                {"id": "start", "type": "start", "position": {"x": 400, "y": 50}, "data": {"label": "Start Pipeline"}},
                {"id": "checkout", "type": "task", "position": {"x": 400, "y": 130}, "data": {"label": "Checkout Code", "config": {"action": "git_checkout", "params": {}}}},
                {"id": "install", "type": "task", "position": {"x": 400, "y": 210}, "data": {"label": "Install Dependencies", "config": {"action": "npm_install", "params": {}}}},
                {"id": "lint", "type": "task", "position": {"x": 200, "y": 290}, "data": {"label": "Lint", "config": {"action": "lint", "params": {}}}},
                {"id": "test", "type": "task", "position": {"x": 400, "y": 290}, "data": {"label": "Run Tests", "config": {"action": "test", "params": {}}}},
                {"id": "build", "type": "task", "position": {"x": 600, "y": 290}, "data": {"label": "Build", "config": {"action": "build", "params": {}}}},
                {"id": "merge", "type": "parallel", "position": {"x": 400, "y": 370}, "data": {"label": "Wait for All"}},
                {"id": "deploy", "type": "task", "position": {"x": 400, "y": 450}, "data": {"label": "Deploy", "config": {"action": "deploy", "params": {}}}},
                {"id": "notify", "type": "task", "position": {"x": 400, "y": 530}, "data": {"label": "Notify", "config": {"action": "notify", "params": {}}}},
                {"id": "end", "type": "end", "position": {"x": 400, "y": 610}, "data": {"label": "Complete"}},
            ],
            "edges": [
                {"id": "e1", "source": "start", "target": "checkout"},
                {"id": "e2", "source": "checkout", "target": "install"},
                {"id": "e3", "source": "install", "target": "lint"},
                {"id": "e4", "source": "install", "target": "test"},
                {"id": "e5", "source": "install", "target": "build"},
                {"id": "e6", "source": "lint", "target": "merge"},
                {"id": "e7", "source": "test", "target": "merge"},
                {"id": "e8", "source": "build", "target": "merge"},
                {"id": "e9", "source": "merge", "target": "deploy"},
                {"id": "e10", "source": "deploy", "target": "notify"},
                {"id": "e11", "source": "notify", "target": "end"},
            ],
        },
    },
    {
        "id": "data-pipeline",
        "name": "Data Processing Pipeline",
        "description": "Extract, transform, load (ETL) data pipeline",
        "category": "data",
        "workflow": {
            "nodes": [
                {"id": "start", "type": "start", "position": {"x": 400, "y": 50}, "data": {"label": "Start ETL"}},
                {"id": "extract", "type": "task", "position": {"x": 400, "y": 150}, "data": {"label": "Extract Data", "config": {"action": "extract", "params": {"source": "database"}}}},
                {"id": "validate", "type": "condition", "position": {"x": 400, "y": 250}, "data": {"label": "Validate Data", "config": {"condition": "data.isValid", "true_path": ["transform"], "false_path": ["error"]}}},
                {"id": "transform", "type": "task", "position": {"x": 200, "y": 350}, "data": {"label": "Transform", "config": {"action": "transform", "params": {}}}},
                {"id": "load", "type": "task", "position": {"x": 400, "y": 450}, "data": {"label": "Load to Warehouse", "config": {"action": "load", "params": {"target": "warehouse"}}}},
                {"id": "error", "type": "task", "position": {"x": 600, "y": 350}, "data": {"label": "Handle Error", "config": {"action": "alert", "params": {"message": "Validation failed"}}}},
                {"id": "end", "type": "end", "position": {"x": 400, "y": 550}, "data": {"label": "Complete"}},
            ],
            "edges": [
                {"id": "e1", "source": "start", "target": "extract"},
                {"id": "e2", "source": "extract", "target": "validate"},
                {"id": "e3", "source": "validate", "target": "transform", "type": "conditional", "condition": "data.isValid"},
                {"id": "e4", "source": "validate", "target": "error", "type": "conditional", "condition": "!data.isValid"},
                {"id": "e5", "source": "transform", "target": "load"},
                {"id": "e6", "source": "load", "target": "end"},
                {"id": "e7", "source": "error", "target": "end"},
            ],
        },
    },
]


async def execute_workflow(workflow_def: Dict[str, Any], input_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Convenience function to execute a workflow"""
    executor = WorkflowExecutor()
    execution = await executor.execute(workflow_def.get("workflow", workflow_def), input_data)
    
    return {
        "execution_id": execution.id,
        "status": execution.status.value,
        "output": execution.output_data,
        "error": execution.error,
        "nodes": {
            nid: {
                "status": r.status.value,
                "output": r.output,
                "error": r.error,
                "retries": r.retries,
            }
            for nid, r in execution.nodes.items()
        },
    }