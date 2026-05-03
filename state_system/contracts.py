from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


JsonObject = dict[str, Any]


@dataclass(frozen=True)
class ValidationResult:
    path: Path
    schema: str
    ok: bool
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExampleIndex:
    by_id: dict[str, JsonObject]
    paths_by_id: dict[str, list[Path]]
    documents_by_path: dict[Path, JsonObject]

    @classmethod
    def load(cls, examples_dir: Path) -> "ExampleIndex":
        by_id: dict[str, JsonObject] = {}
        paths_by_id: dict[str, list[Path]] = {}
        documents_by_path: dict[Path, JsonObject] = {}

        for path in sorted(examples_dir.rglob("*.json")):
            document = load_json(path)
            documents_by_path[path] = document
            document_id = document.get("id")
            if isinstance(document_id, str):
                by_id[document_id] = document
                paths_by_id.setdefault(document_id, []).append(path)

        return cls(by_id=by_id, paths_by_id=paths_by_id, documents_by_path=documents_by_path)


def load_json(path: Path) -> JsonObject:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate_all_examples(root: Path) -> list[ValidationResult]:
    schemas = _load_schemas(root / "schemas")
    results: list[ValidationResult] = []

    for path in sorted((root / "examples").rglob("*.json")):
        schema_name = schema_for_example(path.name)
        if schema_name is None:
            continue

        schema = schemas[schema_name]
        document = load_json(path)
        errors = tuple(validate_schema(document, schema))
        results.append(
            ValidationResult(
                path=path,
                schema=schema_name,
                ok=not errors,
                errors=errors,
            )
        )

    return results


def validate_trace(
    root: Path,
    trace_paths: list[str],
    *,
    index: ExampleIndex | None = None,
) -> list[str]:
    index = index or ExampleIndex.load(root / "examples")
    documents = [load_json(root / path) for path in trace_paths]
    failures: list[str] = []

    for document in documents:
        document_id = document.get("id")
        if isinstance(document_id, str) and document_id not in index.by_id:
            failures.append(f"{document_id} is not indexed")

    source_event = _first_with(documents, "source_event_id")
    trigger = _first_trigger_document(documents)
    review_packet = _first_with_prefix(documents, "review_packet.")
    model_output = _first_with_prefix(documents, "model_output.")
    commit_result = _first_with_prefix(documents, "commit.")

    if trigger and review_packet:
        _expect_equal(
            failures,
            review_packet.get("trigger", {}).get("id"),
            trigger.get("id"),
            "review packet trigger id must match trigger id",
        )

    if review_packet and model_output:
        _expect_equal(
            failures,
            model_output.get("review_packet_id"),
            review_packet.get("id"),
            "model output review_packet_id must match review packet id",
        )

    if model_output and commit_result:
        _expect_equal(
            failures,
            commit_result.get("model_output_id"),
            model_output.get("id"),
            "commit result model_output_id must match model output id",
        )

    if source_event and trigger:
        source_event_id = source_event.get("source_event_id")
        _expect_equal(
            failures,
            trigger.get("payload", {}).get("source_event_id"),
            source_event_id,
            "trigger source_event_id must match source event",
        )
        _expect_equal(
            failures,
            source_event.get("idempotency", {}).get("key"),
            source_event_id,
            "source event idempotency key must match source_event_id",
        )

    if commit_result:
        _check_commit_refs(commit_result, index, failures)

    review_signal = _first_with_prefix(documents, "review.")
    if commit_result and review_signal:
        embedded_signal = commit_result.get("review_signal", {})
        _expect_equal(
            failures,
            embedded_signal.get("id"),
            review_signal.get("id"),
            "commit result review signal id must match review signal fixture",
        )

    recent_change = _first_with_prefix(documents, "recent.")
    if recent_change:
        _check_refs(recent_change.get("trigger_refs", []), index, failures, "recent trigger")
        _check_refs(
            recent_change.get("journal_entry_refs", []),
            index,
            failures,
            "recent journal",
        )
        _check_refs(recent_change.get("commit_refs", []), index, failures, "recent commit")
        _check_refs(
            recent_change.get("review_signal_refs", []),
            index,
            failures,
            "recent review signal",
        )

    context_package = _first_with_prefix(documents, "context.")
    if context_package and recent_change:
        entries = context_package.get("recent_change_context", {}).get("entries", [])
        entry_ids = [entry.get("id") for entry in entries]
        if recent_change.get("id") not in entry_ids:
            failures.append("context package must include recent change entry")

    opportunity_packet = _opportunity_packet(documents)
    if opportunity_packet and context_package:
        payload = opportunity_packet.get("trigger", {}).get("payload", {})
        _expect_equal(
            failures,
            payload.get("context_package_ref"),
            context_package.get("id"),
            "opportunity packet must cite context package",
        )
        if recent_change:
            _expect_equal(
                failures,
                payload.get("recent_change_ref"),
                recent_change.get("id"),
                "opportunity packet must cite recent change",
            )

    return failures


