from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.contracts import load_json
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]


class CliRuntimeTests(unittest.TestCase):
    def test_cli_runs_source_event_to_persona_package_loop(self):
        with TemporaryDirectory() as directory:
            state_root = Path(directory)
            stores = self._seed_runtime(state_root)
            source_path = ROOT / "examples" / "source-linear-southern-abrasives-won.json"

            trigger = self._run_cli(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "trigger",
                    str(source_path),
                ]
            )
            self.assertEqual(
                "trigger.linear.southern-abrasives-won",
                trigger["trigger"]["id"],
            )

            evidence_path = self._write_json(
                state_root / "evidence.json",
                [
                    {
                        "ref": "linear:deal:southern-abrasives",
                        "summary": "Linear deal record for Southern Abrasives.",
                        "source_type": "linear_deal",
                        "observed_at": "2026-04-28T16:05:00Z",
                    },
                    {
                        "ref": "linear:event:southern-abrasives-stage-won-2026-04-28",
                        "summary": "Linear shows Southern Abrasives moved from proposal to won.",
                        "source_type": "linear_event",
                        "observed_at": "2026-04-28T16:05:00Z",
                    },
                ],
            )
            governance_path = self._write_json(
                state_root / "governance.json",
                [
                    {
                        "id": "governance.external-copy-approval",
                        "summary": "External-facing copy requires approval before publication.",
                        "approval_required": True,
                    }
                ],
            )

            review = self._run_cli(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "review",
                    "source.linear.southern-abrasives-won",
                    "--packet-id",
                    "review_packet.linear.southern-abrasives-won",
                    "--created-at",
                    "2026-04-28T16:05:30Z",
                    "--persona",
                    str(ROOT / "examples" / "alex-persona.json"),
                    "--resolved-evidence",
                    str(evidence_path),
                    "--governance-constraints",
                    str(governance_path),
                    "--unresolved-evidence-ref",
                    "linear:deal:southern-abrasives.public-announcement-permission",
                    "--unresolved-evidence-ref",
                    "linear:deal:southern-abrasives.delivery-handoff",
                ]
            )
            self.assertEqual("review_packet.linear.southern-abrasives-won", review["id"])
            self.assertEqual(
                ["review_packet.linear.southern-abrasives-won"],
                stores.review_packets.list_ids(),
            )

            commit = self._run_cli(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "commit",
                    str(
                        ROOT
                        / "examples"
                        / "linear-southern-abrasives-won-model-proposal-output.json"
                    ),
                    "--created-at",
                    "2026-04-28T16:07:00Z",
                    "--evidence-ref",
                    "linear:deal:southern-abrasives",
                    "--evidence-ref",
                    "linear:event:southern-abrasives-stage-won-2026-04-28",
                ]
            )
            self.assertEqual("accepted", commit["status"])
            self.assertEqual(
                "won",
                stores.state_objects.read("state.sampleco.deal.southern-abrasives")["status"],
            )

            routes_path = self._write_json(state_root / "routes.json", self._routes())
            recent = self._run_cli(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "index-recent",
                    "source.linear.southern-abrasives-won",
                    "commit.linear.southern-abrasives-won",
                    "--created-at",
                    "2026-04-28T16:07:30Z",
                    "--summary",
                    "Southern Abrasives moved from proposal to won.",
                    "--routes",
                    str(routes_path),
                    "--opportunity-class-hint",
                    "operational_handoff",
                    "--opportunity-class-hint",
                    "marketing_opportunity",
                    "--watermark-ref",
                    "state.sampleco.deal.southern-abrasives@journal.sampleco.deal.southern-abrasives.won",
                    "--watermark-ref",
                    "governance.external-copy-approval",
                    "--stale-after",
                    "2026-04-29T16:07:30Z",
                    "--requires-refresh-before-external-action",
                ]
            )
            self.assertEqual("recent.linear.southern-abrasives-won", recent["id"])

            maya_package = self._run_cli(
                [
                    "--state-root",
                    directory,
                    "build-package",
                    str(ROOT / "examples" / "maya-persona.json"),
                    "context.maya.recent-runtime",
                    "--created-at",
                    "2026-04-28T16:08:00Z",
                    "--review-goal",
                    "Review Maya-relevant recent changes.",
                    "--valid-until",
                    "2026-04-29T16:08:00Z",
                ]
            )
            alex_package = self._run_cli(
                [
                    "--state-root",
                    directory,
                    "build-package",
                    str(ROOT / "examples" / "alex-persona.json"),
                    "context.alex.recent-runtime",
                    "--created-at",
                    "2026-04-28T16:08:00Z",
                    "--review-goal",
                    "Review Alex-relevant recent changes.",
                    "--valid-until",
                    "2026-04-29T16:08:00Z",
                ]
            )

            self.assertTrue(
                maya_package["freshness"]["requires_refresh_before_external_action"]
            )
            self.assertEqual(
                "secondary",
                maya_package["recent_change_context"]["entries"][0]["persona_route"][
                    "relevance_tier"
                ],
            )
            self.assertEqual(
                "primary",
                alex_package["recent_change_context"]["entries"][0]["persona_route"][
                    "relevance_tier"
                ],
            )

    def _run_cli(self, args):
        output = StringIO()
        code = cli.main(args, stdout=output)
        self.assertEqual(0, code, output.getvalue())
        return json.loads(output.getvalue())

    def _seed_runtime(self, root: Path) -> StateStoreBundle:
        stores = StateStoreBundle(root)
        for example in (
            "southern-abrasives-deal-state.json",
            "sample-personal-operating-picture.json",
            "marketing-operating-picture.json",
        ):
            stores.state_objects.create(load_json(ROOT / "examples" / example))
        return stores

    def _write_json(self, path: Path, payload):
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        return path

    def _routes(self):
        return [
            {
                "persona_ref": "persona.alex",
                "relevance_tier": "primary",
                "routing_reason": "Won deal creates operational handoff.",
                "included": True,
                "opportunity_class_hints": ["operational_handoff"],
            },
            {
                "persona_ref": "persona.maya",
                "relevance_tier": "secondary",
                "routing_reason": "Won deal may become a marketing proof point.",
                "included": True,
                "opportunity_class_hints": ["marketing_opportunity"],
            },
        ]


if __name__ == "__main__":
    unittest.main()
