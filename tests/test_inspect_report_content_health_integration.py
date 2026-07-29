from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system.api_surface import StateDispatcher


ROOT = Path(__file__).resolve().parents[1]


class InspectReportContentHealthIntegrationTests(unittest.TestCase):
    def test_inspect_package_reports_content_health_separately_from_process_health(self):
        with TemporaryDirectory() as directory:
            state_root = Path(directory)
            package_dir = state_root / "state" / "instance-agent-packages"
            package_dir.mkdir(parents=True)
            package = {
                "id": "instance_agent_package.sample.content_health",
                "created_at": "2026-06-25T12:00:00Z",
                "source_context": {
                    "source_readiness": [
                        {
                            "connector_ref": "connector.sample.docs",
                            "source_ref": "docs:sample",
                            "freshness_status": "fresh",
                            "content_status": "stale",
                            "process_status": "succeeded",
                            "stale_after": "2026-06-20T00:00:00Z",
                            "source_gap_refs": [
                                "gap.state_instance.sample.connector.sample.docs.content_stale"
                            ],
                            "evidence_refs": ["freshness:docs:stale-content"],
                        }
                    ],
                    "source_gap_refs": [
                        "gap.state_instance.sample.connector.sample.docs.content_stale"
                    ],
                },
                "freshness": {
                    "generated_at": "2026-06-25T12:00:00Z",
                    "requires_refresh_before_external_action": True,
                    "content_status": "stale",
                    "process_status": "succeeded",
                    "source_gap_refs": [
                        "gap.state_instance.sample.connector.sample.docs.content_stale"
                    ],
                },
            }
            package_dir.joinpath(f"{package['id']}.json").write_text(
                json.dumps(package), encoding="utf-8"
            )

            response = StateDispatcher(ROOT, state_root).dispatch(
                "inspect",
                scope="state:local",
                arguments={"package_ref": package["id"]},
            )

        self.assertEqual("ok", response["status"])
        health = response["data"]["package_health"]
        self.assertEqual("succeeded", health["process_status"])
        self.assertEqual("stale", health["content_status"])
        self.assertNotEqual(health["process_status"], health["content_status"])
        self.assertTrue(health["requires_refresh_before_external_action"])
        self.assertIn(
            "gap.state_instance.sample.connector.sample.docs.content_stale",
            health["source_gap_refs"],
        )


if __name__ == "__main__":
    unittest.main()
