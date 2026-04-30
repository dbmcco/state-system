from __future__ import annotations

from copy import deepcopy
import json
from typing import Iterable

from state_system.contracts import validate_schema
from state_system.materializer import PROTECTED_PATCH_FIELDS, materialize_snapshot
from state_system.stores import JsonObject, RecordNotFoundError, StateStoreBundle


class CommitValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("commit validation failed")
        self.errors = tuple(errors)


class Committer:
    def __init__(self, stores: StateStoreBundle, schemas: dict[str, JsonObject]):
        self.stores = stores
        self.schemas = schemas

    def commit(
        self,
        model_output: JsonObject,
        *,
        created_at: str,
        evidence_refs: Iterable[str],
    ) -> JsonObject:
        self._validate_model_output(model_output)
        commit_id = _commit_id(model_output)
        if commit_id in self.stores.commits.list_ids():
            return self.stores.commits.read(commit_id)

        evidence_ref_set = set(evidence_refs)
        pending = _pending_approvals(model_output)
        rejected = self._rejected_proposals(model_output, evidence_ref_set)
        if pending or rejected:
            status = "pending_approval" if pending and not rejected else "rejected"
            queued_rollups = (
                list(model_output["rollup_requests"])
                if status == "pending_approval"
                else []
            )
            result = self._commit_result(
                model_output,
                commit_id=commit_id,
                created_at=created_at,
                status=status,
                accepted_journal_refs=[],
                accepted_memory_refs=[],
                materialized_snapshot_refs=[],
                queued_rollups=queued_rollups,
                pending_approvals=pending,
                rejected_proposals=rejected,
            )
            self._persist_receipt(result)
            return result

        accepted_journal_refs: list[str] = []
        accepted_memory_refs: list[str] = []
        materialized_snapshot_refs: list[str] = []

        for index, proposal in enumerate(model_output["state_proposals"]):
            journal = self._journal_from_proposal(model_output, proposal, index)
            self.stores.journals.create(journal)
            accepted_journal_refs.append(journal["id"])

            snapshot = self.stores.state_objects.read(proposal["target_state_object_id"])
            materialized = materialize_snapshot(snapshot, journal)
            self._replace_record(self.stores.state_objects, materialized)
            materialized_snapshot_refs.append(materialized["id"])

        for index, proposal in enumerate(model_output["memory_proposals"]):
            memory = self._memory_from_proposal(model_output, proposal, index)
            self.stores.memory.create(memory)
            accepted_memory_refs.append(memory["id"])

        status = "accepted" if accepted_journal_refs or accepted_memory_refs else "no_op"
        result = self._commit_result(
            model_output,
            commit_id=commit_id,
            created_at=created_at,
            status=status,
            accepted_journal_refs=accepted_journal_refs,
            accepted_memory_refs=accepted_memory_refs,
            materialized_snapshot_refs=materialized_snapshot_refs,
            queued_rollups=list(model_output["rollup_requests"]),
            pending_approvals=[],
            rejected_proposals=[],
        )
        self._persist_receipt(result)
        return result

    def _validate_model_output(self, model_output: JsonObject) -> None:
        errors = validate_schema(model_output, self.schemas["model_output"])
        if errors:
            raise CommitValidationError(errors)

    def _rejected_proposals(
        self,
        model_output: JsonObject,
        evidence_refs: set[str],
    ) -> list[JsonObject]:
        rejected: list[JsonObject] = []

        for proposal in model_output["state_proposals"]:
            target_ref = proposal["target_state_object_id"]
            try:
                self.stores.state_objects.read(target_ref)
            except RecordNotFoundError:
                rejected.append(
                    _rejection("state", "Target state object does not exist.", target_ref)
                )
                continue

            missing = _missing_refs(proposal["evidence_refs"], evidence_refs)
            if missing:
                rejected.append(
                    _rejection(
                        "state",
                        f"Unresolved evidence refs: {', '.join(missing)}.",
                        target_ref,
                    )
                )

            protected_fields = [
                key for key in proposal["state_patch"] if key in PROTECTED_PATCH_FIELDS
            ]
            if protected_fields:
                rejected.append(
                    _rejection(
                        "state",
                        f"Patch includes protected fields: {', '.join(protected_fields)}.",
                        target_ref,
                    )
                )

        for proposal in model_output["memory_proposals"]:
            missing = _missing_refs(proposal["evidence_refs"], evidence_refs)
            if missing:
                rejected.append(
                    _rejection(
                        "memory",
                        f"Unresolved evidence refs: {', '.join(missing)}.",
                        proposal["agent_ref"],
                    )
                )

        for proposal in model_output["action_proposals"]:
            if proposal["risk"] == "forbidden":
                rejected.append(
                    _rejection("action", "Forbidden action proposal.", _target_ref(proposal))
                )

        return rejected

    def _journal_from_proposal(
        self,
        model_output: JsonObject,
        proposal: JsonObject,
        index: int,
    ) -> JsonObject:
        journal = {
            "id": _indexed_ref(
                model_output["review_signal"].get("journal_entry_refs", []),
                index,
                _journal_id(model_output, proposal),
            ),
            "state_object_id": proposal["target_state_object_id"],
            "created_at": model_output["review_signal"]["created_at"],
            "actor_ref": _actor_ref(model_output),
            "source": "agent_reasoning",
            "trigger_ref": model_output["review_signal"]["trigger_id"],
            "update_class": proposal["update_class"],
            "interpretation": proposal["interpretation"],
            "state_patch": deepcopy(proposal["state_patch"]),
            "evidence_refs": list(proposal["evidence_refs"]),
            "uncertainty": list(proposal["uncertainty"]),
            "rollup_requests": deepcopy(model_output["rollup_requests"]),
            "approval_status": "not_required",
            "proposed_actions": [
                {
                    "summary": action["summary"],
                    "risk": action["risk"],
                    "approval_required": action["approval_required"],
                }
                for action in model_output["action_proposals"]
                if action["risk"] == "low" and not action["approval_required"]
            ],
        }
        self._validate_record(journal, "journal")
        return journal

    def _memory_from_proposal(
        self,
        model_output: JsonObject,
        proposal: JsonObject,
        index: int,
    ) -> JsonObject:
        memory = {
            "id": _indexed_ref(
                model_output["review_signal"].get("memory_entry_refs", []),
                index,
                _memory_id(proposal),
            ),
            "agent_ref": proposal["agent_ref"],
            "created_at": model_output["review_signal"]["created_at"],
            "memory_key": proposal["memory_key"],
            "layer": proposal["layer"],
            "memory_type": proposal["memory_type"],
            "summary": proposal["summary"],
            "content": proposal["content"],
            "confidence": proposal["confidence"],
            "evidence_refs": list(proposal["evidence_refs"]),
            "related_state_refs": list(proposal.get("related_state_refs", [])),
            "promotion_status": proposal["promotion_status"],
        }
        if "supersedes_ref" in proposal:
            memory["supersedes_ref"] = proposal["supersedes_ref"]
        self._validate_record(memory, "memory")
        return memory

    def _commit_result(
        self,
        model_output: JsonObject,
        *,
        commit_id: str,
        created_at: str,
        status: str,
        accepted_journal_refs: list[str],
        accepted_memory_refs: list[str],
        materialized_snapshot_refs: list[str],
        queued_rollups: list[JsonObject],
        pending_approvals: list[JsonObject],
        rejected_proposals: list[JsonObject],
    ) -> JsonObject:
        review_signal = deepcopy(model_output["review_signal"])
        review_signal["journal_entry_refs"] = list(accepted_journal_refs)
        review_signal["memory_entry_refs"] = list(accepted_memory_refs)
        review_signal["rollup_requests"] = deepcopy(queued_rollups)
        if status == "accepted" and queued_rollups:
            review_signal["status"] = "rollup_queued"
        elif status == "accepted":
            review_signal["status"] = "committed"
        elif status == "no_op":
            review_signal["status"] = "no_update_warranted"
        elif status == "pending_approval":
            review_signal["status"] = "pending_approval"
        elif status == "rejected":
            review_signal["status"] = "rejected"

        result = {
            "id": commit_id,
            "model_output_id": model_output["id"],
            "created_at": created_at,
            "status": status,
            "accepted_journal_entry_refs": list(accepted_journal_refs),
            "accepted_memory_entry_refs": list(accepted_memory_refs),
            "materialized_snapshot_refs": list(materialized_snapshot_refs),
            "queued_rollup_requests": deepcopy(queued_rollups),
            "pending_approvals": deepcopy(pending_approvals),
            "rejected_proposals": deepcopy(rejected_proposals),
            "review_signal": review_signal,
        }
        self._validate_record(result, "commit")
        self._validate_record(review_signal, "review_signal")
        return result

    def _persist_receipt(self, result: JsonObject) -> None:
        self.stores.commits.create(result)
        self.stores.review_signals.create(result["review_signal"])

    def _validate_record(self, record: JsonObject, schema_key: str) -> None:
        errors = validate_schema(record, self.schemas[schema_key])
        if errors:
            raise CommitValidationError(errors)

    def _replace_record(self, store, record: JsonObject) -> None:
        path = store.path_for(record["id"])
        with path.open("w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2, sort_keys=True)
            handle.write("\n")


def _pending_approvals(model_output: JsonObject) -> list[JsonObject]:
    pending: list[JsonObject] = []
    for proposal in model_output["state_proposals"]:
        if proposal["approval_required"]:
            pending.append(
                _pending("state", proposal["interpretation"], proposal["target_state_object_id"])
            )
    for proposal in model_output["memory_proposals"]:
        if proposal["approval_required"]:
            pending.append(_pending("memory", proposal["summary"], proposal["agent_ref"]))
    for proposal in model_output["promotion_proposals"]:
        pending.append(
            _pending("promotion", proposal["rationale"], proposal["target_state_object_id"])
        )
    for proposal in model_output["action_proposals"]:
        if proposal["approval_required"] or proposal["risk"] == "high":
            pending.append(_pending("action", proposal["summary"], _target_ref(proposal)))
    return pending


def _pending(proposal_type: str, summary: str, target_ref: str) -> JsonObject:
    return {
        "proposal_type": proposal_type,
        "summary": summary,
        "reason": f"{proposal_type} proposal requires approval before commit.",
        "target_ref": target_ref,
    }


def _rejection(proposal_type: str, reason: str, target_ref: str) -> JsonObject:
    return {
        "proposal_type": proposal_type,
        "summary": reason,
        "reason": reason,
        "target_ref": target_ref,
    }


def _missing_refs(required_refs: list[str], available_refs: set[str]) -> list[str]:
    return [ref for ref in required_refs if ref not in available_refs]


def _commit_id(model_output: JsonObject) -> str:
    output_id = model_output["id"]
    if output_id.startswith("model_output."):
        return f"commit.{output_id[len('model_output.'):]}"
    return f"commit.{output_id}"


def _journal_id(model_output: JsonObject, proposal: JsonObject) -> str:
    return f"journal.{_strip_prefix(proposal['target_state_object_id'], 'state.')}.{_slug(model_output['id'])}"


def _memory_id(proposal: JsonObject) -> str:
    return f"memory.{_strip_prefix(proposal['agent_ref'], 'persona.')}.{proposal['memory_key']}"


def _actor_ref(model_output: JsonObject) -> str:
    output_id = model_output["id"]
    parts = output_id.split(".")
    if len(parts) >= 2 and parts[0] == "model_output":
        return f"persona.{parts[1]}"
    return "agent.unknown"


def _indexed_ref(refs: list[str], index: int, fallback: str) -> str:
    if index < len(refs):
        return refs[index]
    return fallback


def _target_ref(proposal: JsonObject) -> str:
    target = proposal.get("target", {})
    if isinstance(target, dict):
        value = (
            target.get("state_object_id")
            or target.get("target_ref")
            or target.get("owner_ref")
        )
        if isinstance(value, str):
            return value
    return ""


def _strip_prefix(value: str, prefix: str) -> str:
    if value.startswith(prefix):
        return value[len(prefix) :]
    return value


def _slug(value: str) -> str:
    return value.replace("model_output.", "").replace(".", "-")
