"""Configuration parsing for the SWE-agent YAML specification."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, MutableMapping

import yaml


class ConfigError(RuntimeError):
    """Raised when the SWE-agent configuration file is invalid."""


@dataclass
class ModelConfig:
    """Model configuration loaded from YAML."""

    name: str
    api_key: str | None = None
    api_base: str | None = None
    temperature: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityConfig:
    """Security settings for the agent runtime."""

    blocked_commands: list[str] = field(default_factory=list)


@dataclass
class MCPConfig:
    """Filesystem MCP server configuration."""

    path: Path
    tool_allowlist: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    use_structured_content: bool = False


@dataclass
class CommandConfig:
    """Command execution configuration for Apptainer."""

    apptainer_image: Path
    working_directory: Path | None = None
    bind_mounts: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


@dataclass
class WorkspaceConfig:
    """Configuration for workspace management."""

    base_dir: Path = Path("workspaces")
    auto_cleanup: bool = False
    max_age_hours: int = 24


@dataclass
class LimitsConfig:
    """Limits for agent execution."""

    max_tokens: int | None = None
    max_steps: int | None = None


@dataclass
class TemplatesConfig:
    """Prompt templates used by the agent."""

    system_template: str | None = None
    user_template: str | None = None


@dataclass
class SWEAgentConfig:
    """Top-level configuration for the SWE-agent."""

    model: ModelConfig
    security: SecurityConfig
    limits: LimitsConfig
    templates: TemplatesConfig
    mcp: MCPConfig | None
    commands: CommandConfig | None
    workspace: WorkspaceConfig = field(default_factory=WorkspaceConfig)


def _as_dict(node: Any, *, context: str) -> MutableMapping[str, Any]:
    if not isinstance(node, Mapping):
        raise ConfigError(f"Expected mapping for {context}, got {type(node).__name__}")
    return dict(node)


def _load_section(parent: Mapping[str, Any], key: str, *, required: bool = True) -> Mapping[str, Any]:
    if key not in parent:
        if required:
            raise ConfigError(f"Missing required section '{key}'")
        return {}
    section = parent[key]
    if not isinstance(section, Mapping):
        raise ConfigError(f"Section '{key}' must be a mapping")
    return section


def _normalize_path(value: Any, *, field_name: str) -> Path:
    if isinstance(value, Path):
        return value
    if isinstance(value, str):
        return Path(value).expanduser()
    raise ConfigError(f"Field '{field_name}' must be a string path")


def parse_model(config: Mapping[str, Any]) -> ModelConfig:
    name = config.get("name")
    if not isinstance(name, str):
        raise ConfigError("Model name must be provided")
    temperature = config.get("temperature")
    if temperature is not None and not isinstance(temperature, (int, float)):
        raise ConfigError("Model temperature must be numeric")
    extra = {k: v for k, v in config.items() if k not in {"name", "api_key", "api_base", "temperature"}}
    return ModelConfig(
        name=name,
        api_key=config.get("api_key"),
        api_base=config.get("api_base"),
        temperature=float(temperature) if temperature is not None else None,
        extra=extra,
    )


def parse_security(config: Mapping[str, Any]) -> SecurityConfig:
    blocked_commands = config.get("blocked_commands", [])
    if blocked_commands is None:
        blocked_commands = []
    if not isinstance(blocked_commands, list) or not all(isinstance(c, str) for c in blocked_commands):
        raise ConfigError("Security.blocked_commands must be a list of strings")
    return SecurityConfig(blocked_commands=list(blocked_commands))


def parse_limits(config: Mapping[str, Any]) -> LimitsConfig:
    def _as_int(value: Any, field_name: str) -> int | None:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            normalized = value.strip().replace(",", "").replace("_", "")
            try:
                return int(normalized)
            except ValueError as exc:
                raise ConfigError(f"Field '{field_name}' must be an integer") from exc
        raise ConfigError(f"Field '{field_name}' must be an integer")

    return LimitsConfig(
        max_tokens=_as_int(config.get("max_tokens"), "max_tokens"),
        max_steps=_as_int(config.get("max_steps"), "max_steps"),
    )


def parse_templates(config: Mapping[str, Any]) -> TemplatesConfig:
    system_template = config.get("system_template")
    if system_template is not None and not isinstance(system_template, str):
        raise ConfigError("templates.system_template must be a string")
    user_template = config.get("user_template")
    if user_template is not None and not isinstance(user_template, str):
        raise ConfigError("templates.user_template must be a string")
    return TemplatesConfig(system_template=system_template, user_template=user_template)


def parse_mcp(config: Mapping[str, Any]) -> MCPConfig:
    path_value = config.get("path")
    if path_value is None:
        raise ConfigError("mcp.path is required to locate the filesystem server executable")
    tool_allowlist = config.get("tool_allowlist", [])
    if tool_allowlist is None:
        tool_allowlist = []
    if not isinstance(tool_allowlist, list) or not all(isinstance(t, str) for t in tool_allowlist):
        raise ConfigError("mcp.tool_allowlist must be a list of strings")
    env = config.get("env", {})
    if env is None:
        env = {}
    if not isinstance(env, Mapping) or not all(isinstance(k, str) and isinstance(v, str) for k, v in env.items()):
        raise ConfigError("mcp.env must be a mapping of string to string")
    use_structured = config.get("use_structured_content", False)
    if not isinstance(use_structured, bool):
        raise ConfigError("mcp.use_structured_content must be boolean")
    return MCPConfig(
        path=_normalize_path(path_value, field_name="mcp.path"),
        tool_allowlist=list(tool_allowlist),
        env=dict(env),
        use_structured_content=use_structured,
    )


def parse_commands(config: Mapping[str, Any]) -> CommandConfig:
    image = config.get("apptainer_image")
    if image is None:
        raise ConfigError("commands.apptainer_image is required")
    working_dir = config.get("working_directory")
    if working_dir is not None and not isinstance(working_dir, str):
        raise ConfigError("commands.working_directory must be a string path")
    bind_mounts = config.get("bind_mounts", [])
    if bind_mounts is None:
        bind_mounts = []
    if not isinstance(bind_mounts, list) or not all(isinstance(b, str) for b in bind_mounts):
        raise ConfigError("commands.bind_mounts must be a list of strings")
    env = config.get("env", {})
    if env is None:
        env = {}
    if not isinstance(env, Mapping) or not all(isinstance(k, str) and isinstance(v, str) for k, v in env.items()):
        raise ConfigError("commands.env must be a mapping of string to string")
    return CommandConfig(
        apptainer_image=_normalize_path(image, field_name="commands.apptainer_image"),
        working_directory=_normalize_path(working_dir, field_name="commands.working_directory")
        if working_dir
        else None,
        bind_mounts=list(bind_mounts),
        env=dict(env),
    )


def parse_workspace(config: Mapping[str, Any]) -> WorkspaceConfig:
    """Parse workspace configuration."""
    base_dir = config.get("base_dir", "workspaces")
    if not isinstance(base_dir, str):
        raise ConfigError("workspace.base_dir must be a string path")
    
    auto_cleanup = config.get("auto_cleanup", False)
    if not isinstance(auto_cleanup, bool):
        raise ConfigError("workspace.auto_cleanup must be a boolean")
    
    max_age_hours = config.get("max_age_hours", 24)
    if not isinstance(max_age_hours, int):
        raise ConfigError("workspace.max_age_hours must be an integer")
    
    return WorkspaceConfig(
        base_dir=Path(base_dir),
        auto_cleanup=auto_cleanup,
        max_age_hours=max_age_hours,
    )


@dataclass
class AgentConfigLoader:
    """Loads SWE-agent configurations from YAML files."""

    path: Path

    def load(self) -> SWEAgentConfig:
        data = self._read_yaml()
        agent_section = _load_section(data, "agent")
        model_section = _load_section(agent_section, "model")
        security_section = _load_section(agent_section, "security", required=False)
        limits_section = _load_section(agent_section, "limits", required=False)
        templates_section = _load_section(agent_section, "templates", required=False)
        mcp_section = _load_section(agent_section, "mcp", required=False)
        commands_section = _load_section(agent_section, "commands", required=False)
        workspace_section = _load_section(agent_section, "workspace", required=False)

        return SWEAgentConfig(
            model=parse_model(model_section),
            security=parse_security(security_section),
            limits=parse_limits(limits_section),
            templates=parse_templates(templates_section),
            mcp=parse_mcp(mcp_section) if mcp_section else None,
            commands=parse_commands(commands_section) if commands_section else None,
            workspace=parse_workspace(workspace_section) if workspace_section else WorkspaceConfig(),
        )

    def _read_yaml(self) -> Mapping[str, Any]:
        if not self.path.exists():
            raise ConfigError(f"Configuration file {self.path} does not exist")
        try:
            with self.path.open("r", encoding="utf-8") as file:
                content = yaml.safe_load(file)
        except yaml.YAMLError as exc:
            raise ConfigError(f"Failed to parse YAML: {exc}") from exc
        if not isinstance(content, Mapping):
            raise ConfigError("Top-level YAML structure must be a mapping")
        return self._expand_env_vars(content)
    
    def _expand_env_vars(self, data: Any) -> Any:
        """Recursively expand environment variables in ${VAR} format."""
        if isinstance(data, str):
            # Replace ${VAR} with environment variable value
            def replace_env(match):
                var_name = match.group(1)
                return os.getenv(var_name, match.group(0))
            return re.sub(r'\$\{([^}]+)\}', replace_env, data)
        elif isinstance(data, dict):
            return {key: self._expand_env_vars(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._expand_env_vars(item) for item in data]
        return data

