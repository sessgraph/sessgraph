"""Deterministic memory compaction for local tests and examples."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any

from sessgraph.context import InMemoryMemoryStore, MemoryRecord, memory_id_for_record
from sessgraph.core import (
    Checkpoint,
    Event,
    JsonObject,
    Session,
    ValidationError,
    _copy_json_object,
    _require_datetime,
    _require_non_empty,
    _require_non_negative_int,
    _freeze_json_object,
)
from sessgraph.stores import InMemoryCheckpointStore, InMemoryEventStore


@dataclass(frozen=True, slots=True)
class DeterministicCompactionPolicy:
    """Local deterministic policy used to prove compaction boundaries."""

    policy_id: str = "deterministic-summary-v1"
    memory_type: str = "event_summary"
    max_events: int | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty("policy_id", self.policy_id)
        _require_non_empty("memory_type", self.memory_type)
        if self.max_events is not None:
            _require_non_negative_int("max_events", self.max_events)
        object.__setattr__(self, "metadata", _freeze_json_object("metadata", self.metadata))

    def to_dict(self) -> JsonObject:
        return {
            "policy_id": self.policy_id,
            "memory_type": self.memory_type,
            "max_events": self.max_events,
            "metadata": _copy_json_object("metadata", self.metadata),
        }


@dataclass(frozen=True, slots=True)
class MemoryCompactionResult:
    """Records produced by one deterministic compaction run."""

    session_id: str
    memory: MemoryRecord
    event: Event
    checkpoint: Checkpoint
    active_memory_ids: tuple[str, ...]


@dataclass(slots=True)
class MemoryCompactor:
    """Compact Event Log windows into durable MemoryRecords."""

    event_store: InMemoryEventStore
    memory_store: InMemoryMemoryStore
    checkpoint_store: InMemoryCheckpointStore
    policy: DeterministicCompactionPolicy = field(
        default_factory=DeterministicCompactionPolicy
    )
    clock: Callable[[], datetime] = field(default_factory=lambda: _utcnow)

    def compact(
        self,
        session: Session,
        *,
        source_events: Sequence[Event] | None = None,
        supersedes_memory_ids: Sequence[str] | None = None,
    ) -> MemoryCompactionResult:
        selected_events = self._select_source_events(session, source_events)
        if not selected_events:
            raise ValidationError("source_events must contain at least one Event")

        active_before = self.memory_store.list_active_for_session(session.session_id)
        supersedes_ids = (
            _coerce_string_tuple("supersedes_memory_ids", supersedes_memory_ids)
            if supersedes_memory_ids is not None
            else tuple(record.memory_id for record in active_before)
        )
        policy_metadata = self.policy.to_dict()
        source_event_ids = tuple(event.event_id for event in selected_events)
        idempotency_key = _compaction_idempotency_key(
            policy_metadata=policy_metadata,
            source_event_ids=source_event_ids,
            supersedes_memory_ids=supersedes_ids,
        )
        memory_id = memory_id_for_record(
            session_id=session.session_id,
            memory_type=self.policy.memory_type,
            source_event_ids=source_event_ids,
            idempotency_key=idempotency_key,
        )
        memory = self._save_memory(
            session=session,
            memory_id=memory_id,
            source_events=selected_events,
            source_event_ids=source_event_ids,
            supersedes_memory_ids=supersedes_ids,
            idempotency_key=idempotency_key,
            policy_metadata=policy_metadata,
        )
        event = self._append_compaction_event(
            session=session,
            memory=memory,
            source_event_ids=source_event_ids,
            supersedes_memory_ids=supersedes_ids,
            policy_metadata=policy_metadata,
        )
        active_records = self.memory_store.list_active_for_session(session.session_id)
        active_memory_ids = tuple(record.memory_id for record in active_records)
        checkpoint = self._save_checkpoint(
            session=session,
            memory=memory,
            event=event,
            active_memory_ids=active_memory_ids,
            source_event_ids=source_event_ids,
            supersedes_memory_ids=supersedes_ids,
            policy_metadata=policy_metadata,
        )
        return MemoryCompactionResult(
            session_id=session.session_id,
            memory=memory,
            event=event,
            checkpoint=checkpoint,
            active_memory_ids=active_memory_ids,
        )

    def _select_source_events(
        self,
        session: Session,
        source_events: Sequence[Event] | None,
    ) -> tuple[Event, ...]:
        events = (
            tuple(source_events)
            if source_events is not None
            else self.event_store.list_for_session(session.session_id)
        )
        for event in events:
            if not isinstance(event, Event):
                raise ValidationError("source_events must contain only Event records")
            if event.session_id != session.session_id:
                raise ValidationError("source_events must match session_id")
        selected = tuple(sorted(events, key=lambda event: event.sequence))
        if self.policy.max_events is not None:
            if self.policy.max_events == 0:
                return ()
            selected = selected[-self.policy.max_events:]
        return selected

    def _save_memory(
        self,
        *,
        session: Session,
        memory_id: str,
        source_events: tuple[Event, ...],
        source_event_ids: tuple[str, ...],
        supersedes_memory_ids: tuple[str, ...],
        idempotency_key: str,
        policy_metadata: JsonObject,
    ) -> MemoryRecord:
        existing = self.memory_store.get(memory_id)
        if existing is not None:
            return existing

        memory = MemoryRecord(
            memory_id=memory_id,
            session_id=session.session_id,
            memory_type=self.policy.memory_type,
            content=_memory_content(
                source_events=source_events,
                supersedes_memory_ids=supersedes_memory_ids,
                policy_metadata=policy_metadata,
            ),
            source_event_ids=source_event_ids,
            created_at=self._now(),
            idempotency_key=idempotency_key,
            supersedes_memory_ids=supersedes_memory_ids,
        )
        return self.memory_store.save(memory)

    def _append_compaction_event(
        self,
        *,
        session: Session,
        memory: MemoryRecord,
        source_event_ids: tuple[str, ...],
        supersedes_memory_ids: tuple[str, ...],
        policy_metadata: JsonObject,
    ) -> Event:
        event_id = _compaction_event_id(session.session_id, memory.memory_id)
        existing = self.event_store.get(event_id)
        if existing is not None:
            return existing

        sequence = self.event_store.next_sequence(session.session_id)
        event = Event(
            event_id=event_id,
            session_id=session.session_id,
            event_type="memory_compacted",
            sequence=sequence,
            payload={
                "memory_id": memory.memory_id,
                "source_event_ids": list(source_event_ids),
                "supersedes_memory_ids": list(supersedes_memory_ids),
                "policy": _copy_json_object("policy", policy_metadata),
            },
            occurred_at=self._now(),
        )
        return self.event_store.append(event, expected_next_sequence=sequence)

    def _save_checkpoint(
        self,
        *,
        session: Session,
        memory: MemoryRecord,
        event: Event,
        active_memory_ids: tuple[str, ...],
        source_event_ids: tuple[str, ...],
        supersedes_memory_ids: tuple[str, ...],
        policy_metadata: JsonObject,
    ) -> Checkpoint:
        checkpoint_id = _compaction_checkpoint_id(session.session_id, memory.memory_id)
        existing = self.checkpoint_store.get(checkpoint_id)
        if existing is not None:
            return existing

        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            session_id=session.session_id,
            session_revision=session.revision,
            event_sequence=event.sequence,
            state={
                "session": session.to_dict(),
                "memory": memory.to_dict(),
                "event_ids": [event.event_id],
                "compaction": {
                    "memory_id": memory.memory_id,
                    "active_memory_ids": list(active_memory_ids),
                    "source_event_ids": list(source_event_ids),
                    "supersedes_memory_ids": list(supersedes_memory_ids),
                    "compaction_event_id": event.event_id,
                    "policy": _copy_json_object("policy", policy_metadata),
                },
            },
            created_at=self._now(),
        )
        return self.checkpoint_store.save(checkpoint)

    def _now(self) -> datetime:
        current = self.clock()
        _require_datetime("clock", current)
        return current.astimezone(timezone.utc)


def _memory_content(
    *,
    source_events: tuple[Event, ...],
    supersedes_memory_ids: tuple[str, ...],
    policy_metadata: JsonObject,
) -> JsonObject:
    return {
        "summary": " | ".join(
            f"{event.sequence}:{event.event_type}" for event in source_events
        ),
        "event_count": len(source_events),
        "event_types": [event.event_type for event in source_events],
        "source_event_sequences": [event.sequence for event in source_events],
        "supersedes_memory_ids": list(supersedes_memory_ids),
        "policy": _copy_json_object("policy", policy_metadata),
    }


def _coerce_string_tuple(field_name: str, value: Sequence[str] | None) -> tuple[str, ...]:
    if value is None:
        return ()
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


def _compaction_idempotency_key(
    *,
    policy_metadata: Mapping[str, Any],
    source_event_ids: tuple[str, ...],
    supersedes_memory_ids: tuple[str, ...],
) -> str:
    payload = {
        "policy": _copy_json_object("policy", policy_metadata),
        "source_event_ids": list(source_event_ids),
        "supersedes_memory_ids": list(supersedes_memory_ids),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"memory_compaction:{sha256(encoded).hexdigest()[:16]}"


def _compaction_event_id(session_id: str, memory_id: str) -> str:
    return f"{session_id}:event:memory_compacted:{memory_id}"


def _compaction_checkpoint_id(session_id: str, memory_id: str) -> str:
    return f"{session_id}:checkpoint:memory_compacted:{memory_id}"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)
