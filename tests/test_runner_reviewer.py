from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system.contracts import load_json, validate_schema
from state_system.reviewer import FixtureReviewer
from state_system.runner import ReviewPacketBuilder, SourceEventIngestor
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]


class RunnerReviewerTests(unittest.TestCase):
    def test_runner_builds_existing_laura_review_packet_shape(self):
        expected = load_json(ROOT / "examples" / "laura-model-review-packet.json")
        stores = self._stores_for_expected_packet(expected)

        packet = ReviewPacketBuilder(stores).build(
            trigger=expected["trigger"],
            created_at=expected["created_at"],
            packet_id=expected["id"],
            resolved_evidence_by_ref={
                item["ref"]: item for item in expected["evidence_packet"]["resolved_evidence"]
            },
            unresolved_evidence_refs=expected["evidence_packet"][
                "unresolved_evidence_refs"
            ],
            persona=expected["persona_context"]["persona"],
            governance_constraints=expected["governance_context"]["constraints"],
        )

        schema = load_json(ROOT / "schemas" / "model-review-packet.schema.json")
        self.assertEqual(expected, packet)
        self.assertEqual([], validate_schema(packet, schema))

    def test_runner_builds_packet_from_ingested_source_event(self):
        source_event = load_json(
            ROOT / "examples" / "source-linear-southern-abrasives-won.json"
        )
        source_schema = load_json(ROOT / "schemas" / "source-event.schema.json")

        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            ingested = SourceEventIngestor(stores, source_schema).ingest(source_event)
            packet = ReviewPacketBuilder(stores).build(
                trigger=ingested.trigger,
                created_at="2026-04-28T16:05:30Z",
                packet_id="review_packet.linear.southern-abrasives-won",
                resolved_evidence_by_ref={
                    "linear:event:southern-abrasives-stage-won-2026-04-28": {
                        "ref": "linear:event:southern-abrasives-stage-won-2026-04-28",
                        "summary": (
                            "Linear stage change event shows Southern Abrasives "
                            "moved from proposal to won."
                        ),
                        "source_type": "linear_event",
                        "observed_at": "2026-04-28T16:05:00Z",
                    }
                },
                unresolved_evidence_refs=[
                    "linear:deal:southern-abrasives.delivery-handoff"
                ],
                persona={"id": "persona.patrick", "name": "Patrick"},
            )
            source_event_ids = [record["id"] for record in stores.source_events.replay()]

        self.assertEqual(ingested.trigger, packet["trigger"])
        self.assertEqual(
            ["source.linear.southern-abrasives-won"],
            source_event_ids,
        )
        self.assertIn(
            "linear:deal:southern-abrasives",
            packet["evidence_packet"]["unresolved_evidence_refs"],
        )
        schema = load_json(ROOT / "schemas" / "model-review-packet.schema.json")
        self.assertEqual([], validate_schema(packet, schema))

    def test_fixture_reviewer_replays_all_example_model_outputs(self):
        reviewer = FixtureReviewer.from_examples(ROOT / "examples")
        output_paths = sorted(
            path
            for path in (ROOT / "examples").glob("*.json")
            if "model-output" in path.name or "model-proposal-output" in path.name
        )

        self.assertGreater(len(output_paths), 0)
        for path in output_paths:
            expected = load_json(path)
            packet = {"id": expected["review_packet_id"]}

            self.assertEqual(expected, reviewer.review(packet))

    def test_no_op_and_missing_evidence_fixtures_do_not_mutate_state(self):
        no_op = {
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
            "review_signal": {"id": "review.no-op", "status": "no_op"},
        }
        missing_evidence = {
            "id": "model_output.missing-evidence",
            "review_packet_id": "review_packet.missing-evidence",
            "decision": "needs_evidence",
            "observations": ["Evidence is missing."],
            "state_proposals": [],
            "memory_proposals": [],
            "promotion_proposals": [],
            "action_proposals": [],
            "rollup_requests": [],
            "uncertainty": ["The source record could not be resolved."],
            "missing_evidence": [
                {
                    "summary": "Canonical source record is missing.",
                    "needed_ref_or_source": "source system record",
                }
            ],
            "review_signal": {
                "id": "review.missing-evidence",
                "status": "evidence_missing",
            },
        }

        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            stores.state_objects.create({"id": "state.example", "summary": "Unchanged"})
            reviewer = FixtureReviewer(
                {
                    no_op["review_packet_id"]: no_op,
                    missing_evidence["review_packet_id"]: missing_evidence,
                }
            )

            self.assertEqual(no_op, reviewer.review({"id": "review_packet.no-op"}))
            self.assertEqual(
                missing_evidence,
                reviewer.review({"id": "review_packet.missing-evidence"}),
            )
            self.assertEqual(
                {"id": "state.example", "summary": "Unchanged"},
                stores.state_objects.read("state.example"),
            )

    def _stores_for_expected_packet(self, expected):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        stores = StateStoreBundle(Path(temporary.name))
        for snapshot in expected["state_context"]["snapshots"]:
            stores.state_objects.create(snapshot)
        for entry in expected["journal_context"]["recent_entries"]:
            stores.journals.create(entry)
        for entry in expected["memory_context"]["entries"]:
            stores.memory.create(entry)
        return stores


if __name__ == "__main__":
    unittest.main()
