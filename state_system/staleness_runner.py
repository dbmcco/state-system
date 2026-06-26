"""Staleness review loop — freshness evidence -> reviewer -> dated packet.

This module assembles existing state-system parts into a model-mediated
staleness review loop. The division of ownership is deliberate and matches the
project's model-mediated doctrine:

- CODE owns: gathering freshness evidence, computing objective facts (lag,
  exceeds-stale-after) from a record's own declared fields, packet structure,
  schema validation, the auto-demote *gate* (explicit policy), rendering the
  dated packet, and persistence.
- MODEL owns: every semantic judgment per surfaced finding — the natural-
  language question, the recommended action, the confidence, and the
  objective_stale / uncertain classification. Code never generates these.

The reviewer is a pluggable contract. ``RecordedStalenessReviewer`` replays
recorded model outputs (the legitimate fixture pattern used elsewhere in this
repo for tests and dry-runs — it represents a real model's judgment, it does
not fabricate one). A live model adapter resolves a route through the central
registry and is documented as the production hook; it is not auto-fired in this
build phase.

Hard rules honored here:
- No live cadence host. This runs on demand.
- No auto-mutation. The auto-demote gate only ever *proposes*; execution always
  requires Committer approval routed through governance.
- Auto-demote defaults OFF and this module never turns it on.
- No heuristics / regex / thresholds for classification.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Protocol

from state_system.contracts import JsonObject, load_json, validate_schema
from state_system.stores import StateStoreBundle


# --------------------------------------------------------------------------
# Governance context (explicit policy, not semantic judgment)
# --------------------------------------------------------------------------

DEFAULT_REVIEW_QUESTION = (
    "For each stale, failed, or unknown freshness finding, decide whether it is "
    "an objective staleness call (safe to refresh or, once the gate is open and "
    "approved, demote) or whether it needs a human judgment. Surface a plain-"
    "language question plus a recommended action, with evidence and a confidence "
    "score. Do not assume staleness matters; judge it from the evidence."
)

DEFAULT_GOVERNANCE_CONSTRAINTS: list[JsonObject] = [
    {
        "id": "no-auto-mutation",
        "rule": (
            "No mutation executes without operator approval routed through "
            "governance. "
            "The runner only surfaces findings or produces proposals that still "
            "require approval."
        ),
    },
    {
        "id": "model-mediated-discipline",
        "rule": (
            "Classification, recommended action, confidence, and the natural-"
            "language question are model-owned. Code owns structure, evidence, and "
            "gates; it must not substitute heuristics, regex, or thresholds for "
            "these judgments."
        ),
    },
]

GATE_OFF_CONSTRAINT: JsonObject = {
    "id": "auto-demote-gated",
    "rule": (
        "Auto-demote is OFF this build phase. Surface decisions only; do not emit "
        "demote_proposals."
    ),
}

GATE_ON_CONSTRAINT: JsonObject = {
    "id": "auto-demote-armed",
    "rule": (
        "Auto-demote is armed. Demote proposals may be generated for findings the "
        "model classified as objective_stale with recommended_action demote; every "
        "proposal still requires approval before any mutation."
    ),
}


# --------------------------------------------------------------------------
# Time helpers
# --------------------------------------------------------------------------


def parse_instant(value: str) -> datetime:
    """Parse an ISO-8601 instant (Zulu or offset) to an aware UTC datetime."""
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def review_week(as_of: datetime) -> str:
    """ISO-8601 week (e.g. 2026-W26) for the given instant."""
    iso = as_of.date().isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-").lower()


# --------------------------------------------------------------------------
# Step 1 — gather evidence (code-owned; no judgment)
# --------------------------------------------------------------------------


def gather_freshness_records(
    *,
    state_root: Path | None = None,
    freshness_dir: Path | None = None,
) -> list[JsonObject]:
    """Load raw freshness records from a runtime state root and/or a flat dir.

    ``state_root`` reads the real store collections (instance-source-freshness
    and source-freshness) via :class:`StateStoreBundle`. ``freshness_dir`` reads
    flat ``*.json`` records (a convenience for dry-runs and examples). Records
    from both sources are returned as-is; they are evidence, not findings.
    """
    records: list[JsonObject] = []
    if state_root is not None:
        stores = StateStoreBundle(state_root)
        records.extend(stores.instance_source_freshness.replay())
        records.extend(stores.source_freshness.replay())
    if freshness_dir is not None:
        for path in sorted(freshness_dir.glob("*.json")):
            records.append(load_json(path))
    return records


def _subject(record: JsonObject) -> tuple[str, str]:
    if record.get("instance_ref"):
        return "instance", str(record["instance_ref"])
    if record.get("company_ref"):
        return "company", str(record["company_ref"])
    raise ValueError(
        "freshness record has neither instance_ref nor company_ref: "
        f"{record.get('id') or record.get('scope_key')}"
    )


def _is_surfaced(record: JsonObject, as_of: datetime) -> bool:
    """Surface a record when it is not fresh, or when its own stale-after has
    passed as of the review instant.

    This is evidence surfacing, not judgment: ``status`` is the connector's own
    declared ground truth, and comparing ``as_of`` to the record's own
    ``stale_after`` is arithmetic on a field the record itself declares.
    """
    status = str(record.get("status", "unknown"))
    if status != "fresh":
        return True
    stale_after = record.get("stale_after")
    if not stale_after:
        return False
    return as_of >= parse_instant(str(stale_after))


def gather_findings(
    records: Iterable[JsonObject],
    *,
    as_of: datetime,
) -> list[JsonObject]:
    """Build objective staleness findings from raw freshness records.

    Each finding faithfully serializes a freshness record plus two computed
    objective facts (``lag_seconds`` and ``exceeds_stale_after``). No finding
    expresses whether the staleness matters; that is the reviewer's job.
    """
    findings: list[JsonObject] = []
    for record in records:
        if not _is_surfaced(record, as_of):
            continue
        subject_kind, subject_ref = _subject(record)
        checked_at = parse_instant(str(record["checked_at"]))
        stale_after = parse_instant(str(record["stale_after"]))
        lag_seconds = int(max(0, (as_of - checked_at).total_seconds()))
        findings.append(
            {
                "scope_key": str(record["scope_key"]),
                "subject_kind": subject_kind,
                "subject_ref": subject_ref,
                "connector_ref": str(record["connector_ref"]),
                "source_ref": str(record["source_ref"]),
                "freshness_status": str(record["status"]),
                "checked_at": str(record["checked_at"]),
                "stale_after": str(record["stale_after"]),
                "watermark_basis": str(record["watermark_basis"]),
                "status_reason": str(record.get("status_reason", "")),
                "lag_seconds": lag_seconds,
                "exceeds_stale_after": as_of >= stale_after,
                "freshness_record_id": str(record.get("id", "")),
                "evidence_refs": list(record.get("evidence_refs", [])),
                "detail": str(record.get("detail", "")),
            }
        )
    findings.sort(key=lambda f: (f["subject_ref"], f["scope_key"]))
    return findings


# --------------------------------------------------------------------------
# Step 2 — build the review packet (code-owned structure)
# --------------------------------------------------------------------------


def packet_id(scope: str, week: str) -> str:
    return f"staleness_review_packet.{_slug(scope)}.{week}"


def _allowed_outputs(auto_demote_enabled: bool) -> list[str]:
    """Effect surface permitted to the reviewer. Restricted by the gate.

    This is explicit policy scoping the model's effect surface, not semantic
    judgment: the gate decides whether demotion is even an available output.
    """
    outputs = ["surface_decisions", "needs_evidence", "no_op"]
    if auto_demote_enabled:
        outputs.append("demote_proposals")
    return outputs


def build_review_packet(
    findings: list[JsonObject],
    *,
    as_of: datetime,
    scope: str = "all",
    auto_demote_enabled: bool = False,
    schema: JsonObject | None = None,
    governance_constraints: list[JsonObject] | None = None,
    review_question: str | None = None,
    packet_id_override: str | None = None,
    created_at: datetime | None = None,
) -> JsonObject:
    """Assemble a staleness review packet from findings + governance context."""
    week = review_week(as_of)
    constraints = list(governance_constraints or DEFAULT_GOVERNANCE_CONSTRAINTS)
    constraints.append(deepcopy(GATE_ON_CONSTRAINT if auto_demote_enabled else GATE_OFF_CONSTRAINT))
    generated_at = (created_at or datetime.now(timezone.utc))
    packet = {
        "id": packet_id_override or packet_id(scope, week),
        "created_at": _zulu(generated_at),
        "review_kind": "staleness",
        "review_week": week,
        "as_of": _zulu(as_of),
        "findings": deepcopy(findings),
        "governance_context": {"constraints": constraints},
        "allowed_outputs": _allowed_outputs(auto_demote_enabled),
        "review_question": review_question or DEFAULT_REVIEW_QUESTION,
    }
    if schema is not None:
        errors = validate_schema(packet, schema)
        if errors:
            raise StalenessPacketValidationError(errors)
    return packet


def _zulu(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class StalenessPacketValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("staleness review packet validation failed")
        self.errors = tuple(errors)


# --------------------------------------------------------------------------
# Step 3 — reviewer (model-owned judgment, pluggable)
# --------------------------------------------------------------------------


class StalenessReviewer(Protocol):
    """A reviewer owns every per-finding judgment.

    Implementations must return a document conforming to
    ``staleness-review-output.schema.json``. Code validates the contract; it does
    not rewrite or repair the model's judgment.
    """

    def review(self, packet: JsonObject) -> JsonObject:  # pragma: no cover - protocol
        ...


class MissingStalenessJudgmentError(KeyError):
    """Raised when no recorded model judgment exists for a packet.

    The runner treats this as a signal to surface an evidence-only packet
    (clearly marked as awaiting model review) rather than fabricate judgment.
    """


class RecordedStalenessReviewer:
    """Replay recorded staleness review outputs, keyed by review packet id.

    This is the fixture pattern used elsewhere in the repo (see
    ``reviewer.FixtureReviewer``): a recorded output represents a real model's
    judgment about a specific packet. It is the dry-run / test reviewer; it does
    not invent judgment for packets it has no recording for.
    """

    def __init__(self, outputs_by_packet_id: dict[str, JsonObject]):
        self.outputs_by_packet_id = {
            key: deepcopy(value) for key, value in outputs_by_packet_id.items()
        }

    @classmethod
    def from_examples(cls, examples_dir: Path) -> "RecordedStalenessReviewer":
        outputs: dict[str, JsonObject] = {}
        for path in sorted(examples_dir.rglob("staleness-review-output-*.json")):
            output = load_json(path)
            outputs[output["review_packet_id"]] = output
        return cls(outputs)

    def review(self, packet: JsonObject) -> JsonObject:
        packet_id = packet["id"]
        if packet_id not in self.outputs_by_packet_id:
            raise MissingStalenessJudgmentError(packet_id)
        return deepcopy(self.outputs_by_packet_id[packet_id])


class LiveStalenessReviewer:
    """Production hook: resolve a model route through the central registry.

    NOT wired in this build phase. The contract is documented here so the
    production path is explicit: build the packet, resolve the route + credential
    alias from the central registry, call the model, validate its output against
    ``staleness-review-output.schema.json``, and return it. Code never substitutes
    a heuristic when the model is unavailable.
    """

    def __init__(self, *, registry_route: str):
        self.registry_route = registry_route

    def review(self, packet: JsonObject) -> JsonObject:  # pragma: no cover - not wired
        raise NotImplementedError(
            "Live staleness review is not wired this build phase. Resolve route "
            f"'{self.registry_route}' through the central registry, call the model "
            "with the packet, and validate its output against "
            "staleness-review-output.schema.json. Use the recorded reviewer for "
            "dry-runs."
        )


# --------------------------------------------------------------------------
# Step 4 — auto-demote gate (built, OFF by default; proposes only)
# --------------------------------------------------------------------------


class AutoDemoteGate:
    """Explicit policy gate over model-decided demotions.

    The MODEL decides classification and recommended_action. This gate only
    decides whether to act on a model decision at all, and even when armed it
    only *proposes* — every proposal carries ``approval_required: true`` and
    execution still requires the Committer governance surface. Nothing mutates
    in this build phase.
    """

    def __init__(self, *, enabled: bool = False):
        self.enabled = enabled

    def build_proposals(self, output: JsonObject) -> list[JsonObject]:
        """Derive demote proposals from model-classified objective_stale+demote
        entries. Returns [] when the gate is disabled.
        """
        if not self.enabled:
            return []
        proposals: list[JsonObject] = []
        for entry in output.get("entries", []):
            if (
                entry.get("classification") == "objective_stale"
                and entry.get("recommended_action") == "demote"
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
    # scope_key is "<subject_ref>|<connector_ref>|<source_ref>"; subject is the demote target
    return scope_key.split("|", 1)[0]


# --------------------------------------------------------------------------
# Step 5 — render the dated packet (code-owned presentation)
# --------------------------------------------------------------------------


def _humanize_lag(lag_seconds: int) -> str:
    days = lag_seconds // 86400
    hours = (lag_seconds % 86400) // 3600
    if days >= 1:
        return f"{days} day{'s' if days != 1 else ''}"
    if hours >= 1:
        return f"{hours} hour{'s' if hours != 1 else ''}"
    return f"{lag_seconds} seconds"


def _split_scope(scope_key: str) -> tuple[str, str, str]:
    parts = scope_key.split("|")
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    return scope_key, "", ""


def _finding_index(packet: JsonObject) -> dict[str, JsonObject]:
    return {finding["scope_key"]: finding for finding in packet.get("findings", [])}


def render_packet_markdown(
    packet: JsonObject,
    output: JsonObject,
    *,
    reviewer_label: str = "recorded",
) -> str:
    """Render a full HYBRID packet (model judgments present) to markdown."""
    findings = _finding_index(packet)
    entries = output.get("entries", [])
    objective = sum(1 for e in entries if e.get("classification") == "objective_stale")
    uncertain = sum(1 for e in entries if e.get("classification") == "uncertain")
    companies = sorted({f.split("|", 1)[0] for f in findings})
    lines: list[str] = []
    lines.append(f"# State staleness review — {packet['review_week']}")
    lines.append("")
    lines.append(
        f"Generated {output['created_at']} · as_of {packet['as_of']} · "
        f"{len(entries)} decision{'s' if len(entries) != 1 else ''} queued"
    )
    gate_label = "ON (armed; proposals still require approval)" if output.get("auto_demote_enabled") else "OFF (surface only)"
    lines.append(f"Auto-demote: {gate_label} · Reviewer: {reviewer_label}")
    lines.append("")
    lines.append(
        "> Raw evidence layer. Every question, action, and classification below "
        "is a model judgment (not a code heuristic). The review persona synthesizes "
        "these into the weekly brief; the operator decides."
    )
    lines.append("")
    lines.append("## Summary")
    lines.append(
        f"- {len(entries)} finding{'s' if len(entries) != 1 else ''} surfaced"
        + (f" across {', '.join(companies)}" if companies else "")
    )
    lines.append(f"- {objective} objective_stale · {uncertain} uncertain")
    lines.append(f"- decision: {output.get('decision')}")
    lines.append("")
    lines.append("## Decisions")
    lines.append("")
    for index, entry in enumerate(entries, start=1):
        finding = findings.get(entry["scope_key"], {})
        subject, connector, source = _split_scope(entry["scope_key"])
        confidence = entry.get("confidence")
        confidence_text = f"{confidence:.2f}" if isinstance(confidence, (int, float)) else "n/a"
        lines.append(
            f"### {index}. {entry.get('classification')} · "
            f"{entry.get('recommended_action')} · confidence {confidence_text}"
        )
        status = finding.get("freshness_status", "")
        checked = finding.get("checked_at", "")
        lag = _humanize_lag(int(finding.get("lag_seconds", 0))) if finding else "n/a"
        meta = f"**{subject}** · {connector}|{source}".replace("|", " · ")
        if status:
            meta += f"  \n*{status}, last checked {checked}, {lag} lag*"
        lines.append("")
        lines.append(meta)
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
    lines.append("## Auto-demote")
    if output.get("auto_demote_enabled"):
        proposals = output.get("demote_proposals", [])
        lines.append(
            f"ON. {len(proposals)} demotion proposal{'s' if len(proposals) != 1 else ''} "
            "generated from model-classified objective_stale+demote entries. Every "
            "proposal requires operator approval (routed through governance) before any mutation."
        )
    else:
        lines.append(
            "OFF. No demotion proposals generated. The capability is built and gated; "
            "execution always requires operator approval routed through governance."
        )
    lines.append("")
    return "\n".join(lines)


def render_evidence_only_markdown(packet: JsonObject) -> str:
    """Render findings with no model judgment — clearly marked as awaiting review.

    Used when no recorded/live judgment is available, so real state can still be
    surfaced honestly without code fabricating judgment.
    """
    findings = packet.get("findings", [])
    companies = sorted({f["subject_ref"] for f in findings})
    lines: list[str] = []
    lines.append(f"# State staleness review — {packet['review_week']} (evidence only)")
    lines.append("")
    lines.append(
        f"Generated {packet['created_at']} · as_of {packet['as_of']} · "
        f"{len(findings)} finding{'s' if len(findings) != 1 else ''} surfaced"
    )
    lines.append("")
    lines.append(
        "> **AWAITING MODEL REVIEW.** No model judgment is recorded for this packet. "
        "The findings below are objective evidence only. Questions, actions, "
        "confidence, and objective/uncertain classification will be filled by the "
        "reviewer (recorded fixture or live model) — never by code heuristics."
    )
    lines.append("")
    if companies:
        lines.append("Subjects: " + ", ".join(companies))
        lines.append("")
    lines.append("## Findings awaiting judgment")
    lines.append("")
    for index, finding in enumerate(findings, start=1):
        subject, connector, source = _split_scope(finding["scope_key"])
        lines.append(
            f"### {index}. {finding['freshness_status']} · {_humanize_lag(int(finding['lag_seconds']))} lag"
        )
        lines.append("")
        lines.append(f"**{subject}** · {connector} · {source}")
        lines.append("")
        lines.append(f"- checked_at: {finding['checked_at']}")
        lines.append(f"- stale_after: {finding['stale_after']} (exceeded: {finding['exceeds_stale_after']})")
        lines.append(f"- watermark_basis: {finding['watermark_basis']}")
        lines.append(f"- status_reason: {finding['status_reason']}")
        ev = finding.get("evidence_refs", [])
        lines.append("- evidence: " + (", ".join(f"`{e}`" for e in ev) if ev else "n/a"))
        lines.append("")
    lines.append(
        f"Packet JSON (model input): review_packet id `{packet['id']}`. "
        "Record a matching `staleness-review-output` keyed to this id to populate "
        "the full HYBRID packet."
    )
    lines.append("")
    return "\n".join(lines)


def write_packet_markdown(
    packet: JsonObject,
    output: JsonObject | None,
    *,
    out_dir: Path,
    reviewer_label: str = "recorded",
    filename_suffix: str = "",
) -> Path:
    """Write the dated packet markdown (YYYY-WW[suffix].md). Falls back to evidence-only
    when no model output is supplied.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"-{filename_suffix}" if filename_suffix else ""
    path = out_dir / f"{packet['review_week']}{suffix}.md"
    if output is None:
        text = render_evidence_only_markdown(packet)
    else:
        text = render_packet_markdown(packet, output, reviewer_label=reviewer_label)
    path.write_text(text + ("\n" if not text.endswith("\n") else ""), encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# Orchestrator
# --------------------------------------------------------------------------


@dataclass
class StalenessRunResult:
    packet: JsonObject
    output: JsonObject | None
    markdown_path: Path | None
    auto_demote_enabled: bool
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
            "auto_demote_enabled": self.auto_demote_enabled,
            "demote_proposals": len(self.output.get("demote_proposals", [])) if self.output else 0,
            "markdown_path": str(self.markdown_path) if self.markdown_path else None,
        }


