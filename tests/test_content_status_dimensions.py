from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system.contracts import load_json, validate_schema
from state_system.instance_agent_packages import _package_source
from state_system.instance_capability import InstanceCapabilityRuntime
from state_system.instance_preflight import InstancePreflightRuntime
from state_system.instance_source_freshness import InstanceSourceFreshnessRuntime
from state_system.instance_understanding_surface import (
    build_instance_understanding_surface_read_model,
)
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = ROOT / "examples" / "instance-capability"


class ContentStatusDimensionTests(unittest.TestCase):
    def test_freshness_basis_populates_only_the_proven_dimension(self):
        with TemporaryDirectory() as directory:
            runtime = InstanceSourceFreshnessRuntime(StateStoreBundle(Path(directory)))
            records = [
                runtime.record(_record("content", "fresh", "source_content", latest_source_modified_at="2026-05-17T10:14:00Z")),
                runtime.record(_record("event", "fresh", "source_event", latest_source_event_at="2026-05-17T10:14:00Z")),
                runtime.record(_record("index", "fresh", "source_index", latest_indexed_at="2026-05-17T10:14:00Z")),
                runtime.record(_record("probe", "unknown", "probe_only")),
                runtime.record(_record("package", "unknown", "package_generation", latest_indexed_at="2026-05-17T10:14:00Z", source_watermark="generated_at:2026-05-17T10:14:00Z")),
                runtime.record(_record("stale", "stale", "source_content", latest_source_modified_at="2026-05-17T08:00:00Z")),
                runtime.record(_record("incomplete", "fresh", "source_content", latest_source_modified_at="2026-05-17T10:14:00Z", completeness_status="incomplete")),
            ]

        by_name = {record["source_ref"].split(":")[-1]: record for record in records}
        self.assertEqual("fresh", by_name["content"]["content_status"])
        self.assertEqual("unknown", by_name["event"]["content_status"])
        self.assertEqual("fresh", by_name["event"]["event_status"])
        self.assertEqual("unknown", by_name["index"]["content_status"])
        self.assertEqual("fresh", by_name["index"]["index_status"])
        self.assertEqual("unknown", by_name["probe"]["content_status"])
        self.assertEqual("unknown", by_name["probe"]["probe_status"])
        self.assertEqual("unknown", by_name["package"]["content_status"])
        self.assertEqual("succeeded", by_name["package"]["process_status"])
        self.assertEqual("stale", by_name["stale"]["content_status"])
        self.assertEqual("incomplete", by_name["incomplete"]["completeness_status"])
        self.assertTrue(by_name["incomplete"]["source_gap_refs"])

    def test_dimensions_are_carried_to_surface_and_package_source(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            InstanceCapabilityRuntime(stores).seed(
                [load_json(PACK_DIR / "instance-sample-personal.json")]
            )
            InstancePreflightRuntime(stores).record(
                {
                    "preflight_ref": "preflight.state_instance.sample_personal.connector.personal.kb",
                    "instance_ref": "state_instance.sample_personal",
                    "connector_ref": "connector.personal.kb",
                    "source_ref": "kb:tenant:personal",
                    "connector_type": "kb",
                    "status": "passed",
                    "checked_at": "2026-05-17T10:15:00Z",
                    "stale_after": "2026-05-17T10:30:00Z",
                }
            )
            freshness = InstanceSourceFreshnessRuntime(stores).record(
                _record(
                    "kb",
                    "fresh",
                    "source_content",
                    latest_source_modified_at="2026-05-17T10:14:00Z",
                    source_gap_refs=["gap.content.coverage"],
                    source_ref="kb:tenant:personal",
                )
            )
            surface = build_instance_understanding_surface_read_model(stores)
            source = next(
                item
                for item in surface["instances"][0]["source_readiness"]
                if item["connector_ref"] == "connector.personal.kb"
            )
            packaged = _package_source(source)

        self.assertEqual("fresh", source["content_status"])
        self.assertEqual("source_content", source["watermark_basis"])
        self.assertEqual(["gap.content.coverage"], source["source_gap_refs"])
        self.assertEqual("fresh", packaged["content_status"])
        self.assertEqual(["gap.content.coverage"], packaged["source_gap_refs"])
        self.assertEqual([], validate_schema(
            freshness,
            load_json(ROOT / "schemas" / "instance-source-freshness-record.schema.json"),
        ))


def _record(
    name: str,
    status: str,
    basis: str,
    *,
    latest_source_modified_at: str = "",
    latest_source_event_at: str = "",
    latest_indexed_at: str = "",
    completeness_status: str | None = None,
    source_gap_refs: list[str] | None = None,
    source_watermark: str | None = None,
    source_ref: str | None = None,
) -> dict:
    record = {
        "instance_ref": "state_instance.sample_personal",
        "connector_ref": f"connector.personal.{name}",
        "source_ref": source_ref or f"source:tenant:{name}",
        "connector_type": "test",
        "status": status,
        "checked_at": "2026-05-17T10:15:00Z",
        "source_watermark": source_watermark or f"test.{basis}:2026-05-17T10:14:00Z",
        "stale_after": "2026-05-17T10:30:00Z",
        "watermark_basis": basis,
        "status_reason": "test freshness evidence",
        "evidence_refs": [f"evidence:{name}"],
        "source_gap_refs": source_gap_refs or [],
    }
    if basis == "probe_only":
        record["source_watermark"] += ";corpus_watermark=unproven"
        record["status_reason"] = "probe succeeded but source/corpus freshness is unproven"
    if latest_source_modified_at:
        record["latest_source_modified_at"] = latest_source_modified_at
    if latest_source_event_at:
        record["latest_source_event_at"] = latest_source_event_at
    if latest_indexed_at:
        record["latest_indexed_at"] = latest_indexed_at
    if completeness_status:
        record["completeness_status"] = completeness_status
    return record


if __name__ == "__main__":
    unittest.main()
