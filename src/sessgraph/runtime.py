"""Minimal Activation Runner for the P0 durable Session runtime."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Protocol

from sessgraph.auth import (
    ApprovalRequest,
    AuthContext,
    InMemoryApprovalRequestStore,
    InMemoryPolicyGate,
    PolicyDecision,
    approval_request_id,
)
from sessgraph.context import ContextBuilder, ContextSnapshot
from sessgraph.core import (
    AgentDefinition,
    Checkpoint,
    Decision,
    DecisionKind,
    Event,
    JsonObject,
    Session,
    SessionStatus,
    Signal,
)
from sessgraph.jobs import InMemoryJobStore, JobRecord, job_id_for_decision
from sessgraph.stores import (
    InMemoryCheckpointStore,
    InMemoryEventStore,
    InMemoryInboxStore,
    InMemorySessionStore,
    RecordNotFoundError,
)
from sessgraph.tools import SyncToolExecutor, ToolResult


class DecisionRejectedError(ValueError):
    """Raised when a model Decision does not match runtime invariants."""


@dataclass(frozen=True, slots=True)
class ActivationContext:
    """Read-only context passed to a model adapter."""

    agent: AgentDefinition
    session: Session
    signal: Signal
    events: tuple[Event, ...]
    now: datetime
    context_snapshot: ContextSnapshot | None = None
    auth_context: AuthContext | None = None


class ModelAdapter(Protocol):
    """Protocol for provider-independent model adapters."""

    def decide(self, context: ActivationContext) -> Decision:
        """Return one Decision for the activation."""


@dataclass(frozen=True, slots=True)
class ActivationResult:
    """Result of a single runner activation attempt."""

    session_id: str
    activated: bool
    session: Session | None = None
    signal: Signal | None = None
    decision: Decision | None = None
    events: tuple[Event, ...] = ()
    checkpoint: Checkpoint | None = None
    tool_result: ToolResult | None = None
    job: JobRecord | None = None
    context_snapshot: ContextSnapshot | None = None
    policy_decision: PolicyDecision | None = None
    approval_request: ApprovalRequest | None = None


@dataclass(slots=True)
class ActivationRunner:
    """Wake one Session from one pending Signal and dispatch one Decision."""

    agent: AgentDefinition
    model: ModelAdapter
    session_store: InMemorySessionStore
    inbox_store: InMemoryInboxStore
    event_store: InMemoryEventStore
    checkpoint_store: InMemoryCheckpointStore
    tool_executor: SyncToolExecutor | None = None
    job_store: InMemoryJobStore | None = None
    context_builder: ContextBuilder | None = None
    policy_gate: InMemoryPolicyGate | None = None
    approval_store: InMemoryApprovalRequestStore | None = None
    clock: Callable[[], datetime] = field(default_factory=lambda: _utcnow)

    def run_once(
        self,
        session_id: str,
        *,
        auth_context: AuthContext | None = None,
    ) -> ActivationResult:
        session = self.session_store.get(session_id)
        if session is None:
            raise RecordNotFoundError(f"session does not exist: {session_id}")

        pending_signals = self.inbox_store.list_for_session(session_id)
        if not pending_signals:
            return ActivationResult(session_id=session_id, activated=False, session=session)
        signal = pending_signals[0]

        running = replace(
            session,
            status=SessionStatus.RUNNING,
            updated_at=self._now(),
            revision=session.revision + 1,
        )
        context_snapshot = self._build_context(running, signal)
        context = ActivationContext(
            agent=self.agent,
            session=running,
            signal=signal,
            events=(
                context_snapshot.event_window
                if context_snapshot is not None
                else self.event_store.list_for_session(session_id)
            ),
            now=self._now(),
            context_snapshot=context_snapshot,
            auth_context=auth_context,
        )
        decision = self.model.decide(context)
        self._validate_decision(decision, session_id)
        policy_decision = self._authorize_decision(
            session=running,
            decision=decision,
            auth_context=auth_context,
        )
        approval_required = (
            policy_decision is not None and policy_decision.requires_approval
        )
        denied = (
            policy_decision is not None
            and not policy_decision.allowed
            and not policy_decision.requires_approval
        )
        dispatch_allowed = policy_decision is None or policy_decision.allowed
        approval_request = (
            self._new_approval_request(
                session=running,
                signal=signal,
                decision=decision,
                policy_decision=policy_decision,
            )
            if approval_required and policy_decision is not None
            else None
        )
        tool_result = self._execute_tool_call(decision) if dispatch_allowed else None
        job = self._submit_job(decision) if dispatch_allowed else None

        running = self.session_store.update(running, expected_revision=session.revision)
        if approval_request is not None:
            approval_request = self._save_approval_request(approval_request)
        signal_event = self._append_event(
            session_id=session_id,
            event_type="signal_received",
            payload={
                "signal_id": signal.signal_id,
                "signal_type": signal.signal_type,
                "idempotency_key": signal.idempotency_key,
                "payload": signal.to_dict()["payload"],
            },
            source_signal_id=signal.signal_id,
        )
        decision_event = self._append_event(
            session_id=session_id,
            event_type="decision_produced",
            payload={"decision": decision.to_dict()},
            source_signal_id=signal.signal_id,
        )
        events = [signal_event, decision_event]

        if denied and policy_decision is not None:
            authorization_event = self._append_event(
                session_id=session_id,
                event_type="authorization_denied",
                payload=_policy_denial_payload(decision, policy_decision),
                source_signal_id=signal.signal_id,
            )
            events.append(authorization_event)

        if approval_request is not None and policy_decision is not None:
            approval_event = self._append_event(
                session_id=session_id,
                event_type="approval_requested",
                payload=_approval_requested_payload(approval_request, policy_decision),
                source_signal_id=signal.signal_id,
            )
            events.append(approval_event)

        if tool_result is not None:
            tool_call_event = self._append_event(
                session_id=session_id,
                event_type="tool_call_requested",
                payload={
                    "decision_id": decision.decision_id,
                    "tool_name": tool_result.tool_name,
                    "arguments": decision.payload["arguments"],
                },
                source_signal_id=signal.signal_id,
            )
            tool_result_event = self._append_event(
                session_id=session_id,
                event_type="tool_result_produced",
                payload={"decision_id": decision.decision_id, "result": tool_result.to_dict()},
                source_signal_id=signal.signal_id,
            )
            events.extend([tool_call_event, tool_result_event])

        if job is not None:
            job_event = self._append_event(
                session_id=session_id,
                event_type="job_submitted",
                payload={
                    "decision_id": decision.decision_id,
                    "job_id": job.job_id,
                    "job": job.to_dict(),
                },
                source_signal_id=signal.signal_id,
            )
            events.append(job_event)

        if denied:
            final_status = SessionStatus.IDLE
        elif approval_request is not None:
            final_status = SessionStatus.WAITING
        else:
            final_status = _status_for_decision(decision)
        checkpoint_id = _checkpoint_id(session_id, running.revision + 1, events[-1].sequence)
        final_session = replace(
            running,
            status=final_status,
            updated_at=self._now(),
            revision=running.revision + 1,
            checkpoint_id=checkpoint_id,
        )
        final_session = self.session_store.update(final_session, expected_revision=running.revision)
        checkpoint = self._save_checkpoint(
            checkpoint_id=checkpoint_id,
            session=final_session,
            signal=signal,
            decision=decision,
            events=tuple(events),
            tool_result=tool_result,
            job=job,
            context_snapshot=context_snapshot,
            policy_decision=policy_decision,
            approval_request=approval_request,
        )
        if tool_result is not None:
            self.inbox_store.enqueue(
                Signal(
                    signal_id=_tool_result_signal_id(session_id, decision.decision_id),
                    session_id=session_id,
                    signal_type="tool_result",
                    payload={
                        "decision_id": decision.decision_id,
                        "result": tool_result.to_dict(),
                    },
                    created_at=self._now(),
                    idempotency_key=f"tool_result:{decision.decision_id}",
                )
            )
        popped = self.inbox_store.pop_next(session_id)
        if popped is None or popped.signal_id != signal.signal_id:
            raise DecisionRejectedError("pending signal changed during activation")

        return ActivationResult(
            session_id=session_id,
            activated=True,
            session=final_session,
            signal=signal,
            decision=decision,
            events=tuple(events),
            checkpoint=checkpoint,
            tool_result=tool_result,
            job=job,
            context_snapshot=context_snapshot,
            policy_decision=policy_decision,
            approval_request=approval_request,
        )

    def _append_event(
        self,
        *,
        session_id: str,
        event_type: str,
        payload: JsonObject,
        source_signal_id: str,
    ) -> Event:
        sequence = self.event_store.next_sequence(session_id)
        event = Event(
            event_id=_event_id(session_id, sequence, event_type),
            session_id=session_id,
            event_type=event_type,
            sequence=sequence,
            payload=payload,
            occurred_at=self._now(),
            source_signal_id=source_signal_id,
        )
        return self.event_store.append(event, expected_next_sequence=sequence)

    def _save_checkpoint(
        self,
        *,
        checkpoint_id: str,
        session: Session,
        signal: Signal,
        decision: Decision,
        events: tuple[Event, ...],
        tool_result: ToolResult | None,
        job: JobRecord | None,
        context_snapshot: ContextSnapshot | None,
        policy_decision: PolicyDecision | None,
        approval_request: ApprovalRequest | None,
    ) -> Checkpoint:
        state: JsonObject = {
            "session": session.to_dict(),
            "signal": signal.to_dict(),
            "decision": decision.to_dict(),
            "event_ids": [event.event_id for event in events],
        }
        if context_snapshot is not None:
            state["context_snapshot"] = _context_snapshot_metadata(context_snapshot)
        if policy_decision is not None:
            state["policy_decision"] = policy_decision.to_dict()
        if approval_request is not None:
            state["approval_request"] = approval_request.to_dict()
        if tool_result is not None:
            state["tool_result"] = tool_result.to_dict()
        if job is not None:
            state["job"] = job.to_dict()

        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            session_id=session.session_id,
            session_revision=session.revision,
            event_sequence=events[-1].sequence,
            state=state,
            created_at=self._now(),
        )
        return self.checkpoint_store.save(checkpoint)

    def _build_context(self, session: Session, signal: Signal) -> ContextSnapshot | None:
        if self.context_builder is None:
            return None
        return self.context_builder.build(session, signal)

    def _authorize_decision(
        self,
        *,
        session: Session,
        decision: Decision,
        auth_context: AuthContext | None,
    ) -> PolicyDecision | None:
        if self.policy_gate is None:
            return None
        action = _policy_action_for_decision(decision)
        if action is None:
            return None
        action_kind, resource = action
        return self.policy_gate.authorize(
            session=session,
            auth_context=auth_context,
            action_kind=action_kind,
            resource=resource,
        )

    def _new_approval_request(
        self,
        *,
        session: Session,
        signal: Signal,
        decision: Decision,
        policy_decision: PolicyDecision,
    ) -> ApprovalRequest:
        if self.approval_store is None:
            raise DecisionRejectedError(
                "approval_store is required for approval-required decisions"
            )
        idempotency_key = f"approval:{signal.signal_id}:{decision.decision_id}"
        approval = ApprovalRequest(
            approval_id=approval_request_id(
                session_id=session.session_id,
                decision_id=decision.decision_id,
                action_kind=policy_decision.action_kind,
                resource=policy_decision.resource,
                idempotency_key=idempotency_key,
            ),
            session_id=session.session_id,
            decision_id=decision.decision_id,
            signal_id=signal.signal_id,
            action_kind=policy_decision.action_kind,
            resource=policy_decision.resource,
            action_payload={
                "decision": decision.to_dict(),
                "source_signal": {
                    "signal_id": signal.signal_id,
                    "signal_type": signal.signal_type,
                },
            },
            requesting_actor=policy_decision.actor,
            created_at=self._now(),
            reason=policy_decision.reason,
            idempotency_key=idempotency_key,
        )
        return approval

    def _save_approval_request(self, approval_request: ApprovalRequest) -> ApprovalRequest:
        if self.approval_store is None:
            raise DecisionRejectedError(
                "approval_store is required for approval-required decisions"
            )
        return self.approval_store.create(approval_request)

    def _validate_decision(self, decision: Decision, session_id: str) -> None:
        if decision.session_id != session_id:
            raise DecisionRejectedError(
                f"decision session_id {decision.session_id} does not match {session_id}"
            )
        supported_kinds = {
            DecisionKind.FINAL_ANSWER,
            DecisionKind.NOOP,
            DecisionKind.TOOL_CALL,
            DecisionKind.ASK_USER,
            DecisionKind.SUBMIT_JOB,
        }
        if decision.kind not in supported_kinds:
            raise DecisionRejectedError(f"unsupported decision kind: {decision.kind.value}")

    def _execute_tool_call(self, decision: Decision) -> ToolResult | None:
        if decision.kind is not DecisionKind.TOOL_CALL:
            return None
        if self.tool_executor is None:
            raise DecisionRejectedError("tool_executor is required for tool_call decisions")
        return self.tool_executor.execute(
            tool_name=str(decision.payload["tool_name"]),
            arguments=decision.payload["arguments"],
        )

    def _submit_job(self, decision: Decision) -> JobRecord | None:
        if decision.kind is not DecisionKind.SUBMIT_JOB:
            return None
        if self.job_store is None:
            raise DecisionRejectedError("job_store is required for submit_job decisions")
        return self.job_store.submit(
            JobRecord(
                job_id=job_id_for_decision(decision.session_id, decision.decision_id),
                session_id=decision.session_id,
                decision_id=decision.decision_id,
                job_type=str(decision.payload["job_type"]),
                arguments=decision.payload["arguments"],
                created_at=decision.created_at,
                idempotency_key=_optional_payload_string(decision, "idempotency_key"),
            )
        )

    def _now(self) -> datetime:
        current = self.clock()
        if current.tzinfo is None or current.utcoffset() is None:
            raise ValueError("runner clock must return timezone-aware datetimes")
        return current.astimezone(timezone.utc)


def _status_for_decision(decision: Decision) -> SessionStatus:
    if decision.kind is DecisionKind.FINAL_ANSWER:
        return SessionStatus.COMPLETED
    if decision.kind is DecisionKind.NOOP:
        return SessionStatus.IDLE
    if decision.kind is DecisionKind.TOOL_CALL:
        return SessionStatus.IDLE
    if decision.kind is DecisionKind.ASK_USER:
        return SessionStatus.WAITING
    if decision.kind is DecisionKind.SUBMIT_JOB:
        return SessionStatus.IDLE
    raise DecisionRejectedError(f"unsupported decision kind: {decision.kind.value}")


def _event_id(session_id: str, sequence: int, event_type: str) -> str:
    return f"{session_id}:event:{sequence}:{event_type}"


def _checkpoint_id(session_id: str, session_revision: int, event_sequence: int) -> str:
    return f"{session_id}:checkpoint:{session_revision}:{event_sequence}"


def _tool_result_signal_id(session_id: str, decision_id: str) -> str:
    return f"{session_id}:signal:tool_result:{decision_id}"


def _optional_payload_string(decision: Decision, field_name: str) -> str | None:
    value = decision.payload.get(field_name)
    if value is None:
        return None
    return str(value)


def _policy_action_for_decision(decision: Decision) -> tuple[str, JsonObject] | None:
    if decision.kind is DecisionKind.TOOL_CALL:
        return decision.kind.value, {"tool_name": str(decision.payload["tool_name"])}
    if decision.kind is DecisionKind.SUBMIT_JOB:
        return decision.kind.value, {"job_type": str(decision.payload["job_type"])}
    return None


def _policy_denial_payload(
    decision: Decision,
    policy_decision: PolicyDecision,
) -> JsonObject:
    decision_data = policy_decision.to_dict()
    return {
        "decision_id": decision.decision_id,
        "action_kind": policy_decision.action_kind,
        "resource": decision_data["resource"],
        "actor": decision_data["actor"],
        "policy": {
            "policy_id": policy_decision.policy_id,
            "grant_id": policy_decision.grant_id,
            "allowed": policy_decision.allowed,
        },
        "reason": policy_decision.reason,
    }


def _approval_requested_payload(
    approval_request: ApprovalRequest,
    policy_decision: PolicyDecision,
) -> JsonObject:
    policy_data = policy_decision.to_dict()
    return {
        "approval_id": approval_request.approval_id,
        "decision_id": approval_request.decision_id,
        "signal_id": approval_request.signal_id,
        "action_kind": approval_request.action_kind,
        "resource": approval_request.to_dict()["resource"],
        "requesting_actor": approval_request.to_dict()["requesting_actor"],
        "policy": {
            "policy_id": policy_decision.policy_id,
            "grant_id": policy_decision.grant_id,
            "allowed": policy_decision.allowed,
            "requires_approval": policy_decision.requires_approval,
        },
        "reason": policy_data["reason"],
    }


def _context_snapshot_metadata(snapshot: ContextSnapshot) -> JsonObject:
    return {
        "session_id": snapshot.session_id,
        "signal_id": snapshot.signal_id,
        "event_ids": list(snapshot.event_ids),
        "memory_ids": list(snapshot.memory_ids),
        "latest_checkpoint_id": snapshot.latest_checkpoint_id,
        "built_at": snapshot.to_dict()["built_at"],
        "ordering": snapshot.to_dict()["ordering"],
        "limits": snapshot.to_dict()["limits"],
    }


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)
