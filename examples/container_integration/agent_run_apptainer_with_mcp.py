"""Use the filesystem MCP server to interact with files in an Apptainer sandbox.

This example demonstrates using the ``@modelcontextprotocol/server-filesystem`` MCP
server to perform file operations on an Apptainer sandbox directory. The MCP server
runs on the host and accesses the sandbox files directly (since Apptainer sandboxes
are just directories on the host filesystem).

The agent uses MCP filesystem tools (read_file, write_file, etc.) to:
1. Read README.md from the sandbox testbed
2. Append a new line to hello.txt

Note: MCP tools run in a separate process (via npx) and do NOT have access to the
agent's run_context. The filesystem server operates directly on host paths.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil

from dotenv import load_dotenv
from openai import AsyncOpenAI

from agents import Agent, OpenAIChatCompletionsModel, Runner
from agents.mcp import MCPServerStdio, MCPServerStdioParams

load_dotenv()

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def _build_filesystem_server_params(testbed_host_path: str) -> MCPServerStdioParams:
    """Return parameters for spawning the filesystem MCP server via npx.

    IMPORTANT: The MCP filesystem server resolves relative paths from the cwd where
    the server process is spawned. We set cwd to the testbed directory so that paths
    like "README.md" resolve correctly within the allowed directory.
    """

    if not shutil.which("npx"):
        raise RuntimeError("npx is not installed. Install Node.js and npm so npx is available.")

    # The filesystem server takes the allowed directory as a positional argument
    # AND we set the cwd to the same directory so relative paths resolve correctly
    return MCPServerStdioParams(
        command="npx",
        args=[
            "-y",
            "@modelcontextprotocol/server-filesystem",
            testbed_host_path,
        ],
        cwd=testbed_host_path,  # Critical: set cwd to testbed for path resolution
    )


async def main() -> None:
    base_url = os.getenv("VLLM_API_BASE") or ""
    api_key = os.getenv("VLLM_API_KEY") or ""
    model_name = os.getenv("VLLM_MODEL_NAME") or "Qwen/Qwen3-8B"

    client = AsyncOpenAI(base_url=base_url, api_key=api_key)
    model = OpenAIChatCompletionsModel(model=model_name, openai_client=client)

    # The sandbox is just a directory on the host filesystem
    sandbox_root = os.path.abspath("workspaces/matplotlib_sandbox")
    testbed_host_path = os.path.join(sandbox_root, "testbed")

    if not os.path.isdir(testbed_host_path):
        raise RuntimeError(
            f"Expected to find a 'testbed' directory at {testbed_host_path}. "
            "Create it or adjust the path before running this example."
        )

    # Point the MCP filesystem server at the testbed directory on the host
    filesystem_server_params = _build_filesystem_server_params(testbed_host_path)

    async with MCPServerStdio(
        name="Filesystem MCP Server",
        params=filesystem_server_params,
    ) as filesystem_server:
        agent = Agent(
            name="File Operations Agent",
            instructions=(
                "You are an agent that can read and modify files using the MCP filesystem "
                "tools. All file paths are relative to the root directory exposed by the "
                "MCP server."
            ),
            mcp_servers=[filesystem_server],
            model=model,
        )

        prompt = (
            "First, read the README.md file to understand what's in it. "
            "Then, append a new line containing exactly 'from agent test' to the hello.txt file. "
            "Use the write_file tool to perform the append operation."
        )

        result = await Runner.run(agent, prompt)
        logger.info("Agent final output: %s", result.final_output)
        print("\n" + "=" * 60)
        print("FINAL OUTPUT:")
        print("=" * 60)
        print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
