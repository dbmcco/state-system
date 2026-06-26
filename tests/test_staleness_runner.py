"""Tests for the staleness review loop.

These tests pin the model-mediated contract: code owns evidence, structure,
gates, and rendering; the model (or a recorded fixture standing in for one)
owns every per-finding judgment. No test may rely on code classifying staleness.
"""

from copy import deepcopy
from datetime import datetime, timezone
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system.cli import main as cli_main
from state_system.contracts import load_json, validate_schema
from state_system.staleness_runner import (
    AutoDemoteGate,
    MissingStalenessJudgmentError,
    RecordedStalenessReviewer,
    StalenessOutputValidationError,
    build_review_packet,
    gather_findings,
    gather_freshness_records,
    load_staleness_schemas,
    parse_instant,
    review_week,
    run_staleness_review,
)


ROOT = Path(__file__).resolve().parents[1]
AS_OF = parse_instant("2026-06-25T12:00:00Z")
FRESHNESS_DIR = ROOT / "examples" / "state-reviews" / "freshness"

LFW_LINEAR = "state_instance.lfw|connector.lfw.linear|linear:lfw-engineering"
SYNTH_CRM = "state_instance.synthyra|connector.synth.crm|crm:synth-contacts"
LFW_STRIPE_FRESH = "state_instance.lfw|connector.lfw.stripe|stripe:lfw-billing"
NAVICYTE_EMAIL_FRESH = "state_instance.navicyte|connector.navicyte.email|email:navicyte-mike"


def _seed_records() -> list[dict]:
    return gather_freshness_records(freshness_dir=FRESHNESS_DIR)


def _schemas() -> dict:
    return load_staleness_schemas(ROOT)


class ReviewWeekTests(unittest.TestCase):
    def test_iso_week_for_known_thursday(self):
        self.assertEqual("2026-W26", review_week(parse_instant("2026-06-25T12:00:00Z")))


class GatherFindingsTests(unittest.TestCase):
    def test_surfaces_non_fresh_and_aged_and_skips_fresh(self):
        findings = gather_findings(_seed_records(), as_of=AS_OF)
        scopes = {finding["scope_key"] for finding in findings}
        self.assertEqual(5, len(findings))
        self.assertIn(LFW_LINEAR, scopes)
        self.assertIn(SYNTH_CRM, scopes)
        # fresh sources with future stale-after are not surfaced
        self.assertNotIn(LFW_STRIPE_FRESH, scopes)
        self.assertNotIn(NAVICYTE_EMAIL_FRESH, scopes)

    def test_lag_and_exceeds_stale_after_are_objective_facts(self):
        findings = {
            finding["scope_key"]: finding
            for finding in gather_findings(_seed_records(), as_of=AS_OF)
        }
        lfw_linear = findings[LFW_LINEAR]
        # 2026-06-25T12:00 minus 2026-05-20T09:00 == 3,121,200 s
        self.assertEqual(3121200, lfw_linear["lag_seconds"])
        self.assertTrue(lfw_linear["exceeds_stale_after"])

    def test_fresh_record_whose_window_expired_is_surfaced(self):
        record = {
            "id": "instance_source_freshness.x.c.s.2026-06-20",
            "scope_key": "state_instance.x|c|s",
            "instance_ref": "state_instance.x",
            "connector_ref": "c",
            "source_ref": "s",
            "status": "fresh",
            "checked_at": "2026-06-20T00:00:00Z",
            "stale_after": "2026-06-01T00:00:00Z",
            "watermark_basis": "source_event",
            "evidence_refs": [],
        }
        findings = gather_findings([record], as_of=AS_OF)
        self.assertEqual(1, len(findings))
        self.assertTrue(findings[0]["exceeds_stale_after"])

    def test_company_level_records_are_supported(self):
        record = {
            "id": "source_freshness.co.c.s.2026-06-01",
            "scope_key": "company.co|c|s",
            "company_ref": "company.co",
            "connector_ref": "c",
            "source_ref": "s",
            "status": "stale",
            "checked_at": "2026-06-01T00:00:00Z",
            "stale_after": "2026-06-10T00:00:00Z",
            "watermark_basis": "source_event",
            "evidence_refs": [],
        }
        findings = gather_findings([record], as_of=AS_OF)
        self.assertEqual(1, len(findings))
        self.assertEqual("company", findings[0]["subject_kind"])
        self.assertEqual("company.co", findings[0]["subject_ref"])


