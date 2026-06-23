"""In-memory authorization primitives for runtime-side policy gates."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any

from sessgraph.core import (
    JsonObject,
    Session,
    ValidationError,
    _copy_json_object,
    _datetime_from_json,
    _datetime_to_json,
    _freeze_json_object,
    _require_datetime,
    _require_field,
    _require_non_empty,
    _require_schema_version,
)
from sessgraph.stores import IdempotencyConflictError

POLICY_ID = "inmemory-capability-v1"


@dataclass(frozen=True, slots=True)
class AuthContext:
    """Provider-independent actor context supplied by the host runtime."""

    actor_id: str
    actor_type: str
    authenticated: bool
    scopes: tuple[str, ...] = ()
    claims: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty("actor_id", self.actor_id)
        _require_non_empty("actor_type", self.actor_type)
        if not isinstance(self.authenticated, bool):
            raise ValidationError("authenticated must be a boolean")
        object.__setattr__(self, "scopes", _coerce_string_tuple("scopes", self.scopes))
        object.__setattr__(self, "claims", _freeze_json_object("claims", self.claims))

    @property
    def subject(self) -> str:
        return f"{self.actor_type}:{self.actor_id}"

    def to_dict(self) -> JsonObject:
        return {
            "schema_version": 1,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "authenticated": self.authenticated,
            "scopes": list(self.scopes),
            "claims": _copy_json_object("claims", self.claims),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AuthContext":
        _require_schema_version(data)
        return cls(
            actor_id=_require_field(data, "actor_id"),
            actor_type=_require_field(data, "actor_type"),
            authenticated=_require_field(data, "authenticated"),
            scopes=_coerce_string_tuple("scopes", data.get("scopes", ())),
            claims=_copy_json_object("claims", data.get("claims", {})),
        )


@dataclass(frozen=True, slots=True)
class CapabilityGrant:
    """Session-scoped grant allowing one subject to dispatch one action kind."""

    grant_id: str
    session_id: str
    subject: str
    action_kind: str
    resource: JsonObject
    created_at: datetime
    agent_id: str | None = None
    constraints: JsonObject = field(default_factory=dict)
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    idempotency_key: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty("grant_id", self.grant_id)
        _require_non_empty("session_id", self.session_id)
        _require_non_empty("subject", self.subject)
        _require_non_empty("action_kind", self.action_kind)
        _require_datetime("created_at", self.created_at)
        if self.agent_id is not None:
            _require_non_empty("agent_id", self.agent_id)
        if self.expires_at is not None:
            _require_datetime("expires_at", self.expires_at)
            if self.expires_at <= self.created_at:
                raise ValidationError("expires_at must be after created_at")
        if self.revoked_at is not None:
            _require_datetime("revoked_at", self.revoked_at)
        if self.idempotency_key is not None:
            _require_non_empty("idempotency_key", self.idempotency_key)
        object.__setattr__(self, "resource", _freeze_json_object("resource", self.resource))
        object.__setattr__(
            self,
            "constraints",
            _freeze_json_object("constraints", self.constraints),
        )

    def is_active(self, now: datetime) -> bool:
        _require_datetime("now", now)
        current = now.astimezone(timezone.utc)
        if self.revoked_at is not None:
            return False
        return self.expires_at is None or self.expires_at > current

    def to_dict(self) -> JsonObject:
        return {
            "schema_version": 1,
            "grant_id": self.grant_id,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "subject": self.subject,
            "action_kind": self.action_kind,
            "resource": _copy_json_object("resource", self.resource),
            "constraints": _copy_json_object("constraints", self.constraints),
            "created_at": _datetime_to_json(self.created_at),
            "expires_at": (
                _datetime_to_json(self.expires_at) if self.expires_at is not None else None
            ),
            "revoked_at": (
                _datetime_to_json(self.revoked_at) if self.revoked_at is not None else None
            ),
            "idempotency_key": self.idempotency_key,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CapabilityGrant":
        _require_schema_version(data)
        expires_at = data.get("expires_at")
        revoked_at = data.get("revoked_at")
        return cls(
            grant_id=_require_field(data, "grant_id"),
            session_id=_require_field(data, "session_id"),
            agent_id=data.get("agent_id"),
            subject=_require_field(data, "subject"),
            action_kind=_require_field(data, "action_kind"),
            resource=_copy_json_object("resource", _require_field(data, "resource")),
            constraints=_copy_json_object("constraints", data.get("constraints", {})),
            created_at=_datetime_from_json(_require_field(data, "created_at"), "created_at"),
            expires_at=(
                _datetime_from_json(expires_at, "expires_at") if expires_at is not None else None
            ),
            revoked_at=(
                _datetime_from_json(revoked_at, "revoked_at") if revoked_at is not None else None
            ),
            idempotency_key=data.get("idempotency_key"),
        )


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    """Deterministic authorization decision emitted by a policy gate."""

    allowed: bool
    action_kind: str
    resource: JsonObject
    reason: str
    actor: JsonObject
    decided_at: datetime
    grant_id: str | None = None
    policy_id: str = POLICY_ID

    def __post_init__(self) -> None:
        if not isinstance(self.allowed, bool):
            raise ValidationError("allowed must be a boolean")
        _require_non_empty("action_kind", self.action_kind)
        _require_non_empty("reason", self.reason)
        _require_datetime("decided_at", self.decided_at)
        if self.grant_id is not None:
            _require_non_empty("grant_id", self.grant_id)
        _require_non_empty("policy_id", self.policy_id)
        object.__setattr__(self, "resource", _freeze_json_object("resource", self.resource))
        object.__setattr__(self, "actor", _freeze_json_object("actor", self.actor))

    def to_dict(self) -> JsonObject:
        return {
            "schema_version": 1,
            "allowed": self.allowed,
            "action_kind": self.action_kind,
            "resource": _copy_json_object("resource", self.resource),
            "reason": self.reason,
            "actor": _copy_json_object("actor", self.actor),
            "grant_id": self.grant_id,
            "policy_id": self.policy_id,
            "decided_at": _datetime_to_json(self.decided_at),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PolicyDecision":
        _require_schema_version(data)
        return cls(
            allowed=_require_field(data, "allowed"),
            action_kind=_require_field(data, "action_kind"),
            resource=_copy_json_object("resource", _require_field(data, "resource")),
            reason=_require_field(data, "reason"),
            actor=_copy_json_object("actor", _require_field(data, "actor")),
            grant_id=data.get("grant_id"),
            policy_id=_require_field(data, "policy_id"),
            decided_at=_datetime_from_json(_require_field(data, "decided_at"), "decided_at"),
        )


@dataclass
class InMemoryCapabilityGrantStore:
    """Store CapabilityGrants by id and session."""

    _grants_by_id: dict[str, CapabilityGrant] = field(default_factory=dict)
    _grant_ids_by_session: dict[str, list[str]] = field(default_factory=dict)
    _grant_ids_by_idempotency: dict[tuple[str, str], str] = field(default_factory=dict)

    def save(self, grant: CapabilityGrant) -> CapabilityGrant:
        existing = self._grants_by_id.get(grant.grant_id)
        if existing is not None:
            _raise_if_different(existing, grant, f"grant id conflict: {grant.grant_id}")
            return _snapshot_grant(existing)

        if grant.idempotency_key is not None:
            idempotency_ref = (grant.session_id, grant.idempotency_key)
            existing_grant_id = self._grant_ids_by_idempotency.get(idempotency_ref)
            if existing_grant_id is not None:
                existing_grant = self._grants_by_id[existing_grant_id]
                _raise_if_different(
                    existing_grant,
                    grant,
                    f"idempotency key conflict: {grant.idempotency_key}",
                )
                return _snapshot_grant(existing_grant)
            self._grant_ids_by_idempotency[idempotency_ref] = grant.grant_id

        self._grants_by_id[grant.grant_id] = _snapshot_grant(grant)
        self._grant_ids_by_session.setdefault(grant.session_id, []).append(grant.grant_id)
        return _snapshot_grant(grant)

    def get(self, grant_id: str) -> CapabilityGrant | None:
        grant = self._grants_by_id.get(grant_id)
        if grant is None:
            return None
        return _snapshot_grant(grant)

    def list_for_session(self, session_id: str) -> tuple[CapabilityGrant, ...]:
        grant_ids = self._grant_ids_by_session.get(session_id, [])
        return tuple(_snapshot_grant(self._grants_by_id[grant_id]) for grant_id in grant_ids)

    def list_active_for_session(
        self,
        session_id: str,
        *,
        now: datetime,
    ) -> tuple[CapabilityGrant, ...]:
        return tuple(grant for grant in self.list_for_session(session_id) if grant.is_active(now))


@dataclass(slots=True)
class InMemoryPolicyGate:
    """Authorize runtime actions against InMemory CapabilityGrants."""

    grant_store: InMemoryCapabilityGrantStore
    clock: Callable[[], datetime] = field(default_factory=lambda: _utcnow)
    policy_id: str = POLICY_ID

    def authorize(
        self,
        *,
        session: Session,
        auth_context: AuthContext | None,
        action_kind: str,
        resource: JsonObject,
    ) -> PolicyDecision:
        _require_non_empty("action_kind", action_kind)
        checked_resource = _copy_json_object("resource", resource)
        now = self._now()

        if auth_context is None:
            return self._deny(
                action_kind=action_kind,
                resource=checked_resource,
                reason="missing_auth_context",
                actor=_anonymous_actor(),
                decided_at=now,
            )
        if not auth_context.authenticated:
            return self._deny(
                action_kind=action_kind,
                resource=checked_resource,
                reason="unauthenticated",
                actor=_actor_metadata(auth_context),
                decided_at=now,
            )

        grants = sorted(
            self.grant_store.list_active_for_session(session.session_id, now=now),
            key=lambda grant: (grant.created_at, grant.grant_id),
        )
        for grant in grants:
            if _grant_matches(
                grant=grant,
                session=session,
                auth_context=auth_context,
                action_kind=action_kind,
                resource=checked_resource,
            ):
                return PolicyDecision(
                    allowed=True,
                    action_kind=action_kind,
                    resource=checked_resource,
                    reason="capability_granted",
                    actor=_actor_metadata(auth_context),
                    grant_id=grant.grant_id,
                    policy_id=self.policy_id,
                    decided_at=now,
                )

        return self._deny(
            action_kind=action_kind,
            resource=checked_resource,
            reason="capability_not_granted",
            actor=_actor_metadata(auth_context),
            decided_at=now,
        )

    def _deny(
        self,
        *,
        action_kind: str,
        resource: JsonObject,
        reason: str,
        actor: JsonObject,
        decided_at: datetime,
    ) -> PolicyDecision:
        return PolicyDecision(
            allowed=False,
            action_kind=action_kind,
            resource=resource,
            reason=reason,
            actor=actor,
            policy_id=self.policy_id,
            decided_at=decided_at,
        )

    def _now(self) -> datetime:
        current = self.clock()
        _require_datetime("clock", current)
        return current.astimezone(timezone.utc)


def capability_grant_id(
    *,
    session_id: str,
    subject: str,
    action_kind: str,
    resource: JsonObject,
) -> str:
    _require_non_empty("session_id", session_id)
    _require_non_empty("subject", subject)
    _require_non_empty("action_kind", action_kind)
    payload = {
        "action_kind": action_kind,
        "resource": _copy_json_object("resource", resource),
        "session_id": session_id,
        "subject": subject,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"{session_id}:grant:{sha256(encoded).hexdigest()[:16]}"


def _grant_matches(
    *,
    grant: CapabilityGrant,
    session: Session,
    auth_context: AuthContext,
    action_kind: str,
    resource: JsonObject,
) -> bool:
    if grant.agent_id is not None and grant.agent_id != session.agent_id:
        return False
    if grant.subject != auth_context.subject:
        return False
    if grant.action_kind != action_kind:
        return False
    if not _resource_matches(grant.resource, resource):
        return False
    return _constraints_match(grant.constraints, auth_context)


def _resource_matches(grant_resource: JsonObject, action_resource: JsonObject) -> bool:
    for key, value in grant_resource.items():
        if key not in action_resource or action_resource[key] != value:
            return False
    return True


def _constraints_match(constraints: JsonObject, auth_context: AuthContext) -> bool:
    required_scopes = constraints.get("required_scopes")
    if required_scopes is None:
        return True
    required = set(_coerce_string_tuple("constraints.required_scopes", required_scopes))
    return required.issubset(set(auth_context.scopes))


def _actor_metadata(auth_context: AuthContext) -> JsonObject:
    return {
        "actor_id": auth_context.actor_id,
        "actor_type": auth_context.actor_type,
        "subject": auth_context.subject,
        "authenticated": auth_context.authenticated,
    }


def _anonymous_actor() -> JsonObject:
    return {
        "actor_id": None,
        "actor_type": None,
        "subject": None,
        "authenticated": False,
    }


def _coerce_string_tuple(field_name: str, value: Any) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValidationError(f"{field_name} must be a sequence of strings")
    result = tuple(value)
    seen: set[str] = set()
    for item in result:
        _require_non_empty(f"{field_name}[]", item)
        if item in seen:
            raise ValidationError(f"{field_name} must not contain duplicate strings")
        seen.add(item)
    return result


def _raise_if_different(
    existing: CapabilityGrant,
    incoming: CapabilityGrant,
    message: str,
) -> None:
    if existing.to_dict() != incoming.to_dict():
        raise IdempotencyConflictError(message)


def _snapshot_grant(grant: CapabilityGrant) -> CapabilityGrant:
    return CapabilityGrant.from_dict(grant.to_dict())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)
