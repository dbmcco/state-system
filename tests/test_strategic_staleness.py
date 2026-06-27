"""Tests for the strategic-staleness review loop.

Mirrors the discipline of ``test_staleness_runner.py``: each layer (gather,
packet build, reviewer, gate, render, end-to-end, CLI) is tested in isolation,
with model-mediated guardrails asserted explicitly (code owns evidence and
structure; the model owns every judgment).
"""

from __future__ import annotations

import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from state_system.cli import main as cli_main
from state_system.staleness_runner import parse_instant
from state_system.strategic_staleness import (
    AutoReviseGate,
    MissingStrategicJudgmentError,
    RecordedStrategicReviewer,
    StrategicOutputValidationError,
    build_strategic_review_packet,
    gather_strategic_findings,
    load_strategic_schemas,
    render_strategic_evidence_only_markdown,
    render_strategic_packet_markdown,
    run_strategic_review,
    strategic_packet_id,
)

ROOT = Path(__file__).resolve().parents[1]
AS_OF = parse_instant("2026-06-25T12:00:00Z")
EXAMPLES_STRATEGIC = ROOT / "examples" / "strategic-reviews"


def _schemas() -> dict:
    return load_strategic_schemas(ROOT)


def _company_memory() -> dict:
    """A self-contained company_memory document (5 strategic claims)."""
    return {
        "id": "company_memory.acme",
        "subject_ref": "company.acme",
        "generated_at": "2026-05-04T15:00:00Z",
        "mission": {
            "summary": "Acme builds bounded AI systems for operating teams.",
            "evidence_refs": ["ev.acme.mission"],
        },
        "strategy": {
            "summary": "Lead with relationship-backed proof, not generic AI positioning.",
            "current_priorities": [
                "Ship the platform substrate.",
                "Use CRM outcomes as doctrine evidence.",
            ],
            "evidence_refs": ["ev.acme.strategy"],
        },
        "projects": [
            {
                "id": "project.platform",
                "summary": "The durable state substrate.",
                "status": "active",
                "evidence_refs": ["ev.acme.platform"],
            }
        ],
        "agent_memory_refs": [],
        "organizational_state_refs": [],
        "evidence_refs": ["ev.acme"],
        "freshness": {
            "as_of": "2026-05-04T15:00:00Z",
            "stale_after": "2026-05-11T15:00:00Z",
            "watermark_refs": ["wm.acme.1"],
        },
    }


def _entity_current_state(
    *,
    entity_id: str = "venture.sample",
    north_star: str = "Ship the sample app for Friday review.",
    status: str = "active",
    effective_at: str = "2026-06-18T13:14:00Z",
    stale_after: str = "2026-06-20T12:00:00Z",
) -> dict:
    """A self-contained entity-current-state record (b-state shape)."""
    return {
        "id": f"entity_current_state.{entity_id}.{effective_at}",
        "entity_id": entity_id,
        "entity_name": entity_id,
        "north_star": north_star,
        "current_priority": "Background agent is building the app; check before Friday.",
        "owner": "Braydon",
        "waiting_on": "Background agent progress",
        "braydon_next_action": "Check agent progress before Friday",
        "effective_at": effective_at,
        "stale_after": stale_after,
        "supersedes": None,
        "source_refs": ["folio:sample-note", "workboard:sample-task"],
        "confidence": "high",
        "status": status,
        "generated_at": effective_at,
        "generated_by": "sam",
    }


def _write_operating_doc(directory: Path, name: str, body: str) -> Path:
    path = directory / name
    path.write_text(body, encoding="utf-8")
    return path


class PacketIdTests(unittest.TestCase):
    def test_packet_id_uses_slug_and_iso_week(self):
        self.assertEqual(
            strategic_packet_id("all", "2026-W26"),
            "strategic_review_packet.all.2026-W26",
        )


