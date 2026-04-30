from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.committer import Committer
from state_system.context_packages import ContextPackager
from state_system.contracts import load_json, validate_schema
from state_system.recent_changes import RecentChangeIndexer
from state_system.reviewer import FixtureReviewer
from state_system.runner import ReviewPacketBuilder, SourceEventIngestor
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]


class E2EPressureHarnessTests(unittest.TestCase):
    def test_linear_won_trace_runs_from_source_event_to_persona_packages_and_cli(self):
        with TemporaryDirectory() as directory:
            state_root = Path(directory)
            stores = self._seed_southern_abrasives_runtime(state_root)
            schemas = self._schemas()
            source_event = load_json(
                ROOT / "examples" / "source-linear-southern-abrasives-won.json"
            )

            ingested = SourceEventIngestor(
                stores,
                schemas["source_event"],
            ).ingest(source_event)
            self.assertTrue(ingested.created)
            self.assertEqual("trigger.linear.southern-abrasives-won", ingested.trigger["id"])

            packet = ReviewPacketBuilder(stores).build(
                trigger=ingested.trigger,
                created_at="2026-04-28T16:05:30Z",
                packet_id="review_packet.linear.southern-abrasives-won",
                resolved_evidence_by_ref={
                    "linear:deal:southern-abrasives": {
                        "ref": "linear:deal:southern-abrasives",
                        "summary": "Linear deal record for Southern Abrasives.",
                        "source_type": "linear_deal",
                        "observed_at": "2026-04-28T16:05:00Z",
                    },
                    "linear:event:southern-abrasives-stage-won-2026-04-28": {
                        "ref": "linear:event:southern-abrasives-stage-won-2026-04-28",
                        "summary": "Linear shows Southern Abrasives moved from proposal to won.",
                        "source_type": "linear_event",
                        "observed_at": "2026-04-28T16:05:00Z",
                    },
                },
                unresolved_evidence_refs=[
                    "linear:deal:southern-abrasives.public-announcement-permission",
                    "linear:deal:southern-abrasives.delivery-handoff",
                ],
                persona=load_json(ROOT / "examples" / "patrick-persona.json"),
                governance_constraints=[
                    {
                        "id": "governance.external-copy-approval",
                        "summary": (
                            "External-facing campaign copy requires approval before "
                            "publication."
                        ),
                        "approval_required": True,
                    }
                ],
            )
            self.assertEqual([], validate_schema(packet, schemas["review_packet"]))

            model_output = FixtureReviewer.from_examples(ROOT / "examples").review(packet)
            commit = Committer(stores, schemas).commit(
                model_output,
                created_at="2026-04-28T16:07:00Z",
                evidence_refs=source_event["source_refs"],
            )
            self.assertEqual("accepted", commit["status"])
            materialized = stores.state_objects.read("state.lfw.deal.southern-abrasives")
            self.assertEqual("won", materialized["status"])
            self.assertIn(
                "journal.lfw.deal.southern-abrasives.won",
                materialized["evidence_refs"],
            )
            self.assertEqual(
                [
                    "action.patrick.southern-abrasives-handoff",
                    "action.laura.southern-abrasives-opportunity-review",
                ],
                [action["id"] for action in materialized["next_actions"]],
            )

            duplicate = SourceEventIngestor(stores, schemas["source_event"]).ingest(
                source_event
            )
            self.assertFalse(duplicate.created)
            self.assertIsNone(duplicate.trigger)
            self.assertEqual(source_event["id"], duplicate.duplicate_of)

            recent = RecentChangeIndexer(stores, schemas).index_from_source_commit(
                source_event=source_event,
                commit_result=commit,
                created_at="2026-04-28T16:07:30Z",
                summary=(
                    "Southern Abrasives moved from proposal to won, creating "
                    "operational handoff work and a possible marketing proof-point "
                    "opportunity."
                ),
                candidate_persona_routes=self._southern_abrasives_routes(),
                opportunity_class_hints=[
                    "operational_handoff",
                    "marketing_opportunity",
                    "relationship_follow_up",
                ],
                freshness={
                    "watermark_refs": [
                        "state.lfw.deal.southern-abrasives@journal.lfw.deal.southern-abrasives.won",
                        "governance.external-copy-approval",
                    ],
                    "stale_after": "2026-04-29T16:07:30Z",
                    "requires_refresh_before_external_action": True,
                },
            )
            self.assertEqual("recent.linear.southern-abrasives-won", recent["id"])

            packager = ContextPackager(stores, schemas)
            laura_package = packager.build_recent_change_package(
                persona=load_json(ROOT / "examples" / "laura-persona.json"),
                package_id="context.laura.recent-e2e",
                created_at="2026-04-28T16:08:00Z",
                review_goal="Review Laura-relevant recent changes.",
                valid_until="2026-04-29T16:08:00Z",
            )
            patrick_package = packager.build_recent_change_package(
                persona=load_json(ROOT / "examples" / "patrick-persona.json"),
                package_id="context.patrick.recent-e2e",
                created_at="2026-04-28T16:08:00Z",
                review_goal="Review Patrick-relevant recent changes.",
                valid_until="2026-04-29T16:08:00Z",
            )

            self.assertTrue(
                laura_package["freshness"]["requires_refresh_before_external_action"]
            )
            self.assertEqual(
                "secondary",
                laura_package["recent_change_context"]["entries"][0]["persona_route"][
                    "relevance_tier"
                ],
            )
            self.assertEqual(
                "primary",
                patrick_package["recent_change_context"]["entries"][0]["persona_route"][
                    "relevance_tier"
                ],
            )

            recent_output = StringIO()
            self.assertEqual(
                0,
                cli.main(
                    ["--state-root", directory, "recent", "persona.laura"],
                    stdout=recent_output,
                ),
            )
            self.assertEqual(
                ["recent.linear.southern-abrasives-won"],
                [entry["id"] for entry in json.loads(recent_output.getvalue())["entries"]],
            )

            package_output = StringIO()
            self.assertEqual(
                0,
                cli.main(
                    ["--state-root", directory, "package", "context.laura.recent-e2e"],
                    stdout=package_output,
                ),
            )
            self.assertEqual(
                "context.laura.recent-e2e",
                json.loads(package_output.getvalue())["id"],
            )

    def test_no_op_missing_evidence_and_external_action_do_not_mutate_state(self):
        with TemporaryDirectory() as directory:
            stores = self._seed_southern_abrasives_runtime(Path(directory))
            schemas = self._schemas()
            before = stores.state_objects.read("state.lfw.deal.southern-abrasives")
            committer = Committer(stores, schemas)

            no_op = self._empty_output(
                "model_output.e2e-no-op",
                "review.no-op",
                "no_op",
                "No durable update is warranted.",
            )
            no_op_commit = committer.commit(
                no_op,
                created_at="2026-04-28T17:00:00Z",
                evidence_refs=[],
            )
            self.assertEqual("no_op", no_op_commit["status"])
            self.assertEqual(before, stores.state_objects.read(before["id"]))

            missing_evidence = deepcopy(
                load_json(ROOT / "examples" / "linear-southern-abrasives-won-model-proposal-output.json")
            )
            missing_evidence["id"] = "model_output.e2e-missing-evidence"
            missing_evidence["review_packet_id"] = "review_packet.e2e-missing-evidence"
            missing_evidence["review_signal"]["id"] = "review.e2e-missing-evidence"
            rejected = committer.commit(
                missing_evidence,
                created_at="2026-04-28T17:01:00Z",
                evidence_refs=["linear:deal:southern-abrasives"],
            )
            self.assertEqual("rejected", rejected["status"])
            self.assertEqual(before, stores.state_objects.read(before["id"]))

            approval_required = self._approval_required_action_output()
            pending = committer.commit(
                approval_required,
                created_at="2026-04-28T17:02:00Z",
                evidence_refs=["linear:deal:southern-abrasives"],
            )
            self.assertEqual("pending_approval", pending["status"])
            self.assertEqual("action", pending["pending_approvals"][0]["proposal_type"])
            self.assertEqual(before, stores.state_objects.read(before["id"]))
            self.assertEqual([], stores.journals.list_ids())

    def _seed_southern_abrasives_runtime(self, root: Path) -> StateStoreBundle:
        stores = StateStoreBundle(root)
        for example in (
            "southern-abrasives-deal-state.json",
            "lfw-ops-operating-picture.json",
            "marketing-operating-picture.json",
        ):
            stores.state_objects.create(load_json(ROOT / "examples" / example))
        return stores

    def _schemas(self):
        return {
            "source_event": load_json(ROOT / "schemas" / "source-event.schema.json"),
            "review_packet": load_json(ROOT / "schemas" / "model-review-packet.schema.json"),
            "model_output": load_json(ROOT / "schemas" / "model-proposal-output.schema.json"),
            "journal": load_json(ROOT / "schemas" / "state-journal-entry.schema.json"),
            "memory": load_json(ROOT / "schemas" / "agent-memory-entry.schema.json"),
            "state": load_json(ROOT / "schemas" / "state-object.schema.json"),
            "commit": load_json(ROOT / "schemas" / "commit-result.schema.json"),
            "review_signal": load_json(ROOT / "schemas" / "review-signal.schema.json"),
            "recent_change": load_json(ROOT / "schemas" / "recent-change-entry.schema.json"),
            "context_package": load_json(ROOT / "schemas" / "context-package.schema.json"),
        }

    def _empty_output(self, output_id, review_id, decision, summary):
        return {
            "id": output_id,
            "review_packet_id": f"review_packet.{review_id}",
            "decision": decision,
            "observations": [summary],
            "state_proposals": [],
            "memory_proposals": [],
            "promotion_proposals": [],
            "action_proposals": [],
            "rollup_requests": [],
            "uncertainty": [],
            "missing_evidence": [],
            "review_signal": {
                "id": review_id,
                "trigger_id": f"trigger.{review_id}",
                "created_at": "2026-04-28T17:00:00Z",
                "status": "no_update_warranted",
                "summary": summary,
                "journal_entry_refs": [],
                "memory_entry_refs": [],
                "rollup_requests": [],
                "follow_up_refs": [],
            },
        }

    def _approval_required_action_output(self):
        return {
            "id": "model_output.e2e-external-action",
            "review_packet_id": "review_packet.e2e-external-action",
            "decision": "needs_approval",
            "observations": ["External publication requires approval."],
            "state_proposals": [],
            "memory_proposals": [],
            "promotion_proposals": [],
            "action_proposals": [
                {
                    "summary": "Publish customer-specific LinkedIn copy.",
                    "risk": "high",
                    "approval_required": True,
                    "target": {
                        "state_object_id": "state.lfw.deal.southern-abrasives"
                    },
                    "payload": {"approval_ref": "approval.laura.external-copy"},
                }
            ],
            "rollup_requests": [],
            "uncertainty": [],
            "missing_evidence": [],
            "review_signal": {
                "id": "review.e2e-external-action",
                "trigger_id": "trigger.e2e-external-action",
                "created_at": "2026-04-28T17:02:00Z",
                "status": "pending_approval",
                "summary": "External publication is pending approval.",
                "journal_entry_refs": [],
                "memory_entry_refs": [],
                "rollup_requests": [],
                "follow_up_refs": ["approval.laura.external-copy"],
            },
        }

    def _southern_abrasives_routes(self):
        return [
            {
                "persona_ref": "persona.patrick",
                "relevance_tier": "primary",
                "routing_reason": (
                    "Won deal creates operational handoff, owner, next-action, "
                    "document, and relationship-sensitivity checks."
                ),
                "included": True,
                "opportunity_class_hints": [
                    "operational_handoff",
                    "relationship_follow_up",
                ],
            },
            {
                "persona_ref": "persona.laura",
                "relevance_tier": "secondary",
                "routing_reason": (
                    "Won deal may become a marketing proof point or announcement, "
                    "but public naming permission is unresolved."
                ),
                "included": True,
                "opportunity_class_hints": [
                    "marketing_opportunity",
                    "proof_point",
                    "external_copy_candidate",
                ],
            },
        ]


if __name__ == "__main__":
    unittest.main()
