from __future__ import annotations

from state_system.contracts import JsonObject
from state_system.instance_capability import (
    build_instance_capability_read_model_from_runtime,
)
from state_system.stores import StateStoreBundle


def build_instance_understanding_surface_read_model(
    stores: StateStoreBundle,
) -> JsonObject:
    capability = build_instance_capability_read_model_from_runtime(stores)
    instances = [
        _instance_surface(instance)
        for instance in capability.get("instances", [])
    ]

    return {
        "id": "instance_understanding_surface_read_model",
        "artifact_type": "json_substrate",
        "generated_at": capability.get("generated_at", ""),
        "instances": instances,
        "index_refs": sorted(
            {
                manifest["index_ref"]
                for instance in instances
                for manifest in instance.get("searchable_surfaces", [])
            }
        ),
        "source_gap_refs": [
            gap["gap_ref"]
            for instance in instances
            for gap in instance.get("source_gaps", [])
        ],
        "invariant": {
            "surface_declares_retrieval_contract": True,
            "surface_executes_retrieval": False,
            "surface_ranks_or_synthesizes": False,
            "preflight_proves_live_access": True,
            "freshness_is_recency_evidence": True,
            "authorizes_execution": False,
            "protected_action_authorized_by": "governance",
        },
    }


def _instance_surface(instance: JsonObject) -> JsonObject:
    source_readiness = [
        _source_readiness(instance, connector)
        for connector in instance.get("source_connectors", [])
    ]
    source_gaps = [
        gap
        for source in source_readiness
        for gap in source.get("gaps", [])
    ]
    return {
        "instance_ref": instance["instance_ref"],
        "primary_entity_ref": instance["primary_entity_ref"],
        "entity_kind": instance["entity_kind"],
        "name": instance["name"],
        "primary_agent_refs": instance.get("primary_agent_refs", []),
        "oversight_agent_refs": instance.get("oversight_agent_refs", []),
        "raw_corpus_refs": instance.get("raw_corpus_refs", []),
        "memory_refs": instance.get("memory_refs", []),
        "operating_picture_refs": instance.get("operating_picture_refs", []),
        "searchable_surfaces": instance.get("index_manifests", []),
        "source_readiness": source_readiness,
        "source_gaps": source_gaps,
    }


def _source_readiness(instance: JsonObject, connector: JsonObject) -> JsonObject:
    instance_ref = instance["instance_ref"]
    connector_ref = connector["id"]
    source_ref = connector["source_ref"]
    index_manifests = [
        manifest
        for manifest in instance.get("index_manifests", [])
        if connector_ref in manifest.get("connector_refs", [])
        or source_ref in manifest.get("source_refs", [])
    ]
    access_status = "missing"
    freshness_status = "missing"
    index_status = _index_status(index_manifests)
    gaps = _source_gaps(
        instance_ref=instance_ref,
        connector_ref=connector_ref,
        source_ref=source_ref,
        access_status=access_status,
        freshness_status=freshness_status,
        index_status=index_status,
    )
    return {
        "connector_ref": connector_ref,
        "connector_type": connector.get("connector_type", ""),
        "source_ref": source_ref,
        "access_status": access_status,
        "freshness_status": freshness_status,
        "index_status": index_status,
        "understanding_status": _understanding_status(
            access_status=access_status,
            freshness_status=freshness_status,
            index_status=index_status,
        ),
        "preflight_records": [],
        "freshness_record": {},
        "index_refs": [manifest["index_ref"] for manifest in index_manifests],
        "gaps": gaps,
    }


def _index_status(index_manifests: list[JsonObject]) -> str:
    statuses = {manifest.get("status") for manifest in index_manifests}
    if "declared" in statuses:
        return "declared"
    if "planned" in statuses:
        return "planned"
    if "disabled" in statuses:
        return "disabled"
    return "missing"


def _understanding_status(
    *,
    access_status: str,
    freshness_status: str,
    index_status: str,
) -> str:
    if index_status == "declared" and access_status == "passed" and freshness_status == "fresh":
        return "ready"
    if index_status == "declared" and access_status == "passed":
        return "usable_with_freshness_gap"
    if index_status == "declared":
        return "searchable_access_unproven"
    if index_status == "planned":
        return "planned"
    return "gap"


def _source_gaps(
    *,
    instance_ref: str,
    connector_ref: str,
    source_ref: str,
    access_status: str,
    freshness_status: str,
    index_status: str,
) -> list[JsonObject]:
    gaps: list[JsonObject] = []
    if access_status != "passed":
        gaps.append(
            _gap(instance_ref, connector_ref, source_ref, f"access_{access_status}")
        )
    if freshness_status != "fresh":
        gaps.append(
            _gap(
                instance_ref,
                connector_ref,
                source_ref,
                f"freshness_{freshness_status}",
            )
        )
    if index_status != "declared":
        gaps.append(_gap(instance_ref, connector_ref, source_ref, f"index_{index_status}"))
    return gaps


def _gap(
    instance_ref: str,
    connector_ref: str,
    source_ref: str,
    reason: str,
) -> JsonObject:
    return {
        "gap_ref": f"gap.{instance_ref}.{connector_ref}.{reason}",
        "instance_ref": instance_ref,
        "connector_ref": connector_ref,
        "source_ref": source_ref,
        "reason": reason,
    }