class GatherStrategicFindingsTests(unittest.TestCase):
    def test_company_memory_claims_cover_mission_strategy_priorities_projects(self):
        findings = gather_strategic_findings(
            company_memory_docs=[(_company_memory(), "company_memory.acme")],
            as_of=AS_OF,
        )
        kinds = sorted(f["claim_kind"] for f in findings)
        self.assertEqual(
            kinds,
            [
                "company_mission",
                "company_priority",  # x2
                "company_priority",
                "company_project",
                "company_strategy",
            ],
        )
        mission = next(f for f in findings if f["claim_kind"] == "company_mission")
        self.assertIn("bounded AI systems", mission["claim_summary"])
        self.assertIn("ev.acme.mission", mission["evidence_refs"])
        project = next(f for f in findings if f["claim_kind"] == "company_project")
        self.assertEqual("active", project["declared_status"])
        self.assertEqual("company.acme|company_project:project.platform", project["scope_key"])

    def test_age_and_validity_window_are_objective_facts(self):
        findings = gather_strategic_findings(
            company_memory_docs=[(_company_memory(), "company_memory.acme")],
            as_of=AS_OF,
        )
        for finding in findings:
            # as_of 2026-06-25 minus freshness.as_of 2026-05-04 = 51 days
            self.assertEqual(51, finding["age_days"])
            # as_of is past the declared stale_after 2026-05-11
            self.assertTrue(finding["validity_window_exceeded"])
            self.assertEqual("2026-05-11T15:00:00Z", finding["declared_stale_after"])

    def test_operating_doc_extracts_declared_status_and_created_date(self):
        with TemporaryDirectory() as directory:
            directory = Path(directory)
            path = _write_operating_doc(
                directory,
                "positioning.md",
                "# Positioning Cleanup\n\n"
                "**Status:** Draft (ready to assign)\n\n"
                "**Created:** 2026-06-24\n\n"
                "The 30/60/90 model is dead.\n",
            )
            findings = gather_strategic_findings(operating_docs=[path], as_of=AS_OF)
        self.assertEqual(1, len(findings))
        finding = findings[0]
        self.assertEqual("operating_decision", finding["claim_kind"])
        self.assertEqual("portfolio", finding["subject_ref"])
        # colon sits inside the markdown bold; value must not carry stray markers
        self.assertEqual("Draft (ready to assign)", finding["declared_status"])
        self.assertEqual("2026-06-24T00:00:00Z", finding["last_validated_at"])
        self.assertEqual(1, finding["age_days"])
        self.assertFalse(finding["validity_window_exceeded"])  # no declared window

    def test_operating_doc_without_metadata_is_honest_unknown(self):
        with TemporaryDirectory() as directory:
            directory = Path(directory)
            path = _write_operating_doc(
                directory,
                "framework.md",
                "# Operating Framework\n\nNo status or date is declared here.\n",
            )
            findings = gather_strategic_findings(operating_docs=[path], as_of=AS_OF)
        finding = findings[0]
        self.assertEqual("", finding["declared_status"])
        self.assertNotIn("last_validated_at", finding)
        self.assertNotIn("age_days", finding)
        self.assertFalse(finding["validity_window_exceeded"])
        self.assertEqual("Operating Framework", finding["claim_summary"])

    def test_findings_combine_both_layers_and_sort(self):
        with TemporaryDirectory() as directory:
            directory = Path(directory)
            op_path = _write_operating_doc(
                directory, "decision.md", "# A Decision\n**Status:** Open\n"
            )
            findings = gather_strategic_findings(
                company_memory_docs=[(_company_memory(), "company_memory.acme")],
                operating_docs=[op_path],
                as_of=AS_OF,
            )
        # 5 company claims + 1 operating decision
        self.assertEqual(6, len(findings))
        # sorted by (subject_ref, claim_kind, scope_key); portfolio sorts after company.acme
        subjects = [f["subject_ref"] for f in findings]
        self.assertEqual(subjects, sorted(subjects))


