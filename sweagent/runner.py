"""Entrypoint helpers for running the SWE-agent."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agents.run import DEFAULT_AGENT_RUNNER

from sweagent.config import AgentConfigLoader
from sweagent.logging import configure_logging, logger
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
        agent = runtime.build_agent()
        run_config = runtime.build_run_config()

        logger.info("Starting SWE-agent run", extra={"input": input_text[:200]})

        await DEFAULT_AGENT_RUNNER.run(
            agent,
            input_text,
            context=context,
            run_config=run_config,
            max_turns=run_config.max_turns,
        )

        logger.info("SWE-agent run complete")

