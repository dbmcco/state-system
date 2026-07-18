from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system.audit_ledger import StateAuditLedger
from state_system.gap_acknowledgement import GapAcknowledgementLedger, acknowledge_gap


NOW = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)


class GapAcknowledgementLedgerTests(unittest.TestCase):
    def test_acknowledge_gap_persists_canonical_ack_without_authorizing(self):
        with TemporaryDirectory() as directory:
            ledger = StateAuditLedger(Path(directory) / "audit.jsonl", clock=lambda: NOW)
            acknowledgements = GapAcknowledgementLedger(ledger)

            record = acknowledgements.acknowledge_gap(
                "gap:source.stale",
                request_id="request-gap-1",
                idempotency_key="idem-gap-1",
                acknowledged_by_ref="actor:agent",
                reason="reviewed and disclosed to the user",
                scope="instance:home",
            )

            self.assertEqual("gap_acknowledgement", record["event_type"])
            self.assertFalse(record["authorizes"])
            self.assertNotIn("authorization_ref", record["payload"])
            self.assertEqual("gap:source.stale", record["payload"]["gap_ref"])
            self.assertTrue(ledger.verify())

    def test_acknowledge_gap_replays_idempotently(self):
        with TemporaryDirectory() as directory:
            ledger = StateAuditLedger(Path(directory) / "audit.jsonl", clock=lambda: NOW)
            first = acknowledge_gap(
                ledger,
                gap_ref="gap:source.stale",
                request_id="request-gap-1",
                idempotency_key="idem-gap-1",
                acknowledged_by_ref="actor:agent",
                reason="reviewed",
            )
            replay = acknowledge_gap(
                ledger,
                gap_ref="gap:source.stale",
                request_id="request-gap-1",
                idempotency_key="idem-gap-1",
                acknowledged_by_ref="actor:agent",
                reason="reviewed",
            )

            self.assertEqual(first["entry_hash"], replay["entry_hash"])
            self.assertEqual(1, len(ledger.entries()))


if __name__ == "__main__":
    unittest.main()
