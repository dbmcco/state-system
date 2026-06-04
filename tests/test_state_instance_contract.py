from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]


class StateInstanceContractTests(unittest.TestCase):
    def test_sampleco_and_personal_state_instances_are_schema_valid(self):
        schema_path = ROOT / "schemas/state-instance.schema.json"
        self.assertTrue(schema_path.exists())
        schema = _load_json(schema_path)
        validator = Draft202012Validator(schema)

        for filename in (
            "state-instance-sampleco.json",
            "state-instance-sample-personal.json",
        ):
            with self.subTest(filename=filename):
                instance_path = ROOT / "examples/instances" / filename
                self.assertTrue(instance_path.exists())
                instance = _load_json(instance_path)
                errors = sorted(validator.iter_errors(instance), key=str)
                self.assertEqual([], [error.message for error in errors])

    def test_personal_instance_uses_entity_not_company_ref(self):
        instance_path = ROOT / "examples/instances/state-instance-sample-personal.json"
        self.assertTrue(instance_path.exists())
        instance = _load_json(instance_path)

        self.assertEqual("state_instance.sample_personal", instance["instance_ref"])
        self.assertEqual("entity.example_person", instance["primary_entity_ref"])
        self.assertEqual("person", instance["entity_kind"])
        self.assertNotIn("company_ref", instance)


def _load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


if __name__ == "__main__":
    unittest.main()
