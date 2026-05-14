from __future__ import annotations

from state_system.contracts import JsonObject


def build_company_capability_read_model(packs: list[JsonObject]) -> JsonObject:
    sorted_packs = sorted(packs, key=lambda pack: pack["company_ref"])
    return {
        "id": "company_capability_read_model",
        "artifact_type": "json_substrate",
        "generated_at": max(pack["generated_at"] for pack in sorted_packs),
        "companies": [_company_summary(pack) for pack in sorted_packs],
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
        "invariant": {
            "company_capability_pack_declares_context": True,
            "company_capability_pack_proves_live_access": False,
            "company_capability_pack_authorizes_execution": False,
            "live_access_proven_by": "paia_connector_preflight",
            "protected_action_authorized_by": "governance",
        },
    }


def _company_summary(pack: JsonObject) -> JsonObject:
    return {
        "id": pack["id"],
        "company_ref": pack["company_ref"],
        "name": pack["identity"]["name"],
        "primary_agent_refs": pack["identity"]["primary_agent_refs"],
        "oversight_agent_refs": pack["identity"].get("oversight_agent_refs", []),
        "connector_refs": [connector["id"] for connector in pack["source_connectors"]],
        "connector_types": sorted(
            {connector["connector_type"] for connector in pack["source_connectors"]}
        ),
        "raw_corpus_refs": pack["raw_corpus"]["source_refs"],
        "evidence_index_refs": pack["evidence_index"]["index_refs"],
        "company_memory_refs": pack["company_memory_refs"],
        "operating_picture_refs": pack["operating_picture_refs"],
        "action_surface_refs": pack["action_surface"]["action_refs"],
        "governance_refs": pack["governance"]["governance_refs"],
        "preflight_check_refs": [
            check["id"] for check in pack["connector_preflight"]["required_checks"]
        ],
        "runtime_constraints": pack["runtime_constraints"]["constraints"],
        "freshness": pack["freshness"],
        "invariant": pack["invariant"],
    }
