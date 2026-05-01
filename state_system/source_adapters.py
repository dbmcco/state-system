from __future__ import annotations

from state_system.stores import JsonObject


def git_commit_to_source_event(
    commit: JsonObject,
    *,
    repo_ref: str,
    observed_at: str,
    candidate_state_refs: list[str] | None = None,
    governance_refs: list[str] | None = None,
) -> JsonObject:
    sha = _required_string(commit, "sha")
    authored_at = _required_string(commit, "authored_at")
    subject = _required_string(commit, "subject")
    changed_files = _string_list(commit.get("changed_files", []))
    source_ref = f"git:{repo_ref}:commit:{sha}"
    author_ref = _author_ref(commit)

    return {
        "id": f"source.git.{repo_ref}.{sha}",
        "source_system": "git",
        "source_event": "commit.created",
        "source_event_id": source_ref,
        "occurred_at": authored_at,
        "observed_at": observed_at,
        "actor_ref": author_ref,
        "summary": f"Git commit {sha} in {repo_ref}: {subject}",
        "source_refs": [source_ref],
        "change": {
            "kind": "record_created",
            "object_ref": repo_ref,
            "field": "commit",
            "old_value": None,
            "new_value": {
                "sha": sha,
                "author_name": commit.get("author_name", ""),
                "author_email": commit.get("author_email", ""),
                "subject": subject,
                "body": commit.get("body", ""),
                "changed_files": changed_files,
            },
            "payload_summary": _payload_summary(subject, changed_files),
        },
        "candidate_state_refs": list(candidate_state_refs or []),
        "candidate_persona_refs": [],
        "governance_refs": list(governance_refs or []),
        "idempotency": {
            "key": source_ref,
            "dedupe_strategy": "source_event_id",
            "semantic_fingerprint": source_ref,
        },
        "sync_context": {
            "sync_id": f"git-commit-{sha}",
            "cursor": sha,
            "source_watermark": authored_at,
            "partial": False,
            "confidence": "high",
        },
    }


def _required_string(value: JsonObject, key: str) -> str:
    candidate = value.get(key)
    if not isinstance(candidate, str) or not candidate:
        raise ValueError(f"git commit metadata must include non-empty {key}")
    return candidate


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("git commit changed_files must be a list of strings")
    return list(value)


def _author_ref(commit: JsonObject) -> str:
    email = commit.get("author_email")
    if isinstance(email, str) and email:
        return f"git.author.{email}"
    name = commit.get("author_name")
    if isinstance(name, str) and name:
        return f"git.author.{name}"
    return "git.author.unknown"


def _payload_summary(subject: str, changed_files: list[str]) -> str:
    if not changed_files:
        return subject
    return f"{subject} ({len(changed_files)} changed files)"
