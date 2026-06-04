from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system.committer import Committer
from state_system.contracts import load_json
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]


class GovernancePressureTests(unittest.TestCase):
    def test_external_publication_opportunity_is_pending_and_cites_target_state(self):
        model_output = load_json(
            ROOT / "examples" / "laura-southern-abrasives-opportunity-model-output.json"
        )

        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            result = Committer(stores, self._schemas()).commit(
                model_output,
                created_at="2026-04-28T16:11:00Z",
                evidence_refs=set(),
            )

            self.assertEqual("pending_approval", result["status"])
            self.assertEqual([], result["accepted_journal_entry_refs"])
            self.assertEqual([], result["accepted_memory_entry_refs"])
            self.assertEqual([], stores.journals.list_ids())
            self.assertEqual([], stores.memory.list_ids())
            self.assertEqual(
                ["state.operating_picture.marketing"],
                [item["state_object_id"] for item in result["queued_rollup_requests"]],
            )
            self.assertEqual(
                "state.sampleco.deal.southern-abrasives",
                result["pending_approvals"][0]["target_ref"],
            )

    def test_missing_contract_evidence_records_uncertainty_without_fabricating_truth(self):
        model_output = load_json(ROOT / "examples" / "patrick-model-proposal-output.json")
        expected_snapshot = load_json(
            ROOT / "examples" / "harbor-contract-obligation-state-after-patrick.json"
        )

        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            stores.state_objects.create(
                load_json(ROOT / "examples" / "harbor-contract-obligation-state.json")
            )

            result = Committer(stores, self._schemas()).commit(
                model_output,
                created_at="2026-04-28T14:17:00Z",
                evidence_refs={
                    "sampleco-process/pipeline/ops-manager-operating-model.md",
                    "state.sampleco.contract.harbor",
                },
            )

            journal = stores.journals.read("journal.sampleco.contract.harbor.stale-review")
            snapshot = stores.state_objects.read("state.sampleco.contract.harbor")
            self.assertEqual("accepted", result["status"])
            self.assertIn("Current contract stage is not evidenced.", journal["uncertainty"])
            self.assertEqual("waiting_on_internal", snapshot["status"])
            self.assertNotEqual("done", snapshot["status"])
            self.assertNotEqual("ready_to_act", snapshot["status"])
            for evidence_ref in expected_snapshot["evidence_refs"]:
                self.assertIn(evidence_ref, snapshot["evidence_refs"])
            self.assertEqual(
                expected_snapshot["latest_journal_entry_id"],
                snapshot["latest_journal_entry_id"],
            )

    def test_corrective_update_appends_later_journal_without_editing_original(self):
        first_output = load_json(ROOT / "examples" / "laura-model-proposal-output.json")
        second_output = self._corrective_campaign_output()

        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            stores.state_objects.create(
                load_json(ROOT / "examples" / "marketing-campaign-state.json")
            )
            committer = Committer(stores, self._schemas())

            committer.commit(
                first_output,
                created_at="2026-04-28T13:07:00Z",
                evidence_refs={
                    "conversation.2026-04-28.state-system",
                    "state.campaign.launch-positioning-v1",
                },
            )
            original_journal = deepcopy(
                stores.journals.read(
                    "journal.campaign.launch-positioning-v1.audience-clarified"
                )
            )
            committer.commit(
                second_output,
                created_at="2026-04-28T13:32:00Z",
                evidence_refs={
                    "journal.campaign.launch-positioning-v1.audience-clarified",
                    "conversation.2026-04-28.state-system",
                },
            )

            self.assertEqual(
                [
                    "journal.campaign.launch-positioning-v1.audience-clarified",
                    "journal.campaign.launch-positioning-v1.correct-proof-gap",
                ],
                stores.journals.list_ids(),
            )
            self.assertEqual(
                original_journal,
                stores.journals.read(
                    "journal.campaign.launch-positioning-v1.audience-clarified"
                ),
            )
            snapshot = stores.state_objects.read("state.campaign.launch-positioning-v1")
            self.assertEqual(
                "journal.campaign.launch-positioning-v1.correct-proof-gap",
                snapshot["latest_journal_entry_id"],
            )
            self.assertIn("Proof point is now the next blocker", snapshot["summary"])

    def _schemas(self):
        return {
            "model_output": load_json(ROOT / "schemas" / "model-proposal-output.schema.json"),
            "journal": load_json(ROOT / "schemas" / "state-journal-entry.schema.json"),
            "memory": load_json(ROOT / "schemas" / "agent-memory-entry.schema.json"),
            "state": load_json(ROOT / "schemas" / "state-object.schema.json"),
            "commit": load_json(ROOT / "schemas" / "commit-result.schema.json"),
            "review_signal": load_json(ROOT / "schemas" / "review-signal.schema.json"),
        }

    def _corrective_campaign_output(self):
        return {
            "id": "model_output.laura.campaign-proof-gap-correction",
            "review_packet_id": "review_packet.laura.campaign-proof-gap-correction",
            "decision": "propose_updates",
            "observations": ["The proof point gap should be reflected as the next blocker."],
            "state_proposals": [
                {
                    "target_state_object_id": "state.campaign.launch-positioning-v1",
                    "update_class": "corrective",
                    "interpretation": "Audience is clear; proof point selection is now the next blocker.",
                    "state_patch": {
                        "summary": "Proof point is now the next blocker after audience clarification for the launch positioning campaign.",
                        "open_questions": [
                            "What proof point makes the offer credible?"
                        ],
                    },
                    "evidence_refs": [
                        "journal.campaign.launch-positioning-v1.audience-clarified",
                        "conversation.2026-04-28.state-system",
                    ],
                    "uncertainty": ["The proof point has still not been selected."],
                    "approval_required": False,
                }
            ],
            "memory_proposals": [],
            "promotion_proposals": [],
            "action_proposals": [],
            "rollup_requests": [],
            "uncertainty": ["The proof point has still not been selected."],
            "missing_evidence": [],
            "review_signal": {
                "id": "review.laura.campaign-proof-gap-correction",
                "trigger_id": "trigger.laura.campaign-proof-gap-correction",
                "created_at": "2026-04-28T13:31:00Z",
                "status": "committed",
                "summary": "Campaign proof gap correction should append after audience clarification.",
                "journal_entry_refs": [
                    "journal.campaign.launch-positioning-v1.correct-proof-gap"
                ],
                "memory_entry_refs": [],
                "rollup_requests": [],
                "follow_up_refs": [],
            },
        }


if __name__ == "__main__":
    unittest.main()
