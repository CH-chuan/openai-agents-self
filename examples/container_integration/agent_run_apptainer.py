"""Run agent-controlled commands inside an Apptainer sandbox.

This example shows how to wire the Agents SDK run context into a tool so that
every tool call executes inside a specific Apptainer container. Adjust the
paths and bindings below to match your local environment before running.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Dict, Iterable

from dotenv import load_dotenv

from agents import Agent, Runner, function_tool

from agents.tool_context import ToolContext
from agents.model_settings import ModelSettings

from openai import AsyncOpenAI
from agents import OpenAIChatCompletionsModel

load_dotenv()

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

@dataclass
class ApptainerContext:
    """Holds per-run configuration for talking to an Apptainer sandbox."""

    sandbox_path: str
    """Path to the writable sandbox directory (created from the .sif image)."""

    binds: Iterable[str] = field(default_factory=list)
    """Optional ``host_path:container_path`` bind mounts passed to Apptainer."""

    env: Dict[str, str] = field(default_factory=dict)
    """Environment variables injected into the container."""

    apptainer_executable: str = "apptainer"
    """Executable name or absolute path for Apptainer."""

    writable: bool = False
    """Whether to add ``--writable`` when launching the container."""


def _build_exec_command(ctx: ApptainerContext, command: str) -> list[str]:
    base: list[str] = [ctx.apptainer_executable, "exec"]

    if ctx.writable:
        base.append("--writable")

    for bind in ctx.binds:
        base.extend(["--bind", bind])

    for key, value in ctx.env.items():
        base.extend(["--env", f"{key}={value}"])

    base.append(ctx.sandbox_path)
    base.extend(["/bin/bash", "-lc", command])
    return base


@function_tool
async def run_in_apptainer(ctx: ToolContext[ApptainerContext], command: str) -> str:
    """Execute a bash command inside the configured Apptainer sandbox."""

    logger.info("Running command in Apptainer: %s", command)
    workdir = "/testbed"
    wrapped_command = f"mkdir -p {workdir} && cd {workdir} && {command}"
    exec_cmd = _build_exec_command(ctx.context, wrapped_command)

    process = await asyncio.create_subprocess_exec(  # type: ignore[arg-type]
        *exec_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await process.communicate()
    output = stdout.decode("utf-8", errors="replace")

    if process.returncode != 0:
        logger.error(
            "Command failed (exit code %s). Output: %s",
            process.returncode,
            output.strip(),
        )
        return (
            f"Command failed with exit code {process.returncode}. Output:\n"
            f"{output.strip()}"
        )

    cleaned_output = output.strip() or "(no output)"
    logger.info("Command succeeded. Output: %s", cleaned_output)
    return cleaned_output


async def main() -> None:
    BASE_URL = os.getenv("VLLM_API_BASE") or ""
    API_KEY = os.getenv("VLLM_API_KEY") or ""
    MODEL_NAME = "Qwen/Qwen3-8B" # os.getenv("VLLM_MODEL_NAME") or ""

    client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)
    model = OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client)

    # Update sandbox_path (and optional binds/env) to match your environment.
    sandbox_root = os.path.abspath("workspaces/matplotlib_sandbox")

    container_ctx = ApptainerContext(
        sandbox_path=sandbox_root,
        # binds=["/workspaces/data:/mnt/data"],
        # env={"PYTHONPATH": "/testbed"},
        writable=True,
    )

    agent = Agent(
        name="Apptainer Operator",
        instructions=(
            "You can execute shell commands inside the configured Apptainer sandbox. "
            "Use the run_in_apptainer tool to inspect files, run Python, or execute "
            "tests inside the container."
        ),
        tools=[run_in_apptainer],
        model=model,
        # model_settings=ModelSettings(tool_choice="required")
    )

    prompt = (
        "List the Python version of the current environment."
        "write a txt file with hello world inside using cat command"
    )

    result = await Runner.run(agent, prompt, context=container_ctx)

    # for response_idx, response in enumerate(result.raw_responses):
    #     logger.info("Agent response %s usage: %s", response_idx, response.usage)
    #     for item_idx, item in enumerate(response.output):
    #         logger.info("Agent response %s item %s: %s", response_idx, item_idx, item)

    # logger.info("Agent final output: %s", result.final_output)
    # print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())

