"""Deterministic InMemory async job flow for the P1 runtime."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from types import MappingProxyType
from typing import Any

from sessgraph.core import Event, JsonObject, JsonValue, Signal, ValidationError
from sessgraph.stores import (
    ConcurrencyError,
    IdempotencyConflictError,
    InMemoryEventStore,
    InMemoryInboxStore,
    RecordNotFoundError,
)

JOB_SCHEMA_VERSION = 1


class JobStatus(str, Enum):
    """Local lifecycle status for an InMemory async job."""

    SUBMITTED = "submitted"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class JobRecord:
    """A local async job requested by a model Decision."""

    job_id: str
    session_id: str
    decision_id: str
    job_type: str
    arguments: JsonObject
    created_at: datetime
    idempotency_key: str | None = None
    status: JobStatus = JobStatus.SUBMITTED
    started_at: datetime | None = None
    completed_at: datetime | None = None
    output: JsonObject = field(default_factory=dict)
    error: JsonObject | None = None
    result_signal_id: str | None = None
    result_enqueued_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_non_empty("job_id", self.job_id)
        _require_non_empty("session_id", self.session_id)
        _require_non_empty("decision_id", self.decision_id)
        _require_non_empty("job_type", self.job_type)
        _require_datetime("created_at", self.created_at)
        if self.idempotency_key is not None:
            _require_non_empty("idempotency_key", self.idempotency_key)
        object.__setattr__(self, "status", _coerce_enum("status", self.status, JobStatus))
        if self.started_at is not None:
            _require_datetime("started_at", self.started_at)
        if self.completed_at is not None:
            _require_datetime("completed_at", self.completed_at)
        if self.result_signal_id is not None:
            _require_non_empty("result_signal_id", self.result_signal_id)
        if self.result_enqueued_at is not None:
            _require_datetime("result_enqueued_at", self.result_enqueued_at)
        object.__setattr__(self, "arguments", _freeze_json_object("arguments", self.arguments))
        object.__setattr__(self, "output", _freeze_json_object("output", self.output))
        if self.error is not None:
            object.__setattr__(self, "error", _freeze_json_object("error", self.error))
        _validate_job_lifecycle(self)

    def to_dict(self) -> JsonObject:
        return {
            "schema_version": JOB_SCHEMA_VERSION,
            "job_id": self.job_id,
            "session_id": self.session_id,
            "decision_id": self.decision_id,
            "job_type": self.job_type,
            "arguments": _copy_json_object("arguments", self.arguments),
            "created_at": _datetime_to_json(self.created_at),
            "idempotency_key": self.idempotency_key,
            "status": self.status.value,
            "started_at": None if self.started_at is None else _datetime_to_json(self.started_at),
            "completed_at": (
                None if self.completed_at is None else _datetime_to_json(self.completed_at)
            ),
            "output": _copy_json_object("output", self.output),
            "error": None if self.error is None else _copy_json_object("error", self.error),
            "result_signal_id": self.result_signal_id,
            "result_enqueued_at": (
                None
                if self.result_enqueued_at is None
                else _datetime_to_json(self.result_enqueued_at)
            ),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "JobRecord":
        _require_job_schema_version(data)
        started_at = data.get("started_at")
        completed_at = data.get("completed_at")
        result_enqueued_at = data.get("result_enqueued_at")
        return cls(
            job_id=_require_field(data, "job_id"),
            session_id=_require_field(data, "session_id"),
            decision_id=_require_field(data, "decision_id"),
            job_type=_require_field(data, "job_type"),
            arguments=_require_json_object(data, "arguments"),
            created_at=_datetime_from_json(_require_field(data, "created_at"), "created_at"),
            idempotency_key=data.get("idempotency_key"),
            status=_require_field(data, "status"),
            started_at=(
                None if started_at is None else _datetime_from_json(started_at, "started_at")
            ),
            completed_at=(
                None
                if completed_at is None
                else _datetime_from_json(completed_at, "completed_at")
            ),
            output=_optional_json_object(data, "output"),
            error=None if data.get("error") is None else _require_json_object(data, "error"),
            result_signal_id=data.get("result_signal_id"),
            result_enqueued_at=(
                None
                if result_enqueued_at is None
                else _datetime_from_json(result_enqueued_at, "result_enqueued_at")
            ),
        )


@dataclass
class InMemoryJobStore:
    """Store local async jobs and expose deterministic lifecycle transitions."""

    _jobs_by_id: dict[str, JobRecord] = field(default_factory=dict)
    _job_ids_by_session: dict[str, list[str]] = field(default_factory=dict)
    _job_ids_by_idempotency: dict[tuple[str, str], str] = field(default_factory=dict)

    def submit(self, job: JobRecord) -> JobRecord:
        if job.status is not JobStatus.SUBMITTED:
            raise ValidationError("submitted jobs must start in submitted status")

        existing = self._jobs_by_id.get(job.job_id)
        if existing is not None:
            _raise_if_job_id_submission_different(existing, job)
            return _snapshot_job(existing)

        if job.idempotency_key is not None:
            idempotency_ref = (job.session_id, job.idempotency_key)
            existing_job_id = self._job_ids_by_idempotency.get(idempotency_ref)
            if existing_job_id is not None:
                existing_job = self._jobs_by_id[existing_job_id]
                _raise_if_idempotent_submission_different(existing_job, job)
                return _snapshot_job(existing_job)
            self._job_ids_by_idempotency[idempotency_ref] = job.job_id

        self._jobs_by_id[job.job_id] = _snapshot_job(job)
        self._job_ids_by_session.setdefault(job.session_id, []).append(job.job_id)
        return _snapshot_job(job)

    def get(self, job_id: str) -> JobRecord | None:
        job = self._jobs_by_id.get(job_id)
        if job is None:
            return None
        return _snapshot_job(job)

    def list_for_session(self, session_id: str) -> tuple[JobRecord, ...]:
        job_ids = self._job_ids_by_session.get(session_id, [])
        return tuple(_snapshot_job(self._jobs_by_id[job_id]) for job_id in job_ids)

    def list_completed_pending_result(self) -> tuple[JobRecord, ...]:
        jobs = [
            job
            for job in self._jobs_by_id.values()
            if job.status in {JobStatus.SUCCEEDED, JobStatus.FAILED}
            and job.result_signal_id is None
        ]
        jobs.sort(
            key=lambda job: (
                job.completed_at or job.created_at,
                job.created_at,
                job.job_id,
            )
        )
        return tuple(_snapshot_job(job) for job in jobs)

    def mark_running(self, job_id: str, *, started_at: datetime) -> JobRecord:
        _require_datetime("started_at", started_at)
        current = self._require_job(job_id)
        if current.status is JobStatus.RUNNING:
            if current.started_at == started_at:
                return _snapshot_job(current)
            raise ConcurrencyError(f"job already running: {job_id}")
        if current.status is not JobStatus.SUBMITTED:
            raise ConcurrencyError(f"job cannot start from {current.status.value}: {job_id}")
        running = replace(current, status=JobStatus.RUNNING, started_at=started_at)
        self._jobs_by_id[job_id] = _snapshot_job(running)
        return _snapshot_job(running)

    def mark_succeeded(
        self,
        job_id: str,
        *,
        completed_at: datetime,
        output: JsonObject,
    ) -> JobRecord:
        _require_datetime("completed_at", completed_at)
        copied_output = _copy_json_object("output", output)
        current = self._require_job(job_id)
        if current.status is JobStatus.SUCCEEDED:
            if current.completed_at == completed_at and _copy_json_object(
                "output", current.output
            ) == copied_output:
                return _snapshot_job(current)
            raise ConcurrencyError(f"job already succeeded: {job_id}")
        if current.status is JobStatus.FAILED:
            raise ConcurrencyError(f"job already failed: {job_id}")
        if current.status is not JobStatus.RUNNING:
            raise ConcurrencyError(f"job must be running before success: {job_id}")
        succeeded = replace(
            current,
            status=JobStatus.SUCCEEDED,
            completed_at=completed_at,
            output=copied_output,
            error=None,
        )
        self._jobs_by_id[job_id] = _snapshot_job(succeeded)
        return _snapshot_job(succeeded)

    def mark_failed(
        self,
        job_id: str,
        *,
        completed_at: datetime,
        error: JsonObject,
    ) -> JobRecord:
        _require_datetime("completed_at", completed_at)
        copied_error = _copy_json_object("error", error)
        current = self._require_job(job_id)
        if current.status is JobStatus.FAILED:
            if current.completed_at == completed_at and _copy_json_object(
                "error", current.error
            ) == copied_error:
                return _snapshot_job(current)
            raise ConcurrencyError(f"job already failed: {job_id}")
        if current.status is JobStatus.SUCCEEDED:
            raise ConcurrencyError(f"job already succeeded: {job_id}")
        if current.status is not JobStatus.RUNNING:
            raise ConcurrencyError(f"job must be running before failure: {job_id}")
        failed = replace(
            current,
            status=JobStatus.FAILED,
            completed_at=completed_at,
            output={},
            error=copied_error,
        )
        self._jobs_by_id[job_id] = _snapshot_job(failed)
        return _snapshot_job(failed)

    def mark_result_enqueued(
        self,
        job_id: str,
        *,
        enqueued_at: datetime,
        signal_id: str,
    ) -> JobRecord:
        _require_datetime("enqueued_at", enqueued_at)
        _require_non_empty("signal_id", signal_id)
        current = self._require_job(job_id)
        if current.status not in {JobStatus.SUCCEEDED, JobStatus.FAILED}:
            raise ConcurrencyError(f"job result is not complete: {job_id}")
        if current.result_signal_id is not None:
            if current.result_signal_id == signal_id and current.result_enqueued_at == enqueued_at:
                return _snapshot_job(current)
            raise ConcurrencyError(f"job result already enqueued: {job_id}")
        enqueued = replace(
            current,
            result_signal_id=signal_id,
            result_enqueued_at=enqueued_at,
        )
        self._jobs_by_id[job_id] = _snapshot_job(enqueued)
        return _snapshot_job(enqueued)

    def _require_job(self, job_id: str) -> JobRecord:
        current = self._jobs_by_id.get(job_id)
        if current is None:
            raise RecordNotFoundError(f"job does not exist: {job_id}")
        return current


@dataclass(frozen=True, slots=True)
class JobResultDispatcher:
    """Convert completed jobs into job_result Signals for Session activation."""

    job_store: InMemoryJobStore
    inbox_store: InMemoryInboxStore
    event_store: InMemoryEventStore
    clock: Callable[[], datetime]

    def enqueue_completed(self) -> tuple[Signal, ...]:
        now = _normalize_datetime("now", self.clock())
        enqueued: list[Signal] = []
        for job in self.job_store.list_completed_pending_result():
            signal = _signal_for_job_result(job, now)
            enqueued_signal = self.inbox_store.enqueue(signal)
            self._append_result_event(job=job, signal=enqueued_signal, occurred_at=now)
            self.job_store.mark_result_enqueued(
                job.job_id,
                enqueued_at=now,
                signal_id=enqueued_signal.signal_id,
            )
            enqueued.append(enqueued_signal)
        return tuple(enqueued)

    def _append_result_event(self, *, job: JobRecord, signal: Signal, occurred_at: datetime) -> Event:
        sequence = self.event_store.next_sequence(job.session_id)
        event = Event(
            event_id=_event_id(job.session_id, sequence, "job_result_enqueued"),
            session_id=job.session_id,
            event_type="job_result_enqueued",
            sequence=sequence,
            payload={
                "job_id": job.job_id,
                "job": job.to_dict(),
                "signal_id": signal.signal_id,
            },
            occurred_at=occurred_at,
        )
        return self.event_store.append(event, expected_next_sequence=sequence)


def _signal_for_job_result(job: JobRecord, created_at: datetime) -> Signal:
    signal_id = _job_result_signal_id(job.session_id, job.job_id)
    ok = job.status is JobStatus.SUCCEEDED
    return Signal(
        signal_id=signal_id,
        session_id=job.session_id,
        signal_type="job_result",
        payload={
            "job_id": job.job_id,
            "ok": ok,
            "output": _copy_json_object("output", job.output),
            "error": None if job.error is None else _copy_json_object("error", job.error),
        },
        created_at=created_at,
        idempotency_key=f"job_result:{job.job_id}",
    )


def job_id_for_decision(session_id: str, decision_id: str) -> str:
    _require_non_empty("session_id", session_id)
    _require_non_empty("decision_id", decision_id)
    return f"{session_id}:job:{decision_id}"


def _job_result_signal_id(session_id: str, job_id: str) -> str:
    return f"{session_id}:signal:job_result:{job_id}"


def _event_id(session_id: str, sequence: int, event_type: str) -> str:
    return f"{session_id}:event:{sequence}:{event_type}"


def _validate_job_lifecycle(job: JobRecord) -> None:
    has_result_signal = job.result_signal_id is not None
    has_result_time = job.result_enqueued_at is not None
    if has_result_signal != has_result_time:
        raise ValidationError("job result enqueue fields must be set together")

    if job.status is JobStatus.SUBMITTED:
        if job.started_at is not None or job.completed_at is not None:
            raise ValidationError("submitted jobs must not include lifecycle timestamps")
        if job.output or job.error is not None or has_result_signal:
            raise ValidationError("submitted jobs must not include result fields")
        return

    if job.status is JobStatus.RUNNING:
        if job.started_at is None or job.completed_at is not None:
            raise ValidationError("running jobs require started_at only")
        if job.started_at < job.created_at:
            raise ValidationError("started_at must be greater than or equal to created_at")
        if job.output or job.error is not None or has_result_signal:
            raise ValidationError("running jobs must not include result fields")
        return

    if job.status in {JobStatus.SUCCEEDED, JobStatus.FAILED}:
        if job.started_at is None or job.completed_at is None:
            raise ValidationError("completed jobs require started_at and completed_at")
        if job.completed_at < job.started_at:
            raise ValidationError("completed_at must be greater than or equal to started_at")
        if job.result_enqueued_at is not None and job.result_enqueued_at < job.completed_at:
            raise ValidationError("result_enqueued_at must be greater than or equal to completed_at")
        if job.status is JobStatus.SUCCEEDED and job.error is not None:
            raise ValidationError("succeeded jobs must not include error")
        if job.status is JobStatus.FAILED and job.error is None:
            raise ValidationError("failed jobs require error")
        return

    raise ValidationError(f"unsupported job status: {job.status.value}")


def _raise_if_job_id_submission_different(existing: JobRecord, incoming: JobRecord) -> None:
    existing_ref = (
        existing.session_id,
        existing.decision_id,
        existing.job_type,
        _copy_json_object("arguments", existing.arguments),
        existing.idempotency_key,
    )
    incoming_ref = (
        incoming.session_id,
        incoming.decision_id,
        incoming.job_type,
        _copy_json_object("arguments", incoming.arguments),
        incoming.idempotency_key,
    )
    if existing_ref != incoming_ref:
        raise IdempotencyConflictError(f"job id conflict: {incoming.job_id}")


def _raise_if_idempotent_submission_different(existing: JobRecord, incoming: JobRecord) -> None:
    existing_ref = (
        existing.session_id,
        existing.job_type,
        _copy_json_object("arguments", existing.arguments),
        existing.idempotency_key,
    )
    incoming_ref = (
        incoming.session_id,
        incoming.job_type,
        _copy_json_object("arguments", incoming.arguments),
        incoming.idempotency_key,
    )
    if existing_ref != incoming_ref:
        raise IdempotencyConflictError(f"idempotency key conflict: {incoming.idempotency_key}")


def _snapshot_job(job: JobRecord) -> JobRecord:
    return JobRecord.from_dict(job.to_dict())


def _require_field(data: Mapping[str, Any], field_name: str) -> Any:
    if field_name not in data:
        raise ValidationError(f"{field_name} is required")
    return data[field_name]


def _require_job_schema_version(data: Mapping[str, Any]) -> None:
    version = _require_field(data, "schema_version")
    if version != JOB_SCHEMA_VERSION:
        raise ValidationError(f"schema_version must be {JOB_SCHEMA_VERSION}")


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
        copied: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise ValidationError(f"{path} keys must be non-empty strings")
            copied[key] = _copy_json_value(f"{path}.{key}", item)
        return copied
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_copy_json_value(f"{path}[]", item) for item in value]
    raise ValidationError(f"{path} must be JSON-compatible")
