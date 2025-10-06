"""Command execution utilities for routing through Apptainer."""

from __future__ import annotations

import asyncio
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from agents.tool import LocalShellCommandRequest

from .config import CommandConfig, SecurityConfig
from .logging import logger, write_json_log


class CommandExecutionError(RuntimeError):
    """Raised when an Apptainer execution fails."""


@dataclass
class ApptainerCommandExecutor:
    """Executes commands through Apptainer based on configuration."""

    security: SecurityConfig
    command_config: CommandConfig

    async def __call__(self, request: LocalShellCommandRequest) -> str:
        command_line = request.data.command
        self._assert_not_blocked(command_line)

        argv = self._build_apptainer_argv(command_line)
        process = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await process.communicate()

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")

        if process.returncode != 0:
            logger.error(
                "Apptainer command failed",
                extra={
                    "payload": {
                        "tool": "local_shell",
                        "command": command_line,
                        "argv": argv,
                        "returncode": process.returncode,
                    }
                },
            )
            write_json_log(
                Path("logs/sweagent_tools.jsonl"),
                {
                    "tool": "local_shell",
                    "command": command_line,
                    "argv": argv,
                    "returncode": process.returncode,
                    "stdout": "[redacted]",
                    "stderr": "[redacted]",
                },
            )
            raise CommandExecutionError(
                f"Apptainer command failed with exit code {process.returncode}: {stderr.strip()}"
            )

        success_payload = {
            "tool": "local_shell",
            "command": command_line,
            "argv": argv,
            "returncode": process.returncode,
            "stdout": stdout,
            "stderr": stderr,
        }
        write_json_log(Path("logs/sweagent_tools.jsonl"), success_payload)

        if stderr:
            return f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}"
        return stdout

    def _assert_not_blocked(self, command_line: str) -> None:
        tokens = shlex.split(command_line, posix=True)
        for token in tokens:
            if token in self.security.blocked_commands:
                logger.warning("Blocked command token detected", extra={"token": token})
                raise CommandExecutionError(
                    f"Command contains blocked token '{token}'."
                )

    def _build_apptainer_argv(self, command_line: str) -> list[str]:
        base: list[str] = [
            "apptainer",
            "exec",
        ]
        base.extend(self._format_bind_mounts(self.command_config.bind_mounts))
        if self.command_config.working_directory:
            base.extend(["--pwd", str(self.command_config.working_directory)])
        for key, value in self.command_config.env.items():
            base.extend(["--env", f"{key}={value}"])
        base.append(str(self.command_config.apptainer_image))
        base.extend(["/bin/bash", "-lc", command_line])
        return base

    @staticmethod
    def _format_bind_mounts(bind_mounts: Sequence[str]) -> Iterable[str]:
        for mount in bind_mounts:
            yield "--bind"
            yield mount

