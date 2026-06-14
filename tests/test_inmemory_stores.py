from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import unittest

from sessgraph import (
    Checkpoint,
    ConcurrencyError,
    DuplicateRecordError,
    Event,
    IdempotencyConflictError,
    InMemoryCheckpointStore,
    InMemoryEventStore,
    InMemoryInboxStore,
    InMemorySessionStore,
    RecordNotFoundError,
    Session,
    SessionStatus,
    Signal,
)


NOW = datetime(2026, 6, 14, 9, 0, tzinfo=timezone.utc)


class InMemorySessionStoreTests(unittest.TestCase):
    def test_create_get_and_list_sessions_return_snapshots(self) -> None:
        store = InMemorySessionStore()
        session = _session(revision=0)

        created = store.create(session)

        self.assertEqual(created, session)
        self.assertIsNot(created, session)
        self.assertEqual(store.get("sess-1"), session)
        self.assertEqual(store.list_sessions(), (session,))

        with self.assertRaises(TypeError):
            created.metadata["new"] = "blocked"

    def test_create_rejects_duplicate_session(self) -> None:
        store = InMemorySessionStore()
        store.create(_session())

        with self.assertRaises(DuplicateRecordError):
            store.create(_session())

    def test_update_requires_existing_session_and_expected_revision(self) -> None:
        store = InMemorySessionStore()

        with self.assertRaises(RecordNotFoundError):
            store.update(_session(revision=1), expected_revision=0)

        store.create(_session(revision=0))
        updated = replace(_session(revision=0), status=SessionStatus.RUNNING, revision=1)

        self.assertEqual(store.update(updated, expected_revision=0), updated)

        stale = replace(updated, status=SessionStatus.COMPLETED, revision=1)
        with self.assertRaises(ConcurrencyError):
            store.update(stale, expected_revision=0)

        skipped = replace(updated, revision=3)
        with self.assertRaises(ConcurrencyError):
            store.update(skipped, expected_revision=1)


class InMemoryInboxStoreTests(unittest.TestCase):
    def test_enqueue_list_and_pop_are_fifo(self) -> None:
        store = InMemoryInboxStore()
        first = _signal("sig-1", created_at=NOW)
        second = _signal("sig-2", created_at=datetime(2026, 6, 14, 9, 1, tzinfo=timezone.utc))

        store.enqueue(first)
        store.enqueue(second)

        self.assertEqual(store.list_for_session("sess-1"), (first, second))
        self.assertEqual(store.pop_next("sess-1"), first)
        self.assertEqual(store.pop_next("sess-1"), second)
        self.assertIsNone(store.pop_next("sess-1"))
        self.assertEqual(store.get("sig-1"), first)

    def test_enqueue_is_idempotent_for_same_signal(self) -> None:
        store = InMemoryInboxStore()
        signal = _signal("sig-1", idempotency_key="request-1")

        self.assertEqual(store.enqueue(signal), signal)
        self.assertEqual(store.enqueue(signal), signal)
        self.assertEqual(store.list_for_session("sess-1"), (signal,))

    def test_enqueue_rejects_idempotency_conflicts(self) -> None:
        store = InMemoryInboxStore()
        store.enqueue(_signal("sig-1", idempotency_key="request-1", content="hello"))

        with self.assertRaises(IdempotencyConflictError):
            store.enqueue(_signal("sig-2", idempotency_key="request-1", content="changed"))

        with self.assertRaises(IdempotencyConflictError):
            store.enqueue(_signal("sig-1", content="changed"))


class InMemoryEventStoreTests(unittest.TestCase):
    def test_append_list_and_next_sequence(self) -> None:
        store = InMemoryEventStore()
        first = _event("evt-1", sequence=0)
        second = _event("evt-2", sequence=1)

        self.assertEqual(store.next_sequence("sess-1"), 0)
        self.assertEqual(store.append(first, expected_next_sequence=0), first)
        self.assertEqual(store.append(second, expected_next_sequence=1), second)

        self.assertEqual(store.next_sequence("sess-1"), 2)
        self.assertEqual(store.list_for_session("sess-1"), (first, second))
        self.assertEqual(store.get("evt-1"), first)

    def test_append_is_idempotent_for_same_event_id_and_content(self) -> None:
        store = InMemoryEventStore()
        event = _event("evt-1", sequence=0)

        self.assertEqual(store.append(event), event)
        self.assertEqual(store.append(event, expected_next_sequence=0), event)
        self.assertEqual(store.list_for_session("sess-1"), (event,))

    def test_append_rejects_sequence_gaps_and_conflicts(self) -> None:
        store = InMemoryEventStore()

        with self.assertRaises(ConcurrencyError):
            store.append(_event("evt-2", sequence=1))

        store.append(_event("evt-1", sequence=0))

        with self.assertRaises(ConcurrencyError):
            store.append(_event("evt-2", sequence=1), expected_next_sequence=0)

        with self.assertRaises(IdempotencyConflictError):
            store.append(_event("evt-1", sequence=0, payload={"changed": True}))


class InMemoryCheckpointStoreTests(unittest.TestCase):
    def test_save_get_and_latest_checkpoint(self) -> None:
        store = InMemoryCheckpointStore()
        first = _checkpoint("chk-1", revision=1, event_sequence=2)
        second = _checkpoint("chk-2", revision=2, event_sequence=4)

        self.assertEqual(store.save(first), first)
        self.assertEqual(store.save(second), second)
        self.assertEqual(store.get("chk-1"), first)
        self.assertEqual(store.latest_for_session("sess-1"), second)

    def test_save_is_idempotent_and_rejects_checkpoint_id_conflicts(self) -> None:
        store = InMemoryCheckpointStore()
        checkpoint = _checkpoint("chk-1", revision=1, event_sequence=2)

        self.assertEqual(store.save(checkpoint), checkpoint)
        self.assertEqual(store.save(checkpoint), checkpoint)

        with self.assertRaises(IdempotencyConflictError):
            store.save(_checkpoint("chk-1", revision=2, event_sequence=3))


def _session(revision: int = 0) -> Session:
    return Session(
        session_id="sess-1",
        agent_id="agent-1",
        status=SessionStatus.IDLE,
        created_at=NOW,
        updated_at=NOW,
        revision=revision,
        metadata={"scope": "test"},
    )


def _signal(
    signal_id: str,
    *,
    created_at: datetime = NOW,
    idempotency_key: str | None = None,
    content: str = "hello",
) -> Signal:
    return Signal(
        signal_id=signal_id,
        session_id="sess-1",
        signal_type="user_message",
        payload={"content": content},
        created_at=created_at,
        idempotency_key=idempotency_key,
    )


def _event(event_id: str, *, sequence: int, payload: dict[str, object] | None = None) -> Event:
    return Event(
        event_id=event_id,
        session_id="sess-1",
        event_type="signal_received",
        sequence=sequence,
        payload=payload or {"signal_id": "sig-1"},
        occurred_at=NOW,
        source_signal_id="sig-1",
    )


def _checkpoint(checkpoint_id: str, *, revision: int, event_sequence: int) -> Checkpoint:
    return Checkpoint(
        checkpoint_id=checkpoint_id,
        session_id="sess-1",
        session_revision=revision,
        event_sequence=event_sequence,
        state={"status": "idle"},
        created_at=NOW,
    )


if __name__ == "__main__":
    unittest.main()
