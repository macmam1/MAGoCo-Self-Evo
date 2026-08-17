"""Workflow Execution Engine.

Executes DAGs (Directed Acyclic Graphs) of tasks with dependencies,
supporting parallel execution, failure handling, and state persistence.
"""

import asyncio
import logging
from typing import Dict, List, Any, Set
from datetime import datetime

logger = logging.getLogger("magoco.workflow.engine")


class WorkflowNode:
    def __init__(self, node_id: str, name: str, node_type: str, config: Dict[str, Any], dependencies: Set[str] = None):
        self.node_id = node_id
        self.name = name
        self.node_type = node_type  # "agent", "tool", "condition", "code"
        self.config = config
        self.dependencies = dependencies or set()
        self.status = "pending"  # pending, running, completed, failed
        self.result = None
        self.error = None


class WorkflowEngine:
    def __init__(self):
        self.nodes: Dict[str, WorkflowNode] = {}
        self.execution_order: List[str] = []

    def add_node(self, node: WorkflowNode):
        self.nodes[node.node_id] = node

    def _resolve_dependencies(self) -> List[Set[str]]:
        """Topological sort returning execution batches (nodes that can run in parallel)."""
        executed: Set[str] = set()
        batches: List[Set[str]] = []

        remaining = set(self.nodes.keys())

        while remaining:
            # Find nodes whose dependencies are all in `executed`
            batch = {
                node_id for node_id in remaining
                if self.nodes[node_id].dependencies.issubset(executed)
            }

            if not batch:
                raise ValueError("Cyclic dependency detected in workflow graph!")

            batches.append(batch)
            executed.update(batch)
            remaining -= batch

        return batches

    async def execute(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute the workflow in batches."""
        context = context or {}
        batches = self._resolve_dependencies()
        results = {}

        logger.info(f"Starting workflow with {len(self.nodes)} nodes across {len(batches)} batches.")

        for batch_index, batch in enumerate(batches):
            logger.info(f"Executing batch {batch_index + 1}/{len(batches)} with nodes: {batch}")
            
            # Execute all nodes in the current batch concurrently
            tasks = [self._execute_node(node_id, context, results) for node_id in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check for errors in batch
            for node_id, res in zip(batch, batch_results):
                if isinstance(res, Exception):
                    self.nodes[node_id].status = "failed"
                    self.nodes[node_id].error = str(res)
                    raise res
                else:
                    self.nodes[node_id].status = "completed"
                    self.nodes[node_id].result = res
                    results[node_id] = res

        return results

    async def _execute_node(self, node_id: str, context: Dict[str, Any], previous_results: Dict[str, Any]) -> Any:
        node = self.nodes[node_id]
        node.status = "running"

        logger.info(f"Executing node {node.name} ({node.node_type})")

        # Simulate node execution based on type
        await asyncio.sleep(0.5)  # Simulate latency

        if node.node_type == "agent":
            prompt = node.config.get("prompt", "Default task")
            return f"Agent '{node.name}' completed task: '{prompt}'"
        elif node.node_type == "tool":
            tool_name = node.config.get("tool_name", "file_read")
            return f"Tool '{tool_name}' executed successfully"
        elif node.node_type == "code":
            code = node.config.get("code", "print('hello')")
            return f"Code executed output: 'SUCCESS'"
        else:
            return f"Node {node.name} executed."
