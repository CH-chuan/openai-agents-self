# SWE Agent Setup Guide 7 Problems to Solve

This guide walks you through setting up and testing the SWE Agent with MCP server integration.

## Prerequisites

- Python 3.8+
- Node.js 20.x LTS
- Apptainer/Singularity

## Setup Instructions

### 1. Python Environment Setup

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Apptainer Image Setup

Build the test instance image:

```bash
python swebench_instances/build_test_instance.py
```

Verify the image works correctly:

```bash
apptainer shell swebench_instances/images/swebench_sweb.eval.x86_64.astropy_1776_astropy-12907.sif
cd /testbed  # Should enter the image root path containing a repo with a bug
```

### 3. MCP Server Setup

We use the official filesystem MCP server for testing.

#### 3a. Install Node.js (if not already installed)

```bash
# Download and run the setup script for Node.js 20.x LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -

# Install Node.js (includes npm and npx)
sudo apt-get install -y nodejs

# Verify installation
node --version    # Should show v20.x.x
npm --version     # Should show 10.x.x
npx --version     # Should show 10.x.x
```

Test the installation:

```bash
# Create a test directory
cd /tmp
mkdir node-test && cd node-test

# Initialize package.json
npm init -y

# Install a test package
npm install lodash

# Test npx
npx cowsay "Node.js is installed!"
```

#### 3b. Install Filesystem MCP Server

```bash
cd ~/projects/openai-agents-self

# Create MCP servers directory
mkdir -p mcp-servers/filesystem
cd mcp-servers/filesystem

# Initialize and install the filesystem server
npm init -y
npm install @modelcontextprotocol/server-filesystem
```

### 4. Run Component Tests

Execute the test suite to verify all components work correctly:

```bash
./run_sweagent_tests.sh
```

At this point, all components should be functioning properly.

---

## Known Issues and Work in Progress

### 5. Agent Loop Testing

**Current Status:** Not fully functional

#### Running the Agent

```bash
python sweagent/cli.py \
    --agent-config sweagent/agent_config.yaml \
    --task-config swebench_instances/task_config.yaml
```

#### Identified Issues

##### Issue 6.1: vLLM Compatibility with OpenAI Chat Completions API

The current implementation uses vLLM to host `openai/gpt-oss-20b`, which has compatibility issues with the OpenAI Chat Completions format.

**Problem:** The agent execution logic checks `processed_response.has_tools_or_approvals_to_run()`, which returns `False` when there are no tool calls to process, causing execution to stop prematurely. However, here should be a rety mechanism, allowing agent to rety for certain max_num, with each time notify the agent the tool call is not activated successfully.

While the root cause of tool call not being successful are described below:

**Example Raw Response** (from `src/agents/models/openai_chatcompletions.py` lines 99-110):

```python
ChatCompletion(
    id='chatcmpl-c538d97b02b84093aeed371c7e22dd99',
    choices=[Choice(
        finish_reason='stop',
        index=0,
        message=ChatCompletionMessage(
            content='{"path": "", "depth": 3}\n',
            role='assistant',
            tool_calls=[],
            reasoning_content="We need to fix bug in matplotlib ax.bar for all-nan data..."
        )
    )],
    model='openai/gpt-oss-20b',
    usage=CompletionUsage(completion_tokens=63, prompt_tokens=1489, total_tokens=1552)
)
```

**Root Causes:**

1. **Reasoning Content Handling**: The `gpt-oss-20b` model uses `reasoning_content`, which is not properly parsed by the current implementation. This content should either:
   - Be handled through modified reasoning parameters (requires deeper compatibility investigation)
   - Be merged into the main `content` field (requires careful context management for agent self-loops)

2. **Incomplete Tool Call Information**: The response only contains `'{"path": "", "depth": 3}\n'` in the content field, suggesting that:
   - Tool call formatting may be stripped by vLLM's internal processing
   - The raw response may not be truly "raw" and requires further investigation

3. **Tool Input Format**: The method of passing tool definitions to vLLM (via tool parameters) needs verification to ensure:
   - Tool information is properly added to the model's context
   - The LLM can correctly understand and use the available tools

##### Issue 6.2: Retry Logic for Failed Tool Calls

**Required Feature:** Implement retry logic that allows the agent to attempt tool calls multiple times when they fail, rather than stopping execution immediately.

### Next Steps

1. **Investigate vLLM Compatibility**: 
   - Check how vLLM processes and formats tool calls internally
   - Compare input/output patterns between vLLM and OpenAI's official API
   - Test with different models to understand model-specific formatting

2. **Standardize Tool Call Handling**:
   - Ensure tool definitions are properly communicated to the model
   - Verify that tool call responses follow expected formats
   - Create adapters for different model providers if needed

3. **Implement Retry Logic**:
   - Add configurable retry attempts for failed tool calls
   - Improve error handling and logging

4. **Model-Specific Testing Protocol**:
   - Establish a standard procedure for testing new models
   - Document compatibility requirements and known issues
   - Create model-specific configuration templates

### Vision

Once these compatibility issues are resolved, the pipeline will be complete with MCP server integration, making future development more streamlined. All subsequent work will focus on:

- Prompt engineering and optimization
- Adapting data formats to OpenAI Chat Completions standard
- Adding new capabilities through MCP servers
