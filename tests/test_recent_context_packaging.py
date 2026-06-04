from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system.context_packages import ContextPackager
from state_system.contracts import load_json, validate_schema
from state_system.recent_changes import RecentChangeIndexer
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]


class RecentContextPackagingTests(unittest.TestCase):
    def test_recent_change_entry_preserves_refs_routes_and_freshness(self):
        source_event = load_json(ROOT / "examples" / "source-linear-southern-abrasives-won.json")
        commit_result = load_json(
            ROOT / "examples" / "linear-southern-abrasives-won-commit-result.json"
        )

        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            entry = RecentChangeIndexer(stores, self._schemas()).index_from_source_commit(
                source_event=source_event,
                commit_result=commit_result,
                created_at="2026-04-28T16:07:30Z",
                summary=(
                    "Southern Abrasives moved from proposal to won, creating "
                    "operational handoff work and a possible marketing proof-point "
                    "opportunity."
                ),
                candidate_persona_routes=self._southern_abrasives_routes(),
                opportunity_class_hints=[
                    "operational_handoff",
                    "marketing_opportunity",
                    "relationship_follow_up",
                ],
                freshness={
                    "watermark_refs": [
                        "state.sampleco.deal.southern-abrasives@journal.sampleco.deal.southern-abrasives.won",
                        "governance.external-copy-approval",
                    ],
                    "stale_after": "2026-04-29T16:07:30Z",
                    "requires_refresh_before_external_action": True,
                },
            )

            self.assertEqual("recent.linear.southern-abrasives-won", entry["id"])
            self.assertEqual(["commit.linear.southern-abrasives-won"], entry["commit_refs"])
            self.assertEqual(
                ["journal.sampleco.deal.southern-abrasives.won"],
                entry["journal_entry_refs"],
            )
            self.assertEqual(
                ["review.linear.southern-abrasives-won"],
                entry["review_signal_refs"],
            )
            self.assertEqual(
                ["persona.patrick", "persona.laura"],
                [route["persona_ref"] for route in entry["candidate_persona_routes"]],
            )
            self.assertTrue(entry["freshness"]["requires_refresh_before_external_action"])
            self.assertEqual(entry, stores.recent_changes.read(entry["id"]))
            self.assertEqual([], validate_schema(entry, self._schemas()["recent_change"]))

    def test_laura_opportunity_package_includes_relevant_context_and_exclusions(self):
        with TemporaryDirectory() as directory:
            stores = self._stores_with_southern_abrasives_context(Path(directory))
            recent_change = load_json(
                ROOT / "examples" / "recent-linear-southern-abrasives-won.json"
            )
            stores.recent_changes.create(recent_change)

            package = ContextPackager(stores, self._schemas()).build_opportunity_package(
                persona=load_json(ROOT / "examples" / "laura-persona.json"),
                recent_change_id=recent_change["id"],
                package_id="context.laura.southern-abrasives-won-opportunity",
                created_at="2026-04-28T16:08:00Z",
                review_goal=(
                    "Decide whether the Southern Abrasives won deal creates a "
                    "marketing opportunity, and if so propose only internal draft "
                    "or approval-gated external publication actions."
                ),
                state_refs=[
                    "state.sampleco.deal.southern-abrasives",
                    "state.operating_picture.marketing",
                ],
                memory_refs=["memory.laura.marketing.draft.audience-before-copy"],
                governance_constraints=[
                    {
                        "id": "governance.external-copy-approval",
                        "summary": "External-facing campaign copy requires approval before publication.",
                        "approval_required": True,
                    }
                ],
                resolved_evidence=[
                    {
                        "ref": "linear:event:southern-abrasives-stage-won-2026-04-28",
                        "summary": "Linear shows Southern Abrasives moved from proposal to won.",
                        "source_type": "linear_event",
                        "observed_at": "2026-04-28T16:05:00Z",
                    }
                ],
                unresolved_evidence_refs=[
                    "linear:deal:southern-abrasives.public-announcement-permission",
                    "linear:deal:southern-abrasives.approved-proof-point",
                ],
                relationship_sensitivity={
                    "level": "unknown",
                    "summary": (
                        "The deal can be used for internal reasoning, but public "
                        "naming and customer-specific claims are not approved."
                    ),
                    "redactions": [
                        "commercial terms",
                        "private negotiation detail",
                        "delivery handoff detail",
                    ],
                },
                available_actions=[
                    {
                        "id": "action.laura.southern-abrasives-internal-proof-note",
                        "summary": "Draft an internal proof-point note.",
                        "approval_required": False,
                    },
                    {
                        "id": "action.laura.southern-abrasives-linkedin-publish",
                        "summary": "Publish LinkedIn copy.",
                        "approval_required": True,
                    },
                ],
                excluded_context_summary=[
                    {
                        "scope": "operations",
                        "summary": (
                            "Delivery handoff details and operational task detail "
                            "were excluded from Laura's package."
                        ),
                    }
                ],
                open_questions=[
                    "Can Southern Abrasives be named publicly?",
                    "What proof point is approved for external use?",
                ],
                valid_until="2026-04-29T16:08:00Z",
                stale_if_refs_change=[
                    "state.sampleco.deal.southern-abrasives",
                    "governance.external-copy-approval",
                ],
            )

            self.assertEqual("opportunity", package["package_type"])
            self.assertEqual("persona.laura", package["persona_context"]["persona_ref"])
            self.assertEqual(
                ["recent.linear.southern-abrasives-won"],
                [entry["id"] for entry in package["recent_change_context"]["entries"]],
            )
            self.assertEqual(
                ["state.sampleco.deal.southern-abrasives", "state.operating_picture.marketing"],
                [snapshot["id"] for snapshot in package["state_context"]["snapshots"]],
            )
            self.assertEqual(
                ["memory.laura.marketing.draft.audience-before-copy"],
                [entry["id"] for entry in package["memory_context"]["entries"]],
            )
            self.assertTrue(package["freshness"]["requires_refresh_before_external_action"])
            self.assertIn("operations", package["excluded_context_summary"][0]["scope"])
            self.assertEqual(package, stores.context_packages.read(package["id"]))
            self.assertEqual([], validate_schema(package, self._schemas()["context_package"]))

    def test_recent_change_package_excludes_ambient_and_excluded_routes_by_default(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            stores.recent_changes.create(
                self._change_with_routes(
                    "recent.github.internal-webhook-retry",
                    [
                        {
                            "persona_ref": "persona.patrick",
                            "relevance_tier": "primary",
                            "routing_reason": "Operational reliability work affects follow-through.",
                            "included": True,
                        },
                        {
                            "persona_ref": "persona.laura",
                            "relevance_tier": "ambient",
                            "routing_reason": "Low-level implementation detail has no explicit marketing route.",
                            "included": False,
                            "excluded_context_summary": (
                                "Internal webhook retry task excluded from Laura's default package."
                            ),
                        },
                    ],
                )
            )
            stores.recent_changes.create(
                self._change_with_routes(
                    "recent.github.audit-trail-merged",
                    [
                        {
                            "persona_ref": "persona.laura",
                            "relevance_tier": "escalated",
                            "routing_reason": "Capability was explicitly escalated as launch-proof context.",
                            "included": True,
                            "opportunity_class_hints": ["launch_proof"],
                        }
                    ],
                )
            )

            package = ContextPackager(stores, self._schemas()).build_recent_change_package(
                persona=load_json(ROOT / "examples" / "laura-persona.json"),
                package_id="context.laura.recent",
                created_at="2026-04-30T12:00:00Z",
                review_goal="Review recent Laura-relevant changes.",
                valid_until="2026-04-30T18:00:00Z",
            )

            self.assertEqual(
                ["recent.github.audit-trail-merged"],
                [entry["id"] for entry in package["recent_change_context"]["entries"]],
            )
            self.assertEqual(
                ["recent.github.internal-webhook-retry"],
                [
                    item["recent_change_ref"]
                    for item in package["excluded_context_summary"]
                ],
            )

    def test_recent_change_package_preserves_freshness_for_external_action(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            change = self._change_with_routes(
                "recent.linear.southern-abrasives-won",
                [
                    {
                        "persona_ref": "persona.laura",
                        "relevance_tier": "secondary",
                        "routing_reason": "Won deal may become a proof point.",
                        "included": True,
                    }
                ],
            )
            change["freshness"] = {
                "watermark_refs": [
                    "state.sampleco.deal.southern-abrasives@journal.sampleco.deal.southern-abrasives.won",
                    "governance.external-copy-approval",
                ],
                "stale_after": "2026-04-29T16:07:30Z",
                "requires_refresh_before_external_action": True,
            }
            stores.recent_changes.create(change)

            package = ContextPackager(stores, self._schemas()).build_recent_change_package(
                persona=load_json(ROOT / "examples" / "laura-persona.json"),
                package_id="context.laura.recent-refresh-required",
                created_at="2026-04-30T12:00:00Z",
                review_goal="Review recent Laura-relevant changes.",
                valid_until="2026-04-30T18:00:00Z",
            )

            self.assertTrue(package["freshness"]["requires_refresh_before_external_action"])
            self.assertEqual(
                [
                    "state.sampleco.deal.southern-abrasives@journal.sampleco.deal.southern-abrasives.won",
                    "governance.external-copy-approval",
                ],
                package["freshness"]["watermark_refs"],
            )

    def test_shared_change_can_route_differently_to_laura_and_patrick(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            stores.recent_changes.create(
                self._change_with_routes(
                    "recent.linear.southern-abrasives-won",
                    self._southern_abrasives_routes(),
                )
            )

            laura_package = ContextPackager(stores, self._schemas()).build_recent_change_package(
                persona=load_json(ROOT / "examples" / "laura-persona.json"),
                package_id="context.laura.recent-southern-abrasives",
                created_at="2026-04-30T12:00:00Z",
                review_goal="Review Laura-relevant changes.",
                valid_until="2026-04-30T18:00:00Z",
            )
            patrick_package = ContextPackager(
                stores,
                self._schemas(),
            ).build_recent_change_package(
                persona=load_json(ROOT / "examples" / "patrick-persona.json"),
                package_id="context.patrick.recent-southern-abrasives",
                created_at="2026-04-30T12:00:00Z",
                review_goal="Review Patrick-relevant changes.",
                valid_until="2026-04-30T18:00:00Z",
            )

            self.assertEqual(
                "secondary",
                laura_package["recent_change_context"]["entries"][0]["persona_route"][
                    "relevance_tier"
                ],
            )
            self.assertEqual(
                "primary",
                patrick_package["recent_change_context"]["entries"][0]["persona_route"][
                    "relevance_tier"
                ],
            )

    def _stores_with_southern_abrasives_context(self, root: Path) -> StateStoreBundle:
        stores = StateStoreBundle(root)
        stores.state_objects.create(
            load_json(ROOT / "examples" / "southern-abrasives-deal-state-after-won.json")
        )
        stores.state_objects.create(load_json(ROOT / "examples" / "marketing-operating-picture.json"))
        stores.journals.create(load_json(ROOT / "examples" / "southern-abrasives-won-journal-entry.json"))
        stores.memory.create(load_json(ROOT / "examples" / "laura-agent-memory-entry.json"))
        return stores

    def _schemas(self):
        return {
            "recent_change": load_json(ROOT / "schemas" / "recent-change-entry.schema.json"),
            "context_package": load_json(ROOT / "schemas" / "context-package.schema.json"),
        }

    def _southern_abrasives_routes(self):
        return [
            {
                "persona_ref": "persona.patrick",
                "relevance_tier": "primary",
                "routing_reason": (
                    "Won deal creates operational handoff, owner, next-action, "
                    "document, and relationship-sensitivity checks."
                ),
                "included": True,
                "opportunity_class_hints": [
                    "operational_handoff",
                    "relationship_follow_up",
                ],
            },
            {
                "persona_ref": "persona.laura",
                "relevance_tier": "secondary",
                "routing_reason": (
                    "Won deal may become a marketing proof point or announcement, "
                    "but public naming permission is unresolved."
                ),
                "included": True,
                "opportunity_class_hints": [
                    "marketing_opportunity",
                    "proof_point",
                    "external_copy_candidate",
                ],
            },
        ]

    def _change_with_routes(self, change_id, routes):
        return {
            "id": change_id,
            "created_at": "2026-04-30T12:00:00Z",
            "occurred_at": "2026-04-30T11:55:00Z",
            "source_system": "github",
            "source_event": "pull_request.merged",
            "summary": change_id,
            "source_refs": [change_id.replace("recent.", "github:")],
            "affected_state_refs": [],
            "candidate_persona_routes": routes,
            "opportunity_class_hints": [],
            "freshness": {
                "watermark_refs": [change_id],
                "stale_after": "2026-05-01T12:00:00Z",
                "requires_refresh_before_external_action": False,
            },
        }


if __name__ == "__main__":
    unittest.main()
