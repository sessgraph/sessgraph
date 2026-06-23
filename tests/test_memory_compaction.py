from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from examples.memory_compaction_session import run_memory_compaction_session
from sessgraph import (
    ContextBuilder,
    DeterministicCompactionPolicy,
    Event,
    InMemoryCheckpointStore,
    InMemoryEventStore,
    InMemoryMemoryStore,
    MemoryCompactor,
    MemoryRecord,
    Session,
    SessionStatus,
    Signal,
)


NOW = datetime(2026, 6, 23, 14, 0, tzinfo=timezone.utc)


class MemoryCompactionTests(unittest.TestCase):
    def test_compactor_writes_memory_event_and_checkpoint_boundary(self) -> None:
        fixture = _fixture()
        old_memory = _memory("mem-old")
        fixture.memory_store.save(old_memory)
        source_events = fixture.event_store.list_for_session("sess-1")[:2]

        result = fixture.compactor.compact(
            fixture.session,
            source_events=source_events,
            supersedes_memory_ids=("mem-old",),
        )

        self.assertEqual(result.memory.memory_type, "event_summary")
        self.assertEqual(result.memory.source_event_ids, ("evt-0", "evt-1"))
        self.assertEqual(result.memory.supersedes_memory_ids, ("mem-old",))
        self.assertEqual(result.memory.content["event_count"], 2)
        self.assertEqual(result.memory.content["event_types"], ("fact", "fact"))
        self.assertEqual(
            fixture.memory_store.list_active_for_session("sess-1"),
            (result.memory,),
        )

        self.assertEqual(result.event.event_type, "memory_compacted")
        self.assertEqual(result.event.sequence, 3)
        self.assertEqual(result.event.payload["memory_id"], result.memory.memory_id)
        self.assertEqual(result.event.payload["source_event_ids"], ("evt-0", "evt-1"))
        self.assertEqual(result.event.payload["supersedes_memory_ids"], ("mem-old",))
        self.assertEqual(fixture.event_store.get("evt-0").event_type, "fact")

        self.assertEqual(result.checkpoint.event_sequence, result.event.sequence)
        self.assertEqual(result.checkpoint.session_revision, fixture.session.revision)
        compaction_state = result.checkpoint.state["compaction"]
        self.assertEqual(compaction_state["memory_id"], result.memory.memory_id)
        self.assertEqual(compaction_state["active_memory_ids"], (result.memory.memory_id,))
        self.assertEqual(compaction_state["compaction_event_id"], result.event.event_id)
        self.assertEqual(
            fixture.checkpoint_store.latest_for_session("sess-1"),
            result.checkpoint,
        )

    def test_compaction_is_idempotent_for_same_explicit_inputs(self) -> None:
        fixture = _fixture()
        source_events = fixture.event_store.list_for_session("sess-1")[:2]

        first = fixture.compactor.compact(
            fixture.session,
            source_events=source_events,
            supersedes_memory_ids=(),
        )
        second = fixture.compactor.compact(
            fixture.session,
            source_events=source_events,
            supersedes_memory_ids=(),
        )

        self.assertEqual(second.memory, first.memory)
        self.assertEqual(second.event, first.event)
        self.assertEqual(second.checkpoint, first.checkpoint)
        self.assertEqual(fixture.event_store.next_sequence("sess-1"), 4)
        self.assertEqual(fixture.memory_store.list_for_session("sess-1"), (first.memory,))

    def test_context_builder_uses_active_memory_after_compaction(self) -> None:
        fixture = _fixture()
        old_memory = _memory("mem-old")
        fixture.memory_store.save(old_memory)

        result = fixture.compactor.compact(
            fixture.session,
            supersedes_memory_ids=("mem-old",),
        )
        snapshot = ContextBuilder(
            event_store=fixture.event_store,
            memory_store=fixture.memory_store,
            checkpoint_store=fixture.checkpoint_store,
            clock=fixture.clock,
        ).build(fixture.session, _signal())

        self.assertEqual(snapshot.memory_ids, (result.memory.memory_id,))
        self.assertNotIn("mem-old", snapshot.memory_ids)
        self.assertIn(result.event.event_id, snapshot.event_ids)
        self.assertEqual(snapshot.latest_checkpoint_id, result.checkpoint.checkpoint_id)

    def test_memory_compaction_example_smoke(self) -> None:
        result = run_memory_compaction_session()

        self.assertEqual(result.compaction.event.event_type, "memory_compacted")
        self.assertTrue(result.activation.activated)
        self.assertEqual(result.activation.decision.payload["content"], "context compacted")
        self.assertEqual(
            result.activation.context_snapshot.memory_ids,
            (result.compaction.memory.memory_id,),
        )
        self.assertEqual(
            result.activation.context_snapshot.latest_checkpoint_id,
            result.compaction.checkpoint.checkpoint_id,
        )


class Fixture:
    def __init__(self) -> None:
        self.clock = ManualClock(NOW)
        self.session = Session(
            session_id="sess-1",
            agent_id="agent-1",
            status=SessionStatus.IDLE,
            created_at=NOW,
            updated_at=NOW,
        )
        self.event_store = InMemoryEventStore()
        self.memory_store = InMemoryMemoryStore()
        self.checkpoint_store = InMemoryCheckpointStore()
        for sequence in range(3):
            self.event_store.append(
                _event(f"evt-{sequence}", sequence=sequence),
                expected_next_sequence=sequence,
            )
        self.compactor = MemoryCompactor(
            event_store=self.event_store,
            memory_store=self.memory_store,
            checkpoint_store=self.checkpoint_store,
            policy=DeterministicCompactionPolicy(metadata={"fixture": "test"}),
            clock=self.clock,
        )


class ManualClock:
    def __init__(self, current: datetime) -> None:
        self._current = current

    def __call__(self) -> datetime:
        current = self._current
        self._current = self._current + timedelta(seconds=1)
        return current


def _fixture() -> Fixture:
    return Fixture()


def _event(event_id: str, *, sequence: int) -> Event:
    return Event(
        event_id=event_id,
        session_id="sess-1",
        event_type="fact",
        sequence=sequence,
        payload={"content": event_id},
        occurred_at=NOW + timedelta(seconds=sequence),
    )


def _memory(memory_id: str) -> MemoryRecord:
    return MemoryRecord(
        memory_id=memory_id,
        session_id="sess-1",
        memory_type="event_summary",
        content={"summary": memory_id},
        source_event_ids=("evt-old",),
        created_at=NOW,
    )


def _signal() -> Signal:
    return Signal(
        signal_id="sig-1",
        session_id="sess-1",
        signal_type="user_message",
        payload={"content": "continue"},
        created_at=NOW,
    )


if __name__ == "__main__":
    unittest.main()
