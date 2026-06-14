from __future__ import annotations

from datetime import datetime, timezone
from math import inf, nan
import unittest

from sessgraph import (
    AgentDefinition,
    Checkpoint,
    Decision,
    DecisionKind,
    Event,
    Session,
    SessionStatus,
    Signal,
    ValidationError,
)


NOW = datetime(2026, 6, 12, 15, 30, tzinfo=timezone.utc)


class CoreModelTests(unittest.TestCase):
    def test_agent_definition_round_trips(self) -> None:
        agent = AgentDefinition(
            agent_id="agent-1",
            name="Planner",
            instructions="Return Decisions only.",
            metadata={"owner": "core", "limits": {"parallel": 1}},
        )

        restored = AgentDefinition.from_dict(agent.to_dict())

        self.assertEqual(restored, agent)
        self.assertEqual(restored.to_dict()["schema_version"], 1)

    def test_session_validates_lifecycle_fields(self) -> None:
        session = Session(
            session_id="sess-1",
            agent_id="agent-1",
            status="idle",
            created_at=NOW,
            updated_at=NOW,
            revision=0,
        )

        self.assertEqual(session.status, SessionStatus.IDLE)
        self.assertEqual(Session.from_dict(session.to_dict()), session)

        with self.assertRaises(ValidationError):
            Session(
                session_id="sess-1",
                agent_id="agent-1",
                status="missing",
                created_at=NOW,
                updated_at=NOW,
            )

        with self.assertRaises(ValidationError):
            Session(
                session_id="sess-1",
                agent_id="agent-1",
                status=SessionStatus.IDLE,
                created_at=NOW,
                updated_at=datetime(2026, 6, 12, 15, 29, tzinfo=timezone.utc),
            )

    def test_signal_round_trips_with_idempotency_key(self) -> None:
        signal = Signal(
            signal_id="sig-1",
            session_id="sess-1",
            signal_type="user_message",
            payload={"content": "hello"},
            created_at=NOW,
            idempotency_key="client-request-1",
        )

        restored = Signal.from_dict(signal.to_dict())

        self.assertEqual(restored, signal)
        self.assertEqual(restored.idempotency_key, "client-request-1")

    def test_event_round_trips_with_sequence_and_source_signal(self) -> None:
        event = Event(
            event_id="evt-1",
            session_id="sess-1",
            event_type="signal_received",
            sequence=0,
            payload={"signal_type": "user_message"},
            occurred_at=NOW,
            source_signal_id="sig-1",
        )

        restored = Event.from_dict(event.to_dict())

        self.assertEqual(restored, event)
        self.assertEqual(restored.sequence, 0)
        self.assertEqual(restored.source_signal_id, "sig-1")

    def test_decision_round_trips_and_validates_final_answer(self) -> None:
        decision = Decision(
            decision_id="dec-1",
            session_id="sess-1",
            kind="final_answer",
            payload={"content": "done"},
            created_at=NOW,
        )

        restored = Decision.from_dict(decision.to_dict())

        self.assertEqual(restored, decision)
        self.assertEqual(restored.kind, DecisionKind.FINAL_ANSWER)

        with self.assertRaises(ValidationError):
            Decision(
                decision_id="dec-2",
                session_id="sess-1",
                kind=DecisionKind.FINAL_ANSWER,
                payload={},
                created_at=NOW,
            )

    def test_decision_round_trips_and_validates_tool_call(self) -> None:
        decision = Decision(
            decision_id="dec-tool-1",
            session_id="sess-1",
            kind="tool_call",
            payload={"tool_name": "echo", "arguments": {"text": "hello"}},
            created_at=NOW,
        )

        restored = Decision.from_dict(decision.to_dict())

        self.assertEqual(restored, decision)
        self.assertEqual(restored.kind, DecisionKind.TOOL_CALL)

        invalid_payloads = (
            {},
            {"tool_name": "", "arguments": {}},
            {"tool_name": "echo"},
            {"tool_name": "echo", "arguments": []},
        )
        for payload in invalid_payloads:
            with self.assertRaises(ValidationError):
                Decision(
                    decision_id="dec-tool-invalid",
                    session_id="sess-1",
                    kind=DecisionKind.TOOL_CALL,
                    payload=payload,
                    created_at=NOW,
                )

    def test_decision_round_trips_and_validates_ask_user(self) -> None:
        decision = Decision(
            decision_id="dec-ask-1",
            session_id="sess-1",
            kind="ask_user",
            payload={"question": "What should I do next?"},
            created_at=NOW,
        )

        restored = Decision.from_dict(decision.to_dict())

        self.assertEqual(restored, decision)
        self.assertEqual(restored.kind, DecisionKind.ASK_USER)

        for payload in ({}, {"question": ""}):
            with self.assertRaises(ValidationError):
                Decision(
                    decision_id="dec-ask-invalid",
                    session_id="sess-1",
                    kind=DecisionKind.ASK_USER,
                    payload=payload,
                    created_at=NOW,
                )

    def test_checkpoint_round_trips(self) -> None:
        checkpoint = Checkpoint(
            checkpoint_id="chk-1",
            session_id="sess-1",
            session_revision=3,
            event_sequence=7,
            state={"status": "idle", "scratch": ["a", "b"]},
            created_at=NOW,
        )

        self.assertEqual(Checkpoint.from_dict(checkpoint.to_dict()), checkpoint)

    def test_serialization_rejects_invalid_schema_version(self) -> None:
        data = {
            "schema_version": 2,
            "agent_id": "agent-1",
            "name": "Planner",
            "instructions": "Return Decisions only.",
            "version": 1,
            "metadata": {},
        }

        with self.assertRaises(ValidationError):
            AgentDefinition.from_dict(data)

    def test_json_payloads_are_strict_and_copied(self) -> None:
        payload = {"items": [{"n": 1}]}
        signal = Signal(
            signal_id="sig-1",
            session_id="sess-1",
            signal_type="user_message",
            payload=payload,
            created_at=NOW,
        )
        payload["items"][0]["n"] = 2

        self.assertEqual(signal.payload["items"][0]["n"], 1)

        with self.assertRaises(TypeError):
            signal.payload["extra"] = "blocked"

        with self.assertRaises(TypeError):
            signal.payload["items"][0]["n"] = 3

        with self.assertRaises(ValidationError):
            Signal(
                signal_id="sig-2",
                session_id="sess-1",
                signal_type="user_message",
                payload={1: "bad"},
                created_at=NOW,
            )

        for invalid in (nan, inf):
            with self.assertRaises(ValidationError):
                Signal(
                    signal_id="sig-3",
                    session_id="sess-1",
                    signal_type="user_message",
                    payload={"value": invalid},
                    created_at=NOW,
                )

    def test_datetimes_must_be_timezone_aware(self) -> None:
        with self.assertRaises(ValidationError):
            Signal(
                signal_id="sig-1",
                session_id="sess-1",
                signal_type="user_message",
                payload={},
                created_at=datetime(2026, 6, 12, 15, 30),
            )


if __name__ == "__main__":
    unittest.main()
