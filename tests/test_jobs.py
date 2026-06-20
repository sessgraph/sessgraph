from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import unittest

from examples.async_job_session import run_async_job_session
from sessgraph import (
    ActivationRunner,
    AgentDefinition,
    ConcurrencyError,
    DecisionKind,
    DecisionRejectedError,
    FakeModel,
    IdempotencyConflictError,
    InMemoryCheckpointStore,
    InMemoryEventStore,
    InMemoryInboxStore,
    InMemoryJobStore,
    InMemorySessionStore,
    JobRecord,
    JobResultDispatcher,
    JobStatus,
    Session,
    SessionStatus,
    Signal,
    ValidationError,
)


NOW = datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc)


class JobRecordTests(unittest.TestCase):
    def test_job_record_round_trips_and_freezes_arguments(self) -> None:
        job = _job("job-1", arguments={"items": [{"n": 1}]})

        restored = JobRecord.from_dict(job.to_dict())

        self.assertEqual(restored, job)
        self.assertEqual(restored.to_dict()["schema_version"], 1)
        with self.assertRaises(TypeError):
            job.arguments["extra"] = "blocked"
        with self.assertRaises(TypeError):
            job.arguments["items"][0]["n"] = 2

    def test_failed_job_requires_error(self) -> None:
        with self.assertRaises(ValidationError):
            JobRecord(
                job_id="job-1",
                session_id="sess-1",
                decision_id="dec-1",
                job_type="export",
                arguments={},
                created_at=NOW,
                status=JobStatus.FAILED,
                started_at=NOW,
                completed_at=NOW,
            )


class InMemoryJobStoreTests(unittest.TestCase):
    def test_lifecycle_success_and_result_enqueue_mark(self) -> None:
        store = InMemoryJobStore()
        job = _job("job-1")

        self.assertEqual(store.submit(job), job)
        running = store.mark_running("job-1", started_at=NOW + timedelta(seconds=1))
        succeeded = store.mark_succeeded(
            "job-1",
            completed_at=NOW + timedelta(seconds=2),
            output={"value": 42},
        )

        self.assertEqual(running.status, JobStatus.RUNNING)
        self.assertEqual(succeeded.status, JobStatus.SUCCEEDED)
        self.assertEqual(succeeded.output["value"], 42)
        self.assertEqual(store.list_completed_pending_result(), (succeeded,))

        enqueued = store.mark_result_enqueued(
            "job-1",
            enqueued_at=NOW + timedelta(seconds=3),
            signal_id="sig-result",
        )

        self.assertEqual(enqueued.result_signal_id, "sig-result")
        self.assertEqual(store.list_completed_pending_result(), ())

    def test_lifecycle_failure_stores_dataized_error(self) -> None:
        store = InMemoryJobStore()
        store.submit(_job("job-1"))
        store.mark_running("job-1", started_at=NOW + timedelta(seconds=1))

        failed = store.mark_failed(
            "job-1",
            completed_at=NOW + timedelta(seconds=2),
            error={"message": "boom"},
        )

        self.assertEqual(failed.status, JobStatus.FAILED)
        self.assertEqual(failed.error["message"], "boom")
        self.assertEqual(failed.output, {})

    def test_submit_is_idempotent_and_rejects_conflicts(self) -> None:
        store = InMemoryJobStore()
        job = _job("job-1", arguments={"n": 1}, idempotency_key="request-1")

        self.assertEqual(store.submit(job), job)
        self.assertEqual(store.submit(job), job)
        self.assertEqual(
            store.submit(
                _job(
                    "job-retry",
                    decision_id="dec-retry",
                    arguments={"n": 1},
                    idempotency_key="request-1",
                )
            ),
            job,
        )

        with self.assertRaises(IdempotencyConflictError):
            store.submit(
                _job(
                    "job-conflict",
                    decision_id="dec-conflict",
                    arguments={"n": 2},
                    idempotency_key="request-1",
                )
            )

        with self.assertRaises(IdempotencyConflictError):
            store.submit(_job("job-1", arguments={"n": 2}))

    def test_invalid_state_transitions_are_rejected(self) -> None:
        store = InMemoryJobStore()
        store.submit(_job("job-1"))

        with self.assertRaises(ConcurrencyError):
            store.mark_succeeded("job-1", completed_at=NOW, output={})

        store.mark_running("job-1", started_at=NOW + timedelta(seconds=1))
        store.mark_succeeded("job-1", completed_at=NOW + timedelta(seconds=2), output={})

        with self.assertRaises(ConcurrencyError):
            store.mark_running("job-1", started_at=NOW + timedelta(seconds=3))


