"""Strategic staleness review loop — strategic claims -> reviewer -> dated packet.

This is the SEMANTIC/STRATEGIC staleness surface. Where ``staleness_runner.py``
surfaces infrastructure/connector freshness ("is the Stripe connector still
wired?"), this module surfaces whether STRATEGIC decisions, claims, and
directions still hold or have drifted. The canonical case it exists to catch:
the ForgeWorks 30/60/90 delivery model was a strategic claim that became stale
and was superseded by the 30-day-to-working-software model, but nothing flagged
it as drifted until it was caught manually. This runner surfaces exactly that
kind of drift.

Division of ownership (same model-mediated doctrine as the freshness runner):

- CODE owns: gathering strategic claims from source documents, computing
  objective facts (age since a declared last-validated date, whether a declared
  validity window has been exceeded), packet structure, schema validation, the
  auto-revise *gate* (explicit policy, OFF this build phase), rendering the
  dated packet, and persistence.
- MODEL owns: every semantic judgment per surfaced claim — the natural-language
  question, the recommended action (validate / revise / retire), the
  confidence, and the objective_drift / uncertain classification. Code never
  generates these.

Two source layers feed the loop:

1. COMPANY-LEVEL strategic state — ``company_memory`` read models carry mission,
   strategy, current priorities, and projects per portfolio company. Each
   declared claim becomes a finding (mission / strategy / priority / project).
2. CROSS-CUTTING operating decisions — the operating framework, tracker
   boundaries, and decision-claim handoffs. Each operating document becomes a
   finding carrying the declared metadata the document itself states (title,
   a declared ``Status:`` line, a declared ``Created:`` / ``Updated:`` date).
   Code extracts these declared fields exactly as a freshness record exposes its
   own ``status``; it does not interpret whether the decision has drifted.

Hard rules honored here (same as the freshness runner):

- No live cadence host. This runs on demand.
- No auto-mutation. The auto-revise gate only ever *proposes*; execution always
  requires operator approval routed through governance.
- Auto-revise defaults OFF and this module never turns it on.
- No heuristics / regex / thresholds for classification. Regex is used only to
  extract declared metadata fields a document states about itself (status,
  dates) — evidence gathering, never judgment.
"""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Protocol

from state_system.contracts import JsonObject, load_json, validate_schema
from state_system.staleness_runner import parse_instant, review_week


# --------------------------------------------------------------------------
# Governance context (explicit policy, not semantic judgment)
# --------------------------------------------------------------------------

DEFAULT_STRATEGIC_REVIEW_QUESTION = (
    "For each strategic claim — a company mission, strategy, current priority, "
    "project, or cross-cutting operating decision — judge whether it still holds "
    "or has drifted. Has the underlying context changed? Has it been superseded "
    "by a newer decision or document? Is there evidence it is being acted on as "
    "if still current when it may not be? Surface a plain-language question plus "
    "a recommended action (validate, revise, or retire), with evidence and a "
    "confidence score. Classify each claim objective_drift (a verifiable change "
    "— a referenced fact moved, a stated priority was superseded in a newer "
    "document) or uncertain (needs human judgment). Do not assume drift matters; "
    "judge it from the evidence."
)

DEFAULT_STRATEGIC_GOVERNANCE_CONSTRAINTS: list[JsonObject] = [
    {
        "id": "no-auto-mutation",
        "rule": (
            "No mutation executes without operator approval routed through "
            "governance. The runner only surfaces findings or produces proposals "
            "that still require approval."
        ),
    },
    {
        "id": "model-mediated-discipline",
        "rule": (
            "Classification, recommended action, confidence, and the natural-"
            "language question are model-owned. Code owns structure, evidence, "
            "and gates; it must not substitute heuristics, regex, or thresholds "
            "for these judgments."
        ),
    },
]

REVISE_GATE_OFF_CONSTRAINT: JsonObject = {
    "id": "auto-revise-gated",
    "rule": (
        "Auto-revise is OFF this build phase. Surface decisions only; do not emit "
        "revise_proposals."
    ),
}

REVISE_GATE_ON_CONSTRAINT: JsonObject = {
    "id": "auto-revise-armed",
    "rule": (
        "Auto-revise is armed. Revise proposals may be generated for claims the "
        "model classified as objective_drift with recommended_action revise; "
        "every proposal still requires approval before any mutation."
    ),
}


