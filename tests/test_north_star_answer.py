from __future__ import annotations

from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.contracts import load_json, validate_schema
from state_system.north_star_answer import build_north_star_answer


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PATH = (
    ROOT
    / "examples"
    / "instance-agent-package"
    / "instance-agent-package-acme-ops-samantha.json"
)
ACME_PACKAGE_PATH = (
    ROOT
    / "examples"
    / "instance-agent-package"
    / "instance-agent-package-acme-caroline.json"
)
SCHEMA_PATH = ROOT / "schemas" / "north-star-answer.schema.json"


class NorthStarAnswerTests(unittest.TestCase):
    def test_answer_summarizes_current_state_evidence_gaps_and_next_actions(self):
        package = load_json(PACKAGE_PATH)

        report = build_north_star_answer(
            {package["id"]: package},
            query="What is the current state of this instance?",
        )

        self.assertEqual("state_system_north_star_answer", report["id"])
        self.assertEqual("usable_with_gaps", report["answerability"]["status"])
        self.assertEqual(
            ["instance_agent_package.acme_ops.samantha"],
            report["package_refs"],
        )
        self.assertEqual(
            "state_instance.acme_ops",
            report["current_state"][0]["instance_ref"],
        )
        self.assertIn(
            "gap.state_instance.acme_ops.connector.personal.spotify.freshness_stale",
            report["uncertainty"]["source_gap_refs"],
        )
        self.assertIn(
            "spotify:assistant_postgres:spotify_listening_records:3091",
            report["evidence"]["evidence_refs"],
        )
        self.assertTrue(report["next_actions"]["requires_refresh_before_external_action"])
        self.assertFalse(report["invariant"]["ingests_raw_source_data"])
        self.assertFalse(report["invariant"]["authorizes_execution"])
        self.assertEqual([], validate_schema(report, load_json(SCHEMA_PATH)))

    def test_multi_package_pressure_answer_validates_and_rolls_up_federation(self):
        personal = load_json(PACKAGE_PATH)
        acme_inst = load_json(ACME_PACKAGE_PATH)

        report = build_north_star_answer(
            {
                personal["id"]: personal,
                acme_inst["id"]: acme_inst,
            },
            query="What is the current cross-instance operating state?",
        )

        self.assertEqual([], validate_schema(report, load_json(SCHEMA_PATH)))
        self.assertEqual(
            [
                "instance_agent_package.acme.caroline",
                "instance_agent_package.acme_ops.samantha",
            ],
            report["package_refs"],
        )
        self.assertEqual(2, len(report["current_state"]))
        self.assertIn(
            "state_instance.acme_ops",
            report["broader_effects"]["federated_instance_refs"],
        )
        self.assertIn(
            "state_instance.acme",
            report["broader_effects"]["federated_instance_refs"],
        )
        self.assertEqual("usable_with_gaps", report["answerability"]["status"])

    def test_answer_preserves_federation_boundaries_without_materialization(self):
        package = load_json(PACKAGE_PATH)
        package["federation_packs"] = [
            {
                "id": "instance_federation_pack.personal_to_acme_state",
                "federation_mode": "instance_read",
                "remote_instance_refs": ["state_instance.acme"],
                "materialization_policy": {"local_materialization": False},
            }
        ]
        package["question_routes"] = [
            {
                "id": "question_route.personal.acme_state",
                "intent": "Answer work-state questions through the LFW instance.",
                "source_order": ["connector.personal.acme_state_system"],
                "required_actions": ["route_to_acme_state"],
                "answer_contract": ["cite_acme_package_evidence"],
                "query_route": {
                    "source_instance_ref": "state_instance.acme",
                    "query_surface_ref": "state_system_interpreted_index_read_model",
                    "local_materialization": False,
                    "boundaries": ["do_not_copy_raw_acme_corpus"],
                },
            }
        ]

        report = build_north_star_answer({package["id"]: package})

        self.assertEqual(
            ["state_instance.acme"],
            report["broader_effects"]["federated_instance_refs"],
        )
        self.assertEqual(
            [False],
            [
                route["local_materialization"]
                for route in report["broader_effects"]["federated_query_routes"]
            ],
        )
        self.assertTrue(report["invariant"]["federated_raw_materialization_forbidden"])

    def test_cli_writes_north_star_answer_report(self):
        with TemporaryDirectory() as output_dir:
            stdout = StringIO()
            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "north-star-answer",
                    "--query",
                    "What changed recently?",
                    "--package",
                    f"personal={PACKAGE_PATH}",
                    "--output-dir",
                    output_dir,
                ],
                stdout=stdout,
            )

            self.assertEqual(0, code, stdout.getvalue())
            payload = json.loads(stdout.getvalue())
            self.assertTrue(payload["schema_valid"])
            report_path = Path(payload["answer_path"])
            self.assertEqual("north-star-answer.json", report_path.name)
            report = load_json(report_path)
            self.assertEqual("What changed recently?", report["query"])
            self.assertEqual("state_system_north_star_answer", report["id"])
            self.assertEqual([], validate_schema(report, load_json(SCHEMA_PATH)))

    def test_cli_renders_checked_north_star_answer(self):
        personal = load_json(PACKAGE_PATH)
        acme_inst = load_json(ACME_PACKAGE_PATH)
        report = build_north_star_answer(
            {
                personal["id"]: personal,
                acme_inst["id"]: acme_inst,
            },
            query="What is the current cross-instance operating state?",
        )

        with TemporaryDirectory() as output_dir:
            answer_path = Path(output_dir) / "north-star-answer.json"
            render_path = Path(output_dir) / "north-star-answer.txt"
            answer_path.write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            stdout = StringIO()

            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "north-star-answer-render",
                    str(answer_path),
                    "--check",
                    "--output-path",
                    str(render_path),
                ],
                stdout=stdout,
            )

            self.assertEqual(0, code, stdout.getvalue())
            payload = json.loads(stdout.getvalue())
            self.assertTrue(payload["schema_valid"])
            self.assertTrue(payload["render_valid"])
            rendered = render_path.read_text(encoding="utf-8")
            self.assertIn(
                "Query: What is the current cross-instance operating state?",
                rendered,
            )
            self.assertIn("Answerability: usable_with_gaps", rendered)
            self.assertIn("Source gaps", rendered)
            self.assertIn(
                "gap.state_instance.acme_ops.connector.personal.spotify.freshness_stale",
                rendered,
            )
            self.assertIn("Federated query routes", rendered)
            self.assertIn("Local materialization: false", rendered)


if __name__ == "__main__":
    unittest.main()
