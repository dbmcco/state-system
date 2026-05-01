from __future__ import annotations

from copy import deepcopy

from state_system.committer import Committer
from state_system.context_packages import ContextPackager
from state_system.contracts import validate_schema
from state_system.recent_changes import RecentChangeIndexer
from state_system.runner import ReviewPacketBuilder
from state_system.stores import JsonObject, StateStoreBundle


def build_review_packet_from_source_event(
    stores: StateStoreBundle,
    schemas: dict[str, JsonObject],
    *,
    source_event_id: str,
    packet_id: str,
    created_at: str,
    resolved_evidence: list[JsonObject],
    unresolved_evidence_refs: list[str],
    persona: JsonObject,
    governance_constraints: list[JsonObject],
) -> JsonObject:
    source_event = stores.source_events.read(source_event_id)
    trigger = trigger_from_source_event(source_event)
    packet = ReviewPacketBuilder(stores).build(
        trigger=trigger,
        created_at=created_at,
        packet_id=packet_id,
        resolved_evidence_by_ref={
            item["ref"]: item for item in resolved_evidence
        },
        unresolved_evidence_refs=unresolved_evidence_refs,
        persona=persona,
        governance_constraints=governance_constraints,
    )
    errors = validate_schema(packet, schemas["review_packet"])
    if errors:
        raise RuntimeValidationError(errors)
    stores.review_packets.create(packet)
    return packet


def commit_model_output(
    stores: StateStoreBundle,
    schemas: dict[str, JsonObject],
    *,
    model_output: JsonObject,
    created_at: str,
    evidence_refs: list[str],
) -> JsonObject:
    return Committer(stores, schemas).commit(
        model_output,
        created_at=created_at,
        evidence_refs=evidence_refs,
    )


def index_recent_change(
    stores: StateStoreBundle,
    schemas: dict[str, JsonObject],
    *,
    source_event_id: str,
    commit_id: str,
    created_at: str,
    summary: str,
    routes: list[JsonObject],
    opportunity_class_hints: list[str],
    watermark_refs: list[str],
    stale_after: str,
    requires_refresh_before_external_action: bool,
) -> JsonObject:
    return RecentChangeIndexer(stores, schemas).index_from_source_commit(
        source_event=stores.source_events.read(source_event_id),
        commit_result=stores.commits.read(commit_id),
        created_at=created_at,
        summary=summary,
        candidate_persona_routes=routes,
        opportunity_class_hints=opportunity_class_hints,
        freshness={
            "watermark_refs": watermark_refs,
            "stale_after": stale_after,
            "requires_refresh_before_external_action": (
                requires_refresh_before_external_action
            ),
        },
    )


def index_recent_change_from_source_event(
    stores: StateStoreBundle,
    schemas: dict[str, JsonObject],
    *,
    source_event_id: str,
    created_at: str,
    summary: str,
    routes: list[JsonObject],
    opportunity_class_hints: list[str],
    watermark_refs: list[str],
    stale_after: str,
    requires_refresh_before_external_action: bool,
) -> JsonObject:
    return RecentChangeIndexer(stores, schemas).index_from_source_event(
        source_event=stores.source_events.read(source_event_id),
        created_at=created_at,
        summary=summary,
        candidate_persona_routes=routes,
        opportunity_class_hints=opportunity_class_hints,
        freshness={
            "watermark_refs": watermark_refs,
            "stale_after": stale_after,
            "requires_refresh_before_external_action": (
                requires_refresh_before_external_action
            ),
        },
    )


def build_recent_package(
    stores: StateStoreBundle,
    schemas: dict[str, JsonObject],
    *,
    persona: JsonObject,
    package_id: str,
    created_at: str,
    review_goal: str,
    valid_until: str,
) -> JsonObject:
    return ContextPackager(stores, schemas).build_recent_change_package(
        persona=persona,
        package_id=package_id,
        created_at=created_at,
        review_goal=review_goal,
        valid_until=valid_until,
    )


def trigger_from_source_event(source_event: JsonObject) -> JsonObject:
    payload = {
        "source_system": source_event["source_system"],
        "source_event": source_event["source_event"],
    }
    for key in ("source_event_id", "change", "sync_context"):
        if key in source_event:
            payload[key] = deepcopy(source_event[key])

    return {
        "id": _trigger_id(source_event),
        "source": "tool_result",
        "created_at": source_event["observed_at"],
        "actor_ref": source_event["actor_ref"],
        "summary": source_event["summary"],
        "payload": payload,
        "evidence_refs": list(source_event["source_refs"]),
        "candidate_state_refs": list(source_event.get("candidate_state_refs", [])),
        "candidate_memory_refs": [],
        "governance_refs": list(source_event.get("governance_refs", [])),
    }


class RuntimeValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("runtime validation failed")
        self.errors = tuple(errors)


def _trigger_id(source_event: JsonObject) -> str:
    source_id = str(source_event["id"])
    if source_id.startswith("source."):
        return f"trigger.{source_id[len('source.'):]}"
    return f"trigger.{source_id}"