def run_staleness_review(
    *,
    records: Iterable[JsonObject],
    as_of: datetime,
    reviewer: StalenessReviewer | None = None,
    scope: str = "all",
    auto_demote_enabled: bool = False,
    out_dir: Path | None = None,
    output_schema: JsonObject | None = None,
    packet_schema: JsonObject | None = None,
    governance_constraints: list[JsonObject] | None = None,
    reviewer_label: str = "recorded",
    filename_suffix: str = "",
) -> StalenessRunResult:
    """Run the full staleness loop: gather -> packet -> review -> render.

    If ``reviewer`` is omitted or has no judgment for the packet, an evidence-
    only packet is produced (no fabricated judgment). ``auto_demote_enabled``
    defaults False and is never turned on by this module.
    """
    findings = gather_findings(records, as_of=as_of)
    packet = build_review_packet(
        findings,
        as_of=as_of,
        scope=scope,
        auto_demote_enabled=auto_demote_enabled,
        schema=packet_schema,
        governance_constraints=governance_constraints,
    )

    output: JsonObject | None = None
    judgments_present = False
    if reviewer is not None:
        try:
            reviewed = reviewer.review(packet)
        except MissingStalenessJudgmentError:
            reviewed = None
        if reviewed is not None:
            gate = AutoDemoteGate(enabled=auto_demote_enabled)
            proposals = gate.build_proposals(reviewed)
            reviewed = dict(reviewed)
            reviewed["auto_demote_enabled"] = auto_demote_enabled
            reviewed["demote_proposals"] = proposals
            reviewed["review_packet_id"] = packet["id"]
            reviewed.setdefault("review_week", packet["review_week"])
            if output_schema is not None:
                errors = _validate_output_deep(reviewed, output_schema)
                if errors:
                    raise StalenessOutputValidationError(errors)
            output = reviewed
            judgments_present = True

    markdown_path: Path | None = None
    if out_dir is not None:
        markdown_path = write_packet_markdown(
            packet,
            output,
            out_dir=out_dir,
            reviewer_label=reviewer_label,
            filename_suffix=filename_suffix,
        )

    decisions_queued = len(output.get("entries", [])) if output else len(findings)
    return StalenessRunResult(
        packet=packet,
        output=output,
        markdown_path=markdown_path,
        auto_demote_enabled=auto_demote_enabled,
        judgments_present=judgments_present,
        decisions_queued=decisions_queued,
    )