class JobRuntimeTests(unittest.TestCase):
    def test_submit_job_decision_creates_job_and_records_event(self) -> None:
        fixture = _fixture(
            model=FakeModel(
                kind=DecisionKind.SUBMIT_JOB,
                job_type="export",
                job_arguments={"format": "json"},
                job_idempotency_key="job-request-1",
            )
        )

        result = fixture.runner.run_once("sess-1")

        self.assertTrue(result.activated)
        self.assertEqual(result.session.status, SessionStatus.IDLE)
        self.assertEqual(result.decision.kind, DecisionKind.SUBMIT_JOB)
        self.assertEqual(result.job.status, JobStatus.SUBMITTED)
        self.assertEqual(result.job.job_type, "export")
        self.assertEqual(result.job.arguments["format"], "json")
        self.assertEqual(result.job.idempotency_key, "job-request-1")
        self.assertEqual(fixture.job_store.list_for_session("sess-1"), (result.job,))
        self.assertEqual([event.event_type for event in result.events], [
            "signal_received",
            "decision_produced",
            "job_submitted",
        ])
        self.assertEqual(result.checkpoint.event_sequence, 2)
        self.assertEqual(result.checkpoint.state["job"]["job_id"], result.job.job_id)
        self.assertEqual(fixture.inbox_store.list_for_session("sess-1"), ())

    def test_submit_job_requires_job_store(self) -> None:
        fixture = _fixture(
            model=FakeModel(kind=DecisionKind.SUBMIT_JOB),
            include_job_store=False,
        )

        with self.assertRaises(DecisionRejectedError):
            fixture.runner.run_once("sess-1")

        self.assertEqual(fixture.session_store.get("sess-1").status, SessionStatus.IDLE)
        self.assertEqual(fixture.event_store.list_for_session("sess-1"), ())

    def test_dispatcher_enqueues_success_result_and_event_once(self) -> None:
        fixture = _fixture(model=FakeModel(kind=DecisionKind.NOOP))
        job = _completed_job(output={"answer": 42})
        fixture.job_store.submit(_job("job-1"))
        fixture.job_store.mark_running("job-1", started_at=NOW + timedelta(seconds=1))
        fixture.job_store.mark_succeeded(
            "job-1",
            completed_at=NOW + timedelta(seconds=2),
            output=job.output,
        )
        dispatcher = JobResultDispatcher(
            job_store=fixture.job_store,
            inbox_store=fixture.inbox_store,
            event_store=fixture.event_store,
            clock=lambda: NOW + timedelta(seconds=3),
        )

        signals = dispatcher.enqueue_completed()
        repeated = dispatcher.enqueue_completed()

        self.assertEqual(len(signals), 1)
        self.assertEqual(repeated, ())
        self.assertEqual(signals[0].signal_type, "job_result")
        self.assertTrue(signals[0].payload["ok"])
        self.assertEqual(signals[0].payload["output"]["answer"], 42)
        self.assertIsNone(signals[0].payload["error"])
        self.assertEqual(fixture.event_store.list_for_session("sess-1")[0].event_type, (
            "job_result_enqueued"
        ))

    def test_failed_job_result_is_data_not_failed_session(self) -> None:
        fixture = _fixture(model=FakeModel(final_answer="handled failure"), enqueue_signal=False)
        fixture.job_store.submit(_job("job-1"))
        fixture.job_store.mark_running("job-1", started_at=NOW + timedelta(seconds=1))
        fixture.job_store.mark_failed(
            "job-1",
            completed_at=NOW + timedelta(seconds=2),
            error={"message": "boom"},
        )
        dispatcher = JobResultDispatcher(
            job_store=fixture.job_store,
            inbox_store=fixture.inbox_store,
            event_store=fixture.event_store,
            clock=lambda: NOW + timedelta(seconds=3),
        )
        signals = dispatcher.enqueue_completed()

        result = fixture.runner.run_once("sess-1")

        self.assertEqual(signals[0].payload["ok"], False)
        self.assertEqual(signals[0].payload["error"]["message"], "boom")
        self.assertTrue(result.activated)
        self.assertEqual(result.signal.signal_type, "job_result")
        self.assertEqual(result.session.status, SessionStatus.COMPLETED)
        self.assertEqual(result.decision.payload["content"], "handled failure")

    def test_async_job_example_smoke(self) -> None:
        result = run_async_job_session()

        self.assertEqual(result.submit_activation.job.status, JobStatus.SUBMITTED)
        self.assertEqual(len(result.result_signals), 1)
        self.assertTrue(result.result_signals[0].payload["ok"])
        self.assertEqual(result.result_signals[0].payload["output"]["summary"], "job complete")
        self.assertTrue(result.result_activation.activated)
        self.assertEqual(result.result_activation.session.status, SessionStatus.COMPLETED)
        self.assertEqual(result.result_activation.decision.payload["content"], "job complete")


