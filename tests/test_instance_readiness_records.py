from __future__ import annotations

from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.contracts import load_json, validate_schema
from state_system.instance_capability import InstanceCapabilityRuntime
from state_system.instance_preflight import (
    InstancePreflightRuntime,
    build_instance_preflight_read_model,
)
from state_system.instance_source_freshness import (
    InstanceSourceFreshnessRuntime,
    build_instance_source_freshness_read_model,
)
from state_system.instance_understanding_surface import (
    build_instance_understanding_surface_read_model,
)
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = ROOT / "examples" / "instance-capability"


class InstanceReadinessRecordTests(unittest.TestCase):
    def test_instance_preflight_record_normalizes_and_validates(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            record = InstancePreflightRuntime(stores).record(
                {
                    "preflight_ref": "preflight.personal.agentmem",
                    "instance_ref": "state_instance.braydon_personal",
                    "connector_ref": "connector.personal.agentmem",
                    "source_ref": "agentmem:tenant:braydon",
                    "status": "passed",
                    "checked_at": "2026-05-16T20:00:00Z",
                    "stale_after": "2026-05-16T21:00:00Z",
                    "evidence_refs": ["paia:preflight:agentmem:tenant:braydon"],
                }
            )

            schema = load_json(ROOT / "schemas" / "instance-preflight-result.schema.json")
            errors = validate_schema(record, schema)
            read_model = build_instance_preflight_read_model(stores)

        self.assertEqual([], errors)
        self.assertEqual("state_instance.braydon_personal", record["instance_ref"])
        self.assertEqual("connector.personal.agentmem", record["connector_ref"])
        self.assertEqual("agentmem:tenant:braydon", record["source_ref"])
        self.assertTrue(record["proves_live_access"])
        self.assertFalse(record["authorizes_execution"])
        self.assertEqual("instance_preflight_result_read_model", read_model["id"])
        self.assertEqual(record["id"], read_model["latest_by_scope_key"][record["scope_key"]]["id"])
        self.assertEqual(
            record["id"],
            read_model["latest_by_preflight_ref"]["preflight.personal.agentmem"]["id"],
        )

    def test_instance_freshness_record_normalizes_and_validates(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            record = InstanceSourceFreshnessRuntime(stores).record(
                {
                    "instance_ref": "state_instance.braydon_personal",
                    "connector_ref": "connector.personal.msgvault",
                    "source_ref": "msgvault:account:gmail",
                    "connector_type": "msgvault",
                    "status": "fresh",
                    "checked_at": "2026-05-16T20:01:00Z",
                    "source_watermark": "msgvault.synced_at:2026-05-16T19:59:00Z",
                    "stale_after": "2026-05-16T20:16:00Z",
                    "lag_seconds": 120,
                    "evidence_refs": ["paia:freshness:msgvault:gmail"],
                }
            )

            schema = load_json(
                ROOT / "schemas" / "instance-source-freshness-record.schema.json"
            )
            errors = validate_schema(record, schema)
            read_model = build_instance_source_freshness_read_model(stores)

        self.assertEqual([], errors)
        self.assertTrue(record["freshness_is_recency_evidence"])
        self.assertFalse(record["proves_live_access"])
        self.assertEqual("instance_source_freshness_read_model", read_model["id"])
        self.assertEqual(record["id"], read_model["latest_by_scope_key"][record["scope_key"]]["id"])

    def test_instance_understanding_surface_consumes_readiness_records(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            InstanceCapabilityRuntime(stores).seed(
                [load_json(PACK_DIR / "instance-braydon-personal.json")]
            )
            InstancePreflightRuntime(stores).record(
                {
                    "preflight_ref": "preflight.personal.agentmem",
                    "instance_ref": "state_instance.braydon_personal",
                    "connector_ref": "connector.personal.agentmem",
                    "source_ref": "agentmem:tenant:braydon",
                    "status": "passed",
                    "checked_at": "2026-05-16T20:00:00Z",
                    "stale_after": "2026-05-16T21:00:00Z",
                    "evidence_refs": ["paia:preflight:agentmem:tenant:braydon"],
                }
            )
            InstanceSourceFreshnessRuntime(stores).record(
                {
                    "instance_ref": "state_instance.braydon_personal",
                    "connector_ref": "connector.personal.agentmem",
                    "source_ref": "agentmem:tenant:braydon",
                    "connector_type": "agentmem",
                    "status": "fresh",
                    "checked_at": "2026-05-16T20:01:00Z",
                    "source_watermark": "agentmem.updated_at:2026-05-16T20:00:30Z",
                    "stale_after": "2026-05-16T20:16:00Z",
                    "evidence_refs": ["paia:freshness:agentmem:tenant:braydon"],
                }
            )

            read_model = build_instance_understanding_surface_read_model(stores)

        personal = read_model["instances"][0]
        agentmem = next(
            source
            for source in personal["source_readiness"]
            if source["connector_ref"] == "connector.personal.agentmem"
        )
        self.assertEqual("passed", agentmem["access_status"])
        self.assertEqual("fresh", agentmem["freshness_status"])
        self.assertEqual("ready", agentmem["understanding_status"])
        self.assertEqual(1, len(agentmem["preflight_records"]))
        self.assertEqual("fresh", agentmem["freshness_record"]["status"])
        self.assertNotIn(
            "gap.state_instance.braydon_personal.connector.personal.agentmem.access_missing",
            read_model["source_gap_refs"],
        )

    def test_cli_records_and_exports_instance_readiness(self):
        with TemporaryDirectory() as directory, TemporaryDirectory() as output_dir:
            preflight_output = StringIO()
            preflight_code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "instance-preflight-record",
                    "--preflight-ref",
                    "preflight.personal.agentmem",
                    "--instance-ref",
                    "state_instance.braydon_personal",
                    "--connector-ref",
                    "connector.personal.agentmem",
                    "--source-ref",
                    "agentmem:tenant:braydon",
                    "--status",
                    "passed",
                    "--checked-at",
                    "2026-05-16T20:00:00Z",
                    "--stale-after",
                    "2026-05-16T21:00:00Z",
                    "--evidence-ref",
                    "paia:preflight:agentmem:tenant:braydon",
                ],
                stdout=preflight_output,
            )

            export_output = StringIO()
            export_code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "instance-preflight-export",
                    "--output-dir",
                    output_dir,
                ],
                stdout=export_output,
            )

            self.assertEqual(0, preflight_code, preflight_output.getvalue())
            self.assertEqual(0, export_code, export_output.getvalue())
            payload = json.loads(export_output.getvalue())
            read_model_path = Path(payload["read_model_path"])
            read_model = json.loads(read_model_path.read_text(encoding="utf-8"))
            self.assertEqual("instance_preflight_result_read_model", read_model["id"])
            self.assertEqual(1, len(read_model["results"]))


if __name__ == "__main__":
    unittest.main()
