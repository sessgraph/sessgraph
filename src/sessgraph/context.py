"""Deterministic memory records and context snapshots."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any

from sessgraph.core import (
    Event,
    JsonObject,
    Session,
    Signal,
    ValidationError,
    _copy_json_object,
    _datetime_from_json,
    _datetime_to_json,
    _freeze_json_object,
    _require_datetime,
    _require_field,
    _require_non_empty,
    _require_non_negative_int,
    _require_schema_version,
)
from sessgraph.stores import (
    IdempotencyConflictError,
    InMemoryCheckpointStore,
    InMemoryEventStore,
)

EVENT_ORDERING = "sequence_asc"
MEMORY_ORDERING = "created_at_memory_id_asc"


@dataclass(frozen=True, slots=True)
class MemoryRecord:
    """Session-scoped durable memory record used by context building."""

    memory_id: str
    session_id: str
    memory_type: str
    content: JsonObject
    source_event_ids: tuple[str, ...]
    created_at: datetime
    idempotency_key: str | None = None
    supersedes_memory_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_non_empty("memory_id", self.memory_id)
        _require_non_empty("session_id", self.session_id)
        _require_non_empty("memory_type", self.memory_type)
        _require_datetime("created_at", self.created_at)
        if self.idempotency_key is not None:
            _require_non_empty("idempotency_key", self.idempotency_key)
        object.__setattr__(self, "content", _freeze_json_object("content", self.content))
        object.__setattr__(
            self,
            "source_event_ids",
            _coerce_string_tuple("source_event_ids", self.source_event_ids),
        )
        object.__setattr__(
            self,
            "supersedes_memory_ids",
            _coerce_string_tuple("supersedes_memory_ids", self.supersedes_memory_ids),
        )

    def to_dict(self) -> JsonObject:
        return {
            "schema_version": 1,
            "memory_id": self.memory_id,
            "session_id": self.session_id,
            "memory_type": self.memory_type,
            "content": _copy_json_object("content", self.content),
            "source_event_ids": list(self.source_event_ids),
            "created_at": _datetime_to_json(self.created_at),
            "idempotency_key": self.idempotency_key,
            "supersedes_memory_ids": list(self.supersedes_memory_ids),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MemoryRecord":
        _require_schema_version(data)
        return cls(
            memory_id=_require_field(data, "memory_id"),
            session_id=_require_field(data, "session_id"),
            memory_type=_require_field(data, "memory_type"),
            content=_copy_json_object("content", _require_field(data, "content")),
            source_event_ids=_coerce_string_tuple(
                "source_event_ids", _require_field(data, "source_event_ids")
            ),
            created_at=_datetime_from_json(_require_field(data, "created_at"), "created_at"),
            idempotency_key=data.get("idempotency_key"),
            supersedes_memory_ids=_coerce_string_tuple(
                "supersedes_memory_ids", data.get("supersedes_memory_ids", ())
            ),
        )


@dataclass(frozen=True, slots=True)
class ContextSnapshot:
    """Activation-time context derived from durable Session facts."""

    session_id: str
    signal_id: str
    event_window: tuple[Event, ...]
    memory_records: tuple[MemoryRecord, ...]
    latest_checkpoint_id: str | None
    built_at: datetime
    ordering: JsonObject = field(default_factory=lambda: _default_ordering())
    limits: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty("session_id", self.session_id)
        _require_non_empty("signal_id", self.signal_id)
        _require_datetime("built_at", self.built_at)
        if self.latest_checkpoint_id is not None:
            _require_non_empty("latest_checkpoint_id", self.latest_checkpoint_id)

        event_window = _coerce_event_tuple("event_window", self.event_window)
        memory_records = _coerce_memory_tuple("memory_records", self.memory_records)
        _validate_event_window(self.session_id, event_window)
        _validate_memory_records(self.session_id, memory_records)

        object.__setattr__(self, "event_window", event_window)
        object.__setattr__(self, "memory_records", memory_records)
        object.__setattr__(self, "ordering", _freeze_json_object("ordering", self.ordering))
        object.__setattr__(self, "limits", _freeze_json_object("limits", self.limits))

    def to_dict(self) -> JsonObject:
        return {
            "schema_version": 1,
            "session_id": self.session_id,
            "signal_id": self.signal_id,
            "event_window": [event.to_dict() for event in self.event_window],
            "memory_records": [record.to_dict() for record in self.memory_records],
            "latest_checkpoint_id": self.latest_checkpoint_id,
            "built_at": _datetime_to_json(self.built_at),
            "ordering": _copy_json_object("ordering", self.ordering),
            "limits": _copy_json_object("limits", self.limits),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ContextSnapshot":
        _require_schema_version(data)
        return cls(
            session_id=_require_field(data, "session_id"),
            signal_id=_require_field(data, "signal_id"),
            event_window=_event_window_from_data(_require_field(data, "event_window")),
            memory_records=_memory_records_from_data(_require_field(data, "memory_records")),
            latest_checkpoint_id=data.get("latest_checkpoint_id"),
            built_at=_datetime_from_json(_require_field(data, "built_at"), "built_at"),
            ordering=_copy_json_object("ordering", data.get("ordering", _default_ordering())),
            limits=_copy_json_object("limits", data.get("limits", {})),
        )

    @property
    def event_ids(self) -> tuple[str, ...]:
        return tuple(event.event_id for event in self.event_window)

    @property
    def memory_ids(self) -> tuple[str, ...]:
        return tuple(record.memory_id for record in self.memory_records)


@dataclass
class InMemoryMemoryStore:
    """Store Session-scoped MemoryRecords by id and idempotency key."""

    _memories_by_id: dict[str, MemoryRecord] = field(default_factory=dict)
    _memory_ids_by_session: dict[str, list[str]] = field(default_factory=dict)
    _memory_ids_by_idempotency: dict[tuple[str, str], str] = field(default_factory=dict)

    def save(self, memory: MemoryRecord) -> MemoryRecord:
        existing = self._memories_by_id.get(memory.memory_id)
        if existing is not None:
            _raise_if_different(existing, memory, f"memory id conflict: {memory.memory_id}")
            return _snapshot_memory(existing)

        if memory.idempotency_key is not None:
            idempotency_ref = (memory.session_id, memory.idempotency_key)
            existing_memory_id = self._memory_ids_by_idempotency.get(idempotency_ref)
            if existing_memory_id is not None:
                existing_memory = self._memories_by_id[existing_memory_id]
                _raise_if_different(
                    existing_memory,
                    memory,
                    f"idempotency key conflict: {memory.idempotency_key}",
                )
                return _snapshot_memory(existing_memory)
            self._memory_ids_by_idempotency[idempotency_ref] = memory.memory_id

        self._memories_by_id[memory.memory_id] = _snapshot_memory(memory)
        self._memory_ids_by_session.setdefault(memory.session_id, []).append(memory.memory_id)
        return _snapshot_memory(memory)

    def get(self, memory_id: str) -> MemoryRecord | None:
        memory = self._memories_by_id.get(memory_id)
        if memory is None:
            return None
        return _snapshot_memory(memory)

    def list_for_session(self, session_id: str) -> tuple[MemoryRecord, ...]:
        memory_ids = self._memory_ids_by_session.get(session_id, [])
        return tuple(_snapshot_memory(self._memories_by_id[memory_id]) for memory_id in memory_ids)


@dataclass(frozen=True, slots=True)
class ContextBuilder:
    """Build deterministic activation context from local InMemory stores."""

    event_store: InMemoryEventStore
    memory_store: InMemoryMemoryStore
    checkpoint_store: InMemoryCheckpointStore
    clock: Callable[[], datetime] = field(default_factory=lambda: _utcnow)
    max_events: int | None = None

    def __post_init__(self) -> None:
        if self.max_events is not None:
            _require_non_negative_int("max_events", self.max_events)

    def build(self, session: Session, signal: Signal) -> ContextSnapshot:
        if signal.session_id != session.session_id:
            raise ValidationError("signal session_id must match session session_id")

        all_events = tuple(
            sorted(
                self.event_store.list_for_session(session.session_id),
                key=lambda event: event.sequence,
            )
        )
        event_window = _window_events(all_events, self.max_events)
        memory_records = tuple(
            sorted(
                self.memory_store.list_for_session(session.session_id),
                key=lambda record: (record.created_at, record.memory_id),
            )
        )
        latest_checkpoint = self.checkpoint_store.latest_for_session(session.session_id)

        return ContextSnapshot(
            session_id=session.session_id,
            signal_id=signal.signal_id,
            event_window=event_window,
            memory_records=memory_records,
            latest_checkpoint_id=(
                latest_checkpoint.checkpoint_id if latest_checkpoint is not None else None
            ),
            built_at=self._now(),
            ordering=_default_ordering(),
            limits=_limits_metadata(
                all_events=all_events,
                event_window=event_window,
                max_events=self.max_events,
            ),
        )

    def _now(self) -> datetime:
        current = self.clock()
        if not isinstance(current, datetime):
            raise ValidationError("context builder clock must return a datetime")
        if current.tzinfo is None or current.utcoffset() is None:
            raise ValidationError("context builder clock must return timezone-aware datetimes")
        return current.astimezone(timezone.utc)


def memory_id_for_record(
    *,
    session_id: str,
    memory_type: str,
    source_event_ids: Sequence[str],
    idempotency_key: str | None = None,
) -> str:
    """Return a deterministic MemoryRecord id for local runtime-produced memory."""

    _require_non_empty("session_id", session_id)
    _require_non_empty("memory_type", memory_type)
    source_ids = _coerce_string_tuple("source_event_ids", source_event_ids)
    if idempotency_key is not None:
        _require_non_empty("idempotency_key", idempotency_key)
    payload = {
        "idempotency_key": idempotency_key,
        "memory_type": memory_type,
        "session_id": session_id,
        "source_event_ids": list(source_ids),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"{session_id}:memory:{sha256(encoded).hexdigest()[:16]}"


def _coerce_string_tuple(field_name: str, value: Any) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValidationError(f"{field_name} must be a sequence of strings")
    result = tuple(value)
    seen: set[str] = set()
    for item in result:
        _require_non_empty(f"{field_name}[]", item)
        if item in seen:
            raise ValidationError(f"{field_name} must not contain duplicate ids")
        seen.add(item)
    return result


def _coerce_event_tuple(field_name: str, value: Any) -> tuple[Event, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValidationError(f"{field_name} must be a sequence of Event records")
    result = tuple(value)
    for event in result:
        if not isinstance(event, Event):
            raise ValidationError(f"{field_name} must contain only Event records")
    return result


def _coerce_memory_tuple(field_name: str, value: Any) -> tuple[MemoryRecord, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValidationError(f"{field_name} must be a sequence of MemoryRecord records")
    result = tuple(value)
    for record in result:
        if not isinstance(record, MemoryRecord):
            raise ValidationError(f"{field_name} must contain only MemoryRecord records")
    return result


def _validate_event_window(session_id: str, event_window: tuple[Event, ...]) -> None:
    previous_sequence: int | None = None
    event_ids: set[str] = set()
    for event in event_window:
        if event.session_id != session_id:
            raise ValidationError("event_window records must match snapshot session_id")
        if event.event_id in event_ids:
            raise ValidationError("event_window must not contain duplicate event ids")
        if previous_sequence is not None and event.sequence <= previous_sequence:
            raise ValidationError("event_window must be ordered by ascending sequence")
        event_ids.add(event.event_id)
        previous_sequence = event.sequence


def _validate_memory_records(session_id: str, records: tuple[MemoryRecord, ...]) -> None:
    previous_key: tuple[datetime, str] | None = None
    memory_ids: set[str] = set()
    for record in records:
        if record.session_id != session_id:
            raise ValidationError("memory_records must match snapshot session_id")
        if record.memory_id in memory_ids:
            raise ValidationError("memory_records must not contain duplicate memory ids")
        key = (record.created_at, record.memory_id)
        if previous_key is not None and key < previous_key:
            raise ValidationError("memory_records must be ordered by created_at and memory_id")
        memory_ids.add(record.memory_id)
        previous_key = key


def _event_window_from_data(value: Any) -> tuple[Event, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValidationError("event_window must be a sequence")
    return tuple(Event.from_dict(_require_mapping("event_window[]", item)) for item in value)


def _memory_records_from_data(value: Any) -> tuple[MemoryRecord, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValidationError("memory_records must be a sequence")
    return tuple(
        MemoryRecord.from_dict(_require_mapping("memory_records[]", item)) for item in value
    )


def _require_mapping(field_name: str, value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field_name} must be a JSON object")
    return value


def _window_events(events: tuple[Event, ...], max_events: int | None) -> tuple[Event, ...]:
    if max_events is None:
        return events
    if max_events == 0:
        return ()
    return events[-max_events:]


def _limits_metadata(
    *,
    all_events: tuple[Event, ...],
    event_window: tuple[Event, ...],
    max_events: int | None,
) -> JsonObject:
    metadata: dict[str, int | None] = {
        "max_events": max_events,
        "event_count": len(all_events),
        "event_window_count": len(event_window),
    }
    if event_window:
        metadata["event_window_start_sequence"] = event_window[0].sequence
        metadata["event_window_end_sequence"] = event_window[-1].sequence
    return metadata


def _default_ordering() -> JsonObject:
    return {
        "events": EVENT_ORDERING,
        "memory_records": MEMORY_ORDERING,
    }


def _raise_if_different(existing: MemoryRecord, incoming: MemoryRecord, message: str) -> None:
    if existing.to_dict() != incoming.to_dict():
        raise IdempotencyConflictError(message)


def _snapshot_memory(memory: MemoryRecord) -> MemoryRecord:
    return MemoryRecord.from_dict(memory.to_dict())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)
