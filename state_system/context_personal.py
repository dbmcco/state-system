from __future__ import annotations

from pathlib import Path

from state_system.contracts import JsonObject, load_json, validate_schema
from state_system.instance_capability import InstanceCapabilityRuntime
from state_system.instance_understanding_surface import (
    build_instance_understanding_surface_read_model,
)
from state_system.stores import StateStoreBundle


DEFAULT_NON_GOALS = (
    "Do not synthesize life state in deterministic code.",
    "Do not copy raw email, agent memory, or work instance corpora into personal state.",
    "Do not bypass governance on federated work instances.",
)

BOUNDED_EXCERPT_CONNECTOR_TYPES = frozenset({"msgvault", "agentmem"})


class PersonalContextPackageValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("personal context package validation failed")
        self.errors = tuple(errors)


def build_personal_context_package(
    *,
    stores: StateStoreBundle,
    instance_ref: str,
    package_id: str,
    created_at: str,
    synthesis_goal: str,
    valid_until: str,
    schema: JsonObject | None = None,
) -> JsonObject:
    surface = build_instance_understanding_surface_read_model(stores)
    instance = _find_instance(surface, instance_ref)
    if instance is None:
        raise ValueError(
            f"{instance_ref} does not exist in instance understanding surface"
        )
    capability = InstanceCapabilityRuntime(stores).read_instance(instance_ref)

    package = _assemble_package(
        instance=instance,
        capability=capability,
        package_id=package_id,
        created_at=created_at,
        synthesis_goal=synthesis_goal,
        valid_until=valid_until,
    )
    errors = validate_schema(package, schema or _default_schema(stores))
    if errors:
        raise PersonalContextPackageValidationError(errors)
    return package


def _assemble_package(
    *,
    instance: JsonObject,
    capability: JsonObject,
    package_id: str,
    created_at: str,
    synthesis_goal: str,
    valid_until: str,
) -> JsonObject:
    connector_index = {c["id"]: c for c in capability.get("source_connectors", [])}
    manifest_by_connector = _manifests_by_connector(capability)
    return {
        "id": package_id,
        "package_type": "personal_b_state_synthesis",
        "instance_ref": instance["instance_ref"],
        "primary_entity_ref": instance["primary_entity_ref"],
        "entity_kind": instance["entity_kind"],
        "created_at": created_at,
        "synthesis_goal": synthesis_goal,
        "primary_agent_refs": list(instance.get("primary_agent_refs", [])),
        "oversight_agent_refs": list(instance.get("oversight_agent_refs", [])),
        "source_boundaries": [
            _boundary(source, connector_index.get(source["connector_ref"], {}))
            for source in instance["source_readiness"]
        ],
        "retrieval_refs": _retrieval_refs(instance, manifest_by_connector),
        "freshness": _freshness(instance, capability, created_at, valid_until),
        "governance": {
            "governance_refs": list(capability["governance"]["governance_refs"]),
            "constraints": list(capability["runtime_constraints"]["constraints"]),
        },
        "unresolved_gaps": _unresolved_gaps(instance),
        "non_goals": list(DEFAULT_NON_GOALS),
        "invariant": {
            "declares_synthesis_input": True,
            "synthesizes_state": False,
            "copies_raw_corpora": False,
            "msgvault_excerpts_bounded": True,
            "agentmem_excerpts_bounded": True,
        },
    }


def _boundary(source: JsonObject, connector: JsonObject) -> JsonObject:
    return {
        "connector_ref": source["connector_ref"],
        "source_ref": source["source_ref"],
        "connector_type": source["connector_type"],
        "owner": connector.get("owner", ""),
        "access_mode": connector.get("access_mode", ""),
        "understanding_status": source["understanding_status"],
        "raw_corpus_included": False,
        "governance_refs": list(connector.get("governance_refs", [])),
    }


def _retrieval_refs(
    instance: JsonObject,
    manifest_by_connector: dict[str, list[JsonObject]],
) -> list[JsonObject]:
    refs: list[JsonObject] = []
    for source in instance["source_readiness"]:
        for manifest in manifest_by_connector.get(source["connector_ref"], []):
            refs.append(_retrieval_ref(manifest, source))
    return refs


def _retrieval_ref(manifest: JsonObject, source: JsonObject) -> JsonObject:
    representation = (
        "bounded_excerpt"
        if source["connector_type"] in BOUNDED_EXCERPT_CONNECTOR_TYPES
        and manifest.get("scope") == "memory_index"
        else "retrieval_ref"
    )
    ref: JsonObject = {
        "index_ref": manifest["index_ref"],
        "connector_ref": source["connector_ref"],
        "source_ref": source["source_ref"],
        "owner": manifest.get("owner", ""),
        "scope": manifest.get("scope", ""),
        "record_kinds": list(manifest.get("record_kinds", [])),
        "representation": representation,
        "query_surface": dict(manifest.get("query_surface", {})),
    }
    if representation == "bounded_excerpt":
        ref["bounded_excerpt"] = {
            "summary": (
                f"Bounded excerpt placeholder for {manifest['index_ref']}; "
                "source-owned retrieval required for full content."
            ),
            "size_hint": "<= 1 KB",
            "provenance_ref": manifest["index_ref"],
        }
    return ref


def _unresolved_gaps(instance: JsonObject) -> list[JsonObject]:
    return [
        {
            "gap_ref": gap["gap_ref"],
            "instance_ref": gap["instance_ref"],
            "connector_ref": gap["connector_ref"],
            "source_ref": gap["source_ref"],
            "reason": gap["reason"],
            "blocking": gap["reason"].startswith("access_")
            or gap["reason"] == "federation_missing",
        }
        for gap in instance.get("source_gaps", [])
    ]


def _freshness(
    instance: JsonObject,
    capability: JsonObject,
    as_of: str,
    valid_until: str,
) -> JsonObject:
    watermark_refs: list[str] = []
    seen: set[str] = set()
    for marker in _watermarks(instance, capability):
        if marker and marker not in seen:
            seen.add(marker)
            watermark_refs.append(marker)
    return {
        "as_of": as_of,
        "valid_until": valid_until,
        "watermark_refs": watermark_refs,
        "requires_refresh_before_synthesis": any(
            source["understanding_status"] != "ready"
            for source in instance["source_readiness"]
        ),
        "stale_if_refs_change": [],
    }


def _watermarks(instance: JsonObject, capability: JsonObject):
    for source in instance["source_readiness"]:
        yield source.get("freshness_record", {}).get("source_watermark")
    yield from capability["freshness"].get("watermark_refs", [])


def _manifests_by_connector(capability: JsonObject) -> dict[str, list[JsonObject]]:
    grouped: dict[str, list[JsonObject]] = {}
    for manifest in capability.get("index_manifests", []):
        for connector_ref in manifest.get("connector_refs", []):
            grouped.setdefault(connector_ref, []).append(manifest)
    return grouped


def _find_instance(surface: JsonObject, instance_ref: str) -> JsonObject | None:
    for instance in surface.get("instances", []):
        if instance.get("instance_ref") == instance_ref:
            return instance
    return None


def _default_schema(stores: StateStoreBundle) -> JsonObject:
    return load_json(
        Path(__file__).resolve().parents[1]
        / "schemas"
        / "personal-context-package.schema.json"
    )
