from __future__ import annotations

import unittest

from state_system.instance_agent_packages import evaluate_route_freshness_sufficiency


class RouteFreshnessSufficiencyTests(unittest.TestCase):
    def test_route_must_explicitly_declare_the_dimension_and_basis_it_accepts(self):
        route = {
            "id": "question_route.test.event_lookup",
            "required_source_coverage": [
                {
                    "connector_refs": ["connector.test.events"],
                    "freshness_sufficiency": {
                        "required_dimensions": ["event_status"],
                        "acceptable_watermark_bases": ["source_event"],
                        "minimum_status": "fresh",
                    },
                }
            ],
        }
        result = evaluate_route_freshness_sufficiency(
            route,
            [
                {
                    "connector_ref": "connector.test.events",
                    "event_status": "fresh",
                    "content_status": "unknown",
                    "watermark_basis": "source_event",
                    "source_gap_refs": [],
                }
            ],
        )
        self.assertTrue(result["sufficient"])
        self.assertEqual("event_status", result["satisfied_dimensions"][0])

    def test_index_route_does_not_promote_index_freshness_to_content_freshness(self):
        route = {
            "id": "question_route.test.index_lookup",
            "required_source_coverage": [
                {
                    "connector_refs": ["connector.test.index"],
                    "freshness_sufficiency": {
                        "required_dimensions": ["index_status"],
                        "acceptable_watermark_bases": ["source_index"],
                        "minimum_status": "fresh",
                    },
                }
            ],
        }
        result = evaluate_route_freshness_sufficiency(
            route,
            [
                {
                    "connector_ref": "connector.test.index",
                    "index_status": "fresh",
                    "content_status": "unknown",
                    "watermark_basis": "source_index",
                    "source_gap_refs": [],
                }
            ],
        )
        self.assertTrue(result["sufficient"])
        self.assertEqual("unknown", result["content_status"])

    def test_route_without_declaration_is_not_sufficient(self):
        result = evaluate_route_freshness_sufficiency(
            {
                "id": "question_route.test.implicit",
                "required_source_coverage": [
                    {"connector_refs": ["connector.test.source"]}
                ],
            },
            [
                {
                    "connector_ref": "connector.test.source",
                    "content_status": "fresh",
                    "watermark_basis": "source_content",
                    "source_gap_refs": [],
                }
            ],
        )
        self.assertFalse(result["sufficient"])
        self.assertIn("explicit freshness sufficiency declaration", result["status_reason"])

    def test_incomplete_content_remains_visible_and_blocks_content_route(self):
        route = {
            "id": "question_route.test.complete_content",
            "required_source_coverage": [
                {
                    "connector_refs": ["connector.test.content"],
                    "freshness_sufficiency": {
                        "required_dimensions": ["content_status", "completeness_status"],
                        "acceptable_watermark_bases": ["source_content"],
                        "minimum_status": "fresh",
                    },
                }
            ],
        }
        result = evaluate_route_freshness_sufficiency(
            route,
            [
                {
                    "connector_ref": "connector.test.content",
                    "content_status": "fresh",
                    "completeness_status": "incomplete",
                    "watermark_basis": "source_content",
                    "source_gap_refs": ["gap.content.incomplete"],
                }
            ],
        )
        self.assertFalse(result["sufficient"])
        self.assertIn("gap.content.incomplete", result["source_gap_refs"])


if __name__ == "__main__":
    unittest.main()
