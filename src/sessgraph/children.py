"""Deterministic InMemory parent/child Session creation flow."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from hashlib import sha256
import json
from typing import Any

from sessgraph.core import (
    JsonObject,
    ValidationError,
    _coerce_enum,
    _copy_json_object,
    _datetime_from_json,
    _datetime_to_json,
    _freeze_json_object,
    _require_datetime,
    _require_field,
    _require_non_empty,
)
from sessgraph.stores import IdempotencyConflictError

CHILD_SESSION_SCHEMA_VERSION = 1


class ChildSessionStatus(str, Enum):
    """Durable relationship status for a child Session."""

    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ChildSessionRecord:
    """Durable relationship between one Parent Session and one Child Session."""

    child_session_id: str
    parent_session_id: str
    parent_decision_id: str
    parent_signal_id: str
    child_agent_id: str
    input: JsonObject
    created_at: datetime
    metadata: JsonObject = field(default_factory=dict)
    context_policy: JsonObject = field(default_factory=dict)
    idempotency_key: str | None = None
    status: ChildSessionStatus = ChildSessionStatus.STARTED
    completed_at: datetime | None = None
    result_signal_id: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty("child_session_id", self.child_session_id)
        _require_non_empty("parent_session_id", self.parent_session_id)
        _require_non_empty("parent_decision_id", self.parent_decision_id)
        _require_non_empty("parent_signal_id", self.parent_signal_id)
        _require_non_empty("child_agent_id", self.child_agent_id)
        _require_datetime("created_at", self.created_at)
        if self.idempotency_key is not None:
            _require_non_empty("idempotency_key", self.idempotency_key)
        object.__setattr__(
            self,
            "status",
            _coerce_enum("status", self.status, ChildSessionStatus),
        )
        if self.completed_at is not None:
            _require_datetime("completed_at", self.completed_at)
        if self.result_signal_id is not None:
            _require_non_empty("result_signal_id", self.result_signal_id)
        object.__setattr__(self, "input", _freeze_json_object("input", self.input))
        object.__setattr__(self, "metadata", _freeze_json_object("metadata", self.metadata))
        object.__setattr__(
            self,
            "context_policy",
            _freeze_json_object("context_policy", self.context_policy),
        )
        _validate_child_lifecycle(self)

    def to_dict(self) -> JsonObject:
        return {
            "schema_version": CHILD_SESSION_SCHEMA_VERSION,
            "child_session_id": self.child_session_id,
            "parent_session_id": self.parent_session_id,
            "parent_decision_id": self.parent_decision_id,
            "parent_signal_id": self.parent_signal_id,
            "child_agent_id": self.child_agent_id,
            "status": self.status.value,
            "input": _copy_json_object("input", self.input),
            "metadata": _copy_json_object("metadata", self.metadata),
            "context_policy": _copy_json_object("context_policy", self.context_policy),
            "idempotency_key": self.idempotency_key,
            "created_at": _datetime_to_json(self.created_at),
            "completed_at": (
                None if self.completed_at is None else _datetime_to_json(self.completed_at)
            ),
            "result_signal_id": self.result_signal_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ChildSessionRecord":
        _require_child_schema_version(data)
        completed_at = data.get("completed_at")
        return cls(
            child_session_id=_require_field(data, "child_session_id"),
            parent_session_id=_require_field(data, "parent_session_id"),
            parent_decision_id=_require_field(data, "parent_decision_id"),
            parent_signal_id=_require_field(data, "parent_signal_id"),
            child_agent_id=_require_field(data, "child_agent_id"),
            status=_require_field(data, "status"),
            input=_copy_json_object("input", _require_field(data, "input")),
            metadata=_copy_json_object("metadata", data.get("metadata", {})),
            context_policy=_copy_json_object("context_policy", data.get("context_policy", {})),
            idempotency_key=data.get("idempotency_key"),
            created_at=_datetime_from_json(_require_field(data, "created_at"), "created_at"),
            completed_at=(
                None
                if completed_at is None
                else _datetime_from_json(completed_at, "completed_at")
            ),
            result_signal_id=data.get("result_signal_id"),
        )


@dataclass
class InMemoryChildSessionStore:
    """Store child Session relationships by child id, parent id, and idempotency key."""

    _children_by_id: dict[str, ChildSessionRecord] = field(default_factory=dict)
    _child_ids_by_parent: dict[str, list[str]] = field(default_factory=dict)
    _child_ids_by_idempotency: dict[tuple[str, str], str] = field(default_factory=dict)

    def start(self, child: ChildSessionRecord) -> ChildSessionRecord:
        if child.status is not ChildSessionStatus.STARTED:
            raise ValidationError("child sessions must start in started status")

        existing = self._children_by_id.get(child.child_session_id)
        if existing is not None:
            _raise_if_child_id_start_different(existing, child)
            return _snapshot_child(existing)

        if child.idempotency_key is not None:
            idempotency_ref = (child.parent_session_id, child.idempotency_key)
            existing_child_id = self._child_ids_by_idempotency.get(idempotency_ref)
            if existing_child_id is not None:
                existing_child = self._children_by_id[existing_child_id]
                _raise_if_idempotent_start_different(existing_child, child)
                return _snapshot_child(existing_child)
            self._child_ids_by_idempotency[idempotency_ref] = child.child_session_id

        self._children_by_id[child.child_session_id] = _snapshot_child(child)
        self._child_ids_by_parent.setdefault(child.parent_session_id, []).append(
            child.child_session_id
        )
        return _snapshot_child(child)

    def get(self, child_session_id: str) -> ChildSessionRecord | None:
        child = self._children_by_id.get(child_session_id)
        if child is None:
            return None
        return _snapshot_child(child)

    def list_for_parent(self, parent_session_id: str) -> tuple[ChildSessionRecord, ...]:
        child_ids = self._child_ids_by_parent.get(parent_session_id, [])
        return tuple(_snapshot_child(self._children_by_id[child_id]) for child_id in child_ids)


def child_session_id_for_decision(
    *,
    parent_session_id: str,
    parent_decision_id: str,
    child_agent_id: str,
    idempotency_key: str | None = None,
) -> str:
    _require_non_empty("parent_session_id", parent_session_id)
    _require_non_empty("parent_decision_id", parent_decision_id)
    _require_non_empty("child_agent_id", child_agent_id)
    if idempotency_key is not None:
        _require_non_empty("idempotency_key", idempotency_key)
    payload = {
        "child_agent_id": child_agent_id,
        "idempotency_key": idempotency_key,
        "parent_decision_id": parent_decision_id,
        "parent_session_id": parent_session_id,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"{parent_session_id}:child:{sha256(encoded).hexdigest()[:16]}"


def _child_start_ref(child: ChildSessionRecord) -> tuple[object, ...]:
    return (
        child.parent_session_id,
        child.parent_decision_id,
        child.parent_signal_id,
        child.child_agent_id,
        _copy_json_object("input", child.input),
        _copy_json_object("metadata", child.metadata),
        _copy_json_object("context_policy", child.context_policy),
        child.idempotency_key,
    )


def _idempotent_child_start_ref(child: ChildSessionRecord) -> tuple[object, ...]:
    return (
        child.parent_session_id,
        child.child_agent_id,
        _copy_json_object("input", child.input),
        _copy_json_object("metadata", child.metadata),
        _copy_json_object("context_policy", child.context_policy),
        child.idempotency_key,
    )


def _raise_if_child_id_start_different(
    existing: ChildSessionRecord,
    incoming: ChildSessionRecord,
) -> None:
    if _child_start_ref(existing) != _child_start_ref(incoming):
        raise IdempotencyConflictError(f"child session id conflict: {incoming.child_session_id}")


def _raise_if_idempotent_start_different(
    existing: ChildSessionRecord,
    incoming: ChildSessionRecord,
) -> None:
    if _idempotent_child_start_ref(existing) != _idempotent_child_start_ref(incoming):
        raise IdempotencyConflictError(f"idempotency key conflict: {incoming.idempotency_key}")


def _validate_child_lifecycle(child: ChildSessionRecord) -> None:
    if child.status is ChildSessionStatus.STARTED:
        if child.completed_at is not None or child.result_signal_id is not None:
            raise ValidationError("started child sessions must not include result fields")
        return
    if child.completed_at is None:
        raise ValidationError("terminal child sessions require completed_at")
    if child.completed_at < child.created_at:
        raise ValidationError("completed_at must be greater than or equal to created_at")


def _snapshot_child(child: ChildSessionRecord) -> ChildSessionRecord:
    return ChildSessionRecord.from_dict(child.to_dict())


def _require_child_schema_version(data: Mapping[str, Any]) -> None:
    version = _require_field(data, "schema_version")
    if version != CHILD_SESSION_SCHEMA_VERSION:
        raise ValidationError(f"schema_version must be {CHILD_SESSION_SCHEMA_VERSION}")
