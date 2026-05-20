from __future__ import annotations

import json
from pathlib import Path

from state_system.contracts import JsonObject
from state_system.instance_capability import (
    build_instance_capability_read_model_from_runtime,
)
from state_system.instance_preflight import build_instance_preflight_read_model
from state_system.instance_source_freshness import (
    build_instance_source_freshness_read_model,
)
from state_system.stores import StateStoreBundle


def build_instance_understanding_surface_read_model(
    stores: StateStoreBundle,
) -> JsonObject:
    capability = build_instance_capability_read_model_from_runtime(stores)
    preflight = build_instance_preflight_read_model(stores)
    freshness = build_instance_source_freshness_read_model(stores)
    generated_at = max(
        (
            value
            for value in [
                capability.get("generated_at", ""),
                preflight.get("generated_at", ""),
                freshness.get("generated_at", ""),
            ]
            if value
        ),
        default="",
    )
    instances = [
        _instance_surface(instance, preflight, freshness)
        for instance in capability.get("instances", [])
    ]

    return {
        "id": "instance_understanding_surface_read_model",
        "artifact_type": "json_substrate",
        "generated_at": generated_at,
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


def _instance_surface(
    instance: JsonObject,
    preflight_read_model: JsonObject,
    freshness_read_model: JsonObject,
) -> JsonObject:
    source_readiness = [
        _source_readiness(
            instance,
            connector,
            preflight_read_model,
            freshness_read_model,
        )
        for connector in instance.get("source_connectors", [])
    ]
    source_gaps = [
        gap
        for source in source_readiness
        for gap in source.get("gaps", [])
    ]
    federation_packs = _federation_packs(instance["instance_ref"], source_readiness)
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
        "federation_packs": federation_packs,
    }


def _source_readiness(
    instance: JsonObject,
    connector: JsonObject,
    preflight_read_model: JsonObject,
    freshness_read_model: JsonObject,
) -> JsonObject:
    instance_ref = instance["instance_ref"]
    connector_ref = connector["id"]
    source_ref = connector["source_ref"]
    preflight_records = _preflight_records_for_connector(
        preflight_read_model,
        instance_ref,
        connector_ref,
        source_ref,
    )
    freshness_record = _freshness_record_for_source(
        freshness_read_model,
        instance_ref,
        connector_ref,
        source_ref,
    )
    index_manifests = [
        manifest
        for manifest in instance.get("index_manifests", [])
        if connector_ref in manifest.get("connector_refs", [])
        or source_ref in manifest.get("source_refs", [])
    ]
    federated_instance = _federated_instance(connector)
    access_status = _access_status(preflight_records)
    freshness_status = freshness_record.get("status", "missing")
    index_status = _index_status(index_manifests)
    connector_type = connector.get("connector_type", "")
    source_module_ref = connector.get(
        "source_module_ref",
        f"source_module.{connector_type}" if connector_type else "",
    )
    gaps = _source_gaps(
        instance_ref=instance_ref,
        connector_ref=connector_ref,
        source_ref=source_ref,
        access_status=access_status,
        freshness_status=freshness_status,
        index_status=index_status,
        federation_status=federated_instance.get("status"),
    )
    readiness = {
        "connector_ref": connector_ref,
        "connector_type": connector_type,
        "source_ref": source_ref,
        "source_module_ref": source_module_ref,
        "module_registry_ref": connector.get(
            "module_registry_ref",
            "source_module_registry.core_connectors",
        ),
        "module_mode": connector.get(
            "module_mode",
            _module_mode(connector, federated_instance),
        ),
        "checked_at": freshness_record.get("checked_at")
        or _latest_preflight_checked_at(preflight_records),
        "source_watermark": freshness_record.get("source_watermark", ""),
        "stale_after": freshness_record.get("stale_after", ""),
        "preflight_contract_ref": (
            f"{source_module_ref}.preflight" if source_module_ref else ""
        ),
        "freshness_contract_ref": (
            f"{source_module_ref}.freshness" if source_module_ref else ""
        ),
        "gap_behavior_ref": (
            f"{source_module_ref}.gap_behavior" if source_module_ref else ""
        ),
        "usable_access_status": _usable_access_status(
            access_status=access_status,
            freshness_status=freshness_status,
            index_status=index_status,
        ),
        "access_status": access_status,
        "freshness_status": freshness_status,
        "index_status": index_status,
        "understanding_status": _understanding_status(
            access_status=access_status,
            freshness_status=freshness_status,
            index_status=index_status,
        ),
        "preflight_records": preflight_records,
        "freshness_record": freshness_record,
        "index_refs": [manifest["index_ref"] for manifest in index_manifests],
        "gaps": gaps,
    }
    artifact_generated_at = connector.get("artifact_generated_at") or federated_instance.get(
        "generated_at"
    )
    if artifact_generated_at:
        readiness["artifact_generated_at"] = artifact_generated_at
    if connector.get("planned_missing_reason"):
        readiness["planned_missing_reason"] = connector["planned_missing_reason"]
    elif access_status != "passed":
        readiness["planned_missing_reason"] = (
            f"{connector_ref} access is {access_status}."
        )
    pipeline_dependency = connector.get("pipeline_dependency") or _pipeline_dependency(
        connector
    )
    if pipeline_dependency:
        readiness["pipeline_dependency"] = pipeline_dependency
    if federated_instance:
        readiness["federated_instance"] = federated_instance
    return readiness


