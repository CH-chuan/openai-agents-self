#!/usr/bin/env python
"""Minimal real agent response test.

This script loads configuration from test_config.yaml and makes a real API call
to the hosted model to get a response.

Usage:
    python sweagent/test/test_minimal_real_response.py
"""

import asyncio
import os
from pathlib import Path
from unittest.mock import patch

from dotenv import load_dotenv

# print the working dir
print(os.getcwd())

from agents.run import Runner
from sweagent.config import AgentConfigLoader
from sweagent.runtime import SWEAgentRuntime


async def main():
    # Load environment variables from .env
    load_dotenv()
    
    print("="*70)
    print("Minimal Real Agent Response Test")
    print("="*70)
    print(f"API Base: {os.getenv('VLLM_API_BASE')}")
    print(f"API Key: {os.getenv('VLLM_API_KEY')[:20]}..." if os.getenv('VLLM_API_KEY') else "Not set")
    print("="*70)
    print()
    
    # Load configuration
    config_path = Path(__file__).parent / "test_config.yaml"
    config = AgentConfigLoader(path=config_path).load()
    
    print(f"Model: {config.model.name}")
    print(f"Max steps: {config.limits.max_steps}")
    print(f"Temperature: {config.model.temperature}")
    print()
    
    # Build runtime (without instance metadata for this test)
    runtime = SWEAgentRuntime(
        config=config,
        instance_id=None,
        model_name=None,
    )
    
    # Mock only the Apptainer container execution
    # (we don't have actual .sif images)
    # Let MCP server subprocess run normally
    original_subprocess_exec = asyncio.create_subprocess_exec
    
    class DummyProcess:
        returncode = 0
        
        async def communicate(self):
            # Simulate successful ls command output
            return b"file1.py\nfile2.py\nREADME.md\n", b""
    
    async def fake_subprocess_exec(*args, **kwargs):
        # Only mock apptainer commands, let MCP server run normally
        if args and "apptainer" in args[0]:
            print(f"[Mock] Apptainer exec: {args[-1] if len(args) > 0 else 'unknown'}")
            return DummyProcess()
        else:
            # Let MCP server and other processes run normally
            return await original_subprocess_exec(*args, **kwargs)
    
    with patch("asyncio.create_subprocess_exec", side_effect=fake_subprocess_exec), \
         patch("sweagent.commands.write_json_log"):
        
        # Build agent
        agent = await runtime.build_agent()
        run_config = runtime.build_run_config()
        
        print(f"Agent: {agent.name}")
        print(f"Tools: {[tool.name for tool in agent.tools]}")
        print(f"MCP Servers: {[server.name for server in agent.mcp_servers]}")
        print()
        
        # Connect MCP servers
        print("Connecting MCP servers...")
        for mcp_server in agent.mcp_servers:
            await mcp_server.connect()
        print("✓ MCP servers connected")
        print()
        
        # Simple task
        task_input = "Say hello and tell me what you can do in one sentence."
        
        print("="*70)
        print(f"Task: {task_input}")
        print("="*70)
        print()
        
        try:
            # Run the agent
            result = await Runner.run(
                agent,
                task_input,
                run_config=run_config,
                max_turns=run_config.max_turns,
            )
            
            print()
            print("="*70)
            print("✓ Agent execution completed successfully!")
            print("="*70)
            
            # Print result summary
            if hasattr(result, 'final_output') and result.final_output:
                print(f"\nFinal Output: {result.final_output}")
            
        except Exception as e:
            print()
            print("="*70)
            print(f"✗ Error during execution: {e}")
            print("="*70)
            import traceback
            traceback.print_exc()
        
        finally:
            # Clean up MCP servers to avoid async errors
            print("\nCleaning up MCP servers...")
            for mcp_server in agent.mcp_servers:
                try:
                    await mcp_server.cleanup()
                except Exception as e:
                    print(f"Warning during cleanup: {e}")
            print("✓ Cleanup complete")


if __name__ == "__main__":
    asyncio.run(main())

