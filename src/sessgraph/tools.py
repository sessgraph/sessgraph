"""Synchronous tool execution primitives for the P0 runtime."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from math import isfinite
from types import MappingProxyType
from typing import Any, TypeAlias

from sessgraph.core import JsonObject, JsonValue, ValidationError

ToolHandler: TypeAlias = Callable[[JsonObject], JsonObject]


class ToolError(Exception):
    """Base class for tool registry and execution errors."""


class DuplicateToolError(ToolError):
    """Raised when registering the same tool name more than once."""


class ToolNotFoundError(ToolError):
    """Raised when executing an unregistered tool."""


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Local synchronous tool registered with the runtime."""

    name: str
    description: str
    handler: ToolHandler
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty("name", self.name)
        _require_non_empty("description", self.description)
        if not callable(self.handler):
            raise ValidationError("handler must be callable")
        object.__setattr__(self, "metadata", _freeze_json_object("metadata", self.metadata))


@dataclass(frozen=True, slots=True)
class ToolResult:
    """Data result from one synchronous tool execution."""

    tool_name: str
    ok: bool
    output: JsonObject = field(default_factory=dict)
    error: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty("tool_name", self.tool_name)
        if not isinstance(self.ok, bool):
            raise ValidationError("ok must be a bool")
        if self.ok and self.error is not None:
            raise ValidationError("error must be None when ok is True")
        if not self.ok and self.error is None:
            raise ValidationError("error is required when ok is False")
        if self.error is not None:
            _require_non_empty("error", self.error)
        object.__setattr__(self, "output", _freeze_json_object("output", self.output))

    def to_dict(self) -> JsonObject:
        return {
            "tool_name": self.tool_name,
            "ok": self.ok,
            "output": _copy_json_object("output", self.output),
            "error": self.error,
        }


@dataclass
class ToolRegistry:
    """In-memory registry of local synchronous tools."""

    _tools: dict[str, ToolSpec] = field(default_factory=dict)

    def register(self, spec: ToolSpec) -> ToolSpec:
        if spec.name in self._tools:
            raise DuplicateToolError(f"tool already registered: {spec.name}")
        self._tools[spec.name] = spec
        return spec

    def get(self, name: str) -> ToolSpec:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolNotFoundError(f"tool not found: {name}") from exc

    def list_tools(self) -> tuple[ToolSpec, ...]:
        return tuple(self._tools.values())


@dataclass(frozen=True, slots=True)
class SyncToolExecutor:
    """Execute registered tools synchronously and return data results."""

    registry: ToolRegistry

    def execute(self, tool_name: str, arguments: JsonObject) -> ToolResult:
        _require_non_empty("tool_name", tool_name)
        arguments = _copy_json_object("arguments", arguments)
        try:
            spec = self.registry.get(tool_name)
            output = spec.handler(arguments)
            return ToolResult(
                tool_name=tool_name,
                ok=True,
                output=_copy_json_object("output", output),
            )
        except ToolNotFoundError:
            raise
        except Exception as exc:
            error = str(exc) or exc.__class__.__name__
            return ToolResult(tool_name=tool_name, ok=False, error=error, output={})


def _require_non_empty(field_name: str, value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string")


def _freeze_json_object(field_name: str, value: Any) -> JsonObject:
    frozen = _freeze_json_value(field_name, value)
    if not isinstance(frozen, Mapping):
        raise ValidationError(f"{field_name} must be a JSON object")
    return frozen


def _freeze_json_value(path: str, value: Any) -> JsonValue:
    copied = _copy_json_value(path, value)
    if isinstance(copied, dict):
        return MappingProxyType(
            {key: _freeze_json_value(f"{path}.{key}", item) for key, item in copied.items()}
        )
    if isinstance(copied, list):
        return tuple(_freeze_json_value(f"{path}[]", item) for item in copied)
    return copied


def _copy_json_object(field_name: str, value: Any) -> JsonObject:
    copied = _copy_json_value(field_name, value)
    if not isinstance(copied, dict):
        raise ValidationError(f"{field_name} must be a JSON object")
    return copied


def _copy_json_value(path: str, value: Any) -> JsonValue:
    if value is None or isinstance(value, str) or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not isfinite(value):
            raise ValidationError(f"{path} must not contain NaN or Infinity")
        return value
    if isinstance(value, Mapping):
        copied: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise ValidationError(f"{path} keys must be non-empty strings")
            copied[key] = _copy_json_value(f"{path}.{key}", item)
        return copied
    if isinstance(value, (list, tuple)):
        return [_copy_json_value(f"{path}[]", item) for item in value]
    raise ValidationError(f"{path} must be JSON-compatible")
