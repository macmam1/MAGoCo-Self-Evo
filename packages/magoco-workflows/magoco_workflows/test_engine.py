"""Test the Workflow Execution Engine."""

import asyncio
from magoco_workflows.engine import WorkflowEngine, WorkflowNode


async def test_workflow_engine():
    engine = WorkflowEngine()

    # Define a simple 3-node DAG:
    #   [Fetch Data] ---> [Process Data] ---> [Save Report]
    #         \---------> [Audit Log] -----/
    
    node1 = WorkflowNode("n1", "Fetch Data", "agent", {"prompt": "Scrape metrics"})
    node2 = WorkflowNode("n2", "Process Data", "code", {"code": "df.mean()"}, dependencies={"n1"})
    node3 = WorkflowNode("n3", "Audit Log", "tool", {"tool_name": "log_event"}, dependencies={"n1"})
    node4 = WorkflowNode("n4", "Save Report", "tool", {"tool_name": "file_write"}, dependencies={"n2", "n3"})

    engine.add_node(node1)
    engine.add_node(node2)
    engine.add_node(node3)
    engine.add_node(node4)

    results = await engine.execute()

    print("Execution Results:")
    for nid, res in results.items():
        print(f"  [{nid}]: {res}")

    assert len(results) == 4
    assert engine.nodes["n4"].status == "completed"
    print("\n✅ Workflow Engine test passed successfully!")


if __name__ == "__main__":
    asyncio.run(test_workflow_engine())
