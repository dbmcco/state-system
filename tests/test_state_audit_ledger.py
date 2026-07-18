from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system.audit_ledger import LedgerConflictError, LedgerTamperError, StateAuditLedger


NOW = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)


def decision(reason: str = "source freshness inspected") -> dict[str, object]:
    return {
        "protocol_version": "state-system.v1",
        "decision": "degrade",
        "reason": reason,
        "route_ref": "route:state.inspect",
        "decided_at": NOW.isoformat().replace("+00:00", "Z"),
        "evidence_refs": ["evidence:source.freshness"],
        "gap_refs": ["gap:source.stale"],
        "requires_refresh_before_external_action": True,
    }


class StateAuditLedgerTests(unittest.TestCase):
    def test_appends_context_decision_as_redacted_hash_chained_jsonl(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            ledger = StateAuditLedger(path, clock=lambda: NOW)

            record = ledger.append_context_decision(
                decision("PRIVATE MESSAGE BODY: do not persist"),
                request_id="request-1",
                correlation_id="correlation-1",
                idempotency_key="idem-1",
                actor_ref="actor:agent",
            )

            self.assertEqual("state_context_decision", record["event_type"])
            self.assertNotIn("PRIVATE MESSAGE BODY", path.read_text(encoding="utf-8"))
            self.assertEqual(64, len(record["entry_hash"]))
            self.assertEqual("0" * 64, record["previous_hash"])
            self.assertTrue(ledger.verify())

    def test_duplicate_request_correlation_or_idempotency_is_idempotent(self):
        with TemporaryDirectory() as directory:
            ledger = StateAuditLedger(Path(directory) / "audit.jsonl", clock=lambda: NOW)
            first = ledger.append_context_decision(
                decision(),
                request_id="request-1",
                correlation_id="correlation-1",
                idempotency_key="idem-1",
                actor_ref="actor:agent",
            )

            for request_id, correlation_id, idempotency_key in (
                ("request-1", "correlation-new", "idem-new"),
                ("request-new", "correlation-1", "idem-newer"),
                ("request-newer", "correlation-newer", "idem-1"),
            ):
                replay = ledger.append_context_decision(
                    decision(),
                    request_id=request_id,
                    correlation_id=correlation_id,
                    idempotency_key=idempotency_key,
                    actor_ref="actor:agent",
                )
                self.assertEqual(first["entry_hash"], replay["entry_hash"])

            self.assertEqual(1, len(ledger.entries()))

    def test_conflicting_duplicate_is_rejected_and_tampering_is_detected(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            ledger = StateAuditLedger(path, clock=lambda: NOW)
            ledger.append_context_decision(
                decision(),
                request_id="request-1",
                correlation_id="correlation-1",
                idempotency_key="idem-1",
                actor_ref="actor:agent",
            )

            with self.assertRaises(LedgerConflictError):
                ledger.append_context_decision(
                    decision("different"),
                    request_id="request-1",
                    correlation_id="correlation-1",
                    idempotency_key="idem-1",
                    actor_ref="actor:agent",
                )

            raw = json.loads(path.read_text(encoding="utf-8"))
            raw["payload"]["route_ref"] = "route:tampered"
            path.write_text(json.dumps(raw) + "\n", encoding="utf-8")
            with self.assertRaises(LedgerTamperError):
                ledger.verify()


if __name__ == "__main__":
    unittest.main()
