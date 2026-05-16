from __future__ import annotations

from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.contracts import load_json
from state_system.instance_preflight import (
    run_instance_connector_preflight,
)
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = ROOT / "examples" / "instance-capability"


class InstancePreflightRunnerTests(unittest.TestCase):
    def test_runner_checks_local_path_and_records_planned_connector_gaps(self):
        with TemporaryDirectory() as directory:
            state_root = Path(directory) / "state-root"
            local_root = Path(directory) / "personal"
            local_root.mkdir()
            stores = StateStoreBundle(state_root)
            pack = {
                "instance_ref": "state_instance.test_person",
                "source_connectors": [
                    {
                        "id": "connector.test.local",
                        "connector_type": "local_path",
                        "source_ref": f"local:{local_root}",
                    },
                    {
                        "id": "connector.test.agentmem",
                        "connector_type": "agentmem",
                        "source_ref": "agentmem:tenant:test",
                    },
                ],
            }

            summary = run_instance_connector_preflight(
                stores,
                pack,
                checked_at="2026-05-16T21:00:00Z",
                stale_after="2026-05-16T22:00:00Z",
                allow_network=False,
            )

        by_connector = {
            record["connector_ref"]: record
            for record in summary["records"]
        }
        self.assertEqual("passed", by_connector["connector.test.local"]["status"])
        self.assertEqual(
            "planned",
            by_connector["connector.test.agentmem"]["status"],
        )
        self.assertIn(
            "no_safe_probe_declared",
            by_connector["connector.test.agentmem"]["detail"],
        )

    def test_cli_runs_personal_instance_preflight_into_state_root(self):
        with TemporaryDirectory() as directory:
            output = StringIO()
            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "instance-preflight-run",
                    str(PACK_DIR / "instance-braydon-personal.json"),
                    "--checked-at",
                    "2026-05-16T21:05:00Z",
                    "--stale-after",
                    "2026-05-16T22:05:00Z",
                    "--no-network",
                ],
                stdout=output,
            )

            self.assertEqual(0, code, output.getvalue())
            payload = json.loads(output.getvalue())
            records = payload["records"]
            stored_records = list(
                (Path(directory) / "state" / "instance-preflight-results").glob("*.json")
            )

        self.assertEqual(len(records), len(stored_records))
        self.assertIn(
            "connector.personal.agentmem",
            {record["connector_ref"] for record in records},
        )
        self.assertIn(
            "connector.personal.relationship_substrate",
            {record["connector_ref"] for record in records},
        )


if __name__ == "__main__":
    unittest.main()
