from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest

from state_system.trace_runner import run_trace_manifest


ROOT = Path(__file__).resolve().parents[1]


class TraceReportingTests(unittest.TestCase):
    def test_trace_run_writes_user_testable_activation_report(self):
        with TemporaryDirectory() as directory:
            report = run_trace_manifest(
                project_root=ROOT,
                manifest_path=ROOT / "examples" / "traces" / "laura-agent-activation.trace.json",
                output_dir=Path(directory),
            )

            report_path = Path(directory) / "index.html"

            self.assertEqual("passed", report["status"])
            self.assertTrue(report_path.exists())
            html = report_path.read_text(encoding="utf-8")
            self.assertIn("State System User Test Report", html)
            self.assertIn("trace.laura-agent-activation", html)
            self.assertIn("Draft internal material and identify what requires approval.", html)
            self.assertIn("Expected response type", html)
            self.assertIn("proposal", html)
            self.assertIn("Allowed Actions", html)
            self.assertIn("action.laura.southern-abrasives-internal-proof-note", html)
            self.assertIn("Prohibited Actions", html)
            self.assertIn("action.laura.southern-abrasives-linkedin-publish", html)
            self.assertIn("Requires refresh before external action", html)
            self.assertIn("Captured Agent Response", html)
            self.assertIn("I can draft an internal proof-point note", html)

    def test_demo_script_runs_activation_trace_and_prints_report_path(self):
        with TemporaryDirectory() as directory:
            result = subprocess.run(
                ["bash", str(ROOT / "scripts" / "demo_state_system.sh")],
                cwd=ROOT,
                env={"STATE_SYSTEM_DEMO_ROOT": directory},
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("Report:", result.stdout)
            self.assertTrue((Path(directory) / "index.html").exists())


if __name__ == "__main__":
    unittest.main()
