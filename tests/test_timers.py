from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from examples.timer_session import run_timer_session
from sessgraph import (
    ConcurrencyError,
    IdempotencyConflictError,
    InMemoryInboxStore,
    InMemoryTimerStore,
    SessionStatus,
    TimerDispatcher,
    TimerRecord,
    TimerStatus,
)


NOW = datetime(2026, 6, 20, 11, 0, tzinfo=timezone.utc)


class TimerRecordTests(unittest.TestCase):
    def test_timer_record_round_trips_and_freezes_data(self) -> None:
        timer = _timer("timer-1", due_at=NOW, data={"items": [{"n": 1}]})

        restored = TimerRecord.from_dict(timer.to_dict())

        self.assertEqual(restored, timer)
        self.assertEqual(restored.to_dict()["schema_version"], 1)
        with self.assertRaises(TypeError):
            timer.data["extra"] = "blocked"
        with self.assertRaises(TypeError):
            timer.data["items"][0]["n"] = 2

    def test_fired_timer_requires_signal_boundary(self) -> None:
        with self.assertRaises(ValueError):
            TimerRecord(
                timer_id="timer-1",
                session_id="sess-1",
                due_at=NOW,
                reason="bad",
                created_at=NOW,
                status=TimerStatus.FIRED,
            )


class InMemoryTimerStoreTests(unittest.TestCase):
    def test_schedule_list_due_and_mark_fired(self) -> None:
        store = InMemoryTimerStore()
        due = _timer("timer-due", due_at=NOW)
        future = _timer("timer-future", due_at=NOW + timedelta(minutes=1))

        store.schedule(future)
        store.schedule(due)

        self.assertEqual(store.list_for_session("sess-1"), (future, due))
        self.assertEqual(store.list_due(NOW), (due,))

        fired = store.mark_fired(
            "timer-due",
            fired_at=NOW,
            signal_id="sess-1:signal:timer:timer-due",
        )

        self.assertEqual(fired.status, TimerStatus.FIRED)
        self.assertEqual(fired.fired_at, NOW)
        self.assertEqual(store.list_due(NOW + timedelta(hours=1)), (future,))

    def test_schedule_is_idempotent_and_rejects_conflicts(self) -> None:
        store = InMemoryTimerStore()
        timer = _timer("timer-1", due_at=NOW, idempotency_key="request-1")

        self.assertEqual(store.schedule(timer), timer)
        self.assertEqual(store.schedule(timer), timer)
        self.assertEqual(store.list_for_session("sess-1"), (timer,))

        with self.assertRaises(IdempotencyConflictError):
            store.schedule(
                _timer(
                    "timer-2",
                    due_at=NOW,
                    reason="changed",
                    idempotency_key="request-1",
                )
            )

        with self.assertRaises(IdempotencyConflictError):
            store.schedule(_timer("timer-1", due_at=NOW, reason="changed"))

    def test_mark_fired_rejects_conflicting_second_mark(self) -> None:
        store = InMemoryTimerStore()
        store.schedule(_timer("timer-1", due_at=NOW))
        store.mark_fired("timer-1", fired_at=NOW, signal_id="sig-1")

        with self.assertRaises(ConcurrencyError):
            store.mark_fired("timer-1", fired_at=NOW + timedelta(seconds=1), signal_id="sig-2")


class TimerDispatcherTests(unittest.TestCase):
    def test_dispatcher_enqueues_due_timer_signal_once(self) -> None:
        clock = ManualClock(NOW)
        timer_store = InMemoryTimerStore()
        inbox_store = InMemoryInboxStore()
        timer_store.schedule(
            _timer(
                "timer-1",
                due_at=NOW,
                reason="wake_for_followup",
                data={"topic": "timer"},
            )
        )
        dispatcher = TimerDispatcher(timer_store=timer_store, inbox_store=inbox_store, clock=clock)

        signals = dispatcher.enqueue_due()
        repeated = dispatcher.enqueue_due()

        self.assertEqual(len(signals), 1)
        self.assertEqual(repeated, ())
        self.assertEqual(signals[0].signal_id, "sess-1:signal:timer:timer-1")
        self.assertEqual(signals[0].signal_type, "timer")
        self.assertEqual(signals[0].idempotency_key, "timer:timer-1")
        self.assertEqual(signals[0].payload["timer_id"], "timer-1")
        self.assertEqual(signals[0].payload["reason"], "wake_for_followup")
        self.assertEqual(signals[0].payload["data"]["topic"], "timer")
        self.assertEqual(inbox_store.list_for_session("sess-1"), signals)
        self.assertEqual(timer_store.get("timer-1").status, TimerStatus.FIRED)

    def test_timer_signal_wakes_session_through_runner(self) -> None:
        result = run_timer_session()

        self.assertEqual(len(result.dispatched_signals), 1)
        self.assertTrue(result.activation.activated)
        self.assertEqual(result.activation.signal.signal_type, "timer")
        self.assertEqual(result.activation.signal.payload["timer_id"], "timer-1")
        self.assertEqual(result.activation.session.status, SessionStatus.COMPLETED)
        self.assertEqual(result.activation.decision.payload["content"], "timer fired")
        self.assertEqual([event.event_type for event in result.activation.events], [
            "signal_received",
            "decision_produced",
        ])
        self.assertEqual(
            result.activation.checkpoint.state["signal"]["payload"]["reason"],
            "wake_for_followup",
        )


class ManualClock:
    def __init__(self, current: datetime) -> None:
        self._current = current

    def __call__(self) -> datetime:
        return self._current

    def set(self, current: datetime) -> None:
        self._current = current


def _timer(
    timer_id: str,
    *,
    due_at: datetime,
    reason: str = "wake",
    data: dict[str, object] | None = None,
    idempotency_key: str | None = None,
) -> TimerRecord:
    return TimerRecord(
        timer_id=timer_id,
        session_id="sess-1",
        due_at=due_at,
        reason=reason,
        data=data or {},
        created_at=NOW,
        idempotency_key=idempotency_key,
    )


if __name__ == "__main__":
    unittest.main()
