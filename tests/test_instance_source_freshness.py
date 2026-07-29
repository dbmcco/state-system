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
    / "instance-source-freshness-sample-personal-msgvault.json"
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
                    "instance_ref": "state_instance.sample_personal",
                    "connector_ref": "connector.personal.msgvault",
                    "source_ref": "msgvault:tenant:personal-email",
                    "connector_type": "msgvault",
                    "status": "unknown",
                    "checked_at": "2026-05-17T10:15:00Z",
                    "source_watermark": "msgvault.sync_status:unknown;source_status=unavailable",
                    "stale_after": "2026-05-17T10:30:00Z",
                    "watermark_basis": "declared_gap",
                    "status_reason": "msgvault output is unavailable, so source freshness is unknown",
                    "evidence_refs": ["agent-runtime:freshness:msgvault:unknown"],
                    "index_refs": ["index.personal.msgvault.email"],
                    "index_metadata": {
                        "owner": "source_system",
                        "backend": "msgvault_sqlite_vec",
                    },
                }
            )

            self.assertEqual(
                "state_instance.sample_personal|connector.personal.msgvault|"
                "msgvault:tenant:personal-email|declared_gap",
                record["scope_key"],
            )
            self.assertTrue(
                record["id"].startswith(
                    "instance_source_freshness.state_instance.sample_personal"
                )
            )
            self.assertTrue(record["freshness_is_recency_evidence"])
            self.assertFalse(record["proves_live_access"])
            self.assertFalse(record["authorizes_execution"])
            self.assertEqual("msgvault_sqlite_vec", record["index_metadata"]["backend"])
            self.assertEqual(record, runtime.read(record["id"]))

    def test_record_preserves_typed_corpus_and_index_watermark_metadata(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            runtime = InstanceSourceFreshnessRuntime(stores)

            record = runtime.record(
                {
                    "instance_ref": "state_instance.sample_personal",
                    "connector_ref": "connector.personal.msgvault",
                    "source_ref": "msgvault:tenant:personal-email",
                    "connector_type": "msgvault",
                    "status": "fresh",
                    "checked_at": "2026-05-17T10:15:00Z",
                    "source_watermark": "msgvault.latest_sent_at:2026-05-17T10:12:00Z",
                    "stale_after": "2026-05-17T10:30:00Z",
                    "watermark_basis": "source_content",
                    "latest_source_event_at": "2026-05-17T10:12:00Z",
                    "latest_source_modified_at": "2026-05-17T10:12:00Z",
                    "latest_indexed_at": "2026-05-17T10:14:00Z",
                    "source_item_count": 1204,
                    "index_item_count": 1204,
                    "freshness_policy_ref": "source_module.msgvault.freshness",
                    "status_reason": "latest indexed message is inside policy window",
                    "content_stale_after": "2026-05-19T10:12:00Z",
                    "index_stale_after": "2026-05-17T11:14:00Z",
                    "probe_stale_after": "2026-05-17T10:45:00Z",
                    "evidence_refs": ["agent-runtime:freshness:msgvault:fresh"],
                }
            )

            errors = validate_schema(
                record,
                load_json(ROOT / "schemas" / "instance-source-freshness-record.schema.json"),
            )

            self.assertEqual([], errors)
            self.assertEqual("source_content", record["watermark_basis"])
            self.assertEqual("2026-05-17T10:12:00Z", record["latest_source_event_at"])
            self.assertEqual(1204, record["source_item_count"])

    def test_record_rejects_fresh_probe_only_status(self):
        with TemporaryDirectory() as directory:
            runtime = InstanceSourceFreshnessRuntime(StateStoreBundle(Path(directory)))

            with self.assertRaisesRegex(ValueError, "fresh cannot be proven by probe_only"):
                runtime.record(
                    {
                        "instance_ref": "state_instance.sample_personal",
                        "connector_ref": "connector.personal.workboard",
                        "source_ref": "paia-workboard:default",
                        "connector_type": "workboard",
                        "status": "fresh",
                        "checked_at": "2026-05-17T10:15:00Z",
                        "source_watermark": "workboard.checked_at:2026-05-17T10:15:00Z;corpus_watermark=unproven",
                        "stale_after": "2026-05-17T11:15:00Z",
                        "watermark_basis": "probe_only",
                        "status_reason": "connector health was checked but corpus freshness is unproven",
                    }
                )

    def test_record_rejects_source_content_without_source_timestamp(self):
        with TemporaryDirectory() as directory:
            runtime = InstanceSourceFreshnessRuntime(StateStoreBundle(Path(directory)))

            with self.assertRaisesRegex(ValueError, "source_content.*latest_source_modified_at"):
                runtime.record(
                    {
                        "instance_ref": "state_instance.sample_personal",
                        "connector_ref": "connector.personal.msgvault",
                        "source_ref": "msgvault:tenant:personal-email",
                        "connector_type": "msgvault",
                        "status": "fresh",
                        "checked_at": "2026-05-17T10:15:00Z",
                        "source_watermark": "msgvault.latest_sent_at:2026-05-17T10:12:00Z",
                        "stale_after": "2026-05-19T10:12:00Z",
                        "watermark_basis": "source_content",
                        "status_reason": "latest source content timestamp is inside policy",
                    }
                )

    def test_record_rejects_source_content_with_event_only_watermark(self):
        with TemporaryDirectory() as directory:
            runtime = InstanceSourceFreshnessRuntime(StateStoreBundle(Path(directory)))

            with self.assertRaisesRegex(ValueError, "source_content.*latest_source_modified_at"):
                runtime.record(
                    {
                        "instance_ref": "state_instance.sample_personal",
                        "connector_ref": "connector.personal.msgvault",
                        "source_ref": "msgvault:tenant:personal-email",
                        "connector_type": "msgvault",
                        "status": "stale",
                        "checked_at": "2026-05-17T10:15:00Z",
                        "source_watermark": "msgvault.latest_sent_at:2026-05-17T10:12:00Z",
                        "stale_after": "2026-05-17T10:30:00Z",
                        "watermark_basis": "source_content",
                        "latest_source_event_at": "2026-05-17T10:12:00Z",
                        "status_reason": "event time alone is ambiguous for a source_content watermark",
                    }
                )

    def test_record_rejects_package_generation_marked_fresh(self):
        with TemporaryDirectory() as directory:
            runtime = InstanceSourceFreshnessRuntime(StateStoreBundle(Path(directory)))

            with self.assertRaisesRegex(ValueError, "fresh cannot be proven by package_generation"):
                runtime.record(
                    {
                        "instance_ref": "state_instance.sample_personal",
                        "connector_ref": "connector.personal.lfw_state_system",
                        "source_ref": "state-system-instance:state_instance.lfw",
                        "connector_type": "state_system_instance",
                        "status": "fresh",
                        "checked_at": "2026-05-17T10:15:00Z",
                        "source_watermark": "state_system_instance.lfw.generated_at:2026-05-17T10:14:00Z",
                        "stale_after": "2026-05-17T11:15:00Z",
                        "watermark_basis": "package_generation",
                        "latest_indexed_at": "2026-05-17T10:14:00Z",
                        "status_reason": "package was generated recently",
                    }
                )

    def test_read_model_exports_latest_freshness_by_scope_key(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            runtime = InstanceSourceFreshnessRuntime(stores)
            base = {
                "instance_ref": "state_instance.sample_personal",
                "connector_ref": "connector.personal.kb",
                "source_ref": "kb:tenant:personal",
                "connector_type": "kb",
                "stale_after": "2026-05-17T10:30:00Z",
            }
            runtime.record(
                {
                    **base,
                    "status": "stale",
                    "checked_at": "2026-05-17T10:00:00Z",
                    "source_watermark": "kb.indexed_at:2026-05-17T08:00:00Z",
                    "watermark_basis": "source_index",
                    "latest_indexed_at": "2026-05-17T08:00:00Z",
                    "status_reason": "latest indexed corpus timestamp is outside policy",
                    "lag_seconds": 7200,
                    "evidence_refs": ["agent-runtime:freshness:kb:stale"],
                }
            )
            runtime.record(
                {
                    **base,
                    "status": "fresh",
                    "checked_at": "2026-05-17T10:15:00Z",
                    "source_watermark": "kb.indexed_at:2026-05-17T10:14:00Z",
                    "watermark_basis": "source_index",
                    "latest_indexed_at": "2026-05-17T10:14:00Z",
                    "status_reason": "latest indexed corpus timestamp is inside policy",
                    "lag_seconds": 60,
                    "evidence_refs": ["agent-runtime:freshness:kb:fresh"],
                }
            )

            read_model = build_instance_source_freshness_read_model(stores)

            self.assertEqual("instance_source_freshness_read_model", read_model["id"])
            scope_key = (
                "state_instance.sample_personal|connector.personal.kb|"
                "kb:tenant:personal|source_index"
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
                    "state_instance.sample_personal",
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
                    "--watermark-basis",
                    "probe_only",
                    "--status-reason",
                    "account list was checked but source/corpus freshness is unproven because corpus timestamp is unavailable",
                    "--evidence-ref",
                    "agent-runtime:freshness:msgvault:unknown",
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
            self.assertEqual("probe_only", payload["source_freshness"]["watermark_basis"])
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

    def test_record_rejects_source_event_without_latest_source_event_at(self):
        with TemporaryDirectory() as directory:
            runtime = InstanceSourceFreshnessRuntime(StateStoreBundle(Path(directory)))

            with self.assertRaisesRegex(ValueError, "source_event.*latest_source_event_at"):
                runtime.record(
                    {
                        "instance_ref": "state_instance.sampleco",
                        "connector_ref": "connector.sampleco.linear",
                        "source_ref": "linear:teams:FORGE,INT",
                        "connector_type": "linear",
                        "status": "fresh",
                        "checked_at": "2026-05-17T10:15:00Z",
                        "source_watermark": "linear.latest_updated_at:2026-05-17T10:12:00Z",
                        "stale_after": "2026-05-17T10:30:00Z",
                        "watermark_basis": "source_event",
                        "status_reason": "latest source event timestamp is inside policy",
                    }
                )

    def test_record_rejects_remote_head_without_latest_remote_head_at(self):
        with TemporaryDirectory() as directory:
            runtime = InstanceSourceFreshnessRuntime(StateStoreBundle(Path(directory)))

            with self.assertRaisesRegex(ValueError, "remote_head.*latest_remote_head_at"):
                runtime.record(
                    {
                        "instance_ref": "state_instance.sampleco",
                        "connector_ref": "connector.sampleco.repo",
                        "source_ref": "github:repo:SampleCo-Org/state-system",
                        "connector_type": "repo",
                        "status": "fresh",
                        "checked_at": "2026-05-17T10:15:00Z",
                        "source_watermark": "github.remote_head:2026-05-17T10:14:00Z",
                        "stale_after": "2026-05-17T10:30:00Z",
                        "watermark_basis": "remote_head",
                        "status_reason": "remote HEAD is recent",
                    }
                )

    def test_record_rejects_local_checkout_without_latest_local_checkout_at(self):
        with TemporaryDirectory() as directory:
            runtime = InstanceSourceFreshnessRuntime(StateStoreBundle(Path(directory)))

            with self.assertRaisesRegex(ValueError, "local_checkout.*latest_local_checkout_at"):
                runtime.record(
                    {
                        "instance_ref": "state_instance.sampleco",
                        "connector_ref": "connector.sampleco.repo",
                        "source_ref": "github:repo:SampleCo-Org/state-system",
                        "connector_type": "repo",
                        "status": "stale",
                        "checked_at": "2026-05-17T10:15:00Z",
                        "source_watermark": "local.checkout_mtime:2026-05-17T08:00:00Z",
                        "stale_after": "2026-05-17T10:30:00Z",
                        "watermark_basis": "local_checkout",
                        "status_reason": "local checkout lags remote HEAD",
                    }
                )

    def test_record_rejects_sync_index_without_latest_sync_index_at(self):
        with TemporaryDirectory() as directory:
            runtime = InstanceSourceFreshnessRuntime(StateStoreBundle(Path(directory)))

            with self.assertRaisesRegex(ValueError, "sync_index.*latest_sync_index_at"):
                runtime.record(
                    {
                        "instance_ref": "state_instance.sampleco",
                        "connector_ref": "connector.sampleco.gws_drive",
                        "source_ref": "gws:sampleco:drive:sampleco",
                        "connector_type": "gws_drive",
                        "status": "fresh",
                        "checked_at": "2026-05-17T10:15:00Z",
                        "source_watermark": "gws_drive.sync_index:2026-05-17T10:14:00Z",
                        "stale_after": "2026-05-17T10:30:00Z",
                        "watermark_basis": "sync_index",
                        "status_reason": "sync index is recent",
                    }
                )

    def test_record_rejects_remote_corpus_without_latest_remote_corpus_at(self):
        with TemporaryDirectory() as directory:
            runtime = InstanceSourceFreshnessRuntime(StateStoreBundle(Path(directory)))

            with self.assertRaisesRegex(ValueError, "remote_corpus.*latest_remote_corpus_at"):
                runtime.record(
                    {
                        "instance_ref": "state_instance.sampleco",
                        "connector_ref": "connector.sampleco.gws_drive",
                        "source_ref": "gws:sampleco:drive:sampleco",
                        "connector_type": "gws_drive",
                        "status": "fresh",
                        "checked_at": "2026-05-17T10:15:00Z",
                        "source_watermark": "gws_drive.remote_corpus_max_modified:2026-05-17T10:14:00Z",
                        "stale_after": "2026-05-17T10:30:00Z",
                        "watermark_basis": "remote_corpus",
                        "status_reason": "remote corpus is recent",
                    }
                )

    def test_record_accepts_remote_head_repo_watermark(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            runtime = InstanceSourceFreshnessRuntime(stores)

            record = runtime.record(
                {
                    "instance_ref": "state_instance.sampleco",
                    "connector_ref": "connector.sampleco.repo",
                    "source_ref": "github:repo:SampleCo-Org/state-system",
                    "connector_type": "repo",
                    "status": "fresh",
                    "checked_at": "2026-05-17T10:15:00Z",
                    "source_watermark": "github.remote_head:2026-05-17T10:14:00Z",
                    "stale_after": "2026-05-17T10:30:00Z",
                    "watermark_basis": "remote_head",
                    "latest_remote_head_at": "2026-05-17T10:14:00Z",
                    "status_reason": "remote HEAD is inside policy",
                    "evidence_refs": ["agent-runtime:freshness:repo:remote_head"],
                }
            )

            self.assertEqual("remote_head", record["watermark_basis"])
            self.assertEqual("2026-05-17T10:14:00Z", record["latest_remote_head_at"])
            self.assertEqual([], validate_schema(record, load_json(ROOT / "schemas" / "instance-source-freshness-record.schema.json")))

    def test_record_accepts_local_checkout_lagging_remote_head(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            runtime = InstanceSourceFreshnessRuntime(stores)

            record = runtime.record(
                {
                    "instance_ref": "state_instance.sampleco",
                    "connector_ref": "connector.sampleco.repo",
                    "source_ref": "github:repo:SampleCo-Org/state-system",
                    "connector_type": "repo",
                    "status": "stale",
                    "checked_at": "2026-05-17T10:15:00Z",
                    "source_watermark": "local.checkout_commit:2026-05-17T08:00:00Z;remote_head:2026-05-17T10:14:00Z",
                    "stale_after": "2026-05-17T10:30:00Z",
                    "watermark_basis": "local_checkout",
                    "latest_local_checkout_at": "2026-05-17T08:00:00Z",
                    "latest_remote_head_at": "2026-05-17T10:14:00Z",
                    "lag_seconds": 8100,
                    "watermark_lag_seconds": 8040,
                    "status_reason": "local checkout HEAD lags remote HEAD; checked_at proves adapter ran, not corpus current",
                    "evidence_refs": ["agent-runtime:freshness:repo:local_checkout"],
                }
            )

            self.assertEqual("local_checkout", record["watermark_basis"])
            self.assertEqual("2026-05-17T08:00:00Z", record["latest_local_checkout_at"])
            self.assertEqual(8100, record["lag_seconds"])
            self.assertEqual(8040, record["watermark_lag_seconds"])
            self.assertEqual([], validate_schema(record, load_json(ROOT / "schemas" / "instance-source-freshness-record.schema.json")))

    def test_record_accepts_sync_index_lagging_remote_corpus(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            runtime = InstanceSourceFreshnessRuntime(stores)

            record = runtime.record(
                {
                    "instance_ref": "state_instance.sampleco",
                    "connector_ref": "connector.sampleco.gws_drive",
                    "source_ref": "gws:sampleco:drive:sampleco",
                    "connector_type": "gws_drive",
                    "status": "stale",
                    "checked_at": "2026-05-17T10:15:00Z",
                    "source_watermark": "gws_drive.sync_index:2026-05-17T08:00:00Z;remote_corpus_max:2026-05-17T10:14:00Z",
                    "stale_after": "2026-05-17T10:30:00Z",
                    "watermark_basis": "sync_index",
                    "latest_sync_index_at": "2026-05-17T08:00:00Z",
                    "latest_remote_corpus_at": "2026-05-17T10:14:00Z",
                    "lag_seconds": 8100,
                    "watermark_lag_seconds": 8040,
                    "status_reason": "sync index lags remote corpus; checked_at proves adapter ran, not corpus current",
                    "evidence_refs": ["agent-runtime:freshness:gws_drive:sync_index"],
                }
            )

            self.assertEqual("sync_index", record["watermark_basis"])
            self.assertEqual("2026-05-17T08:00:00Z", record["latest_sync_index_at"])
            self.assertEqual(8100, record["lag_seconds"])
            self.assertEqual(8040, record["watermark_lag_seconds"])
            self.assertEqual([], validate_schema(record, load_json(ROOT / "schemas" / "instance-source-freshness-record.schema.json")))

    def test_record_accepts_remote_corpus_watermark(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            runtime = InstanceSourceFreshnessRuntime(stores)

            record = runtime.record(
                {
                    "instance_ref": "state_instance.sampleco",
                    "connector_ref": "connector.sampleco.gws_drive",
                    "source_ref": "gws:sampleco:drive:sampleco",
                    "connector_type": "gws_drive",
                    "status": "fresh",
                    "checked_at": "2026-05-17T10:15:00Z",
                    "source_watermark": "gws_drive.remote_corpus_max_modified:2026-05-17T10:14:00Z",
                    "stale_after": "2026-05-17T10:30:00Z",
                    "watermark_basis": "remote_corpus",
                    "latest_remote_corpus_at": "2026-05-17T10:14:00Z",
                    "status_reason": "remote corpus max modified time is inside policy",
                    "evidence_refs": ["agent-runtime:freshness:gws_drive:remote_corpus"],
                }
            )

            self.assertEqual("remote_corpus", record["watermark_basis"])
            self.assertEqual("2026-05-17T10:14:00Z", record["latest_remote_corpus_at"])
            self.assertEqual([], validate_schema(record, load_json(ROOT / "schemas" / "instance-source-freshness-record.schema.json")))

    def test_cli_records_repo_remote_head_and_local_checkout_watermarks(self):
        with TemporaryDirectory() as directory:
            output = StringIO()
            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "instance-source-freshness-record",
                    "--instance-ref",
                    "state_instance.sampleco",
                    "--connector-ref",
                    "connector.sampleco.repo",
                    "--source-ref",
                    "github:repo:SampleCo-Org/state-system",
                    "--connector-type",
                    "repo",
                    "--status",
                    "stale",
                    "--checked-at",
                    "2026-05-17T10:15:00Z",
                    "--source-watermark",
                    "local.checkout_commit:2026-05-17T08:00:00Z;remote_head:2026-05-17T10:14:00Z",
                    "--stale-after",
                    "2026-05-17T10:30:00Z",
                    "--watermark-basis",
                    "local_checkout",
                    "--latest-local-checkout-at",
                    "2026-05-17T08:00:00Z",
                    "--latest-remote-head-at",
                    "2026-05-17T10:14:00Z",
                    "--lag-seconds",
                    "8100",
                    "--watermark-lag-seconds",
                    "8040",
                    "--status-reason",
                    "local checkout lags remote HEAD; checked_at proves adapter ran, not corpus current",
                    "--evidence-ref",
                    "agent-runtime:freshness:repo:local_checkout",
                ],
                stdout=output,
            )

            self.assertEqual(0, code, output.getvalue())
            payload = json.loads(output.getvalue())
            self.assertEqual("local_checkout", payload["source_freshness"]["watermark_basis"])
            self.assertEqual("2026-05-17T08:00:00Z", payload["source_freshness"]["latest_local_checkout_at"])
            self.assertEqual("2026-05-17T10:14:00Z", payload["source_freshness"]["latest_remote_head_at"])
            self.assertEqual(8100, payload["source_freshness"]["lag_seconds"])
            self.assertEqual(8040, payload["source_freshness"]["watermark_lag_seconds"])
            self.assertEqual("2026-05-17T10:14:00Z", payload["source_freshness"]["latest_remote_head_at"])

    def test_both_repo_bases_at_same_checked_at_produce_distinct_records(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            runtime = InstanceSourceFreshnessRuntime(stores)
            base = {
                "instance_ref": "state_instance.sampleco",
                "connector_ref": "connector.sampleco.repo",
                "source_ref": "github:repo:SampleCo-Org/state-system",
                "connector_type": "repo",
                "checked_at": "2026-05-17T10:15:00Z",
                "stale_after": "2026-05-17T10:30:00Z",
                "status_reason": "repo watermark basis disambiguation",
            }
            remote_head = runtime.record(
                {
                    **base,
                    "status": "fresh",
                    "source_watermark": "github.remote_head:2026-05-17T10:14:00Z",
                    "watermark_basis": "remote_head",
                    "latest_remote_head_at": "2026-05-17T10:14:00Z",
                    "evidence_refs": ["agent-runtime:freshness:repo:remote_head"],
                }
            )
            local_checkout = runtime.record(
                {
                    **base,
                    "status": "stale",
                    "source_watermark": "local.checkout_commit:2026-05-17T08:00:00Z;remote_head:2026-05-17T10:14:00Z",
                    "watermark_basis": "local_checkout",
                    "latest_local_checkout_at": "2026-05-17T08:00:00Z",
                    "latest_remote_head_at": "2026-05-17T10:14:00Z",
                    "lag_seconds": 8100,
                    "watermark_lag_seconds": 8040,
                    "evidence_refs": ["agent-runtime:freshness:repo:local_checkout"],
                }
            )

            self.assertNotEqual(remote_head["id"], local_checkout["id"])
            self.assertNotEqual(remote_head["scope_key"], local_checkout["scope_key"])
            read_model = build_instance_source_freshness_read_model(stores)
            self.assertEqual(2, len(read_model["results"]))
            self.assertEqual(2, len(read_model["latest_by_scope_key"]))

    def test_record_rejects_fresh_local_checkout_that_lags_remote_head(self):
        with TemporaryDirectory() as directory:
            runtime = InstanceSourceFreshnessRuntime(StateStoreBundle(Path(directory)))

            with self.assertRaisesRegex(ValueError, "local_checkout cannot be fresh when the local checkout lags remote HEAD"):
                runtime.record(
                    {
                        "instance_ref": "state_instance.sampleco",
                        "connector_ref": "connector.sampleco.repo",
                        "source_ref": "github:repo:SampleCo-Org/state-system",
                        "connector_type": "repo",
                        "status": "fresh",
                        "checked_at": "2026-05-17T10:15:00Z",
                        "source_watermark": "local.checkout_commit:2026-05-17T08:00:00Z;remote_head:2026-05-17T10:14:00Z",
                        "stale_after": "2026-05-17T10:30:00Z",
                        "watermark_basis": "local_checkout",
                        "latest_local_checkout_at": "2026-05-17T08:00:00Z",
                        "latest_remote_head_at": "2026-05-17T10:14:00Z",
                        "status_reason": "fresh local checkout that lags remote HEAD",
                    }
                )

    def test_record_rejects_fresh_sync_index_that_lags_remote_corpus(self):
        with TemporaryDirectory() as directory:
            runtime = InstanceSourceFreshnessRuntime(StateStoreBundle(Path(directory)))

            with self.assertRaisesRegex(ValueError, "sync_index cannot be fresh when the sync index lags the remote corpus"):
                runtime.record(
                    {
                        "instance_ref": "state_instance.sampleco",
                        "connector_ref": "connector.sampleco.gws_drive",
                        "source_ref": "gws:sampleco:drive:sampleco",
                        "connector_type": "gws_drive",
                        "status": "fresh",
                        "checked_at": "2026-05-17T10:15:00Z",
                        "source_watermark": "gws_drive.sync_index:2026-05-17T08:00:00Z;remote_corpus_max:2026-05-17T10:14:00Z",
                        "stale_after": "2026-05-17T10:30:00Z",
                        "watermark_basis": "sync_index",
                        "latest_sync_index_at": "2026-05-17T08:00:00Z",
                        "latest_remote_corpus_at": "2026-05-17T10:14:00Z",
                        "status_reason": "fresh sync index that lags remote corpus",
                    }
                )


if __name__ == "__main__":
    unittest.main()
