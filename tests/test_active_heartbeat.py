from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.company_capability import CompanyCapabilityRuntime
from state_system.contracts import load_json
from state_system.heartbeat import run_source_heartbeat
from state_system.source_freshness import build_source_freshness_read_model
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = ROOT / "examples" / "company-capability"


class ActiveHeartbeatTests(unittest.TestCase):
    def test_heartbeat_records_local_path_freshness_and_delegated_unknowns(self):
        with TemporaryDirectory() as state_dir, TemporaryDirectory() as local_dir:
            stores = StateStoreBundle(Path(state_dir))
            pack = _sampleco_pack_with_local_path(Path(local_dir))
            CompanyCapabilityRuntime(stores).seed([pack])

            summary = run_source_heartbeat(
                stores,
                company_ref="company.sampleco",
                checked_at="2026-05-15T13:00:00Z",
                stale_after="2026-05-15T13:15:00Z",
                output_dir=Path(state_dir) / "source-freshness",
            )

            self.assertEqual("source_heartbeat.company.sampleco", summary["id"])
            self.assertEqual("company.sampleco", summary["company_ref"])
            self.assertEqual(9, summary["recorded"])
            self.assertEqual(2, summary["status_counts"]["fresh"])
            self.assertEqual(7, summary["status_counts"]["unknown"])

            read_model = build_source_freshness_read_model(stores)
            local = _latest(read_model, "connector.sampleco.local")
            self.assertEqual("fresh", local["status"])
            self.assertEqual("local_path", local["connector_type"])
            self.assertEqual(f"local:{local_dir}", local["source_ref"])
            self.assertIn("local.mtime_ns:", local["source_watermark"])
            self.assertFalse(local["proves_live_access"])

            kb = _latest(read_model, "connector.sampleco.kb")
            self.assertEqual("unknown", kb["status"])
            self.assertEqual("delegated:not_checked", kb["source_watermark"])
            self.assertEqual("delegated_connector", kb["error"]["code"])

            zulip = _latest(read_model, "connector.sampleco.zulip")
            self.assertEqual("unknown", zulip["status"])
            self.assertEqual("zulip", zulip["connector_type"])
            self.assertEqual("zulip:realm:sampleco", zulip["source_ref"])
            self.assertEqual("delegated_connector", zulip["error"]["code"])

            github = _latest(read_model, "connector.sampleco.github_org")
            self.assertEqual("unknown", github["status"])
            self.assertEqual("repo", github["connector_type"])
            self.assertEqual("github:org:SampleCo-Org", github["source_ref"])
            self.assertEqual("delegated_connector", github["error"]["code"])

            transcripts_raw = _latest(read_model, "connector.sampleco.transcripts.raw")
            self.assertEqual("fresh", transcripts_raw["status"])
            self.assertEqual("local_path", transcripts_raw["connector_type"])
            self.assertEqual(f"local:{local_dir}", transcripts_raw["source_ref"])

            transcripts_processed = _latest(
                read_model,
                "connector.sampleco.transcripts.processed",
            )
            self.assertEqual("unknown", transcripts_processed["status"])
            self.assertEqual("docs", transcripts_processed["connector_type"])
            self.assertEqual("transcripts:pipeline:sampleco", transcripts_processed["source_ref"])
            self.assertEqual(
                "delegated_connector",
                transcripts_processed["error"]["code"],
            )

    def test_heartbeat_records_failed_local_path_when_missing(self):
        with TemporaryDirectory() as state_dir:
            stores = StateStoreBundle(Path(state_dir))
            missing_path = Path(state_dir) / "missing"
            pack = _sampleco_pack_with_local_path(missing_path)
            CompanyCapabilityRuntime(stores).seed([pack])

            run_source_heartbeat(
                stores,
                company_ref="company.sampleco",
                checked_at="2026-05-15T13:00:00Z",
                stale_after="2026-05-15T13:15:00Z",
                output_dir=Path(state_dir) / "source-freshness",
            )

            read_model = build_source_freshness_read_model(stores)
            local = _latest(read_model, "connector.sampleco.local")

            self.assertEqual("failed", local["status"])
            self.assertEqual("local.path_missing", local["source_watermark"])
            self.assertEqual("path_missing", local["error"]["code"])

    def test_cli_runs_source_heartbeat_and_exports_read_model(self):
        with TemporaryDirectory() as state_dir, TemporaryDirectory() as local_dir:
            stores = StateStoreBundle(Path(state_dir))
            CompanyCapabilityRuntime(stores).seed(
                [_sampleco_pack_with_local_path(Path(local_dir))]
            )
            output_dir = Path(state_dir) / "source-freshness"

            output = StringIO()
            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    state_dir,
                    "source-heartbeat-run",
                    "--company-ref",
                    "company.sampleco",
                    "--checked-at",
                    "2026-05-15T13:00:00Z",
                    "--stale-after",
                    "2026-05-15T13:15:00Z",
                    "--output-dir",
                    str(output_dir),
                ],
                stdout=output,
            )

            self.assertEqual(0, code, output.getvalue())
            payload = json.loads(output.getvalue())
            self.assertEqual(9, payload["recorded"])
            read_model_path = Path(payload["read_model_path"])
            self.assertEqual(
                output_dir / "source-freshness-read-model.json",
                read_model_path,
            )
            read_model = json.loads(read_model_path.read_text(encoding="utf-8"))
            self.assertEqual(9, len(read_model["results"]))


def _sampleco_pack_with_local_path(path: Path):
    pack = load_json(PACK_DIR / "company-sampleco.json")
    source_ref = f"local:{path}"
    for connector in pack["source_connectors"]:
        if connector["id"] in {
            "connector.sampleco.local",
            "connector.sampleco.transcripts.raw",
        }:
            connector["source_ref"] = source_ref
    pack["raw_corpus"]["source_refs"] = [
        source_ref if value.startswith("local:") else value
        for value in pack["raw_corpus"]["source_refs"]
    ]
    return pack


def _latest(read_model, connector_ref):
    return next(
        record
        for record in read_model["latest_by_scope_key"].values()
        if record["connector_ref"] == connector_ref
    )


if __name__ == "__main__":
    unittest.main()
