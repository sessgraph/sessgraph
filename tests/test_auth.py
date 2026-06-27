from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import unittest

from sessgraph import (
    ActivationRunner,
    AgentDefinition,
    ApprovalRequest,
    ApprovalStatus,
    AuthContext,
    CapabilityGrant,
    ConcurrencyError,
    DecisionKind,
    FakeModel,
    IdempotencyConflictError,
    InMemoryApprovalRequestStore,
    InMemoryCapabilityGrantStore,
    InMemoryCheckpointStore,
    InMemoryEventStore,
    InMemoryInboxStore,
    InMemoryJobStore,
    InMemoryPolicyGate,
    InMemorySessionStore,
    PolicyDecision,
    Session,
    SessionStatus,
    Signal,
    SyncToolExecutor,
    ToolRegistry,
    ToolSpec,
    ValidationError,
    approval_request_id,
    capability_grant_id,
)


NOW = datetime(2026, 6, 23, 16, 0, tzinfo=timezone.utc)


class AuthModelTests(unittest.TestCase):
    def test_auth_context_round_trips_and_freezes_claims(self) -> None:
        context = AuthContext(
            actor_id="user-1",
            actor_type="user",
            authenticated=True,
            scopes=("tools:use",),
            claims={"profile": {"tier": "admin"}},
        )

        restored = AuthContext.from_dict(context.to_dict())

        self.assertEqual(restored, context)
        self.assertEqual(restored.subject, "user:user-1")
        with self.assertRaises(TypeError):
            restored.claims["extra"] = "blocked"
        with self.assertRaises(TypeError):
            restored.claims["profile"]["tier"] = "changed"

    def test_capability_grant_round_trips_and_has_deterministic_id(self) -> None:
        grant_id = capability_grant_id(
            session_id="sess-1",
            subject="user:user-1",
            action_kind="tool_call",
            resource={"tool_name": "uppercase"},
        )
        grant = _grant(grant_id=grant_id)

        restored = CapabilityGrant.from_dict(grant.to_dict())

        self.assertEqual(restored, grant)
        self.assertTrue(grant_id.startswith("sess-1:grant:"))
        self.assertTrue(restored.is_active(NOW + timedelta(minutes=1)))

    def test_grant_store_is_idempotent_and_rejects_conflicts(self) -> None:
        store = InMemoryCapabilityGrantStore()
        grant = _grant(idempotency_key="grant-request-1")

        self.assertEqual(store.save(grant), grant)
        self.assertEqual(store.save(grant), grant)
        self.assertEqual(store.get(grant.grant_id), grant)
        self.assertEqual(store.list_for_session("sess-1"), (grant,))

        with self.assertRaises(TypeError):
            store.get(grant.grant_id).resource["extra"] = "blocked"

        with self.assertRaises(IdempotencyConflictError):
            store.save(_grant(resource={"tool_name": "other"}))

        with self.assertRaises(IdempotencyConflictError):
            store.save(_grant(grant_id="grant-2", idempotency_key="grant-request-1"))


class ApprovalRequestModelTests(unittest.TestCase):
    def test_approval_request_round_trips_and_has_deterministic_id(self) -> None:
        approval_id = approval_request_id(
            session_id="sess-1",
            decision_id="dec-1",
            action_kind="tool_call",
            resource={"tool_name": "uppercase"},
            idempotency_key="approval-request-1",
        )
        approval = _approval_request(
            approval_id=approval_id,
            idempotency_key="approval-request-1",
        )

        restored = ApprovalRequest.from_dict(approval.to_dict())

        self.assertEqual(restored, approval)
        self.assertFalse(restored.is_terminal)
        self.assertTrue(approval_id.startswith("sess-1:approval:"))
        with self.assertRaises(TypeError):
            restored.resource["extra"] = "blocked"
        with self.assertRaises(TypeError):
            restored.action_payload["arguments"]["text"] = "changed"

    def test_approval_request_requires_consistent_lifecycle_fields(self) -> None:
        with self.assertRaises(ValidationError):
            _approval_request(resolved_at=NOW)

        with self.assertRaises(ValidationError):
            _approval_request(status=ApprovalStatus.APPROVED)

        with self.assertRaises(ValidationError):
            _approval_request(
                status=ApprovalStatus.APPROVED,
                resolved_at=NOW - timedelta(seconds=1),
                resolved_by=_actor("approver"),
            )


