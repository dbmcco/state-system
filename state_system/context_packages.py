from __future__ import annotations

from copy import deepcopy

from state_system.contracts import validate_schema
from state_system.stores import JsonObject, StateStoreBundle


DEFAULT_INCLUDED_TIERS = ("primary", "secondary", "escalated")


class ContextPackageValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("context package validation failed")
        self.errors = tuple(errors)


class ContextPackager:
    def __init__(self, stores: StateStoreBundle, schemas: dict[str, JsonObject]):
        self.stores = stores
        self.schemas = schemas

    def build_opportunity_package(
        self,
        *,
        persona: JsonObject,
        recent_change_id: str,
        package_id: str,
        created_at: str,
        review_goal: str,
        state_refs: list[str],
        memory_refs: list[str],
        governance_constraints: list[JsonObject],
        resolved_evidence: list[JsonObject],
        unresolved_evidence_refs: list[str],
        relationship_sensitivity: JsonObject,
        available_actions: list[JsonObject],
        excluded_context_summary: list[JsonObject],
        open_questions: list[str],
        valid_until: str,
        stale_if_refs_change: list[str],
    ) -> JsonObject:
        recent_change = self.stores.recent_changes.read(recent_change_id)
        package = self._base_package(
            package_id=package_id,
            package_type="opportunity",
            created_at=created_at,
            persona=persona,
            review_goal=review_goal,
            recent_entries=[
                self._recent_entry_for_persona(recent_change, persona["id"], state_refs)
            ],
            state_refs=state_refs,
            memory_refs=memory_refs,
            governance_constraints=governance_constraints,
            evidence_refs=_unique(
                recent_change["source_refs"],
                recent_change.get("journal_entry_refs", []),
            ),
            resolved_evidence=resolved_evidence,
            unresolved_evidence_refs=unresolved_evidence_refs,
            relationship_sensitivity=relationship_sensitivity,
            available_actions=available_actions,
            excluded_context_summary=excluded_context_summary,
            open_questions=open_questions,
            watermark_refs=_unique(
                recent_change["freshness"]["watermark_refs"],
                [recent_change["id"]],
            ),
            valid_until=valid_until,
            requires_refresh_before_external_action=recent_change["freshness"].get(
                "requires_refresh_before_external_action", False
            ),
            stale_if_refs_change=stale_if_refs_change,
        )
        return self._persist(package)

    def build_recent_change_package(
        self,
        *,
        persona: JsonObject,
        package_id: str,
        created_at: str,
        review_goal: str,
        valid_until: str,
        included_tiers: tuple[str, ...] = DEFAULT_INCLUDED_TIERS,
    ) -> JsonObject:
        included_entries: list[JsonObject] = []
        excluded_summary: list[JsonObject] = []
        watermark_refs: list[str] = []

        for recent_change in self.stores.recent_changes.replay():
            route = _route_for_persona(recent_change, persona["id"])
            if route is None:
                continue
            watermark_refs = _unique(
                watermark_refs,
                recent_change["freshness"]["watermark_refs"],
            )
            if route["included"] and route["relevance_tier"] in included_tiers:
                included_entries.append(
                    self._recent_entry_for_persona(recent_change, persona["id"], None)
                )
            else:
                excluded_summary.append(
                    {
                        "recent_change_ref": recent_change["id"],
                        "relevance_tier": route["relevance_tier"],
                        "summary": route.get(
                            "excluded_context_summary",
                            route["routing_reason"],
                        ),
                    }
                )

        package = self._base_package(
            package_id=package_id,
            package_type="recent_change",
            created_at=created_at,
            persona=persona,
            review_goal=review_goal,
            recent_entries=included_entries,
            state_refs=[],
            memory_refs=[],
            governance_constraints=[],
            evidence_refs=[],
            resolved_evidence=[],
            unresolved_evidence_refs=[],
            relationship_sensitivity={"level": "unknown", "summary": "", "redactions": []},
            available_actions=[],
            excluded_context_summary=excluded_summary,
            open_questions=[],
            watermark_refs=watermark_refs,
            valid_until=valid_until,
            requires_refresh_before_external_action=False,
            stale_if_refs_change=[],
        )
        return self._persist(package)

    def _base_package(
        self,
        *,
        package_id: str,
        package_type: str,
        created_at: str,
        persona: JsonObject,
        review_goal: str,
        recent_entries: list[JsonObject],
        state_refs: list[str],
        memory_refs: list[str],
        governance_constraints: list[JsonObject],
        evidence_refs: list[str],
        resolved_evidence: list[JsonObject],
        unresolved_evidence_refs: list[str],
        relationship_sensitivity: JsonObject,
        available_actions: list[JsonObject],
        excluded_context_summary: list[JsonObject],
        open_questions: list[str],
        watermark_refs: list[str],
        valid_until: str,
        requires_refresh_before_external_action: bool,
        stale_if_refs_change: list[str],
    ) -> JsonObject:
        return {
            "id": package_id,
            "package_type": package_type,
            "created_at": created_at,
            "persona_context": {
                "persona_ref": persona["id"],
                "summary": (
                    f"{persona['name']} is a {persona['role']} focused on "
                    f"{persona['mission']}"
                ),
                "watched_domains": list(persona.get("state_domains_watched", [])),
                "authority_boundaries": list(persona.get("authority_boundaries", [])),
            },
            "review_goal": review_goal,
            "recent_change_context": {"entries": deepcopy(recent_entries)},
            "state_context": {
                "snapshots": [
                    self.stores.state_objects.read(state_ref) for state_ref in state_refs
                ]
            },
            "journal_context": {
                "recent_entries": [
                    entry
                    for entry in self.stores.journals.replay()
                    if entry.get("state_object_id") in state_refs
                ]
            },
            "memory_context": {
                "entries": [
                    self.stores.memory.read(memory_ref) for memory_ref in memory_refs
                ]
            },
            "evidence_context": {
                "evidence_refs": list(evidence_refs),
                "resolved_evidence": deepcopy(resolved_evidence),
                "unresolved_evidence_refs": list(unresolved_evidence_refs),
            },
            "governance_context": {"constraints": deepcopy(governance_constraints)},
            "relationship_sensitivity": deepcopy(relationship_sensitivity),
            "available_actions": deepcopy(available_actions),
            "excluded_context_summary": deepcopy(excluded_context_summary),
            "open_questions": list(open_questions),
            "freshness": {
                "watermark_refs": list(watermark_refs),
                "valid_until": valid_until,
                "requires_refresh_before_external_action": (
                    requires_refresh_before_external_action
                ),
                "stale_if_refs_change": list(stale_if_refs_change),
            },
        }

    def _recent_entry_for_persona(
        self,
        recent_change: JsonObject,
        persona_ref: str,
        state_refs: list[str] | None,
    ) -> JsonObject:
        route = _route_for_persona(recent_change, persona_ref)
        affected_state_refs = list(recent_change["affected_state_refs"])
        if state_refs is not None:
            state_ref_set = set(state_refs)
            affected_state_refs = [
                state_ref for state_ref in affected_state_refs if state_ref in state_ref_set
            ]
        return {
            "id": recent_change["id"],
            "summary": recent_change["summary"],
            "persona_route": {
                "persona_ref": persona_ref,
                "relevance_tier": route["relevance_tier"] if route else "ambient",
                "routing_reason": route["routing_reason"] if route else "No route recorded.",
            },
            "source_refs": list(recent_change["source_refs"]),
            "affected_state_refs": affected_state_refs,
        }

    def _persist(self, package: JsonObject) -> JsonObject:
        errors = validate_schema(package, self.schemas["context_package"])
        if errors:
            raise ContextPackageValidationError(errors)
        self.stores.context_packages.create(package)
        return package


def _route_for_persona(recent_change: JsonObject, persona_ref: str) -> JsonObject | None:
    for route in recent_change["candidate_persona_routes"]:
        if route["persona_ref"] == persona_ref:
            return route
    return None


def _unique(*groups: list[str]) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for value in group:
            if value in seen:
                continue
            seen.add(value)
            values.append(value)
    return values
