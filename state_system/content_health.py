from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from state_system.contracts import JsonObject

STALE_STATUSES = {"stale", "expired"}
FAILED_STATUSES = {"failed", "error"}
UNKNOWN_STATUSES = {"unknown", "missing", "planned", "unproven", ""}


def expired_at(stale_after: object, as_of: object) -> bool:
    if not stale_after or not as_of:
        return False
    stale_after_dt = parse_timestamp(str(stale_after))
    as_of_dt = parse_timestamp(str(as_of))
    if stale_after_dt is None or as_of_dt is None:
        return False
    return stale_after_dt < as_of_dt


def parse_timestamp(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def aggregate_status(statuses: Iterable[object]) -> str:
    normalized = {str(status or "unknown") for status in statuses}
    if not normalized:
        return "unknown"
    if normalized & FAILED_STATUSES:
        return "failed"
    if normalized & STALE_STATUSES:
        return "stale"
    if normalized & UNKNOWN_STATUSES:
        return "unknown"
    if normalized == {"fresh"}:
        return "fresh"
    if "fresh" in normalized and len(normalized) == 1:
        return "fresh"
    return "unknown"


def staleness_banner(*, status: str, requires_refresh: bool) -> str:
    if status == "fresh" and not requires_refresh:
        return ""
    return (
        "HARD STALENESS BANNER: content health is "
        f"{status}; disclose freshness gaps and refresh before relying on this "
        "surface for external action."
    )


def build_content_health(
    *,
    statuses: Iterable[object],
    requires_refresh: bool = False,
    source_gap_refs: Iterable[object] = (),
    expired_freshness_refs: Iterable[object] = (),
    evidence_refs: Iterable[object] = (),
    generated_at: str = "",
) -> JsonObject:
    expired_refs = sorted({str(ref) for ref in _refs(expired_freshness_refs) if ref})
    gap_refs = sorted({str(ref) for ref in _refs(source_gap_refs) if ref})
    status_values = list(statuses)
    if expired_refs:
        status_values.append("stale")
    status = aggregate_status(status_values)
    refresh_required = requires_refresh or bool(expired_refs) or status != "fresh"
    return {
        "status": status,
        "requires_refresh_before_external_action": refresh_required,
        "source_gap_refs": gap_refs,
        "expired_freshness_refs": expired_refs,
        "evidence_refs": sorted({str(ref) for ref in _refs(evidence_refs) if ref}),
        "generated_at": generated_at,
        "staleness_banner": staleness_banner(
            status=status,
            requires_refresh=refresh_required,
        ),
    }


def _refs(value: object) -> list[object]:
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return []


def _inspect_expired_freshness_refs(
    *,
    package_id: str,
    sources: Iterable[object],
    as_of: str,
) -> list[str]:
    refs: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            continue
        if not expired_at(source.get("stale_after", ""), as_of):
            continue
        refs.add(
            ".".join(
                [
                    "expired_freshness",
                    package_id,
                    str(source.get("connector_ref", "")),
                    "stale_after",
                    str(source.get("stale_after", "")),
                ]
            )
        )
    return sorted(refs)


def build_process_health(*, status: str, generated_at: str = "", artifact_refs: Iterable[object] = ()) -> JsonObject:
    return {
        "status": status,
        "generated_at": generated_at,
        "artifact_refs": sorted({str(ref) for ref in artifact_refs if ref}),
    }


def build_package_health(package: JsonObject, *, as_of: str | None = None) -> JsonObject:
    freshness = package.get("freshness", {}) if isinstance(package.get("freshness"), dict) else {}
    source_context = package.get("source_context", {}) if isinstance(package.get("source_context"), dict) else {}
    sources = source_context.get("source_readiness", []) if isinstance(source_context.get("source_readiness", []), list) else []
    inspect_as_of = as_of or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    inspect_expired_refs = _inspect_expired_freshness_refs(
        package_id=str(package.get("id", "")),
        sources=sources,
        as_of=inspect_as_of,
    )
    statuses = [freshness.get("content_status", "unknown")]
    statuses.extend(source.get("content_status", source.get("freshness_status", "unknown")) for source in sources if isinstance(source, dict))
    if inspect_expired_refs:
        statuses.append("stale")
    source_gap_refs = set(_refs(freshness.get("source_gap_refs", [])))
    source_gap_refs.update(_refs(source_context.get("source_gap_refs", [])))
    for source in sources:
        if isinstance(source, dict):
            source_gap_refs.update(_refs(source.get("source_gap_refs", [])))
            source_gap_refs.update(_refs(source.get("gap_refs", [])))
    evidence_refs = set(_refs(freshness.get("evidence_refs", [])))
    for source in sources:
        if isinstance(source, dict):
            evidence_refs.update(_refs(source.get("evidence_refs", [])))
    expired_freshness_refs = sorted(
        {str(ref) for ref in _refs(freshness.get("expired_freshness_refs", [])) if ref}
        | set(inspect_expired_refs)
    )
    source_gap_refs.update(expired_freshness_refs)
    content = build_content_health(
        statuses=statuses,
        requires_refresh=bool(freshness.get("requires_refresh_before_external_action")),
        source_gap_refs=source_gap_refs,
        expired_freshness_refs=expired_freshness_refs,
        evidence_refs=evidence_refs,
        generated_at=str(freshness.get("generated_at") or package.get("created_at") or ""),
    )
    process_status = str(freshness.get("process_status") or package.get("status") or "unknown")
    return {
        "process_status": process_status,
        "content_status": content["status"],
        "requires_refresh_before_external_action": content[
            "requires_refresh_before_external_action"
        ],
        "source_gap_refs": content["source_gap_refs"],
        "expired_freshness_refs": content["expired_freshness_refs"],
        "staleness_banner": content["staleness_banner"],
        "process_health": build_process_health(
            status=process_status,
            generated_at=str(package.get("created_at") or ""),
            artifact_refs=[package.get("id", "")],
        ),
        "content_health": content,
    }
