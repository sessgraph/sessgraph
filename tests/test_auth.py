from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import unittest

from sessgraph import (
    ActivationRunner,
    AgentDefinition,
    AuthContext,
    CapabilityGrant,
    DecisionKind,
    FakeModel,
    IdempotencyConflictError,
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


@dataclass
class RunnerFixture:
    runner: ActivationRunner
    inbox_store: InMemoryInboxStore
    grant_store: InMemoryCapabilityGrantStore
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
        clock=clock,
    )
    return RunnerFixture(
        runner=runner,
        inbox_store=inbox_store,
        grant_store=grant_store,
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
    resource: dict[str, object] | None = None,
    constraints: dict[str, object] | None = None,
    idempotency_key: str | None = None,
) -> CapabilityGrant:
    return CapabilityGrant(
        grant_id=grant_id,
        session_id="sess-1",
        agent_id="agent-1",
        subject="user:user-1",
        action_kind="tool_call",
        resource=resource or {"tool_name": "uppercase"},
        constraints=constraints or {},
        created_at=NOW,
        idempotency_key=idempotency_key,
    )


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
