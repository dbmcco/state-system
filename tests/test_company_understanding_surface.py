from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.company_capability import CompanyCapabilityRuntime
from state_system.company_preflight import CompanyPreflightRuntime
from state_system.company_understanding_surface import (
    build_company_understanding_surface_read_model,
)
from state_system.contracts import load_json
from state_system.source_freshness import SourceFreshnessRuntime
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = ROOT / "examples" / "company-capability"


class CompanyUnderstandingSurfaceTests(unittest.TestCase):
    def test_surface_rolls_capability_access_freshness_and_indexes_together(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
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
                    "checked_at": "2026-05-15T18:00:00Z",
                    "stale_after": "2026-05-15T18:15:00Z",
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
                    "checked_at": "2026-05-15T18:01:00Z",
                    "source_watermark": "kb.indexed_at:2026-05-15T18:00:30Z",
                    "stale_after": "2026-05-15T18:16:00Z",
                    "watermark_basis": "source_index",
                    "latest_indexed_at": "2026-05-15T18:00:30Z",
                    "status_reason": "latest indexed corpus timestamp is inside policy",
                    "evidence_refs": ["agent-runtime:freshness:kb:sampleco"],
                }
            )

            read_model = build_company_understanding_surface_read_model(stores)

            self.assertEqual("company_understanding_surface_read_model", read_model["id"])
            self.assertFalse(read_model["invariant"]["surface_executes_retrieval"])
            self.assertIn("index.sampleco.kb.corpus", read_model["index_refs"])
            sampleco_inst = read_model["companies"][0]
            kb = _source(sampleco_inst, "connector.sampleco.kb")
            self.assertEqual("passed", kb["access_status"])
            self.assertEqual("fresh", kb["freshness_status"])
            self.assertEqual("declared", kb["index_status"])
            self.assertEqual("ready", kb["understanding_status"])
            self.assertEqual(["index.sampleco.kb.corpus"], kb["index_refs"])

            zulip = _source(sampleco_inst, "connector.sampleco.zulip")
            self.assertEqual("missing", zulip["access_status"])
            self.assertEqual("missing", zulip["freshness_status"])
            self.assertEqual("declared", zulip["index_status"])
            self.assertEqual("searchable_access_unproven", zulip["understanding_status"])
            self.assertIn(
                "gap.company.sampleco.connector.sampleco.zulip.access_missing",
                read_model["source_gap_refs"],
            )

    def test_cli_writes_company_understanding_surface(self):
        with TemporaryDirectory() as directory, TemporaryDirectory() as output_dir:
            seed_output = StringIO()
            seed_code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "company-capability-seed",
                    str(PACK_DIR / "company-sampleco.json"),
                ],
                stdout=seed_output,
            )
            self.assertEqual(0, seed_code, seed_output.getvalue())

            read_output = StringIO()
            read_code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "company-understanding-surface-read",
                    "--output-dir",
                    output_dir,
                ],
                stdout=read_output,
            )

            self.assertEqual(0, read_code, read_output.getvalue())
            payload = json.loads(read_output.getvalue())
            read_model_path = Path(payload["read_model_path"])
            self.assertEqual(
                "company-understanding-surface-read-model.json",
                read_model_path.name,
            )
            read_model = json.loads(read_model_path.read_text(encoding="utf-8"))
            self.assertEqual("company_understanding_surface_read_model", read_model["id"])
            self.assertEqual(["company.sampleco"], [c["company_ref"] for c in read_model["companies"]])


def _source(company: dict, connector_ref: str) -> dict:
    return next(
        source
        for source in company["source_readiness"]
        if source["connector_ref"] == connector_ref
    )


if __name__ == "__main__":
    unittest.main()