class InMemoryApprovalRequestStoreTests(unittest.TestCase):
    def test_create_get_and_list_return_snapshots(self) -> None:
        store = InMemoryApprovalRequestStore()
        later = _approval_request(
            approval_id="approval-2",
            decision_id="dec-2",
            created_at=NOW + timedelta(seconds=1),
        )
        earlier = _approval_request(approval_id="approval-1", decision_id="dec-1")

        self.assertEqual(store.create(later), later)
        self.assertEqual(store.create(earlier), earlier)

        self.assertEqual(store.get("approval-1"), earlier)
        self.assertEqual(store.list_for_session("sess-1"), (earlier, later))
        self.assertEqual(store.list_pending_for_session("sess-1"), (earlier, later))
        with self.assertRaises(TypeError):
            store.get("approval-1").data["extra"] = "blocked"

    def test_create_is_idempotent_and_rejects_conflicts(self) -> None:
        store = InMemoryApprovalRequestStore()
        approval = _approval_request(idempotency_key="approval-request-1")

        self.assertEqual(store.create(approval), approval)
        self.assertEqual(store.create(approval), approval)

        with self.assertRaises(IdempotencyConflictError):
            store.create(_approval_request(resource={"tool_name": "other"}))

        with self.assertRaises(IdempotencyConflictError):
            store.create(
                _approval_request(
                    approval_id="approval-2",
                    idempotency_key="approval-request-1",
                )
            )

        with self.assertRaises(ValidationError):
            store.create(
                _approval_request(
                    status=ApprovalStatus.DENIED,
                    resolved_at=NOW + timedelta(seconds=1),
                    resolved_by=_actor("approver"),
                )
            )

    def test_resolve_terminal_status_and_idempotency(self) -> None:
        store = InMemoryApprovalRequestStore()
        approval = _approval_request(idempotency_key="approval-request-1")
        store.create(approval)

        resolved = store.resolve(
            "approval-1",
            status=ApprovalStatus.APPROVED,
            resolved_at=NOW + timedelta(seconds=5),
            resolved_by=_actor("approver"),
            reason="approved_by_user",
            data={"ticket": "APP-1"},
        )

        self.assertEqual(resolved.status, ApprovalStatus.APPROVED)
        self.assertTrue(resolved.is_terminal)
        self.assertEqual(resolved.resolved_by["actor_id"], "approver")
        self.assertEqual(resolved.data["ticket"], "APP-1")
        self.assertEqual(store.list_pending_for_session("sess-1"), ())
        self.assertEqual(
            store.resolve(
                "approval-1",
                status=ApprovalStatus.APPROVED,
                resolved_at=NOW + timedelta(seconds=5),
                resolved_by=_actor("approver"),
                reason="approved_by_user",
                data={"ticket": "APP-1"},
            ),
            resolved,
        )

        with self.assertRaises(ConcurrencyError):
            store.resolve(
                "approval-1",
                status=ApprovalStatus.DENIED,
                resolved_at=NOW + timedelta(seconds=6),
                resolved_by=_actor("approver"),
                reason="changed_mind",
            )

    def test_resolve_rejects_pending_status(self) -> None:
        store = InMemoryApprovalRequestStore()
        store.create(_approval_request())

        with self.assertRaises(ValidationError):
            store.resolve(
                "approval-1",
                status=ApprovalStatus.PENDING,
                resolved_at=NOW + timedelta(seconds=1),
                resolved_by=_actor("approver"),
                reason="not_terminal",
            )