class BuildReviewPacketTests(unittest.TestCase):
    def test_packet_validates_and_gate_off_shape(self):
        schemas = _schemas()
        findings = gather_findings(_seed_records(), as_of=AS_OF)
        packet = build_review_packet(findings, as_of=AS_OF, schema=schemas["staleness_packet"])
        self.assertEqual([], validate_schema(packet, schemas["staleness_packet"]))
        self.assertEqual("staleness_review_packet.all.2026-W26", packet["id"])
        self.assertNotIn("demote_proposals", packet["allowed_outputs"])
        constraint_ids = {c["id"] for c in packet["governance_context"]["constraints"]}
        self.assertIn("auto-demote-gated", constraint_ids)
        self.assertIn("model-mediated-discipline", constraint_ids)

    def test_gate_on_adds_demote_output_and_armed_constraint(self):
        schemas = _schemas()
        findings = gather_findings(_seed_records(), as_of=AS_OF)
        packet = build_review_packet(
            findings,
            as_of=AS_OF,
            auto_demote_enabled=True,
            schema=schemas["staleness_packet"],
        )
        self.assertIn("demote_proposals", packet["allowed_outputs"])
        constraint_ids = {c["id"] for c in packet["governance_context"]["constraints"]}
        self.assertIn("auto-demote-armed", constraint_ids)


class RecordedReviewerTests(unittest.TestCase):
    def test_replays_recorded_output_for_known_packet(self):
        reviewer = RecordedStalenessReviewer.from_examples(
            ROOT / "examples" / "state-reviews"
        )
        packet = build_review_packet(
            gather_findings(_seed_records(), as_of=AS_OF), as_of=AS_OF
        )
        output = reviewer.review(packet)
        self.assertEqual(packet["id"], output["review_packet_id"])
        self.assertEqual(5, len(output["entries"]))
        entry_scopes = {entry["scope_key"] for entry in output["entries"]}
        self.assertEqual(
            {finding["scope_key"] for finding in gather_findings(_seed_records(), as_of=AS_OF)},
            entry_scopes,
        )

    def test_raises_on_missing_recording(self):
        reviewer = RecordedStalenessReviewer({})
        with self.assertRaises(MissingStalenessJudgmentError):
            reviewer.review({"id": "staleness_review_packet.unknown.2026-W26"})


class AutoDemoteGateTests(unittest.TestCase):
    def test_off_gate_produces_no_proposals(self):
        gate = AutoDemoteGate(enabled=False)
        output = {
            "entries": [
                {
                    "classification": "objective_stale",
                    "recommended_action": "demote",
                    "scope_key": "a|b|c",
                    "evidence_refs": [],
                }
            ]
        }
        self.assertEqual([], gate.build_proposals(output))

    def test_on_gate_proposes_only_for_objective_stale_demote(self):
        gate = AutoDemoteGate(enabled=True)
        output = {
            "entries": [
                {
                    "classification": "objective_stale",
                    "recommended_action": "demote",
                    "scope_key": "s|c|src",
                    "evidence_refs": ["e1"],
                    "rationale": "r",
                },
                {
                    "classification": "objective_stale",
                    "recommended_action": "refresh",
                    "scope_key": "s2|c2|src2",
                    "evidence_refs": [],
                },
                {
                    "classification": "uncertain",
                    "recommended_action": "demote",
                    "scope_key": "s3|c3|src3",
                    "evidence_refs": [],
                },
            ]
        }
        proposals = gate.build_proposals(output)
        self.assertEqual(1, len(proposals))
        self.assertEqual("s", proposals[0]["target_ref"])
        self.assertTrue(proposals[0]["approval_required"])
        self.assertEqual(["e1"], proposals[0]["evidence_refs"])


