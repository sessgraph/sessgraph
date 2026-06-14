"""In-memory stores for the P0 durable Session runtime."""

from __future__ import annotations

from dataclasses import dataclass, field

from sessgraph.core import Checkpoint, Event, Session, Signal


class StoreError(Exception):
    """Base class for SessGraph store errors."""


class DuplicateRecordError(StoreError):
    """Raised when creating a record that already exists."""


class RecordNotFoundError(StoreError):
    """Raised when updating a record that does not exist."""


class ConcurrencyError(StoreError):
    """Raised when optimistic concurrency or append-only ordering fails."""


class IdempotencyConflictError(StoreError):
    """Raised when an idempotency key or record id maps to different content."""


@dataclass
class InMemorySessionStore:
    """Store durable Session snapshots by session id."""

    _sessions: dict[str, Session] = field(default_factory=dict)

    def create(self, session: Session) -> Session:
        if session.session_id in self._sessions:
            raise DuplicateRecordError(f"session already exists: {session.session_id}")
        self._sessions[session.session_id] = _snapshot_session(session)
        return _snapshot_session(session)

    def get(self, session_id: str) -> Session | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        return _snapshot_session(session)

    def update(self, session: Session, *, expected_revision: int) -> Session:
        current = self._sessions.get(session.session_id)
        if current is None:
            raise RecordNotFoundError(f"session does not exist: {session.session_id}")
        if current.revision != expected_revision:
            raise ConcurrencyError(
                f"session {session.session_id} revision is {current.revision}, "
                f"expected {expected_revision}"
            )
        if session.revision != expected_revision + 1:
            raise ConcurrencyError(
                f"session {session.session_id} revision must advance to {expected_revision + 1}"
            )
        self._sessions[session.session_id] = _snapshot_session(session)
        return _snapshot_session(session)

    def list_sessions(self) -> tuple[Session, ...]:
        return tuple(_snapshot_session(session) for session in self._sessions.values())


@dataclass
class InMemoryInboxStore:
    """Store pending Signals by Session."""

    _signals_by_id: dict[str, Signal] = field(default_factory=dict)
    _signal_ids_by_session: dict[str, list[str]] = field(default_factory=dict)
    _signal_ids_by_idempotency: dict[tuple[str, str], str] = field(default_factory=dict)

    def enqueue(self, signal: Signal) -> Signal:
        existing = self._signals_by_id.get(signal.signal_id)
        if existing is not None:
            _raise_if_different(existing, signal, f"signal id conflict: {signal.signal_id}")
            return _snapshot_signal(existing)

        if signal.idempotency_key is not None:
            idempotency_ref = (signal.session_id, signal.idempotency_key)
            existing_signal_id = self._signal_ids_by_idempotency.get(idempotency_ref)
            if existing_signal_id is not None:
                existing_signal = self._signals_by_id[existing_signal_id]
                _raise_if_different(
                    existing_signal,
                    signal,
                    f"idempotency key conflict: {signal.idempotency_key}",
                )
                return _snapshot_signal(existing_signal)
            self._signal_ids_by_idempotency[idempotency_ref] = signal.signal_id

        self._signals_by_id[signal.signal_id] = _snapshot_signal(signal)
        self._signal_ids_by_session.setdefault(signal.session_id, []).append(signal.signal_id)
        return _snapshot_signal(signal)

    def get(self, signal_id: str) -> Signal | None:
        signal = self._signals_by_id.get(signal_id)
        if signal is None:
            return None
        return _snapshot_signal(signal)

    def list_for_session(self, session_id: str) -> tuple[Signal, ...]:
        signal_ids = self._signal_ids_by_session.get(session_id, [])
        return tuple(_snapshot_signal(self._signals_by_id[signal_id]) for signal_id in signal_ids)

    def pop_next(self, session_id: str) -> Signal | None:
        signal_ids = self._signal_ids_by_session.get(session_id)
        if not signal_ids:
            return None
        signal_id = signal_ids.pop(0)
        if not signal_ids:
            self._signal_ids_by_session.pop(session_id, None)
        return _snapshot_signal(self._signals_by_id[signal_id])


