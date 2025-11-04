# Apptainer Integration Example

This example shows how to pass per-run configuration (path, bind mounts, env) to
an Agents SDK tool so that every tool call executes inside an Apptainer
container based on the `swebench_instances/images/matplotlib_1776_matplotlib-24149.sif`
image.

## 1. Build the sandbox

```
# Create a writable sandbox directory from the supplied .sif image
apptainer build --sandbox workspaces/matplotlib_sandbox \
  swebench_instances/images/matplotlib_1776_matplotlib-24149.sif
```

## 2. (Optional) Prepare bind mounts

Create any directories you want to mount into the sandbox. In the example we
bind `/host/data` to `/mnt/data`.

```
mkdir -p /host/data
```

## 3. Configure environment variables if you use a self-hosted model

Point the OpenAI client at your vLLM deployment (compatible with the OpenAI
client API) and supply an API key/token.

```
export OPENAI_BASE_URL="https://YOUR-VLLM-ENDPOINT/v1"
export OPENAI_API_KEY="not-used-but-required"
```

## 4. Review and update the example context

Edit `examples/container_integration/1.py` and change:

- `sandbox_path` to the sandbox directory from step 1.
- `binds` to any `host:container` mounts you need.
- `env` to environment variables required inside the container.
- `model` if you want a different model name.

The context object you pass to `Runner.run` is wrapped automatically and handed
to every tool invocation as a `ToolContext`. `run_in_apptainer` uses that context
to build `apptainer exec` commands, so the LLM never sees your paths or secrets.

## 5. Run the example

```
uv run python examples/container_integration/1.py
```

The script creates an agent with a single tool (`run_in_apptainer`). When the
model decides to inspect the environment, the tool executes the requested shell
commands inside the sandbox and returns the output back through the normal tool
response flow.

## 6. Next steps

- Add more tools (e.g. file upload/download) that read from the same context.
- Toggle the `writable` flag if you need to modify the sandbox.
- Use guardrails or hooks to restrict which commands the model can run; they
  receive the same `ToolContext` and can enforce policies before execution.