def _module_mode(connector: JsonObject, federated_instance: JsonObject) -> str:
    connector_type = connector.get("connector_type", "")
    source_ref = connector.get("source_ref", "")
    if connector_type == "state_system_instance":
        return "federated_query"
    if connector_type == "relationship_substrate" and federated_instance:
        return "federated_query"
    if connector_type == "spotify":
        return "historical_cache"
    if connector_type in {
        "garmin_connect",
        "relationship_substrate",
        "paia_memory",
        "paia_workboard",
    }:
        return "local_sync"
    if connector_type == "docs":
        return "generated_read_model"
    if connector_type == "local_path" and source_ref.startswith("state-system-instance:"):
        return "federated_query"
    return connector.get("access_mode", "declared")


def _federation_packs(instance_ref: str, sources: list[JsonObject]) -> list[JsonObject]:
    connector_refs = {source["connector_ref"] for source in sources}
    packs: list[JsonObject] = []
    if "connector.personal.lfw_state_system" in connector_refs:
        lfw_state = _source_by_ref(sources, "connector.personal.lfw_state_system")
        packs.append(
            _federation_pack_summary(
                pack_id="instance_federation_pack.personal_to_lfw_state",
                status="ready",
                mode="instance_read",
                remote_instance_refs=["state_instance.lfw"],
                local_materialization=False,
                freshness_status=lfw_state.get("freshness_status", "unknown"),
                gap_refs=[gap["gap_ref"] for gap in lfw_state.get("gaps", [])],
            )
        )
    if instance_ref == "state_instance.lfw":
        packs.append(
            _federation_pack_summary(
                pack_id="instance_federation_pack.lfw_to_personal_relationship_substrate",
                status="ready",
                mode="source_substrate_query",
                remote_instance_refs=["state_instance.braydon_personal"],
                local_materialization=False,
                freshness_status="fresh",
                gap_refs=[],
            )
        )
    if instance_ref in {"state_instance.navicyte", "state_instance.synthyra"}:
        packs.append(
            _federation_pack_summary(
                pack_id="instance_federation_pack.portfolio_to_navicyte_synthyra",
                status="planned",
                mode="portfolio_rollup",
                remote_instance_refs=[
                    "state_instance.navicyte",
                    "state_instance.synthyra",
                ],
                local_materialization=False,
                freshness_status="unknown",
                gap_refs=[
                    f"gap.{instance_ref}.portfolio_federation.package_readiness_unproved"
                ],
            )
        )
    return packs


def _federation_pack_summary(
    *,
    pack_id: str,
    status: str,
    mode: str,
    remote_instance_refs: list[str],
    local_materialization: bool,
    freshness_status: str,
    gap_refs: list[str],
) -> JsonObject:
    return {
        "id": pack_id,
        "status": status,
        "federation_mode": mode,
        "remote_instance_refs": remote_instance_refs,
        "materialization_policy": {
            "local_materialization": local_materialization,
        },
        "freshness_policy": {
            "freshness_status": freshness_status,
            "gap_refs": gap_refs,
        },
    }


def _source_by_ref(sources: list[JsonObject], connector_ref: str) -> JsonObject:
    for source in sources:
        if source["connector_ref"] == connector_ref:
            return source
    return {}


