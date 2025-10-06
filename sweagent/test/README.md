# SWE-Agent Tests

## Overview

Tests for the SWE-agent runtime components.

## Test Files

### `test_commands.py`

Validates the Apptainer command executor builds correct shell invocations.

**What it tests:**
- Configuration loading from YAML
- Command wrapping with `apptainer exec`
- Bind mount arguments (`--bind`)
- Working directory setup (`--pwd`)
- Container image path resolution
- Bash execution wrapper (`/bin/bash -lc`)

**Mock strategy:**
- Intercepts `asyncio.create_subprocess_exec` to capture argv
- Verifies argument order matches Apptainer CLI expectations
- Skips actual container execution

### `test_agent.py`

Integration tests for the complete agent runtime and execution flow.

**What it tests:**
- Agent construction from config (runtime assembly)
- OpenAI client integration (mocked)
- Shell tool registration and availability
- Step limit enforcement from config
- Security blocking of dangerous commands
- Optional MCP server handling

**Mock strategy:**
- Mocks OpenAI API responses to avoid real model calls
- Mocks subprocess execution for container isolation
- Validates end-to-end agent workflow without external dependencies

### `test_real_model.py`

**Live model integration tests** - requires real API credentials.

**What it tests:**
- Real communication with hosted model endpoint
- Agent orchestration with live model calls
- Tool calling through the agent framework
- End-to-end workflow with real model responses

**Requirements:**
- `VLLM_API_KEY` environment variable
- `VLLM_API_BASE` environment variable
- Running model endpoint

**Mock strategy:**
- Mocks only Apptainer container execution (no .sif needed)
- All model communication is real
- Tests are skipped if credentials not available

### `test_config.yaml`

Minimal configuration for test scenarios. Includes model settings, security blocks, step limits, and container paths. MCP section is commented out to test optional MCP handling. Does not require real API keys or `.sif` images to run.

## Running Tests

### Unit and Integration Tests (mocked)

```bash
# Set PYTHONPATH to project root
export PYTHONPATH=/home/cche/projects/openai-agents-self

# All mocked tests
pytest sweagent/test/test_commands.py sweagent/test/test_agent.py -v

# Single test file
pytest sweagent/test/test_commands.py
pytest sweagent/test/test_agent.py

# With output
pytest -s sweagent/test/test_commands.py
```

### Real Model Tests (requires API credentials)

```bash
# Set API credentials and PYTHONPATH
export VLLM_API_KEY="your-api-key"
export VLLM_API_BASE="http://your-endpoint:8000/v1"
export PYTHONPATH=/home/cche/projects/openai-agents-self

# Run real model tests with verbose output
pytest sweagent/test/test_real_model.py -s -v

# Skip real model tests
pytest sweagent/test/ -v -k "not real_model"
```

**Requirements:**
- `pytest-asyncio` plugin (installed via dev dependencies)
- `PYTHONPATH` must include project root for imports to work
- Real model tests require `VLLM_API_KEY` and `VLLM_API_BASE` environment variables