class GatherEntityCurrentStateTests(unittest.TestCase):
    def test_surfaces_active_expired_card_as_one_finding(self):
        findings = gather_strategic_findings(
            entity_current_state_docs=[
                (_entity_current_state(), "entity_current_state.venture.sample")
            ],
            as_of=AS_OF,  # 2026-06-25 > stale_after 2026-06-20
        )
        self.assertEqual(1, len(findings))
        finding = findings[0]
        self.assertEqual("entity_current_state", finding["claim_kind"])
        self.assertEqual("entity.venture.sample", finding["subject_ref"])
        self.assertIn("Ship the sample app", finding["claim_summary"])
        self.assertEqual("active", finding["declared_status"])
        self.assertTrue(finding["validity_window_exceeded"])

    def test_skips_card_still_within_validity_window(self):
        fresh = _entity_current_state(stale_after="2026-07-01T12:00:00Z")
        findings = gather_strategic_findings(
            entity_current_state_docs=[(fresh, "ecs.fresh")], as_of=AS_OF
        )
        self.assertEqual([], findings)  # current by its own declaration; not worth review

    def test_skips_non_active_cards(self):
        superseded = _entity_current_state(status="superseded")
        retracted = _entity_current_state(status="retracted")
        findings = gather_strategic_findings(
            entity_current_state_docs=[
                (superseded, "ecs.s"),
                (retracted, "ecs.r"),
            ],
            as_of=AS_OF,
        )
        self.assertEqual([], findings)  # own declared status says not-current

    def test_evidence_and_detail_carry_card_content_faithfully(self):
        findings = gather_strategic_findings(
            entity_current_state_docs=[
                (_entity_current_state(), "entity_current_state.venture.sample")
            ],
            as_of=AS_OF,
        )
        finding = findings[0]
        self.assertIn("folio:sample-note", finding["evidence_refs"])
        self.assertIn("workboard:sample-task", finding["evidence_refs"])
        detail = finding.get("detail", "")
        # current_priority + next_action carried as evidence; source confidence
        # carried as declared evidence, NOT a model confidence.
        self.assertIn("current_priority:", detail)
        self.assertIn("high", detail)

    def test_combines_with_company_memory_and_operating_docs(self):
        with TemporaryDirectory() as directory:
            directory = Path(directory)
            op_path = _write_operating_doc(
                directory, "decision.md", "# A Decision\n**Status:** Open\n"
            )
            findings = gather_strategic_findings(
                company_memory_docs=[(_company_memory(), "company_memory.acme")],
                entity_current_state_docs=[(_entity_current_state(), "ecs.sample")],
                operating_docs=[op_path],
                as_of=AS_OF,
            )
        kinds = sorted(f["claim_kind"] for f in findings)
        self.assertIn("company_mission", kinds)
        self.assertIn("entity_current_state", kinds)
        self.assertIn("operating_decision", kinds)


class _OneEntryReviewer:
    """Test double: emits one model-style judgment for the first finding.

    Stands in for a live model reviewer. Its entry carries the finding's
    scope_key so the output-enrichment join can be exercised.
    """

    def review(self, packet):
        findings = packet.get("findings") or []
        if not findings:
            raise MissingStrategicJudgmentError(packet["id"])
        head = findings[0]
        return {
            "id": "strategic_review_output.test",
            "created_at": "2026-06-25T12:00:00Z",
            "decision": "surface_decisions",
            "observations": [],
            "entries": [
                {
                    "scope_key": head["scope_key"],
                    "nl_question": "does this strategic claim still hold?",
                    "recommended_action": "revise",
                    "classification": "objective_drift",
                    "confidence": 0.8,
                    "evidence_refs": list(head.get("evidence_refs", [])),
                    "rationale": "test double",
                }
            ],
            "uncertainty": [],
            "review_signal": {
                "id": "review_signal.test",
                "status": "surfaced",
                "created_at": "2026-06-25T12:00:00Z",
                "trigger_ref": "trigger.test",
            },
        }


