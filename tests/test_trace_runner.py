from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.contracts import load_json, validate_all_examples
from state_system.trace_runner import run_trace_manifest


ROOT = Path(__file__).resolve().parents[1]


class TraceRunnerTests(unittest.TestCase):
    def test_trace_manifest_validates_with_examples(self):
        results = validate_all_examples(ROOT)

        trace_results = [
            result
            for result in results
            if result.path.name == "linear-deal-won.trace.json"
        ]
        self.assertEqual(1, len(trace_results))
        self.assertTrue(trace_results[0].ok, trace_results[0].errors)

    def test_trace_runner_replays_source_event_to_agent_context_flow(self):
        with TemporaryDirectory() as directory:
            report = run_trace_manifest(
                project_root=ROOT,
                manifest_path=ROOT / "examples" / "traces" / "linear-deal-won.trace.json",
                output_dir=Path(directory),
            )

            self.assertEqual("passed", report["status"])
            self.assertEqual("trace.linear-deal-won", report["trace_id"])
            self.assertEqual(
                "won",
                load_json(Path(directory) / "05-updated-state.json")["status"],
            )
            self.assertIn(
                "08-rendered-package.txt",
                [Path(step["artifact_path"]).name for step in report["steps"]],
            )
            rendered = (Path(directory) / "08-rendered-package.txt").read_text(
                encoding="utf-8"
            )
            self.assertIn("State System Agent Package", rendered)
            self.assertIn("Package: context.laura.demo-recent", rendered)

    def test_cli_trace_run_returns_machine_readable_report(self):
        with TemporaryDirectory() as directory:
            output = StringIO()

            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "trace-run",
                    str(ROOT / "examples" / "traces" / "linear-deal-won.trace.json"),
                    "--output-dir",
                    directory,
                ],
                stdout=output,
            )

            self.assertEqual(0, code, output.getvalue())
            payload = json.loads(output.getvalue())
            self.assertEqual("passed", payload["status"])
            self.assertEqual("trace.linear-deal-won", payload["trace_id"])
            self.assertTrue((Path(directory) / "trace-report.json").exists())


if __name__ == "__main__":
    unittest.main()
