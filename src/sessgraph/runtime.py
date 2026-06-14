"""Minimal Activation Runner for the P0 durable Session runtime."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Protocol

from sessgraph.core import (
    AgentDefinition,
    Checkpoint,
    Decision,
    DecisionKind,
    Event,
    JsonObject,
    Session,
    SessionStatus,
    Signal,
)
from sessgraph.stores import (
    InMemoryCheckpointStore,
    InMemoryEventStore,
    InMemoryInboxStore,
    InMemorySessionStore,
    RecordNotFoundError,
)


class DecisionRejectedError(ValueError):
    """Raised when a model Decision does not match runtime invariants."""


@dataclass(frozen=True, slots=True)
class ActivationContext:
    """Read-only context passed to a model adapter."""

    agent: AgentDefinition
    session: Session
    signal: Signal
    events: tuple[Event, ...]
    now: datetime


class ModelAdapter(Protocol):
    """Protocol for provider-independent model adapters."""

    def decide(self, context: ActivationContext) -> Decision:
        """Return one Decision for the activation."""


@dataclass(frozen=True, slots=True)
class ActivationResult:
    """Result of a single runner activation attempt."""

    session_id: str
    activated: bool
    session: Session | None = None
    signal: Signal | None = None
    decision: Decision | None = None
    events: tuple[Event, ...] = ()
    checkpoint: Checkpoint | None = None


@dataclass(slots=True)
class ActivationRunner:
    """Wake one Session from one pending Signal and dispatch one Decision."""

    agent: AgentDefinition
    model: ModelAdapter
    session_store: InMemorySessionStore
    inbox_store: InMemoryInboxStore
    event_store: InMemoryEventStore
    checkpoint_store: InMemoryCheckpointStore
    clock: Callable[[], datetime] = field(default_factory=lambda: _utcnow)

    def run_once(self, session_id: str) -> ActivationResult:
        session = self.session_store.get(session_id)
        if session is None:
            raise RecordNotFoundError(f"session does not exist: {session_id}")

        pending_signals = self.inbox_store.list_for_session(session_id)
        if not pending_signals:
            return ActivationResult(session_id=session_id, activated=False, session=session)
        signal = pending_signals[0]

        running = replace(
            session,
            status=SessionStatus.RUNNING,
            updated_at=self._now(),
            revision=session.revision + 1,
        )
        context = ActivationContext(
            agent=self.agent,
            session=running,
            signal=signal,
            events=self.event_store.list_for_session(session_id),
            now=self._now(),
        )
        decision = self.model.decide(context)
        self._validate_decision(decision, session_id)

        running = self.session_store.update(running, expected_revision=session.revision)
        signal_event = self._append_event(
            session_id=session_id,
            event_type="signal_received",
            payload={
                "signal_id": signal.signal_id,
                "signal_type": signal.signal_type,
                "idempotency_key": signal.idempotency_key,
                "payload": signal.to_dict()["payload"],
            },
            source_signal_id=signal.signal_id,
        )
        decision_event = self._append_event(
            session_id=session_id,
            event_type="decision_produced",
            payload={"decision": decision.to_dict()},
            source_signal_id=signal.signal_id,
        )

        final_status = _status_for_decision(decision)
        checkpoint_id = _checkpoint_id(session_id, running.revision + 1, decision_event.sequence)
        final_session = replace(
            running,
            status=final_status,
            updated_at=self._now(),
            revision=running.revision + 1,
            checkpoint_id=checkpoint_id,
        )
        final_session = self.session_store.update(final_session, expected_revision=running.revision)
        checkpoint = self._save_checkpoint(
            checkpoint_id=checkpoint_id,
            session=final_session,
            signal=signal,
            decision=decision,
            events=(signal_event, decision_event),
        )
        popped = self.inbox_store.pop_next(session_id)
        if popped is None or popped.signal_id != signal.signal_id:
            raise DecisionRejectedError("pending signal changed during activation")

        return ActivationResult(
            session_id=session_id,
            activated=True,
            session=final_session,
            signal=signal,
            decision=decision,
            events=(signal_event, decision_event),
            checkpoint=checkpoint,
        )

    def _append_event(
        self,
        *,
        session_id: str,
        event_type: str,
        payload: JsonObject,
        source_signal_id: str,
    ) -> Event:
        sequence = self.event_store.next_sequence(session_id)
        event = Event(
            event_id=_event_id(session_id, sequence, event_type),
            session_id=session_id,
            event_type=event_type,
            sequence=sequence,
            payload=payload,
            occurred_at=self._now(),
            source_signal_id=source_signal_id,
        )
        return self.event_store.append(event, expected_next_sequence=sequence)

    def _save_checkpoint(
        self,
        *,
        checkpoint_id: str,
        session: Session,
        signal: Signal,
        decision: Decision,
        events: tuple[Event, ...],
    ) -> Checkpoint:
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            session_id=session.session_id,
            session_revision=session.revision,
            event_sequence=events[-1].sequence,
            state={
                "session": session.to_dict(),
                "signal": signal.to_dict(),
                "decision": decision.to_dict(),
                "event_ids": [event.event_id for event in events],
            },
            created_at=self._now(),
        )
        return self.checkpoint_store.save(checkpoint)

    def _validate_decision(self, decision: Decision, session_id: str) -> None:
        if decision.session_id != session_id:
            raise DecisionRejectedError(
                f"decision session_id {decision.session_id} does not match {session_id}"
            )
        if decision.kind not in {DecisionKind.FINAL_ANSWER, DecisionKind.NOOP}:
            raise DecisionRejectedError(f"unsupported decision kind: {decision.kind.value}")

    def _now(self) -> datetime:
        current = self.clock()
        if current.tzinfo is None or current.utcoffset() is None:
            raise ValueError("runner clock must return timezone-aware datetimes")
        return current.astimezone(timezone.utc)


def _status_for_decision(decision: Decision) -> SessionStatus:
    if decision.kind is DecisionKind.FINAL_ANSWER:
        return SessionStatus.COMPLETED
    if decision.kind is DecisionKind.NOOP:
        return SessionStatus.IDLE
    raise DecisionRejectedError(f"unsupported decision kind: {decision.kind.value}")


def _event_id(session_id: str, sequence: int, event_type: str) -> str:
    return f"{session_id}:event:{sequence}:{event_type}"


def _checkpoint_id(session_id: str, session_revision: int, event_sequence: int) -> str:
    return f"{session_id}:checkpoint:{session_revision}:{event_sequence}"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)
