from __future__ import annotations

from pathlib import Path
import unittest

from state_system.staleness_runner import (
    StalenessOutputValidationError,
    load_staleness_schemas,
    parse_instant,
    run_staleness_review,
)


ROOT = Path(__file__).resolve().parents[1]


class _UngroundedEvidenceReviewer:
    def review(self, packet: dict) -> dict:
        finding = packet["findings"][0]
        return {
            "id": "staleness_review_output.ungrounded",
            "review_packet_id": packet["id"],
            "created_at": "2026-06-25T12:00:00Z",
            "review_week": packet["review_week"],
            "decision": "surface_decisions",
            "observations": [],
            "entries": [
                {
                    "scope_key": finding["scope_key"],
                    "nl_question": "Is the source stale?",
                    "recommended_action": "refresh",
                    "classification": "objective_stale",
                    "confidence": 0.9,
                    "evidence_refs": ["evidence:not-present-in-packet"],
                    "rationale": "This cites evidence not present in the packet.",
                }
            ],
            "uncertainty": [],
            "auto_demote_enabled": False,
            "review_signal": {
                "id": "review_signal.ungrounded",
                "status": "surface_decisions",
                "created_at": "2026-06-25T12:00:00Z",
                "trigger_ref": packet["id"],
            },
        }


class CommitEvidenceGroundingTests(unittest.TestCase):
    def test_staleness_review_output_rejects_evidence_refs_not_in_packet(self):
        schemas = load_staleness_schemas(ROOT)
        record = {
            "id": "instance_source_freshness.sample.docs.2026-06-01",
            "scope_key": "state_instance.sample|connector.sample.docs|docs:sample",
            "instance_ref": "state_instance.sample",
            "connector_ref": "connector.sample.docs",
            "source_ref": "docs:sample",
            "status": "stale",
            "checked_at": "2026-06-01T00:00:00Z",
            "stale_after": "2026-06-02T00:00:00Z",
            "watermark_basis": "source_content",
            "status_reason": "source content has not changed since June 1",
            "evidence_refs": ["evidence:declared-in-packet"],
        }

        with self.assertRaisesRegex(
            StalenessOutputValidationError, "evidence:not-present-in-packet"
        ):
            run_staleness_review(
                records=[record],
                as_of=parse_instant("2026-06-25T12:00:00Z"),
                reviewer=_UngroundedEvidenceReviewer(),
                packet_schema=schemas["staleness_packet"],
                output_schema=schemas["staleness_output"],
            )


if __name__ == "__main__":
    unittest.main()
