from pathlib import Path
import unittest

from state_system.contracts import load_json, validate_all_examples, validate_schema


ROOT = Path(__file__).resolve().parents[1]


class MissionRecordContractTests(unittest.TestCase):
    def test_mission_fixture_validates_against_schema(self):
        results = validate_all_examples(ROOT)
        mission_results = [
            result
            for result in results
            if "missions" in result.path.parts and result.path.suffix == ".json"
        ]

        self.assertGreater(len(mission_results), 0)
        self.assertEqual([], [result for result in mission_results if not result.ok])

    def test_core_mission_records_validate_individually(self):
        fixture = load_json(ROOT / "examples" / "missions" / "repo-audit-streamlinear.json")
        schema_names = {
            "mission_runs": "mission-run.schema.json",
            "agent_runs": "mission-agent-run.schema.json",
            "events": "mission-event.schema.json",
            "observations": "mission-observation.schema.json",
            "findings": "mission-finding.schema.json",
            "stumbles": "mission-stumble.schema.json",
            "artifacts": "mission-artifact.schema.json",
            "governance_receipts": "mission-governance-receipt.schema.json",
        }

        failures = []
        for collection, schema_name in schema_names.items():
            schema = load_json(ROOT / "schemas" / schema_name)
            for record in fixture[collection]:
                failures.extend(validate_schema(record, schema))

        self.assertEqual([], failures)

    def test_mission_run_schema_is_generic_not_paia_specific(self):
        schema = load_json(ROOT / "schemas" / "mission-run.schema.json")
        mission_types = schema["properties"]["mission_type"]["enum"]

        self.assertIn("repo_audit", mission_types)
        self.assertIn("marketing_opportunity_review", mission_types)
        self.assertNotIn("paia_repo_audit", mission_types)


if __name__ == "__main__":
    unittest.main()
