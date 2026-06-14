from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import unittest

from examples.basic_session import run_basic_session
from sessgraph import (
    ActivationContext,
    ActivationRunner,
    AgentDefinition,
    Decision,
    DecisionKind,
    DecisionRejectedError,
    FakeModel,
    InMemoryCheckpointStore,
    InMemoryEventStore,
    InMemoryInboxStore,
    InMemorySessionStore,
    RecordNotFoundError,
    Session,
    SessionStatus,
    Signal,
)


NOW = datetime(2026, 6, 14, 11, 0, tzinfo=timezone.utc)


class ActivationRunnerTests(unittest.TestCase):
    def test_run_once_final_answer_completes_session_and_checkpoints(self) -> None:
        fixture = _fixture(model=FakeModel(final_answer="done"))

        result = fixture.runner.run_once("sess-1")

        self.assertTrue(result.activated)
        self.assertEqual(result.session.status, SessionStatus.COMPLETED)
        self.assertEqual(result.session.revision, 2)
        self.assertEqual(result.decision.kind, DecisionKind.FINAL_ANSWER)
        self.assertEqual(result.decision.payload["content"], "done")
        self.assertEqual([event.event_type for event in result.events], [
            "signal_received",
            "decision_produced",
        ])
        self.assertEqual([event.sequence for event in result.events], [0, 1])
        self.assertEqual(fixture.event_store.next_sequence("sess-1"), 2)
        self.assertEqual(fixture.inbox_store.list_for_session("sess-1"), ())

        latest = fixture.checkpoint_store.latest_for_session("sess-1")
        self.assertEqual(latest, result.checkpoint)
        self.assertEqual(latest.session_revision, 2)
        self.assertEqual(latest.event_sequence, 1)
        self.assertEqual(latest.state["decision"]["payload"]["content"], "done")
        self.assertEqual(latest.state["event_ids"], (
            "sess-1:event:0:signal_received",
            "sess-1:event:1:decision_produced",
        ))

    def test_run_once_noop_returns_session_to_idle(self) -> None:
        fixture = _fixture(model=FakeModel(kind=DecisionKind.NOOP))

        result = fixture.runner.run_once("sess-1")

        self.assertTrue(result.activated)
        self.assertEqual(result.session.status, SessionStatus.IDLE)
        self.assertEqual(result.session.revision, 2)
        self.assertEqual(result.decision.kind, DecisionKind.NOOP)
        self.assertEqual(fixture.checkpoint_store.latest_for_session("sess-1"), result.checkpoint)

    def test_run_once_without_pending_signal_is_inactive(self) -> None:
        fixture = _fixture(enqueue_signal=False)

        result = fixture.runner.run_once("sess-1")

        self.assertFalse(result.activated)
        self.assertEqual(result.session.status, SessionStatus.IDLE)
        self.assertIsNone(result.decision)
        self.assertEqual(fixture.event_store.list_for_session("sess-1"), ())
        self.assertIsNone(fixture.checkpoint_store.latest_for_session("sess-1"))

    def test_run_once_requires_existing_session(self) -> None:
        fixture = _fixture(enqueue_signal=False)

        with self.assertRaises(RecordNotFoundError):
            fixture.runner.run_once("missing")

    def test_runner_rejects_decision_for_different_session(self) -> None:
        fixture = _fixture(model=WrongSessionModel())

        with self.assertRaises(DecisionRejectedError):
            fixture.runner.run_once("sess-1")

        self.assertEqual(fixture.session_store.get("sess-1").status, SessionStatus.IDLE)
        self.assertEqual(fixture.session_store.get("sess-1").revision, 0)
        self.assertEqual(fixture.inbox_store.list_for_session("sess-1")[0].signal_id, "sig-1")
        self.assertEqual(fixture.event_store.list_for_session("sess-1"), ())
        self.assertIsNone(fixture.checkpoint_store.latest_for_session("sess-1"))

    def test_basic_session_example_smoke(self) -> None:
        result = run_basic_session()

        self.assertTrue(result.activated)
        self.assertEqual(result.session.status, SessionStatus.COMPLETED)
        self.assertEqual(result.decision.payload["content"], "hello SessGraph")


@dataclass
class RunnerFixture:
    runner: ActivationRunner
    session_store: InMemorySessionStore
    inbox_store: InMemoryInboxStore
    event_store: InMemoryEventStore
    checkpoint_store: InMemoryCheckpointStore


@dataclass(frozen=True, slots=True)
class WrongSessionModel:
    def decide(self, context: ActivationContext) -> Decision:
        return Decision(
            decision_id="wrong-session-decision",
            session_id="other-session",
            kind=DecisionKind.FINAL_ANSWER,
            payload={"content": "bad"},
            created_at=context.now,
        )


class FixedClock:
    def __init__(self, start: datetime) -> None:
        self._current = start

    def __call__(self) -> datetime:
        current = self._current
        self._current = self._current + timedelta(seconds=1)
        return current


def _fixture(
    *,
    model: object = FakeModel(),
    enqueue_signal: bool = True,
) -> RunnerFixture:
    clock = FixedClock(NOW)
    agent = AgentDefinition(
        agent_id="agent-1",
        name="Test Agent",
        instructions="Return Decisions only.",
    )
    session = Session(
        session_id="sess-1",
        agent_id="agent-1",
        status=SessionStatus.IDLE,
        created_at=clock(),
        updated_at=clock(),
    )

    session_store = InMemorySessionStore()
    inbox_store = InMemoryInboxStore()
    event_store = InMemoryEventStore()
    checkpoint_store = InMemoryCheckpointStore()
    session_store.create(session)
    if enqueue_signal:
        inbox_store.enqueue(
            Signal(
                signal_id="sig-1",
                session_id="sess-1",
                signal_type="user_message",
                payload={"content": "hello"},
                created_at=clock(),
                idempotency_key="request-1",
            )
        )

    return RunnerFixture(
        runner=ActivationRunner(
            agent=agent,
            model=model,
            session_store=session_store,
            inbox_store=inbox_store,
            event_store=event_store,
            checkpoint_store=checkpoint_store,
            clock=clock,
        ),
        session_store=session_store,
        inbox_store=inbox_store,
        event_store=event_store,
        checkpoint_store=checkpoint_store,
    )


if __name__ == "__main__":
    unittest.main()
