from __future__ import annotations

import json

from state_system.contracts import JsonObject
from state_system.stores import RecordNotFoundError, StateStoreBundle


def build_instance_capability_read_model(packs: list[JsonObject]) -> JsonObject:
    sorted_packs = sorted(packs, key=lambda pack: pack["instance_ref"])
    return {
        "id": "instance_capability_read_model",
        "artifact_type": "json_substrate",
        "generated_at": max(pack["generated_at"] for pack in sorted_packs),
        "instances": [_instance_summary(pack) for pack in sorted_packs],
        "source_refs": sorted(
            {
                source_ref
                for pack in sorted_packs
                for source_ref in pack["raw_corpus"]["source_refs"]
            }
        ),
        "evidence_index_refs": sorted(
            {
                index_ref
                for pack in sorted_packs
                for index_ref in pack["evidence_index"]["index_refs"]
            }
        ),
        "index_manifests": [
            manifest
            for pack in sorted_packs
            for manifest in pack.get("index_manifests", [])
        ],
        "index_refs": sorted(
            {
                manifest["index_ref"]
                for pack in sorted_packs
                for manifest in pack.get("index_manifests", [])
            }
        ),
        "invariant": {
            "instance_capability_pack_declares_context": True,
            "instance_capability_pack_proves_live_access": False,
            "instance_capability_pack_authorizes_execution": False,
            "live_access_proven_by": "connector_preflight",
            "protected_action_authorized_by": "governance",
        },
    }


def build_instance_capability_read_model_from_runtime(
    stores: StateStoreBundle,
) -> JsonObject:
    return build_instance_capability_read_model(
        InstanceCapabilityRuntime(stores).list_packs()
    )


class InstanceCapabilityRuntime:
    def __init__(self, stores: StateStoreBundle):
        self.store = stores.instance_capabilities

    def seed(self, packs: list[JsonObject]) -> JsonObject:
        created: list[str] = []
        updated: list[str] = []
        seeded: list[JsonObject] = []

        for pack in sorted(packs, key=lambda value: value["instance_ref"]):
            record_id = pack["id"]
            path = self.store.path_for(record_id)
            path.parent.mkdir(parents=True, exist_ok=True)

            if path.exists():
                updated.append(record_id)
            else:
                created.append(record_id)

            with path.open("w", encoding="utf-8") as handle:
                json.dump(pack, handle, indent=2, sort_keys=True)
                handle.write("\n")
            seeded.append({"id": record_id, "instance_ref": pack["instance_ref"]})

        return {
            "created": created,
            "updated": updated,
            "seeded": seeded,
            "count": len(seeded),
        }

    def read(self, record_id: str) -> JsonObject:
        return self.store.read(record_id)

    def read_instance(self, instance_ref: str) -> JsonObject:
        for pack in self.list_packs():
            if pack["instance_ref"] == instance_ref:
                return pack
        raise RecordNotFoundError(
            f"{instance_ref} does not exist in instance-capabilities"
        )

    def list_packs(self) -> list[JsonObject]:
        return sorted(self.store.replay(), key=lambda pack: pack["instance_ref"])


def _instance_summary(pack: JsonObject) -> JsonObject:
    return {
        "id": pack["id"],
        "instance_ref": pack["instance_ref"],
        "primary_entity_ref": pack["primary_entity_ref"],
        "entity_kind": pack["entity_kind"],
        "name": pack["identity"]["name"],
        "primary_agent_refs": pack["identity"]["primary_agent_refs"],
        "oversight_agent_refs": pack["identity"].get("oversight_agent_refs", []),
        "source_connectors": pack["source_connectors"],
        "connector_refs": [connector["id"] for connector in pack["source_connectors"]],
        "connector_types": sorted(
            {connector["connector_type"] for connector in pack["source_connectors"]}
        ),
        "raw_corpus_refs": pack["raw_corpus"]["source_refs"],
        "evidence_index_refs": pack["evidence_index"]["index_refs"],
        "index_manifests": pack.get("index_manifests", []),
        "index_refs": [
            manifest["index_ref"] for manifest in pack.get("index_manifests", [])
        ],
        "memory_refs": pack["memory_refs"],
        "operating_picture_refs": pack["operating_picture_refs"],
        "action_surface_refs": pack["action_surface"]["action_refs"],
        "tool_capability_bindings": pack["tool_capability_bindings"],
        "governance_refs": pack["governance"]["governance_refs"],
        "preflight_check_refs": [
            check["id"] for check in pack["connector_preflight"]["required_checks"]
        ],
        "runtime_constraints": pack["runtime_constraints"]["constraints"],
        "freshness": pack["freshness"],
        "invariant": pack["invariant"],
    }
