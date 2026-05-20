from __future__ import annotations

from io import StringIO
import json
from pathlib import Path
import unittest

from state_system import cli
from state_system.contracts import load_json, validate_schema


ROOT = Path(__file__).resolve().parents[1]
BSTATE_ROOT = Path("/Users/braydon/projects/personal/b-state")
LFW_ROOT = Path("/Users/braydon/projects/work/lfw/state-system")


@unittest.skipUnless(
    BSTATE_ROOT.exists() and LFW_ROOT.exists(),
    "deployed b-state and LFW state roots are required for this pressure test",
)
class InstanceAgentPackageE2ETests(unittest.TestCase):
    def test_builds_renders_and_validates_bstate_and_lfw_packages(self):
        schema = load_json(ROOT / "schemas" / "instance-agent-package.schema.json")

        bstate_package = self._build_package(
            state_root=BSTATE_ROOT,
            instance_ref="state_instance.braydon_personal",
            agent_ref="agent.samantha",
            persona_ref="persona.samantha",
            package_id="instance_agent_package.e2e.braydon_personal.samantha",
            review_goal=(
                "E2E pressure test: review b-state readiness, freshness, "
                "federated LFW metadata, and gaps."
            ),
        )
        lfw_package = self._build_package(
            state_root=LFW_ROOT,
            instance_ref="state_instance.lfw",
            agent_ref="agent.caroline",
            persona_ref="persona.caroline",
            package_id="instance_agent_package.e2e.lfw.caroline",
            review_goal=(
                "E2E pressure test: review LFW readiness, freshness, interpreted "
                "state, and gaps."
            ),
        )

        self.assertEqual([], validate_schema(bstate_package, schema))
        self.assertEqual([], validate_schema(lfw_package, schema))
        self.assertNotIn(
            "gap.state_instance.braydon_personal.connector.personal.garmin_connect.access_planned",
            bstate_package["source_context"]["source_gap_refs"],
        )
        self.assertNotIn(
            "gap.state_instance.braydon_personal.connector.personal.spotify.access_planned",
            bstate_package["source_context"]["source_gap_refs"],
        )
        self.assertNotIn(
            "gap.state_instance.braydon_personal.connector.personal.spotify.index_planned",
            bstate_package["source_context"]["source_gap_refs"],
        )
        self.assertIn(
            "gap.state_instance.braydon_personal.connector.personal.spotify.freshness_stale",
            bstate_package["source_context"]["source_gap_refs"],
        )
        self.assertIn(
            "state_instance.lfw",
            bstate_package["evidence_context"]["federated_instance_refs"],
        )
        self.assertEqual(
            {
                "gap.state_instance.lfw.connector.lfw.transcripts.processed.access_planned",
                "gap.state_instance.lfw.connector.lfw.transcripts.processed.freshness_unknown",
                "gap.state_instance.lfw.connector.lfw.transcripts.processed.index_planned",
                "gap.state_instance.lfw.connector.lfw.transcripts.raw.access_planned",
                "gap.state_instance.lfw.connector.lfw.transcripts.raw.index_planned",
            },
            set(lfw_package["source_context"]["source_gap_refs"]),
        )
        self.assertNotIn(
            "gap.state_instance.lfw.connector.lfw.linear.freshness_failed",
            lfw_package["source_context"]["source_gap_refs"],
        )
        self.assertNotIn(
            "gap.state_instance.lfw.connector.lfw.github.freshness_failed",
            lfw_package["source_context"]["source_gap_refs"],
        )
        self.assertNotIn("garmin", json.dumps(lfw_package).lower())
        self.assertFalse(bstate_package["invariant"]["agent_package_authorizes_execution"])
        self.assertFalse(lfw_package["invariant"]["agent_package_authorizes_execution"])

        bstate_rendered = self._render_package(
            BSTATE_ROOT,
            "instance_agent_package.e2e.braydon_personal.samantha",
        )
        lfw_rendered = self._render_package(
            LFW_ROOT,
            "instance_agent_package.e2e.lfw.caroline",
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
        self.assertIn("Federated instance: state_instance.lfw (available)", bstate_rendered)
        self.assertIn("Do not:", bstate_rendered)
        self.assertIn("State System Instance Agent Package", lfw_rendered)
        self.assertIn("connector.lfw.msgvault", lfw_rendered)
        self.assertIn("freshness=fresh", lfw_rendered)
        self.assertIn("question_route.lfw.federated_relationship_index", lfw_rendered)
        self.assertIn("Local materialization: False", lfw_rendered)
        self.assertIn("state_instance.braydon_personal", lfw_rendered)
        self.assertIn("Do not:", lfw_rendered)

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
