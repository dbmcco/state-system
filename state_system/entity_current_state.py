# ABOUTME: Shared per-entity current-state cards — append-only store + mechanical
# ABOUTME: resolution of effective_at/stale_after/supersedes/status into a read model.
from __future__ import annotations

import json
import re
from collections import Counter

from state_system.contracts import JsonObject
from state_system.stores import StateStoreBundle


ACTIVE = "active"
SUPERSEDED = "superseded"
RETRACTED = "retracted"


def build_entity_current_state_read_model(
    stores: StateStoreBundle,
    *,
    as_of: str,
) -> JsonObject:
    """Resolve raw entity current-state records into the ACTIVE read model.

    This resolution is MECHANICAL POLICY only — it never interprets the meaning
    of card content:

      * ``status == "retracted"``                  -> excluded from active view
      * id referenced by another record's ``supersedes`` -> superseded, excluded
      * ``status == "superseded"``                 -> excluded
      * everything else is an ACTIVE head and is copied through verbatim
      * ``as_of >= stale_after``                   -> ``is_stale`` (decay flag)
      * ``as_of <  effective_at``                  -> ``not_yet_effective``

    Card CONTENT (north_star, current_priority, owner, waiting_on,
    braydon_next_action, confidence, ...) is owned by the model/human and is
    passed through unchanged. ``as_of`` is an explicit caller input — the
    exporter never reads the wall clock, so resolution is deterministic and
    testable. Superseded/retracted records remain in the raw store; they are
    only excluded from the active view.
    """
    records = EntityCurrentStateRuntime(stores).list_records()
    superseded_ids = {
        record["supersedes"] for record in records if record.get("supersedes")
    }

    active_cards: list[JsonObject] = []
    superseded_refs: list[str] = []
    retracted_refs: list[str] = []
    for record in records:
        record_id = record["id"]
        status = record.get("status", ACTIVE)
        if status == RETRACTED:
            retracted_refs.append(record_id)
            continue
        if status == SUPERSEDED or record_id in superseded_ids:
            superseded_refs.append(record_id)
            continue
        active_cards.append(_resolve_card(record, as_of=as_of))

    active_cards.sort(key=lambda card: (card["entity_id"], card["effective_at"]))
    return {
        "id": "entity_current_state_read_model",
        "artifact_type": "json_substrate",
        "generated_at": as_of,
        "as_of": as_of,
        "entity_ids": sorted({card["entity_id"] for card in active_cards}),
        "active_cards": active_cards,
        "superseded_record_refs": sorted(superseded_refs),
        "retracted_record_refs": sorted(retracted_refs),
        "conflicting_entity_ids": _conflicting_entity_ids(active_cards),
        "invariant": {
            "resolution_is_mechanical_policy": True,
            "card_content_is_model_authored": True,
            "as_of_is_explicit_input": True,
            "precedence_by_supersession_and_decay": True,
            "ranks_card_content_semantically": False,
            "authorizes_execution": False,
        },
    }


class EntityCurrentStateRuntime:
    """Append-only writer/reader for entity current-state cards.

    A supersede is a brand new record whose ``supersedes`` points at the prior
    record id; prior records are never mutated or deleted. Writing over an
    existing id raises, which keeps the store immutable.
    """

    def __init__(self, stores: StateStoreBundle):
        self.store = stores.entity_current_state

    def record(self, card: JsonObject) -> JsonObject:
        record = _normalize_record(card)
        # Delegate to the append-only file store, which raises if the id exists.
        self.store.create(record)
        return record

    def read(self, record_id: str) -> JsonObject:
        return self.store.read(record_id)

    def list_records(self) -> list[JsonObject]:
        return sorted(
            self.store.replay(),
            key=lambda record: (
                record["entity_id"],
                record.get("effective_at", ""),
                record["id"],
            ),
        )


def _resolve_card(record: JsonObject, *, as_of: str) -> JsonObject:
    card = dict(record)
    stale_after = record.get("stale_after") or ""
    effective_at = record.get("effective_at") or ""
    is_stale = bool(stale_after) and as_of >= stale_after
    card["is_stale"] = is_stale
    card["not_yet_effective"] = bool(effective_at) and as_of < effective_at
    card["decay_warning"] = (
        f"stale_after {stale_after} has passed as of {as_of}; "
        "precedence reduced — refresh before relying on this card"
        if is_stale
        else ""
    )
    return card


def _conflicting_entity_ids(active_cards: list[JsonObject]) -> list[str]:
    counts = Counter(card["entity_id"] for card in active_cards)
    return sorted(entity_id for entity_id, count in counts.items() if count > 1)


def _normalize_record(card: JsonObject) -> JsonObject:
    record = dict(card)
    record.setdefault("status", ACTIVE)
    record.setdefault("supersedes", None)
    record.setdefault("waiting_on", "")
    record.setdefault("braydon_next_action", "")
    record.setdefault("source_refs", [])
    record.setdefault("id", _record_id(record))
    return record


def _record_id(record: JsonObject) -> str:
    version = record.get("effective_at") or record.get("generated_at") or ""
    return f"entity_current_state.{_slug(record['entity_id'])}.{_slug(version)}"


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")
