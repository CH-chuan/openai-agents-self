"""Entrypoint helpers for running the SWE-agent."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agents.run import DEFAULT_AGENT_RUNNER

from sweagent.config import AgentConfigLoader
from sweagent.sweagent_logging import configure_logging, logger
from sweagent.runtime import SWEAgentRuntime


@dataclass
class SWEAgentRunner:
    """Loads configuration and executes the agent workflow."""

    config_path: Path

    async def run(self, input_text: str, *, context: Any | None = None) -> None:
        configure_logging()
        loader = AgentConfigLoader(path=self.config_path)
        config = loader.load()

        runtime = SWEAgentRuntime(config=config)
        agent = await runtime.build_agent()
        run_config = runtime.build_run_config()

        logger.info("Starting SWE-agent run", extra={"input": input_text[:200]})

        try:
            result = await DEFAULT_AGENT_RUNNER.run(
                agent,
                input_text,
                context=context,
                run_config=run_config,
                max_turns=run_config.max_turns,
            )

            logger.info("SWE-agent run complete", extra={
                "final_output": str(result.final_output)[:500] if result.final_output else None,
                "num_turns": len(result.raw_responses),
                "num_items": len(result.new_items)
            })
        
        finally:
            # Clean up MCP servers to avoid async cleanup errors
            for mcp_server in agent.mcp_servers:
                try:
                    await mcp_server.cleanup()
                except Exception as e:
                    logger.warning(f"Error cleaning up MCP server: {e}")

