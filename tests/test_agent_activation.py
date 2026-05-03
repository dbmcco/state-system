from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.contracts import load_json, validate_all_examples
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]


class AgentActivationTests(unittest.TestCase):
    def test_activation_schema_validates_example(self):
        results = validate_all_examples(ROOT)

        activation_results = [
            result
            for result in results
            if result.path.name == "laura-approval-gated-publication-activation.json"
        ]
        self.assertEqual(1, len(activation_results))
        self.assertTrue(activation_results[0].ok, activation_results[0].errors)

    def test_activation_separates_allowed_and_prohibited_actions_from_package(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            package = load_json(
                ROOT / "examples" / "laura-southern-abrasives-opportunity-context-package.json"
            )
            stores.context_packages.create(package)

            output = StringIO()
            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "activate-agent",
                    package["id"],
                    "--consumer",
                    "consumer.codex",
                    "--created-at",
                    "2026-05-03T10:00:00Z",
                    "--activation-goal",
                    "Draft internal material and identify what requires approval.",
                    "--expected-response-type",
                    "proposal",
                ],
                stdout=output,
            )

            self.assertEqual(0, code, output.getvalue())
            activation = json.loads(output.getvalue())
            self.assertEqual("agent_activation", activation["type"])
            self.assertEqual(package["id"], activation["package_id"])
            self.assertEqual("consumer.codex", activation["consumer_ref"])
            self.assertIn(
                "action.laura.southern-abrasives-internal-proof-note",
                activation["allowed_action_refs"],
            )
            self.assertIn(
                "action.laura.southern-abrasives-linkedin-publish",
                activation["prohibited_action_refs"],
            )
            self.assertTrue(
                activation["freshness"]["requires_refresh_before_external_action"]
            )
            self.assertEqual("capture_required", activation["capture_policy"]["mode"])
            self.assertEqual(
                activation,
                stores.agent_activations.read(activation["id"]),
            )

    def test_render_activation_wraps_package_with_agent_instructions(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            package = load_json(
                ROOT / "examples" / "laura-southern-abrasives-opportunity-context-package.json"
            )
            stores.context_packages.create(package)
            activation = self._activate(directory, package["id"])

            rendered = StringIO()
            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "render-activation",
                    activation["id"],
                ],
                stdout=rendered,
            )

            self.assertEqual(0, code)
            text = rendered.getvalue()
            self.assertIn("State System Agent Activation", text)
            self.assertIn("Activation:", text)
            self.assertIn("Expected response type: proposal", text)
            self.assertIn("Allowed action refs:", text)
            self.assertIn("Prohibited action refs:", text)
            self.assertIn("action.laura.southern-abrasives-linkedin-publish", text)
            self.assertIn("State System Agent Package", text)
            self.assertIn("Requires refresh before external action.", text)

    def test_trace_run_can_create_activation_and_capture_linked_response(self):
        with TemporaryDirectory() as directory:
            output = StringIO()

            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "trace-run",
                    str(ROOT / "examples" / "traces" / "laura-agent-activation.trace.json"),
                    "--output-dir",
                    directory,
                ],
                stdout=output,
            )

            self.assertEqual(0, code, output.getvalue())
            report = json.loads(output.getvalue())
            self.assertEqual("passed", report["status"])
            self.assertEqual(
                "trace.laura-agent-activation",
                report["trace_id"],
            )
            self.assertEqual(
                "activation.context.laura.southern-abrasives-won-opportunity.consumer.codex.20260503T100000Z",
                report["validated"]["agent_activation_id"],
            )
            activation = load_json(Path(directory) / "02-agent-activation.json")
            response = load_json(Path(directory) / "04-agent-response.json")
            self.assertEqual(activation["id"], response["activation_id"])
            self.assertIn(activation["id"], response["evidence_refs"])

    def _activate(self, state_root: str, package_id: str):
        output = StringIO()
        code = cli.main(
            [
                "--project-root",
                str(ROOT),
                "--state-root",
                state_root,
                "activate-agent",
                package_id,
                "--consumer",
                "consumer.codex",
                "--created-at",
                "2026-05-03T10:00:00Z",
                "--activation-goal",
                "Draft internal material and identify what requires approval.",
                "--expected-response-type",
                "proposal",
            ],
            stdout=output,
        )
        self.assertEqual(0, code, output.getvalue())
        return json.loads(output.getvalue())


if __name__ == "__main__":
    unittest.main()
