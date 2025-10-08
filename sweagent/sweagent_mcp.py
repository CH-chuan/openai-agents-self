"""Utilities for configuring filesystem MCP server instances."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from agents.mcp.server import MCPServerStdio, MCPServerStdioParams

from sweagent.config import MCPConfig
from sweagent.sweagent_logging import logger, write_json_log
from sweagent.workspace import WorkspaceInfo


@dataclass
class MCPServerFactory:
    """Constructs MCP server instances from configuration."""

    config: MCPConfig
    workspace_info: Optional[WorkspaceInfo] = None

    def create(self) -> MCPServerStdio:
        # Determine MCP server allowed directory
        if self.workspace_info:
            # Use workspace testbed directory (same as container sees)
            mcp_args = [str(self.workspace_info.testbed_dir.absolute())]
            allowed_dir = str(self.workspace_info.testbed_dir.absolute())
        else:
            # Fallback to current directory
            mcp_args = ["."]
            allowed_dir = "."
        
        params: MCPServerStdioParams = {
            "command": str(self.config.path),
            "args": mcp_args,
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
                "allowed_directory": allowed_dir,
                "tool_allowlist": self.config.tool_allowlist,
                "workspace_based": self.workspace_info is not None,
            },
        )
        logger.info(
            "Filesystem MCP server configured",
            extra={
                "path": str(self.config.path),
                "allowed_directory": allowed_dir,
                "allowed_tools": self.config.tool_allowlist,
                "workspace_based": self.workspace_info is not None,
            },
        )
        return server

