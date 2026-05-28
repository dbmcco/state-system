from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.company_preflight import (
    CompanyPreflightRuntime,
    build_company_preflight_read_model,
)
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]


class CompanyPreflightResultTests(unittest.TestCase):
    def test_record_persists_preflight_result_as_live_access_evidence_only(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            runtime = CompanyPreflightRuntime(stores)

            record = runtime.record(
                {
                    "preflight_ref": "preflight.acme.linear",
                    "company_ref": "company.acme",
                    "connector_ref": "connector.acme.linear",
                    "tool_ref": "tool.paia.linear.read",
                    "action_ref": "action_surface.acme.read_linear",
                    "agent_ref": "persona.caroline",
                    "runner_ref": "runner.paia.codex",
                    "status": "passed",
                    "checked_at": "2026-05-14T18:20:00Z",
                    "stale_after": "2026-05-14T19:20:00Z",
                    "ttl_seconds": 3600,
                    "evidence_refs": ["paia:preflight:linear:20260514T182000Z"],
                    "detail": "Linear read preflight passed for FORGE/INT teams.",
                }
            )

            self.assertEqual(
                "preflight.acme.linear|company.acme|connector.acme.linear|"
                "tool.paia.linear.read|action_surface.acme.read_linear|"
                "persona.caroline|runner.paia.codex",
                record["scope_key"],
            )
            self.assertTrue(
                record["id"].startswith("preflight_result.preflight.acme.linear")
            )
            self.assertFalse(record["authorizes_execution"])
            self.assertEqual(record, runtime.read(record["id"]))

    def test_read_model_exports_latest_results_by_preflight_ref(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            runtime = CompanyPreflightRuntime(stores)
            runtime.record(
                {
                    "preflight_ref": "preflight.acme.linear",
                    "company_ref": "company.acme",
                    "connector_ref": "connector.acme.linear",
                    "tool_ref": "tool.paia.linear.read",
                    "action_ref": "action_surface.acme.read_linear",
                    "agent_ref": "persona.caroline",
                    "status": "failed",
                    "checked_at": "2026-05-14T18:00:00Z",
                    "stale_after": "2026-05-14T19:00:00Z",
                    "evidence_refs": ["paia:preflight:linear:failed"],
                    "error": {"code": "missing_token", "message": "Linear token missing."},
                }
            )
            runtime.record(
                {
                    "preflight_ref": "preflight.acme.linear",
                    "company_ref": "company.acme",
                    "connector_ref": "connector.acme.linear",
                    "tool_ref": "tool.paia.linear.read",
                    "action_ref": "action_surface.acme.read_linear",
                    "agent_ref": "persona.caroline",
                    "status": "passed",
                    "checked_at": "2026-05-14T18:15:00Z",
                    "stale_after": "2026-05-14T19:15:00Z",
                    "evidence_refs": ["paia:preflight:linear:passed"],
                }
            )

            read_model = build_company_preflight_read_model(stores)

            self.assertEqual("company_preflight_result_read_model", read_model["id"])
            scope_key = (
                "preflight.acme.linear|company.acme|connector.acme.linear|"
                "tool.paia.linear.read|action_surface.acme.read_linear|"
                "persona.caroline|"
            )
            latest = read_model["latest_by_scope_key"][scope_key]
            self.assertEqual("passed", latest["status"])
            self.assertEqual("2026-05-14T18:15:00Z", latest["checked_at"])
            self.assertFalse(read_model["invariant"]["authorizes_execution"])
            self.assertEqual(
                "governance",
                read_model["invariant"]["protected_action_authorized_by"],
            )

    def test_cli_records_lists_and_exports_preflight_results(self):
        with TemporaryDirectory() as directory, TemporaryDirectory() as output_dir:
            output = StringIO()
            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "company-preflight-record",
                    "--preflight-ref",
                    "preflight.acme.linear",
                    "--company-ref",
                    "company.acme",
                    "--connector-ref",
                    "connector.acme.linear",
                    "--tool-ref",
                    "tool.paia.linear.read",
                    "--action-ref",
                    "action_surface.acme.read_linear",
                    "--agent-ref",
                    "persona.caroline",
                    "--runner-ref",
                    "runner.paia.codex",
                    "--status",
                    "passed",
                    "--checked-at",
                    "2026-05-14T18:20:00Z",
                    "--stale-after",
                    "2026-05-14T19:20:00Z",
                    "--evidence-ref",
                    "paia:preflight:linear:20260514T182000Z",
                    "--detail",
                    "Linear read preflight passed.",
                ],
                stdout=output,
            )

            self.assertEqual(0, code, output.getvalue())
            payload = json.loads(output.getvalue())
            self.assertEqual("passed", payload["preflight_result"]["status"])

            list_output = StringIO()
            list_code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "company-preflight-list",
                ],
                stdout=list_output,
            )

            self.assertEqual(0, list_code, list_output.getvalue())
            self.assertEqual(1, len(json.loads(list_output.getvalue())["results"]))

            export_output = StringIO()
            export_code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "company-preflight-export",
                    "--output-dir",
                    output_dir,
                ],
                stdout=export_output,
            )

            self.assertEqual(0, export_code, export_output.getvalue())
            export_payload = json.loads(export_output.getvalue())
            read_model_path = Path(export_payload["read_model_path"])
            read_model = json.loads(read_model_path.read_text(encoding="utf-8"))
            self.assertEqual(1, len(read_model["results"]))
            self.assertFalse(read_model["results"][0]["authorizes_execution"])


if __name__ == "__main__":
    unittest.main()
