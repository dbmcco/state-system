from __future__ import annotations

from pathlib import Path
import shutil

from state_system.company_capability import CompanyCapabilityRuntime
from state_system.contracts import JsonObject
from state_system.heartbeat import run_source_heartbeat
from state_system.runtime_bootstrap import bootstrap_runtime_state_system
from state_system.stores import StateStoreBundle


def migrate_state_root(
    *,
    project_root: Path,
    source_root: Path,
    target_root: Path,
    compat_link: Path | None,
    validate_company_ref: str | None,
    refresh: bool,
    heartbeat_company_ref: str | None,
    heartbeat_checked_at: str | None,
    heartbeat_stale_after: str | None,
) -> JsonObject:
    source_root = source_root.expanduser()
    target_root = target_root.expanduser()
    compat_link = compat_link.expanduser() if compat_link else None
    source_real = source_root.resolve()

    if not source_real.exists() or not source_real.is_dir():
        raise FileNotFoundError(f"source root does not exist: {source_root}")
    if source_real == target_root.resolve() and not target_root.is_symlink():
        raise ValueError("source root and target root must be different paths")

    _prepare_target(target_root)
    shutil.copytree(source_real, target_root, symlinks=True)

    validation = _validate_target(target_root, validate_company_ref)
    refresh_result: JsonObject | None = None
    if refresh:
        refresh_result = bootstrap_runtime_state_system(project_root, target_root)

    heartbeat_result: JsonObject | None = None
    if heartbeat_company_ref:
        if not heartbeat_checked_at or not heartbeat_stale_after:
            raise ValueError(
                "heartbeat checked_at and stale_after are required with heartbeat"
            )
        heartbeat_result = run_source_heartbeat(
            StateStoreBundle(target_root),
            company_ref=heartbeat_company_ref,
            checked_at=heartbeat_checked_at,
            stale_after=heartbeat_stale_after,
            output_dir=target_root / "source-freshness",
        )

    compat_result: JsonObject | None = None
    if compat_link:
        compat_result = _replace_compat_link(compat_link, target_root)

    return {
        "ok": True,
        "source_root": str(source_root),
        "source_real": str(source_real),
        "target_root": str(target_root),
        "compat_link": str(compat_link) if compat_link else None,
        "validation": validation,
        "refresh": refresh_result,
        "heartbeat": heartbeat_result,
        "compat": compat_result,
        "invariant": {
            "copy_not_destructive": True,
            "target_is_real_directory": True,
            "compat_link_points_to_target": bool(compat_link),
        },
    }


def _prepare_target(target_root: Path) -> None:
    if target_root.is_symlink():
        target_root.unlink()
        return
    if target_root.exists():
        raise FileExistsError(
            f"target root already exists and is not a symlink: {target_root}"
        )
    target_root.parent.mkdir(parents=True, exist_ok=True)


def _validate_target(
    target_root: Path,
    validate_company_ref: str | None,
) -> JsonObject:
    stores = StateStoreBundle(target_root)
    company_refs = [
        pack["company_ref"]
        for pack in CompanyCapabilityRuntime(stores).list_packs()
    ]
    if validate_company_ref and validate_company_ref not in company_refs:
        raise ValueError(
            f"{validate_company_ref} was not found in migrated company capabilities"
        )
    return {
        "company_refs": company_refs,
        "validated_company_ref": validate_company_ref,
    }


def _replace_compat_link(compat_link: Path, target_root: Path) -> JsonObject:
    backup_path: str | None = None
    if compat_link.is_symlink():
        compat_link.unlink()
    elif compat_link.exists():
        backup = _backup_path_for(compat_link)
        compat_link.rename(backup)
        backup_path = str(backup)
    else:
        compat_link.parent.mkdir(parents=True, exist_ok=True)

    compat_link.symlink_to(target_root, target_is_directory=True)
    return {
        "path": str(compat_link),
        "target": str(target_root),
        "backup_path": backup_path,
    }


def _backup_path_for(path: Path) -> Path:
    candidate = path.with_name(f"{path.name}.pre-migration-backup")
    if not candidate.exists():
        return candidate
    index = 1
    while True:
        numbered = path.with_name(f"{path.name}.pre-migration-backup-{index}")
        if not numbered.exists():
            return numbered
        index += 1
