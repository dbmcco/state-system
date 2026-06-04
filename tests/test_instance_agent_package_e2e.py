from __future__ import annotations

from io import StringIO
import json
from pathlib import Path
import unittest

from state_system import cli
from state_system.contracts import load_json, validate_schema


ROOT = Path(__file__).resolve().parents[1]
BSTATE_ROOT = Path("/tmp/personal-state")
ACME_ROOT = Path("/tmp/sampleco-state-system")


@unittest.skipUnless(
    BSTATE_ROOT.exists() and ACME_ROOT.exists(),
    "deployed personal state and SampleCo state roots are required for this pressure test",
)
class InstanceAgentPackageE2ETests(unittest.TestCase):
    def test_builds_renders_and_validates_bstate_and_sampleco_packages(self):
        schema = load_json(ROOT / "schemas" / "instance-agent-package.schema.json")

        bstate_package = self._build_package(
            state_root=BSTATE_ROOT,
            instance_ref="state_instance.sample_personal",
            agent_ref="agent.samantha",
            persona_ref="persona.samantha",
            package_id="instance_agent_package.e2e.sample_personal.samantha",
            review_goal=(
                "E2E pressure test: review personal state readiness, freshness, "
                "federated SampleCo metadata, and gaps."
            ),
        )
        sampleco_package = self._build_package(
            state_root=ACME_ROOT,
            instance_ref="state_instance.sampleco",
            agent_ref="agent.caroline",
            persona_ref="persona.caroline",
            package_id="instance_agent_package.e2e.sampleco.caroline",
            review_goal=(
                "E2E pressure test: review SampleCo readiness, freshness, interpreted "
                "state, and gaps."
            ),
        )

        self.assertEqual([], validate_schema(bstate_package, schema))
        self.assertEqual([], validate_schema(sampleco_package, schema))
        self.assertNotIn(
            "gap.state_instance.sample_personal.connector.personal.garmin_connect.access_planned",
            bstate_package["source_context"]["source_gap_refs"],
        )
        self.assertNotIn(
            "gap.state_instance.sample_personal.connector.personal.spotify.access_planned",
            bstate_package["source_context"]["source_gap_refs"],
        )
        self.assertNotIn(
            "gap.state_instance.sample_personal.connector.personal.spotify.index_planned",
            bstate_package["source_context"]["source_gap_refs"],
        )
        self.assertIn(
            "gap.state_instance.sample_personal.connector.personal.spotify.freshness_stale",
            bstate_package["source_context"]["source_gap_refs"],
        )
        self.assertIn(
            "state_instance.sampleco",
            bstate_package["evidence_context"]["federated_instance_refs"],
        )
        self.assertEqual(
            {
                "gap.state_instance.sampleco.connector.sampleco.transcripts.processed.access_planned",
                "gap.state_instance.sampleco.connector.sampleco.transcripts.processed.freshness_unknown",
                "gap.state_instance.sampleco.connector.sampleco.transcripts.processed.index_planned",
                "gap.state_instance.sampleco.connector.sampleco.transcripts.raw.access_planned",
                "gap.state_instance.sampleco.connector.sampleco.transcripts.raw.index_planned",
            },
            set(sampleco_package["source_context"]["source_gap_refs"]),
        )
        self.assertNotIn(
            "gap.state_instance.sampleco.connector.sampleco.linear.freshness_failed",
            sampleco_package["source_context"]["source_gap_refs"],
        )
        self.assertNotIn(
            "gap.state_instance.sampleco.connector.sampleco.github.freshness_failed",
            sampleco_package["source_context"]["source_gap_refs"],
        )
        self.assertNotIn("garmin", json.dumps(sampleco_package).lower())
        self.assertFalse(bstate_package["invariant"]["agent_package_authorizes_execution"])
        self.assertFalse(sampleco_package["invariant"]["agent_package_authorizes_execution"])

        bstate_rendered = self._render_package(
            BSTATE_ROOT,
            "instance_agent_package.e2e.sample_personal.samantha",
        )
        sampleco_rendered = self._render_package(
            ACME_ROOT,
            "instance_agent_package.e2e.sampleco.caroline",
        )

        self.assertIn("State System Instance Agent Package", bstate_rendered)
        self.assertIn("connector.personal.garmin_connect", bstate_rendered)
        self.assertIn(
            "question_route.personal.relationship_follow_up_triage",
            bstate_rendered,
        )
        self.assertIn("Start with relationship_substrate", bstate_rendered)
        self.assertIn(
            "tool.relationship_substrate.search_small_consulting_firm_contacts",
            bstate_rendered,
        )
        self.assertIn("Federated instance: state_instance.sampleco (available)", bstate_rendered)
        self.assertIn("Do not:", bstate_rendered)
        self.assertIn("State System Instance Agent Package", sampleco_rendered)
        self.assertIn("connector.sampleco.msgvault", sampleco_rendered)
        self.assertIn("freshness=fresh", sampleco_rendered)
        self.assertIn("question_route.sampleco.federated_relationship_index", sampleco_rendered)
        self.assertIn("Local materialization: False", sampleco_rendered)
        self.assertIn("state_instance.sample_personal", sampleco_rendered)
        self.assertIn("Do not:", sampleco_rendered)

    def _build_package(
        self,
        *,
        state_root: Path,
        instance_ref: str,
        agent_ref: str,
        persona_ref: str,
        package_id: str,
        review_goal: str,
    ) -> dict:
        output = StringIO()
        code = cli.main(
            [
                "--project-root",
                str(ROOT),
                "--state-root",
                str(state_root),
                "instance-agent-package-build",
                "--instance-ref",
                instance_ref,
                "--agent-ref",
                agent_ref,
                "--persona-ref",
                persona_ref,
                "--created-at",
                "2026-05-17T17:10:00Z",
                "--package-id",
                package_id,
                "--review-goal",
                review_goal,
            ],
            stdout=output,
        )
        self.assertEqual(0, code, output.getvalue())
        return json.loads(output.getvalue())["package"]

    def _render_package(self, state_root: Path, package_id: str) -> str:
        output = StringIO()
        code = cli.main(
            [
                "--project-root",
                str(ROOT),
                "--state-root",
                str(state_root),
                "instance-agent-package-render",
                package_id,
            ],
            stdout=output,
        )
        self.assertEqual(0, code, output.getvalue())
        return output.getvalue()


if __name__ == "__main__":
    unittest.main()
