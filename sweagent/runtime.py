"""Runtime assembly for the SWE-agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agents import Agent, RunConfig, set_default_openai_client
from agents.model_settings import ModelSettings
from agents.models.interface import Model
from agents.models.openai_responses import OpenAIResponsesModel
from agents.tool import LocalShellTool
from openai import AsyncOpenAI

from .commands import ApptainerCommandExecutor
from .config import SWEAgentConfig
from .logging import configure_logging, logger
from .mcp import MCPServerFactory


@dataclass
class SWEAgentRuntime:
    """Constructs agent instances based on configuration."""

    config: SWEAgentConfig

    def build_agent(self) -> Agent[Any]:
        configure_logging()
        executor = ApptainerCommandExecutor(
            security=self.config.security,
            command_config=self.config.commands,
        )
        shell_tool = LocalShellTool(executor=executor)

        mcp_server = MCPServerFactory(self.config.mcp).create()

        openai_client = AsyncOpenAI(
            api_key=self.config.model.api_key,
            base_url=self.config.model.api_base,
        )
        set_default_openai_client(openai_client, use_for_tracing=True)

        model: Model = OpenAIResponsesModel(
            model=self.config.model.name,
            openai_client=openai_client,
        )

        instructions = self.config.templates.system_template or ""

        agent = Agent[
            Any
        ](  # Generic context; SWE-bench harness will supply details via RunConfig
            name="swe-agent",
            instructions=instructions,
            tools=[shell_tool],
            mcp_servers=[mcp_server],
            model=model,
            model_settings=self._build_model_settings(),
        )

        logger.info(
            "SWE-agent constructed",
            extra={
                "model": self.config.model.name,
                "max_steps": self.config.limits.max_steps,
                "max_tokens": self.config.limits.max_tokens,
            },
        )

        return agent

    def build_run_config(self) -> RunConfig:
        run_config = RunConfig()
        if self.config.limits.max_steps is not None:
            run_config.max_turns = self.config.limits.max_steps
        return run_config

    def _build_model_settings(self) -> ModelSettings:
        settings = ModelSettings()
        if self.config.model.temperature is not None:
            settings.temperature = self.config.model.temperature
        if self.config.limits.max_tokens is not None:
            settings.max_tokens = self.config.limits.max_tokens
        for key, value in self.config.model.extra.items():
            setattr(settings, key, value)
        return settings