def _validate_output_deep(output: JsonObject, schema: JsonObject) -> list[str]:
    """Validate the top-level contract, then each entry against its $defs subschema.

    The repo's ``validate_schema`` is a JSON-Schema subset that does not follow
    ``$ref``. Validating each entry against the ``$defs/entry`` subschema gives
    real per-entry contract enforcement (required/type/enum) without hand-rolled
    checks — this is schema constraint, not heuristic judgment.
    """
    errors = list(validate_schema(output, schema))
    entry_schema = schema.get("$defs", {}).get("entry")
    if isinstance(entry_schema, dict):
        for index, entry in enumerate(output.get("entries", [])):
            errors.extend(validate_schema(entry, entry_schema, f"$.entries[{index}]"))
    proposal_schema = schema.get("$defs", {}).get("demote_proposal")
    if isinstance(proposal_schema, dict):
        for index, proposal in enumerate(output.get("demote_proposals", [])):
            errors.extend(validate_schema(proposal, proposal_schema, f"$.demote_proposals[{index}]"))
    return errors


class StalenessOutputValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("staleness review output validation failed")
        self.errors = tuple(errors)


def load_staleness_schemas(project_root: Path) -> dict[str, JsonObject]:
    """Load the two staleness schemas by name (packet, output)."""
    schemas_dir = project_root / "schemas"
    return {
        "staleness_packet": load_json(schemas_dir / "staleness-review-packet.schema.json"),
        "staleness_output": load_json(schemas_dir / "staleness-review-output.schema.json"),
    }
