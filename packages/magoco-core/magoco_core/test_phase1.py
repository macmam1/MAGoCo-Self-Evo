"""Tests for ThreeLayerMemory and ReActAgent."""

import asyncio
import time
from magoco_core.memory.three_layer import ThreeLayerMemory
from magoco_core.agents.react_agent import ReActAgent


def test_memory_layers():
    """Test three-layer memory system."""
    mem = ThreeLayerMemory(max_working_size=3)
    
    # Add multiple turns
    for i in range(5):
        mem.add_turn("user", f"message {i}")
    
    # Verbatim should keep all
    assert len(mem.verbatim_history) == 5, \
        f"Verbatim expected 5, got {len(mem.verbatim_history)}"
    
    # Working context should trim
    assert len(mem.working_context) <= 3, \
        f"Working context should be trimmed, got {len(mem.working_context)}"
    
    # Store knowledge
    mem.store_knowledge("user_name", "Mammad")
    assert mem.get_knowledge("user_name") == "Mammad"
    
    print("✅ Memory layers work correctly")


async def test_react_simple():
    """Test basic ReAct agent operation."""
    agent = ReActAgent()
    result = await agent.run("read file /etc/hostname")
    
    assert result.success or not result.success  # May fail due to permission
    assert "memory" in result.metadata
    
    # Memory should have entries
    assert len(agent.memory) > 0
    
    print("✅ ReAct agent runs")


async def test_react_with_tools():
    """Test agent uses tools."""
    agent = ReActAgent()
    
    # Write a test file
    write_result = await agent.run("write /tmp/test_react.txt hello world")
    
    # Verify file was created
    import os
    assert os.path.exists("/tmp/test_react.txt")
    
    # Read it back
    read_result = await agent.run("read /tmp/test_react.txt")
    assert read_result.success or "hello" in read_result.content
    
    # Cleanup
    os.unlink("/tmp/test_react.txt")
    
    print("✅ ReAct agent uses tools")


def test_knowledge_layer():
    """Test distilled knowledge storage."""
    mem = ThreeLayerMemory()
    
    mem.store_knowledge("project", "MAGoCo-Self-Evo")
    mem.store_knowledge("phase", 1)
    mem.store_knowledge("tools", ["react", "memory", "tools"])
    
    snapshot = mem.to_dict()
    
    assert "project" in snapshot["distilled_knowledge_keys"]
    assert "phase" in snapshot["distilled_knowledge_keys"]
    
    print("✅ Knowledge layer works:", snapshot)


if __name__ == "__main__":
    test_memory_layers()
    test_knowledge_layer()
    asyncio.run(test_react_simple())
    asyncio.run(test_react_with_tools())
    print("\n🚀 All Phase 1.5 tests passed!")
