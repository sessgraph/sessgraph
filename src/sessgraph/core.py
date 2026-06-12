"""P0 core data structures for the durable Session runtime."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from types import MappingProxyType
from typing import Any, TypeAlias

JsonValue: TypeAlias = str | int | float | bool | None | Sequence[Any] | Mapping[str, Any]
JsonObject: TypeAlias = Mapping[str, JsonValue]

SCHEMA_VERSION = 1


class ValidationError(ValueError):
    """Raised when a SessGraph core object violates P0 invariants."""


class SessionStatus(str, Enum):
    """Durable lifecycle status for a Session."""

    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


class DecisionKind(str, Enum):
    """Provider-independent model decisions supported by the P0 data model."""

    NOOP = "noop"
    FINAL_ANSWER = "final_answer"


@dataclass(frozen=True, slots=True)
class AgentDefinition:
    """Static definition for an agent that can own durable sessions."""

    agent_id: str
    name: str
    instructions: str
    version: int = 1
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty("agent_id", self.agent_id)
        _require_non_empty("name", self.name)
        _require_non_empty("instructions", self.instructions)
        _require_positive_int("version", self.version)
        object.__setattr__(self, "metadata", _freeze_json_object("metadata", self.metadata))

    def to_dict(self) -> JsonObject:
        return {
            "schema_version": SCHEMA_VERSION,
            "agent_id": self.agent_id,
            "name": self.name,
            "instructions": self.instructions,
            "version": self.version,
            "metadata": _copy_json_object("metadata", self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AgentDefinition":
        _require_schema_version(data)
        return cls(
            agent_id=_require_field(data, "agent_id"),
            name=_require_field(data, "name"),
            instructions=_require_field(data, "instructions"),
            version=_require_field(data, "version"),
            metadata=_optional_json_object(data, "metadata"),
        )


@dataclass(frozen=True, slots=True)
class Session:
    """Durable state center activated by Signals and recovered from Checkpoints."""

    session_id: str
    agent_id: str
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    revision: int = 0
    checkpoint_id: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty("session_id", self.session_id)
        _require_non_empty("agent_id", self.agent_id)
        _require_non_negative_int("revision", self.revision)
        _require_datetime("created_at", self.created_at)
        _require_datetime("updated_at", self.updated_at)
        if self.updated_at < self.created_at:
            raise ValidationError("updated_at must be greater than or equal to created_at")
        if self.checkpoint_id is not None:
            _require_non_empty("checkpoint_id", self.checkpoint_id)
        object.__setattr__(self, "status", _coerce_enum("status", self.status, SessionStatus))
        object.__setattr__(self, "metadata", _freeze_json_object("metadata", self.metadata))

    def to_dict(self) -> JsonObject:
        return {
            "schema_version": SCHEMA_VERSION,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "status": self.status.value,
            "created_at": _datetime_to_json(self.created_at),
            "updated_at": _datetime_to_json(self.updated_at),
            "revision": self.revision,
            "checkpoint_id": self.checkpoint_id,
            "metadata": _copy_json_object("metadata", self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Session":
        _require_schema_version(data)
        return cls(
            session_id=_require_field(data, "session_id"),
            agent_id=_require_field(data, "agent_id"),
            status=_require_field(data, "status"),
            created_at=_datetime_from_json(_require_field(data, "created_at"), "created_at"),
            updated_at=_datetime_from_json(_require_field(data, "updated_at"), "updated_at"),
            revision=_require_field(data, "revision"),
            checkpoint_id=data.get("checkpoint_id"),
            metadata=_optional_json_object(data, "metadata"),
        )


@dataclass(frozen=True, slots=True)
class Signal:
    """External activation input for a durable Session."""

    signal_id: str
    session_id: str
    signal_type: str
    payload: JsonObject
    created_at: datetime
    idempotency_key: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty("signal_id", self.signal_id)
        _require_non_empty("session_id", self.session_id)
        _require_non_empty("signal_type", self.signal_type)
        _require_datetime("created_at", self.created_at)
        if self.idempotency_key is not None:
            _require_non_empty("idempotency_key", self.idempotency_key)
        object.__setattr__(self, "payload", _freeze_json_object("payload", self.payload))

    def to_dict(self) -> JsonObject:
        return {
            "schema_version": SCHEMA_VERSION,
            "signal_id": self.signal_id,
            "session_id": self.session_id,
            "signal_type": self.signal_type,
            "payload": _copy_json_object("payload", self.payload),
            "created_at": _datetime_to_json(self.created_at),
            "idempotency_key": self.idempotency_key,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Signal":
        _require_schema_version(data)
        return cls(
            signal_id=_require_field(data, "signal_id"),
            session_id=_require_field(data, "session_id"),
            signal_type=_require_field(data, "signal_type"),
            payload=_require_json_object(data, "payload"),
            created_at=_datetime_from_json(_require_field(data, "created_at"), "created_at"),
            idempotency_key=data.get("idempotency_key"),
        )


@dataclass(frozen=True, slots=True)
class Event:
    """Append-only fact record for a Session."""

    event_id: str
    session_id: str
    event_type: str
    sequence: int
    payload: JsonObject
    occurred_at: datetime
    source_signal_id: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty("event_id", self.event_id)
        _require_non_empty("session_id", self.session_id)
        _require_non_empty("event_type", self.event_type)
        _require_non_negative_int("sequence", self.sequence)
        _require_datetime("occurred_at", self.occurred_at)
        if self.source_signal_id is not None:
            _require_non_empty("source_signal_id", self.source_signal_id)
        object.__setattr__(self, "payload", _freeze_json_object("payload", self.payload))

    def to_dict(self) -> JsonObject:
        return {
            "schema_version": SCHEMA_VERSION,
            "event_id": self.event_id,
            "session_id": self.session_id,
            "event_type": self.event_type,
            "sequence": self.sequence,
            "payload": _copy_json_object("payload", self.payload),
            "occurred_at": _datetime_to_json(self.occurred_at),
            "source_signal_id": self.source_signal_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Event":
        _require_schema_version(data)
        return cls(
            event_id=_require_field(data, "event_id"),
            session_id=_require_field(data, "session_id"),
            event_type=_require_field(data, "event_type"),
            sequence=_require_field(data, "sequence"),
            payload=_require_json_object(data, "payload"),
            occurred_at=_datetime_from_json(_require_field(data, "occurred_at"), "occurred_at"),
            source_signal_id=data.get("source_signal_id"),
        )


@dataclass(frozen=True, slots=True)
class Decision:
    """Provider-independent model output awaiting runtime validation."""

    decision_id: str
    session_id: str
    kind: DecisionKind
    payload: JsonObject
    created_at: datetime

    def __post_init__(self) -> None:
        _require_non_empty("decision_id", self.decision_id)
        _require_non_empty("session_id", self.session_id)
        _require_datetime("created_at", self.created_at)
        object.__setattr__(self, "kind", _coerce_enum("kind", self.kind, DecisionKind))
        object.__setattr__(self, "payload", _freeze_json_object("payload", self.payload))
        if self.kind is DecisionKind.FINAL_ANSWER:
            _require_non_empty("payload.content", self.payload.get("content"))

    def to_dict(self) -> JsonObject:
        return {
            "schema_version": SCHEMA_VERSION,
            "decision_id": self.decision_id,
            "session_id": self.session_id,
            "kind": self.kind.value,
            "payload": _copy_json_object("payload", self.payload),
            "created_at": _datetime_to_json(self.created_at),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Decision":
        _require_schema_version(data)
        return cls(
            decision_id=_require_field(data, "decision_id"),
            session_id=_require_field(data, "session_id"),
            kind=_require_field(data, "kind"),
            payload=_require_json_object(data, "payload"),
            created_at=_datetime_from_json(_require_field(data, "created_at"), "created_at"),
        )


@dataclass(frozen=True, slots=True)
class Checkpoint:
    """Recoverable snapshot boundary for a Session."""

    checkpoint_id: str
    session_id: str
    session_revision: int
    event_sequence: int
    state: JsonObject
    created_at: datetime

    def __post_init__(self) -> None:
        _require_non_empty("checkpoint_id", self.checkpoint_id)
        _require_non_empty("session_id", self.session_id)
        _require_non_negative_int("session_revision", self.session_revision)
        _require_non_negative_int("event_sequence", self.event_sequence)
        _require_datetime("created_at", self.created_at)
        object.__setattr__(self, "state", _freeze_json_object("state", self.state))

    def to_dict(self) -> JsonObject:
        return {
            "schema_version": SCHEMA_VERSION,
            "checkpoint_id": self.checkpoint_id,
            "session_id": self.session_id,
            "session_revision": self.session_revision,
            "event_sequence": self.event_sequence,
            "state": _copy_json_object("state", self.state),
            "created_at": _datetime_to_json(self.created_at),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Checkpoint":
        _require_schema_version(data)
        return cls(
            checkpoint_id=_require_field(data, "checkpoint_id"),
            session_id=_require_field(data, "session_id"),
            session_revision=_require_field(data, "session_revision"),
            event_sequence=_require_field(data, "event_sequence"),
            state=_require_json_object(data, "state"),
            created_at=_datetime_from_json(_require_field(data, "created_at"), "created_at"),
        )


def _require_field(data: Mapping[str, Any], field_name: str) -> Any:
    if field_name not in data:
        raise ValidationError(f"{field_name} is required")
    return data[field_name]


def _require_schema_version(data: Mapping[str, Any]) -> None:
    version = _require_field(data, "schema_version")
    if version != SCHEMA_VERSION:
        raise ValidationError(f"schema_version must be {SCHEMA_VERSION}")


def _require_non_empty(field_name: str, value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string")


def _require_positive_int(field_name: str, value: Any) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValidationError(f"{field_name} must be a positive integer")


def _require_non_negative_int(field_name: str, value: Any) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValidationError(f"{field_name} must be a non-negative integer")


def _require_datetime(field_name: str, value: Any) -> None:
    if not isinstance(value, datetime):
        raise ValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValidationError(f"{field_name} must be timezone-aware")


def _coerce_enum(field_name: str, value: Any, enum_type: type[Enum]) -> Enum:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(value)
    except ValueError as exc:
        allowed = ", ".join(member.value for member in enum_type)
        raise ValidationError(f"{field_name} must be one of: {allowed}") from exc


def _datetime_to_json(value: datetime) -> str:
    _require_datetime("datetime", value)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _datetime_from_json(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{field_name} must be an ISO 8601 datetime string")
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be an ISO 8601 datetime string") from exc
    _require_datetime(field_name, parsed)
    return parsed.astimezone(timezone.utc)


def _optional_json_object(data: Mapping[str, Any], field_name: str) -> JsonObject:
    if field_name not in data or data[field_name] is None:
        return {}
    return _require_json_object(data, field_name)


def _require_json_object(data: Mapping[str, Any], field_name: str) -> JsonObject:
    return _copy_json_object(field_name, _require_field(data, field_name))


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
        copied: JsonObject = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise ValidationError(f"{path} keys must be non-empty strings")
            copied[key] = _copy_json_value(f"{path}.{key}", item)
        return copied
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_copy_json_value(f"{path}[]", item) for item in value]
    raise ValidationError(f"{path} must be JSON-compatible")
