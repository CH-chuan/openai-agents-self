# SWE Agent Setup Guide for HPC Environment

This guide walks you through setting up and testing the SWE Agent with MCP server integration on HPC systems.

## Setup Instructions

### 1. Python Environment Setup

Load the miniforge module and create a virtual environment:

```bash
# Load miniforge to enable venv
module load miniforge

# Create and activate a virtual environment
conda create -n sweagent python=3.10
conda activate sweagent
```

**Important:** Before installing dependencies, you need to modify `requirements.txt`:

```bash
# Remove the version specification from backports.asyncio.runner
# Change: backports.asyncio.runner==x.x.x
# To:     backports.asyncio.runner
sed -i 's/backports\.asyncio\.runner==.*/backports.asyncio.runner/' requirements.txt
```

Then install dependencies:

```bash
pip install -r requirements.txt
```

### 2. Apptainer Image Setup

**Important:** Building containers requires significant memory. Request an interactive job before building:

```bash
# Request an interactive job with sufficient memory
# Replace <your_account> with your actual HPC account/allocation
ijob -A jingjing_lab -p interactive --mem=50G
```

Once your interactive job starts, load the apptainer module and build the test instance image:

```bash
# Load apptainer module
module load apptainer

# Build the test instance image
python swebench_instances/build_test_instance.py
```

**Note:** The generated `.sif` filename may be shorter than shown in the documentation. Look for the actual filename in the `swebench_instances/images/` directory.

Verify the image works correctly:

```bash
# Use the actual .sif filename from your images directory
apptainer shell swebench_instances/images/<your_image_name>.sif
cd /testbed  # Should enter the image root path containing a repo with a bug
exit  # Exit the container after verification
```

### 3. MCP Server Setup

We use the official filesystem MCP server for testing.

#### 3a. Load Node.js Module

Instead of installing Node.js manually, use the HPC module system:

```bash
# Load the Node.js module (v24.5.0)
module load nodejs

# Verify installation
node --version    # Should show v24.5.0
npm --version
npx --version
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

Deploy model by vLLM:
```bash
pip isntall vllm
vllm serve openai/gpt-oss-20b
```

Set .env file by including"
```
VLLM_API_KEY="api-key-not-required"
VLLM_API_BASE="http://0.0.0.0:8000/v1"
```

Execute the test suite to verify all components work correctly:

```bash
# Make sure you're in an interactive job or on a compute node
./run_sweagent_tests.sh
```

At this point, all components should be functioning properly.

---

## HPC Environment Tips

### Module Loading Best Practices

To avoid repeatedly loading modules, you can add them to your shell configuration:

```bash
# Add to ~/.bashrc or ~/.bash_profile
module load miniforge
module load apptainer
module load nodejs
```

### Resource Requirements

- **Frontend nodes**: Suitable for light tasks (editing, small tests)
- **Interactive jobs**: Required for building containers and running agent tests
  - Minimum memory: 50G
  - Recommended for development and testing
- **Batch jobs**: Best for production runs and multiple experiments

### Common Issues

1. **Container build fails**: Make sure you're running on an interactive job with sufficient memory (≥50G)
2. **Module not found**: Check available modules with `module avail <module_name>`
3. **Permission issues**: Ensure you have write access to the project directory
4. **SIF file not found**: Check the actual filename in `swebench_instances/images/` directory

---

## Known Issues and Work in Progress

### 5. Agent Loop Testing

**Current Status:** Not fully functional

#### Running the Agent

```bash
# Make sure you're in an interactive job with sufficient resources
python sweagent/cli.py \
    --agent-config sweagent/agent_config.yaml \
    --task-config swebench_instances/task_config.yaml
```

#### Identified Issues

##### Issue 6.1: vLLM Compatibility with OpenAI Chat Completions API

The current implementation uses vLLM to host `openai/gpt-oss-20b`, which has compatibility issues with the OpenAI Chat Completions format.

**Problem:** The agent execution logic checks `processed_response.has_tools_or_approvals_to_run()`, which returns `False` when there are no tool calls to process, causing execution to stop prematurely. However, here should be a retry mechanism, allowing agent to retry for certain max_num, with each time notify the agent the tool call is not activated successfully.

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

