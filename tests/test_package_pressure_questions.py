from __future__ import annotations

import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from jsonschema import Draft202012Validator

from state_system import cli
from state_system.contracts import load_json, validate_all_examples
from state_system.package_pressure import run_package_pressure


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "examples" / "pressure-questions" / "package-pressure-core-real-questions.json"


class PackagePressureQuestionTests(unittest.TestCase):
    def test_pressure_registry_example_validates(self):
        schema = load_json(ROOT / "schemas" / "package-pressure-question.schema.json")
        registry = load_json(REGISTRY)
        errors = sorted(Draft202012Validator(schema).iter_errors(registry), key=str)

        self.assertEqual([], [error.message for error in errors])

    def test_pressure_registry_targets_real_implemented_state_ids(self):
        registry = load_json(REGISTRY)
        package_ids = {case["package_id"] for case in registry["cases"]}

        self.assertEqual(
            {
                "instance_agent_package.sample_personal.samantha",
                "instance_agent_package.sampleco.caroline",
                "instance_agent_package.portfolio_co.helena",
                "instance_agent_package.researchco.ingrid.scaffold.v0",
            },
            package_ids,
        )
    def test_validate_all_examples_includes_pressure_registry(self):
        results = validate_all_examples(ROOT)
        pressure_results = [
            result
            for result in results
            if "pressure-questions" in result.path.parts
        ]

        self.assertEqual(
            ["package-pressure-core-real-questions.json"],
            [result.path.name for result in pressure_results],
        )
        self.assertEqual([], [result for result in pressure_results if not result.ok])

    def test_ready_pressure_cases_pass_against_contract_packages(self):
        report = run_package_pressure(
            load_json(REGISTRY),
            {
                "instance_agent_package.sample_personal.samantha": _sam_package(),
                "instance_agent_package.sampleco.caroline": _caroline_package(),
            },
        )

        self.assertTrue(report["ok"], report)
        self.assertEqual(8, report["case_count"])

    def test_include_planned_cases_checks_scaffolded_packages(self):
        report = run_package_pressure(
            load_json(REGISTRY),
            {
                "instance_agent_package.sample_personal.samantha": _sam_package(),
                "instance_agent_package.sampleco.caroline": _caroline_package(),
                "instance_agent_package.portfolio_co.helena": _scaffold_package("portfolio_co", "helena"),
                "instance_agent_package.researchco.ingrid.scaffold.v0": _scaffold_package(
                    "researchco",
                    "ingrid",
                    package_id="instance_agent_package.researchco.ingrid.scaffold.v0",
                ),
            },
            include_planned=True,
        )

        self.assertTrue(report["ok"], report)
        self.assertEqual(10, report["case_count"])

    def test_cli_runs_pressure_harness(self):
        with TemporaryDirectory() as directory:
            sam_path = Path(directory) / "sam.json"
            caroline_path = Path(directory) / "caroline.json"
            sam_path.write_text(json.dumps(_sam_package()), encoding="utf-8")
            caroline_path.write_text(json.dumps(_caroline_package()), encoding="utf-8")

            output = io.StringIO()
            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "package-pressure-run",
                    str(REGISTRY),
                    "--package",
                    f"instance_agent_package.sample_personal.samantha={sam_path}",
                    "--package",
                    f"instance_agent_package.sampleco.caroline={caroline_path}",
                ],
                stdout=output,
            )

        self.assertEqual(0, code, output.getvalue())
        payload = json.loads(output.getvalue())
        self.assertTrue(payload["ok"])


