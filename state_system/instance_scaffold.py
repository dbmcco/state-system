from __future__ import annotations

import json
from pathlib import Path

from state_system.contracts import JsonObject, validate_schema


class InstanceScaffoldError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("instance scaffold failed")
        self.errors = tuple(errors)


def scaffold_state_instance(
    *,
    project_root: Path,
    runtime_root: Path,
    instance_ref: str,
    kind: str,
    display_name: str,
    primary_entity_ref: str,
    entity_kind: str,
    created_at: str,
    governance_refs: list[str],
    sensitivity_default: str = "confidential",
    federates_with: list[str] | None = None,
    connector_types: list[str] | None = None,
) -> JsonObject:
    instance = {
        "id": instance_ref,
        "instance_ref": instance_ref,
        "kind": kind,
        "display_name": display_name,
        "runtime_root": str(runtime_root),
        "primary_entity_ref": primary_entity_ref,
        "entity_kind": entity_kind,
        "governance_refs": governance_refs,
        "sensitivity_default": sensitivity_default,
        "federates_with": list(federates_with or []),
        "created_at": created_at,
        "updated_at": created_at,
    }
    schema = _load_json(project_root / "schemas/state-instance.schema.json")
    errors = validate_schema(instance, schema)
    if errors:
        raise InstanceScaffoldError(errors)

    slug = instance_ref.removeprefix("state_instance.")
    paths = _ensure_runtime_dirs(runtime_root)
    instance_path = runtime_root / "state" / "instances" / f"state-instance-{slug}.json"
    _write_json(instance_path, instance)

    module_registry_path = None
    if connector_types:
        module_registry = _module_registry_subset(
            project_root=project_root,
            slug=slug,
            connector_types=connector_types,
            generated_at=created_at,
        )
        module_registry_path = (
            runtime_root
            / "state"
            / "source-modules"
            / f"source-module-registry-{slug}.json"
        )
        _write_json(module_registry_path, module_registry)

    runbook_path = runtime_root / "README.md"
    if not runbook_path.exists():
        runbook_path.write_text(
            _runbook_text(instance_ref=instance_ref, display_name=display_name),
            encoding="utf-8",
        )

    return {
        "ok": True,
        "instance_ref": instance_ref,
        "runtime_root": str(runtime_root),
        "instance_path": str(instance_path),
        "module_registry_path": str(module_registry_path) if module_registry_path else "",
        "created_dirs": [str(path) for path in paths],
    }


def _ensure_runtime_dirs(runtime_root: Path) -> list[Path]:
    dirs = [
        runtime_root / "state" / "instances",
        runtime_root / "state" / "source-modules",
        runtime_root / "state" / "instance-capabilities",
        runtime_root / "state" / "instance-agent-packages",
        runtime_root / "instance-preflight",
        runtime_root / "instance-source-freshness",
        runtime_root / "instance-understanding",
        runtime_root / "instance-agent-package",
    ]
    for directory in dirs:
        directory.mkdir(parents=True, exist_ok=True)
    return dirs


def _module_registry_subset(
    *,
    project_root: Path,
    slug: str,
    connector_types: list[str],
    generated_at: str,
) -> JsonObject:
    core = _load_json(
        project_root / "examples/source-modules/source-module-core-connectors.json"
    )
    wanted = set(connector_types)
    modules = [
        module
        for module in core["modules"]
        if module["connector_type"] in wanted
    ]
    found = {module["connector_type"] for module in modules}
    missing = sorted(wanted - found)
    if missing:
        raise InstanceScaffoldError(
            [f"connector types without source modules: {', '.join(missing)}"]
        )
    return {
        "id": f"source_module_registry.{slug}",
        "generated_at": generated_at,
        "description": f"Instance-local source module registry subset for {slug}.",
        "modules": modules,
        "invariant": core["invariant"],
    }


def _runbook_text(*, instance_ref: str, display_name: str) -> str:
    return (
        f"# {display_name}\n\n"
        f"State System runtime root for `{instance_ref}`.\n\n"
        "This scaffold declares runtime structure only. Source access, freshness, "
        "indexes, and agent packages must be recorded explicitly before an agent "
        "treats a source as usable evidence.\n"
    )


def _write_json(path: Path, payload: JsonObject) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_json(path: Path) -> JsonObject:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value