# --------------------------------------------------------------------------
# Local presentation helpers (kept local so this module does not reach into the
# freshness runner's private names; parse_instant / review_week are public).
# --------------------------------------------------------------------------


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-").lower()


def _zulu(moment: datetime) -> str:
    return (
        moment.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


# --------------------------------------------------------------------------
# Step 1 — gather strategic claims (code-owned; no judgment)
# --------------------------------------------------------------------------


def gather_company_memory_docs(
    *,
    company_memory_dir: Path | None = None,
    company_memory_files: Iterable[Path] | None = None,
) -> list[tuple[JsonObject, str]]:
    """Load company_memory documents from a directory and/or explicit files.

    Returns ``(document, source_doc_ref)`` pairs. The source ref is the file
    path when loaded from disk so a reviewer can cite provenance. Documents are
    returned as-is; they are evidence, not findings.
    """
    pairs: list[tuple[JsonObject, str]] = []
    if company_memory_dir is not None:
        for path in sorted(company_memory_dir.glob("*-company-memory.json")):
            pairs.append((load_json(path), str(path)))
    if company_memory_files is not None:
        for path in company_memory_files:
            path = Path(path)
            pairs.append((load_json(path), str(path)))
    return pairs


def _claims_from_company_memory(
    document: JsonObject, source_doc_ref: str
) -> list[JsonObject]:
    """Turn one company_memory document into pre-finding claim records.

    Produces one claim per declared strategic assertion: the mission, the
    strategy, each current priority, and each project. Every field is carried
    verbatim from the document's own declarations; nothing here judges whether
    a claim still holds.
    """
    subject = str(document["subject_ref"])
    freshness = document.get("freshness", {})
    as_of_raw = freshness.get("as_of")
    stale_after_raw = freshness.get("stale_after")
    doc_evidence = list(document.get("evidence_refs", []))
    claims: list[JsonObject] = []

    mission = document.get("mission", {})
    claims.append(
        _claim(
            scope_key=f"{subject}|company_mission",
            claim_kind="company_mission",
            subject_ref=subject,
            claim_summary=str(mission.get("summary", "")),
            declared_status="",
            last_validated_at=as_of_raw,
            declared_stale_after=stale_after_raw,
            source_doc_ref=source_doc_ref,
            evidence_refs=[*mission.get("evidence_refs", []), *doc_evidence],
            detail="",
        )
    )

    strategy = document.get("strategy", {})
    priorities = list(strategy.get("current_priorities", []))
    claims.append(
        _claim(
            scope_key=f"{subject}|company_strategy",
            claim_kind="company_strategy",
            subject_ref=subject,
            claim_summary=str(strategy.get("summary", "")),
            declared_status="",
            last_validated_at=as_of_raw,
            declared_stale_after=stale_after_raw,
            source_doc_ref=source_doc_ref,
            evidence_refs=[*strategy.get("evidence_refs", []), *doc_evidence],
            detail="; ".join(priorities),
        )
    )

    for index, priority in enumerate(priorities):
        claims.append(
            _claim(
                scope_key=f"{subject}|company_priority:{index}",
                claim_kind="company_priority",
                subject_ref=subject,
                claim_summary=str(priority),
                declared_status="",
                last_validated_at=as_of_raw,
                declared_stale_after=stale_after_raw,
                source_doc_ref=source_doc_ref,
                evidence_refs=[*strategy.get("evidence_refs", []), *doc_evidence],
                detail="",
            )
        )

    for project in document.get("projects", []):
        claims.append(
            _claim(
                scope_key=f"{subject}|company_project:{project.get('id', '')}",
                claim_kind="company_project",
                subject_ref=subject,
                claim_summary=str(project.get("summary", "")),
                declared_status=str(project.get("status", "")),
                last_validated_at=as_of_raw,
                declared_stale_after=stale_after_raw,
                source_doc_ref=source_doc_ref,
                evidence_refs=[*project.get("evidence_refs", []), *doc_evidence],
                detail="",
            )
        )

    return claims


_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def _extract_declared_field(lines: list[str], key: str) -> str:
    """Extract a declared metadata value for ``key`` (e.g. Status, Created).

    Matches a line that states the field at the start, with optional markdown
    bold markers, immediately followed by a colon — the shape of declared
    metadata lines like ``**Status:** Draft`` or ``Created: 2026-06-24``. This
    is reading a field the document declares about itself (evidence), exactly
    analogous to reading a freshness record's own ``status`` field; it is not
    semantic judgment.
    """
    pattern = re.compile(
        r"^\s*\*{0,2}"
        + re.escape(key)
        + r"\*{0,2}\s*:\s*\*{0,2}\s*(.+?)\s*$",
        re.IGNORECASE,
    )
    for line in lines:
        match = pattern.match(line)
        if match:
            # Strip any residual markdown bold markers around the value; the
            # colon can sit inside the bold (**Status:** value) or after it.
            return match.group(1).strip().strip("*").strip()
    return ""


def _declared_date_to_iso(raw: str) -> str | None:
    """Parse the first YYYY-MM-DD in a declared date string to a Zulu instant.

    Operating docs state human dates ("2026-06-24", "2026-06-25 20:15 EDT").
    Extracting the declared calendar date is objective evidence of when the doc
    says it was last touched; it is not a judgment about currency.
    """
    if not raw:
        return None
    match = _DATE_RE.search(raw)
    if not match:
        return None
    return f"{match.group(1)}T00:00:00Z"


def _claims_from_operating_doc(path: Path) -> list[JsonObject]:
    """Turn one operating/decision-claim markdown document into a claim record.

    Carries the document's own declared metadata (title, a declared Status line,
    a declared Created/Updated date). Code does not parse the body for meaning;
    a live reviewer reads the document, and a recorded reviewer carries a prior
    judgment. The finding is honest evidence either way.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    title = ""
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            break
    if not title:
        title = path.stem
    declared_status = _extract_declared_field(lines, "Status")
    created = _extract_declared_field(lines, "Created")
    updated = _extract_declared_field(lines, "Updated") or _extract_declared_field(
        lines, "Last updated"
    )
    last_validated_raw = updated or created
    return [
        _claim(
            scope_key=f"portfolio|operating-decision:{_slug(path.stem)}",
            claim_kind="operating_decision",
            subject_ref="portfolio",
            claim_summary=title,
            declared_status=declared_status,
            last_validated_at=_declared_date_to_iso(last_validated_raw),
            declared_stale_after=None,
            source_doc_ref=str(path),
            evidence_refs=[f"operating-decision:{_slug(path.stem)}", str(path)],
            detail=(
                f"declared status: {declared_status}" if declared_status
                else "no declared status line"
            ),
        )
    ]


def _claim(
    *,
    scope_key: str,
    claim_kind: str,
    subject_ref: str,
    claim_summary: str,
    declared_status: str,
    last_validated_at: str | None,
    declared_stale_after: str | None,
    source_doc_ref: str,
    evidence_refs: list[str],
    detail: str,
) -> JsonObject:
    return {
        "scope_key": scope_key,
        "claim_kind": claim_kind,
        "subject_ref": subject_ref,
        "claim_summary": claim_summary,
        "declared_status": declared_status,
        "last_validated_at": last_validated_at,
        "declared_stale_after": declared_stale_after,
        "source_doc_ref": source_doc_ref,
        "evidence_refs": sorted(set(evidence_refs)),
        "detail": detail,
    }


def _to_finding(claim: JsonObject, as_of: datetime) -> JsonObject:
    """Compute the objective facts (age, window-exceeded) for a claim record.

    Arithmetic only, on fields the source document itself declares — mirroring
    the freshness runner's ``lag_seconds`` / ``exceeds_stale_after``. No field
    here expresses whether the claim has drifted.
    """
    finding: JsonObject = {
        "scope_key": claim["scope_key"],
        "claim_kind": claim["claim_kind"],
        "subject_ref": claim["subject_ref"],
        "claim_summary": claim["claim_summary"],
        "declared_status": claim["declared_status"],
        "validity_window_exceeded": False,
        "source_doc_ref": claim["source_doc_ref"],
        "evidence_refs": list(claim["evidence_refs"]),
    }
    last_validated = claim.get("last_validated_at")
    if last_validated:
        finding["last_validated_at"] = last_validated
        finding["age_days"] = max(0, (as_of - parse_instant(last_validated)).days)
    stale_after = claim.get("declared_stale_after")
    if stale_after:
        finding["declared_stale_after"] = stale_after
        finding["validity_window_exceeded"] = as_of >= parse_instant(stale_after)
    if claim.get("detail"):
        finding["detail"] = claim["detail"]
    return finding


def gather_strategic_findings(
    *,
    company_memory_dir: Path | None = None,
    company_memory_files: Iterable[Path] | None = None,
    company_memory_docs: Iterable[tuple[JsonObject, str]] | None = None,
    operating_docs: Iterable[Path] | None = None,
    as_of: datetime,
) -> list[JsonObject]:
    """Build objective strategic-drift findings from all source layers.

    ``company_memory_docs`` accepts pre-loaded ``(document, source_ref)`` pairs
    (useful for tests); ``company_memory_dir`` / ``company_memory_files`` load
    from disk. ``operating_docs`` accepts markdown paths the operator has
    curated as decision-claim sources (the curation is a human decision, not a
    code heuristic — code surfaces exactly the documents it is pointed at).
    """
    claims: list[JsonObject] = []

    loaded = list(company_memory_docs or [])
    if company_memory_dir is not None or company_memory_files is not None:
        loaded.extend(
            gather_company_memory_docs(
                company_memory_dir=company_memory_dir,
                company_memory_files=company_memory_files,
            )
        )
    for document, source_doc_ref in loaded:
        claims.extend(_claims_from_company_memory(document, source_doc_ref))

    for path in operating_docs or []:
        claims.extend(_claims_from_operating_doc(Path(path)))

    findings = [_to_finding(claim, as_of) for claim in claims]
    findings.sort(key=lambda f: (f["subject_ref"], f["claim_kind"], f["scope_key"]))
    return findings


# --------------------------------------------------------------------------
# Step 2 — build the review packet (code-owned structure)
# --------------------------------------------------------------------------


def strategic_packet_id(scope: str, week: str) -> str:
    return f"strategic_review_packet.{_slug(scope)}.{week}"


def _allowed_strategic_outputs(auto_revise_enabled: bool) -> list[str]:
    """Effect surface permitted to the reviewer. Restricted by the gate.

    Explicit policy scoping the model's effect surface, not semantic judgment.
    """
    outputs = ["surface_decisions", "needs_evidence", "no_op"]
    if auto_revise_enabled:
        outputs.append("revise_proposals")
    return outputs


def build_strategic_review_packet(
    findings: list[JsonObject],
    *,
    as_of: datetime,
    scope: str = "all",
    auto_revise_enabled: bool = False,
    schema: JsonObject | None = None,
    governance_constraints: list[JsonObject] | None = None,
    review_question: str | None = None,
    packet_id_override: str | None = None,
    created_at: datetime | None = None,
) -> JsonObject:
    """Assemble a strategic-staleness review packet from findings + governance."""
    week = review_week(as_of)
    constraints = list(governance_constraints or DEFAULT_STRATEGIC_GOVERNANCE_CONSTRAINTS)
    constraints.append(
        deepcopy(REVISE_GATE_ON_CONSTRAINT if auto_revise_enabled else REVISE_GATE_OFF_CONSTRAINT)
    )
    generated_at = created_at or datetime.now(timezone.utc)
    packet = {
        "id": packet_id_override or strategic_packet_id(scope, week),
        "created_at": _zulu(generated_at),
        "review_kind": "strategic_staleness",
        "review_week": week,
        "as_of": _zulu(as_of),
        "findings": deepcopy(findings),
        "governance_context": {"constraints": constraints},
        "allowed_outputs": _allowed_strategic_outputs(auto_revise_enabled),
        "review_question": review_question or DEFAULT_STRATEGIC_REVIEW_QUESTION,
    }
    if schema is not None:
        errors = validate_schema(packet, schema)
        if errors:
            raise StrategicPacketValidationError(errors)
    return packet


class StrategicPacketValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("strategic review packet validation failed")
        self.errors = tuple(errors)


# --------------------------------------------------------------------------
# Step 3 — reviewer (model-owned judgment, pluggable)
# --------------------------------------------------------------------------


class StrategicReviewer(Protocol):
    """A reviewer owns every per-claim judgment.

    Implementations must return a document conforming to
    ``strategic-review-output.schema.json``. Code validates the contract; it
    does not rewrite or repair the model's judgment.
    """

    def review(self, packet: JsonObject) -> JsonObject:  # pragma: no cover - protocol
        ...


class MissingStrategicJudgmentError(KeyError):
    """Raised when no recorded model judgment exists for a packet.

    The runner treats this as a signal to surface an evidence-only packet
    (clearly marked as awaiting model review) rather than fabricate judgment.
    """


class RecordedStrategicReviewer:
    """Replay recorded strategic review outputs, keyed by review packet id.

    The fixture pattern used by the freshness runner: a recorded output
    represents a real model's judgment about a specific packet. It is the
    dry-run / test reviewer; it does not invent judgment for packets it has no
    recording for.
    """

    def __init__(self, outputs_by_packet_id: dict[str, JsonObject]):
        self.outputs_by_packet_id = {
            key: deepcopy(value) for key, value in outputs_by_packet_id.items()
        }

    @classmethod
    def from_examples(cls, examples_dir: Path) -> "RecordedStrategicReviewer":
        outputs: dict[str, JsonObject] = {}
        for path in sorted(examples_dir.rglob("strategic-review-output-*.json")):
            output = load_json(path)
            outputs[output["review_packet_id"]] = output
        return cls(outputs)

    def review(self, packet: JsonObject) -> JsonObject:
        packet_id = packet["id"]
        if packet_id not in self.outputs_by_packet_id:
            raise MissingStrategicJudgmentError(packet_id)
        return deepcopy(self.outputs_by_packet_id[packet_id])


class LiveStrategicReviewer:
    """Production hook: resolve a model route through the central registry.

    NOT wired this build phase. The contract is documented here so the
    production path is explicit: build the packet, resolve the route +
    credential alias from the central registry, call the model with the packet
    (the model may read the cited operating docs), validate its output against
    ``strategic-review-output.schema.json``, and return it. Code never
    substitutes a heuristic when the model is unavailable.
    """

    def __init__(self, *, registry_route: str):
        self.registry_route = registry_route

    def review(self, packet: JsonObject) -> JsonObject:  # pragma: no cover - not wired
        raise NotImplementedError(
            "Live strategic review is not wired this build phase. Resolve route "
            f"'{self.registry_route}' through the central registry, call the model "
            "with the packet (it may read the cited operating docs), and validate "
            "its output against strategic-review-output.schema.json. Use the "
            "recorded reviewer for dry-runs."
        )


# --------------------------------------------------------------------------
# Step 4 — auto-revise gate (built, OFF by default; proposes only)
# --------------------------------------------------------------------------


class AutoReviseGate:
    """Explicit policy gate over model-decided revisions.

    The MODEL decides classification and recommended_action. This gate only
    decides whether to act on a model decision at all, and even when armed it
    only *proposes* — every proposal carries ``approval_required: true`` and
    execution still requires operator approval. Nothing mutates this build phase.
    """

    def __init__(self, *, enabled: bool = False):
        self.enabled = enabled

    def build_proposals(self, output: JsonObject) -> list[JsonObject]:
        """Derive revise proposals from model-classified objective_drift+revise
        entries. Returns [] when the gate is disabled.
        """
        if not self.enabled:
            return []
        proposals: list[JsonObject] = []
        for entry in output.get("entries", []):
            if (
                entry.get("classification") == "objective_drift"
                and entry.get("recommended_action") == "revise"
            ):
                proposals.append(
                    {
                        "scope_key": entry["scope_key"],
                        "target_ref": _target_ref_from_scope(entry["scope_key"]),
                        "rationale": str(entry.get("rationale", "")),
                        "evidence_refs": list(entry.get("evidence_refs", [])),
                        "approval_required": True,
                    }
                )
        return proposals


def _target_ref_from_scope(scope_key: str) -> str:
    # scope_key is "<subject_ref>|<claim_kind>:<slug>"; subject is the revise target
    return scope_key.split("|", 1)[0]


# --------------------------------------------------------------------------
# Step 5 — render the dated packet (code-owned presentation)
# --------------------------------------------------------------------------


def _humanize_age(age_days: int) -> str:
    if age_days >= 1:
        return f"{age_days} day{'s' if age_days != 1 else ''}"
    return "today"


def _split_claim_scope(scope_key: str) -> tuple[str, str]:
    parts = scope_key.split("|", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return scope_key, ""


_CLAIM_KIND_LABEL = {
    "company_mission": "company mission",
    "company_strategy": "company strategy",
    "company_priority": "current priority",
    "company_project": "project",
    "operating_decision": "operating decision",
}


def _claim_kind_label(kind: str) -> str:
    return _CLAIM_KIND_LABEL.get(kind, kind)


def _finding_index(packet: JsonObject) -> dict[str, JsonObject]:
    return {finding["scope_key"]: finding for finding in packet.get("findings", [])}


def render_strategic_packet_markdown(
    packet: JsonObject,
    output: JsonObject,
    *,
    reviewer_label: str = "recorded",
) -> str:
    """Render a full HYBRID strategic packet (model judgments present)."""
    findings = _finding_index(packet)
    entries = output.get("entries", [])
    drift = sum(1 for e in entries if e.get("classification") == "objective_drift")
    uncertain = sum(1 for e in entries if e.get("classification") == "uncertain")
    subjects = sorted({f["subject_ref"] for f in packet.get("findings", [])})
    lines: list[str] = []
    lines.append(f"# Strategic staleness review — {packet['review_week']}")
    lines.append("")
    lines.append(
        f"Generated {output['created_at']} · as_of {packet['as_of']} · "
        f"{len(entries)} decision{'s' if len(entries) != 1 else ''} queued"
    )
    gate_label = (
        "ON (armed; proposals still require approval)"
        if output.get("auto_revise_enabled")
        else "OFF (surface only)"
    )
    lines.append(f"Auto-revise: {gate_label} · Reviewer: {reviewer_label}")
    lines.append("")
    lines.append(
        "> Strategic drift surface. Every question, action, and classification "
        "below is a model judgment (not a code heuristic). Each entry asks whether "
        "a strategic claim still holds or has drifted; the operator decides."
    )
    lines.append("")
    lines.append("## Summary")
    lines.append(
        f"- {len(entries)} strategic claim{'s' if len(entries) != 1 else ''} surfaced"
        + (f" across {', '.join(subjects)}" if subjects else "")
    )
    lines.append(f"- {drift} objective_drift · {uncertain} uncertain")
    lines.append(f"- decision: {output.get('decision')}")
    lines.append("")
    lines.append("## Decisions")
    lines.append("")
    for index, entry in enumerate(entries, start=1):
        finding = findings.get(entry["scope_key"], {})
        subject, claim_part = _split_claim_scope(entry["scope_key"])
        confidence = entry.get("confidence")
        confidence_text = (
            f"{confidence:.2f}" if isinstance(confidence, (int, float)) else "n/a"
        )
        lines.append(
            f"### {index}. {entry.get('classification')} · "
            f"{entry.get('recommended_action')} · confidence {confidence_text}"
        )
        meta = f"**{subject}** · {_claim_kind_label(str(finding.get('claim_kind', '')))}"
        if claim_part:
            meta += f"  \n*{claim_part}*"
        lines.append("")
        lines.append(meta)
        lines.append("")
        summary = finding.get("claim_summary", "")
        if summary:
            lines.append(f"> claim: {summary}")
            lines.append("")
        validated = finding.get("last_validated_at", "")
        age = finding.get("age_days")
        status = finding.get("declared_status", "")
        provenance_bits: list[str] = []
        if status:
            provenance_bits.append(f"declared status: {status}")
        if validated:
            age_text = _humanize_age(int(age)) if isinstance(age, int) else "n/a"
            provenance_bits.append(f"last validated {validated} ({age_text} ago)")
        window = finding.get("validity_window_exceeded")
        if window:
            provenance_bits.append("declared validity window exceeded")
        provenance_bits.append(f"source: `{finding.get('source_doc_ref', '')}`")
        lines.append("- " + " · ".join(provenance_bits))
        lines.append("")
        lines.append(f"> {entry.get('nl_question')}")
        lines.append("")
        lines.append(f"- recommended action: **{entry.get('recommended_action')}**")
        ev = entry.get("evidence_refs", []) or []
        lines.append("- evidence: " + (", ".join(f"`{e}`" for e in ev) if ev else "n/a"))
        rationale = entry.get("rationale")
        if rationale:
            lines.append(f"- rationale: {rationale}")
        lines.append("")
    if output.get("uncertainty"):
        lines.append("## Uncertainty")
        lines.append("")
        for note in output["uncertainty"]:
            lines.append(f"- {note}")
        lines.append("")
    lines.append("## Auto-revise")
    if output.get("auto_revise_enabled"):
        proposals = output.get("revise_proposals", [])
        lines.append(
            f"ON. {len(proposals)} revision proposal{'s' if len(proposals) != 1 else ''} "
            "generated from model-classified objective_drift+revise entries. Every "
            "proposal requires operator approval (routed through governance) before any mutation."
        )
    else:
        lines.append(
            "OFF. No revision proposals generated. The capability is built and gated; "
            "execution always requires operator approval routed through governance."
        )
    lines.append("")
    return "\n".join(lines)


def render_strategic_evidence_only_markdown(packet: JsonObject) -> str:
    """Render findings with no model judgment — clearly marked as awaiting review."""
    findings = packet.get("findings", [])
    subjects = sorted({f["subject_ref"] for f in findings})
    lines: list[str] = []
    lines.append(f"# Strategic staleness review — {packet['review_week']} (evidence only)")
    lines.append("")
    lines.append(
        f"Generated {packet['created_at']} · as_of {packet['as_of']} · "
        f"{len(findings)} claim{'s' if len(findings) != 1 else ''} surfaced"
    )
    lines.append("")
    lines.append(
        "> **AWAITING MODEL REVIEW.** No model judgment is recorded for this packet. "
        "The findings below are objective evidence only (declared claims, declared "
        "status, declared dates, and age/window arithmetic). Questions, actions, "
        "confidence, and objective_drift/uncertain classification will be filled by "
        "the reviewer (recorded fixture or live model) — never by code heuristics."
    )
    lines.append("")
    if subjects:
        lines.append("Subjects: " + ", ".join(subjects))
        lines.append("")
    lines.append("## Claims awaiting judgment")
    lines.append("")
    for index, finding in enumerate(findings, start=1):
        subject, claim_part = _split_claim_scope(finding["scope_key"])
        lines.append(
            f"### {index}. {_claim_kind_label(finding['claim_kind'])} · {subject}"
        )
        lines.append("")
        if finding.get("claim_summary"):
            lines.append(f"> {finding['claim_summary']}")
            lines.append("")
        bits: list[str] = []
        if finding.get("declared_status"):
            bits.append(f"declared status: {finding['declared_status']}")
        if finding.get("last_validated_at"):
            age = finding.get("age_days")
            age_text = _humanize_age(int(age)) if isinstance(age, int) else "n/a"
            bits.append(f"last validated {finding['last_validated_at']} ({age_text} ago)")
        if finding.get("validity_window_exceeded"):
            bits.append("declared validity window exceeded")
        bits.append(f"source: `{finding.get('source_doc_ref', '')}`")
        lines.append("- " + " · ".join(bits))
        ev = finding.get("evidence_refs", [])
        lines.append("- evidence: " + (", ".join(f"`{e}`" for e in ev) if ev else "n/a"))
        lines.append("")
    lines.append(
        f"Packet JSON (model input): review_packet id `{packet['id']}`. "
        "Record a matching `strategic-review-output` keyed to this id to populate "
        "the full HYBRID packet."
    )
    lines.append("")
    return "\n".join(lines)


def write_strategic_packet_markdown(
    packet: JsonObject,
    output: JsonObject | None,
    *,
    out_dir: Path,
    reviewer_label: str = "recorded",
    filename_suffix: str = "",
) -> Path:
    """Write the dated packet markdown (YYYY-WW[suffix].md). Falls back to
    evidence-only when no model output is supplied.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"-{filename_suffix}" if filename_suffix else ""
    path = out_dir / f"{packet['review_week']}{suffix}.md"
    if output is None:
        text = render_strategic_evidence_only_markdown(packet)
    else:
        text = render_strategic_packet_markdown(packet, output, reviewer_label=reviewer_label)
    path.write_text(text + ("\n" if not text.endswith("\n") else ""), encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# Orchestrator
# --------------------------------------------------------------------------


@dataclass
class StrategicRunResult:
    packet: JsonObject
    output: JsonObject | None
    markdown_path: Path | None
    auto_revise_enabled: bool
    judgments_present: bool
    decisions_queued: int = field(default=0)

    def summary(self) -> JsonObject:
        return {
            "packet_id": self.packet["id"],
            "review_week": self.packet["review_week"],
            "as_of": self.packet["as_of"],
            "findings": len(self.packet["findings"]),
            "judgments_present": self.judgments_present,
            "decisions_queued": self.decisions_queued,
            "decision": self.output.get("decision") if self.output else "awaiting_review",
            "auto_revise_enabled": self.auto_revise_enabled,
            "revise_proposals": len(self.output.get("revise_proposals", [])) if self.output else 0,
            "markdown_path": str(self.markdown_path) if self.markdown_path else None,
        }


def run_strategic_review(
    *,
    company_memory_dir: Path | None = None,
    company_memory_files: Iterable[Path] | None = None,
    company_memory_docs: Iterable[tuple[JsonObject, str]] | None = None,
    operating_docs: Iterable[Path] | None = None,
    as_of: datetime,
    reviewer: StrategicReviewer | None = None,
    scope: str = "all",
    auto_revise_enabled: bool = False,
    out_dir: Path | None = None,
    output_schema: JsonObject | None = None,
    packet_schema: JsonObject | None = None,
    governance_constraints: list[JsonObject] | None = None,
    reviewer_label: str = "recorded",
    filename_suffix: str = "",
) -> StrategicRunResult:
    """Run the full strategic loop: gather -> packet -> review -> render.

    If ``reviewer`` is omitted or has no judgment for the packet, an evidence-
    only packet is produced (no fabricated judgment). ``auto_revise_enabled``
    defaults False and is never turned on by this module.
    """
    findings = gather_strategic_findings(
        company_memory_dir=company_memory_dir,
        company_memory_files=company_memory_files,
        company_memory_docs=company_memory_docs,
        operating_docs=operating_docs,
        as_of=as_of,
    )
    packet = build_strategic_review_packet(
        findings,
        as_of=as_of,
        scope=scope,
        auto_revise_enabled=auto_revise_enabled,
        schema=packet_schema,
        governance_constraints=governance_constraints,
    )

    output: JsonObject | None = None
    judgments_present = False
    if reviewer is not None:
        try:
            reviewed = reviewer.review(packet)
        except MissingStrategicJudgmentError:
            reviewed = None
        if reviewed is not None:
            gate = AutoReviseGate(enabled=auto_revise_enabled)
            proposals = gate.build_proposals(reviewed)
            reviewed = dict(reviewed)
            reviewed["auto_revise_enabled"] = auto_revise_enabled
            reviewed["revise_proposals"] = proposals
            reviewed["review_packet_id"] = packet["id"]
            reviewed.setdefault("review_week", packet["review_week"])
            if output_schema is not None:
                errors = _validate_output_deep(reviewed, output_schema)
                if errors:
                    raise StrategicOutputValidationError(errors)
            output = reviewed
            judgments_present = True

    markdown_path: Path | None = None
    if out_dir is not None:
        markdown_path = write_strategic_packet_markdown(
            packet,
            output,
            out_dir=out_dir,
            reviewer_label=reviewer_label,
            filename_suffix=filename_suffix,
        )

    decisions_queued = len(output.get("entries", [])) if output else len(findings)
    return StrategicRunResult(
        packet=packet,
        output=output,
        markdown_path=markdown_path,
        auto_revise_enabled=auto_revise_enabled,
        judgments_present=judgments_present,
        decisions_queued=decisions_queued,
    )


def _validate_output_deep(output: JsonObject, schema: JsonObject) -> list[str]:
    """Validate the top-level contract, then each entry/proposal against $defs.

    Schema constraint (per-entry required/type/enum), not heuristic judgment —
    mirroring the freshness runner's deep validation.
    """
    errors = list(validate_schema(output, schema))
    entry_schema = schema.get("$defs", {}).get("entry")
    if isinstance(entry_schema, dict):
        for index, entry in enumerate(output.get("entries", [])):
            errors.extend(validate_schema(entry, entry_schema, f"$.entries[{index}]"))
    proposal_schema = schema.get("$defs", {}).get("revise_proposal")
    if isinstance(proposal_schema, dict):
        for index, proposal in enumerate(output.get("revise_proposals", [])):
            errors.extend(validate_schema(proposal, proposal_schema, f"$.revise_proposals[{index}]"))
    return errors


class StrategicOutputValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("strategic review output validation failed")
        self.errors = tuple(errors)


def load_strategic_schemas(project_root: Path) -> dict[str, JsonObject]:
    """Load the two strategic schemas by name (packet, output)."""
    schemas_dir = project_root / "schemas"
    return {
        "strategic_packet": load_json(schemas_dir / "strategic-review-packet.schema.json"),
        "strategic_output": load_json(schemas_dir / "strategic-review-output.schema.json"),
    }
