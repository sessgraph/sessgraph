from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sessgraph import (
    ActivationResult,
    ActivationRunner,
    AgentDefinition,
    DecisionKind,
    FakeModel,
    InMemoryCheckpointStore,
    InMemoryEventStore,
    InMemoryInboxStore,
    InMemoryJobStore,
    InMemorySessionStore,
    JobRecord,
    JobResultDispatcher,
    Session,
    SessionStatus,
    Signal,
)


@dataclass(frozen=True, slots=True)
class AsyncJobSessionResult:
    job: JobRecord
    result_signals: tuple[Signal, ...]
    submit_activation: ActivationResult
    result_activation: ActivationResult


def run_async_job_session() -> AsyncJobSessionResult:
    start = datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc)
    clock = ManualClock(start)
    agent = AgentDefinition(
        agent_id="agent-job",
        name="Async Job Agent",
        instructions="Return Decisions only.",
    )
    session = Session(
        session_id="sess-job",
        agent_id=agent.agent_id,
        status=SessionStatus.IDLE,
        created_at=start,
        updated_at=start,
    )

    session_store = InMemorySessionStore()
    inbox_store = InMemoryInboxStore()
    event_store = InMemoryEventStore()
    checkpoint_store = InMemoryCheckpointStore()
    job_store = InMemoryJobStore()
    session_store.create(session)
    inbox_store.enqueue(
        Signal(
            signal_id="sig-submit-job",
            session_id=session.session_id,
            signal_type="user_message",
            payload={"content": "run async job"},
            created_at=start,
            idempotency_key="submit-job-example",
        )
    )

    submit_runner = ActivationRunner(
        agent=agent,
        model=FakeModel(
            kind=DecisionKind.SUBMIT_JOB,
            job_type="summarize",
            job_arguments={"topic": "jobs"},
            job_idempotency_key="job-example-1",
        ),
        session_store=session_store,
        inbox_store=inbox_store,
        event_store=event_store,
        checkpoint_store=checkpoint_store,
        job_store=job_store,
        clock=clock,
    )
    submit_activation = submit_runner.run_once(session.session_id)

    clock.set(start + timedelta(minutes=1))
    running = job_store.mark_running(submit_activation.job.job_id, started_at=clock())
    clock.set(start + timedelta(minutes=2))
    job = job_store.mark_succeeded(
        running.job_id,
        completed_at=clock(),
        output={"summary": "job complete"},
    )
    clock.set(start + timedelta(minutes=3))
    dispatcher = JobResultDispatcher(
        job_store=job_store,
        inbox_store=inbox_store,
        event_store=event_store,
        clock=clock,
    )
    result_signals = dispatcher.enqueue_completed()

    clock.set(start + timedelta(minutes=4))
    result_runner = ActivationRunner(
        agent=agent,
        model=FakeModel(final_answer="job complete"),
        session_store=session_store,
        inbox_store=inbox_store,
        event_store=event_store,
        checkpoint_store=checkpoint_store,
        job_store=job_store,
        clock=clock,
    )
    result_activation = result_runner.run_once(session.session_id)
    return AsyncJobSessionResult(
        job=job,
        result_signals=result_signals,
        submit_activation=submit_activation,
        result_activation=result_activation,
    )


class ManualClock:
    def __init__(self, current: datetime) -> None:
        self._current = current

    def __call__(self) -> datetime:
        return self._current

    def set(self, current: datetime) -> None:
        self._current = current


if __name__ == "__main__":
    result = run_async_job_session()
    if result.result_activation.decision is not None:
        print(result.result_activation.decision.payload["content"])
