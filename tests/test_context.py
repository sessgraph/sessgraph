from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import unittest

from sessgraph import (
    ActivationContext,
    ActivationRunner,
    AgentDefinition,
    Checkpoint,
    ContextBuilder,
    ContextSnapshot,
    Decision,
    DecisionKind,
    Event,
    IdempotencyConflictError,
    InMemoryCheckpointStore,
    InMemoryEventStore,
    InMemoryInboxStore,
    InMemoryMemoryStore,
    InMemorySessionStore,
    MemoryRecord,
    Session,
    SessionStatus,
    Signal,
    memory_id_for_record,
)


NOW = datetime(2026, 6, 23, 9, 0, tzinfo=timezone.utc)


class ContextModelTests(unittest.TestCase):
    def test_memory_record_round_trips_and_freezes_content(self) -> None:
        record = _memory(
            "mem-1",
            content={"summary": {"text": "hello"}},
            source_event_ids=("evt-1",),
            supersedes_memory_ids=("mem-0",),
        )

        restored = MemoryRecord.from_dict(record.to_dict())

        self.assertEqual(restored, record)
        self.assertEqual(restored.to_dict()["schema_version"], 1)
        with self.assertRaises(TypeError):
            restored.content["extra"] = "blocked"
        with self.assertRaises(TypeError):
            restored.content["summary"]["text"] = "changed"

    def test_memory_id_for_record_is_deterministic(self) -> None:
        first = memory_id_for_record(
            session_id="sess-1",
            memory_type="summary",
            source_event_ids=("evt-1", "evt-2"),
            idempotency_key="compact:1",
        )
        second = memory_id_for_record(
            session_id="sess-1",
            memory_type="summary",
            source_event_ids=("evt-1", "evt-2"),
            idempotency_key="compact:1",
        )

        self.assertEqual(first, second)
        self.assertTrue(first.startswith("sess-1:memory:"))

    def test_memory_store_is_idempotent_and_rejects_conflicts(self) -> None:
        store = InMemoryMemoryStore()
        memory = _memory("mem-1", idempotency_key="request-1")

        self.assertEqual(store.save(memory), memory)
        self.assertEqual(store.save(memory), memory)
        self.assertEqual(store.get("mem-1"), memory)
        self.assertEqual(store.list_for_session("sess-1"), (memory,))

        with self.assertRaises(TypeError):
            store.get("mem-1").content["new"] = "blocked"

        with self.assertRaises(IdempotencyConflictError):
            store.save(_memory("mem-1", content={"summary": "changed"}))

        with self.assertRaises(IdempotencyConflictError):
            store.save(_memory("mem-2", idempotency_key="request-1"))

    def test_context_snapshot_round_trips(self) -> None:
        snapshot = ContextSnapshot(
            session_id="sess-1",
            signal_id="sig-1",
            event_window=(_event("evt-1", sequence=0),),
            memory_records=(_memory("mem-1", source_event_ids=("evt-1",)),),
            latest_checkpoint_id="chk-1",
            built_at=NOW,
            limits={"max_events": 1, "event_count": 1},
        )

        restored = ContextSnapshot.from_dict(snapshot.to_dict())

        self.assertEqual(restored, snapshot)
        self.assertEqual(restored.event_ids, ("evt-1",))
        self.assertEqual(restored.memory_ids, ("mem-1",))
        self.assertEqual(restored.ordering["events"], "sequence_asc")


class ContextBuilderTests(unittest.TestCase):
    def test_builder_orders_memory_windows_events_and_tracks_checkpoint(self) -> None:
        clock = FixedClock(NOW + timedelta(minutes=10))
        event_store = InMemoryEventStore()
        memory_store = InMemoryMemoryStore()
        checkpoint_store = InMemoryCheckpointStore()
        builder = ContextBuilder(
            event_store=event_store,
            memory_store=memory_store,
            checkpoint_store=checkpoint_store,
            clock=clock,
            max_events=2,
        )

        event_store.append(_event("evt-0", sequence=0), expected_next_sequence=0)
        event_store.append(_event("evt-1", sequence=1), expected_next_sequence=1)
        event_store.append(_event("evt-2", sequence=2), expected_next_sequence=2)
        memory_store.save(_memory("mem-b", created_at=NOW + timedelta(seconds=1)))
        memory_store.save(_memory("mem-a", created_at=NOW + timedelta(seconds=1)))
        memory_store.save(_memory("mem-c", created_at=NOW + timedelta(seconds=2)))
        checkpoint_store.save(_checkpoint("chk-1", revision=1, event_sequence=0))
        checkpoint_store.save(_checkpoint("chk-2", revision=2, event_sequence=2))

        snapshot = builder.build(_session(), _signal())

        self.assertEqual([event.sequence for event in snapshot.event_window], [1, 2])
        self.assertEqual(snapshot.memory_ids, ("mem-a", "mem-b", "mem-c"))
        self.assertEqual(snapshot.latest_checkpoint_id, "chk-2")
        self.assertEqual(snapshot.built_at, NOW + timedelta(minutes=10))
        self.assertEqual(snapshot.limits["max_events"], 2)
        self.assertEqual(snapshot.limits["event_count"], 3)
        self.assertEqual(snapshot.limits["event_window_count"], 2)
        self.assertEqual(snapshot.limits["event_window_start_sequence"], 1)
        self.assertEqual(snapshot.limits["event_window_end_sequence"], 2)