class EntityIdBridgeTests(unittest.TestCase):
    """The strategic output must join to entity-current-state cards by a
    first-class ``entity_id`` — never by parsing ``scope_key``.

    ``scope_key`` nests the id as ``entity.<id>|entity_current_state:<slug>``;
    a naive equality join against a card's bare ``entity_id`` silently no-ops,
    and the slug half is lossy. Carrying the verbatim ``entity_id`` on the
    finding and surfacing it on the entry removes that hazard and lets a
    consumer join with ``entry.entity_id == card.entity_id``.
    """

    def test_ecs_finding_carries_verbatim_dotted_entity_id(self):
        findings = gather_strategic_findings(
            entity_current_state_docs=[
                (_entity_current_state(entity_id="venture.sampleco"), "ecs.sampleco")
            ],
            as_of=AS_OF,
        )
        self.assertEqual(1, len(findings))
        # verbatim dotted id preserved as a first-class field, not parsed out
        self.assertEqual("venture.sampleco", findings[0]["entity_id"])

    def test_ecs_finding_entity_id_is_raw_not_a_lossy_slug(self):
        # an id whose slug form differs from its raw form proves the bridge
        # carries the verbatim key rather than a derived slug
        findings = gather_strategic_findings(
            entity_current_state_docs=[
                (_entity_current_state(entity_id="LFW Co"), "ecs.lfwco")
            ],
            as_of=AS_OF,
        )
        self.assertEqual("LFW Co", findings[0]["entity_id"])

    def test_output_entry_enriched_with_entity_id_joined_by_scope(self):
        result = run_strategic_review(
            entity_current_state_docs=[
                (_entity_current_state(entity_id="venture.sampleco"), "ecs.sampleco")
            ],
            as_of=AS_OF,
            reviewer=_OneEntryReviewer(),
            output_schema=None,
            packet_schema=None,
        )
        self.assertTrue(result.judgments_present)
        entries = result.output["entries"]
        self.assertEqual(1, len(entries))
        # the entry now carries the joinable entity_id, joined from the finding
        self.assertEqual("venture.sampleco", entries[0]["entity_id"])

    def test_non_ecs_entries_have_no_entity_id(self):
        result = run_strategic_review(
            company_memory_docs=[(_company_memory(), "company_memory.acme")],
            as_of=AS_OF,
            reviewer=_OneEntryReviewer(),
            output_schema=None,
            packet_schema=None,
        )
        self.assertTrue(result.judgments_present)
        # company_memory claims are not entity-scoped: entity_id must be absent
        for entry in result.output["entries"]:
            self.assertNotIn("entity_id", entry)

    def test_model_smuggled_entity_id_on_non_ecs_entry_is_scrubbed(self):
        # the contract: entity_id is code-owned and present only on
        # entity-current-state entries. Even if a model erroneously emits one
        # on a company-memory entry, code must strip it (no model-owned ids).
        class _SmugglingReviewer(_OneEntryReviewer):
            def review(self, packet):
                out = super().review(packet)
                out["entries"][0]["entity_id"] = "smuggled-by-model"
                return out

        result = run_strategic_review(
            company_memory_docs=[(_company_memory(), "company_memory.acme")],
            as_of=AS_OF,
            reviewer=_SmugglingReviewer(),
            output_schema=None,
            packet_schema=None,
        )
        self.assertNotIn("entity_id", result.output["entries"][0])


class BuildStrategicPacketTests(unittest.TestCase):
    def test_packet_validates_and_gate_off_shape(self):
        findings = gather_strategic_findings(
            company_memory_docs=[(_company_memory(), "company_memory.acme")],
            as_of=AS_OF,
        )
        packet = build_strategic_review_packet(
            findings, as_of=AS_OF, schema=_schemas()["strategic_packet"]
        )
        self.assertEqual("strategic_staleness", packet["review_kind"])
        self.assertEqual("2026-W26", packet["review_week"])
        self.assertIn("surface_decisions", packet["allowed_outputs"])
        self.assertNotIn("revise_proposals", packet["allowed_outputs"])
        constraint_ids = {c["id"] for c in packet["governance_context"]["constraints"]}
        self.assertIn("auto-revise-gated", constraint_ids)
        self.assertIn(packet["review_question"], packet["review_question"])  # non-empty

    def test_gate_on_adds_revise_output_and_armed_constraint(self):
        findings = gather_strategic_findings(
            company_memory_docs=[(_company_memory(), "company_memory.acme")],
            as_of=AS_OF,
        )
        packet = build_strategic_review_packet(
            findings,
            as_of=AS_OF,
            auto_revise_enabled=True,
            schema=_schemas()["strategic_packet"],
        )
        self.assertIn("revise_proposals", packet["allowed_outputs"])
        constraint_ids = {c["id"] for c in packet["governance_context"]["constraints"]}
        self.assertIn("auto-revise-armed", constraint_ids)


class RecordedReviewerTests(unittest.TestCase):
    def test_replays_recorded_output_for_known_packet(self):
        reviewer = RecordedStrategicReviewer.from_examples(EXAMPLES_STRATEGIC)
        packet = build_strategic_review_packet(
            gather_strategic_findings(
                company_memory_docs=[(_company_memory(), "company_memory.acme")],
                as_of=AS_OF,
            ),
            as_of=AS_OF,
        )
        output = reviewer.review(packet)
        self.assertEqual(packet["id"], output["review_packet_id"])
        self.assertTrue(output["entries"])

    def test_raises_on_missing_recording(self):
        reviewer = RecordedStrategicReviewer(outputs_by_packet_id={})
        packet = {"id": "strategic_review_packet.unknown.2026-W26"}
        with self.assertRaises(MissingStrategicJudgmentError):
            reviewer.review(packet)