@dataclass
class RuntimeFixture:
    runner: ActivationRunner
    session_store: InMemorySessionStore
    inbox_store: InMemoryInboxStore
    event_store: InMemoryEventStore
    checkpoint_store: InMemoryCheckpointStore
    job_store: InMemoryJobStore


class ManualClock:
    def __init__(self, current: datetime) -> None:
        self._current = current

    def __call__(self) -> datetime:
        return self._current


def _fixture(
    *,
    model: object,
    include_job_store: bool = True,
    enqueue_signal: bool = True,
) -> RuntimeFixture:
    clock = ManualClock(NOW)
    agent = AgentDefinition(
        agent_id="agent-1",
        name="Test Agent",
        instructions="Return Decisions only.",
    )
    session = Session(
        session_id="sess-1",
        agent_id="agent-1",
        status=SessionStatus.IDLE,
        created_at=NOW,
        updated_at=NOW,
    )
    session_store = InMemorySessionStore()
    inbox_store = InMemoryInboxStore()
    event_store = InMemoryEventStore()
    checkpoint_store = InMemoryCheckpointStore()
    job_store = InMemoryJobStore()
    session_store.create(session)
    if enqueue_signal:
        inbox_store.enqueue(
            Signal(
                signal_id="sig-1",
                session_id="sess-1",
                signal_type="user_message",
                payload={"content": "hello"},
                created_at=NOW,
                idempotency_key="request-1",
            )
        )
    runner = ActivationRunner(
        agent=agent,
        model=model,
        session_store=session_store,
        inbox_store=inbox_store,
        event_store=event_store,
        checkpoint_store=checkpoint_store,
        job_store=job_store if include_job_store else None,
        clock=clock,
    )
    return RuntimeFixture(
        runner=runner,
        session_store=session_store,
        inbox_store=inbox_store,
        event_store=event_store,
        checkpoint_store=checkpoint_store,
        job_store=job_store,
    )


def _job(
    job_id: str,
    *,
    decision_id: str = "dec-1",
    job_type: str = "export",
    arguments: dict[str, object] | None = None,
    idempotency_key: str | None = None,
) -> JobRecord:
    return JobRecord(
        job_id=job_id,
        session_id="sess-1",
        decision_id=decision_id,
        job_type=job_type,
        arguments=arguments or {},
        created_at=NOW,
        idempotency_key=idempotency_key,
    )


def _completed_job(*, output: dict[str, object]) -> JobRecord:
    return JobRecord(
        job_id="job-1",
        session_id="sess-1",
        decision_id="dec-1",
        job_type="export",
        arguments={},
        created_at=NOW,
        status=JobStatus.SUCCEEDED,
        started_at=NOW + timedelta(seconds=1),
        completed_at=NOW + timedelta(seconds=2),
        output=output,
    )


if __name__ == "__main__":
    unittest.main()