class InMemoryPolicyGateTests(unittest.TestCase):
    def test_policy_gate_allows_matching_active_grant(self) -> None:
        store = InMemoryCapabilityGrantStore()
        auth_context = _auth_context(scopes=("tools:use",))
        store.save(_grant(constraints={"required_scopes": ["tools:use"]}))
        gate = InMemoryPolicyGate(grant_store=store, clock=lambda: NOW + timedelta(seconds=1))

        decision = gate.authorize(
            session=_session(),
            auth_context=auth_context,
            action_kind="tool_call",
            resource={"tool_name": "uppercase", "arguments_shape": "json_object"},
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reason, "capability_granted")
        self.assertEqual(decision.grant_id, "grant-1")
        self.assertEqual(PolicyDecision.from_dict(decision.to_dict()), decision)

    def test_policy_gate_denies_missing_or_unmatched_capability(self) -> None:
        store = InMemoryCapabilityGrantStore()
        store.save(_grant(resource={"tool_name": "uppercase"}))
        gate = InMemoryPolicyGate(grant_store=store, clock=lambda: NOW)

        missing_auth = gate.authorize(
            session=_session(),
            auth_context=None,
            action_kind="tool_call",
            resource={"tool_name": "uppercase"},
        )
        resource_mismatch = gate.authorize(
            session=_session(),
            auth_context=_auth_context(),
            action_kind="tool_call",
            resource={"tool_name": "other"},
        )
        unauthenticated = gate.authorize(
            session=_session(),
            auth_context=_auth_context(authenticated=False),
            action_kind="tool_call",
            resource={"tool_name": "uppercase"},
        )

        self.assertFalse(missing_auth.allowed)
        self.assertEqual(missing_auth.reason, "missing_auth_context")
        self.assertFalse(resource_mismatch.allowed)
        self.assertEqual(resource_mismatch.reason, "capability_not_granted")
        self.assertFalse(unauthenticated.allowed)
        self.assertEqual(unauthenticated.reason, "unauthenticated")

    def test_policy_gate_can_require_approval_for_matching_grant(self) -> None:
        store = InMemoryCapabilityGrantStore()
        store.save(_grant(constraints={"requires_approval": True}))
        gate = InMemoryPolicyGate(grant_store=store, clock=lambda: NOW)

        decision = gate.authorize(
            session=_session(),
            auth_context=_auth_context(),
            action_kind="tool_call",
            resource={"tool_name": "uppercase"},
        )

        self.assertFalse(decision.allowed)
        self.assertTrue(decision.requires_approval)
        self.assertEqual(decision.reason, "approval_required")
        self.assertEqual(decision.grant_id, "grant-1")
        self.assertEqual(PolicyDecision.from_dict(decision.to_dict()), decision)


