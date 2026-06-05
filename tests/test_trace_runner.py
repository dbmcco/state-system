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

        trace_results = {
            result.path.name: result
            for result in results
            if result.path.name.endswith(".trace.json")
        }
        self.assertEqual(
            {
                "maya-approval-gated-publication.trace.json",
                "maya-agent-activation.trace.json",
                "maya-stale-context-refresh.trace.json",
                "linear-deal-won.trace.json",
                "southern-abrasives-loop.trace.json",
            },
            set(trace_results),
        )
        self.assertEqual([], [result for result in trace_results.values() if not result.ok])

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
            self.assertIn("Package: context.maya.demo-recent", rendered)

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

    def test_approval_gated_trace_preserves_pending_approval_without_state_effect(self):
        with TemporaryDirectory() as directory:
            report = run_trace_manifest(
                project_root=ROOT,
                manifest_path=(
                    ROOT
                    / "examples"
                    / "traces"
                    / "maya-approval-gated-publication.trace.json"
                ),
                output_dir=Path(directory),
            )

            self.assertEqual("passed", report["status"])
            self.assertEqual(
                "trace.maya-approval-gated-publication",
                report["trace_id"],
            )
            self.assertEqual("pending_approval", report["validated"]["commit_status"])
            self.assertEqual(1, report["validated"]["pending_approval_count"])
            self.assertEqual(0, report["validated"]["materialized_snapshot_count"])
            artifacts = {
                step["name"]: Path(step["artifact_path"])
                for step in report["steps"]
                if "artifact_path" in step
            }
            self.assertNotIn("updated-state", artifacts)

            commit = load_json(artifacts["commit"])
            self.assertEqual("pending_approval", commit["status"])
            self.assertEqual([], commit["accepted_journal_entry_refs"])
            self.assertEqual([], commit["materialized_snapshot_refs"])
            self.assertEqual(1, len(commit["pending_approvals"]))

            effects = load_json(artifacts["commit-effects"])
            self.assertEqual("pending_approval", effects["commit_status"])
            self.assertEqual([], effects["materialized_snapshot_refs"])
            self.assertEqual(1, len(effects["pending_approvals"]))

            rendered = artifacts["render-package"].read_text(encoding="utf-8")
            self.assertIn("Requires refresh before external action.", rendered)


if __name__ == "__main__":
    unittest.main()
