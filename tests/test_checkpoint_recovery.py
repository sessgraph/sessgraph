from __future__ import annotations

import unittest

from examples.checkpoint_recovery import run_checkpoint_recovery
from sessgraph import Checkpoint, Session, SessionStatus


class CheckpointRecoveryTests(unittest.TestCase):
    def test_latest_checkpoint_recovers_session_snapshot(self) -> None:
        result = run_checkpoint_recovery()

        self.assertTrue(result.activation.activated)
        self.assertEqual(result.checkpoint, result.activation.checkpoint)
        self.assertEqual(result.recovered_session, result.activation.session)
        self.assertEqual(result.recovered_session.status, SessionStatus.COMPLETED)
        self.assertEqual(result.recovered_session.checkpoint_id, result.checkpoint.checkpoint_id)
        self.assertEqual(result.recovered_session.revision, result.checkpoint.session_revision)

    def test_checkpoint_state_preserves_event_boundary(self) -> None:
        result = run_checkpoint_recovery()
        event_ids = tuple(event.event_id for event in result.activation.events)

        self.assertEqual(result.checkpoint.state["event_ids"], event_ids)
        self.assertEqual(result.checkpoint.event_sequence, result.activation.events[-1].sequence)
        self.assertEqual(len(event_ids), result.checkpoint.event_sequence + 1)

    def test_checkpoint_round_trip_still_recovers_session(self) -> None:
        result = run_checkpoint_recovery()
        checkpoint = Checkpoint.from_dict(result.checkpoint.to_dict())
        recovered_session = Session.from_dict(checkpoint.state["session"])

        self.assertEqual(checkpoint, result.checkpoint)
        self.assertEqual(recovered_session, result.recovered_session)


if __name__ == "__main__":
    unittest.main()
