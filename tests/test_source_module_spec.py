from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from state_system.contracts import load_json, validate_all_examples


ROOT = Path(__file__).resolve().parents[1]
MODULE_REGISTRY = ROOT / "examples" / "source-modules" / "source-module-core-connectors.json"


class SourceModuleSpecTests(unittest.TestCase):
    def test_source_module_registry_example_validates(self):
        schema = load_json(ROOT / "schemas" / "source-module-spec.schema.json")
        registry = load_json(MODULE_REGISTRY)
        errors = sorted(Draft202012Validator(schema).iter_errors(registry), key=str)

        self.assertEqual([], [error.message for error in errors])

    def test_validate_all_examples_includes_source_module_registry(self):
        results = validate_all_examples(ROOT)
        module_results = [
            result
            for result in results
            if "source-modules" in result.path.parts and result.path.suffix == ".json"
        ]

        self.assertEqual(["source-module-core-connectors.json"], [result.path.name for result in module_results])
        self.assertEqual([], [result for result in module_results if not result.ok])

    def test_current_capability_pack_connector_types_have_module_specs(self):
        registry = load_json(MODULE_REGISTRY)
        module_types = {module["connector_type"] for module in registry["modules"]}
        connector_types: set[str] = set()

        for directory in ("instance-capability", "company-capability"):
            for path in sorted((ROOT / "examples" / directory).glob("*.json")):
                pack = load_json(path)
                connector_types.update(
                    connector["connector_type"]
                    for connector in pack.get("source_connectors", [])
                )

        self.assertLessEqual(connector_types, module_types)

    def test_capability_pack_schemas_do_not_hardcode_connector_type_enums(self):
        for schema_name in (
            "instance-capability-pack.schema.json",
            "company-capability-pack.schema.json",
        ):
            with self.subTest(schema_name=schema_name):
                schema = load_json(ROOT / "schemas" / schema_name)
                connector_type = schema["$defs"]["source_connector"]["properties"]["connector_type"]
                self.assertEqual("string", connector_type["type"])
                self.assertNotIn("enum", connector_type)

    def test_key_personal_modules_declare_freshness_preflight_tools_and_governance(self):
        registry = load_json(MODULE_REGISTRY)
        modules = {
            module["connector_type"]: module
            for module in registry["modules"]
        }

        for connector_type in (
            "spotify",
            "garmin_connect",
            "relationship_substrate",
            "paia_memory",
            "blog",
            "beeper_messaging",
        ):
            with self.subTest(connector_type=connector_type):
                module = modules[connector_type]
                self.assertTrue(module["preflight_contract"]["required"])
                self.assertTrue(module["freshness_contract"]["required"])
                self.assertTrue(module["index_contract"]["record_kinds"])
                self.assertTrue(module["tool_contract"]["tool_refs"])
                self.assertTrue(module["governance_defaults"]["allowed_uses"])
                self.assertTrue(module["invariant"]["module_declares_interface_not_live_access"])
                self.assertTrue(module["invariant"]["private_data_not_required"])

    def test_key_personal_modules_capture_live_runtime_modes_and_gap_behavior(self):
        registry = load_json(MODULE_REGISTRY)
        modules = {
            module["connector_type"]: module
            for module in registry["modules"]
        }

        spotify_modes = {mode["mode"] for mode in modules["spotify"]["module_modes"]}
        self.assertEqual({"historical_cache", "live_api"}, spotify_modes)
        self.assertIn("credential_gap", modules["spotify"]["gap_behavior"])
        self.assertTrue(modules["spotify"]["output_policy"]["requires_evidence_refs"])

        garmin_modes = {mode["mode"] for mode in modules["garmin_connect"]["module_modes"]}
        self.assertIn("local_sync", garmin_modes)
        self.assertTrue(modules["garmin_connect"]["output_policy"]["summary_only"])

        relationship = modules["relationship_substrate"]
        correction_effects = {
            surface["effect_type"]
            for surface in relationship["correction_surfaces"]
        }
        self.assertIn("source_owned_correction_write", correction_effects)
        self.assertIn("hidden filters", relationship["output_policy"]["answer_behavior"])
        self.assertIn(
            "tool.relationship_substrate.search_history_backed_people",
            relationship["read_surfaces"],
        )

        state_system_modes = {
            mode["mode"]
            for mode in modules["state_system_instance"]["module_modes"]
        }
        self.assertIn("federated_query", state_system_modes)
        self.assertIn(
            "evidence_card",
            modules["state_system_instance"]["index_contract"]["record_kinds"],
        )

        paia_memory = modules["paia_memory"]
        self.assertIn(
            "conversation_turn",
            paia_memory["index_contract"]["record_kinds"],
        )
        self.assertIn("facet_history", paia_memory["index_contract"]["record_kinds"])
        self.assertIn("tool.paia_memory.retrieve_facets", paia_memory["read_surfaces"])
        paia_effects = {
            surface["effect_type"]
            for surface in paia_memory["correction_surfaces"]
        }
        self.assertIn("source_owned_correction_write", paia_effects)
        self.assertIn("raw private facets", paia_memory["output_policy"]["redaction_policy"])

        blog = modules["blog"]
        self.assertIn("local_sync", {mode["mode"] for mode in blog["module_modes"]})
        self.assertIn("blog_post", blog["index_contract"]["record_kinds"])
        self.assertIn("historical context", blog["output_policy"]["answer_behavior"])

        beeper = modules["beeper_messaging"]
        self.assertEqual(
            {"local_sync", "live_api", "export"},
            {mode["mode"] for mode in beeper["module_modes"]},
        )
        self.assertIn("message_thread", beeper["index_contract"]["record_kinds"])
        self.assertIn("tool.beeper.search", beeper["read_surfaces"])
        self.assertIn(
            "raw chat exports",
            beeper["output_policy"]["redaction_policy"],
        )


if __name__ == "__main__":
    unittest.main()
