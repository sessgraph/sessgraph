from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sessgraph import (
    ActivationResult,
    ActivationRunner,
    AgentDefinition,
    ContextBuilder,
    Event,
    FakeModel,
    InMemoryCheckpointStore,
    InMemoryEventStore,
    InMemoryInboxStore,
    InMemoryMemoryStore,
    InMemorySessionStore,
    MemoryCompactionResult,
    MemoryCompactor,
    Session,
    SessionStatus,
    Signal,
)


@dataclass(frozen=True, slots=True)
class MemoryCompactionSessionResult:
    compaction: MemoryCompactionResult
    activation: ActivationResult


def run_memory_compaction_session() -> MemoryCompactionSessionResult:
    start = datetime(2026, 6, 23, 13, 0, tzinfo=timezone.utc)
    clock = ManualClock(start)
    agent = AgentDefinition(
        agent_id="agent-memory",
        name="Memory Agent",
        instructions="Return Decisions only.",
    )
    session = Session(
        session_id="sess-memory",
        agent_id=agent.agent_id,
        status=SessionStatus.IDLE,
        created_at=start,
        updated_at=start,
    )

    session_store = InMemorySessionStore()
    inbox_store = InMemoryInboxStore()
    event_store = InMemoryEventStore()
    checkpoint_store = InMemoryCheckpointStore()
    memory_store = InMemoryMemoryStore()
    session_store.create(session)

    for sequence, content in enumerate(("remember alpha", "remember beta", "remember gamma")):
        event_store.append(
            Event(
                event_id=f"sess-memory:event:{sequence}:user_note",
                session_id=session.session_id,
                event_type="user_note",
                sequence=sequence,
                payload={"content": content},
                occurred_at=start + timedelta(seconds=sequence),
            ),
            expected_next_sequence=sequence,
        )

    compactor = MemoryCompactor(
        event_store=event_store,
        memory_store=memory_store,
        checkpoint_store=checkpoint_store,
        clock=clock,
    )
    compaction = compactor.compact(session)

    inbox_store.enqueue(
        Signal(
            signal_id="sig-after-compaction",
            session_id=session.session_id,
            signal_type="user_message",
            payload={"content": "continue"},
            created_at=clock(),
            idempotency_key="after-compaction",
        )
    )
    runner = ActivationRunner(
        agent=agent,
        model=FakeModel(final_answer="context compacted"),
        session_store=session_store,
        inbox_store=inbox_store,
        event_store=event_store,
        checkpoint_store=checkpoint_store,
        context_builder=ContextBuilder(
            event_store=event_store,
            memory_store=memory_store,
            checkpoint_store=checkpoint_store,
            clock=clock,
        ),
        clock=clock,
    )
    activation = runner.run_once(session.session_id)
    return MemoryCompactionSessionResult(compaction=compaction, activation=activation)


class ManualClock:
    def __init__(self, current: datetime) -> None:
        self._current = current

    def __call__(self) -> datetime:
        current = self._current
        self._current = self._current + timedelta(seconds=1)
        return current


if __name__ == "__main__":
    result = run_memory_compaction_session()
    if result.activation.decision is not None:
        print(result.compaction.memory.memory_id, result.activation.decision.payload["content"])