class MarkdownRenderTests(unittest.TestCase):
    def _run(self, **overrides):
        schemas = _schemas()
        kwargs = dict(
            records=_seed_records(),
            as_of=AS_OF,
            reviewer=RecordedStalenessReviewer.from_examples(
                ROOT / "examples" / "state-reviews"
            ),
            output_schema=schemas["staleness_output"],
            packet_schema=schemas["staleness_packet"],
        )
        with TemporaryDirectory() as directory:
            kwargs["out_dir"] = Path(directory)
            kwargs.update(overrides)
            result = run_staleness_review(**kwargs)
            markdown = Path(result.markdown_path).read_text()
        return result, markdown

    def test_full_packet_markdown_has_hybrid_shape(self):
        result, markdown = self._run()
        self.assertEqual("2026-W26.md", Path(result.markdown_path).name)
        for needle in (
            "State staleness review — 2026-W26",
            "decisions queued",
            "objective_stale",
            "uncertain",
            "recommended action:",
            "confidence",
            "evidence:",
            "Auto-demote: OFF",
        ):
            self.assertIn(needle, markdown)
        self.assertIn("Linear engineering feed", markdown)

    def test_evidence_only_markdown_when_no_judgment(self):
        schemas = _schemas()
        with TemporaryDirectory() as directory:
            result = run_staleness_review(
                records=_seed_records(),
                as_of=AS_OF,
                reviewer=RecordedStalenessReviewer({}),
                scope="lfw",
                out_dir=Path(directory),
                packet_schema=schemas["staleness_packet"],
            )
            markdown = Path(result.markdown_path).read_text()
        self.assertFalse(result.judgments_present)
        self.assertEqual("awaiting_review", result.summary()["decision"])
        self.assertIn("AWAITING MODEL REVIEW", markdown)
        self.assertIn("evidence", markdown)


class EndToEndAndModelMediationTests(unittest.TestCase):
    def _fixed_reviewer(self, packet, classification, action, confidence):
        output = {
            "id": "staleness_review_output.fixed",
            "review_packet_id": packet["id"],
            "created_at": "2026-06-25T12:00:00Z",
            "review_week": "2026-W26",
            "decision": "surface_decisions",
            "observations": [],
            "entries": [
                {
                    "scope_key": finding["scope_key"],
                    "nl_question": "Q?",
                    "recommended_action": action,
                    "classification": classification,
                    "confidence": confidence,
                    "evidence_refs": finding["evidence_refs"],
                }
                for finding in packet["findings"]
            ],
            "uncertainty": [],
            "auto_demote_enabled": False,
            "review_signal": {
                "id": "review_signal.fixed",
                "status": "surface_decisions",
                "created_at": "2026-06-25T12:00:00Z",
                "trigger_ref": packet["id"],
            },
        }

        class _Fixed:
            def review(self, _packet):
                return deepcopy(output)

        return _Fixed()

    def test_run_preserves_model_judgments_verbatim(self):
        # Code must not override, reclassify, or rewrite model judgments.
        schemas = _schemas()
        packet = build_review_packet(
            gather_findings(_seed_records(), as_of=AS_OF),
            as_of=AS_OF,
            schema=schemas["staleness_packet"],
        )
        reviewer = self._fixed_reviewer(packet, "uncertain", "investigate", 0.42)
        result = run_staleness_review(
            records=_seed_records(),
            as_of=AS_OF,
            reviewer=reviewer,
            output_schema=schemas["staleness_output"],
            packet_schema=schemas["staleness_packet"],
        )
        for entry in result.output["entries"]:
            self.assertEqual("uncertain", entry["classification"])
            self.assertEqual("investigate", entry["recommended_action"])
            self.assertEqual(0.42, entry["confidence"])
        self.assertEqual(0, len(result.output["demote_proposals"]))

    def test_invalid_model_output_raises(self):
        schemas = _schemas()
        packet = build_review_packet(
            gather_findings(_seed_records(), as_of=AS_OF),
            as_of=AS_OF,
            schema=schemas["staleness_packet"],
        )
        bad_output = {
            "id": "x",
            "review_packet_id": packet["id"],
            "created_at": "2026-06-25T12:00:00Z",
            "review_week": "2026-W26",
            "decision": "surface_decisions",
            "observations": [],
            "entries": [{"scope_key": "nope"}],  # missing required judgment fields
            "uncertainty": [],
            "auto_demote_enabled": False,
            "review_signal": {
                "id": "rs",
                "status": "surface_decisions",
                "created_at": "2026-06-25T12:00:00Z",
                "trigger_ref": packet["id"],
            },
        }

        class _Bad:
            def review(self, _packet):
                return deepcopy(bad_output)

        with self.assertRaises(StalenessOutputValidationError):
            run_staleness_review(
                records=_seed_records(),
                as_of=AS_OF,
                reviewer=_Bad(),
                packet_schema=schemas["staleness_packet"],
                output_schema=schemas["staleness_output"],
            )

    def test_auto_demote_on_produces_approved_proposal_for_synth_crm(self):
        schemas = _schemas()
        reviewer = RecordedStalenessReviewer.from_examples(
            ROOT / "examples" / "state-reviews"
        )
        with TemporaryDirectory() as directory:
            result = run_staleness_review(
                records=_seed_records(),
                as_of=AS_OF,
                reviewer=reviewer,
                auto_demote_enabled=True,
                out_dir=Path(directory),
                output_schema=schemas["staleness_output"],
                packet_schema=schemas["staleness_packet"],
            )
        proposals = result.output["demote_proposals"]
        self.assertEqual(1, len(proposals))
        self.assertTrue(proposals[0]["approval_required"])
        self.assertEqual("state_instance.synthyra", proposals[0]["target_ref"])


