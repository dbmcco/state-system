from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from state_system.contracts import JsonObject, validate_schema
from state_system.instance_capability import InstanceCapabilityRuntime
from state_system.instance_understanding_surface import (
    build_instance_understanding_surface_read_model,
)
from state_system.stores import StateStoreBundle


class InstanceAgentPackageValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("instance agent package validation failed")
        self.errors = tuple(errors)


class InstanceAgentPackageRuntime:
    def __init__(self, stores: StateStoreBundle):
        self.stores = stores
        self.store = stores.instance_agent_packages

    def build(
        self,
        schemas: dict[str, JsonObject],
        *,
        instance_ref: str,
        agent_ref: str,
        created_at: str,
        persona_ref: str | None = None,
        review_goal: str | None = None,
        package_id: str | None = None,
    ) -> JsonObject:
        surface = build_instance_understanding_surface_read_model(self.stores)
        instance = _instance(surface, instance_ref)
        capability = InstanceCapabilityRuntime(self.stores).read_instance(instance_ref)
        package = _package_from_instance(
            instance=instance,
            capability=capability,
            agent_ref=agent_ref,
            persona_ref=persona_ref,
            created_at=created_at,
            review_goal=review_goal,
            package_id=package_id,
            state_root=self.stores.root,
        )
        errors = validate_schema(package, schemas["instance_agent_package"])
        if errors:
            raise InstanceAgentPackageValidationError(errors)
        self._write(package)
        return package

    def read(self, package_id: str) -> JsonObject:
        return self.store.read(package_id)

    def list_packages(self) -> list[JsonObject]:
        return self.store.replay()

    def export(self, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        read_model = {
            "id": "instance_agent_package_read_model",
            "artifact_type": "json_substrate",
            "packages": self.list_packages(),
        }
        path = output_dir / "instance-agent-packages-read-model.json"
        path.write_text(json.dumps(read_model, indent=2, sort_keys=True) + "\n")
        return path

    def _write(self, package: JsonObject) -> None:
        path = self.store.path_for(package["id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(package, indent=2, sort_keys=True) + "\n")


def _package_from_instance(
    *,
    instance: JsonObject,
    capability: JsonObject,
    agent_ref: str,
    persona_ref: str | None,
    created_at: str,
    review_goal: str | None,
    package_id: str | None,
    state_root: Path | None = None,
) -> JsonObject:
    sources = [_package_source(source) for source in instance["source_readiness"]]
    evidence_refs = sorted(
        {
            evidence_ref
            for source in sources
            for evidence_ref in source.get("evidence_refs", [])
        }
    )
    index_refs = {
        index_ref
        for source in sources
        for index_ref in source.get("index_refs", [])
    }
    gap_refs = sorted(
        {
            gap_ref
            for source in sources
            for gap_ref in source.get("gap_refs", [])
        }
    )
    federated_refs = {
        source["federated_instance"]["source_instance_ref"]
        for source in sources
        if source.get("federated_instance", {}).get("status") == "available"
    }
    question_routes = _question_routes(
        instance_ref=instance["instance_ref"],
        sources=sources,
        state_root=state_root,
    )
    federation_packs = _federation_packs(
        instance_ref=instance["instance_ref"],
        sources=sources,
        routes=question_routes,
    )
    federated_refs.update(_question_route_federated_instance_refs(question_routes))
    federated_refs.update(_federation_pack_remote_instance_refs(federation_packs))
    index_refs.update(_question_route_index_refs(question_routes))
    federated_refs = sorted(federated_refs)
    index_refs = sorted(index_refs)
    resolved_package_id = package_id or _package_id(instance["instance_ref"], agent_ref)
    expired_freshness_refs = _expired_freshness_refs(
        package_id=resolved_package_id,
        sources=sources,
        as_of=created_at,
    )
    requires_refresh = any(
        source["freshness_status"] != "fresh" or source["access_status"] != "passed"
        for source in sources
    ) or bool(expired_freshness_refs)
    selected_persona_ref = persona_ref or _first(capability["identity"].get("primary_agent_refs"))
    return {
        "id": resolved_package_id,
        "package_type": "instance_agent_package",
        "created_at": created_at,
        "instance_ref": instance["instance_ref"],
        "primary_entity_ref": instance["primary_entity_ref"],
        "entity_kind": instance["entity_kind"],
        "agent_context": {
            "agent_ref": agent_ref,
            "persona_ref": selected_persona_ref,
            "summary": f"Agent package over {instance['name']}.",
        },
        "review_goal": review_goal
        or "Review the instance state using only visible readiness, freshness, evidence, and gap metadata.",
        "source_context": {
            "source_readiness": sources,
            "source_gap_refs": gap_refs,
        },
        "evidence_context": {
            "index_refs": index_refs,
            "evidence_refs": evidence_refs,
            "federated_instance_refs": federated_refs,
            "unresolved_evidence_refs": [],
        },
        "governance_context": {
            "governance_refs": capability["governance"]["governance_refs"],
            "constraints": capability["runtime_constraints"]["constraints"],
            "protected_action_authorized_by": capability["invariant"][
                "protected_action_authorized_by"
            ],
        },
        "available_actions": capability["action_surface"]["action_refs"],
        "federation_packs": federation_packs,
        "question_routes": question_routes,
        "open_questions": _open_questions(sources),
        "freshness": {
            "generated_at": created_at,
            "requires_refresh_before_external_action": requires_refresh,
            "watermark_refs": _watermark_refs(instance["source_readiness"]),
            "expired_freshness_refs": expired_freshness_refs,
        },
        "invariant": {
            "agent_package_executes_retrieval": False,
            "agent_package_authorizes_execution": False,
            "source_gaps_are_visible": True,
        },
    }


def _package_source(source: JsonObject) -> JsonObject:
    connector_type = source["connector_type"]
    freshness_record = source.get("freshness_record", {})
    preflight_records = source.get("preflight_records", [])
    source_module_ref = f"source_module.{connector_type}"
    packaged = {
        "connector_ref": source["connector_ref"],
        "connector_type": connector_type,
        "source_ref": source["source_ref"],
        "source_module_ref": source.get("source_module_ref", source_module_ref),
        "module_registry_ref": source.get(
            "module_registry_ref",
            "source_module_registry.core_connectors",
        ),
        "module_mode": source.get("module_mode", _module_mode(source)),
        "checked_at": freshness_record.get("checked_at")
        or _latest_preflight_checked_at(preflight_records),
        "source_watermark": freshness_record.get("source_watermark", ""),
        "stale_after": freshness_record.get("stale_after", ""),
        "preflight_contract_ref": f"{source_module_ref}.preflight",
        "freshness_contract_ref": f"{source_module_ref}.freshness",
        "gap_behavior_ref": f"{source_module_ref}.gap_behavior",
        "usable_access_status": _usable_access_status(source),
        "access_status": source["access_status"],
        "freshness_status": source["freshness_status"],
        "index_status": source["index_status"],
        "understanding_status": source["understanding_status"],
        "index_refs": source.get("index_refs", []),
        "gap_refs": [gap["gap_ref"] for gap in source.get("gaps", [])],
        "evidence_refs": _source_evidence_refs(source),
    }
    if source.get("artifact_generated_at"):
        packaged["artifact_generated_at"] = source["artifact_generated_at"]
    if source.get("planned_missing_reason"):
        packaged["planned_missing_reason"] = source["planned_missing_reason"]
    elif packaged["access_status"] not in {"passed", "available"}:
        packaged["planned_missing_reason"] = (
            f"{source['connector_ref']} access is {packaged['access_status']}."
        )
    if source.get("pipeline_dependency"):
        packaged["pipeline_dependency"] = source["pipeline_dependency"]
    elif connector_type == "docs":
        packaged["pipeline_dependency"] = "document_processing_pipeline"
    elif connector_type == "local_path" and "transcript" in source["source_ref"]:
        packaged["pipeline_dependency"] = "raw_transcript_ingest"
    if "federated_instance" in source:
        packaged["federated_instance"] = source["federated_instance"]
    return packaged


def _module_mode(source: JsonObject) -> str:
    connector_type = source["connector_type"]
    source_ref = source["source_ref"]
    if connector_type == "state_system_instance":
        return "federated_query"
    if connector_type == "relationship_substrate" and source.get("federated_instance"):
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
    if connector_type in {"docs"}:
        return "generated_read_model"
    if connector_type == "local_path" and source_ref.startswith("state-system-instance:"):
        return "federated_query"
    return source.get("access_mode", "declared")


def _usable_access_status(source: JsonObject) -> str:
    if source["access_status"] != "passed":
        return "not_usable"
    if source["index_status"] in {"missing", "failed"}:
        return "access_passed_index_unusable"
    if source["freshness_status"] in {"failed", "stale", "unknown"}:
        return "usable_with_freshness_gap"
    return "usable"


def _latest_preflight_checked_at(records: list[JsonObject]) -> str:
    checked = sorted(
        record.get("checked_at", "")
        for record in records
        if record.get("checked_at")
    )
    return checked[-1] if checked else ""


def _source_evidence_refs(source: JsonObject) -> list[str]:
    refs = {
        ref
        for record in source.get("preflight_records", [])
        for ref in record.get("evidence_refs", [])
    }
    refs.update(source.get("freshness_record", {}).get("evidence_refs", []))
    return sorted(refs)


def _expired_freshness_refs(
    *,
    package_id: str,
    sources: list[JsonObject],
    as_of: str,
) -> list[str]:
    return sorted(
        {
            _expired_freshness_ref(package_id, source)
            for source in sources
            if _is_expired(source.get("stale_after", ""), as_of)
        }
    )


def _expired_freshness_ref(package_id: str, source: JsonObject) -> str:
    return ".".join(
        [
            "expired_freshness",
            package_id,
            str(source.get("connector_ref", "")),
            "stale_after",
            str(source.get("stale_after", "")),
        ]
    )


def _is_expired(stale_after: object, as_of: str | None) -> bool:
    if not stale_after or not as_of:
        return False
    stale_after_dt = _parse_timestamp(str(stale_after))
    as_of_dt = _parse_timestamp(as_of)
    if stale_after_dt is None or as_of_dt is None:
        return False
    return stale_after_dt < as_of_dt


def _parse_timestamp(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _question_routes(
    *,
    instance_ref: str,
    sources: list[JsonObject],
    state_root: Path | None = None,
) -> list[JsonObject]:
    connector_refs = {source["connector_ref"] for source in sources}
    routes: list[JsonObject] = []
    if {
        "connector.personal.relationship_substrate",
        "connector.personal.msgvault",
    }.issubset(connector_refs):
        routes.append(
            {
                "id": "question_route.personal.relationship_follow_up_triage",
                "intent": "Find relationship follow-up threads that may deserve action.",
                "applies_to": [
                    "Do I have any relationship follow-up threads I should take action on?",
                    "Who should I follow up with?",
                    "What relationship loops are warm, stale, or unresolved?",
                ],
                "source_order": [
                    "connector.personal.relationship_substrate",
                    "connector.personal.agentmem",
                    "connector.personal.paia_memory.samantha",
                    "connector.personal.paia_memory.owner",
                    "connector.personal.msgvault",
                    "connector.personal.workboard",
                    "connector.personal.sampleco_state_system",
                ],
                "tool_refs": [
                    "tool.relationship_substrate.operating_picture",
                    "tool.relationship_substrate.list_subject_notes",
                    "agentmem:service:local",
                    "tool.paia_memory.retrieve_summary",
                    "tool.paia_memory.retrieve_facets",
                    "tool.paia_memory.retrieve_turns",
                    "tool.paia.msgvault.search",
                    "tool.paia.workboard.read",
                    "tool.state_system.instance_read",
                ],
                "tool_action_refs": [
                    "tool_action.relationship_substrate.operating_picture",
                    "tool_action.relationship_substrate.list_subject_notes",
                    "tool_action.msgvault.search",
                    "tool_action.agentmem.search",
                    "tool_action.paia_memory.read",
                    "tool_action.paia_workboard.read",
                    "tool_action.state_system_instance.read",
                ],
                "route_contract_ref": "question_route_contract.personal.relationship_follow_up_triage",
                "required_source_coverage": [
                    {
                        "coverage_ref": "coverage.personal.relationship_core",
                        "connector_refs": [
                            "connector.personal.relationship_substrate",
                            "connector.personal.msgvault",
                        ],
                        "source_module_refs": [
                            "source_module.relationship_substrate",
                            "source_module.msgvault",
                        ],
                        "minimum_status": "usable_with_visible_gaps",
                    }
                ],
                "required_tools": [
                    "tool.relationship_substrate.operating_picture",
                    "tool.relationship_substrate.list_subject_notes",
                    "tool.paia.msgvault.search",
                ],
                "optional_tools": [
                    "agentmem:service:local",
                    "tool.paia_memory.retrieve_summary",
                    "tool.paia_memory.retrieve_facets",
                    "tool.paia_memory.retrieve_turns",
                    "tool.paia.workboard.read",
                    "tool.state_system.instance_read",
                ],
                "optional_external_context_tools": ["calendar"],
                "required_actions": [
                    "Start with relationship_substrate operating_picture for people, organizations, interaction freshness, and operating-picture context.",
                    "Use subject-level relationship notes as example owner's explicit relationship corrections when they are available.",
                    "Use memory_search or agentmem relationship context when available before deciding a follow-up is missing or important.",
                    "Use PAIA memory Samantha conversation summaries, facets, and recent turns for Sam continuity context, and use example owner facets as separate owner context with tenant labels preserved.",
                    "Use msgvault for concrete thread evidence; cite message/thread evidence refs and avoid broad keyword-only conclusions.",
                    "Check workboard for existing follow-up tasks or agent-owned obligations before proposing a new action.",
                    "Use calendar only as schedule context; it must not be the sole relationship follow-up evidence source when broader sources are available.",
                    "Include federated SampleCo state when the relationship or obligation is work-related.",
                ],
                "answer_contract": [
                    "Return ranked follow-up candidates, not just calendar items.",
                    "For each candidate include person or organization, reason, source freshness, evidence refs, and the safest next action.",
                    "Separate direct evidence from model interpretation.",
                    "Say when no strong candidate is proven and name which source coverage limits that conclusion.",
                    "Do not produce a calendar-only answer when relationship_substrate, memory, email/msgvault, or workboard coverage is available.",
                ],
                "answer_contract_policy": {
                    "requires_evidence_refs": True,
                    "requires_source_freshness_summary": True,
                    "direct_evidence_vs_interpretation": True,
                    "subject_note_policy": [
                        "subject_note_context_demote_explain_not_hide"
                    ],
                    "rules": [
                        "Return ranked follow-up candidates, not just calendar items.",
                        "Do not produce a calendar-only answer when relationship substrate, memory, email/msgvault, or workboard coverage is available.",
                    ],
                },
                "fallback_policy": {
                    "policy": "If relationship substrate or msgvault is missing, answer with the missing-source limitation instead of pretending the calendar is enough.",
                    "repair_gate": "Ask for or run source repair when required relationship sources are unavailable.",
                    "external_context_rule": "calendar_is_schedule_context_not_relationship_evidence",
                },
                "gap_behavior": {
                    "when_required_source_missing": "Say the route is undercovered and identify missing relationship/email sources.",
                    "when_source_stale": "Use stale sources only with explicit freshness caveat.",
                    "relevant_gap_refs": _route_gap_refs(
                        sources,
                        {
                            "connector.personal.relationship_substrate",
                            "connector.personal.msgvault",
                            "connector.personal.agentmem",
                            "connector.personal.paia_memory.samantha",
                            "connector.personal.paia_memory.owner",
                            "connector.personal.workboard",
                            "connector.personal.sampleco_state_system",
                        },
                    ),
                },
            }
        )
    if {
        "connector.personal.beeper.imessage",
        "connector.personal.beeper.whatsapp",
    }.issubset(connector_refs):
        routes.append(
            {
                "id": "question_route.personal.messaging_context",
                "intent": "Use private messaging context from Beeper-backed iMessage and WhatsApp when a personal-state question needs chat evidence.",
                "applies_to": [
                    "Can you check my iMessage or WhatsApp context?",
                    "What did I discuss with this person over chat?",
                    "Do any message threads need follow-up?",
                ],
                "source_order": [
                    "connector.personal.relationship_substrate",
                    "connector.personal.beeper.imessage",
                    "connector.personal.beeper.whatsapp",
                    "connector.personal.msgvault",
                ],
                "tool_refs": ["tool.beeper.search"],
                "tool_action_refs": ["tool_action.beeper_messaging.search"],
                "route_contract_ref": "question_route_contract.personal.messaging_context",
                "required_source_coverage": [
                    {
                        "coverage_ref": "coverage.personal.private_messaging",
                        "connector_refs": [
                            "connector.personal.beeper.imessage",
                            "connector.personal.beeper.whatsapp",
                        ],
                        "source_module_refs": ["source_module.beeper_messaging"],
                        "minimum_status": "usable_with_visible_gaps",
                    }
                ],
                "required_tools": ["tool.beeper.search"],
                "answer_contract_policy": {
                    "requires_evidence_refs": True,
                    "requires_source_freshness_summary": True,
                    "direct_evidence_vs_interpretation": True,
                    "bounded_private_message_excerpts": True,
                },
                "fallback_policy": {
                    "policy": "If a Beeper network is missing or stale, say which network is limited and fall back to relationship_substrate or msgvault only with that caveat.",
                    "fallback_tool_refs": [
                        "tool.relationship_substrate.operating_picture",
                        "tool.paia.msgvault.search",
                    ],
                },
                "gap_behavior": {
                    "access_gap": "Do not infer chat history from account presence alone.",
                    "freshness_gap": "Use message evidence only with the visible stale watermark.",
                    "privacy_boundary": "Never materialize broad raw chat exports in the agent package.",
                },
            }
        )
    if "connector.personal.relationship_substrate" in connector_refs:
        routes.append(
            {
                "id": "question_route.personal.small_consulting_firm_contacts",
                "intent": "Find history-backed contacts at smaller consulting, advisory, agency, or specialist operating firms.",
                "applies_to": [
                    "Do I know anybody at smaller consulting firms?",
                    "Who do I know at smaller consulting firms?",
                    "Who do I know at boutique consulting or advisory firms?",
                    "Which smaller specialist consulting or advisory firms are already in my network?",
                ],
                "source_order": [
                    "connector.personal.relationship_substrate",
                    "connector.personal.msgvault",
                    "connector.personal.agentmem",
                    "connector.personal.paia_memory.samantha",
                    "connector.personal.paia_memory.owner",
                    "connector.personal.workboard",
                    "connector.personal.sampleco_state_system",
                ],
                "tool_refs": [
                    "tool.relationship_substrate.search_small_consulting_firm_contacts",
                    "tool.relationship_substrate.search_history_backed_people",
                    "tool.relationship_substrate.list_subject_notes",
                    "tool.paia.msgvault.search",
                    "agentmem:service:local",
                    "tool.paia_memory.retrieve_summary",
                    "tool.paia_memory.retrieve_facets",
                    "tool.paia.workboard.read",
                ],
                "tool_action_refs": [
                    "tool_action.relationship_substrate.search_small_consulting_firm_contacts",
                    "tool_action.relationship_substrate.list_subject_notes",
                    "tool_action.relationship_substrate.search_history_backed_people",
                    "tool_action.msgvault.search",
                    "tool_action.agentmem.search",
                    "tool_action.paia_memory.read",
                    "tool_action.paia_workboard.read",
                ],
                "capability_refs": [
                    "capability.personal.relationship_substrate.search_small_consulting_firm_contacts",
                    "capability.personal.relationship_substrate.list_subject_notes",
                ],
                "route_contract_ref": "question_route_contract.personal.small_consulting_firm_contacts",
                "required_source_coverage": [
                    {
                        "coverage_ref": "coverage.personal.relationship_search",
                        "connector_refs": ["connector.personal.relationship_substrate"],
                        "source_module_refs": ["source_module.relationship_substrate"],
                        "minimum_status": "usable_with_visible_gaps",
                    }
                ],
                "required_tools": [
                    "tool.relationship_substrate.search_small_consulting_firm_contacts",
                    "tool.relationship_substrate.list_subject_notes",
                ],
                "optional_tools": [
                    "tool.relationship_substrate.search_history_backed_people",
                    "tool.paia.msgvault.search",
                    "agentmem:service:local",
                    "tool.paia_memory.retrieve_summary",
                    "tool.paia_memory.retrieve_facets",
                    "tool.paia.workboard.read",
                    "tool.state_system.instance_read",
                ],
                "required_actions": [
                    "Use relationship_substrate search_small_consulting_firm_contacts before making a candidate list.",
                    "If the default action is unavailable, use relationship_substrate search_history_backed_people with actual_employee_count and consultant_count enrichment filters.",
                    "Use enrichment-backed organization filters for actual employee count and consultant/team count; do not rely on keyword-only matching.",
                    "Interpret returned subject notes as relationship-context corrections, not canonical profile facts or broad category filters.",
                    "If a subject note says the contact or organization is not a good fit for the requested context, do not lead with it as a recommended candidate.",
                    "Treat results as relationship candidates requiring cited evidence, not outreach approval.",
                    "Use msgvault/email to validate concrete relationship history before treating a contact as warm.",
                    "Use memory_search or agentmem for known relationship context when available.",
                    "Use PAIA memory Samantha facets and owner facets as separately labeled context without promoting private facets or raw turns to relationship facts.",
                    "Check workboard for existing outreach tasks or constraints before suggesting next steps.",
                    "Use SampleCo state only to verify a specific obligation or work context after candidates are found.",
                ],
                "answer_contract": [
                    "Return contacts with person, organization, enrichment fields used, relationship evidence, and source freshness.",
                    "When a subject note changes context fit, demote or explain that person or organization for the specific context instead of hiding a broad class of contacts.",
                    "Separate proven enrichment fields from model interpretation of whether the firm is a consulting/advisory fit.",
                    "Name coverage gaps when the relationship substrate query is unavailable or sparse.",
                ],
                "answer_contract_policy": {
                    "requires_evidence_refs": True,
                    "requires_source_freshness_summary": True,
                    "direct_evidence_vs_interpretation": True,
                    "subject_note_policy": [
                        "subject_note_context_demote_explain_not_hide"
                    ],
                    "rules": [
                        "Return candidates with enrichment fields, relationship evidence, and context-fit caveats."
                    ],
                },
                "fallback_policy": {
                    "policy": "Use search_history_backed_people only as the declared backing surface with enrichment filters.",
                    "repair_gate": "Do not answer from keyword-only email search when enrichment-backed relationship search is unavailable.",
                    "fallback_tool_refs": [
                        "tool.relationship_substrate.search_history_backed_people"
                    ],
                },
                "gap_behavior": {
                    "when_required_source_missing": "Say relationship search is unavailable and avoid fabricating candidates.",
                    "when_source_stale": "Name relationship index freshness before ranking candidates.",
                    "relevant_gap_refs": _route_gap_refs(
                        sources,
                        {
                            "connector.personal.relationship_substrate",
                            "connector.personal.msgvault",
                            "connector.personal.agentmem",
                            "connector.personal.paia_memory.samantha",
                            "connector.personal.paia_memory.owner",
                            "connector.personal.workboard",
                            "connector.personal.sampleco_state_system",
                        },
                    ),
                },
            }
        )
    if instance_ref == "state_instance.sampleco":
        routes.append(
            {
                "id": "question_route.sampleco.relationship_follow_up_triage",
                "intent": "Find SampleCo relationship-backed work follow-ups.",
                "source_order": [
                    "connector.sampleco.state_system",
                    "connector.sampleco.msgvault",
                    "connector.sampleco.linear",
                ],
                "required_actions": [
                    "Use interpreted SampleCo state for active obligations and relationship-sensitive work.",
                    "Use msgvault only as cited thread evidence, respecting freshness status.",
                    "Use Linear or Workgraph task state for owned internal follow-ups.",
                ],
                "answer_contract": [
                    "Return work follow-up candidates with owners, evidence refs, and approval boundaries.",
                    "Do not mix in personal personal state sources unless explicitly federated into SampleCo.",
                ],
                "route_contract_ref": "question_route_contract.sampleco.relationship_follow_up_triage",
                "required_source_coverage": [
                    {
                        "coverage_ref": "coverage.sampleco.company_follow_up",
                        "connector_refs": [
                            "connector.sampleco.state_system",
                            "connector.sampleco.msgvault",
                        ],
                        "source_module_refs": [
                            "source_module.state_system_instance",
                            "source_module.msgvault",
                        ],
                        "minimum_status": "usable_with_visible_gaps",
                    }
                ],
                "required_tools": ["tool.state_system.instance_read"],
                "optional_tools": ["tool.paia.msgvault.search", "tool.linear.search"],
                "tool_action_refs": ["tool_action.state_system_instance.read"],
                "fallback_policy": {
                    "policy": "If SampleCo interpreted state is stale or missing, answer with company source gap caveats.",
                    "repair_gate": "Do not use personal sources unless an explicit federated route applies.",
                },
                "answer_contract_policy": {
                    "requires_evidence_refs": True,
                    "requires_source_freshness_summary": True,
                    "direct_evidence_vs_interpretation": True,
                    "rules": [
                        "Return work follow-up candidates with owners, evidence refs, and approval boundaries."
                    ],
                },
                "gap_behavior": {
                    "when_required_source_missing": "Declare SampleCo follow-up route undercovered.",
                    "when_source_stale": "Name stale company source before recommending action.",
                    "relevant_gap_refs": _route_gap_refs(
                        sources,
                        {
                            "connector.sampleco.state_system",
                            "connector.sampleco.msgvault",
                            "connector.sampleco.linear",
                        },
                    ),
                },
            }
        )
        routes.append(
            {
                "id": "question_route.sampleco.federated_relationship_index",
                "intent": "Use example owner long-history relationship evidence for SampleCo relationship and business-development questions when contact context matters.",
                "source_order": [
                    "connector.sampleco.state_system",
                    "connector.sampleco.msgvault",
                    "connector.sampleco.folio",
                    "query_surface.federated.relationship_index.search",
                ],
                "tool_refs": [
                    "tool.relationship_substrate.search_small_consulting_firm_contacts"
                ],
                "tool_action_refs": [
                    "tool_action.relationship_substrate.search_small_consulting_firm_contacts"
                ],
                "capability_refs": [
                    "capability.federated.relationship_index.search_small_consulting_firm_contacts"
                ],
                "route_contract_ref": "question_route_contract.sampleco.federated_relationship_index",
                "module_modes": [
                    {
                        "source_module_ref": "source_module.relationship_substrate",
                        "mode": "federated_query",
                    }
                ],
                "required_source_coverage": [
                    {
                        "coverage_ref": "coverage.sampleco.company_context",
                        "connector_refs": [
                            "connector.sampleco.state_system",
                            "connector.sampleco.msgvault",
                            "connector.sampleco.folio",
                        ],
                        "source_module_refs": [
                            "source_module.state_system_instance",
                            "source_module.msgvault",
                            "source_module.folio",
                        ],
                        "minimum_status": "usable_with_visible_gaps",
                    },
                    {
                        "coverage_ref": "coverage.sampleco.federated_relationship_context",
                        "connector_refs": [
                            "connector.federated.sample_personal.relationship_substrate"
                        ],
                        "source_module_refs": ["source_module.relationship_substrate"],
                        "minimum_status": "declared_governed_route",
                    },
                ],
                "required_tools": [
                    "tool.relationship_substrate.search_small_consulting_firm_contacts"
                ],
                "query_route": {
                    "status": "declared_governed_route",
                    "query_surface_ref": "query_surface.federated.relationship_index.search",
                    "index_ref": "index.federated.sample_personal.relationship_index",
                    "source_ref": "relationship_index:sample_personal_long_history",
                    "source_instance_ref": "state_instance.sample_personal",
                    "local_materialization": False,
                    "boundaries": [
                        "Query on demand; do not copy raw personal relationship records into SampleCo.",
                        "Use returned evidence as federated relationship context, not deterministic scoring.",
                        "Use subject-level relationship notes for context-specific corrections; do not apply broad hidden category exclusions or treat them as canonical profile facts.",
                        "Do not route through personal media, health, fitness, or other non-SampleCo source surfaces.",
                        "Prefer SampleCo company evidence first when the question is directly about active SampleCo work.",
                    ],
                },
                "federated_query": {
                    "source_instance_ref": "state_instance.sample_personal",
                    "query_surface_ref": "query_surface.federated.relationship_index.search",
                    "index_ref": "index.federated.sample_personal.relationship_index",
                    "local_materialization": False,
                    "boundaries": [
                        "Query on demand; do not copy raw personal relationship records into SampleCo.",
                        "Use subject-note context as context-specific correction evidence, not hidden filters.",
                    ],
                },
                "required_actions": [
                    "Search ready SampleCo company surfaces for active obligations and company evidence.",
                    "Use the federated relationship-index route only when relationship history would materially improve the answer.",
                    "For smaller consulting firm questions, call the relationship index with enrichment-backed employee-count and consultant-count filters.",
                    "Cite or summarize returned relationship evidence with source boundaries and explicit gaps.",
                ],
                "answer_contract": [
                    "Use governed relationship-index evidence only as cited federated context for SampleCo relationship or business-development questions.",
                    "Declare the relationship-index route unavailable or insufficient when it cannot be queried or does not return relevant evidence.",
                    "Do not materialize raw personal relationship records into SampleCo runtime state.",
                ],
                "answer_contract_policy": {
                    "requires_evidence_refs": True,
                    "requires_source_freshness_summary": True,
                    "direct_evidence_vs_interpretation": True,
                    "subject_note_policy": [
                        "subject_note_context_demote_explain_not_hide"
                    ],
                    "rules": [
                        "Do not materialize raw personal relationship records into SampleCo runtime state."
                    ],
                },
                "fallback_policy": {
                    "policy": "If the federated relationship index is unavailable, answer from SampleCo company sources and explicitly name the missing relationship route.",
                    "repair_gate": "Do not silently replace federated relationship evidence with personal media, health, or unrelated personal state sources.",
                },
                "gap_behavior": {
                    "when_required_source_missing": "Declare the federated route unavailable or insufficient.",
                    "when_source_stale": "Name stale SampleCo company or federated source freshness before using it.",
                    "relevant_gap_refs": _route_gap_refs(
                        sources,
                        {
                            "connector.sampleco.state_system",
                            "connector.sampleco.msgvault",
                            "connector.sampleco.folio",
                            "connector.sampleco.linear",
                            "connector.sampleco.github_org",
                        },
                    ),
                },
            }
        )
    if instance_ref == "state_instance.sampleco":
        routes.append(
            {
                "id": "question_route.sampleco.relationship_follow_up_triage",
                "intent": "Find SampleCo relationship-backed work follow-ups.",
                "source_order": [
                    "connector.sampleco.state_system",
                    "connector.sampleco.msgvault",
                    "connector.sampleco.linear",
                ],
                "required_actions": [
                    "Use interpreted SampleCo state for active obligations and relationship-sensitive work.",
                    "Use msgvault only as cited thread evidence, respecting freshness status.",
                    "Use Linear or Workgraph task state for owned internal follow-ups.",
                ],
                "answer_contract": [
                    "Return work follow-up candidates with owners, evidence refs, and approval boundaries.",
                    "Do not mix in personal personal state sources unless explicitly federated into SampleCo.",
                ],
                "route_contract_ref": "question_route_contract.sampleco.relationship_follow_up_triage",
                "required_source_coverage": [
                    {
                        "coverage_ref": "coverage.sampleco.company_follow_up",
                        "connector_refs": [
                            "connector.sampleco.state_system",
                            "connector.sampleco.msgvault",
                        ],
                        "source_module_refs": [
                            "source_module.state_system_instance",
                            "source_module.msgvault",
                        ],
                        "minimum_status": "usable_with_visible_gaps",
                    }
                ],
                "required_tools": ["tool.state_system.instance_read"],
                "optional_tools": ["tool.paia.msgvault.search", "tool.linear.search"],
                "fallback_policy": {
                    "policy": "If SampleCo interpreted state is stale or missing, answer with company source gap caveats.",
                    "repair_gate": "Do not use personal sources unless an explicit federated route applies.",
                },
                "answer_contract_policy": {
                    "requires_evidence_refs": True,
                    "requires_source_freshness_summary": True,
                    "direct_evidence_vs_interpretation": True,
                    "rules": [
                        "Return work follow-up candidates with owners, evidence refs, and approval boundaries."
                    ],
                },
                "gap_behavior": {
                    "when_required_source_missing": "Declare SampleCo follow-up route undercovered.",
                    "when_source_stale": "Name stale company source before recommending action.",
                    "relevant_gap_refs": _route_gap_refs(
                        sources,
                        {
                            "connector.sampleco.state_system",
                            "connector.sampleco.msgvault",
                            "connector.sampleco.linear",
                        },
                    ),
                },
            }
        )
        routes.append(
            {
                "id": "question_route.sampleco.federated_relationship_index",
                "intent": "Use example owner long-history relationship evidence for SampleCo relationship and business-development questions when contact context matters.",
                "applies_to": [
                    "Who does example owner know at smaller consulting firms who might matter for SampleCo?",
                    "Does example owner already have relationships at boutique consulting or advisory firms relevant to SampleCo?",
                    "Find SampleCo-relevant relationship paths through boutique advisory, agency, or specialist operating firms.",
                ],
                "source_order": [
                    "connector.sampleco.state_system",
                    "connector.sampleco.msgvault",
                    "connector.sampleco.folio",
                    "query_surface.federated.relationship_index.search",
                ],
                "tool_refs": [
                    "tool.relationship_substrate.search_small_consulting_firm_contacts"
                ],
                "tool_action_refs": [
                    "tool_action.relationship_substrate.search_small_consulting_firm_contacts"
                ],
                "capability_refs": [
                    "capability.federated.relationship_index.search_small_consulting_firm_contacts"
                ],
                "route_contract_ref": "question_route_contract.sampleco.federated_relationship_index",
                "module_modes": [
                    {
                        "source_module_ref": "source_module.relationship_substrate",
                        "mode": "federated_query",
                    }
                ],
                "required_source_coverage": [
                    {
                        "coverage_ref": "coverage.sampleco.company_context",
                        "connector_refs": [
                            "connector.sampleco.state_system",
                            "connector.sampleco.msgvault",
                            "connector.sampleco.folio",
                        ],
                        "source_module_refs": [
                            "source_module.state_system_instance",
                            "source_module.msgvault",
                            "source_module.folio",
                        ],
                        "minimum_status": "usable_with_visible_gaps",
                    },
                    {
                        "coverage_ref": "coverage.sampleco.federated_relationship_context",
                        "connector_refs": [
                            "connector.federated.sample_personal.relationship_substrate"
                        ],
                        "source_module_refs": ["source_module.relationship_substrate"],
                        "minimum_status": "declared_governed_route",
                    },
                ],
                "required_tools": [
                    "tool.relationship_substrate.search_small_consulting_firm_contacts"
                ],
                "query_route": {
                    "status": "declared_governed_route",
                    "query_surface_ref": "query_surface.federated.relationship_index.search",
                    "index_ref": "index.federated.sample_personal.relationship_index",
                    "source_ref": "relationship_index:sample_long_history",
                    "source_instance_ref": "state_instance.sample_personal",
                    "local_materialization": False,
                    "boundaries": [
                    "Query on demand; do not copy raw personal relationship records into SampleCo.",
                    "Use returned evidence as federated relationship context, not deterministic scoring.",
                    "Use subject-level relationship notes for context-specific corrections; do not apply broad hidden category exclusions or treat them as canonical profile facts.",
                    "Do not route through personal media, health, fitness, or other non-SampleCo source surfaces.",
                    "Prefer SampleCo company evidence first when the question is directly about active SampleCo work.",
                ],
                },
                "federated_query": {
                    "source_instance_ref": "state_instance.sample_personal",
                    "query_surface_ref": "query_surface.federated.relationship_index.search",
                    "index_ref": "index.federated.sample_personal.relationship_index",
                    "local_materialization": False,
                    "boundaries": [
                        "Query on demand; do not copy raw personal relationship records into SampleCo.",
                        "Use subject-note context as context-specific correction evidence, not hidden filters.",
                    ],
                },
                "required_actions": [
                    "Search ready SampleCo company surfaces for active obligations and company evidence.",
                    "Use the federated relationship-index route only when relationship history would materially improve the answer.",
                    "For smaller consulting firm questions, call the relationship index with enrichment-backed employee-count and consultant-count filters.",
                    "Cite or summarize returned relationship evidence with source boundaries and explicit gaps.",
                ],
                "answer_contract": [
                    "Use governed relationship-index evidence only as cited federated context for SampleCo relationship or business-development questions.",
                    "Declare the relationship-index route unavailable or insufficient when it cannot be queried or does not return relevant evidence.",
                    "Do not materialize raw personal relationship records into SampleCo runtime state.",
                ],
                "answer_contract_policy": {
                    "requires_evidence_refs": True,
                    "requires_source_freshness_summary": True,
                    "direct_evidence_vs_interpretation": True,
                    "subject_note_policy": [
                        "subject_note_context_demote_explain_not_hide"
                    ],
                    "rules": [
                        "Do not materialize raw personal relationship records into SampleCo runtime state."
                    ],
                },
                "fallback_policy": {
                    "policy": "If the federated relationship index is unavailable, answer from SampleCo company sources and explicitly name the missing relationship route.",
                    "repair_gate": "Do not silently replace federated relationship evidence with personal media, health, or unrelated personal state sources.",
                },
                "gap_behavior": {
                    "when_required_source_missing": "Declare the federated route unavailable or insufficient.",
                    "when_source_stale": "Name stale SampleCo company or federated source freshness before using it.",
                    "relevant_gap_refs": _route_gap_refs(
                        sources,
                        {
                            "connector.sampleco.state_system",
                            "connector.sampleco.msgvault",
                            "connector.sampleco.folio",
                            "connector.sampleco.linear",
                            "connector.sampleco.github",
                            "connector.sampleco.repo",
                        },
                    ),
                },
            }
        )
    routes.extend(_state_root_question_routes(state_root, sources))
    return _dedupe_routes(routes)


def _state_root_question_routes(
    state_root: Path | None,
    sources: list[JsonObject],
) -> list[JsonObject]:
    if state_root is None:
        return []
    connector_refs = {source["connector_ref"] for source in sources}
    tool_action_refs_by_tool = _tool_action_refs_by_tool_ref(state_root)
    routes: list[JsonObject] = []
    for registry_path in _registry_paths(state_root, "question-routes"):
        try:
            registry = json.loads(registry_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        for route in registry.get("routes", []):
            if not isinstance(route, dict):
                continue
            if not _route_mentions_sources(route, connector_refs):
                continue
            normalized = _normalize_state_root_question_route(
                route,
                tool_action_refs_by_tool,
            )
            if normalized:
                routes.append(normalized)
    return routes


def _registry_paths(state_root: Path, collection: str) -> list[Path]:
    paths: list[Path] = []
    for directory in (state_root / collection, state_root / "state" / collection):
        if directory.exists():
            paths.extend(sorted(directory.glob("*.json")))
    return paths


def _route_mentions_sources(route: JsonObject, connector_refs: set[str]) -> bool:
    mentioned = set(route.get("source_order", []))
    for coverage in route.get("required_source_coverage", []):
        mentioned.update(coverage.get("connector_refs", []))
    return bool(mentioned & connector_refs)


def _normalize_state_root_question_route(
    route: JsonObject,
    tool_action_refs_by_tool: dict[str, list[str]],
) -> JsonObject | None:
    route_id = route.get("id") or route.get("route_id")
    if not isinstance(route_id, str) or not route_id:
        return None
    normalized = {
        key: value
        for key, value in route.items()
        if key not in {"id", "route_id", "answer_contract"}
    }
    normalized["id"] = route_id
    normalized.setdefault(
        "route_contract_ref",
        route_id.replace("question_route.", "question_route_contract.", 1),
    )
    tool_refs = _route_tool_refs(normalized)
    if tool_refs:
        normalized["tool_refs"] = tool_refs
    normalized.setdefault("tool_action_refs", _route_tool_action_refs(tool_refs, tool_action_refs_by_tool))
    normalized.setdefault("required_actions", _route_required_actions(normalized))
    answer_contract = route.get("answer_contract")
    if isinstance(answer_contract, dict):
        normalized.setdefault("answer_contract_policy", answer_contract)
        normalized["answer_contract"] = answer_contract.get("rules", [])
    elif isinstance(answer_contract, list):
        normalized["answer_contract"] = answer_contract
    else:
        normalized["answer_contract"] = []
    return normalized


def _route_tool_refs(route: JsonObject) -> list[str]:
    refs: list[str] = []
    for field in ("tool_refs", "required_tools", "optional_tools"):
        refs.extend(route.get(field, []))
    return sorted(set(refs))


def _route_tool_action_refs(
    tool_refs: list[str],
    tool_action_refs_by_tool: dict[str, list[str]],
) -> list[str]:
    refs = {
        action_ref
        for tool_ref in tool_refs
        for action_ref in tool_action_refs_by_tool.get(tool_ref, [])
    }
    return sorted(refs)


def _route_required_actions(route: JsonObject) -> list[str]:
    required_tools = route.get("required_tools", [])
    if not required_tools:
        return ["Use declared source coverage and visible gap behavior before answering."]
    return [
        f"Use {tool_ref} only through declared source coverage and visible gap behavior."
        for tool_ref in required_tools
    ]


def _tool_action_refs_by_tool_ref(state_root: Path) -> dict[str, list[str]]:
    action_refs_by_tool: dict[str, set[str]] = {}
    registry_paths = _registry_paths(state_root, "tool-actions")
    core_registry = Path(__file__).resolve().parents[1] / "examples" / "tool-actions" / "tool-action-core-source-tools.json"
    if core_registry.exists():
        registry_paths.append(core_registry)
    for registry_path in registry_paths:
        try:
            registry = json.loads(registry_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        for action in registry.get("actions", []):
            tool_ref = action.get("tool_ref")
            action_ref = action.get("id")
            if isinstance(tool_ref, str) and isinstance(action_ref, str):
                action_refs_by_tool.setdefault(tool_ref, set()).add(action_ref)
    return {
        tool_ref: sorted(action_refs)
        for tool_ref, action_refs in action_refs_by_tool.items()
    }


def _dedupe_routes(routes: list[JsonObject]) -> list[JsonObject]:
    deduped: list[JsonObject] = []
    seen: set[str] = set()
    for route in routes:
        route_id = route.get("id")
        if route_id in seen:
            continue
        seen.add(route_id)
        deduped.append(route)
    return deduped


def _federation_packs(
    *,
    instance_ref: str,
    sources: list[JsonObject],
    routes: list[JsonObject],
) -> list[JsonObject]:
    route_ids = {route["id"] for route in routes}
    connector_refs = {source["connector_ref"] for source in sources}
    packs: list[JsonObject] = []

    personal_state_connector = (
        "connector.personal.sampleco_state_system"
        if "connector.personal.sampleco_state_system" in connector_refs
        else ""
    )
    if personal_state_connector:
        packs.append(
            _federation_pack(
                pack_id="instance_federation_pack.personal_to_sampleco_state",
                status="ready",
                mode="instance_read",
                local_instance_ref=instance_ref,
                remote_instance_refs=["state_instance.sampleco"],
                route_refs=[
                    route_id
                    for route_id in (
                        "question_route.personal.relationship_follow_up_triage",
                        "question_route.personal.small_consulting_firm_contacts",
                    )
                    if route_id in route_ids
                ],
                query_surface_refs=["query_surface.state_system.instance_read"],
                tool_action_refs=["tool_action.state_system.instance_read"],
                source_module_refs=["source_module.state_system_instance"],
                local_materialization=False,
                raw_remote_corpus_policy=(
                    "Raw SampleCo source corpora remain in the SampleCo instance."
                ),
                freshness_status=_source_status(
                    sources,
                    personal_state_connector,
                    "freshness_status",
                ),
                checked_at=_source_status(
                    sources,
                    personal_state_connector,
                    "checked_at",
                ),
                source_watermark=_source_status(
                    sources,
                    personal_state_connector,
                    "source_watermark",
                ),
                gap_refs=_source_gap_refs(sources, personal_state_connector),
                repair_owner="state_instance.sampleco",
                when_unavailable=(
                    "Answer from personal sources and state that SampleCo federation is unavailable."
                ),
                when_stale="Name the stale SampleCo package watermark before relying on it.",
            )
        )

    if "question_route.sampleco.federated_relationship_index" in route_ids:
        packs.append(
            _federation_pack(
                pack_id="instance_federation_pack.sampleco_to_personal_relationship_substrate",
                status="ready",
                mode="source_substrate_query",
                local_instance_ref=instance_ref,
                remote_instance_refs=["state_instance.sample_personal"],
                route_refs=["question_route.sampleco.federated_relationship_index"],
                query_surface_refs=[
                    "query_surface.federated.relationship_index.search"
                ],
                tool_action_refs=[
                    "tool_action.relationship_substrate.search_small_consulting_firm_contacts"
                ],
                source_module_refs=["source_module.relationship_substrate"],
                local_materialization=False,
                raw_remote_corpus_policy=(
                    "No raw personal relationship records may be copied into SampleCo state."
                ),
                freshness_status="fresh",
                checked_at="",
                source_watermark="",
                gap_refs=[],
                repair_owner="state_instance.sample_personal",
                when_unavailable=(
                    "Answer from SampleCo company sources and name the missing relationship federation route."
                ),
                when_stale=(
                    "State the Relationship Substrate freshness gap before using old relationship context."
                ),
                subject_notes_apply=True,
            )
        )

    if instance_ref in {"state_instance.portfolio_co", "state_instance.researchco"}:
        packs.append(
            _federation_pack(
                pack_id="instance_federation_pack.portfolio_to_portfolio_co_researchco",
                status="planned",
                mode="portfolio_rollup",
                local_instance_ref=instance_ref,
                remote_instance_refs=[
                    "state_instance.portfolio_co",
                    "state_instance.researchco",
                ],
                route_refs=["question_route.portfolio.company_readiness_rollup"],
                query_surface_refs=["query_surface.state_system.instance_read"],
                tool_action_refs=["tool_action.state_system.instance_read"],
                source_module_refs=["source_module.state_system_instance"],
                local_materialization=False,
                raw_remote_corpus_policy=(
                    "No company raw corpora are copied into portfolio rollups."
                ),
                freshness_status="unknown",
                checked_at="",
                source_watermark="",
                gap_refs=[
                    f"gap.{instance_ref}.portfolio_federation.package_readiness_unproved"
                ],
                repair_owner=instance_ref,
                when_unavailable=(
                    "Report that portfolio federation is planned and list missing package readiness proofs."
                ),
                when_stale="Regenerate remote package/readiness before portfolio answers.",
            )
        )

    return packs


def _federation_pack(
    *,
    pack_id: str,
    status: str,
    mode: str,
    local_instance_ref: str,
    remote_instance_refs: list[str],
    route_refs: list[str],
    query_surface_refs: list[str],
    tool_action_refs: list[str],
    source_module_refs: list[str],
    local_materialization: bool,
    raw_remote_corpus_policy: str,
    freshness_status: str,
    checked_at: str,
    source_watermark: str,
    gap_refs: list[str],
    repair_owner: str,
    when_unavailable: str,
    when_stale: str,
    subject_notes_apply: bool = False,
) -> JsonObject:
    return {
        "id": pack_id,
        "status": status,
        "federation_mode": mode,
        "local_instance_ref": local_instance_ref,
        "remote_instance_refs": remote_instance_refs,
        "route_refs": route_refs,
        "query_surface_refs": query_surface_refs,
        "tool_action_refs": tool_action_refs,
        "source_module_refs": source_module_refs,
        "materialization_policy": {
            "local_materialization": local_materialization,
            "raw_remote_corpus_policy": raw_remote_corpus_policy,
            "allowed_artifact_types": ["safe_summary", "evidence_ref"],
        },
        "freshness_policy": {
            "freshness_status": freshness_status or "unknown",
            "checked_at": checked_at,
            "source_watermark": source_watermark,
            "stale_after": "",
            "gap_refs": gap_refs,
        },
        "subject_note_policy": {
            "applies": subject_notes_apply,
            "policy": (
                "Subject notes demote or explain context; they are not hidden broad filters."
                if subject_notes_apply
                else "This federation pack does not read or write subject notes."
            ),
        },
        "repair_policy": {
            "owner": repair_owner,
            "when_unavailable": when_unavailable,
            "when_stale": when_stale,
        },
    }


def _source_status(sources: list[JsonObject], connector_ref: str, key: str) -> str:
    for source in sources:
        if source["connector_ref"] == connector_ref:
            return str(source.get(key, ""))
    return ""


def _source_gap_refs(sources: list[JsonObject], connector_ref: str) -> list[str]:
    for source in sources:
        if source["connector_ref"] == connector_ref:
            return source.get("gap_refs", [])
    return []


def _route_gap_refs(sources: list[JsonObject], connector_refs: set[str]) -> list[str]:
    return sorted(
        {
            gap_ref
            for source in sources
            if source["connector_ref"] in connector_refs
            for gap_ref in source.get("gap_refs", [])
        }
    )


def _question_route_federated_instance_refs(routes: list[JsonObject]) -> set[str]:
    return {
        route["query_route"]["source_instance_ref"]
        for route in routes
        if route.get("query_route", {}).get("local_materialization") is False
        and route.get("query_route", {}).get("source_instance_ref")
    }


def _question_route_index_refs(routes: list[JsonObject]) -> set[str]:
    return {
        route["query_route"]["index_ref"]
        for route in routes
        if route.get("query_route", {}).get("local_materialization") is False
        and route.get("query_route", {}).get("index_ref")
    }


def _federation_pack_remote_instance_refs(packs: list[JsonObject]) -> set[str]:
    return {
        remote_ref
        for pack in packs
        for remote_ref in pack.get("remote_instance_refs", [])
    }


def _watermark_refs(sources: list[JsonObject]) -> list[str]:
    return sorted(
        {
            source.get("freshness_record", {}).get("source_watermark", "")
            for source in sources
            if source.get("freshness_record", {}).get("source_watermark")
        }
    )


def _open_questions(sources: list[JsonObject]) -> list[str]:
    return [
        (
            f"{source['connector_ref']} is {source['understanding_status']} "
            f"(access={source['access_status']}, freshness={source['freshness_status']}, "
            f"index={source['index_status']})."
        )
        for source in sources
        if source["understanding_status"] != "ready"
    ]


def _instance(surface: JsonObject, instance_ref: str) -> JsonObject:
    for instance in surface.get("instances", []):
        if instance.get("instance_ref") == instance_ref:
            return instance
    raise ValueError(f"{instance_ref} does not exist in instance understanding surface")


def _package_id(instance_ref: str, agent_ref: str) -> str:
    return f"instance_agent_package.{instance_ref.removeprefix('state_instance.')}.{agent_ref.removeprefix('agent.')}"


def _first(values: list[str]) -> str:
    return values[0] if values else ""
