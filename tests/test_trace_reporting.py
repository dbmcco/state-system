from pathlib import Path
from io import StringIO
import json
import os
import subprocess
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.reporting import run_report_suite
from state_system.trace_runner import run_trace_manifest


ROOT = Path(__file__).resolve().parents[1]


class TraceReportingTests(unittest.TestCase):
    def test_trace_run_writes_user_testable_activation_report(self):
        with TemporaryDirectory() as directory:
            report = run_trace_manifest(
                project_root=ROOT,
                manifest_path=ROOT / "examples" / "traces" / "maya-agent-activation.trace.json",
                output_dir=Path(directory),
            )

            report_path = Path(directory) / "index.html"

            self.assertEqual("passed", report["status"])
            self.assertTrue(report_path.exists())
            html = report_path.read_text(encoding="utf-8")
            self.assertIn("State System User Test Report", html)
            self.assertIn("trace.maya-agent-activation", html)
            self.assertIn("Draft internal material and identify what requires approval.", html)
            self.assertIn("Expected response type", html)
            self.assertIn("proposal", html)
            self.assertIn("Allowed Actions", html)
            self.assertIn("action.maya.southern-abrasives-internal-proof-note", html)
            self.assertIn("Prohibited Actions", html)
            self.assertIn("action.maya.southern-abrasives-linkedin-publish", html)
            self.assertIn("Requires refresh before external action", html)
            self.assertIn("Captured Agent Response", html)
            self.assertIn("I can draft an internal proof-point note", html)

    def test_trace_report_surfaces_stale_context_refresh_boundary(self):
        with TemporaryDirectory() as directory:
            report = run_trace_manifest(
                project_root=ROOT,
                manifest_path=(
                    ROOT
                    / "examples"
                    / "traces"
                    / "maya-stale-context-refresh.trace.json"
                ),
                output_dir=Path(directory),
            )

            report_path = Path(directory) / "index.html"

            self.assertEqual("passed", report["status"])
            html = report_path.read_text(encoding="utf-8")
            self.assertIn("trace.maya-stale-context-refresh", html)
            self.assertIn("Package stale at activation", html)
            self.assertIn("2026-04-29T16:08:00Z", html)
            self.assertIn("Requires refresh before external action", html)
            self.assertIn(
                "Refresh the package before any external-facing action.",
                html,
            )
            self.assertIn("action.maya.southern-abrasives-linkedin-publish", html)

    def test_demo_script_runs_report_suite_and_prints_report_path(self):
        with TemporaryDirectory() as directory:
            result = subprocess.run(
                ["bash", str(ROOT / "scripts" / "demo_state_system.sh")],
                cwd=ROOT,
                env={**os.environ, "STATE_SYSTEM_DEMO_ROOT": directory},
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("Report Suite:", result.stdout)
            self.assertTrue((Path(directory) / "index.html").exists())
            self.assertTrue(
                (Path(directory) / "agent-activation-trace" / "index.html").exists()
            )
            self.assertTrue(
                (Path(directory) / "app-integrations" / "index.html").exists()
            )
            self.assertTrue((Path(directory) / "mission-records" / "index.html").exists())

    def test_report_suite_writes_index_for_trace_app_and_mission_reports(self):
        with TemporaryDirectory() as directory:
            report = run_report_suite(
                project_root=ROOT,
                output_dir=Path(directory),
            )

            self.assertEqual("passed", report["status"])
            self.assertEqual(
                {"agent-activation-trace", "app-integrations", "mission-records"},
                {entry["id"] for entry in report["reports"]},
            )
            self.assertTrue((Path(directory) / "index.html").exists())
            self.assertTrue((Path(directory) / "mission-records" / "index.html").exists())
            self.assertTrue(
                (Path(directory) / "mission-records" / "mission-read-model.json").exists()
            )
            html = (Path(directory) / "index.html").read_text(encoding="utf-8")
            self.assertIn("State System Report Suite", html)
            self.assertIn("Agent Activation Trace", html)
            self.assertIn("App Integration Report", html)
            self.assertIn("Mission Records Read Model", html)
            self.assertIn("href=\"mission-records/index.html\"", html)
            mission_html = (
                Path(directory) / "mission-records" / "index.html"
            ).read_text(encoding="utf-8")
            self.assertIn("Mission Records Report", mission_html)
            self.assertIn("mission.repo_audit.streamlinear", mission_html)
            self.assertIn("completed", mission_html)
            self.assertIn("Agent Roster", mission_html)
            self.assertIn("Timeline", mission_html)
            self.assertIn("Findings", mission_html)
            self.assertIn("Stumbles", mission_html)
            self.assertIn("Governance", mission_html)
            self.assertIn("Artifacts", mission_html)
            self.assertIn("Follow-ups", mission_html)
            self.assertIn("mission-read-model.json", mission_html)

    def test_cli_runs_report_suite(self):
        with TemporaryDirectory() as directory:
            output = StringIO()
            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "report-suite-run",
                    "--output-dir",
                    directory,
                ],
                stdout=output,
            )

            self.assertEqual(0, code)
            payload = json.loads(output.getvalue())
            self.assertEqual("passed", payload["status"])
            self.assertTrue((Path(directory) / "index.html").exists())
            self.assertTrue(
                (Path(directory) / "agent-activation-trace" / "index.html").exists()
            )
            self.assertTrue(
                (Path(directory) / "app-integrations" / "index.html").exists()
            )
            self.assertTrue((Path(directory) / "mission-records" / "index.html").exists())
            self.assertTrue(
                (Path(directory) / "mission-records" / "mission-read-model.json").exists()
            )


if __name__ == "__main__":
    unittest.main()