class ActivationRunnerContextTests(unittest.TestCase):
    def test_runner_passes_context_snapshot_and_checkpoints_metadata(self) -> None:
        clock = FixedClock(NOW)
        agent = AgentDefinition(
            agent_id="agent-1",
            name="Test Agent",
            instructions="Return Decisions only.",
        )
        session_store = InMemorySessionStore()
        inbox_store = InMemoryInboxStore()
        event_store = InMemoryEventStore()
        checkpoint_store = InMemoryCheckpointStore()
        memory_store = InMemoryMemoryStore()
        model = ContextAwareModel()

        session_store.create(_session(created_at=clock(), updated_at=clock()))
        event_store.append(_event("evt-0", sequence=0), expected_next_sequence=0)
        checkpoint_store.save(_checkpoint("chk-0", revision=0, event_sequence=0))
        memory_store.save(
            _memory(
                "mem-1",
                content={"summary": "prior context"},
                source_event_ids=("evt-0",),
                idempotency_key="memory-1",
                created_at=clock(),
            )
        )
        inbox_store.enqueue(_signal(created_at=clock()))

        runner = ActivationRunner(
            agent=agent,
            model=model,
            session_store=session_store,
            inbox_store=inbox_store,
            event_store=event_store,
            checkpoint_store=checkpoint_store,
            context_builder=ContextBuilder(
                event_store=event_store,
                memory_store=memory_store,
                checkpoint_store=checkpoint_store,
                clock=clock,
            ),
            clock=clock,
        )

        result = runner.run_once("sess-1")

        self.assertTrue(result.activated)
        self.assertIsNotNone(result.context_snapshot)
        self.assertIs(model.context.context_snapshot, result.context_snapshot)
        self.assertEqual(model.context.events, result.context_snapshot.event_window)
        self.assertEqual(result.context_snapshot.event_ids, ("evt-0",))
        self.assertEqual(result.context_snapshot.memory_ids, ("mem-1",))
        self.assertEqual(result.context_snapshot.latest_checkpoint_id, "chk-0")
        self.assertEqual(result.decision.payload["content"], "mem-1")
        self.assertEqual([event.sequence for event in result.events], [1, 2])

        metadata = result.checkpoint.state["context_snapshot"]
        self.assertEqual(metadata["event_ids"], ("evt-0",))
        self.assertEqual(metadata["memory_ids"], ("mem-1",))
        self.assertEqual(metadata["latest_checkpoint_id"], "chk-0")


@dataclass
class ContextAwareModel:
    context: ActivationContext | None = None

    def decide(self, context: ActivationContext) -> Decision:
        self.context = context
        memory_ids = context.context_snapshot.memory_ids if context.context_snapshot else ()
        return Decision(
            decision_id="dec-1",
            session_id=context.session.session_id,
            kind=DecisionKind.FINAL_ANSWER,
            payload={"content": ",".join(memory_ids) or "empty"},
            created_at=context.now,
        )


class FixedClock:
    def __init__(self, start: datetime) -> None:
        self._current = start

    def __call__(self) -> datetime:
        current = self._current
        self._current = self._current + timedelta(seconds=1)
        return current


def _session(
    *,
    session_id: str = "sess-1",
    created_at: datetime = NOW,
    updated_at: datetime = NOW,
) -> Session:
    return Session(
        session_id=session_id,
        agent_id="agent-1",
        status=SessionStatus.IDLE,
        created_at=created_at,
        updated_at=updated_at,
    )


def _signal(
    *,
    signal_id: str = "sig-1",
    session_id: str = "sess-1",
    created_at: datetime = NOW,
) -> Signal:
    return Signal(
        signal_id=signal_id,
        session_id=session_id,
        signal_type="user_message",
        payload={"content": "hello"},
        created_at=created_at,
        idempotency_key="request-1",
    )


def _event(event_id: str, *, sequence: int) -> Event:
    return Event(
        event_id=event_id,
        session_id="sess-1",
        event_type="fact",
        sequence=sequence,
        payload={"event_id": event_id},
        occurred_at=NOW + timedelta(seconds=sequence),
        source_signal_id="sig-0",
    )


def _memory(
    memory_id: str,
    *,
    content: dict[str, object] | None = None,
    source_event_ids: tuple[str, ...] = (),
    created_at: datetime = NOW,
    idempotency_key: str | None = None,
    supersedes_memory_ids: tuple[str, ...] = (),
) -> MemoryRecord:
    return MemoryRecord(
        memory_id=memory_id,
        session_id="sess-1",
        memory_type="summary",
        content=content or {"summary": memory_id},
        source_event_ids=source_event_ids,
        created_at=created_at,
        idempotency_key=idempotency_key,
        supersedes_memory_ids=supersedes_memory_ids,
    )


def _checkpoint(checkpoint_id: str, *, revision: int, event_sequence: int) -> Checkpoint:
    return Checkpoint(
        checkpoint_id=checkpoint_id,
        session_id="sess-1",
        session_revision=revision,
        event_sequence=event_sequence,
        state={"status": "idle"},
        created_at=NOW + timedelta(seconds=event_sequence),
    )


if __name__ == "__main__":
    unittest.main()
