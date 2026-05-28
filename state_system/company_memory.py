from __future__ import annotations

from state_system.contracts import JsonObject
from state_system.crm_operating_picture import build_crm_operating_picture_summary


def build_company_memory_read_model(
    company_memory: JsonObject,
    crm_operating_picture: JsonObject,
) -> JsonObject:
    evidence_refs = sorted(
        {
            *company_memory["evidence_refs"],
            *crm_operating_picture["evidence_refs"],
        }
    )
    return {
        "id": f"company_memory_read_model.{_subject_slug(company_memory['subject_ref'])}",
        "artifact_type": "json_substrate",
        "subject_ref": company_memory["subject_ref"],
        "generated_at": max(
            company_memory["generated_at"],
            crm_operating_picture["generated_at"],
        ),
        "company": {
            "mission": company_memory["mission"],
            "strategy": company_memory["strategy"],
            "projects": company_memory["projects"],
            "organizational_state_refs": company_memory["organizational_state_refs"],
        },
        "crm": {
            "system_of_record_ref": crm_operating_picture["system_of_record_ref"],
            "state_system_role": crm_operating_picture["state_system_role"],
            "relationships": crm_operating_picture["relationships"],
            "opportunities": crm_operating_picture["opportunities"],
            "open_loops": crm_operating_picture["open_loops"],
            "recent_changes": crm_operating_picture["recent_changes"],
            "summary": build_crm_operating_picture_summary(crm_operating_picture),
        },
        "agent_memory": {
            "private_memory_refs": company_memory["agent_memory_refs"],
            "promotion_boundary": (
                "Agent memory remains private or draft until explicit promotion "
                "into organizational state is proposed, evidenced, and accepted."
            ),
        },
        "freshness": {
            "as_of": max(
                company_memory["freshness"]["as_of"],
                crm_operating_picture["freshness"]["as_of"],
            ),
            "stale_after": min(
                company_memory["freshness"]["stale_after"],
                crm_operating_picture["freshness"]["stale_after"],
            ),
            "watermark_refs": sorted(
                {
                    *company_memory["freshness"]["watermark_refs"],
                    *crm_operating_picture["freshness"]["watermark_refs"],
                }
            ),
        },
        "evidence_refs": evidence_refs,
    }


def build_agent_context_packages(read_model: JsonObject) -> dict[str, JsonObject]:
    return {
        "persona.laura.marketing": {
            "id": "context.company-memory.acme.laura.generated",
            "persona_ref": "persona.laura.marketing",
            "source_read_model_ref": read_model["id"],
            "review_goal": (
                "Find marketable proof and narrative signals while preserving "
                "approval boundaries around CRM relationship details."
            ),
            "included_slices": [
                "mission",
                "strategy",
                "relationship_story",
                "marketable_proof_candidate",
            ],
            "evidence_refs": read_model["evidence_refs"],
            "action_boundaries": [
                "No external publication without approval.",
                "Do not treat private agent memory as organizational truth.",
            ],
        },
        "persona.patrick.operations": {
            "id": "context.company-memory.acme.patrick.generated",
            "persona_ref": "persona.patrick.operations",
            "source_read_model_ref": read_model["id"],
            "review_goal": (
                "Find open loops, stale claims, and unsupported CRM follow-up "
                "risks from the same substrate."
            ),
            "included_slices": [
                "crm_open_loop",
                "freshness",
                "source_of_record_boundary",
                "follow_up_risk",
            ],
            "evidence_refs": read_model["evidence_refs"],
            "action_boundaries": [
                "Do not mutate CRM directly.",
                "Propose follow-up or state updates with evidence refs.",
            ],
        },
    }


def _subject_slug(subject_ref: str) -> str:
    return subject_ref.rsplit(".", 1)[-1]
