from __future__ import annotations

import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from state_system.contracts import load_json, validate_all_examples


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "examples" / "question-routes" / "question-route-core-agent-routes.json"


class QuestionRouteContractTests(unittest.TestCase):
    def test_question_route_registry_example_validates(self):
        schema = load_json(ROOT / "schemas" / "question-route-contract.schema.json")
        registry = load_json(REGISTRY)
        errors = sorted(Draft202012Validator(schema).iter_errors(registry), key=str)

        self.assertEqual([], [error.message for error in errors])

    def test_validate_all_examples_includes_question_route_registry(self):
        results = validate_all_examples(ROOT)
        route_results = [
            result
            for result in results
            if "question-routes" in result.path.parts and result.path.suffix == ".json"
        ]

        self.assertEqual(["question-route-core-agent-routes.json"], [result.path.name for result in route_results])
        self.assertEqual([], [result for result in route_results if not result.ok])

    def test_personal_relationship_route_structures_no_calendar_only_rule(self):
        routes = _routes_by_id(load_json(REGISTRY))
        route = routes["question_route.personal.relationship_follow_up_triage"]

        self.assertIn("connector.personal.relationship_substrate", route["required_source_coverage"][0]["connector_refs"])
        self.assertIn("tool.relationship_substrate.list_subject_notes", route["required_tools"])
        self.assertIn("connector.personal.sampleco_state_system", route["source_order"])
        self.assertIn("tool.paia.workboard.read", route["optional_tools"])
        self.assertIn("calendar", route["optional_external_context_tools"])
        self.assertEqual("calendar_is_schedule_context_not_relationship_evidence", route["fallback_policy"]["external_context_rule"])
        self.assertTrue(route["answer_contract"]["requires_source_freshness_summary"])
        self.assertEqual([], route["gap_behavior"]["relevant_gap_refs"])

    def test_sampleco_federated_relationship_route_preserves_no_materialization_boundary(self):
        routes = _routes_by_id(load_json(REGISTRY))
        route = routes["question_route.sampleco.federated_relationship_index"]

        self.assertEqual("federated_query", route["module_modes"][0]["mode"])
        self.assertFalse(route["federated_query"]["local_materialization"])
        self.assertEqual(
            "state_instance.sample_personal",
            route["federated_query"]["source_instance_ref"],
        )
        self.assertIn(
            "subject_note_context_demote_explain_not_hide",
            route["answer_contract"]["subject_note_policy"],
        )
        self.assertIn("gap.state_instance.sampleco.connector.sampleco.linear.freshness_failed", route["gap_behavior"]["relevant_gap_refs"])

    def test_small_consulting_route_keeps_workboard_and_sampleco_context_optional(self):
        routes = _routes_by_id(load_json(REGISTRY))
        route = routes["question_route.personal.small_consulting_firm_contacts"]

        self.assertIn("connector.personal.sampleco_state_system", route["source_order"])
        self.assertIn("tool.paia.workboard.read", route["optional_tools"])
        self.assertIn("tool.state_system.instance_read", route["optional_tools"])


def _routes_by_id(registry: dict) -> dict[str, dict]:
    return {route["route_id"]: route for route in registry["routes"]}


if __name__ == "__main__":
    unittest.main()
