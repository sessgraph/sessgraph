from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sessgraph import (
    ActivationResult,
    ActivationRunner,
    AgentDefinition,
    FakeModel,
    InMemoryCheckpointStore,
    InMemoryEventStore,
    InMemoryInboxStore,
    InMemorySessionStore,
    InMemoryTimerStore,
    Session,
    SessionStatus,
    Signal,
    TimerDispatcher,
    TimerRecord,
)


@dataclass(frozen=True, slots=True)
class TimerSessionResult:
    dispatched_signals: tuple[Signal, ...]
    activation: ActivationResult


def run_timer_session() -> TimerSessionResult:
    start = datetime(2026, 6, 20, 11, 0, tzinfo=timezone.utc)
    due_at = start + timedelta(minutes=5)
    clock = ManualClock(start)
    agent = AgentDefinition(
        agent_id="agent-timer",
        name="Timer Agent",
        instructions="Return a final_answer Decision.",
    )
    session = Session(
        session_id="sess-timer",
        agent_id=agent.agent_id,
        status=SessionStatus.IDLE,
        created_at=start,
        updated_at=start,
    )
    timer = TimerRecord(
        timer_id="timer-1",
        session_id=session.session_id,
        due_at=due_at,
        reason="wake_for_followup",
        data={"topic": "timer"},
        created_at=start,
        idempotency_key="timer-example-1",
    )

    session_store = InMemorySessionStore()
    inbox_store = InMemoryInboxStore()
    event_store = InMemoryEventStore()
    checkpoint_store = InMemoryCheckpointStore()
    timer_store = InMemoryTimerStore()
    session_store.create(session)
    timer_store.schedule(timer)

    clock.set(due_at)
    dispatcher = TimerDispatcher(timer_store=timer_store, inbox_store=inbox_store, clock=clock)
    dispatched_signals = dispatcher.enqueue_due()

    runner = ActivationRunner(
        agent=agent,
        model=FakeModel(final_answer="timer fired"),
        session_store=session_store,
        inbox_store=inbox_store,
        event_store=event_store,
        checkpoint_store=checkpoint_store,
        clock=clock,
    )
    activation = runner.run_once(session.session_id)
    return TimerSessionResult(dispatched_signals=dispatched_signals, activation=activation)


class ManualClock:
    def __init__(self, current: datetime) -> None:
        self._current = current

    def __call__(self) -> datetime:
        return self._current

    def set(self, current: datetime) -> None:
        self._current = current


if __name__ == "__main__":
    result = run_timer_session()
    if result.activation.decision is not None:
        print(result.activation.decision.payload["content"])
