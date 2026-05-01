from __future__ import annotations

from state_system.stores import JsonObject, RecordExistsError, StateStoreBundle


def seed_repo_runtime(
    stores: StateStoreBundle,
    *,
    repo_ref: str,
    created_at: str,
) -> JsonObject:
    state_object = _repo_runtime_state(repo_ref, created_at)
    created_refs: list[str] = []
    try:
        stores.state_objects.create(state_object)
        created_refs.append(state_object["id"])
    except RecordExistsError:
        pass
    return {
        "repo_ref": repo_ref,
        "created_state_object_refs": created_refs,
        "existing_state_object_refs": (
            [] if created_refs else [state_object["id"]]
        ),
    }


def _repo_runtime_state(repo_ref: str, created_at: str) -> JsonObject:
    slug = repo_ref.removeprefix("repo.")
    return {
        "id": f"state.repo.{slug}.runtime",
        "type": "capability",
        "primary_family": "work",
        "secondary_families": ["operating"],
        "state_traits": ["dynamic"],
        "scope": repo_ref,
        "owner_refs": ["persona.patrick"],
        "as_of": created_at,
        "summary": f"{repo_ref} runtime state is seeded for live Git source-event trials.",
        "status": "seeded",
        "situations": [
            {
                "id": f"situation.{slug}.runtime-live-trial",
                "label": "Runtime live trial is available",
                "state": "watching",
                "rationale": (
                    "The repo has baseline state so real Git commits can be "
                    "ingested and packaged without manual state-file setup."
                ),
            }
        ],
        "goals": [
            "Track real repo source events through the State System runtime loop."
        ],
        "blockers": [],
        "open_questions": [
            "Which real commits should become Patrick operational context?",
            "Which real commits are market-facing enough for Laura?",
        ],
        "next_actions": [
            {
                "id": f"action.{slug}.ingest-live-git-commit",
                "summary": "Ingest one real Git commit and inspect persona packages.",
                "owner_ref": "persona.patrick",
                "status": "active",
            }
        ],
        "evidence_refs": [repo_ref],
        "parent_state_refs": [],
        "child_state_refs": [],
        "latest_journal_entry_id": "",
    }
