# Apptainer Integration Examples

This directory contains two examples showing different approaches to working with Apptainer containers:

1. **`agent_run_apptainer.py`**: Custom tool with `ToolContext` for executing shell commands inside containers
2. **`agent_run_apptainer_with_mcp.py`**: MCP filesystem server for file operations on container directories

## Prerequisites

### 1. Build the sandbox

Both examples use the same Apptainer sandbox:

```bash
# Create a writable sandbox directory from the supplied .sif image
apptainer build --sandbox workspaces/matplotlib_sandbox \
  swebench_instances/images/matplotlib_1776_matplotlib-24149.sif
```

### 2. Configure environment variables

For self-hosted models (e.g., vLLM):

```bash
export VLLM_API_BASE="https://YOUR-VLLM-ENDPOINT/v1"
export VLLM_API_KEY="your-api-key"
export VLLM_MODEL_NAME="Qwen/Qwen3-8B"
```

Or for OpenAI:

```bash
export OPENAI_API_KEY="your-openai-api-key"
```

---

## Example 1: Custom Tool with ToolContext (`agent_run_apptainer.py`)

This example shows how to pass per-run configuration (path, bind mounts, env) to
a custom tool so that shell commands execute inside an Apptainer container.

### How it works

- Defines an `ApptainerContext` dataclass with sandbox configuration
- Creates a custom `run_in_apptainer` tool that accepts `ToolContext[ApptainerContext]`
- The tool wraps commands with `apptainer exec` to run inside the container
- The agent's `run_context` is passed to the tool but never exposed to the LLM

### Key concepts

- **`ToolContext`**: Provides access to the run context in tool implementations
- **Run context isolation**: Configuration stays in Python; LLM only sees tool signatures
- **Container execution**: Commands run inside the container via `apptainer exec`

### Run the example

```bash
python examples/container_integration/agent_run_apptainer.py
```

### Customization

Edit the script to change:
- `sandbox_path`: Path to your sandbox directory
- `binds`: Host-to-container bind mounts (e.g., `["/host/data:/mnt/data"]`)
- `env`: Environment variables injected into the container
- `writable`: Whether to allow writes to the sandbox

### When to use this approach

✅ **Use custom tools with `ToolContext` when you need:**
- Execute commands **inside** a container (not just access files)
- Inject custom context (credentials, database sessions, API clients)
- Implement guardrails or policies based on the execution context
- Audit logging per tool invocation

---

## Example 2: MCP Filesystem Server (`agent_run_apptainer_with_mcp.py`)

This example uses the Model Context Protocol (MCP) filesystem server to perform
file operations on an Apptainer sandbox directory. Since Apptainer sandboxes are
just directories on the host, the MCP server can access them directly without
container execution.

### Prerequisites (Additional)

Install the MCP filesystem server:

```bash
cd ~/projects/openai-agents-self

# Create MCP servers directory
mkdir -p mcp-servers/filesystem
cd mcp-servers/filesystem

# Initialize and install the filesystem server
npm init -y
npm install @modelcontextprotocol/server-filesystem
```

### How it works

- The MCP filesystem server runs as a separate process via `npx`
- It's configured with the sandbox's testbed directory as the allowed directory
- The agent uses MCP tools (`read_file`, `write_file`, etc.) for file operations
- **Important**: MCP tools do NOT receive the agent's `run_context`

### Key concepts

- **MCP server isolation**: Runs in a separate process; no access to run context
- **Path resolution**: Setting `cwd` to the testbed ensures paths resolve correctly
- **Security boundary**: The allowed directory restricts access to the sandbox
- **Direct host access**: No container execution needed for file operations

### Run the example

```bash
python examples/container_integration/agent_run_apptainer_with_mcp.py
```

The agent will:
1. Read `README.md` from `workspaces/matplotlib_sandbox/testbed/`
2. Write a line to `hello.txt` in the same directory

### Critical implementation detail

The MCP filesystem server resolves paths from its **current working directory**, not just the allowed directory. Therefore, we must set `cwd` to the testbed:

```python
MCPServerStdioParams(
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", testbed_host_path],
    cwd=testbed_host_path,  # Critical for correct path resolution
)
```

### When to use this approach

✅ **Use MCP filesystem server when you need:**
- Standard file operations (read, write, edit, list, search)
- Access to files on the host filesystem (including sandbox directories)
- A standardized, well-tested filesystem interface
- File operations without custom execution context

❌ **Don't use MCP filesystem server when you need:**
- Execute commands inside a container
- Pass custom context or configuration to tools
- Implement context-aware guardrails or policies

---

## Comparison: Custom Tools vs MCP

| Feature | Custom Tool (`ToolContext`) | MCP Filesystem Server |
|---------|----------------------------|----------------------|
| **Execution** | Inside container via `apptainer exec` | Host filesystem access |
| **Run context** | ✅ Has access to `ToolContext` | ❌ No access to run context |
| **Use case** | Shell commands, tests, builds | File read/write/edit |
| **Setup** | Define tool function | Install MCP server via npm |
| **Security** | Context-aware policies | Directory-based restrictions |

---

## Combining Both Approaches

You can use both patterns together in a single agent:

```python
agent = Agent(
    name="Hybrid Agent",
    instructions="Use MCP tools for file operations and run_in_apptainer for tests.",
    tools=[run_in_apptainer],        # Custom tool with ToolContext
    mcp_servers=[filesystem_server],  # MCP tools (no context access)
    model=model,
)
```

This gives you:
- **MCP filesystem tools** for file I/O on the host
- **Custom container tool** for running tests inside the container

---

## Additional Resources

- [Tool Context Walkthrough](./tool_context_walkthrough.md) - Detailed guide on using `ToolContext`
- [MCP Filesystem Server](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem) - Official documentation
- [Model Context Protocol](https://spec.modelcontextprotocol.io/) - MCP specification