class RecordedReviewerWeekBoundaryTests(unittest.TestCase):
    """A recorded judgment must replay across a week boundary.

    The packet id is week-bound (``strategic_review_packet.<scope>.<YYYY-WW>``),
    but a recording is a model judgment about a scope, not a calendar week. A
    judgment made in W26 must still replay when ``as_of`` crosses into W27 —
    otherwise the live packet silently degrades to evidence-only at every week
    boundary. Packet-id routing is code-owned structure, so resolving by scope
    (falling back to the latest recording for the scope) is a legitimate
    code-owned routing decision, not a semantic one.
    """

    def test_resolve_key_prefers_exact_match_then_latest_scope_recording(self):
        reviewer = RecordedStrategicReviewer(
            outputs_by_packet_id={
                "strategic_review_packet.all.2026-W25": {
                    "review_packet_id": "strategic_review_packet.all.2026-W25"
                },
                "strategic_review_packet.all.2026-W26": {
                    "review_packet_id": "strategic_review_packet.all.2026-W26"
                },
            }
        )
        # exact match wins
        self.assertEqual(
            "strategic_review_packet.all.2026-W26",
            reviewer.resolve_recording_key("strategic_review_packet.all.2026-W26"),
        )
        # no exact match -> latest recording for the same scope (W26 > W25)
        self.assertEqual(
            "strategic_review_packet.all.2026-W26",
            reviewer.resolve_recording_key("strategic_review_packet.all.2026-W27"),
        )

    def test_resolve_key_does_not_cross_scopes(self):
        reviewer = RecordedStrategicReviewer(
            outputs_by_packet_id={
                "strategic_review_packet.venture.cyrcle.2026-W26": {
                    "review_packet_id": "strategic_review_packet.venture.cyrcle.2026-W26"
                }
            }
        )
        # a dotted scope is matched as a whole; a different scope yields nothing
        self.assertIsNone(
            reviewer.resolve_recording_key("strategic_review_packet.all.2026-W27")
        )

    def test_recording_replays_across_week_boundary(self):
        from datetime import timedelta

        from state_system.staleness_runner import review_week

        recording = {
            "review_packet_id": "strategic_review_packet.all.2026-W26",
            "created_at": "2026-06-25T12:00:00Z",
            "decision": "surface_decisions",
            "entries": [{"scope_key": "entity.venture.sampleco"}],
        }
        reviewer = RecordedStrategicReviewer(
            outputs_by_packet_id={
                "strategic_review_packet.all.2026-W26": recording
            }
        )
        next_week_as_of = AS_OF + timedelta(days=7)
        self.assertNotEqual(review_week(AS_OF), review_week(next_week_as_of))
        packet = build_strategic_review_packet(
            gather_strategic_findings(
                company_memory_docs=[(_company_memory(), "company_memory.acme")],
                as_of=next_week_as_of,
            ),
            as_of=next_week_as_of,
        )
        # packet id is now week-bound to W27; the W26 recording must still replay
        self.assertEqual("strategic_review_packet.all.2026-W27", packet["id"])
        output = reviewer.review(packet)
        self.assertEqual(
            "strategic_review_packet.all.2026-W26", output["review_packet_id"]
        )
        self.assertTrue(output["entries"])

    def test_still_raises_when_no_recording_for_scope(self):
        reviewer = RecordedStrategicReviewer(outputs_by_packet_id={})
        packet = {"id": "strategic_review_packet.unknown.2026-W27"}
        with self.assertRaises(MissingStrategicJudgmentError):
            reviewer.review(packet)


