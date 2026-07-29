from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system.api_surface import StateDispatcher
from state_system.reporting import _trace_report_content_health, run_report_suite


ROOT = Path(__file__).resolve().parents[1]


class InspectReportContentHealthIntegrationTests(unittest.TestCase):
    def test_inspect_package_reports_content_health_separately_from_process_health(self):
        with TemporaryDirectory() as directory:
            state_root = Path(directory)
            package_dir = state_root / "state" / "instance-agent-packages"
            package_dir.mkdir(parents=True)
            package = {
                "id": "instance_agent_package.sample.content_health",
                "created_at": "2026-06-25T12:00:00Z",
                "source_context": {
                    "source_readiness": [
                        {
                            "connector_ref": "connector.sample.docs",
                            "source_ref": "docs:sample",
                            "freshness_status": "fresh",
                            "content_status": "stale",
                            "process_status": "succeeded",
                            "stale_after": "2026-06-20T00:00:00Z",
                            "source_gap_refs": [
                                "gap.state_instance.sample.connector.sample.docs.content_stale"
                            ],
                            "evidence_refs": ["freshness:docs:stale-content"],
                        }
                    ],
                    "source_gap_refs": [
                        "gap.state_instance.sample.connector.sample.docs.content_stale"
                    ],
                },
                "freshness": {
                    "generated_at": "2026-06-25T12:00:00Z",
                    "requires_refresh_before_external_action": True,
                    "content_status": "stale",
                    "process_status": "succeeded",
                    "source_gap_refs": [
                        "gap.state_instance.sample.connector.sample.docs.content_stale"
                    ],
                },
            }
            package_dir.joinpath(f"{package['id']}.json").write_text(
                json.dumps(package), encoding="utf-8"
            )

            response = StateDispatcher(ROOT, state_root).dispatch(
                "inspect",
                scope="state:local",
                arguments={"package_ref": package["id"]},
            )

        self.assertEqual("ok", response["status"])
        health = response["data"]["package_health"]
        self.assertEqual("succeeded", health["process_status"])
        self.assertEqual("stale", health["content_status"])
        self.assertNotEqual(health["process_status"], health["content_status"])
        self.assertTrue(health["requires_refresh_before_external_action"])
        self.assertIn(
            "gap.state_instance.sample.connector.sample.docs.content_stale",
            health["source_gap_refs"],
        )

    def test_inspect_rechecks_package_stale_after_at_inspection_time(self):
        with TemporaryDirectory() as directory:
            state_root = Path(directory)
            package_dir = state_root / "state" / "instance-agent-packages"
            package_dir.mkdir(parents=True)
            package = {
                "id": "instance_agent_package.sample.aged_out",
                "created_at": "2000-01-01T00:00:00Z",
                "source_context": {
                    "source_readiness": [
                        {
                            "connector_ref": "connector.sample.docs",
                            "source_ref": "docs:sample",
                            "freshness_status": "fresh",
                            "content_status": "fresh",
                            "process_status": "succeeded",
                            "stale_after": "2000-01-02T00:00:00Z",
                            "source_gap_refs": [],
                            "gap_refs": [],
                            "evidence_refs": ["freshness:docs:fresh-at-generation"],
                        }
                    ],
                    "source_gap_refs": [],
                },
                "freshness": {
                    "generated_at": "2000-01-01T00:00:00Z",
                    "requires_refresh_before_external_action": False,
                    "content_status": "fresh",
                    "process_status": "succeeded",
                    "source_gap_refs": [],
                    "expired_freshness_refs": [],
                },
            }
            package_dir.joinpath(f"{package['id']}.json").write_text(
                json.dumps(package), encoding="utf-8"
            )

            response = StateDispatcher(ROOT, state_root).dispatch(
                "inspect",
                scope="state:local",
                arguments={"package_ref": package["id"]},
            )

        health = response["data"]["package_health"]
        self.assertEqual("succeeded", health["process_status"])
        self.assertEqual("stale", health["content_status"])
        self.assertTrue(health["expired_freshness_refs"])
        self.assertIn("HARD STALENESS BANNER", health["staleness_banner"])

    def test_inspect_unreadable_package_artifact_falls_back_to_unknown_health(self):
        with TemporaryDirectory() as directory:
            state_root = Path(directory)
            package_dir = state_root / "state" / "instance-agent-packages"
            package_dir.mkdir(parents=True)
            package_ref = "instance_agent_package.sample.unreadable"
            package_dir.joinpath(f"{package_ref}.json").write_bytes(b"\xff\xfe")

            response = StateDispatcher(ROOT, state_root).dispatch(
                "inspect",
                scope="state:local",
                arguments={"package_ref": package_ref},
            )

        self.assertEqual("ok", response["status"])
        self.assertIsNone(response["data"]["package_health"])
        self.assertEqual("unknown", response["data"]["content_health"]["status"])
        self.assertIn("HARD STALENESS BANNER", response["data"]["content_health"]["staleness_banner"])

    def test_inspect_malformed_package_ref_collections_fall_back_safely(self):
        with TemporaryDirectory() as directory:
            state_root = Path(directory)
            package_dir = state_root / "state" / "instance-agent-packages"
            package_dir.mkdir(parents=True)
            package = {
                "id": "instance_agent_package.sample.malformed_refs",
                "created_at": "2026-06-25T12:00:00Z",
                "source_context": {
                    "source_readiness": [
                        {
                            "connector_ref": "connector.sample.docs",
                            "freshness_status": "unknown",
                            "content_status": "unknown",
                            "source_gap_refs": None,
                            "gap_refs": None,
                            "evidence_refs": None,
                        }
                    ],
                    "source_gap_refs": None,
                },
                "freshness": {
                    "generated_at": "2026-06-25T12:00:00Z",
                    "requires_refresh_before_external_action": True,
                    "content_status": "unknown",
                    "process_status": "succeeded",
                    "source_gap_refs": None,
                    "expired_freshness_refs": None,
                    "evidence_refs": None,
                },
            }
            package_dir.joinpath(f"{package['id']}.json").write_text(
                json.dumps(package), encoding="utf-8"
            )

            response = StateDispatcher(ROOT, state_root).dispatch(
                "inspect",
                scope="state:local",
                arguments={"package_ref": package["id"]},
            )

        self.assertEqual("ok", response["status"])
        self.assertEqual("unknown", response["data"]["content_health"]["status"])
        self.assertIn("HARD STALENESS BANNER", response["data"]["content_health"]["staleness_banner"])

    def test_trace_report_content_health_preserves_unknown_content_status(self):
        with TemporaryDirectory() as directory:
            artifact = Path(directory) / "activation.json"
            artifact.write_text(
                json.dumps(
                    {
                        "freshness": {
                            "content_status": "unknown",
                            "requires_refresh_before_external_action": False,
                            "stale_at_activation": False,
                        }
                    }
                ),
                encoding="utf-8",
            )
            health = _trace_report_content_health(
                {
                    "steps": [
                        {
                            "name": "agent-activation",
                            "artifact_type": "json",
                            "artifact_path": str(artifact),
                        }
                    ]
                }
            )

        self.assertEqual("unknown", health["status"])
        self.assertIn("HARD STALENESS BANNER", health["staleness_banner"])

    def test_trace_report_content_health_preserves_failed_content_status(self):
        with TemporaryDirectory() as directory:
            artifact = Path(directory) / "activation.json"
            artifact.write_text(
                json.dumps(
                    {
                        "freshness": {
                            "content_status": "failed",
                            "requires_refresh_before_external_action": True,
                            "stale_at_activation": True,
                        }
                    }
                ),
                encoding="utf-8",
            )
            health = _trace_report_content_health(
                {
                    "steps": [
                        {
                            "name": "agent-activation",
                            "artifact_type": "json",
                            "artifact_path": str(artifact),
                        }
                    ]
                }
            )

        self.assertEqual("failed", health["status"])
        self.assertTrue(health["requires_refresh_before_external_action"])

    def test_report_suite_exposes_content_health_and_raw_artifact_links(self):
        with TemporaryDirectory() as directory:
            output_dir = Path(directory)
            suite = run_report_suite(project_root=ROOT, output_dir=output_dir)
            suite_json = json.loads(
                output_dir.joinpath("report-suite.json").read_text(encoding="utf-8")
            )
            html = output_dir.joinpath("index.html").read_text(encoding="utf-8")

        self.assertEqual("passed", suite["process_health"]["status"])
        self.assertIn("status", suite["content_health"])
        self.assertIn("process_health", suite_json)
        self.assertIn("content_health", suite_json)
        self.assertTrue(
            all(report.get("raw_artifact_refs") for report in suite_json["reports"])
        )
        self.assertIn("Process health", html)
        self.assertIn("Content health", html)
        self.assertIn("Raw artifacts", html)
        self.assertIn("report-suite.json", html)


if __name__ == "__main__":
    unittest.main()