def _usable_access_status(
    *,
    access_status: str,
    freshness_status: str,
    index_status: str,
) -> str:
    if access_status != "passed":
        return "not_usable"
    if index_status in {"missing", "failed"}:
        return "access_passed_index_unusable"
    if freshness_status in {"failed", "stale", "unknown", "missing"}:
        return "usable_with_freshness_gap"
    return "usable"


def _latest_preflight_checked_at(records: list[JsonObject]) -> str:
    checked = sorted(
        record.get("checked_at", "")
        for record in records
        if record.get("checked_at")
    )
    return checked[-1] if checked else ""


def _pipeline_dependency(connector: JsonObject) -> str:
    connector_type = connector.get("connector_type", "")
    source_ref = connector.get("source_ref", "")
    if connector_type == "docs":
        return "document_processing_pipeline"
    if connector_type == "local_path" and "transcript" in source_ref:
        return "raw_transcript_ingest"
    return ""


def _preflight_records_for_connector(
    preflight_read_model: JsonObject,
    instance_ref: str,
    connector_ref: str,
    source_ref: str,
) -> list[JsonObject]:
    records = [
        result
        for result in preflight_read_model.get("latest_by_scope_key", {}).values()
        if result.get("instance_ref") == instance_ref
        and result.get("connector_ref") == connector_ref
        and result.get("source_ref") == source_ref
    ]
    return sorted(records, key=lambda record: record.get("checked_at", ""), reverse=True)


def _access_status(preflight_records: list[JsonObject]) -> str:
    statuses = {record.get("status") for record in preflight_records}
    if "passed" in statuses:
        return "passed"
    if "failed" in statuses:
        return "failed"
    if "planned" in statuses:
        return "planned"
    return "missing"


def _freshness_record_for_source(
    freshness_read_model: JsonObject,
    instance_ref: str,
    connector_ref: str,
    source_ref: str,
) -> JsonObject:
    matching = [
        result
        for result in freshness_read_model.get("latest_by_scope_key", {}).values()
        if result.get("instance_ref") == instance_ref
        and result.get("connector_ref") == connector_ref
        and result.get("source_ref") == source_ref
    ]
    if not matching:
        return {}
    return sorted(matching, key=lambda record: record.get("checked_at", ""), reverse=True)[
        0
    ]


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
    federation_status: str | None = None,
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
    if federation_status == "missing":
        gaps.append(_gap(instance_ref, connector_ref, source_ref, "federation_missing"))
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


def _federated_instance(connector: JsonObject) -> JsonObject:
    if connector.get("connector_type") != "state_system_instance":
        return {}

    runtime_root = connector.get("runtime_root")
    source_instance_ref = _source_instance_ref(connector.get("source_ref", ""))
    if not runtime_root:
        return {
            "status": "missing",
            "source_instance_ref": source_instance_ref,
            "reason": "runtime_root_missing",
        }

    root = Path(str(runtime_root))
    read_models = _federated_read_models(root)
    if not root.exists() or not read_models:
        return {
            "status": "missing",
            "source_instance_ref": source_instance_ref,
            "runtime_root": str(root),
            "reason": "read_models_missing",
        }

    generated_values = [
        model.get("payload", {}).get("generated_at", "")
        for model in read_models
        if model.get("payload", {}).get("generated_at")
    ]
    gap_refs = sorted(
        {
            gap_ref
            for model in read_models
            for gap_ref in model.get("payload", {}).get("source_gap_refs", [])
        }
    )
    return {
        "status": "available",
        "source_instance_ref": source_instance_ref,
        "runtime_root": str(root),
        "read_model_refs": [model["ref"] for model in read_models],
        "generated_at": max(generated_values, default=""),
        "source_gap_refs": gap_refs,
    }


def _federated_read_models(root: Path) -> list[JsonObject]:
    candidates = [
        root
        / "instance-understanding"
        / "instance-understanding-surface-read-model.json",
        root / "instance-capability" / "instance-capability-read-model.json",
        root / "state-interpreted-index" / "state-interpreted-index-read-model.json",
        root
        / "company-understanding"
        / "company-understanding-surface-read-model.json",
    ]
    read_models: list[JsonObject] = []
    for path in candidates:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        read_models.append(
            {
                "ref": path.relative_to(root).as_posix(),
                "id": payload.get("id", ""),
                "generated_at": payload.get("generated_at", ""),
                "payload": payload,
            }
        )
    return read_models


def _source_instance_ref(source_ref: str) -> str:
    if source_ref.startswith("state-system-instance:"):
        return source_ref.removeprefix("state-system-instance:")
    return source_ref
