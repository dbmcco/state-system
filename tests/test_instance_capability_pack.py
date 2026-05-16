from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]


class InstanceCapabilityPackTests(unittest.TestCase):
    def test_personal_and_lfw_instance_packs_are_schema_valid(self):
        schema_path = ROOT / "schemas/instance-capability-pack.schema.json"
        self.assertTrue(schema_path.exists())
        schema = _load_json(schema_path)
        validator = Draft202012Validator(schema)

        for filename in ("instance-braydon-personal.json", "instance-lfw.json"):
            with self.subTest(filename=filename):
                pack_path = ROOT / "examples/instance-capability" / filename
                self.assertTrue(pack_path.exists())
                pack = _load_json(pack_path)
                errors = sorted(validator.iter_errors(pack), key=str)
                self.assertEqual([], [error.message for error in errors])

    def test_personal_pack_declares_workboard_agentmem_relationships_and_federated_work_instances(self):
        pack_path = ROOT / "examples/instance-capability/instance-braydon-personal.json"
        self.assertTrue(pack_path.exists())
        pack = _load_json(pack_path)

        connector_types = {
            connector["connector_type"] for connector in pack["source_connectors"]
        }
        self.assertIn("paia_workboard", connector_types)
        self.assertIn("agentmem", connector_types)
        self.assertIn("relationship_substrate", connector_types)
        self.assertIn("state_system_instance", connector_types)
        self.assertEqual("entity.braydon", pack["primary_entity_ref"])
        self.assertEqual("person", pack["entity_kind"])
        self.assertNotIn("company_ref", pack)

    def test_index_scopes_include_federated_vector_taxonomy(self):
        pack_path = ROOT / "examples/instance-capability/instance-braydon-personal.json"
        self.assertTrue(pack_path.exists())
        pack = _load_json(pack_path)
        scopes = {manifest["scope"] for manifest in pack["index_manifests"]}

        self.assertIn("raw_source_index", scopes)
        self.assertIn("memory_index", scopes)
        self.assertIn("operational_index", scopes)
        self.assertIn("interpreted_state_index", scopes)
        relationship_index = _index_manifest(
            pack,
            "index.personal.relationship_substrate.network",
        )
        self.assertEqual("relationship_index", relationship_index["scope"])

    def test_lfw_instance_uses_operational_interpreted_state_search(self):
        pack_path = ROOT / "examples/instance-capability/instance-lfw.json"
        self.assertTrue(pack_path.exists())
        pack = _load_json(pack_path)
        interpreted = _index_manifest(pack, "index.lfw.state_system.interpreted")

        self.assertEqual("state_system_interpreted_index", interpreted["backend"])
        self.assertEqual("declared", interpreted["status"])
        self.assertEqual(
            {
                "type": "state_system_runtime",
                "tool_ref": "tool.state_system.interpreted_search",
            },
            interpreted["query_surface"],
        )


def _index_manifest(pack: dict, index_ref: str):
    matches = [
        manifest for manifest in pack["index_manifests"] if manifest["index_ref"] == index_ref
    ]
    if not matches:
        raise AssertionError(f"{index_ref} not found")
    return matches[0]


def _load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


if __name__ == "__main__":
    unittest.main()
