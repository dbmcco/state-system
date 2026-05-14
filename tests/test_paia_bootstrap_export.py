from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.company_preflight import CompanyPreflightRuntime
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]


class PaiaBootstrapExportTests(unittest.TestCase):
    def test_cli_bootstrap_creates_paia_runtime_artifact_layout(self):
        with TemporaryDirectory() as directory:
            output = StringIO()
            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "paia-bootstrap-export",
                ],
                stdout=output,
            )

            self.assertEqual(0, code, output.getvalue())
            payload = json.loads(output.getvalue())
            self.assertEqual(str(Path(directory)), payload["state_root"])

            capability_path = (
                Path(directory)
                / "company-capability"
                / "company-capability-read-model.json"
            )
            preflight_path = (
                Path(directory)
                / "company-preflight"
                / "company-preflight-results-read-model.json"
            )

            self.assertEqual(str(capability_path), payload["company_capability_path"])
            self.assertEqual(str(preflight_path), payload["company_preflight_path"])
            self.assertTrue(capability_path.exists())
            self.assertTrue(preflight_path.exists())

            capability = json.loads(capability_path.read_text(encoding="utf-8"))
            preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
            self.assertEqual(3, len(capability["companies"]))
            self.assertEqual([], preflight["results"])
            self.assertEqual({}, preflight["latest_by_scope_key"])
            self.assertFalse(preflight["invariant"]["authorizes_execution"])
            self.assertEqual(
                3,
                len(
                    list(
                        (
                            Path(directory)
                            / "state"
                            / "company-capabilities"
                        ).glob("*.json")
                    )
                ),
            )

    def test_bootstrap_exports_existing_preflight_results(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            CompanyPreflightRuntime(stores).record(
                {
                    "preflight_ref": "preflight.lfw.local",
                    "company_ref": "company.lfw",
                    "connector_ref": "connector.lfw.local",
                    "tool_ref": "tool.paia.local_path.inspect",
                    "action_ref": "action_surface.lfw.inspect_local_workspace",
                    "agent_ref": "persona.caroline",
                    "runner_ref": "runner.paia.codex",
                    "status": "passed",
                    "checked_at": "2026-05-14T18:55:00Z",
                    "stale_after": "2026-05-14T19:55:00Z",
                    "evidence_refs": [
                        "paia:preflight:local-path:lfw",
                    ],
                }
            )

            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "paia-bootstrap-export",
                ],
                stdout=StringIO(),
            )

            self.assertEqual(0, code)
            preflight_path = (
                Path(directory)
                / "company-preflight"
                / "company-preflight-results-read-model.json"
            )
            preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
            self.assertEqual(1, len(preflight["results"]))
            self.assertEqual("passed", preflight["results"][0]["status"])


if __name__ == "__main__":
    unittest.main()