def schema_for_example(filename: str) -> str | None:
    if filename.endswith(".trace.json"):
        return "trace-manifest.schema.json"
    if filename.endswith("-activation.json"):
        return "agent-activation.schema.json"
    if filename.startswith("source-"):
        return "source-event.schema.json"
    if filename.endswith("-trigger.json"):
        return "trigger.schema.json"
    if filename.endswith("-model-review-packet.json") or filename.endswith(
        "-opportunity-review-packet.json"
    ):
        return "model-review-packet.schema.json"
    if filename.endswith("-model-proposal-output.json") or filename.endswith(
        "-opportunity-model-output.json"
    ):
        return "model-proposal-output.schema.json"
    if filename.endswith("-commit-result.json"):
        return "commit-result.schema.json"
    if filename.endswith("-review-signal.json"):
        return "review-signal.schema.json"
    if filename.endswith("-journal-entry.json"):
        return "state-journal-entry.schema.json"
    if filename.endswith("-agent-memory-entry.json"):
        return "agent-memory-entry.schema.json"
    if filename.endswith("-persona.json"):
        return "persona.schema.json"
    if filename.endswith("-policy.json"):
        return "governance-policy.schema.json"
    if filename.startswith("recent-"):
        return "recent-change-entry.schema.json"
    if filename.endswith("-context-package.json"):
        return "context-package.schema.json"
    if filename.endswith("-state.json") or "-state-after-" in filename:
        return "state-object.schema.json"
    return None


def validate_schema(document: Any, schema: JsonObject, path: str = "$") -> list[str]:
    errors: list[str] = []
    expected_type = schema.get("type")

    if expected_type and not _matches_type(document, expected_type):
        return [f"{path}: expected {expected_type}, got {type(document).__name__}"]

    if isinstance(document, dict):
        for key in schema.get("required", []):
            if key not in document:
                errors.append(f"{path}: missing required key {key}")

        properties = schema.get("properties", {})
        for key, subschema in properties.items():
            if key in document and isinstance(subschema, dict):
                errors.extend(validate_schema(document[key], subschema, f"{path}.{key}"))

    if isinstance(document, list):
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(document):
                errors.extend(validate_schema(item, item_schema, f"{path}[{index}]"))

    if "enum" in schema and document not in schema["enum"]:
        errors.append(f"{path}: expected one of {schema['enum']}, got {document!r}")

    return errors


def _load_schemas(schemas_dir: Path) -> dict[str, JsonObject]:
    return {path.name: load_json(path) for path in sorted(schemas_dir.glob("*.json"))}


def _matches_type(value: Any, expected_type: str) -> bool:
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "number":
        return isinstance(value, int | float) and not isinstance(value, bool)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    return True


def _first_with(documents: list[JsonObject], key: str) -> JsonObject | None:
    return next((document for document in documents if key in document), None)


def _first_with_prefix(documents: list[JsonObject], prefix: str) -> JsonObject | None:
    return next(
        (
            document
            for document in documents
            if isinstance(document.get("id"), str) and document["id"].startswith(prefix)
        ),
        None,
    )


def _first_trigger_document(documents: list[JsonObject]) -> JsonObject | None:
    return next(
        (
            document
            for document in documents
            if isinstance(document.get("id"), str)
            and document["id"].startswith("trigger.")
        ),
        None,
    )


def _opportunity_packet(documents: list[JsonObject]) -> JsonObject | None:
    return next(
        (
            document
            for document in documents
            if document.get("trigger", {}).get("payload", {}).get("context_package_ref")
        ),
        None,
    )


def _check_commit_refs(
    commit_result: JsonObject,
    index: ExampleIndex,
    failures: list[str],
) -> None:
    _check_refs(
        commit_result.get("accepted_journal_entry_refs", []),
        index,
        failures,
        "accepted journal",
    )
    _check_refs(
        commit_result.get("accepted_memory_entry_refs", []),
        index,
        failures,
        "accepted memory",
    )
    _check_refs(
        commit_result.get("materialized_snapshot_refs", []),
        index,
        failures,
        "materialized snapshot",
    )


def _check_refs(
    refs: list[str],
    index: ExampleIndex,
    failures: list[str],
    label: str,
) -> None:
    for ref in refs:
        if ref not in index.by_id:
            failures.append(f"{label} ref does not resolve: {ref}")


def _expect_equal(
    failures: list[str],
    actual: Any,
    expected: Any,
    message: str,
) -> None:
    if actual != expected:
        failures.append(f"{message}: expected {expected!r}, got {actual!r}")
