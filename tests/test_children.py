from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest

import sessgraph as sg


NOW = datetime(2026, 6, 27, 17, 0, tzinfo=timezone.utc)


class ChildSessionTests(unittest.TestCase):
    def test_record_store_and_idempotency(self) -> None:
        child_id = sg.child_session_id_for_decision(
            parent_session_id="sess-1", parent_decision_id="dec-1",
            child_agent_id="child-agent", idempotency_key="child-request-1"
        )
        child = _child(child_id, idempotency_key="child-request-1")
        store = sg.InMemoryChildSessionStore()

        self.assertTrue(child_id.startswith("sess-1:child:"))
        self.assertEqual(sg.ChildSessionRecord.from_dict(child.to_dict()), child)
        self.assertEqual(store.start(child), child)
        self.assertEqual(store.start(child), child)
        self.assertEqual(store.list_for_parent("sess-1"), (child,))
        with self.assertRaises(TypeError):
            store.get(child_id).input["extra"] = "blocked"

        retry = _child("child-retry", parent_decision_id="dec-retry",
                       parent_signal_id="sig-retry", idempotency_key="child-request-1")
        self.assertEqual(store.start(retry), child)
        with self.assertRaises(sg.IdempotencyConflictError):
            store.start(_child(child_id, input_payload={"task": "changed"}))

    def test_runtime_creates_child_session_signal_event_and_checkpoint(self) -> None:
        fx = _fixture(sg.FakeModel(
            kind=sg.DecisionKind.START_CHILD_SESSION,
            child_agent_id="child-agent",
            child_input={"task": "review"},
            child_metadata={"priority": "high"},
            child_context_policy={"max_events": 3},
            child_idempotency_key="child-request-1",
        ))

        result = fx.runner.run_once("sess-1")

        self.assertEqual(result.session.status, sg.SessionStatus.IDLE)
        self.assertEqual(result.child_session_record.status, sg.ChildSessionStatus.STARTED)
        self.assertEqual(result.child_session.agent_id, "child-agent")
        self.assertEqual(fx.child_store.list_for_parent("sess-1"), (result.child_session_record,))
        self.assertEqual(
            [event.event_type for event in result.events],
            ["signal_received", "decision_produced", "child_session_started"],
        )
        child_signal = fx.inbox_store.list_for_session(
            result.child_session_record.child_session_id
        )[0]
        self.assertEqual(child_signal.signal_type, "child_start")
        self.assertEqual(child_signal.payload["input"]["task"], "review")
        self.assertEqual(child_signal.payload["metadata"]["priority"], "high")
        self.assertEqual(child_signal.payload["context_policy"]["max_events"], 3)
        self.assertEqual(
            result.checkpoint.state["child_session_record"]["child_session_id"],
            result.child_session_record.child_session_id,
        )
        self.assertEqual(fx.inbox_store.list_for_session("sess-1"), ())

    def test_policy_denial_skips_child_creation(self) -> None:
        denied = _fixture(
            sg.FakeModel(kind=sg.DecisionKind.START_CHILD_SESSION, child_agent_id="child-agent"),
            include_policy=True,
        )
        result = denied.runner.run_once("sess-1", auth_context=_auth_context())

        self.assertFalse(result.policy_decision.allowed)
        self.assertIsNone(result.child_session_record)
        self.assertEqual(denied.child_store.list_for_parent("sess-1"), ())
        self.assertEqual(result.events[-1].event_type, "authorization_denied")
        self.assertEqual(result.events[-1].payload["action_kind"], "start_child_session")
        self.assertNotIn("child_session_record", result.checkpoint.state)

    def test_policy_grant_and_approval_flow_create_child(self) -> None:
        allowed = _fixture(
            sg.FakeModel(kind=sg.DecisionKind.START_CHILD_SESSION, child_agent_id="child-agent"),
            include_policy=True,
        )
        allowed.grant_store.save(_grant())
        allowed_result = allowed.runner.run_once("sess-1", auth_context=_auth_context())
        self.assertTrue(allowed_result.policy_decision.allowed)
        self.assertEqual(allowed_result.events[-1].event_type, "child_session_started")

        gated = _fixture(
            sg.FakeModel(kind=sg.DecisionKind.START_CHILD_SESSION,
                         child_agent_id="child-agent", child_input={"task": "approved"}),
            include_policy=True,
        )
        gated.grant_store.save(_grant(constraints={"requires_approval": True}))
        requested = gated.runner.run_once("sess-1", auth_context=_auth_context())
        gated.runner.model = ModelShouldNotRun()
        _enqueue_approval_result(gated, requested.approval_request.approval_id)
        approved = gated.runner.run_once("sess-1", auth_context=_auth_context())

        self.assertEqual(requested.session.status, sg.SessionStatus.WAITING)
        self.assertIsNone(requested.child_session_record)
        self.assertEqual(requested.approval_request.action_kind, "start_child_session")
        self.assertEqual(approved.approval_request.status, sg.ApprovalStatus.APPROVED)
        self.assertEqual(approved.child_session_record.parent_signal_id, "sig-1")
        self.assertEqual(approved.child_start_signal.payload["input"]["task"], "approved")
        self.assertEqual(approved.events[-1].event_type, "child_session_started")