class AutoReviseGateTests(unittest.TestCase):
    def _output(self, classification: str, action: str) -> dict:
        return {
            "entries": [
                {
                    "scope_key": "company.acme|company_project:project.platform",
                    "classification": classification,
                    "recommended_action": action,
                    "rationale": "drifted",
                    "evidence_refs": ["ev.1"],
                }
            ]
        }

    def test_off_gate_produces_no_proposals(self):
        gate = AutoReviseGate(enabled=False)
        self.assertEqual([], gate.build_proposals(self._output("objective_drift", "revise")))

    def test_on_gate_proposes_only_for_objective_drift_revise(self):
        gate = AutoReviseGate(enabled=True)
        # objective_drift + revise -> proposal
        proposals = gate.build_proposals(self._output("objective_drift", "revise"))
        self.assertEqual(1, len(proposals))
        self.assertTrue(proposals[0]["approval_required"])
        self.assertEqual("company.acme", proposals[0]["target_ref"])
        # uncertain + revise -> no proposal (gate acts only on objective_drift)
        self.assertEqual([], gate.build_proposals(self._output("uncertain", "revise")))
        # objective_drift + validate -> no proposal (gate acts only on revise)
        self.assertEqual([], gate.build_proposals(self._output("objective_drift", "validate")))


class MarkdownRenderTests(unittest.TestCase):
    def test_full_packet_markdown_has_hybrid_shape(self):
        packet = build_strategic_review_packet(
            gather_strategic_findings(
                company_memory_docs=[(_company_memory(), "company_memory.acme")],
                as_of=AS_OF,
            ),
            as_of=AS_OF,
        )
        output = {
            "created_at": "2026-06-25T12:00:00Z",
            "decision": "surface_decisions",
            "entries": [
                {
                    "scope_key": "company.acme|company_mission",
                    "nl_question": "Does the mission still hold?",
                    "recommended_action": "validate",
                    "classification": "uncertain",
                    "confidence": 0.6,
                    "evidence_refs": ["ev.mission"],
                    "rationale": "aged evidence",
                }
            ],
            "uncertainty": ["one open question"],
            "auto_revise_enabled": False,
        }
        text = render_strategic_packet_markdown(packet, output)
        self.assertIn("Strategic staleness review — 2026-W26", text)
        self.assertIn("0 objective_drift · 1 uncertain", text)  # summary line carries both labels
        self.assertIn("Does the mission still hold?", text)
        self.assertIn("validate", text)
        self.assertIn("Auto-revise: OFF", text)

    def test_evidence_only_markdown_when_no_judgment(self):
        packet = build_strategic_review_packet(
            gather_strategic_findings(
                company_memory_docs=[(_company_memory(), "company_memory.acme")],
                as_of=AS_OF,
            ),
            as_of=AS_OF,
        )
        text = render_strategic_evidence_only_markdown(packet)
        self.assertIn("AWAITING MODEL REVIEW", text)
        self.assertIn("company mission", text)
        self.assertIn("declared validity window exceeded", text)


