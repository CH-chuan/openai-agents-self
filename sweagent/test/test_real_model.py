"""Real integration test with live model communication.

This test requires:
- VLLM_API_KEY environment variable
- VLLM_API_BASE environment variable
- A running model endpoint

Run with: pytest sweagent/test/test_real_model.py -s
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from agents.run import DEFAULT_AGENT_RUNNER
from sweagent.config import AgentConfigLoader
from sweagent.runtime import SWEAgentRuntime


@pytest.mark.skipif(
    not os.getenv("VLLM_API_KEY") or not os.getenv("VLLM_API_BASE"),
    reason="Requires VLLM_API_KEY and VLLM_API_BASE environment variables",
)
@pytest.mark.asyncio
async def test_real_model_communication():
    """Test agent with real model API, mocking only container execution."""
    
    config_path = Path(__file__).with_name("test_config.yaml")
    config = AgentConfigLoader(path=config_path).load()
    
    runtime = SWEAgentRuntime(config=config)
    
    # Mock only the container execution, not the model
    class DummyProcess:
        returncode = 0
        
        async def communicate(self):
            # Simulate ls output
            return b"file1.py\nfile2.py\nREADME.md\n", b""
    
    async def fake_subprocess_exec(*args, **kwargs):
        print(f"[Mock] Apptainer command: {' '.join(args[:10])}...")
        return DummyProcess()
    
    with patch("asyncio.create_subprocess_exec", side_effect=fake_subprocess_exec), \
         patch("sweagent.commands.write_json_log"):
        
        agent = runtime.build_agent()
        run_config = runtime.build_run_config()
        
        print(f"\n{'='*60}")
        print(f"Testing with model: {config.model.name}")
        print(f"API Base: {config.model.api_base}")
        print(f"Max steps: {config.limits.max_steps}")
        print(f"{'='*60}\n")
        
        # Run the agent with a simple task
        task_input = "List the files in the current directory."
        
        try:
            result = await DEFAULT_AGENT_RUNNER.run(
                agent,
                task_input,
                run_config=run_config,
                max_turns=run_config.max_turns,
            )
            
            print(f"\n{'='*60}")
            print("Agent execution completed successfully!")
            print(f"{'='*60}\n")
            
            # Basic assertions
            assert result is not None
            
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"Error during execution: {e}")
            print(f"{'='*60}\n")
            raise


@pytest.mark.skipif(
    not os.getenv("VLLM_API_KEY") or not os.getenv("VLLM_API_BASE"),
    reason="Requires VLLM_API_KEY and VLLM_API_BASE environment variables",
)
@pytest.mark.asyncio
async def test_real_model_tool_calling():
    """Test that the model actually makes tool calls through the agent."""
    
    config_path = Path(__file__).with_name("test_config.yaml")
    config = AgentConfigLoader(path=config_path).load()
    
    runtime = SWEAgentRuntime(config=config)
    
    tool_calls_made = []
    
    # Mock container execution and capture tool calls
    class DummyProcess:
        returncode = 0
        
        async def communicate(self):
            return b"test_file.py\n", b""
    
    async def fake_subprocess_exec(*args, **kwargs):
        # Capture the command being executed
        if len(args) > 0:
            command_line = args[-1] if len(args) > 0 else "unknown"
            tool_calls_made.append(command_line)
            print(f"[Tool Call] Command: {command_line}")
        return DummyProcess()
    
    with patch("asyncio.create_subprocess_exec", side_effect=fake_subprocess_exec), \
         patch("sweagent.commands.write_json_log"):
        
        agent = runtime.build_agent()
        run_config = runtime.build_run_config()
        
        # Run the agent
        task_input = "Use the shell to list files in the current directory."
        
        await DEFAULT_AGENT_RUNNER.run(
            agent,
            task_input,
            run_config=run_config,
            max_turns=run_config.max_turns,
        )
        
        print(f"\n{'='*60}")
        print(f"Total tool calls made: {len(tool_calls_made)}")
        for i, call in enumerate(tool_calls_made, 1):
            print(f"  {i}. {call}")
        print(f"{'='*60}\n")
        
        # Verify the model actually called tools
        assert len(tool_calls_made) > 0, "Model should have made at least one tool call"

