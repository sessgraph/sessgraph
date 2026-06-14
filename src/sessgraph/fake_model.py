"""Deterministic FakeModel adapter for P0 tests and examples."""

from __future__ import annotations

from dataclasses import dataclass

from sessgraph.core import Decision, DecisionKind
from sessgraph.runtime import ActivationContext


@dataclass(frozen=True, slots=True)
class FakeModel:
    """Model adapter that deterministically returns one P0 Decision."""

    kind: DecisionKind = DecisionKind.FINAL_ANSWER
    final_answer: str | None = None

    def decide(self, context: ActivationContext) -> Decision:
        if self.kind is DecisionKind.NOOP:
            return Decision(
                decision_id=_decision_id(context),
                session_id=context.session.session_id,
                kind=DecisionKind.NOOP,
                payload={},
                created_at=context.now,
            )

        content = self.final_answer
        if content is None:
            signal_content = context.signal.payload.get("content")
            content = signal_content if isinstance(signal_content, str) and signal_content else "OK"

        return Decision(
            decision_id=_decision_id(context),
            session_id=context.session.session_id,
            kind=DecisionKind.FINAL_ANSWER,
            payload={"content": content},
            created_at=context.now,
        )


def _decision_id(context: ActivationContext) -> str:
    return f"{context.session.session_id}:decision:{context.signal.signal_id}"
