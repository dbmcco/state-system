#!/usr/bin/env python3
# ABOUTME: Seeds the shared entity current-state store with model-authored cards
# ABOUTME: drawn from the WKM north-star load map plus Braydon's direct corrections.
"""Seed the SHARED entity current-state store.

The card CONTENT below (north_star, current_priority, owner, waiting_on,
braydon_next_action, confidence, freshness horizons) is *authored judgment* —
synthesised from:

  - ~/projects/wkm/status/north-star-load-map-2026-06-16.md  (Elena's load map)
  - ~/projects/wkm/status/sam-north-star-comparison-2026-06-16.md  (decay evidence)
  - Braydon's direct corrections (Synthyra two-horizon; LFW ownership)

It is NOT a hardcoded heuristic and the store/exporter never interpret it. Code
owns only the append-only store and the mechanical effective_at / stale_after /
supersedes / status resolution. Re-running is idempotent: records already
present (same entity_id + effective_at) are left untouched.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from state_system.entity_current_state import (  # noqa: E402
    EntityCurrentStateRuntime,
    build_entity_current_state_read_model,
)
from state_system.stores import (  # noqa: E402
    RecordExistsError,
    StateStoreBundle,
)

DEFAULT_STATE_ROOT = Path("/Users/braydon/projects/personal/b-state")
DEFAULT_AS_OF = "2026-06-16T18:00:00Z"
GENERATED_AT = "2026-06-16T18:00:00Z"

LOAD_MAP = "wkm-status:status/north-star-load-map-2026-06-16.md"
COMPARISON = "wkm-status:status/sam-north-star-comparison-2026-06-16.md"

SEED_CARDS = [
    {
        "entity_id": "braydon",
        "entity_name": "Braydon (personal)",
        "north_star": (
            "Build durable, high-impact ventures without sacrificing autonomy, "
            "health, relationships, or creative identity. Today is a load "
            "problem, not an ambition problem."
        ),
        "current_priority": (
            "Protect the operator: run/body reset, Carvana/Subaru/Jeep, "
            "family and Father's Day, travel holds, Garmin/races, home work. "
            "Preserve June 26 SFO for Dorico/Cubase, the SQ3 III cadenza, and "
            "cello concerto composition."
        ),
        "owner": "Braydon",
        "waiting_on": "",
        "braydon_next_action": (
            "Hold protected personal and creative space; keep cash, body, and "
            "company-changing moves ahead of system noise."
        ),
        "effective_at": "2026-06-16T00:00:00Z",
        "stale_after": "2026-06-23T00:00:00Z",
        "supersedes": None,
        "source_refs": [LOAD_MAP, "folio:north-star-os", "workboard:personal"],
        "confidence": "high",
        "status": "active",
        "generated_at": GENERATED_AT,
        "generated_by": "sam",
    },
    {
        "entity_id": "lfw",
        "entity_name": "LFW",
        "north_star": "Repeatable partner-led delivery of one painful workflow.",
        "current_priority": (
            "Partner plans, ABD/API, sandbox validation, contracting/SOW, and "
            "sales needs. Blind spot: ForgeWorks can become an escape from "
            "client execution."
        ),
        # Braydon's correction: Kion is Andrew's, not Braydon's.
        "owner": "Braydon (portfolio); Kion is owned by Andrew, not Braydon.",
        # Braydon's correction: Main Ocean is waiting on Greg, not a Braydon action.
        "waiting_on": "Greg, on Main Ocean (moving to contracting/SOW).",
        "braydon_next_action": (
            "Advance LFW contracting and partner plans. Do NOT promote Main "
            "Ocean (waiting on Greg) or Kion (Andrew owns) to a Braydon action "
            "without a specific next step."
        ),
        "effective_at": "2026-06-16T00:00:00Z",
        "stale_after": "2026-06-23T00:00:00Z",
        "supersedes": None,
        "source_refs": [LOAD_MAP, "linear:lfw"],
        "confidence": "high",
        "status": "active",
        "generated_at": GENERATED_AT,
        "generated_by": "braydon",
    },
    {
        # Two-horizon card per Braydon's direct correction: the durable
        # north_star and the near-term current_priority are BOTH true at
        # different horizons. The June 15 shift is a near-term priority change,
        # NOT a replacement of the durable destination, so this card carries
        # both and is explicitly NOT superseded.
        "entity_id": "synthyra",
        "entity_name": "Synthyra",
        "north_star": (
            "Metabolic engineering destination — the durable long-term "
            "direction. This is NOT stale and is NOT superseded by the June 15 "
            "near-term shift; treating the metabolic narrative as stale is the "
            "error to avoid."
        ),
        "current_priority": (
            "Get to market with known tech — near-term focus, effective ~June "
            "15: decision-support for what to validate next, with proteome-scale "
            "evidence. ERIS deliverables plus buyer discovery to turn N=1 into "
            "N>=3; delegate comparables, logging, and LinkedIn."
        ),
        "owner": "Braydon",
        "waiting_on": "",
        "braydon_next_action": (
            "Push Synthyra ERIS deliverables and buyer discovery; handle the VC "
            "replies."
        ),
        "effective_at": "2026-06-15T00:00:00Z",
        "stale_after": "2026-06-23T00:00:00Z",
        "supersedes": None,
        "source_refs": [LOAD_MAP, "folio:synthyra/STATUS.md", "tracker:synthyra"],
        "confidence": "high",
        "status": "active",
        "generated_at": GENERATED_AT,
        "generated_by": "braydon",
    },
    {
        "entity_id": "navicyte",
        "entity_name": "Navicyte",
        "north_star": (
            "Credible IL-12 IND/licensing path with manufacturing "
            "differentiation and named pharma/investor logic."
        ),
        "current_priority": (
            "Pro forma charts are done, but UD's likely-missing $50k makes "
            "equity, compensation, and fundraising acceleration strategic. Keep "
            "the funding/equity risk high until Thursday forces clarity. Blind "
            "spot: state docs lag the live finance risk."
        ),
        "owner": "Braydon",
        "waiting_on": (
            "UD on the likely-missing $50k (clarity expected Thursday "
            "2026-06-18); Mike on finance."
        ),
        "braydon_next_action": (
            "Keep Navicyte equity/funding risk high until UD is clear; force "
            "clarity Thursday."
        ),
        "effective_at": "2026-06-16T00:00:00Z",
        "stale_after": "2026-06-19T00:00:00Z",
        "supersedes": None,
        "source_refs": [LOAD_MAP, "tracker:navicyte"],
        "confidence": "medium",
        "status": "active",
        "generated_at": GENERATED_AT,
        "generated_by": "sam",
    },
    {
        "entity_id": "paia-sam",
        "entity_name": "PAIA / Sam",
        "north_star": (
            "Personal scale infrastructure: memory-backed prioritization, "
            "source coverage, delegation, agenda prep, Supernote continuity, "
            "and follow-through."
        ),
        "current_priority": (
            "Accumulate decisions, ownership, source freshness, and what "
            "changed. Spend PAIA time only where it reduces tomorrow's load. "
            "Blind spot: agent launch is stronger than harvest; tmux needs a "
            "daily keep/harvest/pause/kill review."
        ),
        "owner": "Braydon",
        "waiting_on": "",
        "braydon_next_action": (
            "Run a daily tmux keep/harvest/pause/kill review; invest in PAIA "
            "only where it reduces load."
        ),
        "effective_at": "2026-06-16T00:00:00Z",
        "stale_after": "2026-06-23T00:00:00Z",
        "supersedes": None,
        "source_refs": [LOAD_MAP, COMPARISON, "workboard:paia"],
        "confidence": "medium",
        "status": "active",
        "generated_at": GENERATED_AT,
        "generated_by": "sam",
    },
    {
        "entity_id": "cyrcle-womens-health",
        "entity_name": "Cyrcle / women's health",
        "north_star": "A testable, deployable women's health product.",
        "current_priority": (
            "Get Cyrcle / women's health testable and deployable for Friday "
            "(2026-06-20). This is the lead item in the next 24-48 hours."
        ),
        "owner": "Braydon",
        "waiting_on": "",
        "braydon_next_action": (
            "Get Cyrcle / women's health testable and deployable by Friday."
        ),
        "effective_at": "2026-06-16T00:00:00Z",
        "stale_after": "2026-06-20T23:59:59Z",
        "supersedes": None,
        "source_refs": [LOAD_MAP],
        "confidence": "high",
        "status": "active",
        "generated_at": GENERATED_AT,
        "generated_by": "sam",
    },
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-root", default=str(DEFAULT_STATE_ROOT))
    parser.add_argument("--as-of", default=DEFAULT_AS_OF)
    args = parser.parse_args(argv)

    state_root = Path(args.state_root)
    stores = StateStoreBundle(state_root)
    runtime = EntityCurrentStateRuntime(stores)

    written: list[str] = []
    skipped: list[str] = []
    for card in SEED_CARDS:
        try:
            record = runtime.record(dict(card))
            written.append(record["id"])
        except RecordExistsError:
            skipped.append(f"{card['entity_id']} @ {card['effective_at']}")

    read_model = build_entity_current_state_read_model(stores, as_of=args.as_of)
    output_dir = state_root / "entity-current-state"
    output_dir.mkdir(parents=True, exist_ok=True)
    read_model_path = output_dir / "entity-current-state-read-model.json"
    import json

    read_model_path.write_text(
        json.dumps(read_model, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(f"state_root: {state_root}")
    print(f"raw records dir: {state_root / 'state' / 'entity-current-state'}")
    print(f"written: {written}")
    print(f"skipped (already present): {skipped}")
    print(f"read model: {read_model_path}")
    print(f"active entities: {read_model['entity_ids']}")
    print(f"conflicts: {read_model['conflicting_entity_ids']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
