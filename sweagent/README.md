# SWE-Agent

This directory contains an MVP implementation of a SWE-bench focused agent built on top of the OpenAI Agents SDK. The agent is configured via YAML, executes all bash commands through Apptainer, and integrates the official filesystem MCP server.

## Layout Overview

- `build_plan.md` – High-level implementation plan and priorities for the MVP.
- `config.py` – Data structures and parsing logic for the YAML configuration file. Validates model credentials, security settings, MCP options, Apptainer command settings, and prompt templates.
- `config.yaml` – Sample configuration showing how to wire model settings, command limits, MCP allowlisting, and container details.
- `commands.py` – Implements the Apptainer-backed shell executor. All local shell calls are wrapped in `apptainer exec`, blocked commands are enforced, and tool invocations are logged to `logs/sweagent_tools.jsonl`.
- `logging.py` – Central logging helpers. Provides a module logger (`sweagent`), a basic stdout handler, and `write_json_log` for appending structured tool/MCP events.
- `mcp.py` – Factory for the filesystem MCP server. Creates an `MCPServerStdio` instance with allowlisted tools and records initialization metadata to `logs/sweagent_mcp.jsonl`.
- `runtime.py` – Assembles the runtime by loading logging, constructing the Apptainer command tool, wiring the filesystem MCP server, initializing the OpenAI client, and building the configured `Agent` with model limits applied.
- `runner.py` – Thin wrapper that loads configuration from disk, builds the runtime, and invokes the default agent runner with the configured step limits. Adds log entries for the start and end of each run.
- `__init__.py` – Exposes the primary objects (`SWEAgentConfig`, `AgentConfigLoader`, `SWEAgentRunner`) for external consumers.

## Running the Agent

1. Update `config.yaml` with your model credentials, MCP server path, and Apptainer image.
2. Ensure the `.sif` image and bind mounts referenced in the config exist.
3. Provide SWE-bench inputs to `SWEAgentRunner` (e.g., through a custom harness or script) and call `await runner.run(task_input)`.
4. Inspect `logs/` for tool execution records and MCP server events.

## Notes

- The agent only executes commands inside Apptainer and respects `blocked_commands` from the YAML configuration.
- MCP tool exposure is controlled through the `tool_allowlist` section of the config.
- Additional validation, testing, and documentation hooks can be added on top of this MVP as needed.

