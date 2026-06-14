from __future__ import annotations

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
    Session,
    SessionStatus,
    Signal,
)


def run_basic_session() -> ActivationResult:
    clock = FixedClock(datetime(2026, 6, 14, 10, 0, tzinfo=timezone.utc))
    agent = AgentDefinition(
        agent_id="agent-basic",
        name="Basic Agent",
        instructions="Return a final_answer Decision.",
    )
    session = Session(
        session_id="sess-basic",
        agent_id=agent.agent_id,
        status=SessionStatus.IDLE,
        created_at=clock(),
        updated_at=clock(),
    )
    signal = Signal(
        signal_id="sig-basic",
        session_id=session.session_id,
        signal_type="user_message",
        payload={"content": "hello SessGraph"},
        created_at=clock(),
        idempotency_key="example-1",
    )

    session_store = InMemorySessionStore()
    inbox_store = InMemoryInboxStore()
    event_store = InMemoryEventStore()
    checkpoint_store = InMemoryCheckpointStore()
    session_store.create(session)
    inbox_store.enqueue(signal)

    runner = ActivationRunner(
        agent=agent,
        model=FakeModel(),
        session_store=session_store,
        inbox_store=inbox_store,
        event_store=event_store,
        checkpoint_store=checkpoint_store,
        clock=clock,
    )
    return runner.run_once(session.session_id)


class FixedClock:
    def __init__(self, start: datetime) -> None:
        self._current = start

    def __call__(self) -> datetime:
        current = self._current
        self._current = self._current + timedelta(seconds=1)
        return current


if __name__ == "__main__":
    result = run_basic_session()
    if result.decision is not None:
        print(result.decision.payload["content"])
