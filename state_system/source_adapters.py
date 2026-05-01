from __future__ import annotations

from pathlib import Path
import subprocess

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


def git_commit_metadata_from_repo(repo_path: Path, commit_ref: str) -> JsonObject:
    header = _git(
        repo_path,
        "show",
        "--no-patch",
        "--format=%H%x1f%an%x1f%ae%x1f%aI%x1f%s%x1f%b",
        commit_ref,
    ).stdout.rstrip("\n")
    parts = header.split("\x1f", 5)
    if len(parts) != 6:
        raise ValueError(f"unable to parse git commit metadata for {commit_ref}")
    changed_files = _git(
        repo_path,
        "diff-tree",
        "--root",
        "--no-commit-id",
        "--name-only",
        "-r",
        commit_ref,
    ).stdout.splitlines()
    return {
        "sha": parts[0],
        "author_name": parts[1],
        "author_email": parts[2],
        "authored_at": parts[3],
        "subject": parts[4],
        "body": parts[5].strip(),
        "changed_files": sorted(file for file in changed_files if file),
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


def _git(repo_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_path,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
