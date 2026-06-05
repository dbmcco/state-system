from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.company_preflight import CompanyPreflightRuntime
from state_system.source_freshness import SourceFreshnessRuntime
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]


class AgentRuntimeBootstrapExportTests(unittest.TestCase):
    def test_cli_bootstrap_creates_agent_runtime_artifact_layout(self):
        with TemporaryDirectory() as directory:
            output = StringIO()
            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "runtime-bootstrap-export",
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
            freshness_path = (
                Path(directory)
                / "source-freshness"
                / "source-freshness-read-model.json"
            )

            self.assertEqual(str(capability_path), payload["company_capability_path"])
            self.assertEqual(str(preflight_path), payload["company_preflight_path"])
            self.assertEqual(str(freshness_path), payload["source_freshness_path"])
            self.assertTrue(capability_path.exists())
            self.assertTrue(preflight_path.exists())
            self.assertTrue(freshness_path.exists())

            capability = json.loads(capability_path.read_text(encoding="utf-8"))
            preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
            freshness = json.loads(freshness_path.read_text(encoding="utf-8"))
            self.assertEqual(3, len(capability["companies"]))
            self.assertEqual([], preflight["results"])
            self.assertEqual({}, preflight["latest_by_scope_key"])
            self.assertFalse(preflight["invariant"]["authorizes_execution"])
            self.assertEqual([], freshness["results"])
            self.assertEqual({}, freshness["latest_by_scope_key"])
            self.assertTrue(
                freshness["invariant"]["freshness_is_recency_evidence"]
            )
            self.assertFalse(freshness["invariant"]["proves_live_access"])
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
                    "preflight_ref": "preflight.sampleco.local",
                    "company_ref": "company.sampleco",
                    "connector_ref": "connector.sampleco.local",
                    "tool_ref": "tool.agent_runtime.local_path.inspect",
                    "action_ref": "action_surface.sampleco.inspect_local_workspace",
                    "agent_ref": "persona.iris",
                    "runner_ref": "runner.agent_runtime.codex",
                    "status": "passed",
                    "checked_at": "2026-05-14T18:55:00Z",
                    "stale_after": "2026-05-14T19:55:00Z",
                    "evidence_refs": [
                        "agent-runtime:preflight:local-path:sampleco",
                    ],
                }
            )

            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "runtime-bootstrap-export",
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

    def test_bootstrap_exports_existing_source_freshness_results(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            SourceFreshnessRuntime(stores).record(
                {
                    "company_ref": "company.sampleco",
                    "connector_ref": "connector.sampleco.kb",
                    "source_ref": "kb:tenant:sampleco",
                    "connector_type": "kb",
                    "status": "fresh",
                    "checked_at": "2026-05-15T12:00:00Z",
                    "source_watermark": "kb.indexed_at:2026-05-15T11:59:00Z",
                    "stale_after": "2026-05-15T12:15:00Z",
                    "lag_seconds": 60,
                    "evidence_refs": ["agent-runtime:freshness:kb:sampleco"],
                }
            )

            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "runtime-bootstrap-export",
                ],
                stdout=StringIO(),
            )

            self.assertEqual(0, code)
            freshness_path = (
                Path(directory)
                / "source-freshness"
                / "source-freshness-read-model.json"
            )
            freshness = json.loads(freshness_path.read_text(encoding="utf-8"))
            self.assertEqual(1, len(freshness["results"]))
            self.assertEqual("fresh", freshness["results"][0]["status"])


if __name__ == "__main__":
    unittest.main()
