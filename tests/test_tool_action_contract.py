from __future__ import annotations

import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from state_system.contracts import load_json, validate_all_examples


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "examples" / "tool-actions" / "tool-action-core-source-tools.json"


class ToolActionContractTests(unittest.TestCase):
    def test_tool_action_registry_example_validates(self):
        schema = load_json(ROOT / "schemas" / "tool-action-contract.schema.json")
        registry = load_json(REGISTRY)
        errors = sorted(Draft202012Validator(schema).iter_errors(registry), key=str)

        self.assertEqual([], [error.message for error in errors])

    def test_validate_all_examples_includes_tool_action_registry(self):
        results = validate_all_examples(ROOT)
        tool_results = [
            result
            for result in results
            if "tool-actions" in result.path.parts and result.path.suffix == ".json"
        ]

        self.assertEqual(["tool-action-core-source-tools.json"], [result.path.name for result in tool_results])
        self.assertEqual([], [result for result in tool_results if not result.ok])

    def test_spotify_historical_cache_maps_to_runtime_postgres_tool(self):
        actions = _actions_by_tool_ref(load_json(REGISTRY))
        spotify = actions["tool.spotify.read"]

        historical = _adapter(spotify, "historical_cache")
        self.assertEqual("tool.postgres.read_spotify_history", historical["runtime_tool_ref"])
        self.assertIn("tool.postgres.read_spotify_history", historical["backing_tool_refs"])
        self.assertEqual("read_only", spotify["effect_type"])
        self.assertEqual("cache_latest_event_at", spotify["output_shape"]["required_fields"][0])

    def test_relationship_subject_note_write_is_correction_not_external_side_effect(self):
        actions = _actions_by_tool_ref(load_json(REGISTRY))
        record = actions["tool.relationship_substrate.record_subject_note"]

        self.assertEqual("source_owned_correction_write", record["effect_type"])
        self.assertEqual("audit_required", record["audit_policy"]["level"])
        self.assertFalse(record["approval_policy"]["requires_external_action_approval"])
        self.assertIn("subject_type", record["params_schema"]["required_fields"])

    def test_relationship_search_has_history_backed_fallback(self):
        actions = _actions_by_tool_ref(load_json(REGISTRY))
        search = actions["tool.relationship_substrate.search_small_consulting_firm_contacts"]

        self.assertIn(
            "tool.relationship_substrate.search_history_backed_people",
            search["backing_tool_refs"],
        )
        self.assertIn("actual_employee_count", search["params_schema"]["optional_fields"])
        self.assertIn("subject_note_context", search["output_shape"]["optional_fields"])

    def test_beeper_messaging_search_has_private_message_boundaries(self):
        actions = _actions_by_tool_ref(load_json(REGISTRY))
        search = actions["tool.beeper.search"]

        self.assertEqual("source_module.beeper_messaging", search["source_module_ref"])
        self.assertEqual("read_only", search["effect_type"])
        self.assertEqual({"local_sync", "live_api", "export"}, set(search["module_modes"]))
        self.assertIn("include_message_excerpt", search["params_schema"]["optional_fields"])
        self.assertIn("tool.sqlite.read", search["backing_tool_refs"])
        self.assertTrue(search["evidence_ref_policy"]["requires_evidence_refs"])

    def test_route_contract_tools_have_tool_action_contracts(self):
        action_tool_refs = set(_actions_by_tool_ref(load_json(REGISTRY)))
        routes = load_json(
            ROOT / "examples" / "question-routes" / "question-route-core-agent-routes.json"
        )
        route_tools = {
            tool_ref
            for route in routes["routes"]
            for tool_ref in (
                route.get("required_tools", [])
                + route.get("optional_tools", [])
                + route.get("fallback_policy", {}).get("fallback_tool_refs", [])
            )
        }

        self.assertLessEqual(route_tools, action_tool_refs)


def _actions_by_tool_ref(registry: dict) -> dict[str, dict]:
    return {action["tool_ref"]: action for action in registry["actions"]}


def _adapter(action: dict, module_mode: str) -> dict:
    for adapter in action["deployment_adapters"]:
        if adapter["module_mode"] == module_mode:
            return adapter
    raise AssertionError(f"{module_mode} adapter not found")


if __name__ == "__main__":
    unittest.main()
