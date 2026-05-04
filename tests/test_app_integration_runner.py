from pathlib import Path
from tempfile import TemporaryDirectory
from io import StringIO
from html import unescape
import json
import unittest

from state_system import cli
from state_system.app_integrations import run_app_integration_fixtures


ROOT = Path(__file__).resolve().parents[1]


class AppIntegrationRunnerTests(unittest.TestCase):
    def test_runner_writes_report_for_current_fixture_chains(self):
        with TemporaryDirectory() as directory:
            report = run_app_integration_fixtures(
                project_root=ROOT,
                output_dir=Path(directory),
            )

            self.assertEqual("passed", report["status"])
            self.assertEqual(6, len(report["chains"]))
            self.assertEqual(
                {
                    "prospect-to-outreach",
                    "outreach-reply-to-crm-secondary-contacts",
                    "meeting-coordination-updates",
                    "thoughtforge-meeting-idea-provenance",
                    "visual-forge-qualitative-learning",
                    "crm-outcome-to-prospect-outreach-doctrine",
                },
                {chain["id"] for chain in report["chains"]},
            )
            self.assertEqual([], [
                check
                for chain in report["chains"]
                for check in chain["checks"]
                if check["status"] != "passed"
            ])
            self.assertTrue((Path(directory) / "app-integration-report.json").exists())
            html = unescape((Path(directory) / "index.html").read_text(encoding="utf-8"))
            self.assertIn("Prospect Researcher -> Outreach Engine", html)
            self.assertIn("Outreach reply -> CRM and secondary contacts", html)
            self.assertIn("Meeting -> cross-app coordination updates", html)
            self.assertIn("Thoughtforge -> meeting-derived idea provenance", html)
            self.assertIn("Visual Forge -> qualitative creative learning", html)
            self.assertIn("CRM outcome -> Prospect and Outreach doctrine", html)
            self.assertIn("No hidden scoring", html)
            self.assertIn("No regex routing", html)
            self.assertIn("No keyword extraction or source-free ideas", html)
            self.assertIn("No hardcoded author assignment or source-free publication", html)
            self.assertIn("No style scores or hidden prompt rewrite", html)
            self.assertIn("No sales scores or app-local doctrine mutation", html)

    def test_cli_runs_app_integration_report(self):
        with TemporaryDirectory() as directory:
            output = StringIO()
            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "app-integrations-run",
                    "--output-dir",
                    directory,
                ],
                stdout=output,
            )

            self.assertEqual(0, code)
            payload = json.loads(output.getvalue())
            self.assertEqual("passed", payload["status"])
            self.assertEqual(str(Path(directory)), payload["output_dir"])
            self.assertTrue((Path(directory) / "index.html").exists())


if __name__ == "__main__":
    unittest.main()