@dataclass
class InMemoryEventStore:
    """Append-only Event Log grouped by Session."""

    _events_by_id: dict[str, Event] = field(default_factory=dict)
    _event_ids_by_session: dict[str, list[str]] = field(default_factory=dict)

    def append(self, event: Event, *, expected_next_sequence: int | None = None) -> Event:
        existing = self._events_by_id.get(event.event_id)
        if existing is not None:
            _raise_if_different(existing, event, f"event id conflict: {event.event_id}")
            return _snapshot_event(existing)

        event_ids = self._event_ids_by_session.setdefault(event.session_id, [])
        next_sequence = len(event_ids)
        if expected_next_sequence is not None and expected_next_sequence != next_sequence:
            raise ConcurrencyError(
                f"session {event.session_id} next event sequence is {next_sequence}, "
                f"expected {expected_next_sequence}"
            )
        if event.sequence != next_sequence:
            raise ConcurrencyError(
                f"event sequence for session {event.session_id} must be {next_sequence}"
            )

        self._events_by_id[event.event_id] = _snapshot_event(event)
        event_ids.append(event.event_id)
        return _snapshot_event(event)

    def get(self, event_id: str) -> Event | None:
        event = self._events_by_id.get(event_id)
        if event is None:
            return None
        return _snapshot_event(event)

    def list_for_session(self, session_id: str) -> tuple[Event, ...]:
        event_ids = self._event_ids_by_session.get(session_id, [])
        return tuple(_snapshot_event(self._events_by_id[event_id]) for event_id in event_ids)

    def next_sequence(self, session_id: str) -> int:
        return len(self._event_ids_by_session.get(session_id, []))


@dataclass
class InMemoryCheckpointStore:
    """Store recoverable Checkpoints by checkpoint id and Session."""

    _checkpoints_by_id: dict[str, Checkpoint] = field(default_factory=dict)
    _checkpoint_ids_by_session: dict[str, list[str]] = field(default_factory=dict)

    def save(self, checkpoint: Checkpoint) -> Checkpoint:
        existing = self._checkpoints_by_id.get(checkpoint.checkpoint_id)
        if existing is not None:
            _raise_if_different(
                existing,
                checkpoint,
                f"checkpoint id conflict: {checkpoint.checkpoint_id}",
            )
            return _snapshot_checkpoint(existing)

        self._checkpoints_by_id[checkpoint.checkpoint_id] = _snapshot_checkpoint(checkpoint)
        self._checkpoint_ids_by_session.setdefault(checkpoint.session_id, []).append(
            checkpoint.checkpoint_id
        )
        return _snapshot_checkpoint(checkpoint)

    def get(self, checkpoint_id: str) -> Checkpoint | None:
        checkpoint = self._checkpoints_by_id.get(checkpoint_id)
        if checkpoint is None:
            return None
        return _snapshot_checkpoint(checkpoint)

    def latest_for_session(self, session_id: str) -> Checkpoint | None:
        checkpoint_ids = self._checkpoint_ids_by_session.get(session_id, [])
        if not checkpoint_ids:
            return None
        checkpoints = [self._checkpoints_by_id[checkpoint_id] for checkpoint_id in checkpoint_ids]
        latest = max(
            checkpoints,
            key=lambda checkpoint: (
                checkpoint.event_sequence,
                checkpoint.session_revision,
                checkpoint.created_at,
                checkpoint.checkpoint_id,
            ),
        )
        return _snapshot_checkpoint(latest)


def _raise_if_different(existing: object, incoming: object, message: str) -> None:
    if _serialized(existing) != _serialized(incoming):
        raise IdempotencyConflictError(message)


def _serialized(record: object) -> object:
    to_dict = getattr(record, "to_dict", None)
    if to_dict is None:
        return record
    return to_dict()


def _snapshot_session(session: Session) -> Session:
    return Session.from_dict(session.to_dict())


def _snapshot_signal(signal: Signal) -> Signal:
    return Signal.from_dict(signal.to_dict())


def _snapshot_event(event: Event) -> Event:
    return Event.from_dict(event.to_dict())


def _snapshot_checkpoint(checkpoint: Checkpoint) -> Checkpoint:
    return Checkpoint.from_dict(checkpoint.to_dict())
