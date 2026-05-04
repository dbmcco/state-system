from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from state_system.contracts import JsonObject, load_json
from state_system.stores import JsonFileStore, RecordExistsError


FIXTURE_COLLECTIONS = {
    "mission_runs": "mission_runs",
    "agent_runs": "agent_runs",
    "events": "events",
    "observations": "observations",
    "findings": "findings",
    "stumbles": "stumbles",
    "artifacts": "artifacts",
    "governance_receipts": "governance_receipts",
    "commit_results": "commit_results",
    "journal_entries": "journal_entries",
    "memory_entries": "memory_entries",
    "review_signals": "review_signals",
}


@dataclass(frozen=True)
class MissionStoreBundle:
    root: Path

    def __post_init__(self) -> None:
        stores = {
            "mission_runs": "mission-runs",
            "agent_runs": "mission-agent-runs",
            "events": "mission-events",
            "observations": "mission-observations",
            "findings": "mission-findings",
            "stumbles": "mission-stumbles",
            "artifacts": "mission-artifacts",
            "governance_receipts": "mission-governance-receipts",
            "commit_results": "mission-commit-results",
            "journal_entries": "mission-journal-entries",
            "memory_entries": "mission-memory-entries",
            "review_signals": "mission-review-signals",
        }
        for attribute, collection in stores.items():
            object.__setattr__(self, attribute, JsonFileStore(self.root, collection))


def replay_mission_fixture(fixture_path: Path, stores: MissionStoreBundle) -> JsonObject:
    fixture = load_json(fixture_path)
    created = {collection: 0 for collection in FIXTURE_COLLECTIONS}
    skipped = {collection: 0 for collection in FIXTURE_COLLECTIONS}

    for collection, store_name in FIXTURE_COLLECTIONS.items():
        store = getattr(stores, store_name)
        for record in fixture[collection]:
            try:
                store.create(record)
                created[collection] += 1
            except RecordExistsError:
                skipped[collection] += 1

    mission_run_id = fixture["mission_runs"][0]["id"]
    return {
        "mission_run_id": mission_run_id,
        "created": created,
        "skipped": skipped,
    }


def build_mission_read_model(stores: MissionStoreBundle, mission_run_id: str) -> JsonObject:
    mission = stores.mission_runs.read(mission_run_id)
    agent_roster = [
        _agent_summary(stores.agent_runs.read(agent_id))
        for agent_id in mission["agent_run_refs"]
    ]
    timeline = [
        stores.events.read(event_id)
        for event_id in mission["event_refs"]
    ]
    findings = [
        stores.findings.read(finding_id)
        for finding_id in mission["finding_refs"]
    ]
    stumbles = [
        stores.stumbles.read(stumble_id)
        for stumble_id in mission["stumble_refs"]
    ]
    artifacts = [
        stores.artifacts.read(artifact_id)
        for artifact_id in mission["artifact_refs"]
    ]
    governance = [
        stores.governance_receipts.read(receipt_id)
        for receipt_id in mission["governance_receipt_refs"]
    ]
    review_signals = [
        stores.review_signals.read(signal_id)
        for signal_id in mission["review_signal_refs"]
    ]
    follow_ups = sorted(
        {
            ref
            for signal in review_signals
            for ref in signal.get("follow_up_refs", [])
        }
    )

    return {
        "mission": {
            "id": mission["id"],
            "mission_type": mission["mission_type"],
            "status": mission["status"],
            "summary": mission["summary"],
            "objective": mission["objective"],
            "freshness": mission["freshness"],
        },
        "agent_roster": agent_roster,
        "timeline": timeline,
        "findings": findings,
        "stumbles": stumbles,
        "artifacts": artifacts,
        "state_effects": {
            "commit_results": stores.commit_results.replay(),
            "journal_entries": stores.journal_entries.replay(),
            "memory_entries": stores.memory_entries.replay(),
            "review_signals": review_signals,
        },
        "governance": governance,
        "follow_ups": follow_ups,
    }


def _agent_summary(agent_run: JsonObject) -> JsonObject:
    return {
        "id": agent_run["id"],
        "agent_ref": agent_run["agent_ref"],
        "persona_ref": agent_run["persona_ref"],
        "role": agent_run["role"],
        "responsibility": agent_run["responsibility"],
        "status": agent_run["status"],
        "model_ref": agent_run["model_ref"],
        "token_usage": agent_run["token_usage"],
        "cost": agent_run["cost"],
    }
