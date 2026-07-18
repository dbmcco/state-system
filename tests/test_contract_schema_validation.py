from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from state_system.contracts import validate_state_system_schema

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 7, 18, 12, 0, tzinfo=UTC).isoformat().replace("+00:00", "Z")


def request_payload() -> dict[str, object]:
    return {
        "protocol_version": "state-system.v1",
        "request_id": "request-1",
        "correlation_id": "correlation-1",
        "operation": "inspect",
        "scope": "instance:samantha-home",
        "requested_at": NOW,
        "schema_ref": "schema:state-request.v1",
    }


def test_state_request_uses_draft_2020_12_and_accepts_valid_payload() -> None:
    assert validate_state_system_schema(request_payload(), "state-request.schema.json", ROOT) == []


def test_state_request_rejects_unknown_fields_and_bad_references() -> None:
    unknown = request_payload() | {"unexpected": True}
    assert validate_state_system_schema(unknown, "state-request.schema.json", ROOT)

    bad_ref = request_payload() | {"scope": "not-a-reference"}
    errors = validate_state_system_schema(bad_ref, "state-request.schema.json", ROOT)
    assert any("scope" in error for error in errors)


def test_freshness_schema_rejects_probe_only_claimed_fresh_and_bad_range() -> None:
    payload = {
        "protocol_version": "state-system.v1",
        "status": "fresh",
        "basis": "probe_only",
        "observed_at": NOW,
        "stale_after_seconds": 31_536_001,
        "coverage_status": "complete",
    }
    errors = validate_state_system_schema(payload, "freshness-summary.schema.json", ROOT)
    assert errors
    assert any("stale_after_seconds" in error or "fresh" in error for error in errors)


def test_unsupported_schema_names_fail_closed() -> None:
    try:
        validate_state_system_schema({}, "legacy-partial.schema.json", ROOT)
    except ValueError as exc:
        assert "unsupported State System schema" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("unsupported schemas must fail closed")
