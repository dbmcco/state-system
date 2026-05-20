from __future__ import annotations

from pathlib import Path
from typing import Any

from state_system.contracts import JsonObject, load_json, validate_schema


class PackagePressureValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("package pressure registry validation failed")
        self.errors = tuple(errors)


def load_pressure_registry(path: Path) -> JsonObject:
    return load_json(path)


def validate_pressure_registry(registry: JsonObject, schema: JsonObject) -> None:
    errors = validate_schema(registry, schema)
    if errors:
        raise PackagePressureValidationError(errors)


def run_package_pressure(
    registry: JsonObject,
    packages: dict[str, JsonObject],
    *,
    include_planned: bool = False,
) -> JsonObject:
    cases = [
        case
        for case in registry.get("cases", [])
        if include_planned or case.get("status") == "ready"
    ]
    results = [_run_case(case, packages) for case in cases]
    failures = [result for result in results if result["status"] != "passed"]
    return {
        "id": f"package_pressure_report.{registry.get('id', 'unknown')}",
        "registry_id": registry.get("id"),
        "ok": not failures,
        "case_count": len(results),
        "failed_count": len(failures),
        "results": results,
    }


def _run_case(case: JsonObject, packages: dict[str, JsonObject]) -> JsonObject:
    package_id = case["package_id"]
    package = packages.get(package_id)
    if package is None:
        return {
            "case_id": case["id"],
            "package_id": package_id,
            "status": "failed",
            "errors": [f"package not supplied: {package_id}"],
        }

    errors: list[str] = []
    assertions = case.get("assertions", {})
    _require_all(errors, "route", assertions.get("required_route_ids", []), _route_ids(package))
    _require_all(
        errors,
        "source coverage",
        assertions.get("required_source_coverage_refs", []),
        _source_coverage_refs(package),
    )
    _require_all(errors, "tool", assertions.get("required_tool_refs", []), _tool_refs(package))
    _require_all(
        errors,
        "tool action",
        assertions.get("required_tool_action_refs", []),
        _tool_action_refs(package),
    )
    _require_all(
        errors,
        "source gap",
        assertions.get("required_source_gap_refs", []),
        set(package.get("source_context", {}).get("source_gap_refs", [])),
    )
    _require_all(
        errors,
        "federation pack",
        assertions.get("required_federation_pack_ids", []),
        _federation_pack_ids(package),
    )
    _require_all(
        errors,
        "remote instance",
        assertions.get("required_remote_instance_refs", []),
        _remote_instance_refs(package),
    )
    _check_materialization_false(
        errors,
        package,
        assertions.get("materialization_false_for_pack_ids", []),
    )
    _check_answer_policy_flags(
        errors,
        package,
        assertions.get("required_answer_policy_flags", []),
    )
    _check_source_status(errors, package, assertions.get("required_source_status", []))
    _check_open_question_fragments(
        errors,
        package,
        assertions.get("required_open_question_fragments", []),
    )
    return {
        "case_id": case["id"],
        "package_id": package_id,
        "status": "failed" if errors else "passed",
        "errors": errors,
    }


def _require_all(
    errors: list[str],
    label: str,
    expected: list[str],
    actual: set[str],
) -> None:
    for value in expected:
        if value not in actual:
            errors.append(f"missing {label}: {value}")


def _route_ids(package: JsonObject) -> set[str]:
    return {route.get("id", "") for route in package.get("question_routes", [])}


def _source_coverage_refs(package: JsonObject) -> set[str]:
    return {
        coverage.get("coverage_ref", "")
        for route in package.get("question_routes", [])
        for coverage in route.get("required_source_coverage", [])
    }


def _tool_refs(package: JsonObject) -> set[str]:
    return {
        tool_ref
        for route in package.get("question_routes", [])
        for tool_ref in route.get("tool_refs", [])
    }


def _tool_action_refs(package: JsonObject) -> set[str]:
    return {
        tool_ref
        for route in package.get("question_routes", [])
        for tool_ref in route.get("tool_action_refs", [])
    }


def _federation_pack_ids(package: JsonObject) -> set[str]:
    return {pack.get("id", "") for pack in package.get("federation_packs", [])}


def _remote_instance_refs(package: JsonObject) -> set[str]:
    return {
        remote_ref
        for pack in package.get("federation_packs", [])
        for remote_ref in pack.get("remote_instance_refs", [])
    }


def _check_materialization_false(
    errors: list[str],
    package: JsonObject,
    pack_ids: list[str],
) -> None:
    packs = {pack.get("id"): pack for pack in package.get("federation_packs", [])}
    for pack_id in pack_ids:
        pack = packs.get(pack_id)
        if not pack:
            errors.append(f"missing federation pack for materialization check: {pack_id}")
            continue
        materialization = pack.get("materialization_policy", {})
        if materialization.get("local_materialization") is not False:
            errors.append(f"federation pack must set local_materialization=false: {pack_id}")


def _check_answer_policy_flags(
    errors: list[str],
    package: JsonObject,
    flags: list[str],
) -> None:
    policies = [
        route.get("answer_contract_policy", {})
        for route in package.get("question_routes", [])
    ]
    for flag in flags:
        if not any(policy.get(flag) is True for policy in policies):
            errors.append(f"missing answer policy flag: {flag}")


def _check_source_status(
    errors: list[str],
    package: JsonObject,
    expected_sources: list[JsonObject],
) -> None:
    sources = {
        source.get("connector_ref"): source
        for source in package.get("source_context", {}).get("source_readiness", [])
    }
    for expected in expected_sources:
        connector_ref = expected["connector_ref"]
        source = sources.get(connector_ref)
        if not source:
            errors.append(f"missing source readiness: {connector_ref}")
            continue
        for key in ("access_status", "freshness_status", "understanding_status"):
            if key in expected and source.get(key) != expected[key]:
                errors.append(
                    f"{connector_ref} {key} expected {expected[key]!r}, got {source.get(key)!r}"
                )


def _check_open_question_fragments(
    errors: list[str],
    package: JsonObject,
    fragments: list[str],
) -> None:
    text = "\n".join(str(value) for value in _walk(package.get("open_questions", [])))
    for fragment in fragments:
        if fragment not in text:
            errors.append(f"open questions missing fragment: {fragment}")


def _walk(value: Any) -> list[Any]:
    if isinstance(value, dict):
        return [item for pair in value.items() for item in _walk(pair)]
    if isinstance(value, list):
        return [item for entry in value for item in _walk(entry)]
    return [value]
