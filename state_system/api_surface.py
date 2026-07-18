"""Model-operable State System dispatcher and response envelopes.

The dispatcher owns protocol shape and mechanical validation. It does not infer
meaning, silently repair requests, authorize external effects, or change source
freshness.
"""

from __future__ import annotations

from datetime import UTC, datetime
import re
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from state_system.audit_ledger import StateAuditLedger
from state_system.contracts import validate_all_examples
from state_system.gap_acknowledgement import GapAcknowledgementLedger


PROTOCOL_VERSION = "state-system.v1"
OPERATIONS = (
    "handshake",
    "inspect",
    "validate",
    "refresh",
    "search",
    "record",
    "repair",
    "acknowledge_gap",
)
EFFECT_CLASSES = ("read_only", "internal_write", "external_effect")
_REF_RE = re.compile(r"^[a-z][a-z0-9+.-]*:[^\s]+$")


class StateDispatcher:
    """Dispatch explicit protocol operations against a State System root."""

    def __init__(self, project_root: Path | str = ".", state_root: Path | str = "."):
        self.project_root = Path(project_root)
        self.state_root = Path(state_root)

    def dispatch(
        self,
        operation: str,
        *,
        request_id: str | None = None,
        correlation_id: str | None = None,
        scope: str = "state:local",
        arguments: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        request_id = request_id or _request_id()
        correlation_id = correlation_id or request_id
        arguments = arguments or {}
        if not isinstance(arguments, Mapping):
            return _error_response(
                operation,
                request_id,
                "invalid_request",
                "arguments must be a JSON object.",
                expected_shape="arguments: object",
                received_value_redacted=type(arguments).__name__,
                safe_examples=['{"arguments": {}}'],
            )
        if operation not in OPERATIONS:
            return _error_response(
                "handshake",
                request_id,
                "unknown_operation",
                f"Unsupported operation {operation!r}; choose a declared operation.",
                expected_shape="operation: one of handshake, inspect, validate, refresh, search, record, repair, acknowledge_gap",
                received_value_redacted=str(operation)[:256],
                safe_examples=["{\"operation\": \"inspect\", \"scope\": \"state:local\"}"],
                next_steps=["Call handshake to discover operations, then retry with a declared operation."],
            )
        if not _valid_ref(scope):
            return _error_response(
                operation,
                request_id,
                "invalid_reference",
                "scope must be a non-empty State System reference.",
                field_path="scope",
                expected_shape="scope: string matching <scheme>:<value>",
                received_value_redacted=str(scope)[:256],
                safe_examples=["state:local", "state_instance:sampleco"],
            )

        try:
            if operation == "handshake":
                data = build_handshake(scope=scope)
                return _ok_response(operation, request_id, data=data)
            if operation == "inspect":
                gap_refs = arguments.get("gap_refs", [])
                if not isinstance(gap_refs, list) or any(not _valid_ref(ref) for ref in gap_refs):
                    return _error_response(
                        operation,
                        request_id,
                        "invalid_reference",
                        "gap_refs must be a list of State System references.",
                        field_path="arguments.gap_refs",
                        expected_shape="gap_refs: list[string matching <scheme>:<value>]",
                        safe_examples=['{"arguments":{"gap_refs":["gap:source.stale"]}}'],
                    )
                return _ok_response(
                    operation,
                    request_id,
                    data=self._inspect(scope=scope, arguments=arguments),
                )
            if operation == "validate":
                return _ok_response(
                    operation,
                    request_id,
                    data=self._validate(),
                )
            if operation == "acknowledge_gap":
                return self._acknowledge_gap(
                    request_id=request_id,
                    correlation_id=correlation_id,
                    scope=scope,
                    arguments=arguments,
                )
            if operation == "repair":
                return _partial_response(
                    operation,
                    request_id,
                    data={
                        "repairable": False,
                        "scope": scope,
                        "message": "Repair requires an explicit source-owner action; State System does not invent connector behavior.",
                    },
                    next_steps=[
                        "Inspect the gap and select a declared source-owner repair action.",
                        "Retry with an explicit action_ref and arguments after repair is available.",
                    ],
                )
            return _partial_response(
                operation,
                request_id,
                data={
                    "supported": True,
                    "scope": scope,
                    "message": f"{operation} is declared but requires a source-specific adapter.",
                },
                next_steps=["Call handshake for the declared contract and adapter requirements."],
            )
        except Exception as error:  # boundary safety: never expose a traceback to callers
            return _error_response(
                operation,
                request_id,
                "internal_error",
                "The dispatcher could not complete the request.",
                retryable=True,
                next_steps=["Retry with the same request if safe; otherwise call handshake and inspect the contract."],
                received_value_redacted=type(error).__name__,
            )

    def _inspect(self, *, scope: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        ledger_path = self.state_root / "audit.jsonl"
        ledger = StateAuditLedger(ledger_path)
        entries = ledger.entries()
        acknowledgements = [
            entry["payload"]
            for entry in entries
            if entry.get("event_type") == "gap_acknowledgement"
        ]
        return {
            "scope": scope,
            "package": arguments.get("package_ref"),
            "source_gap_refs": list(arguments.get("gap_refs", []))
            if isinstance(arguments.get("gap_refs", []), list)
            else [],
            "expired_freshness_refs": [],
            "acknowledged_gap_refs": [item.get("gap_ref") for item in acknowledgements],
            "repair_actions": ["repair", "acknowledge_gap"],
            "ledger": {
                "path": str(ledger_path),
                "entry_count": len(entries),
                "retention_days": 400,
            },
        }

    def _validate(self) -> dict[str, Any]:
        results = validate_all_examples(self.project_root)
        failures = [result for result in results if not result.ok]
        return {
            "ok": not failures,
            "validated_examples": len(results),
            "failures": [
                {
                    "path": str(result.path),
                    "schema": result.schema,
                    "errors": list(result.errors),
                }
                for result in failures
            ],
        }

    def _acknowledge_gap(
        self,
        *,
        request_id: str,
        correlation_id: str,
        scope: str,
        arguments: Mapping[str, Any],
    ) -> dict[str, Any]:
        required = ("gap_ref", "idempotency_key", "acknowledged_by_ref", "reason")
        missing = [name for name in required if not isinstance(arguments.get(name), str) or not arguments[name].strip()]
        if missing:
            return _error_response(
                "acknowledge_gap",
                request_id,
                "invalid_request",
                "acknowledge_gap requires all acknowledgement fields.",
                expected_shape="gap_ref, idempotency_key, acknowledged_by_ref, and reason: non-empty strings",
                field_path=missing[0],
                safe_examples=[
                    '{"gap_ref":"gap:source.stale","idempotency_key":"idem-1","acknowledged_by_ref":"actor:agent","reason":"disclosed"}'
                ],
                next_steps=["Provide the missing fields and retry; acknowledgement changes neither freshness nor authorization."],
            )
        if any("\n" in arguments[name] or "\r" in arguments[name] for name in required):
            return _error_response(
                "acknowledge_gap",
                request_id,
                "invalid_request",
                "acknowledgement fields must be single-line values.",
                field_path="reason",
                expected_shape="acknowledgement fields: bounded single-line strings",
                safe_examples=['{"reason":"reviewed and disclosed"}'],
            )
        if not _valid_ref(arguments["acknowledged_by_ref"]):
            return _error_response(
                "acknowledge_gap",
                request_id,
                "invalid_reference",
                "acknowledged_by_ref must be a State System reference.",
                field_path="acknowledged_by_ref",
                expected_shape="acknowledged_by_ref: string matching <scheme>:<value>",
                received_value_redacted=arguments["acknowledged_by_ref"][:256],
                safe_examples=["actor:agent"],
            )
        if not _valid_ref(arguments["gap_ref"]):
            return _error_response(
                "acknowledge_gap",
                request_id,
                "invalid_reference",
                "gap_ref must be a State System reference.",
                field_path="gap_ref",
                expected_shape="gap_ref: string matching <scheme>:<value>",
                received_value_redacted=arguments["gap_ref"][:256],
                safe_examples=["gap:source.stale"],
            )
        ledger = StateAuditLedger(self.state_root / "audit.jsonl")
        record = GapAcknowledgementLedger(ledger).acknowledge_gap(
            arguments["gap_ref"],
            request_id=request_id,
            idempotency_key=arguments["idempotency_key"],
            acknowledged_by_ref=arguments["acknowledged_by_ref"],
            reason=arguments["reason"],
            scope=scope,
            correlation_id=correlation_id,
        )
        payload = record["payload"]
        receipt = {
            "protocol_version": PROTOCOL_VERSION,
            "entry_ref": record["entry_ref"],
            "request_id": record["request_id"],
            "event_type": record["event_type"],
            "outcome": "committed",
            "occurred_at": record["occurred_at"],
            "actor_ref": record["actor_ref"],
            "idempotency_key": record["idempotency_key"],
            "retention_class": record["retention_class"],
            "retain_until": record["retain_until"],
            "redaction_policy": record["redaction_policy"],
        }
        return _ok_response(
            "acknowledge_gap",
            request_id,
            data={"acknowledgement": payload, "authorizes": False},
            receipt=receipt,
            receipt_ref=record["entry_ref"],
            next_steps=["Keep the gap visible; repair the source before relying on it."],
        )


def build_handshake(*, scope: str = "state:local") -> dict[str, Any]:
    descriptions = {
        "handshake": ("Discover the versioned State System protocol and declared operations.", "read_only"),
        "inspect": ("Read package, freshness, gap, repair, and ledger status without mutation.", "read_only"),
        "validate": ("Validate repository examples and published contracts.", "read_only"),
        "refresh": ("Request a declared internal refresh; source adapters own connector behavior.", "internal_write"),
        "search": ("Search declared State System read models; do not infer connector behavior.", "read_only"),
        "record": ("Record an explicit evidence or state proposal through a declared contract.", "internal_write"),
        "repair": ("Request an explicit source-owner repair action; no implicit fallback is used.", "internal_write"),
        "acknowledge_gap": ("Persist an auditable gap acknowledgement without changing freshness or authorization.", "internal_write"),
    }
    capabilities = []
    for operation in OPERATIONS:
        description, effect_class = descriptions[operation]
        capabilities.append(
            {
                "protocol_version": PROTOCOL_VERSION,
                "capability_ref": f"capability:state-system.{operation}",
                "operation": operation,
                "description": description,
                "schema_ref": "schema:state-request.v1",
                "effect_class": effect_class,
                "requires_idempotency": operation in {"refresh", "record", "repair", "acknowledge_gap"},
                "requires_governance": False,
                "examples": [
                    {"operation": operation, "scope": scope},
                ],
            }
        )
    return {
        "protocol_version": PROTOCOL_VERSION,
        "schema_ref": "schema:state-handshake.v1",
        "instance_ref": scope,
        "service_version": "0.1.0",
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "supported_operations": list(OPERATIONS),
        "capabilities": capabilities,
    }


def dispatch(
    operation: str,
    *,
    project_root: Path | str = ".",
    state_root: Path | str = ".",
    request_id: str | None = None,
    correlation_id: str | None = None,
    scope: str = "state:local",
    arguments: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return StateDispatcher(project_root, state_root).dispatch(
        operation,
        request_id=request_id,
        correlation_id=correlation_id,
        scope=scope,
        arguments=arguments,
    )


def _ok_response(
    operation: str,
    request_id: str,
    *,
    data: dict[str, Any],
    receipt: dict[str, Any] | None = None,
    receipt_ref: str | None = None,
    next_steps: list[str] | None = None,
) -> dict[str, Any]:
    return _response(
        operation,
        request_id,
        status="ok",
        data=data,
        receipt=receipt,
        receipt_ref=receipt_ref,
        next_steps=next_steps,
    )


def _partial_response(
    operation: str,
    request_id: str,
    *,
    data: dict[str, Any],
    next_steps: list[str],
) -> dict[str, Any]:
    return _response(operation, request_id, status="partial", data=data, next_steps=next_steps)


def _error_response(
    operation: str,
    request_id: str,
    code: str,
    message: str,
    *,
    field_path: str | None = None,
    expected_shape: str | None = None,
    received_value_redacted: str | None = None,
    retryable: bool = True,
    safe_examples: list[str] | None = None,
    next_steps: list[str] | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {
        "protocol_version": PROTOCOL_VERSION,
        "code": code,
        "message": message,
        "retryable": retryable,
        "safe_examples": safe_examples or [],
        "next_steps": next_steps or ["Call handshake to inspect the declared request shape, then retry."],
    }
    for key, value in {
        "field_path": field_path,
        "expected_shape": expected_shape,
        "received_value_redacted": received_value_redacted,
    }.items():
        if value is not None:
            error[key] = value
    return _response(operation, request_id, status="error", errors=[error], retryable=retryable)


def _response(
    operation: str,
    request_id: str,
    *,
    status: str,
    data: dict[str, Any] | None = None,
    errors: list[dict[str, Any]] | None = None,
    receipt: dict[str, Any] | None = None,
    receipt_ref: str | None = None,
    next_steps: list[str] | None = None,
    retryable: bool = False,
) -> dict[str, Any]:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "operation": operation,
        "status": status,
        "data": data or {},
        "errors": errors or [],
        "next_steps": next_steps or [],
        "retryable": retryable,
        "receipt": receipt,
        "receipt_ref": receipt_ref,
        "evidence_refs": [],
        "gap_refs": [],
        "freshness": None,
    }


def _valid_ref(value: Any) -> bool:
    return isinstance(value, str) and bool(_REF_RE.fullmatch(value))


def _request_id() -> str:
    return f"request:cli.{uuid4().hex}"
