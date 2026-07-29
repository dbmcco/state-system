from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system.contracts import load_json, validate_schema
from state_system.fleet_refresh import run_fleet_refresh


ROOT = Path(__file__).resolve().parents[1]


class EcsManifestMultiRootTests(unittest.TestCase):
    def test_fleet_manifest_accepts_multiple_entity_current_state_roots(self):
        with TemporaryDirectory() as directory:
            first = Path(directory) / "first"
            second = Path(directory) / "second"
            manifest = {
                "id": "fleet_refresh_manifest.multi_ecs",
                "instances": [
                    {
                        "id": "fleet_instance.placeholder",
                        "state_root": str(Path(directory) / "instance"),
                        "instance_ref": "state_instance.placeholder",
                        "agent_ref": "agent.placeholder",
                        "package_id": "instance_agent_package.placeholder",
                    }
                ],
                "entity_current_state": {
                    "roots": [
                        {"state_root": str(first), "label": "personal"},
                        {"state_root": str(second), "label": "portfolio"},
                    ],
                    "output_dir": "entity-current-state",
                },
            }
            schema = load_json(ROOT / "schemas" / "fleet-refresh-manifest.schema.json")

            errors = validate_schema(manifest, schema)

        self.assertEqual([], errors)

    def test_fleet_refresh_reports_each_entity_current_state_root(self):
        with TemporaryDirectory() as directory:
            first = Path(directory) / "first"
            second = Path(directory) / "second"
            manifest = {
                "id": "fleet_refresh_manifest.multi_ecs",
                "instances": [
                    {
                        "id": "fleet_instance.placeholder",
                        "state_root": str(Path(directory) / "instance"),
                        "instance_ref": "state_instance.placeholder",
                        "agent_ref": "agent.placeholder",
                        "package_id": "instance_agent_package.placeholder",
                    }
                ],
                "entity_current_state": {
                    "roots": [
                        {"state_root": str(first), "label": "personal"},
                        {"state_root": str(second), "label": "portfolio"},
                    ],
                    "output_dir": "entity-current-state",
                },
            }

            report = run_fleet_refresh(
                manifest,
                project_root=ROOT,
                checked_at="2026-06-25T12:00:00Z",
                stale_after="2026-06-25T13:00:00Z",
                dry_run=True,
            )

        ecs = report["entity_current_state"]
        self.assertEqual("planned", ecs["status"])
        self.assertEqual(
            {"personal", "portfolio"},
            {root["label"] for root in ecs["roots"]},
        )
        self.assertEqual(
            {str(first), str(second)},
            {root["state_root"] for root in ecs["roots"]},
        )


if __name__ == "__main__":
    unittest.main()
