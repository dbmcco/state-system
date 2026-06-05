from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system.instance_capability import InstanceCapabilityRuntime
from state_system.instance_understanding_surface import (
    build_instance_understanding_surface_read_model,
)
from state_system.stores import StateStoreBundle


class InstanceFederationTests(unittest.TestCase):
    def test_state_system_instance_connector_exposes_remote_read_model_metadata(self):
        with TemporaryDirectory() as directory, TemporaryDirectory() as remote_root:
            stores = StateStoreBundle(Path(directory))
            _write_json(
                Path(remote_root)
                / "instance-understanding"
                / "instance-understanding-surface-read-model.json",
                {
                    "id": "instance_understanding_surface_read_model",
                    "generated_at": "2026-05-17T16:20:00Z",
                    "source_gap_refs": [
                        "gap.state_instance.sampleco.connector.sampleco.msgvault.freshness_failed"
                    ],
                },
            )
            _write_json(
                Path(remote_root)
                / "state-interpreted-index"
                / "state-interpreted-index-read-model.json",
                {
                    "id": "state_interpreted_index_read_model",
                    "generated_at": "2026-05-17T16:19:00Z",
                },
            )
            InstanceCapabilityRuntime(stores).seed(
                [_personal_pack_with_federation(remote_root)]
            )

            read_model = build_instance_understanding_surface_read_model(stores)

        personal = read_model["instances"][0]
        sampleco_inst = next(
            source
            for source in personal["source_readiness"]
            if source["connector_ref"] == "connector.personal.sampleco_state_system"
        )
        self.assertEqual("available", sampleco_inst["federated_instance"]["status"])
        self.assertEqual(
            "state_instance.sampleco",
            sampleco_inst["federated_instance"]["source_instance_ref"],
        )
        self.assertEqual(
            "2026-05-17T16:20:00Z",
            sampleco_inst["federated_instance"]["generated_at"],
        )
        self.assertIn(
            "instance-understanding/instance-understanding-surface-read-model.json",
            sampleco_inst["federated_instance"]["read_model_refs"],
        )
        self.assertIn(
            "gap.state_instance.sampleco.connector.sampleco.msgvault.freshness_failed",
            sampleco_inst["federated_instance"]["source_gap_refs"],
        )
        self.assertNotIn("raw_records", sampleco_inst["federated_instance"])
        self.assertEqual("missing", sampleco_inst["access_status"])

    def test_missing_state_system_instance_runtime_root_is_a_gap(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            InstanceCapabilityRuntime(stores).seed(
                [_personal_pack_with_federation("/does/not/exist")]
            )

            read_model = build_instance_understanding_surface_read_model(stores)

        self.assertIn(
            "gap.state_instance.sample_personal.connector.personal.sampleco_state_system.federation_missing",
            read_model["source_gap_refs"],
        )


def _personal_pack_with_federation(runtime_root: str):
    return {
        "id": "instance_capability_pack.sample_personal",
        "instance_ref": "state_instance.sample_personal",
        "primary_entity_ref": "entity.example_user",
        "entity_kind": "person",
        "generated_at": "2026-05-17T16:18:00Z",
        "identity": {
            "name": "Sample Personal State",
            "summary": "Test fixture.",
            "primary_agent_refs": ["persona.nova"],
            "oversight_agent_refs": [],
        },
        "source_connectors": [
            {
                "id": "connector.personal.sampleco_state_system",
                "connector_type": "state_system_instance",
                "source_ref": "state-system-instance:state_instance.sampleco",
                "owner": "state_system",
                "declared": True,
                "access_mode": "read",
                "runtime_root": str(runtime_root),
            }
        ],
        "raw_corpus": {
            "definition": "Federated instance refs only.",
            "source_refs": ["state-system-instance:state_instance.sampleco"],
        },
        "evidence_index": {
            "definition": "Federated interpreted indexes.",
            "index_refs": ["index.personal.sampleco_state_system.interpreted"],
        },
        "index_manifests": [
            {
                "index_ref": "index.personal.sampleco_state_system.interpreted",
                "instance_ref": "state_instance.sample_personal",
                "primary_entity_ref": "entity.example_user",
                "owner": "state_system",
                "backend": "state_system_remote",
                "scope": "interpreted_state_index",
                "record_kinds": ["evidence_card", "claim", "operating_picture"],
                "source_refs": ["state-system-instance:state_instance.sampleco"],
                "connector_refs": ["connector.personal.sampleco_state_system"],
                "query_surface": {
                    "type": "state_system_runtime",
                    "tool_ref": "tool.state_system.instance_read",
                },
                "status": "planned",
            }
        ],
        "memory_refs": [],
        "operating_picture_refs": [],
        "action_surface": {
            "definition": "Test actions.",
            "action_refs": ["action_surface.personal.read_sampleco_state"],
        },
        "tool_capability_bindings": [],
        "governance": {
            "definition": "Test governance.",
            "governance_refs": ["governance.sampleco.read_summary"],
        },
        "connector_preflight": {
            "definition": "Preflight proves live access only.",
            "required_checks": [],
        },
        "runtime_constraints": {
            "definition": "Test constraints.",
            "constraints": ["Do not copy raw work corpora."],
        },
        "freshness": {
            "as_of": "2026-05-17T16:18:00Z",
            "stale_after": "2026-05-17T17:18:00Z",
            "watermark_refs": [],
        },
        "invariant": {
            "declares_context": True,
            "proves_live_access": False,
            "authorizes_execution": False,
            "live_access_proven_by": "connector_preflight",
            "protected_action_authorized_by": "governance",
        },
    }


def _write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
