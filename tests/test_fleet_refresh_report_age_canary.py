from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system.contracts import load_json, validate_schema
from state_system.fleet_refresh import run_fleet_refresh


ROOT = Path(__file__).resolve().parents[1]


class FleetRefreshReportAgeCanaryTests(unittest.TestCase):
    def test_manifest_schema_rejects_empty_instances(self):
        schema = load_json(ROOT / "schemas" / "fleet-refresh-manifest.schema.json")
        errors = validate_schema(
            {"id": "fleet_refresh_manifest.empty", "instances": []}, schema
        )

        self.assertTrue(
            any("instances" in error and "minItems" in error for error in errors),
            errors,
        )

    def test_report_includes_age_canary_for_generated_report_itself(self):
        with TemporaryDirectory() as directory:
            state_root = Path(directory) / "runtime"
            manifest = {
                "id": "fleet_refresh_manifest.canary",
                "default_ttl_seconds": 3600,
                "instances": [
                    {
                        "id": "fleet_instance.canary",
                        "state_root": str(state_root),
                        "instance_ref": "state_instance.canary",
                        "agent_ref": "agent.canary",
                        "package_id": "instance_agent_package.canary",
                    }
                ],
            }

            report = run_fleet_refresh(
                manifest,
                project_root=ROOT,
                checked_at="2026-06-25T12:00:00Z",
                stale_after="2026-06-25T13:00:00Z",
                output_dir=Path(directory) / "reports",
                dry_run=True,
            )

        canary = report["report_age_canary"]
        self.assertEqual("2026-06-25T12:00:00Z", canary["checked_at"])
        self.assertEqual("2026-06-25T13:00:00Z", canary["stale_after"])
        self.assertFalse(canary["is_stale_at_checked_at"])
        self.assertIn("fleet-refresh-report.json", canary["report_ref"])


if __name__ == "__main__":
    unittest.main()
