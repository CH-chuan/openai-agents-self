"""Integration tests for the SWE-agent runtime."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sweagent.config import AgentConfigLoader
from sweagent.runtime import SWEAgentRuntime


@pytest.mark.asyncio
async def test_agent_builds_successfully():
    """Runtime should construct an agent from config without errors."""

    config_path = Path(__file__).with_name("test_config.yaml")
    config = AgentConfigLoader(path=config_path).load()

    runtime = SWEAgentRuntime(config=config)

    # Mock OpenAI client to avoid real API calls
    with patch("sweagent.runtime.AsyncOpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        agent = runtime.build_agent()

        assert agent is not None
        assert agent.name == "swe-agent"
        assert len(agent.tools) == 1  # LocalShellTool
        assert len(agent.mcp_servers) == 1  # MCP filesystem server enabled


@pytest.mark.asyncio
async def test_agent_executes_shell_command():
    """Agent should execute shell commands through Apptainer."""

    config_path = Path(__file__).with_name("test_config.yaml")
    config = AgentConfigLoader(path=config_path).load()

    runtime = SWEAgentRuntime(config=config)

    # Mock subprocess execution
    class DummyProcess:
        returncode = 0

        async def communicate(self):
            return b"Hello from container", b""

    async def fake_subprocess_exec(*args, **kwargs):
        return DummyProcess()

    # Mock OpenAI API response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content="I'll list the files",
                tool_calls=None,
                refusal=None,
            ),
            finish_reason="stop",
        )
    ]

    with patch("sweagent.runtime.AsyncOpenAI") as mock_openai_cls, \
         patch("asyncio.create_subprocess_exec", side_effect=fake_subprocess_exec), \
         patch("sweagent.commands.write_json_log"):

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_cls.return_value = mock_client

        agent = runtime.build_agent()
        run_config = runtime.build_run_config()

        # Verify agent is properly configured
        assert agent.name == "swe-agent"
        assert run_config.max_turns == 3  # From test_config.yaml


@pytest.mark.asyncio
async def test_agent_respects_step_limits():
    """Agent should enforce max_steps from config."""

    config_path = Path(__file__).with_name("test_config.yaml")
    config = AgentConfigLoader(path=config_path).load()

    runtime = SWEAgentRuntime(config=config)
    run_config = runtime.build_run_config()

    assert run_config.max_turns == 3  # Configured in test_config.yaml


@pytest.mark.asyncio
async def test_agent_blocks_dangerous_commands():
    """Executor should reject blocked commands from config."""

    config_path = Path(__file__).with_name("test_config.yaml")
    config = AgentConfigLoader(path=config_path).load()

    from sweagent.commands import ApptainerCommandExecutor, CommandExecutionError
    from agents.tool import LocalShellCommandRequest
    from types import SimpleNamespace

    executor = ApptainerCommandExecutor(
        security=config.security,
        command_config=config.commands,
    )

    # Test blocked command 'rm'
    request = LocalShellCommandRequest(
        ctx_wrapper=MagicMock(),
        data=SimpleNamespace(command="rm -rf /important"),
    )

    with pytest.raises(CommandExecutionError, match="blocked token"):
        await executor(request)

