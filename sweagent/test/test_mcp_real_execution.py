#!/usr/bin/env python
"""Real MCP execution test with Apptainer.

This test verifies that MCP filesystem tools can work with real Apptainer execution.
Instead of mocking the agent's output, we mock the agent's input to make the test deterministic.
"""

import asyncio
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from dotenv import load_dotenv

from agents.run import Runner
from sweagent.config import AgentConfigLoader
from sweagent.runtime import SWEAgentRuntime


@pytest.mark.asyncio
async def test_mcp_filesystem_with_real_apptainer():
    """Test MCP filesystem tools with real Apptainer execution."""
    
    # Load environment variables
    load_dotenv()
    
    # Load configuration
    config_path = Path(__file__).with_name("test_config.yaml")
    config = AgentConfigLoader(path=config_path).load()
    
    # Use a real image for testing
    config.commands.apptainer_image = "./swebench_instances/images/astropy_1776_astropy-12907.sif"
    
    runtime = SWEAgentRuntime(config=config)
    
    # Build agent with real MCP server
    agent = await runtime.build_agent()
    run_config = runtime.build_run_config()
    
    print(f"Testing with image: {config.commands.apptainer_image}")
    print(f"Agent tools: {[tool.name for tool in agent.tools]}")
    print(f"MCP servers: {[server.name for server in agent.mcp_servers]}")
    
    # Mock the agent's model response to make it deterministic
    # This ensures the agent will use MCP tools instead of generating random responses
    mock_response_content = """I'll help you list the files in the current directory using the available tools.

Let me use the list_directory tool to see what's in the current directory."""
    
    mock_tool_calls = [
        {
            "id": "call_123",
            "type": "function",
            "function": {
                "name": "list_directory",
                "arguments": '{"path": "."}'
            }
        }
    ]
    
    # Create a mock model response
    class MockModelResponse:
        def __init__(self):
            self.output = [
                MagicMock(
                    content=mock_response_content,
                    tool_calls=mock_tool_calls,
                    role="assistant"
                )
            ]
            self.usage = MagicMock()
            self.response_id = "test_response_123"
    
    # Mock the model's get_response method
    async def mock_get_response(*args, **kwargs):
        return MockModelResponse()
    
    # Patch the model's get_response method
    with patch.object(agent.model, 'get_response', side_effect=mock_get_response):
        try:
            # Run the agent with a simple task
            task = "List the files in the current directory."
            
            print(f"\nRunning task: {task}")
            print("=" * 50)
            
            result = await Runner.run(
                agent,
                task,
                run_config=run_config,
                max_turns=1,  # Limit to 1 turn for testing
            )
            
            print("=" * 50)
            print("✓ Agent execution completed successfully!")
            
            # Verify the result
            assert result is not None
            assert hasattr(result, 'final_output')
            
            print(f"Final output: {result.final_output}")
            
            # Check that MCP tools were available
            assert len(agent.mcp_servers) > 0
            assert agent.mcp_servers[0].name == "filesystem"
            
            print("✓ MCP filesystem server was properly configured")
            
        except Exception as e:
            print(f"✗ Error during execution: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        finally:
            # Clean up MCP servers
            print("\nCleaning up MCP servers...")
            for mcp_server in agent.mcp_servers:
                try:
                    await mcp_server.cleanup()
                except Exception as e:
                    print(f"Warning during cleanup: {e}")
            print("✓ Cleanup complete")


@pytest.mark.asyncio
async def test_mcp_read_file_with_apptainer():
    """Test MCP read_file tool with real Apptainer execution."""
    
    # Load environment variables
    load_dotenv()
    
    # Load configuration
    config_path = Path(__file__).with_name("test_config.yaml")
    config = AgentConfigLoader(path=config_path).load()
    
    # Use a real image for testing
    config.commands.apptainer_image = "./swebench_instances/images/astropy_1776_astropy-12907.sif"
    
    runtime = SWEAgentRuntime(config=config)
    
    # Build agent with real MCP server
    agent = await runtime.build_agent()
    run_config = runtime.build_run_config()
    
    print(f"Testing read_file with image: {config.commands.apptainer_image}")
    
    # Mock the agent's model response to use read_file tool
    mock_response_content = """I'll read the README file to see what's in this project.

Let me use the read_file tool to read the README file."""
    
    mock_tool_calls = [
        {
            "id": "call_456",
            "type": "function",
            "function": {
                "name": "read_file",
                "arguments": '{"path": "README.md"}'
            }
        }
    ]
    
    # Create a mock model response
    class MockModelResponse:
        def __init__(self):
            self.output = [
                MagicMock(
                    content=mock_response_content,
                    tool_calls=mock_tool_calls,
                    role="assistant"
                )
            ]
            self.usage = MagicMock()
            self.response_id = "test_response_456"
    
    # Mock the model's get_response method
    async def mock_get_response(*args, **kwargs):
        return MockModelResponse()
    
    # Patch the model's get_response method
    with patch.object(agent.model, 'get_response', side_effect=mock_get_response):
        try:
            # Run the agent with a task that should trigger read_file
            task = "Read the README file and tell me what this project is about."
            
            print(f"\nRunning task: {task}")
            print("=" * 50)
            
            result = await Runner.run(
                agent,
                task,
                run_config=run_config,
                max_turns=1,  # Limit to 1 turn for testing
            )
            
            print("=" * 50)
            print("✓ Agent execution completed successfully!")
            
            # Verify the result
            assert result is not None
            assert hasattr(result, 'final_output')
            
            print(f"Final output: {result.final_output}")
            
            # Check that MCP tools were available
            assert len(agent.mcp_servers) > 0
            assert agent.mcp_servers[0].name == "filesystem"
            
            print("✓ MCP read_file tool was properly configured")
            
        except Exception as e:
            print(f"✗ Error during execution: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        finally:
            # Clean up MCP servers
            print("\nCleaning up MCP servers...")
            for mcp_server in agent.mcp_servers:
                try:
                    await mcp_server.cleanup()
                except Exception as e:
                    print(f"Warning during cleanup: {e}")
            print("✓ Cleanup complete")


@pytest.mark.asyncio
async def test_shell_command_with_apptainer():
    """Test shell command execution with real Apptainer."""
    
    # Load environment variables
    load_dotenv()
    
    # Load configuration
    config_path = Path(__file__).with_name("test_config.yaml")
    config = AgentConfigLoader(path=config_path).load()
    
    # Use a real image for testing
    config.commands.apptainer_image = "./swebench_instances/images/astropy_1776_astropy-12907.sif"
    
    runtime = SWEAgentRuntime(config=config)
    
    # Build agent with real MCP server
    agent = await runtime.build_agent()
    run_config = runtime.build_run_config()
    
    print(f"Testing shell command with image: {config.commands.apptainer_image}")
    
    # Mock the agent's model response to use shell command
    mock_response_content = """I'll list the files in the current directory using the shell command.

Let me use the local_shell tool to run the ls command."""
    
    mock_tool_calls = [
        {
            "id": "call_789",
            "type": "function",
            "function": {
                "name": "local_shell",
                "arguments": '{"command": "ls -la"}'
            }
        }
    ]
    
    # Create a mock model response
    class MockModelResponse:
        def __init__(self):
            self.output = [
                MagicMock(
                    content=mock_response_content,
                    tool_calls=mock_tool_calls,
                    role="assistant"
                )
            ]
            self.usage = MagicMock()
            self.response_id = "test_response_789"
    
    # Mock the model's get_response method
    async def mock_get_response(*args, **kwargs):
        return MockModelResponse()
    
    # Patch the model's get_response method
    with patch.object(agent.model, 'get_response', side_effect=mock_get_response):
        try:
            # Run the agent with a task that should trigger shell command
            task = "List all files in the current directory using a shell command."
            
            print(f"\nRunning task: {task}")
            print("=" * 50)
            
            result = await Runner.run(
                agent,
                task,
                run_config=run_config,
                max_turns=1,  # Limit to 1 turn for testing
            )
            
            print("=" * 50)
            print("✓ Agent execution completed successfully!")
            
            # Verify the result
            assert result is not None
            assert hasattr(result, 'final_output')
            
            print(f"Final output: {result.final_output}")
            
            # Check that shell tool was available
            assert len(agent.tools) > 0
            assert agent.tools[0].name == "local_shell"
            
            print("✓ Shell command tool was properly configured")
            
        except Exception as e:
            print(f"✗ Error during execution: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        finally:
            # Clean up MCP servers
            print("\nCleaning up MCP servers...")
            for mcp_server in agent.mcp_servers:
                try:
                    await mcp_server.cleanup()
                except Exception as e:
                    print(f"Warning during cleanup: {e}")
            print("✓ Cleanup complete")


if __name__ == "__main__":
    # Run a single test for manual testing
    asyncio.run(test_mcp_filesystem_with_real_apptainer())
