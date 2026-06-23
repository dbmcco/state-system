from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.company_capability import CompanyCapabilityRuntime
from state_system.company_preflight import CompanyPreflightRuntime
from state_system.contracts import load_json
from state_system.interpreted_index import (
    build_interpreted_index_read_model,
    search_interpreted_index,
)
from state_system.source_freshness import SourceFreshnessRuntime
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = ROOT / "examples" / "company-capability"


class InterpretedIndexTests(unittest.TestCase):
    def test_index_materializes_company_readiness_records_without_raw_corpus(self):
        with TemporaryDirectory() as directory:
            stores = _sampleco_runtime(Path(directory))

            read_model = build_interpreted_index_read_model(
                stores,
                company_ref="company.sampleco",
            )

            self.assertEqual("state_system_interpreted_index_read_model", read_model["id"])
            self.assertEqual(["company.sampleco"], read_model["company_refs"])
            self.assertTrue(read_model["records"])
            self.assertTrue(read_model["invariant"]["ingests_raw_source_data"] is False)
            self.assertTrue(read_model["invariant"]["model_owns_synthesis"])
            kinds = {record["record_kind"] for record in read_model["records"]}
            self.assertIn("source_readiness", kinds)
            self.assertIn("source_gap", kinds)
            self.assertIn("searchable_surface", kinds)
            self.assertTrue(
                any(
                    record["record_ref"] == "source_readiness.company.sampleco.connector.sampleco.kb"
                    and "ready" in record["text"]
                    for record in read_model["records"]
                )
            )

    def test_search_returns_ranked_interpreted_records_for_query(self):
        with TemporaryDirectory() as directory:
            stores = _sampleco_runtime(Path(directory))
            read_model = build_interpreted_index_read_model(
                stores,
                company_ref="company.sampleco",
            )

            result = search_interpreted_index(
                read_model,
                query="kb ready source",
                limit=3,
            )

            self.assertEqual("state_system_interpreted_search_result", result["id"])
            self.assertEqual("kb ready source", result["query"])
            self.assertGreaterEqual(len(result["records"]), 1)
            self.assertEqual("company.sampleco", result["records"][0]["company_ref"])
            self.assertIn("kb", result["records"][0]["text"])

    def test_cli_writes_and_searches_interpreted_index(self):
        with TemporaryDirectory() as directory, TemporaryDirectory() as output_dir:
            stores = _sampleco_runtime(Path(directory))
            del stores

            read_output = StringIO()
            read_code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "state-interpreted-index-read",
                    "--company-ref",
                    "company.sampleco",
                    "--output-dir",
                    output_dir,
                ],
                stdout=read_output,
            )

            self.assertEqual(0, read_code, read_output.getvalue())
            read_payload = json.loads(read_output.getvalue())
            self.assertEqual(
                "state-interpreted-index-read-model.json",
                Path(read_payload["read_model_path"]).name,
            )

            search_output = StringIO()
            search_code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "state-interpreted-search",
                    "--company-ref",
                    "company.sampleco",
                    "--query",
                    "linear ready",
                    "--limit",
                    "5",
                ],
                stdout=search_output,
            )

            self.assertEqual(0, search_code, search_output.getvalue())
            search_payload = json.loads(search_output.getvalue())
            self.assertEqual("state_system_interpreted_search_result", search_payload["id"])
            self.assertTrue(search_payload["records"])

    def test_cli_require_records_fails_when_live_search_has_no_records(self):
        with TemporaryDirectory() as directory:
            _sampleco_runtime(Path(directory))

            search_output = StringIO()
            search_code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "state-interpreted-search",
                    "--company-ref",
                    "company.sampleco",
                    "--query",
                    "zzzzzzzzzz",
                    "--limit",
                    "1",
                    "--require-records",
                ],
                stdout=search_output,
            )

            self.assertEqual(1, search_code, search_output.getvalue())
            search_payload = json.loads(search_output.getvalue())
            self.assertFalse(search_payload["ok"])
            self.assertEqual(
                "state_interpreted_search_no_records",
                search_payload["error"]["code"],
            )


def _sampleco_runtime(root: Path) -> StateStoreBundle:
    stores = StateStoreBundle(root)
    CompanyCapabilityRuntime(stores).seed([load_json(PACK_DIR / "company-sampleco.json")])
    CompanyPreflightRuntime(stores).record(
        {
            "preflight_ref": "preflight.sampleco.kb",
            "company_ref": "company.sampleco",
            "connector_ref": "connector.sampleco.kb",
            "tool_ref": "tool.agent_runtime.kb.search",
            "action_ref": "action_surface.sampleco.read_knowledge_store",
            "agent_ref": "persona.iris",
            "runner_ref": "runner.agent_runtime.codex",
            "status": "passed",
            "checked_at": "2026-05-16T19:30:00Z",
            "stale_after": "2026-05-16T19:45:00Z",
            "evidence_refs": ["agent-runtime:preflight:kb:sampleco"],
        }
    )
    SourceFreshnessRuntime(stores).record(
        {
            "company_ref": "company.sampleco",
            "connector_ref": "connector.sampleco.kb",
            "source_ref": "kb:tenant:sampleco",
            "connector_type": "kb",
            "status": "fresh",
            "checked_at": "2026-05-16T19:31:00Z",
            "source_watermark": "kb.updated_at:2026-05-16T19:30:00Z",
            "stale_after": "2026-05-16T19:46:00Z",
            "watermark_basis": "source_index",
            "latest_indexed_at": "2026-05-16T19:30:00Z",
            "status_reason": "latest indexed corpus timestamp is inside policy",
            "evidence_refs": ["agent-runtime:freshness:kb:sampleco"],
        }
    )
    return stores


if __name__ == "__main__":
    unittest.main()
