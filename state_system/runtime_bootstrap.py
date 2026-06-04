from __future__ import annotations

import json
import os
from pathlib import Path

from state_system.company_capability import (
    CompanyCapabilityRuntime,
    build_company_capability_read_model_from_runtime,
)
from state_system.company_preflight import build_company_preflight_read_model
from state_system.contracts import JsonObject, load_json, validate_schema
from state_system.source_freshness import build_source_freshness_read_model
from state_system.stores import StateStoreBundle


DEFAULT_RUNTIME_STATE_ROOT = Path(os.environ.get("STATE_SYSTEM_ROOT", ""))


def bootstrap_runtime_state_system(project_root: Path, state_root: Path) -> JsonObject:
    stores = StateStoreBundle(state_root)
    packs = _load_company_capability_packs(project_root)
    _validate_company_capability_packs(project_root, packs)
    seed_result = CompanyCapabilityRuntime(stores).seed(packs)

    capability_model = build_company_capability_read_model_from_runtime(stores)
    capability_path = (
        state_root / "company-capability" / "company-capability-read-model.json"
    )
    _write_json(capability_path, capability_model)

    preflight_model = build_company_preflight_read_model(stores)
    preflight_path = (
        state_root
        / "company-preflight"
        / "company-preflight-results-read-model.json"
    )
    _write_json(preflight_path, preflight_model)

    freshness_model = build_source_freshness_read_model(stores)
    freshness_path = (
        state_root / "source-freshness" / "source-freshness-read-model.json"
    )
    _write_json(freshness_path, freshness_model)

    return {
        "ok": True,
        "state_root": str(state_root),
        "company_capability_path": str(capability_path),
        "company_preflight_path": str(preflight_path),
        "source_freshness_path": str(freshness_path),
        "company_capability_companies": len(capability_model["companies"]),
        "company_preflight_results": len(preflight_model["results"]),
        "source_freshness_results": len(freshness_model["results"]),
        "seeded": seed_result,
    }


def _load_company_capability_packs(project_root: Path) -> list[JsonObject]:
    directory = project_root / "examples" / "company-capability"
    return [
        load_json(directory / "company-sampleco.json"),
        load_json(directory / "company-researchco.json"),
        load_json(directory / "company-portfolio-co.json"),
    ]


def _validate_company_capability_packs(
    project_root: Path,
    packs: list[JsonObject],
) -> None:
    schema = load_json(
        project_root / "schemas" / "company-capability-pack.schema.json"
    )
    failures = [
        {"id": pack.get("id"), "errors": list(validate_schema(pack, schema))}
        for pack in packs
    ]
    failures = [failure for failure in failures if failure["errors"]]
    if failures:
        raise ValueError(f"company capability seed packs failed validation: {failures}")


def _write_json(path: Path, payload: JsonObject) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
