"""Runtime assembly for the SWE-agent."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from agents import Agent, RunConfig, set_default_openai_client
from agents.model_settings import ModelSettings
from agents.models.interface import Model
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from openai import AsyncOpenAI

from sweagent.commands import ApptainerCommandExecutor
from sweagent.config import SWEAgentConfig
from sweagent.sweagent_logging import configure_logging, logger
from sweagent.sweagent_mcp import MCPServerFactory
from sweagent.workspace import WorkspaceManager, WorkspaceInfo


@dataclass
class SWEAgentRuntime:
    """Constructs agent instances based on configuration."""

    config: SWEAgentConfig
    instance_id: Optional[str] = None
    model_name: Optional[str] = None
    sif_path: Optional[Path] = None
    workspace_info: Optional[WorkspaceInfo] = None

    async def build_agent(self) -> Agent[Any]:
        configure_logging()
        
        # Determine the sif_path to use
        determined_sif_path = self._determine_sif_path()
        
        # Create workspace if instance metadata provided
        if self.instance_id and self.model_name and determined_sif_path:
            workspace_manager = WorkspaceManager(base_dir=self.config.workspace.base_dir)
            self.workspace_info = workspace_manager.create_workspace(
                instance_id=self.instance_id,
                model_name=self.model_name,
                sif_path=determined_sif_path,
            )
            logger.info(
                "Workspace created for instance",
                extra={
                    "instance_id": self.instance_id,
                    "workspace_dir": str(self.workspace_info.workspace_dir),
                }
            )
        
        tools = []
        if self.config.commands is not None:
            executor = ApptainerCommandExecutor(
                security=self.config.security,
                command_config=self.config.commands,
                workspace_info=self.workspace_info,  # Pass workspace info
            )
            # Convert to FunctionTool for ChatCompletions API compatibility
            shell_tool = executor.to_function_tool()
            tools.append(shell_tool)

        mcp_servers = []
        if self.config.mcp is not None:
            mcp_server = MCPServerFactory(
                config=self.config.mcp,
                workspace_info=self.workspace_info,  # Pass workspace info
            ).create()
            # Connect the MCP server before adding it to the agent
            await mcp_server.connect()
            mcp_servers.append(mcp_server)

        openai_client = AsyncOpenAI(
            api_key=self.config.model.api_key,
            base_url=self.config.model.api_base,
        )
        # Disable tracing for non-OpenAI endpoints (like VLLM)
        # This prevents 401 errors when the SDK tries to send traces to OpenAI
        use_for_tracing = self.config.model.api_base is None or "openai.com" in str(self.config.model.api_base)
        set_default_openai_client(openai_client, use_for_tracing=use_for_tracing)

        # Use ChatCompletions model for VLLM compatibility
        model: Model = OpenAIChatCompletionsModel(
            model=self.config.model.name,
            openai_client=openai_client,
        )

        instructions = self.config.templates.system_template or ""

        agent = Agent[
            Any
        ](  # Generic context; SWE-bench harness will supply details via RunConfig
            name="swe-agent",
            instructions=instructions,
            tools=tools,
            mcp_servers=mcp_servers,
            model=model,
            model_settings=self._build_model_settings(),
            output_type=None,  # Don't treat any response as final output
            tool_use_behavior="run_llm_again",  # Explicitly set to continue after tool use
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
    
    def _determine_sif_path(self) -> Optional[Path]:
        """Determine which SIF path to use.
        
        Priority:
        1. Explicitly provided sif_path parameter
        2. From config.commands.apptainer_image
        3. None (if neither provided)
        
        Returns:
            Path to SIF file, or None if not available
        """
        if self.sif_path:
            # Explicitly provided - highest priority
            return self.sif_path
        elif self.config.commands and self.config.commands.apptainer_image:
            # From config
            return self.config.commands.apptainer_image
        else:
            # No SIF path available
            return None

