from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import unittest

from sessgraph import (
    ActivationRunner,
    AgentDefinition,
    DecisionKind,
    FakeModel,
    InMemoryCheckpointStore,
    InMemoryEventStore,
    InMemoryInboxStore,
    InMemorySessionStore,
    Session,
    SessionStatus,
    Signal,
)


NOW = datetime(2026, 6, 14, 12, 0, tzinfo=timezone.utc)


class WaitResumeTests(unittest.TestCase):
    def test_ask_user_puts_session_into_waiting(self) -> None:
        fixture = _fixture(model=FakeModel(kind=DecisionKind.ASK_USER, question="Need input?"))

        result = fixture.runner.run_once("sess-1")

        self.assertTrue(result.activated)
        self.assertEqual(result.session.status, SessionStatus.WAITING)
        self.assertEqual(result.session.revision, 2)
        self.assertEqual(result.decision.kind, DecisionKind.ASK_USER)
        self.assertEqual(result.decision.payload["question"], "Need input?")
        self.assertEqual([event.event_type for event in result.events], [
            "signal_received",
            "decision_produced",
        ])
        self.assertEqual(fixture.inbox_store.list_for_session("sess-1"), ())
        self.assertEqual(result.checkpoint.state["decision"]["payload"]["question"], "Need input?")

    def test_waiting_session_without_signal_is_inactive(self) -> None:
        fixture = _fixture(model=FakeModel(kind=DecisionKind.ASK_USER))
        waiting = fixture.runner.run_once("sess-1").session
        idle_result = fixture.runner.run_once("sess-1")

        self.assertFalse(idle_result.activated)
        self.assertEqual(idle_result.session, waiting)
        self.assertEqual(fixture.event_store.next_sequence("sess-1"), 2)

    def test_user_message_resumes_waiting_session(self) -> None:
        fixture = _fixture(model=FakeModel(kind=DecisionKind.ASK_USER, question="Need input?"))
        waiting = fixture.runner.run_once("sess-1").session
        fixture.inbox_store.enqueue(
            Signal(
                signal_id="sig-resume-1",
                session_id="sess-1",
                signal_type="user_message",
                payload={"content": "continue"},
                created_at=fixture.clock(),
                idempotency_key="resume-1",
            )
        )
        resume_runner = ActivationRunner(
            agent=fixture.agent,
            model=FakeModel(final_answer="resumed"),
            session_store=fixture.session_store,
            inbox_store=fixture.inbox_store,
            event_store=fixture.event_store,
            checkpoint_store=fixture.checkpoint_store,
            clock=fixture.clock,
        )

        result = resume_runner.run_once("sess-1")

        self.assertEqual(waiting.status, SessionStatus.WAITING)
        self.assertTrue(result.activated)
        self.assertEqual(result.session.status, SessionStatus.COMPLETED)
        self.assertEqual(result.session.revision, 4)
        self.assertEqual(result.decision.kind, DecisionKind.FINAL_ANSWER)
        self.assertEqual(result.decision.payload["content"], "resumed")
        self.assertEqual([event.sequence for event in result.events], [2, 3])
        self.assertEqual(fixture.event_store.next_sequence("sess-1"), 4)
        self.assertEqual(fixture.inbox_store.list_for_session("sess-1"), ())
        self.assertEqual(result.checkpoint.session_revision, 4)
        self.assertEqual(result.checkpoint.event_sequence, 3)


@dataclass
class WaitFixture:
    agent: AgentDefinition
    runner: ActivationRunner
    session_store: InMemorySessionStore
    inbox_store: InMemoryInboxStore
    event_store: InMemoryEventStore
    checkpoint_store: InMemoryCheckpointStore
    clock: "FixedClock"


class FixedClock:
    def __init__(self, start: datetime) -> None:
        self._current = start

    def __call__(self) -> datetime:
        current = self._current
        self._current = self._current + timedelta(seconds=1)
        return current


def _fixture(*, model: FakeModel) -> WaitFixture:
    clock = FixedClock(NOW)
    agent = AgentDefinition(
        agent_id="agent-1",
        name="Wait Agent",
        instructions="Ask user when needed.",
    )
    session = Session(
        session_id="sess-1",
        agent_id=agent.agent_id,
        status=SessionStatus.IDLE,
        created_at=clock(),
        updated_at=clock(),
    )
    signal = Signal(
        signal_id="sig-1",
        session_id="sess-1",
        signal_type="user_message",
        payload={"content": "start"},
        created_at=clock(),
        idempotency_key="start-1",
    )
    session_store = InMemorySessionStore()
    inbox_store = InMemoryInboxStore()
    event_store = InMemoryEventStore()
    checkpoint_store = InMemoryCheckpointStore()
    session_store.create(session)
    inbox_store.enqueue(signal)

    return WaitFixture(
        agent=agent,
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
        clock=clock,
    )


if __name__ == "__main__":
    unittest.main()
