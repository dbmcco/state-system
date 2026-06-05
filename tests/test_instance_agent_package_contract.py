from __future__ import annotations

import unittest
from pathlib import Path

from state_system.contracts import load_json, schema_for_example, validate_schema


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = ROOT / "examples" / "instance-agent-package"


class InstanceAgentPackageContractTests(unittest.TestCase):
    def test_instance_agent_package_examples_validate(self):
        schema = load_json(ROOT / "schemas" / "instance-agent-package.schema.json")

        for path in sorted(EXAMPLE_DIR.glob("*.json")):
            with self.subTest(path=path.name):
                self.assertEqual(
                    "instance-agent-package.schema.json",
                    schema_for_example(path.name),
                )
                package = load_json(path)
                self.assertEqual([], validate_schema(package, schema))

    def test_personal_package_keeps_spotify_freshness_gap_visible(self):
        package = load_json(
            EXAMPLE_DIR / "instance-agent-package-sample-personal-nova.json"
        )

        self.assertNotIn(
            "gap.state_instance.sample_personal.connector.personal.garmin_connect.access_planned",
            package["source_context"]["source_gap_refs"],
        )
        self.assertIn(
            "gap.state_instance.sample_personal.connector.personal.spotify.freshness_stale",
            package["source_context"]["source_gap_refs"],
        )
        self.assertTrue(
            package["freshness"]["requires_refresh_before_external_action"]
        )
        self.assertTrue(package["invariant"]["source_gaps_are_visible"])
        self.assertFalse(package["invariant"]["agent_package_authorizes_execution"])

    def test_sampleco_package_excludes_personal_sources(self):
        package = load_json(EXAMPLE_DIR / "instance-agent-package-sampleco-iris.json")
        encoded = str(package)

        self.assertNotIn("garmin", encoded.lower())
        self.assertNotIn("spotify", encoded.lower())
        self.assertIn(
            "gap.state_instance.sampleco.connector.sampleco.msgvault.freshness_failed",
            package["source_context"]["source_gap_refs"],
        )

    def test_sampleco_package_includes_governed_relationship_index_route_without_personal_materialization(self):
        package = load_json(EXAMPLE_DIR / "instance-agent-package-sampleco-iris.json")
        route = _route(package, "question_route.sampleco.federated_relationship_index")

        self.assertEqual(
            "declared_governed_route",
            route["query_route"]["status"],
        )
        self.assertFalse(route["query_route"]["local_materialization"])
        self.assertEqual(
            "state_instance.sample_personal",
            route["query_route"]["source_instance_ref"],
        )
        self.assertEqual(
            "index.federated.sample_personal.relationship_index",
            route["query_route"]["index_ref"],
        )
        self.assertIn(
            "state_instance.sample_personal",
            package["evidence_context"]["federated_instance_refs"],
        )
        self.assertIn(
            "index.federated.sample_personal.relationship_index",
            package["evidence_context"]["index_refs"],
        )
        self.assertIn(
            "tool.relationship_substrate.search_small_consulting_firm_contacts",
            route["tool_refs"],
        )


def _route(package: dict, route_id: str):
    matches = [route for route in package.get("question_routes", []) if route["id"] == route_id]
    if not matches:
        raise AssertionError(f"{route_id} not found")
    return matches[0]


if __name__ == "__main__":
    unittest.main()
