"""Command execution utilities for routing through Apptainer."""

from __future__ import annotations

import asyncio
import json
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from agents.tool import FunctionTool, LocalShellCommandRequest, ToolContext

from sweagent.config import CommandConfig, SecurityConfig
from sweagent.logging import logger, write_json_log


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
    
    def to_function_tool(self) -> FunctionTool:
        """Convert this executor to a FunctionTool for ChatCompletions API.
        
        This allows LocalShellTool-like functionality to work with models
        that only support the ChatCompletions API (like VLLM).
        """
        async def shell_function(ctx: ToolContext[Any], command: str) -> str:
            """Execute a shell command in the Apptainer container.
            
            Args:
                command: The shell command to execute
                
            Returns:
                The command output (stdout), or stdout + stderr if stderr is non-empty
            """
            # Create a LocalShellCommandRequest-like object
            from types import SimpleNamespace
            request = LocalShellCommandRequest(
                ctx_wrapper=ctx.run_context,
                data=SimpleNamespace(command=command),
            )
            return await self(request)
        
        # Create schema for the command parameter
        params_schema = {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute in the container",
                }
            },
            "required": ["command"],
            "additionalProperties": False,
        }
        
        async def on_invoke(ctx: ToolContext[Any], args_json: str) -> Any:
            args = json.loads(args_json)
            return await shell_function(ctx, args["command"])
        
        return FunctionTool(
            name="local_shell",
            description="Execute a shell command in the Apptainer container. Use this to run bash commands, list files, read files, write files, compile code, run tests, etc.",
            params_json_schema=params_schema,
            on_invoke_tool=on_invoke,
            strict_json_schema=True,
        )