class CliDryRunTests(unittest.TestCase):
    def test_cli_recorded_dry_run_produces_packet(self):
        with TemporaryDirectory() as directory:
            buffer = io.StringIO()
            rc = cli_main(
                [
                    "--project-root",
                    str(ROOT),
                    "staleness-review-run",
                    "--freshness-dir",
                    str(FRESHNESS_DIR),
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
            self.assertEqual(5, summary["decisions_queued"])
            self.assertFalse(summary["auto_demote_enabled"])
            self.assertEqual(0, summary["demote_proposals"])
            self.assertTrue(Path(summary["markdown_path"]).exists())

    def test_cli_auto_demote_flag_proposes_but_does_not_mutate(self):
        with TemporaryDirectory() as directory:
            buffer = io.StringIO()
            rc = cli_main(
                [
                    "--project-root",
                    str(ROOT),
                    "staleness-review-run",
                    "--freshness-dir",
                    str(FRESHNESS_DIR),
                    "--as-of",
                    "2026-06-25T12:00:00Z",
                    "--output-dir",
                    directory,
                    "--auto-demote",
                ],
                stdout=buffer,
            )
            self.assertEqual(0, rc)
            summary = json.loads(buffer.getvalue())
        self.assertTrue(summary["auto_demote_enabled"])
        self.assertEqual(1, summary["demote_proposals"])

    def test_cli_company_filter_scopes_records(self):
        with TemporaryDirectory() as directory:
            buffer = io.StringIO()
            rc = cli_main(
                [
                    "--project-root",
                    str(ROOT),
                    "staleness-review-run",
                    "--freshness-dir",
                    str(FRESHNESS_DIR),
                    "--as-of",
                    "2026-06-25T12:00:00Z",
                    "--output-dir",
                    directory,
                    "--company",
                    "navicyte",
                ],
                stdout=buffer,
            )
            self.assertEqual(0, rc)
            summary = json.loads(buffer.getvalue())
        # navicyte has 1 surfaced finding (notion stale); email fresh is skipped.
        self.assertEqual(1, summary["findings"])
        # No recorded fixture exists for the navicyte-scoped packet id, so the
        # runner honestly surfaces evidence only rather than fabricating judgment.
        self.assertFalse(summary["judgments_present"])
        self.assertEqual("awaiting_review", summary["decision"])


if __name__ == "__main__":
    unittest.main()
