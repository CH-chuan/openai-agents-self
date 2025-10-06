"""Tests for Apptainer-based command execution in the SWE-agent runtime."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from agents.tool import LocalShellCommandRequest

from sweagent.commands import ApptainerCommandExecutor
from sweagent.config import AgentConfigLoader


@pytest.mark.asyncio
async def test_local_shell_command_executes_successfully(monkeypatch):
    """Executor should invoke apptainer with the expected arguments."""

    config_path = Path(__file__).with_name("test_config.yaml")
    config = AgentConfigLoader(path=config_path).load()

    executor = ApptainerCommandExecutor(
        security=config.security,
        command_config=config.commands,
    )

    captured_call: dict[str, object] = {}

    class DummyProcess:
        returncode = 0

        async def communicate(self):
            return b"command output", b""

    async def fake_create_subprocess_exec(*args, **kwargs):
        captured_call["args"] = args
        captured_call["kwargs"] = kwargs
        return DummyProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    monkeypatch.setattr("sweagent.commands.write_json_log", MagicMock())

    request = LocalShellCommandRequest(
        ctx_wrapper=MagicMock(),
        data=SimpleNamespace(command="ls"),
    )

    result = await executor(request)

    assert result == "command output"
    assert captured_call["args"] == (
        "apptainer",
        "exec",
        "--bind",
        "/host/data:/workspace/data",
        "--bind",
        "/host/cache:/workspace/.cache",
        "--pwd",
        "/testbed",
        "swebench_instances/images/swebench_sweb.eval.x86_64.astropy_1776_astropy-12907.sif",
        "/bin/bash",
        "-lc",
        "ls",
    )
    assert captured_call["kwargs"] == {
        "stdout": asyncio.subprocess.PIPE,
        "stderr": asyncio.subprocess.PIPE,
    }

