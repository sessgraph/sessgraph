"""Deterministic InMemory timer flow for the P1 runtime."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from types import MappingProxyType
from typing import Any

from sessgraph.core import JsonObject, JsonValue, Signal, ValidationError
from sessgraph.stores import (
    ConcurrencyError,
    IdempotencyConflictError,
    InMemoryInboxStore,
    RecordNotFoundError,
)

TIMER_SCHEMA_VERSION = 1


class TimerStatus(str, Enum):
    """Local lifecycle status for an InMemory timer."""

    PENDING = "pending"
    FIRED = "fired"


@dataclass(frozen=True, slots=True)
class TimerRecord:
    """A local deterministic timer that can wake one Session via a Signal."""

    timer_id: str
    session_id: str
    due_at: datetime
    reason: str
    created_at: datetime
    data: JsonObject = field(default_factory=dict)
    idempotency_key: str | None = None
    status: TimerStatus = TimerStatus.PENDING
    fired_at: datetime | None = None
    signal_id: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty("timer_id", self.timer_id)
        _require_non_empty("session_id", self.session_id)
        _require_datetime("due_at", self.due_at)
        _require_non_empty("reason", self.reason)
        _require_datetime("created_at", self.created_at)
        if self.idempotency_key is not None:
            _require_non_empty("idempotency_key", self.idempotency_key)
        object.__setattr__(self, "status", _coerce_enum("status", self.status, TimerStatus))
        if self.fired_at is not None:
            _require_datetime("fired_at", self.fired_at)
        if self.signal_id is not None:
            _require_non_empty("signal_id", self.signal_id)
        if self.status is TimerStatus.PENDING and (
            self.fired_at is not None or self.signal_id is not None
        ):
            raise ValidationError("pending timers must not include fired_at or signal_id")
        if self.status is TimerStatus.FIRED and (
            self.fired_at is None or self.signal_id is None
        ):
            raise ValidationError("fired timers require fired_at and signal_id")
        object.__setattr__(self, "data", _freeze_json_object("data", self.data))

    def to_dict(self) -> JsonObject:
        return {
            "schema_version": TIMER_SCHEMA_VERSION,
            "timer_id": self.timer_id,
            "session_id": self.session_id,
            "due_at": _datetime_to_json(self.due_at),
            "reason": self.reason,
            "data": _copy_json_object("data", self.data),
            "created_at": _datetime_to_json(self.created_at),
            "idempotency_key": self.idempotency_key,
            "status": self.status.value,
            "fired_at": None if self.fired_at is None else _datetime_to_json(self.fired_at),
            "signal_id": self.signal_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TimerRecord":
        _require_timer_schema_version(data)
        fired_at = data.get("fired_at")
        return cls(
            timer_id=_require_field(data, "timer_id"),
            session_id=_require_field(data, "session_id"),
            due_at=_datetime_from_json(_require_field(data, "due_at"), "due_at"),
            reason=_require_field(data, "reason"),
            data=_require_json_object(data, "data"),
            created_at=_datetime_from_json(_require_field(data, "created_at"), "created_at"),
            idempotency_key=data.get("idempotency_key"),
            status=_require_field(data, "status"),
            fired_at=None if fired_at is None else _datetime_from_json(fired_at, "fired_at"),
            signal_id=data.get("signal_id"),
        )


@dataclass
class InMemoryTimerStore:
    """Store local timers and expose deterministic due scans."""

    _timers_by_id: dict[str, TimerRecord] = field(default_factory=dict)
    _timer_ids_by_session: dict[str, list[str]] = field(default_factory=dict)
    _timer_ids_by_idempotency: dict[tuple[str, str], str] = field(default_factory=dict)

    def schedule(self, timer: TimerRecord) -> TimerRecord:
        existing = self._timers_by_id.get(timer.timer_id)
        if existing is not None:
            _raise_if_different(existing, timer, f"timer id conflict: {timer.timer_id}")
            return _snapshot_timer(existing)

        if timer.idempotency_key is not None:
            idempotency_ref = (timer.session_id, timer.idempotency_key)
            existing_timer_id = self._timer_ids_by_idempotency.get(idempotency_ref)
            if existing_timer_id is not None:
                existing_timer = self._timers_by_id[existing_timer_id]
                _raise_if_different(
                    existing_timer,
                    timer,
                    f"idempotency key conflict: {timer.idempotency_key}",
                )
                return _snapshot_timer(existing_timer)
            self._timer_ids_by_idempotency[idempotency_ref] = timer.timer_id

        self._timers_by_id[timer.timer_id] = _snapshot_timer(timer)
        self._timer_ids_by_session.setdefault(timer.session_id, []).append(timer.timer_id)
        return _snapshot_timer(timer)

    def get(self, timer_id: str) -> TimerRecord | None:
        timer = self._timers_by_id.get(timer_id)
        if timer is None:
            return None
        return _snapshot_timer(timer)

    def list_for_session(self, session_id: str) -> tuple[TimerRecord, ...]:
        timer_ids = self._timer_ids_by_session.get(session_id, [])
        return tuple(_snapshot_timer(self._timers_by_id[timer_id]) for timer_id in timer_ids)

    def list_due(self, now: datetime) -> tuple[TimerRecord, ...]:
        _require_datetime("now", now)
        due = [
            timer
            for timer in self._timers_by_id.values()
            if timer.status is TimerStatus.PENDING and timer.due_at <= now
        ]
        due.sort(key=lambda timer: (timer.due_at, timer.created_at, timer.timer_id))
        return tuple(_snapshot_timer(timer) for timer in due)

    def mark_fired(self, timer_id: str, *, fired_at: datetime, signal_id: str) -> TimerRecord:
        _require_datetime("fired_at", fired_at)
        _require_non_empty("signal_id", signal_id)
        current = self._timers_by_id.get(timer_id)
        if current is None:
            raise RecordNotFoundError(f"timer does not exist: {timer_id}")
        if current.status is TimerStatus.FIRED:
            if current.fired_at == fired_at and current.signal_id == signal_id:
                return _snapshot_timer(current)
            raise ConcurrencyError(f"timer already fired: {timer_id}")

        fired = replace(
            current,
            status=TimerStatus.FIRED,
            fired_at=fired_at,
            signal_id=signal_id,
        )
        self._timers_by_id[timer_id] = _snapshot_timer(fired)
        return _snapshot_timer(fired)


@dataclass(frozen=True, slots=True)
class TimerDispatcher:
    """Convert due timers into timer Signals for Session inbox activation."""

    timer_store: InMemoryTimerStore
    inbox_store: InMemoryInboxStore
    clock: Callable[[], datetime]

    def enqueue_due(self) -> tuple[Signal, ...]:
        now = _normalize_datetime("now", self.clock())
        enqueued: list[Signal] = []
        for timer in self.timer_store.list_due(now):
            signal = _signal_for_timer(timer, now)
            enqueued_signal = self.inbox_store.enqueue(signal)
            self.timer_store.mark_fired(
                timer.timer_id,
                fired_at=now,
                signal_id=enqueued_signal.signal_id,
            )
            enqueued.append(enqueued_signal)
        return tuple(enqueued)


def _signal_for_timer(timer: TimerRecord, created_at: datetime) -> Signal:
    signal_id = _timer_signal_id(timer.session_id, timer.timer_id)
    return Signal(
        signal_id=signal_id,
        session_id=timer.session_id,
        signal_type="timer",
        payload={
            "timer_id": timer.timer_id,
            "reason": timer.reason,
            "data": _copy_json_object("data", timer.data),
        },
        created_at=created_at,
        idempotency_key=f"timer:{timer.timer_id}",
    )


def _timer_signal_id(session_id: str, timer_id: str) -> str:
    return f"{session_id}:signal:timer:{timer_id}"


def _raise_if_different(existing: object, incoming: object, message: str) -> None:
    if _serialized(existing) != _serialized(incoming):
        raise IdempotencyConflictError(message)


def _serialized(record: object) -> object:
    to_dict = getattr(record, "to_dict", None)
    if to_dict is None:
        return record
    return to_dict()


def _snapshot_timer(timer: TimerRecord) -> TimerRecord:
    return TimerRecord.from_dict(timer.to_dict())


def _require_field(data: Mapping[str, Any], field_name: str) -> Any:
    if field_name not in data:
        raise ValidationError(f"{field_name} is required")
    return data[field_name]


def _require_timer_schema_version(data: Mapping[str, Any]) -> None:
    version = _require_field(data, "schema_version")
    if version != TIMER_SCHEMA_VERSION:
        raise ValidationError(f"schema_version must be {TIMER_SCHEMA_VERSION}")


def _require_non_empty(field_name: str, value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string")


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


def _normalize_datetime(field_name: str, value: datetime) -> datetime:
    _require_datetime(field_name, value)
    return value.astimezone(timezone.utc)


def _datetime_to_json(value: datetime) -> str:
    return _normalize_datetime("datetime", value).isoformat().replace("+00:00", "Z")


def _datetime_from_json(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{field_name} must be an ISO 8601 datetime string")
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be an ISO 8601 datetime string") from exc
    return _normalize_datetime(field_name, parsed)


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
        copied: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise ValidationError(f"{path} keys must be non-empty strings")
            copied[key] = _copy_json_value(f"{path}.{key}", item)
        return copied
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_copy_json_value(f"{path}[]", item) for item in value]
    raise ValidationError(f"{path} must be JSON-compatible")
