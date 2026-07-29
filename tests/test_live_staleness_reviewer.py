from __future__ import annotations

from pathlib import Path
import unittest

from state_system.staleness_runner import (
    LiveStalenessReviewer,
    RecordedStalenessReviewer,
    build_review_packet,
    gather_findings,
    gather_freshness_records,
    parse_instant,
)
from state_system.strategic_staleness import LiveStrategicReviewer


ROOT = Path(__file__).resolve().parents[1]


class _RecordingModelClient:
    def __init__(self, output: dict):
        self.output = output
        self.calls: list[dict] = []

    def review(self, *, registry_route: str, packet: dict, schema_ref: str) -> dict:
        self.calls.append(
            {
                "registry_route": registry_route,
                "packet_id": packet["id"],
                "schema_ref": schema_ref,
            }
        )
        return dict(self.output)


class RecordedReviewerCoverageTests(unittest.TestCase):
    def test_navicyte_scoped_packet_replays_recorded_model_judgment(self):
        records = gather_freshness_records(
            freshness_dir=ROOT / "examples" / "state-reviews" / "freshness"
        )
        as_of = parse_instant("2026-06-25T12:00:00Z")
        navicyte_findings = [
            finding
            for finding in gather_findings(records, as_of=as_of)
            if finding["subject_ref"] == "state_instance.navicyte"
        ]
        packet = build_review_packet(navicyte_findings, as_of=as_of, scope="navicyte")
        reviewer = RecordedStalenessReviewer.from_examples(
            ROOT / "examples" / "state-reviews"
        )

        output = reviewer.review(packet)

        self.assertTrue(output["entries"])
        scopes = {entry["scope_key"] for entry in output["entries"]}
        self.assertEqual(
            {"state_instance.navicyte|connector.navicyte.notion|notion:navicyte-grant"},
            scopes,
        )


class LiveReviewerTests(unittest.TestCase):
    def test_live_staleness_reviewer_calls_injected_model_client(self):
        output = {
            "id": "staleness_review_output.live.test",
            "review_packet_id": "staleness_review_packet.test.2026-W26",
            "created_at": "2026-06-25T12:00:00Z",
            "review_week": "2026-W26",
            "decision": "surface_decisions",
            "observations": [],
            "entries": [],
            "uncertainty": [],
            "auto_demote_enabled": False,
            "review_signal": {
                "id": "review_signal.live.staleness",
                "status": "surface_decisions",
                "created_at": "2026-06-25T12:00:00Z",
                "trigger_ref": "staleness_review_packet.test.2026-W26",
            },
        }
        client = _RecordingModelClient(output)
        reviewer = LiveStalenessReviewer(
            registry_route="staleness-review.live", model_client=client
        )
        packet = {"id": "staleness_review_packet.test.2026-W26", "findings": []}

        reviewed = reviewer.review(packet)

        self.assertEqual(output, reviewed)
        self.assertEqual(
            [
                {
                    "registry_route": "staleness-review.live",
                    "packet_id": "staleness_review_packet.test.2026-W26",
                    "schema_ref": "staleness-review-output.schema.json",
                }
            ],
            client.calls,
        )

    def test_live_strategic_reviewer_calls_injected_model_client(self):
        output = {
            "id": "strategic_review_output.live.test",
            "review_packet_id": "strategic_review_packet.test.2026-W26",
            "created_at": "2026-06-25T12:00:00Z",
            "review_week": "2026-W26",
            "decision": "surface_decisions",
            "observations": [],
            "entries": [],
            "uncertainty": [],
            "auto_revise_enabled": False,
            "review_signal": {
                "id": "review_signal.live.strategic",
                "status": "surface_decisions",
                "created_at": "2026-06-25T12:00:00Z",
                "trigger_ref": "strategic_review_packet.test.2026-W26",
            },
        }
        client = _RecordingModelClient(output)
        reviewer = LiveStrategicReviewer(
            registry_route="strategic-review.live", model_client=client
        )
        packet = {"id": "strategic_review_packet.test.2026-W26", "findings": []}

        reviewed = reviewer.review(packet)

        self.assertEqual(output, reviewed)
        self.assertEqual(
            [
                {
                    "registry_route": "strategic-review.live",
                    "packet_id": "strategic_review_packet.test.2026-W26",
                    "schema_ref": "strategic-review-output.schema.json",
                }
            ],
            client.calls,
        )


if __name__ == "__main__":
    unittest.main()
