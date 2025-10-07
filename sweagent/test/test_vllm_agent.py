#!/usr/bin/env python
"""Test SWE-agent with VLLM using ChatCompletions API."""

import asyncio
import os
from pathlib import Path
from unittest.mock import patch

from dotenv import load_dotenv

from agents.run import DEFAULT_AGENT_RUNNER
from sweagent.config import AgentConfigLoader
from sweagent.runtime import SWEAgentRuntime


async def main():
    # Load environment variables
    load_dotenv()
    
    print("="*70)
    print("VLLM Agent Integration Test")
    print("="*70)
    print(f"API Base: {os.getenv('VLLM_API_BASE')}")
    print(f"API Key: {os.getenv('VLLM_API_KEY')[:20] if os.getenv('VLLM_API_KEY') else 'Not set'}...")
    print("="*70)
    print()
    
    # Load configuration
    config_path = Path(__file__).parent / "test_config.yaml"
    config = AgentConfigLoader(path=config_path).load()
    
    print(f"Model: {config.model.name}")
    print(f"Max steps: {config.limits.max_steps}")
    print(f"Using: ChatCompletions API (VLLM compatible)")
    print()
    
    # Build runtime
    runtime = SWEAgentRuntime(config=config)
    
    # Mock only Apptainer execution
    original_subprocess_exec = asyncio.create_subprocess_exec
    
    class DummyProcess:
        returncode = 0
        async def communicate(self):
            return b"README.md\nsetup.py\nsrc/\ntests/\n", b""
    
    async def fake_subprocess_exec(*args, **kwargs):
        if args and "apptainer" in args[0]:
            print(f"[Mock Apptainer] Command: {args[-1]}")
            return DummyProcess()
        return await original_subprocess_exec(*args, **kwargs)
    
    with patch("asyncio.create_subprocess_exec", side_effect=fake_subprocess_exec), \
         patch("sweagent.commands.write_json_log"):
        
        agent = runtime.build_agent()
        run_config = runtime.build_run_config()
        
        print(f"Agent: {agent.name}")
        print(f"Tools available: {[tool.name for tool in agent.tools]}")
        print(f"MCP Servers: {[server.name for server in agent.mcp_servers]}")
        print()
        
        # Connect MCP servers
        print("Connecting MCP servers...")
        for mcp_server in agent.mcp_servers:
            await mcp_server.connect()
        print("✓ MCP servers connected\n")
        
        # Task
        task = "List the files in the current directory using a shell command."
        
        print("="*70)
        print(f"Task: {task}")
        print("="*70)
        print()
        
        try:
            # Run agent
            result = await DEFAULT_AGENT_RUNNER.run(
                agent,
                task,
                run_config=run_config,
                max_turns=run_config.max_turns,
            )
            
            print("\n" + "="*70)
            print("✓ Agent Execution Complete")
            print("="*70)
            
            # Show result
            if hasattr(result, 'final_output') and result.final_output:
                print(f"\nFinal Output:\n{result.final_output}\n")
            
            # Clean up MCP servers properly
            print("Cleaning up MCP servers...")
            for mcp_server in agent.mcp_servers:
                try:
                    await mcp_server.cleanup()
                except Exception as e:
                    print(f"Warning during MCP cleanup: {e}")
            print("✓ Cleanup complete")
            
        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback
            traceback.print_exc()
            
            # Still try to clean up
            for mcp_server in agent.mcp_servers:
                try:
                    await mcp_server.cleanup()
                except:
                    pass


if __name__ == "__main__":
    asyncio.run(main())