class FixedClock:
    def __init__(self, start: datetime) -> None:
        self._current = start

    def __call__(self) -> datetime:
        current = self._current
        self._current = self._current + timedelta(seconds=1)
        return current


def _fixture(
    model: object,
    *,
    include_child_store: bool = True,
    include_policy: bool = False,
) -> SimpleNamespace:
    clock = FixedClock(NOW)
    session_store = sg.InMemorySessionStore()
    inbox_store = sg.InMemoryInboxStore()
    event_store = sg.InMemoryEventStore()
    checkpoint_store = sg.InMemoryCheckpointStore()
    child_store = sg.InMemoryChildSessionStore()
    grant_store = sg.InMemoryCapabilityGrantStore()
    session_store.create(
        sg.Session("sess-1", "agent-1", sg.SessionStatus.IDLE, clock(), clock())
    )
    inbox_store.enqueue(sg.Signal(
        "sig-1", "sess-1", "user_message", {"content": "start child"}, clock(),
        idempotency_key="request-1"
    ))
    runner = sg.ActivationRunner(
        sg.AgentDefinition("agent-1", "Parent Agent", "Return Decisions only."),
        model, session_store, inbox_store, event_store, checkpoint_store,
        child_session_store=child_store if include_child_store else None,
        policy_gate=(sg.InMemoryPolicyGate(grant_store, clock) if include_policy else None),
        approval_store=sg.InMemoryApprovalRequestStore(), clock=clock,
    )
    return SimpleNamespace(
        runner=runner,
        session_store=session_store,
        inbox_store=inbox_store,
        event_store=event_store,
        child_store=child_store,
        grant_store=grant_store,
    )


def _child(
    child_session_id: str,
    *,
    parent_decision_id: str = "dec-1",
    parent_signal_id: str = "sig-1",
    input_payload: dict[str, object] | None = None,
    idempotency_key: str | None = None,
) -> sg.ChildSessionRecord:
    return sg.ChildSessionRecord(
        child_session_id, "sess-1", parent_decision_id, parent_signal_id,
        "child-agent", input_payload or {"task": "review"}, NOW,
        metadata={"priority": "high"}, context_policy={"max_events": 3},
        idempotency_key=idempotency_key,
    )


def _auth_context() -> sg.AuthContext:
    return sg.AuthContext("user-1", "user", True)


def _grant(*, constraints: dict[str, object] | None = None) -> sg.CapabilityGrant:
    return sg.CapabilityGrant(
        "grant-1", "sess-1", "user:user-1", "start_child_session",
        {"child_agent_id": "child-agent"}, NOW,
        agent_id="agent-1", constraints=constraints or {},
    )


def _enqueue_approval_result(fx: SimpleNamespace, approval_id: str) -> sg.Signal:
    return fx.inbox_store.enqueue(sg.Signal(
        "sig-approval-1", "sess-1", "approval_result",
        {"approval_id": approval_id, "approved": True,
         "resolved_by": {"actor_id": "approver"}, "reason": "approved_by_user", "data": {}},
        NOW + timedelta(minutes=1), idempotency_key="approval-result:child",
    ))


class ModelShouldNotRun:
    def decide(self, context: object) -> object:
        raise AssertionError("model must not be called for approval_result signals")


if __name__ == "__main__":
    unittest.main()
