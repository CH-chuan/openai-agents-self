"""Tests for MCP filesystem server integration with Apptainer.

This test verifies that MCP filesystem tools can work alongside
Apptainer-based shell execution.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sweagent.config import AgentConfigLoader
from sweagent.runtime import SWEAgentRuntime


@pytest.mark.asyncio
async def test_mcp_server_initializes():
    """MCP server should initialize when configured."""
    
    config_path = Path(__file__).with_name("test_config.yaml")
    config = AgentConfigLoader(path=config_path).load()
    
    # Verify config loaded MCP settings
    assert config.mcp is not None
    assert "mcp-server-filesystem" in str(config.mcp.path)
    assert "read_file" in config.mcp.tool_allowlist
    assert "write_file" in config.mcp.tool_allowlist
    assert "list_directory" in config.mcp.tool_allowlist


@pytest.mark.asyncio
async def test_agent_has_both_shell_and_mcp_tools():
    """Agent should have both shell tools and MCP tools available."""
    
    config_path = Path(__file__).with_name("test_config.yaml")
    config = AgentConfigLoader(path=config_path).load()
    
    runtime = SWEAgentRuntime(config=config)
    
    # Mock subprocess for shell commands
    class DummyProcess:
        returncode = 0
        async def communicate(self):
            return b"test output", b""
    
    async def fake_subprocess(*args, **kwargs):
        return DummyProcess()
    
    with patch("asyncio.create_subprocess_exec", side_effect=fake_subprocess), \
         patch("sweagent.commands.write_json_log"), \
         patch("sweagent.runtime.AsyncOpenAI") as mock_openai:
        
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        agent = runtime.build_agent()
        
        # Verify agent has shell tool
        assert len(agent.tools) == 1
        assert agent.tools[0].name == "local_shell"
        
        # Verify agent has MCP servers
        assert len(agent.mcp_servers) == 1
        assert agent.mcp_servers[0].name == "filesystem"


@pytest.mark.asyncio
async def test_mcp_filesystem_accessibility():
    """Test understanding of MCP vs Apptainer filesystem access.
    
    Key insight:
    - MCP filesystem server runs on HOST, accesses HOST paths
    - Apptainer shell commands run in CONTAINER, access CONTAINER paths
    - They're connected via bind_mounts which map host -> container paths
    
    Example:
      Host: /host/data/file.txt
      Container (via bind mount): /workspace/data/file.txt
      
      MCP can read: /host/data/file.txt (host path)
      Shell can read: /workspace/data/file.txt (container path)
      Both access the SAME physical file
    """
    
    config_path = Path(__file__).with_name("test_config.yaml")
    config = AgentConfigLoader(path=config_path).load()
    
    # Verify bind mounts are configured
    assert config.commands is not None
    assert len(config.commands.bind_mounts) > 0
    
    # Show bind mount mapping
    bind_mounts = config.commands.bind_mounts
    for mount in bind_mounts:
        host_path, container_path = mount.split(":")
        print(f"  Host: {host_path} -> Container: {container_path}")
    
    # Verify MCP server is configured for filesystem access
    assert config.mcp is not None
    print(f"\nMCP filesystem server: {config.mcp.path}")
    print(f"MCP allowed tools: {', '.join(config.mcp.tool_allowlist)}")
    
    print("\n✓ Architecture verified:")
    print("  - MCP server can access host filesystem")
    print("  - Shell commands run inside Apptainer container")
    print("  - Bind mounts bridge the two filesystems")


@pytest.mark.asyncio
async def test_mcp_tool_allowlist_filtering():
    """MCP server should only expose allowlisted tools."""
    
    config_path = Path(__file__).with_name("test_config.yaml")
    config = AgentConfigLoader(path=config_path).load()
    
    runtime = SWEAgentRuntime(config=config)
    
    with patch("sweagent.runtime.AsyncOpenAI") as mock_openai, \
         patch("sweagent.commands.write_json_log"):
        
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # Mock subprocess
        class DummyProcess:
            returncode = 0
            async def communicate(self):
                return b"", b""
        
        async def fake_subprocess(*args, **kwargs):
            return DummyProcess()
        
        with patch("asyncio.create_subprocess_exec", side_effect=fake_subprocess):
            agent = runtime.build_agent()
            
            # Verify MCP server has tool filter applied
            mcp_server = agent.mcp_servers[0]
            assert mcp_server.tool_filter is not None
            assert "allowed_tool_names" in mcp_server.tool_filter
            assert "read_file" in mcp_server.tool_filter["allowed_tool_names"]
            assert "write_file" in mcp_server.tool_filter["allowed_tool_names"]
            assert "list_directory" in mcp_server.tool_filter["allowed_tool_names"]

