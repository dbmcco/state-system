from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system.committer import Committer, CommitValidationError
from state_system.contracts import load_json, validate_schema
from state_system.stores import StateStoreBundle
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
    def test_schema_validator_honors_review_packet_min_items(self):
        schema = load_json(ROOT / "schemas" / "model-review-packet.schema.json")
        packet = load_json(ROOT / "examples" / "maya-model-review-packet.json")
        packet["evidence_packet"]["evidence_refs"] = []

        errors = validate_schema(packet, schema)

        self.assertTrue(errors)
        self.assertTrue(
            any("evidence_refs" in error and "minItems" in error for error in errors),
            errors,
        )

    def test_committer_rejects_unknown_review_packet_id(self):
        model_output = load_json(ROOT / "examples" / "maya-model-proposal-output.json")

        with TemporaryDirectory() as directory:
            stores = self._stores_with_campaign(Path(directory))

            with self.assertRaisesRegex(
                CommitValidationError,
                "review_packet.maya.campaign-audience-clarified",
            ):
                Committer(stores, self._schemas()).commit(
                    model_output,
                    created_at="2026-04-28T13:07:00Z",
                    evidence_refs={"conversation.2026-04-28.state-system"},
                )

            self.assertEqual([], stores.journals.list_ids())
            self.assertEqual([], stores.memory.list_ids())

    def test_committer_uses_stored_review_packet_evidence_allowlist(self):
        model_output = load_json(ROOT / "examples" / "maya-model-proposal-output.json")

        with TemporaryDirectory() as directory:
            stores = self._stores_with_campaign(Path(directory))
            stores.review_packets.create(
                load_json(ROOT / "examples" / "maya-model-review-packet.json")
            )

            result = Committer(stores, self._schemas()).commit(
                model_output,
                created_at="2026-04-28T13:07:00Z",
                evidence_refs={
                    "conversation.2026-04-28.state-system",
                    "state.campaign.launch-positioning-v1",
                },
            )

            self.assertEqual("rejected", result["status"])
            self.assertEqual([], stores.journals.list_ids())
            self.assertEqual([], stores.memory.list_ids())
            self.assertTrue(
                any(
                    "state.campaign.launch-positioning-v1" in item["reason"]
                    for item in result["rejected_proposals"]
                ),
                result["rejected_proposals"],
            )

    def test_committer_cannot_smuggle_new_evidence_refs_into_acceptance(self):
        model_output = load_json(ROOT / "examples" / "maya-model-proposal-output.json")
        packet = load_json(ROOT / "examples" / "maya-model-review-packet.json")
        packet["evidence_packet"]["evidence_refs"] = [
            "conversation.2026-04-28.state-system",
            "conversation.2026-04-28.state-system",
        ]

        with TemporaryDirectory() as directory:
            stores = self._stores_with_campaign(Path(directory))
            stores.review_packets.create(packet)

            result = Committer(stores, self._schemas()).commit(
                model_output,
                created_at="2026-04-28T13:07:00Z",
                evidence_refs={
                    "conversation.2026-04-28.state-system",
                    "state.campaign.launch-positioning-v1",
                    "proposal:smuggled-evidence-ref",
                },
            )

            self.assertEqual("rejected", result["status"])
            self.assertEqual([], result["accepted_journal_entry_refs"])
            self.assertEqual([], result["accepted_memory_entry_refs"])
            self.assertEqual([], stores.journals.list_ids())
            self.assertEqual([], stores.memory.list_ids())
            self.assertNotIn(
                "proposal:smuggled-evidence-ref",
                stores.review_packets.read(packet["id"])["evidence_packet"]["evidence_refs"],
            )

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
            "latest_source_modified_at": "2026-06-01T00:00:00Z",
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

    def _stores_with_campaign(self, root: Path) -> StateStoreBundle:
        stores = StateStoreBundle(root)
        stores.state_objects.create(
            load_json(ROOT / "examples" / "marketing-campaign-state.json")
        )
        return stores

    def _schemas(self):
        return {
            "model_output": load_json(ROOT / "schemas" / "model-proposal-output.schema.json"),
            "review_packet": load_json(ROOT / "schemas" / "model-review-packet.schema.json"),
            "journal": load_json(ROOT / "schemas" / "state-journal-entry.schema.json"),
            "memory": load_json(ROOT / "schemas" / "agent-memory-entry.schema.json"),
            "state": load_json(ROOT / "schemas" / "state-object.schema.json"),
            "commit": load_json(ROOT / "schemas" / "commit-result.schema.json"),
            "review_signal": load_json(ROOT / "schemas" / "review-signal.schema.json"),
        }


if __name__ == "__main__":
    unittest.main()
