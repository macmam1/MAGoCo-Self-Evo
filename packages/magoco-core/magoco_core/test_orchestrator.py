"""Test the Multi-Agent Orchestrator."""

import asyncio
from magoco_core.agents.orchestrator import (
    MultiAgentOrchestrator,
    AgentConfig,
    AgentRole,
)

async def test_orchestrator():
    # Use default team
    orch = MultiAgentOrchestrator()
    orch.add_default_team()
    
    # Run a simple pipeline
    result = await orch.run_pipeline("Write a Python function that computes factorial")
    
    assert "final" in result
    assert len(result["steps"]) == 6  # full pipeline
    assert len(result["messages"]) > 0
    
    print("Orchestrator summary:")
    print(orch.to_dict())
    print("\nResult keys:", list(result.keys()))
    print("Pipeline steps:", len(result["steps"]))
    print("Messages exchanged:", len(result["messages"]))
    print("\nStep outputs:")
    for step in result["steps"]:
        print(f"  - {step['agent']} ({step['role']}): {step['output'][:80]}...")
    
    print("\n✅ Multi-Agent Orchestrator test passed!")

if __name__ == "__main__":
    asyncio.run(test_orchestrator())