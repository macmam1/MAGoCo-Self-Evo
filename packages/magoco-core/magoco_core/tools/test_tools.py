"""Test file tools to verify registration."""

import asyncio
from magoco_core.tools.registry import tool_registry
from magoco_core.tools.file_tools import (
    FileReadTool, FileWriteTool, FileListTool
)
from magoco_core.tools.code_exec import CodeExecTool


def test_registry():
    """Verify all tools registered."""
    tools = tool_registry.list_tools()
    assert len(tools) == 7, f"Expected 7 tools, got {len(tools)}"

    names = [t.name for t in tools]
    assert "file_read" in names
    assert "file_write" in names
    assert "file_list" in names
    assert "python_exec" in names
    assert "bash_exec" in names
    assert "web_search" in names
    assert "web_fetch" in names
    
    print("✅ All tools registered:", names)


async def test_code_exec():
    """Test code execution."""
    tool = CodeExecTool()
    result = await tool.execute("print('hello world')")
    assert result.success
    assert "hello world" in result.content
    print("✅ Code execution works:", result.content)


async def test_code_exec_timeout():
    """Test timeout protection."""
    tool = CodeExecTool()
    result = await tool.execute("import time; time.sleep(20)", timeout=5)
    assert not result.success
    assert "timeout" in result.error.lower()
    print("✅ Timeout protection works")


async def test_code_exec_security():
    """Test security block."""
    tool = CodeExecTool()
    result = await tool.execute("__import__('os').system('whoami')")
    assert not result.success
    assert "dangerous" in result.error.lower()
    print("✅ Security guard works")


async def test_file_ops():
    """Test file read/write."""
    write_tool = FileWriteTool()
    read_tool = FileReadTool()
    list_tool = FileListTool()
    
    # Write
    test_content = "test content line 1\nline 2\nline 3"
    result = await write_tool.execute("/tmp/test_magoco_file.txt", test_content)
    assert result.success
    
    # Read
    result = await read_tool.execute("/tmp/test_magoco_file.txt")
    assert result.success
    assert "line 1" in result.content
    
    # List
    result = await list_tool.execute("/tmp", pattern="test_magoco_*")
    assert result.success
    assert "test_magoco_file.txt" in result.content
    
    # Cleanup
    import os
    os.unlink("/tmp/test_magoco_file.txt")
    
    print("✅ File operations work")


if __name__ == "__main__":
    test_registry()
    asyncio.run(test_code_exec())
    asyncio.run(test_code_exec_timeout())
    asyncio.run(test_code_exec_security())
    asyncio.run(test_file_ops())
    print("\n🚀 All tests passed!")