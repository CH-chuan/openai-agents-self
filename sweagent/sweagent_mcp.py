"""Utilities for configuring filesystem MCP server instances."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agents.mcp.server import MCPServerStdio, MCPServerStdioParams

from sweagent.config import MCPConfig
from sweagent.sweagent_logging import logger, write_json_log


@dataclass
class MCPServerFactory:
    """Constructs MCP server instances from configuration."""

    config: MCPConfig

    def create(self) -> MCPServerStdio:
        params: MCPServerStdioParams = {
            "command": str(self.config.path),
            "args": ["."],  # Allow access to the current directory
            "env": self.config.env,
        }
        server = MCPServerStdio(
            params=params,
            cache_tools_list=True,
            name="filesystem",
            use_structured_content=self.config.use_structured_content,
        )
        if self.config.tool_allowlist:
            server.tool_filter = {"allowed_tool_names": self.config.tool_allowlist}
        write_json_log(
            Path("logs/sweagent_mcp.jsonl"),
            {
                "event": "mcp_server_initialized",
                "path": str(self.config.path),
                "tool_allowlist": self.config.tool_allowlist,
            },
        )
        logger.info(
            "Filesystem MCP server configured",
            extra={
                "path": str(self.config.path),
                "allowed_tools": self.config.tool_allowlist,
            },
        )
        return server

