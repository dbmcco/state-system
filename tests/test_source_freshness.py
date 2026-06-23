from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.contracts import load_json, validate_schema
from state_system.source_freshness import (
    SourceFreshnessRuntime,
    build_source_freshness_read_model,
)
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]


class SourceFreshnessTests(unittest.TestCase):
    def test_record_persists_freshness_without_proving_access_or_authority(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            runtime = SourceFreshnessRuntime(stores)

            record = runtime.record(
                {
                    "company_ref": "company.sampleco",
                    "connector_ref": "connector.sampleco.linear",
                    "source_ref": "linear:teams:FORGE,INT",
                    "connector_type": "linear",
                    "status": "fresh",
                    "checked_at": "2026-05-15T12:00:00Z",
                    "source_watermark": "linear.latest_updated_at:2026-05-15T11:58:00Z",
                    "stale_after": "2026-05-15T12:15:00Z",
                    "watermark_basis": "source_event",
                    "latest_source_event_at": "2026-05-15T11:58:00Z",
                    "status_reason": "latest source event timestamp is inside policy",
                    "lag_seconds": 120,
                    "evidence_refs": ["agent-runtime:freshness:linear:company.sampleco:20260515T120000Z"],
                    "detail": "Linear FORGE/INT freshness watermark checked.",
                }
            )

            self.assertEqual(
                "company.sampleco|connector.sampleco.linear|linear:teams:FORGE,INT",
                record["scope_key"],
            )
            self.assertTrue(
                record["id"].startswith("source_freshness.company.sampleco")
            )
            self.assertFalse(record["proves_live_access"])
            self.assertFalse(record["authorizes_execution"])
            self.assertEqual("source_event", record["watermark_basis"])
            self.assertEqual(
                [],
                validate_schema(
                    record,
                    load_json(ROOT / "schemas" / "source-freshness-record.schema.json"),
                ),
            )
            self.assertEqual(record, runtime.read(record["id"]))

    def test_read_model_exports_latest_freshness_by_scope_key(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            runtime = SourceFreshnessRuntime(stores)
            runtime.record(
                {
                    "company_ref": "company.sampleco",
                    "connector_ref": "connector.sampleco.kb",
                    "source_ref": "kb:tenant:sampleco",
                    "connector_type": "kb",
                    "status": "stale",
                    "checked_at": "2026-05-15T11:00:00Z",
                    "source_watermark": "kb.indexed_at:2026-05-15T09:00:00Z",
                    "stale_after": "2026-05-15T11:15:00Z",
                    "watermark_basis": "source_index",
                    "latest_indexed_at": "2026-05-15T09:00:00Z",
                    "status_reason": "latest indexed corpus timestamp is outside policy",
                    "lag_seconds": 7200,
                    "evidence_refs": ["agent-runtime:freshness:kb:stale"],
                }
            )
            runtime.record(
                {
                    "company_ref": "company.sampleco",
                    "connector_ref": "connector.sampleco.kb",
                    "source_ref": "kb:tenant:sampleco",
                    "connector_type": "kb",
                    "status": "fresh",
                    "checked_at": "2026-05-15T12:00:00Z",
                    "source_watermark": "kb.indexed_at:2026-05-15T11:59:00Z",
                    "stale_after": "2026-05-15T12:15:00Z",
                    "watermark_basis": "source_index",
                    "latest_indexed_at": "2026-05-15T11:59:00Z",
                    "status_reason": "latest indexed corpus timestamp is inside policy",
                    "lag_seconds": 60,
                    "evidence_refs": ["agent-runtime:freshness:kb:fresh"],
                }
            )

            read_model = build_source_freshness_read_model(stores)

            self.assertEqual("source_freshness_read_model", read_model["id"])
            scope_key = "company.sampleco|connector.sampleco.kb|kb:tenant:sampleco"
            latest = read_model["latest_by_scope_key"][scope_key]
            self.assertEqual("fresh", latest["status"])
            self.assertEqual("2026-05-15T12:00:00Z", latest["checked_at"])
            self.assertTrue(read_model["invariant"]["freshness_is_recency_evidence"])
            self.assertFalse(read_model["invariant"]["proves_live_access"])
            self.assertFalse(read_model["invariant"]["authorizes_execution"])

    def test_record_rejects_fresh_probe_only_status(self):
        with TemporaryDirectory() as directory:
            runtime = SourceFreshnessRuntime(StateStoreBundle(Path(directory)))

            with self.assertRaisesRegex(ValueError, "fresh cannot be proven by probe_only"):
                runtime.record(
                    {
                        "company_ref": "company.sampleco",
                        "connector_ref": "connector.sampleco.kb",
                        "source_ref": "kb:tenant:sampleco",
                        "connector_type": "kb",
                        "status": "fresh",
                        "checked_at": "2026-05-15T12:00:00Z",
                        "source_watermark": "kb.adapter.checked_at:2026-05-15T12:00:00Z;corpus_watermark=unproven",
                        "stale_after": "2026-05-15T12:15:00Z",
                        "watermark_basis": "probe_only",
                        "status_reason": "connector probe ran but source/corpus freshness is unproven",
                    }
                )

    def test_record_rejects_source_index_without_index_timestamp(self):
        with TemporaryDirectory() as directory:
            runtime = SourceFreshnessRuntime(StateStoreBundle(Path(directory)))

            with self.assertRaisesRegex(ValueError, "source_index/derived_index"):
                runtime.record(
                    {
                        "company_ref": "company.sampleco",
                        "connector_ref": "connector.sampleco.kb",
                        "source_ref": "kb:tenant:sampleco",
                        "connector_type": "kb",
                        "status": "fresh",
                        "checked_at": "2026-05-15T12:00:00Z",
                        "source_watermark": "kb.indexed_at:2026-05-15T11:59:00Z",
                        "stale_after": "2026-05-15T12:15:00Z",
                        "watermark_basis": "source_index",
                        "status_reason": "latest indexed corpus timestamp is inside policy",
                    }
                )

    def test_record_rejects_package_generation_marked_fresh(self):
        with TemporaryDirectory() as directory:
            runtime = SourceFreshnessRuntime(StateStoreBundle(Path(directory)))

            with self.assertRaisesRegex(ValueError, "fresh cannot be proven by package_generation"):
                runtime.record(
                    {
                        "company_ref": "company.sampleco",
                        "connector_ref": "connector.sampleco.state_system",
                        "source_ref": "state-system-company:company.sampleco",
                        "connector_type": "state_system_instance",
                        "status": "fresh",
                        "checked_at": "2026-05-15T12:00:00Z",
                        "source_watermark": "state_system_company.sampleco.generated_at:2026-05-15T11:59:00Z",
                        "stale_after": "2026-05-15T12:15:00Z",
                        "watermark_basis": "package_generation",
                        "latest_indexed_at": "2026-05-15T11:59:00Z",
                        "status_reason": "package was generated recently",
                    }
                )

    def test_cli_records_lists_and_exports_source_freshness(self):
        with TemporaryDirectory() as directory, TemporaryDirectory() as output_dir:
            output = StringIO()
            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "source-freshness-record",
                    "--company-ref",
                    "company.sampleco",
                    "--connector-ref",
                    "connector.sampleco.kb",
                    "--source-ref",
                    "kb:tenant:sampleco",
                    "--connector-type",
                    "kb",
                    "--status",
                    "fresh",
                    "--checked-at",
                    "2026-05-15T12:00:00Z",
                    "--source-watermark",
                    "kb.indexed_at:2026-05-15T11:59:00Z",
                    "--stale-after",
                    "2026-05-15T12:15:00Z",
                    "--watermark-basis",
                    "source_index",
                    "--latest-indexed-at",
                    "2026-05-15T11:59:00Z",
                    "--status-reason",
                    "latest indexed corpus timestamp is inside policy",
                    "--lag-seconds",
                    "60",
                    "--evidence-ref",
                    "agent-runtime:freshness:kb:company.sampleco:20260515T120000Z",
                    "--detail",
                    "Knowledge Store tenant sampleco freshness checked.",
                ],
                stdout=output,
            )

            self.assertEqual(0, code, output.getvalue())
            payload = json.loads(output.getvalue())
            self.assertEqual("fresh", payload["source_freshness"]["status"])
            self.assertEqual("source_index", payload["source_freshness"]["watermark_basis"])

            list_output = StringIO()
            list_code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "source-freshness-list",
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
                    "source-freshness-export",
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
