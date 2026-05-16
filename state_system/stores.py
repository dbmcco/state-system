from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


JsonObject = dict[str, Any]

DEFAULT_COLLECTIONS = {
    "state_objects": "objects",
    "source_events": "source-events",
    "review_packets": "review-packets",
    "journals": "journals",
    "memory": "memory",
    "rollups": "rollups",
    "review_signals": "review-signals",
    "commits": "commits",
    "recent_changes": "recent-changes",
    "context_packages": "context-packages",
    "agent_activations": "agent-activations",
    "agent_responses": "agent-responses",
    "instance_capabilities": "instance-capabilities",
    "instance_preflight_results": "instance-preflight-results",
    "instance_source_freshness": "instance-source-freshness",
    "company_capabilities": "company-capabilities",
    "company_preflight_results": "company-preflight-results",
    "source_freshness": "source-freshness",
}


class StoreError(Exception):
    """Base class for file store errors."""


class RecordExistsError(StoreError):
    """Raised when a record id already exists in a collection."""


class RecordNotFoundError(StoreError):
    """Raised when a record id is missing from a collection."""


@dataclass(frozen=True)
class JsonFileStore:
    root: Path
    collection: str

    @property
    def directory(self) -> Path:
        return self.root / "state" / self.collection

    def create(self, record: JsonObject) -> Path:
        record_id = _record_id(record)
        path = self.path_for(record_id)
        if path.exists():
            raise RecordExistsError(f"{record_id} already exists in {self.collection}")

        self.directory.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2, sort_keys=True)
            handle.write("\n")
        return path

    def read(self, record_id: str) -> JsonObject:
        path = self.path_for(record_id)
        if not path.exists():
            raise RecordNotFoundError(f"{record_id} does not exist in {self.collection}")

        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        if not isinstance(value, dict):
            raise ValueError(f"{path} must contain a JSON object")
        return value

    def list_ids(self) -> list[str]:
        if not self.directory.exists():
            return []
        return sorted(path.stem for path in self.directory.glob("*.json"))

    def replay(self) -> list[JsonObject]:
        records = [self.read(record_id) for record_id in self.list_ids()]
        return sorted(records, key=_replay_key)

    def path_for(self, record_id: str) -> Path:
        if not record_id:
            raise ValueError("record id must not be empty")
        if "/" in record_id or "\\" in record_id:
            raise ValueError("record id must not contain path separators")
        return self.directory / f"{record_id}.json"


@dataclass(frozen=True)
class StateStoreBundle:
    root: Path

    def __post_init__(self) -> None:
        for attribute, collection in DEFAULT_COLLECTIONS.items():
            object.__setattr__(self, attribute, JsonFileStore(self.root, collection))


def _record_id(record: JsonObject) -> str:
    record_id = record.get("id")
    if not isinstance(record_id, str) or not record_id:
        raise ValueError("record must include a non-empty string id")
    return record_id


def _replay_key(record: JsonObject) -> tuple[str, str]:
    timestamp = (
        record.get("created_at")
        or record.get("observed_at")
        or record.get("occurred_at")
        or record.get("as_of")
        or ""
    )
    record_id = record.get("id") or ""
    return str(timestamp), str(record_id)