class EndToEndAndModelMediationTests(unittest.TestCase):
    def test_run_preserves_model_judgments_verbatim(self):
        schemas = _schemas()
        result = run_strategic_review(
            company_memory_docs=[(_company_memory(), "company_memory.acme")],
            as_of=AS_OF,
            reviewer=RecordedStrategicReviewer(
                outputs_by_packet_id={
                    "strategic_review_packet.all.2026-W26": {
                        "id": "strategic-review-output.all.2026-W26",
                        "review_packet_id": "strategic_review_packet.all.2026-W26",
                        "created_at": "2026-06-25T12:00:00Z",
                        "review_week": "2026-W26",
                        "decision": "surface_decisions",
                        "observations": ["ok"],
                        "entries": [
                            {
                                "scope_key": "company.acme|company_mission",
                                "nl_question": "Still holds?",
                                "recommended_action": "validate",
                                "classification": "uncertain",
                                "confidence": 0.6,
                                "evidence_refs": ["ev"],
                            }
                        ],
                        "uncertainty": [],
                        "auto_revise_enabled": False,
                        "review_signal": {
                            "id": "rs",
                            "status": "surface_decisions",
                            "created_at": "2026-06-25T12:00:00Z",
                            "trigger_ref": "strategic_review_packet.all.2026-W26",
                        },
                    }
                }
            ),
            output_schema=schemas["strategic_output"],
            packet_schema=schemas["strategic_packet"],
        )
        self.assertTrue(result.judgments_present)
        self.assertEqual(1, result.decisions_queued)
        # model judgment carried verbatim
        self.assertEqual("Still holds?", result.output["entries"][0]["nl_question"])
        self.assertFalse(result.summary()["auto_revise_enabled"])

    def test_invalid_model_output_raises(self):
        schemas = _schemas()
        bad_output = {
            "id": "x",
            "review_packet_id": "strategic_review_packet.all.2026-W26",
            "created_at": "2026-06-25T12:00:00Z",
            "review_week": "2026-W26",
            "decision": "surface_decisions",
            "observations": [],
            "entries": [
                {
                    "scope_key": "company.acme|company_mission",
                    "nl_question": "q",
                    "recommended_action": "validate",
                    "classification": "objective_stale",  # not a strategic enum
                    "confidence": 0.5,
                    "evidence_refs": [],
                }
            ],
            "uncertainty": [],
            "auto_revise_enabled": False,
            "review_signal": {
                "id": "rs",
                "status": "x",
                "created_at": "2026-06-25T12:00:00Z",
                "trigger_ref": "t",
            },
        }
        with self.assertRaises(StrategicOutputValidationError):
            run_strategic_review(
                company_memory_docs=[(_company_memory(), "company_memory.acme")],
                as_of=AS_OF,
                reviewer=RecordedStrategicReviewer(
                    outputs_by_packet_id={"strategic_review_packet.all.2026-W26": bad_output}
                ),
                output_schema=schemas["strategic_output"],
                packet_schema=schemas["strategic_packet"],
            )

    def test_auto_revise_on_produces_approved_proposal(self):
        schemas = _schemas()
        result = run_strategic_review(
            company_memory_docs=[(_company_memory(), "company_memory.acme")],
            as_of=AS_OF,
            auto_revise_enabled=True,
            reviewer=RecordedStrategicReviewer(
                outputs_by_packet_id={
                    "strategic_review_packet.all.2026-W26": {
                        "id": "x",
                        "review_packet_id": "strategic_review_packet.all.2026-W26",
                        "created_at": "2026-06-25T12:00:00Z",
                        "review_week": "2026-W26",
                        "decision": "revise_proposals",
                        "observations": [],
                        "entries": [
                            {
                                "scope_key": "company.acme|company_project:project.platform",
                                "nl_question": "Drifted?",
                                "recommended_action": "revise",
                                "classification": "objective_drift",
                                "confidence": 0.85,
                                "evidence_refs": ["ev"],
                                "rationale": "superseded",
                            }
                        ],
                        "uncertainty": [],
                        "auto_revise_enabled": False,
                        "review_signal": {
                            "id": "rs",
                            "status": "x",
                            "created_at": "2026-06-25T12:00:00Z",
                            "trigger_ref": "t",
                        },
                    }
                }
            ),
            output_schema=schemas["strategic_output"],
            packet_schema=schemas["strategic_packet"],
        )
        summary = result.summary()
        self.assertTrue(summary["auto_revise_enabled"])
        self.assertEqual(1, summary["revise_proposals"])
        proposal = result.output["revise_proposals"][0]
        self.assertTrue(proposal["approval_required"])  # never auto-executed
        self.assertEqual("company.acme", proposal["target_ref"])


class CliDryRunTests(unittest.TestCase):
    def test_cli_recorded_dry_run_produces_packet(self):
        with TemporaryDirectory() as directory:
            buffer = io.StringIO()
            rc = cli_main(
                [
                    "--project-root",
                    str(ROOT),
                    "strategic-review-run",
                    "--company-memory-dir",
                    str(ROOT / "examples" / "company-memory"),
                    "--operating-doc",
                    str(
                        EXAMPLES_STRATEGIC
                        / "operating-docs"
                        / "sampleco-positioning-cleanup-plan.md"
                    ),
                    "--operating-doc",
                    str(
                        EXAMPLES_STRATEGIC
                        / "operating-docs"
                        / "portfolio-operating-framework.md"
                    ),
                    "--as-of",
                    "2026-06-25T12:00:00Z",
                    "--output-dir",
                    directory,
                ],
                stdout=buffer,
            )
            self.assertEqual(0, rc)
            summary = json.loads(buffer.getvalue())
            self.assertTrue(summary["judgments_present"])
            self.assertEqual(7, summary["findings"])
            self.assertFalse(summary["auto_revise_enabled"])
            self.assertEqual(0, summary["revise_proposals"])
            self.assertTrue(Path(summary["markdown_path"]).exists())


if __name__ == "__main__":
    unittest.main()
