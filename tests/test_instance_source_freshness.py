from __future__ import annotations

from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.contracts import load_json, schema_for_example, validate_schema
from state_system.instance_source_freshness import (
    InstanceSourceFreshnessRuntime,
    build_instance_source_freshness_read_model,
)
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = (
    ROOT
    / "examples"
    / "instance-source-freshness"
    / "instance-source-freshness-acme-ops-msgvault.json"
)


class InstanceSourceFreshnessTests(unittest.TestCase):
    def test_example_is_schema_validated_as_instance_source_freshness(self):
        schema_name = schema_for_example(EXAMPLE.name)

        self.assertEqual("instance-source-freshness-record.schema.json", schema_name)
        errors = validate_schema(
            load_json(EXAMPLE),
            load_json(ROOT / "schemas" / schema_name),
        )
        self.assertEqual([], errors)

    def test_record_persists_freshness_without_proving_access_or_authority(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            runtime = InstanceSourceFreshnessRuntime(stores)

            record = runtime.record(
                {
                    "instance_ref": "state_instance.acme_ops",
                    "connector_ref": "connector.personal.msgvault",
                    "source_ref": "msgvault:tenant:personal-email",
                    "connector_type": "msgvault",
                    "status": "unknown",
                    "checked_at": "2026-05-17T10:15:00Z",
                    "source_watermark": "msgvault.sync_status:unknown",
                    "stale_after": "2026-05-17T10:30:00Z",
                    "evidence_refs": ["paia:freshness:msgvault:unknown"],
                    "index_refs": ["index.personal.msgvault.email"],
                    "index_metadata": {
                        "owner": "source_system",
                        "backend": "msgvault_sqlite_vec",
                    },
                }
            )

            self.assertEqual(
                "state_instance.acme_ops|connector.personal.msgvault|"
                "msgvault:tenant:personal-email",
                record["scope_key"],
            )
            self.assertTrue(
                record["id"].startswith(
                    "instance_source_freshness.state_instance.acme_ops"
                )
            )
            self.assertTrue(record["freshness_is_recency_evidence"])
            self.assertFalse(record["proves_live_access"])
            self.assertFalse(record["authorizes_execution"])
            self.assertEqual("msgvault_sqlite_vec", record["index_metadata"]["backend"])
            self.assertEqual(record, runtime.read(record["id"]))

    def test_read_model_exports_latest_freshness_by_scope_key(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            runtime = InstanceSourceFreshnessRuntime(stores)
            base = {
                "instance_ref": "state_instance.acme_ops",
                "connector_ref": "connector.personal.folio",
                "source_ref": "folio:tenant:personal",
                "connector_type": "folio",
                "stale_after": "2026-05-17T10:30:00Z",
            }
            runtime.record(
                {
                    **base,
                    "status": "stale",
                    "checked_at": "2026-05-17T10:00:00Z",
                    "source_watermark": "folio.indexed_at:2026-05-17T08:00:00Z",
                    "lag_seconds": 7200,
                    "evidence_refs": ["paia:freshness:folio:stale"],
                }
            )
            runtime.record(
                {
                    **base,
                    "status": "fresh",
                    "checked_at": "2026-05-17T10:15:00Z",
                    "source_watermark": "folio.indexed_at:2026-05-17T10:14:00Z",
                    "lag_seconds": 60,
                    "evidence_refs": ["paia:freshness:folio:fresh"],
                }
            )

            read_model = build_instance_source_freshness_read_model(stores)

            self.assertEqual("instance_source_freshness_read_model", read_model["id"])
            scope_key = (
                "state_instance.acme_ops|connector.personal.folio|"
                "folio:tenant:personal"
            )
            latest = read_model["latest_by_scope_key"][scope_key]
            self.assertEqual("fresh", latest["status"])
            self.assertEqual("2026-05-17T10:15:00Z", latest["checked_at"])
            self.assertTrue(read_model["invariant"]["freshness_is_recency_evidence"])
            self.assertFalse(read_model["invariant"]["proves_live_access"])

    def test_cli_records_lists_and_exports_instance_source_freshness(self):
        with TemporaryDirectory() as directory, TemporaryDirectory() as output_dir:
            output = StringIO()
            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "instance-source-freshness-record",
                    "--instance-ref",
                    "state_instance.acme_ops",
                    "--connector-ref",
                    "connector.personal.msgvault",
                    "--source-ref",
                    "msgvault:tenant:personal-email",
                    "--connector-type",
                    "msgvault",
                    "--status",
                    "unknown",
                    "--checked-at",
                    "2026-05-17T10:15:00Z",
                    "--source-watermark",
                    "msgvault.sync_status:unknown",
                    "--stale-after",
                    "2026-05-17T10:30:00Z",
                    "--evidence-ref",
                    "paia:freshness:msgvault:unknown",
                    "--index-ref",
                    "index.personal.msgvault.email",
                    "--index-owner",
                    "source_system",
                    "--index-backend",
                    "msgvault_sqlite_vec",
                ],
                stdout=output,
            )

            self.assertEqual(0, code, output.getvalue())
            payload = json.loads(output.getvalue())
            self.assertEqual("unknown", payload["source_freshness"]["status"])
            self.assertEqual(
                "msgvault_sqlite_vec",
                payload["source_freshness"]["index_metadata"]["backend"],
            )

            list_output = StringIO()
            list_code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "instance-source-freshness-list",
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
                    "instance-source-freshness-export",
                    "--output-dir",
                    output_dir,
                ],
                stdout=export_output,
            )

            self.assertEqual(0, export_code, export_output.getvalue())
            read_model_path = Path(json.loads(export_output.getvalue())["read_model_path"])
            read_model = json.loads(read_model_path.read_text(encoding="utf-8"))
            self.assertEqual(1, len(read_model["results"]))


if __name__ == "__main__":
    unittest.main()
