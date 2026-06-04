from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.operational_loop import run_operational_loop


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "examples" / "operational-loop" / "southern-abrasives-loop.trace.json"


class OperationalLoopTests(unittest.TestCase):
    def test_operational_loop_runs_end_to_end_and_summarizes_operator_view(self):
        with TemporaryDirectory() as directory:
            summary = run_operational_loop(
                project_root=ROOT,
                manifest_path=MANIFEST,
                output_dir=Path(directory),
            )

            self.assertEqual("operational_loop.southern-abrasives", summary["id"])
            self.assertEqual("passed", summary["status"])
            self.assertEqual("accepted", summary["commit"]["status"])
            self.assertEqual(
                ["state.sampleco.deal.southern-abrasives"],
                summary["accepted_state_refs"],
            )
            self.assertGreaterEqual(len(summary["evidence_refs"]), 2)
            self.assertEqual(
                "context.laura.operational-loop",
                summary["working_model"]["context_package_id"],
            )
            self.assertTrue(summary["working_model"]["requires_refresh_before_external_action"])
            self.assertTrue(summary["agent"]["activation_id"].startswith("activation."))
            self.assertTrue(summary["agent"]["response_id"].startswith("response."))
            self.assertFalse(summary["agent"]["response_becomes_truth"])
            self.assertTrue((Path(directory) / "operator-summary.json").exists())

    def test_cli_runs_operational_loop(self):
        with TemporaryDirectory() as directory:
            output = StringIO()
            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "operational-loop-run",
                    str(MANIFEST),
                    "--output-dir",
                    directory,
                ],
                stdout=output,
            )

            self.assertEqual(0, code, output.getvalue())
            payload = json.loads(output.getvalue())
            summary_path = Path(payload["summary_path"])
            self.assertTrue(summary_path.exists())
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual("passed", summary["status"])
            self.assertEqual("agent_response", summary["agent"]["response_record_type"])


if __name__ == "__main__":
    unittest.main()
