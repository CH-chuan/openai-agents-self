## Wrapping Tool Execution with Context

This document walks through how `agent_run_apptainer.py` wires a custom context into a tool so every command executes inside a specific Apptainer sandbox. The same pattern applies to any resource you want tool calls to share (databases, SDK clients, feature flags, etc.).

- **Use case:** give tools controlled access to external systems without exposing credentials directly to the model.
- **Key pieces:** a context dataclass, a `ToolContext` argument inside your tool, and passing the context to `Runner.run()`.

### 1. Define a Context Object

Start by collecting the per-run configuration you need. In the Apptainer example this is the sandbox path, bind mounts, environment variables, and the Apptainer executable itself.

```python
@dataclass
class ApptainerContext:
    sandbox_path: str
    binds: Iterable[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    apptainer_executable: str = "apptainer"
    writable: bool = False
```

Create an instance and pass it to the agent when you start a run:

```python
container_ctx = ApptainerContext(
    sandbox_path=os.path.abspath("workspaces/matplotlib_sandbox"),
    writable=True,
)

result = await Runner.run(agent, prompt, context=container_ctx)
```

> The context object never goes to the LLM. It is only available to your Python code.

### 2. Accept `ToolContext` in Your Tool

Decorate your tool with `@function_tool` and type the first argument as `ToolContext[ApptainerContext]`. The SDK fills in the wrapper when the model chooses the tool. 

Notice: the tool name run_in_apptainer will be directly inject into agent's memory.

During implementation, you may simply want to set the tool name to bash_command, rather than run_in_apptainer. Because generally you do not need to let your agent know the specific container it is using.

```python
@function_tool
async def run_in_apptainer(ctx: ToolContext[ApptainerContext], command: str) -> str:
    ...
```

`ToolContext` gives you two groups of data:

- `ctx.context`: the exact `ApptainerContext` you passed to `Runner.run()`.
- Metadata about the call (`ctx.tool_name`, `ctx.tool_call_id`, `ctx.tool_arguments`) that you can use for logging or enforcing policies.

### 3. Use the Context to Wrap Execution

Inside the tool, read the context and build whatever command or client you need. The Apptainer tool assembles the container invocation, enforces a working directory, and runs the model's command inside the sandbox.

```python
exec_cmd = _build_exec_command(ctx.context, wrapped_command)
process = await asyncio.create_subprocess_exec(*exec_cmd, ...)
```

Because every tool call goes through the same helper, the model cannot bypass the sandbox or change the execution binary.

### 4. Why the Wrapper Matters

Internally, `ToolContext` inherits from `RunContextWrapper` (`src/agents/run_context.py`). The wrapper tracks the run's `usage` and ensures the context object is always available when tools execute, without leaking it to the LLM. You can extend your dataclass with more dependencies (database sessions, API keys, adapters) and all `ToolContext`-decorated tools will share them safely.

### 5. Generalising the Pattern

- Define one dataclass per environment or dependency graph you want the agent to use.
- Pass the appropriate context instance to `Runner.run()` (or inject it in callbacks).
- Annotate your tools with `ToolContext[YourContext]` so static type checkers know what is available.
- Use the metadata on `ToolContext` to implement auditing, rate limiting, or guardrails per tool invocation.

Following this approach keeps sensitive configuration under your control while still giving the agent the power to act through tools.