def _sam_package() -> dict:
    return {
        "id": "instance_agent_package.sample_personal.samantha",
        "source_context": {
            "source_gap_refs": [
                "gap.state_instance.sample_personal.connector.personal.spotify.freshness_stale"
            ],
            "source_readiness": [
                {
                    "connector_ref": "connector.personal.spotify",
                    "access_status": "passed",
                    "freshness_status": "stale",
                    "understanding_status": "usable_with_freshness_gap",
                },
                {
                    "connector_ref": "connector.personal.agent_memory.samantha",
                    "access_status": "passed",
                    "freshness_status": "fresh",
                    "understanding_status": "ready",
                },
                {
                    "connector_ref": "connector.personal.agent_memory.owner",
                    "access_status": "passed",
                    "freshness_status": "fresh",
                    "understanding_status": "ready",
                },
                {
                    "connector_ref": "connector.personal.blog",
                    "access_status": "passed",
                    "freshness_status": "fresh",
                    "understanding_status": "ready",
                },
                {
                    "connector_ref": "connector.personal.beeper.imessage",
                    "access_status": "passed",
                    "freshness_status": "unknown",
                    "understanding_status": "usable_with_freshness_gap",
                },
                {
                    "connector_ref": "connector.personal.beeper.whatsapp",
                    "access_status": "passed",
                    "freshness_status": "fresh",
                    "understanding_status": "ready",
                },
            ],
        },
        "federation_packs": [
            {
                "id": "instance_federation_pack.personal_to_sampleco_state",
                "remote_instance_refs": ["state_instance.sampleco"],
                "materialization_policy": {"local_materialization": False},
            }
        ],
        "question_routes": [
            {
                "id": "question_route.personal.messaging_context",
                "tool_refs": [
                    "tool.beeper.search",
                ],
                "tool_action_refs": [
                    "tool_action.beeper_messaging.search",
                ],
            },
            {
                "id": "question_route.personal.relationship_follow_up_triage",
                "tool_refs": [
                    "tool.relationship_substrate.operating_picture",
                    "tool.relationship_substrate.list_subject_notes",
                    "tool.agent_runtime.msgvault.search",
                    "tool.agent_memory.retrieve_summary",
                    "tool.agent_memory.retrieve_facets",
                ],
                "tool_action_refs": [
                    "tool_action.relationship_substrate.operating_picture",
                    "tool_action.relationship_substrate.list_subject_notes",
                    "tool_action.msgvault.search",
                    "tool_action.agent_memory.read",
                ],
                "required_source_coverage": [
                    {"coverage_ref": "coverage.personal.relationship_core"}
                ],
                "answer_contract_policy": {
                    "requires_evidence_refs": True,
                    "requires_source_freshness_summary": True,
                    "direct_evidence_vs_interpretation": True,
                },
            },
            {
                "id": "question_route.personal.small_consulting_firm_contacts",
                "tool_refs": [
                    "tool.relationship_substrate.search_small_consulting_firm_contacts",
                    "tool.relationship_substrate.list_subject_notes",
                ],
                "tool_action_refs": [
                    "tool_action.relationship_substrate.search_small_consulting_firm_contacts",
                    "tool_action.relationship_substrate.search_history_backed_people",
                ],
                "required_source_coverage": [
                    {"coverage_ref": "coverage.personal.relationship_search"}
                ],
                "answer_contract_policy": {
                    "requires_evidence_refs": True,
                    "requires_source_freshness_summary": True,
                    "direct_evidence_vs_interpretation": True,
                },
            },
        ],
        "open_questions": [
            "connector.personal.spotify is usable_with_freshness_gap (access=passed, freshness=stale, index=declared)."
        ],
    }


def _caroline_package() -> dict:
    source_readiness = [
        {
            "connector_ref": "connector.sampleco.linear",
            "access_status": "passed",
            "freshness_status": "fresh",
            "understanding_status": "ready",
        },
        {
            "connector_ref": "connector.sampleco.github_org",
            "access_status": "passed",
            "freshness_status": "fresh",
            "understanding_status": "ready",
        },
        {
            "connector_ref": "connector.sampleco.transcripts.raw",
            "access_status": "passed",
            "freshness_status": "fresh",
            "understanding_status": "ready",
        },
        {
            "connector_ref": "connector.sampleco.transcripts.processed",
            "access_status": "passed",
            "freshness_status": "fresh",
            "understanding_status": "ready",
        },
    ]
    return {
        "id": "instance_agent_package.sampleco.caroline",
        "source_context": {
            "source_gap_refs": [],
            "source_readiness": source_readiness,
        },
        "federation_packs": [
            {
                "id": "instance_federation_pack.sampleco_to_personal_relationship_substrate",
                "remote_instance_refs": ["state_instance.sample_personal"],
                "materialization_policy": {"local_materialization": False},
            }
        ],
        "question_routes": [
            {
                "id": "question_route.sampleco.relationship_follow_up_triage",
                "required_source_coverage": [
                    {"coverage_ref": "coverage.sampleco.company_follow_up"}
                ],
            },
            {
                "id": "question_route.sampleco.federated_relationship_index",
                "tool_action_refs": [
                    "tool_action.relationship_substrate.search_small_consulting_firm_contacts"
                ],
                "required_source_coverage": [
                    {"coverage_ref": "coverage.sampleco.federated_relationship_context"}
                ],
            },
        ],
        "open_questions": [],
    }


def _scaffold_package(slug: str, agent: str, package_id: str | None = None) -> dict:
    return {
        "id": package_id or f"instance_agent_package.{slug}.{agent}",
        "source_context": {"source_gap_refs": [], "source_readiness": []},
        "federation_packs": [
            {
                "id": "instance_federation_pack.portfolio_to_portfolio_co_researchco",
                "remote_instance_refs": [
                    "state_instance.portfolio_co",
                    "state_instance.researchco",
                ],
                "materialization_policy": {"local_materialization": False},
            }
        ],
        "question_routes": [],
        "open_questions": [f"connector.{slug}.local is declared but not ready."],
    }


if __name__ == "__main__":
    unittest.main()
