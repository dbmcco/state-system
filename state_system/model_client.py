"""Live model client for canonical-claim and canon-edit review.

Shells out to ``pi`` (non-anthropic route) to obtain a semantic judgment. Code
owns prompt assembly, the subprocess call, JSON extraction, and schema
validation. The MODEL owns the judgment and whether it is uncertain. No code
path fabricates or defaults a judgment; unparseable or schema-invalid model
output raises :class:`ModelOutputInvalid` so the caller can hold the item for
human review rather than silently fill it.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from state_system.contracts import JsonObject, load_json, validate_schema

DEFAULT_MODEL_ROUTE = "openai-codex/gpt-5.5"


class ModelOutputInvalid(ValueError):
    """The model returned output that could not be parsed or validated."""


_PROMPT_TEMPLATES: dict[str, str] = {
    "canon-edit-judgment.v1": (
        "You are judging a raw human edit to a canonical-claim store. Decide the "
        "governed action that should result.\n"
        "Actions:\n"
        "- supersede: the edit replaces an existing claim with a new canon statement\n"
        "- amend: an in-place correction of the SAME claim (typo, evidence ref, window)\n"
        "- retract: the edit removes a claim with no replacement\n"
        "- add: the edit introduces a brand-new claim\n"
        "- uncertain: you cannot confidently tell which\n\n"
        "Emit ONLY a JSON object with EXACTLY these fields:\n"
        '{"edit_item_id": <string, copied from the edit item id>, '
        '"action": <one of supersede|amend|retract|add|uncertain>, '
        '"confidence": <number 0-1>, "rationale": <one short sentence>, '
        '"requires_human_review": <boolean, true when action is uncertain or the '
        'change is high-stakes>, "resulting_claim": <the canonical-claim record this '
        'edit should become, or null for retract/uncertain>}\n\n'
        "When action is supersede/add/amend, resulting_claim MUST be a complete valid "
        "canonical claim: id, entity_ref, claim_type, statement, artifact_ref, "
        "evidence_refs, status, supersedes, determined_at, validity "
        "{window_days, basis, last_confirmed_at}, generated_at, generated_by. "
        "If you are unsure which action applies, set action=\"uncertain\" and "
        "requires_human_review=true. Emit only the JSON object."
    ),
    "canonical-claim-judgment.v1": (
        "You are judging whether a canonical claim still holds against the current "
        "evidence assembled below.\n"
        "judgment values:\n"
        "- still_holds: the claim matches current evidence\n"
        "- drifted: the underlying context has changed; the claim is partly wrong\n"
        "- superseded: a newer decision/document has replaced it\n"
        "- uncertain: you cannot confidently tell\n\n"
        "Emit ONLY a JSON object with EXACTLY these fields:\n"
        '{"claim_id": <string>, "judgment": <one of still_holds|drifted|superseded'
        '|uncertain>, "rationale": <one short sentence>, "confidence": <number 0-1>, '
        '"newer_evidence_refs": [<strings>], "reviewed_at": <ISO-8601 instant>}. '
        "Emit only the JSON object."
    ),
}


class PiModelClient:
    """Calls ``pi -p`` to obtain a review judgment and validates it.

    The model owns the semantic judgment; this class owns transport, parsing,
    and schema validation. It never substitutes a default judgment.
    """

    def __init__(
        self,
        *,
        model_route: str = DEFAULT_MODEL_ROUTE,
        project_root: Path | str,
        pi_bin: str = "pi",
        timeout: int = 300,
    ) -> None:
        if "anthropic" in model_route:
            raise ValueError(
                "anthropic models are not permitted for state-system review; "
                "use a non-anthropic route."
            )
        self.model_route = model_route
        self.project_root = Path(project_root)
        self.pi_bin = pi_bin
        self.timeout = timeout

    def review(self, *, registry_route: str, schema_ref: str, **payload: Any) -> JsonObject:
        prompt = self._build_prompt(schema_ref, payload)
        raw = self._call_model(prompt)
        judgment = self._extract_json(raw)
        self._validate(schema_ref, judgment)
        return judgment

    def _build_prompt(self, schema_ref: str, payload: dict[str, Any]) -> str:
        template = _PROMPT_TEMPLATES.get(schema_ref)
        if template is None:
            raise ValueError(f"no prompt template for schema_ref {schema_ref!r}")
        return (
            f"{template}\n\n"
            f"REGISTRY ROUTE: {schema_ref}\n"
            "PAYLOAD (edit item or claim + assembled evidence):\n"
            f"{json.dumps(payload, indent=2, sort_keys=True)}\n\n"
            "Emit only the JSON object described above."
        )

    def _call_model(self, prompt: str) -> str:
        proc = subprocess.run(
            [self.pi_bin, "-p", "--no-tools", "--no-session", "--model", self.model_route, prompt],
            capture_output=True,
            text=True,
            timeout=self.timeout,
            check=False,
        )
        if proc.returncode != 0:
            raise ModelOutputInvalid(
                f"pi call failed (exit {proc.returncode}): {proc.stderr.strip()[:400]}"
            )
        return proc.stdout

    @staticmethod
    def _extract_json(raw: str) -> JsonObject:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ModelOutputInvalid("no JSON object found in model output")
        candidate = raw[start : end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as error:
            raise ModelOutputInvalid(f"model output is not valid JSON: {error}") from error

    def _validate(self, schema_ref: str, judgment: JsonObject) -> None:
        if schema_ref == "canon-edit-judgment.v1":
            # No standalone schema file; shape is enforced by the reconcile module.
            from state_system.canon_reconcile import _validate_judgment_shape

            _validate_judgment_shape(judgment)
        elif schema_ref == "canonical-claim-judgment.v1":
            schema = load_json(
                self.project_root / "schemas" / "canonical-claim-judgment.schema.json"
            )
            errors = validate_schema(judgment, schema)
            if errors:
                raise ModelOutputInvalid(
                    f"canonical-claim-judgment failed schema validation: {errors}"
                )
        else:
            raise ValueError(f"unknown schema_ref for validation: {schema_ref!r}")


__all__ = ["PiModelClient", "ModelOutputInvalid", "DEFAULT_MODEL_ROUTE"]
