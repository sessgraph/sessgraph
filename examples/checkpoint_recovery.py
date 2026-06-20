from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sessgraph import (
    ActivationResult,
    ActivationRunner,
    AgentDefinition,
    Checkpoint,
    FakeModel,
    InMemoryCheckpointStore,
    InMemoryEventStore,
    InMemoryInboxStore,
    InMemorySessionStore,
    Session,
    SessionStatus,
    Signal,
)


@dataclass(frozen=True, slots=True)
class CheckpointRecoveryResult:
    activation: ActivationResult
    checkpoint: Checkpoint
    recovered_session: Session


def run_checkpoint_recovery() -> CheckpointRecoveryResult:
    clock = FixedClock(datetime(2026, 6, 20, 10, 0, tzinfo=timezone.utc))
    agent = AgentDefinition(
        agent_id="agent-recovery",
        name="Recovery Agent",
        instructions="Return a final_answer Decision.",
    )
    session = Session(
        session_id="sess-recovery",
        agent_id=agent.agent_id,
        status=SessionStatus.IDLE,
        created_at=clock(),
        updated_at=clock(),
    )
    signal = Signal(
        signal_id="sig-recovery",
        session_id=session.session_id,
        signal_type="user_message",
        payload={"content": "recover me"},
        created_at=clock(),
        idempotency_key="recovery-example-1",
    )

    session_store = InMemorySessionStore()
    inbox_store = InMemoryInboxStore()
    event_store = InMemoryEventStore()
    checkpoint_store = InMemoryCheckpointStore()
    session_store.create(session)
    inbox_store.enqueue(signal)

    runner = ActivationRunner(
        agent=agent,
        model=FakeModel(final_answer="checkpoint saved"),
        session_store=session_store,
        inbox_store=inbox_store,
        event_store=event_store,
        checkpoint_store=checkpoint_store,
        clock=clock,
    )
    activation = runner.run_once(session.session_id)
    checkpoint = checkpoint_store.latest_for_session(session.session_id)
    if checkpoint is None:
        raise RuntimeError("checkpoint was not saved")

    recovered_session = Session.from_dict(checkpoint.state["session"])
    return CheckpointRecoveryResult(
        activation=activation,
        checkpoint=checkpoint,
        recovered_session=recovered_session,
    )


class FixedClock:
    def __init__(self, start: datetime) -> None:
        self._current = start

    def __call__(self) -> datetime:
        current = self._current
        self._current = self._current + timedelta(seconds=1)
        return current


if __name__ == "__main__":
    result = run_checkpoint_recovery()
    print(
        result.recovered_session.session_id,
        result.recovered_session.status.value,
        result.recovered_session.revision,
        result.checkpoint.event_sequence,
    )
