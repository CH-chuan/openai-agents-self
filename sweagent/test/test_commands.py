"""Tests for Apptainer-based command execution in the SWE-agent runtime."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from agents.tool import FunctionTool

from sweagent.commands import ApptainerCommandExecutor
from sweagent.config import AgentConfigLoader


@pytest.mark.asyncio
async def test_apptainer_command_executor_creates_function_tool():
    """Executor should create a FunctionTool that can be used by the agent."""

    config_path = Path(__file__).with_name("test_config.yaml")
    config = AgentConfigLoader(path=config_path).load()

    executor = ApptainerCommandExecutor(
        security=config.security,
        command_config=config.commands,
    )

    # Test that the executor can create a function tool
    function_tool = executor.to_function_tool()
    
    assert isinstance(function_tool, FunctionTool)
    assert function_tool.name == "local_shell"
    assert function_tool.description is not None
    assert "command" in function_tool.params_json_schema["properties"]

