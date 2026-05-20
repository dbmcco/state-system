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

    def test_personal_pack_declares_garmin_connect_and_spotify_sources(self):
        pack_path = ROOT / "examples/instance-capability/instance-braydon-personal.json"
        self.assertTrue(pack_path.exists())
        pack = _load_json(pack_path)

        connector_types = {
            connector["connector_type"] for connector in pack["source_connectors"]
        }
        self.assertIn("garmin_connect", connector_types)
        self.assertIn("spotify", connector_types)
        self.assertIn("garmin-connect:account:braydon", pack["raw_corpus"]["source_refs"])
        self.assertIn("spotify:account:braydon", pack["raw_corpus"]["source_refs"])
        self.assertIn(
            "index.personal.garmin_connect.activity",
            pack["evidence_index"]["index_refs"],
        )
        self.assertIn(
            "index.personal.spotify.listening",
            pack["evidence_index"]["index_refs"],
        )
        self.assertIn(
            "action_surface.personal.read_garmin_connect",
            pack["action_surface"]["action_refs"],
        )
        self.assertIn(
            "action_surface.personal.read_spotify",
            pack["action_surface"]["action_refs"],
        )

        garmin_index = _index_manifest(
            pack,
            "index.personal.garmin_connect.activity",
        )
        spotify_index = _index_manifest(pack, "index.personal.spotify.listening")
        self.assertEqual("declared", garmin_index["status"])
        self.assertEqual("declared", spotify_index["status"])
        self.assertEqual("garmin_postgres", garmin_index["backend"])
        self.assertEqual(
            "assistant_postgres_spotify_history",
            spotify_index["backend"],
        )
        self.assertEqual(["connector.personal.garmin_connect"], garmin_index["connector_refs"])
        self.assertEqual(["connector.personal.spotify"], spotify_index["connector_refs"])

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
        self.assertEqual(
            "tool.relationship_substrate.operating_picture",
            relationship_index["query_surface"]["tool_ref"],
        )

    def test_personal_relationship_substrate_has_tool_binding(self):
        pack_path = ROOT / "examples/instance-capability/instance-braydon-personal.json"
        self.assertTrue(pack_path.exists())
        pack = _load_json(pack_path)
        binding = _binding(pack, "tool_binding.personal.relationship_substrate.read")

        self.assertEqual(
            "capability.personal.relationship_substrate.read",
            binding["capability_ref"],
        )
        self.assertEqual(
            "tool.relationship_substrate.operating_picture",
            binding["tool_ref"],
        )
        self.assertEqual(
            "action_surface.personal.read_relationship_substrate",
            binding["action_ref"],
        )
        self.assertEqual(
            ["connector.personal.relationship_substrate"],
            binding["connector_refs"],
        )
        self.assertFalse(binding["proves_live_access"])
        self.assertFalse(binding["authorizes_execution"])

    def test_personal_relationship_substrate_has_small_consulting_search_binding(self):
        pack_path = ROOT / "examples/instance-capability/instance-braydon-personal.json"
        self.assertTrue(pack_path.exists())
        pack = _load_json(pack_path)
        binding = _binding(
            pack,
            "tool_binding.personal.relationship_substrate.small_consulting_firm_search",
        )

        self.assertIn(
            "action_surface.personal.search_small_consulting_firm_contacts",
            pack["action_surface"]["action_refs"],
        )
        self.assertEqual(
            "capability.personal.relationship_substrate.search_small_consulting_firm_contacts",
            binding["capability_ref"],
        )
        self.assertEqual(
            "tool.relationship_substrate.search_small_consulting_firm_contacts",
            binding["tool_ref"],
        )
        self.assertEqual(
            "action_surface.personal.search_small_consulting_firm_contacts",
            binding["action_ref"],
        )
        self.assertEqual(
            ["connector.personal.relationship_substrate"],
            binding["connector_refs"],
        )
        self.assertFalse(binding["proves_live_access"])
        self.assertFalse(binding["authorizes_execution"])

    def test_personal_relationship_substrate_has_subject_note_bindings(self):
        pack_path = ROOT / "examples/instance-capability/instance-braydon-personal.json"
        self.assertTrue(pack_path.exists())
        pack = _load_json(pack_path)
        action_refs = pack["action_surface"]["action_refs"]

        self.assertIn(
            "action_surface.personal.read_relationship_subject_notes",
            action_refs,
        )
        self.assertIn(
            "action_surface.personal.record_relationship_subject_note",
            action_refs,
        )

        list_binding = _binding(
            pack,
            "tool_binding.personal.relationship_substrate.list_subject_notes",
        )
        self.assertEqual(
            "capability.personal.relationship_substrate.list_subject_notes",
            list_binding["capability_ref"],
        )
        self.assertEqual(
            "tool.relationship_substrate.list_subject_notes",
            list_binding["tool_ref"],
        )
        self.assertFalse(list_binding["authorizes_execution"])

        record_binding = _binding(
            pack,
            "tool_binding.personal.relationship_substrate.record_subject_note",
        )
        self.assertEqual(
            "capability.personal.relationship_substrate.record_subject_note",
            record_binding["capability_ref"],
        )
        self.assertEqual(
            "tool.relationship_substrate.record_subject_note",
            record_binding["tool_ref"],
        )
        self.assertEqual(
            "action_surface.personal.record_relationship_subject_note",
            record_binding["action_ref"],
        )
        self.assertEqual(
            ["connector.personal.relationship_substrate"],
            record_binding["connector_refs"],
        )
        self.assertFalse(record_binding["proves_live_access"])
        self.assertFalse(record_binding["authorizes_execution"])

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


def _binding(pack: dict, binding_id: str):
    matches = [
        binding
        for binding in pack["tool_capability_bindings"]
        if binding["id"] == binding_id
    ]
    if not matches:
        raise AssertionError(f"{binding_id} not found")
    return matches[0]


def _load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


if __name__ == "__main__":
    unittest.main()
