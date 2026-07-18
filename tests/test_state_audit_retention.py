from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system.audit_ledger import StateAuditLedger


BASE = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)


def decision(at: datetime) -> dict[str, object]:
    return {
        "protocol_version": "state-system.v1",
        "decision": "include",
        "reason": "retention test",
        "route_ref": "route:state.inspect",
        "decided_at": at.isoformat().replace("+00:00", "Z"),
    }


class StateAuditRetentionTests(unittest.TestCase):
    def test_prunes_entries_after_400_days_and_keeps_seven_year_checkpoint(self):
        with TemporaryDirectory() as directory:
            now = BASE
            current = {"now": now}
            ledger = StateAuditLedger(
                Path(directory) / "audit.jsonl", clock=lambda: current["now"]
            )
            old_at = now - timedelta(days=401)
            old = ledger.append_context_decision(
                decision(old_at),
                request_id="request-old",
                idempotency_key="idem-old",
                actor_ref="actor:agent",
            )
            recent = ledger.append_context_decision(
                decision(now - timedelta(days=10)),
                request_id="request-recent",
                idempotency_key="idem-recent",
                actor_ref="actor:agent",
            )

            result = ledger.prune()

            self.assertEqual(1, result["pruned_entries"])
            self.assertEqual([recent["entry_hash"]], [entry["entry_hash"] for entry in ledger.entries()])
            self.assertEqual(1, len(ledger.checkpoints()))
            self.assertEqual(old["entry_hash"], ledger.checkpoints()[0]["chain_head_hash"])
            self.assertEqual(
                now + timedelta(days=365 * 7),
                datetime.fromisoformat(
                    ledger.checkpoints()[0]["retain_until"].replace("Z", "+00:00")
                ),
            )
            self.assertTrue(ledger.verify())

    def test_expired_checkpoints_are_removed_deterministically(self):
        with TemporaryDirectory() as directory:
            current = {"now": BASE}
            ledger = StateAuditLedger(
                Path(directory) / "audit.jsonl", clock=lambda: current["now"]
            )
            ledger.append_context_decision(
                decision(BASE - timedelta(days=401)),
                request_id="request-old",
                idempotency_key="idem-old",
                actor_ref="actor:agent",
            )
            ledger.prune()
            current["now"] = BASE + timedelta(days=365 * 7 + 1)
            result = ledger.prune()

            self.assertEqual(1, result["expired_checkpoints"])
            self.assertEqual([], ledger.checkpoints())
            self.assertTrue(ledger.verify())


if __name__ == "__main__":
    unittest.main()
