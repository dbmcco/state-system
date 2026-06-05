from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system.committer import Committer
from state_system.contracts import load_json, validate_schema
from state_system.materializer import materialize_snapshot
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]
CREATED_AT = "2026-04-28T13:07:00Z"


class CommitterMaterializerTests(unittest.TestCase):
    def test_materializer_applies_patch_and_preserves_provenance(self):
        before = load_json(ROOT / "examples" / "marketing-campaign-state.json")
        journal = load_json(
            ROOT / "examples" / "marketing-campaign-audience-journal-entry.json"
        )
        expected = load_json(
            ROOT / "examples" / "marketing-campaign-state-after-audience.json"
        )

        self.assertEqual(expected, materialize_snapshot(before, journal))

    def test_committer_accepts_supported_state_and_memory_proposals(self):
        model_output = load_json(ROOT / "examples" / "maya-model-proposal-output.json")
        expected_snapshot = load_json(
            ROOT / "examples" / "marketing-campaign-state-after-audience.json"
        )

        with TemporaryDirectory() as directory:
            stores = self._stores_with_campaign(Path(directory))
            result = Committer(stores, self._schemas()).commit(
                model_output,
                created_at=CREATED_AT,
                evidence_refs={
                    "conversation.2026-04-28.state-system",
                    "state.campaign.launch-positioning-v1",
                },
            )

            self.assertEqual("accepted", result["status"])
            self.assertEqual(
                ["journal.campaign.launch-positioning-v1.audience-clarified"],
                result["accepted_journal_entry_refs"],
            )
            self.assertEqual(
                ["memory.maya.marketing.draft.audience-before-copy"],
                result["accepted_memory_entry_refs"],
            )
            self.assertEqual(
                ["state.operating_picture.marketing"],
                [item["state_object_id"] for item in result["queued_rollup_requests"]],
            )
            self.assertEqual(
                expected_snapshot,
                stores.state_objects.read("state.campaign.launch-positioning-v1"),
            )
            self.assertEqual([], validate_schema(result, self._schemas()["commit"]))

    def test_committer_holds_approval_required_action_without_mutating_state(self):
        model_output = self._approval_required_action_output()

        with TemporaryDirectory() as directory:
            stores = self._stores_with_campaign(Path(directory))
            before = stores.state_objects.read("state.campaign.launch-positioning-v1")

            result = Committer(stores, self._schemas()).commit(
                model_output,
                created_at="2026-04-28T13:20:00Z",
                evidence_refs={"conversation.2026-04-28.state-system"},
            )

            self.assertEqual("pending_approval", result["status"])
            self.assertEqual([], stores.journals.list_ids())
            self.assertEqual([], stores.memory.list_ids())
            self.assertEqual(
                before,
                stores.state_objects.read("state.campaign.launch-positioning-v1"),
            )
            self.assertEqual("pending_approval", result["review_signal"]["status"])
            self.assertEqual("action", result["pending_approvals"][0]["proposal_type"])

    def test_committer_rejects_state_proposal_with_unresolved_evidence(self):
        model_output = load_json(ROOT / "examples" / "maya-model-proposal-output.json")

        with TemporaryDirectory() as directory:
            stores = self._stores_with_campaign(Path(directory))
            before = stores.state_objects.read("state.campaign.launch-positioning-v1")

            result = Committer(stores, self._schemas()).commit(
                model_output,
                created_at=CREATED_AT,
                evidence_refs={"state.campaign.launch-positioning-v1"},
            )

            self.assertEqual("rejected", result["status"])
            self.assertEqual([], stores.journals.list_ids())
            self.assertEqual([], stores.memory.list_ids())
            self.assertEqual(
                before,
                stores.state_objects.read("state.campaign.launch-positioning-v1"),
            )
            self.assertEqual("state", result["rejected_proposals"][0]["proposal_type"])
            self.assertEqual("rejected", result["review_signal"]["status"])

    def test_committer_rejects_protected_snapshot_patch_before_journaling(self):
        model_output = load_json(ROOT / "examples" / "maya-model-proposal-output.json")
        model_output["state_proposals"][0]["state_patch"]["as_of"] = (
            "2026-04-28T13:06:00Z"
        )

        with TemporaryDirectory() as directory:
            stores = self._stores_with_campaign(Path(directory))
            result = Committer(stores, self._schemas()).commit(
                model_output,
                created_at=CREATED_AT,
                evidence_refs={
                    "conversation.2026-04-28.state-system",
                    "state.campaign.launch-positioning-v1",
                },
            )

            self.assertEqual("rejected", result["status"])
            self.assertEqual([], stores.journals.list_ids())
            self.assertIn("protected", result["rejected_proposals"][0]["reason"])

    def test_committer_records_no_op_without_mutating_state(self):
        model_output = {
            "id": "model_output.no-op",
            "review_packet_id": "review_packet.no-op",
            "decision": "no_op",
            "observations": ["No durable update is warranted."],
            "state_proposals": [],
            "memory_proposals": [],
            "promotion_proposals": [],
            "action_proposals": [],
            "rollup_requests": [],
            "uncertainty": [],
            "missing_evidence": [],
            "review_signal": {
                "id": "review.no-op",
                "trigger_id": "trigger.no-op",
                "created_at": CREATED_AT,
                "status": "no_update_warranted",
                "summary": "No durable update is warranted.",
                "journal_entry_refs": [],
                "memory_entry_refs": [],
                "rollup_requests": [],
                "follow_up_refs": [],
            },
        }

        with TemporaryDirectory() as directory:
            stores = self._stores_with_campaign(Path(directory))
            before = stores.state_objects.read("state.campaign.launch-positioning-v1")
            result = Committer(stores, self._schemas()).commit(
                model_output,
                created_at=CREATED_AT,
                evidence_refs=set(),
            )

            self.assertEqual("no_op", result["status"])
            self.assertEqual([], stores.journals.list_ids())
            self.assertEqual([], stores.memory.list_ids())
            self.assertEqual(
                before,
                stores.state_objects.read("state.campaign.launch-positioning-v1"),
            )
            self.assertEqual("no_update_warranted", result["review_signal"]["status"])

    def test_committer_duplicate_model_output_returns_existing_commit(self):
        model_output = load_json(ROOT / "examples" / "maya-model-proposal-output.json")
        evidence_refs = {
            "conversation.2026-04-28.state-system",
            "state.campaign.launch-positioning-v1",
        }

        with TemporaryDirectory() as directory:
            stores = self._stores_with_campaign(Path(directory))
            committer = Committer(stores, self._schemas())

            first = committer.commit(
                model_output,
                created_at=CREATED_AT,
                evidence_refs=evidence_refs,
            )
            second = committer.commit(
                model_output,
                created_at=CREATED_AT,
                evidence_refs=evidence_refs,
            )

            self.assertEqual(first, second)
            self.assertEqual(
                ["journal.campaign.launch-positioning-v1.audience-clarified"],
                stores.journals.list_ids(),
            )
            self.assertEqual(
                ["memory.maya.marketing.draft.audience-before-copy"],
                stores.memory.list_ids(),
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
            "journal": load_json(ROOT / "schemas" / "state-journal-entry.schema.json"),
            "memory": load_json(ROOT / "schemas" / "agent-memory-entry.schema.json"),
            "state": load_json(ROOT / "schemas" / "state-object.schema.json"),
            "commit": load_json(ROOT / "schemas" / "commit-result.schema.json"),
            "review_signal": load_json(ROOT / "schemas" / "review-signal.schema.json"),
        }

    def _approval_required_action_output(self):
        return {
            "id": "model_output.maya.external-copy-review",
            "review_packet_id": "review_packet.maya.external-copy-review",
            "decision": "needs_approval",
            "observations": ["External publication requires approval."],
            "state_proposals": [],
            "memory_proposals": [],
            "promotion_proposals": [],
            "action_proposals": [
                {
                    "summary": "Publish external-facing campaign copy.",
                    "risk": "high",
                    "approval_required": True,
                    "target": {
                        "state_object_id": "state.campaign.launch-positioning-v1"
                    },
                    "payload": {"approval_ref": "approval.maya.external-copy"},
                }
            ],
            "rollup_requests": [],
            "uncertainty": [],
            "missing_evidence": [],
            "review_signal": {
                "id": "review.maya.external-copy-pending",
                "trigger_id": "trigger.maya.external-copy-review",
                "created_at": "2026-04-28T13:20:00Z",
                "status": "pending_approval",
                "summary": "External-facing campaign copy proposal is pending human approval.",
                "journal_entry_refs": [],
                "memory_entry_refs": [],
                "rollup_requests": [],
                "follow_up_refs": ["approval.maya.external-copy"],
            },
        }


if __name__ == "__main__":
    unittest.main()