class ActivationRunnerPolicyGateTests(unittest.TestCase):
    def test_tool_call_denial_records_event_and_skips_tool_execution(self) -> None:
        fixture = _runner_fixture(model=FakeModel(kind=DecisionKind.TOOL_CALL))

        result = fixture.runner.run_once("sess-1", auth_context=_auth_context())

        self.assertTrue(result.activated)
        self.assertEqual(result.session.status, SessionStatus.IDLE)
        self.assertFalse(result.policy_decision.allowed)
        self.assertIsNone(result.tool_result)
        self.assertEqual(fixture.tool_calls, [])
        self.assertEqual([event.event_type for event in result.events], [
            "signal_received",
            "decision_produced",
            "authorization_denied",
        ])
        self.assertEqual(result.events[-1].payload["reason"], "capability_not_granted")
        self.assertEqual(result.events[-1].payload["action_kind"], "tool_call")
        self.assertEqual(result.checkpoint.state["policy_decision"]["allowed"], False)
        self.assertEqual(fixture.inbox_store.list_for_session("sess-1"), ())

    def test_tool_call_allowed_by_grant_executes_tool(self) -> None:
        fixture = _runner_fixture(
            model=FakeModel(
                kind=DecisionKind.TOOL_CALL,
                tool_name="uppercase",
                tool_arguments={"text": "hello"},
            )
        )
        fixture.grant_store.save(_grant())

        result = fixture.runner.run_once("sess-1", auth_context=_auth_context())

        self.assertTrue(result.policy_decision.allowed)
        self.assertEqual(result.tool_result.output["text"], "HELLO")
        self.assertEqual(fixture.tool_calls, [{"text": "hello"}])
        self.assertEqual([event.event_type for event in result.events], [
            "signal_received",
            "decision_produced",
            "tool_call_requested",
            "tool_result_produced",
        ])
        self.assertEqual(result.checkpoint.state["policy_decision"]["grant_id"], "grant-1")

    def test_tool_call_approval_required_creates_request_and_pauses_action(self) -> None:
        fixture = _runner_fixture(
            model=FakeModel(
                kind=DecisionKind.TOOL_CALL,
                tool_name="uppercase",
                tool_arguments={"text": "hello"},
            )
        )
        fixture.grant_store.save(_grant(constraints={"requires_approval": True}))

        result = fixture.runner.run_once("sess-1", auth_context=_auth_context())

        self.assertFalse(result.policy_decision.allowed)
        self.assertTrue(result.policy_decision.requires_approval)
        self.assertIsNotNone(result.approval_request)
        self.assertEqual(result.approval_request.status, ApprovalStatus.PENDING)
        self.assertEqual(result.session.status, SessionStatus.WAITING)
        self.assertIsNone(result.tool_result)
        self.assertEqual(fixture.tool_calls, [])
        self.assertEqual(
            fixture.approval_store.list_pending_for_session("sess-1"),
            (result.approval_request,),
        )
        self.assertEqual([event.event_type for event in result.events], [
            "signal_received",
            "decision_produced",
            "approval_requested",
        ])
        approval_event = result.events[-1]
        self.assertEqual(approval_event.payload["approval_id"], result.approval_request.approval_id)
        self.assertEqual(approval_event.payload["action_kind"], "tool_call")
        self.assertEqual(approval_event.payload["resource"]["tool_name"], "uppercase")
        self.assertTrue(approval_event.payload["policy"]["requires_approval"])
        self.assertEqual(result.checkpoint.state["policy_decision"]["requires_approval"], True)
        self.assertEqual(
            result.checkpoint.state["approval_request"]["approval_id"],
            result.approval_request.approval_id,
        )
        self.assertEqual(
            result.checkpoint.state["approval_request"]["action_payload"]["decision"][
                "decision_id"
            ],
            result.decision.decision_id,
        )
        self.assertEqual(fixture.inbox_store.list_for_session("sess-1"), ())

    def test_submit_job_denial_skips_job_creation(self) -> None:
        fixture = _runner_fixture(
            model=FakeModel(kind=DecisionKind.SUBMIT_JOB, job_type="export"),
            include_job_store=True,
        )

        result = fixture.runner.run_once("sess-1", auth_context=_auth_context())

        self.assertFalse(result.policy_decision.allowed)
        self.assertIsNone(result.job)
        self.assertEqual(fixture.job_store.list_for_session("sess-1"), ())
        self.assertEqual(result.events[-1].event_type, "authorization_denied")
        self.assertEqual(result.events[-1].payload["resource"]["job_type"], "export")

    def test_submit_job_approval_required_skips_job_creation(self) -> None:
        fixture = _runner_fixture(
            model=FakeModel(kind=DecisionKind.SUBMIT_JOB, job_type="export"),
            include_job_store=True,
        )
        fixture.grant_store.save(
            _grant(
                action_kind="submit_job",
                resource={"job_type": "export"},
                constraints={"requires_approval": True},
            )
        )

        result = fixture.runner.run_once("sess-1", auth_context=_auth_context())

        self.assertTrue(result.policy_decision.requires_approval)
        self.assertIsNotNone(result.approval_request)
        self.assertEqual(result.approval_request.action_kind, "submit_job")
        self.assertIsNone(result.job)
        self.assertEqual(fixture.job_store.list_for_session("sess-1"), ())
        self.assertEqual(result.events[-1].event_type, "approval_requested")
        self.assertEqual(result.events[-1].payload["resource"]["job_type"], "export")


@dataclass
class RunnerFixture:
    runner: ActivationRunner
    inbox_store: InMemoryInboxStore
    grant_store: InMemoryCapabilityGrantStore
    approval_store: InMemoryApprovalRequestStore
    job_store: InMemoryJobStore
    tool_calls: list[dict[str, object]]


class FixedClock:
    def __init__(self, start: datetime) -> None:
        self._current = start

    def __call__(self) -> datetime:
        current = self._current
        self._current = self._current + timedelta(seconds=1)
        return current


def _runner_fixture(
    *,
    model: object,
    include_job_store: bool = False,
) -> RunnerFixture:
    clock = FixedClock(NOW)
    agent = AgentDefinition(
        agent_id="agent-1",
        name="Auth Agent",
        instructions="Return Decisions only.",
    )
    session = _session(created_at=clock(), updated_at=clock())
    session_store = InMemorySessionStore()
    inbox_store = InMemoryInboxStore()
    event_store = InMemoryEventStore()
    checkpoint_store = InMemoryCheckpointStore()
    grant_store = InMemoryCapabilityGrantStore()
    approval_store = InMemoryApprovalRequestStore()
    job_store = InMemoryJobStore()
    tool_calls: list[dict[str, object]] = []

    session_store.create(session)
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

    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="uppercase",
            description="Uppercase text.",
            handler=lambda arguments: _uppercase(arguments, tool_calls),
        )
    )

    runner = ActivationRunner(
        agent=agent,
        model=model,
        session_store=session_store,
        inbox_store=inbox_store,
        event_store=event_store,
        checkpoint_store=checkpoint_store,
        tool_executor=SyncToolExecutor(registry),
        job_store=job_store if include_job_store else None,
        policy_gate=InMemoryPolicyGate(grant_store=grant_store, clock=clock),
        approval_store=approval_store,
        clock=clock,
    )
    return RunnerFixture(
        runner=runner,
        inbox_store=inbox_store,
        grant_store=grant_store,
        approval_store=approval_store,
        job_store=job_store,
        tool_calls=tool_calls,
    )


def _uppercase(
    arguments: dict[str, object],
    tool_calls: list[dict[str, object]],
) -> dict[str, object]:
    tool_calls.append(dict(arguments))
    return {"text": str(arguments["text"]).upper()}


def _auth_context(
    *,
    authenticated: bool = True,
    scopes: tuple[str, ...] = (),
) -> AuthContext:
    return AuthContext(
        actor_id="user-1",
        actor_type="user",
        authenticated=authenticated,
        scopes=scopes,
        claims={"tenant": "test"},
    )


def _grant(
    *,
    grant_id: str = "grant-1",
    action_kind: str = "tool_call",
    resource: dict[str, object] | None = None,
    constraints: dict[str, object] | None = None,
    idempotency_key: str | None = None,
) -> CapabilityGrant:
    default_resource = (
        {"job_type": "export"} if action_kind == "submit_job" else {"tool_name": "uppercase"}
    )
    return CapabilityGrant(
        grant_id=grant_id,
        session_id="sess-1",
        agent_id="agent-1",
        subject="user:user-1",
        action_kind=action_kind,
        resource=resource or default_resource,
        constraints=constraints or {},
        created_at=NOW,
        idempotency_key=idempotency_key,
    )


def _approval_request(
    *,
    approval_id: str = "approval-1",
    decision_id: str = "dec-1",
    signal_id: str = "sig-1",
    action_kind: str = "tool_call",
    resource: dict[str, object] | None = None,
    status: ApprovalStatus = ApprovalStatus.PENDING,
    created_at: datetime = NOW,
    resolved_at: datetime | None = None,
    resolved_by: dict[str, object] | None = None,
    data: dict[str, object] | None = None,
    idempotency_key: str | None = None,
) -> ApprovalRequest:
    return ApprovalRequest(
        approval_id=approval_id,
        session_id="sess-1",
        decision_id=decision_id,
        signal_id=signal_id,
        action_kind=action_kind,
        resource=resource or {"tool_name": "uppercase"},
        action_payload={
            "kind": "tool_call",
            "tool_name": "uppercase",
            "arguments": {"text": "hello"},
        },
        requesting_actor=_actor("user-1"),
        status=status,
        created_at=created_at,
        resolved_at=resolved_at,
        resolved_by=resolved_by,
        reason="requires_user_approval",
        data=data or {},
        idempotency_key=idempotency_key,
    )


def _actor(actor_id: str) -> dict[str, object]:
    return {
        "actor_id": actor_id,
        "actor_type": "user",
        "subject": f"user:{actor_id}",
        "authenticated": True,
    }


def _session(
    *,
    created_at: datetime = NOW,
    updated_at: datetime = NOW,
) -> Session:
    return Session(
        session_id="sess-1",
        agent_id="agent-1",
        status=SessionStatus.IDLE,
        created_at=created_at,
        updated_at=updated_at,
    )


if __name__ == "__main__":
    unittest.main()
