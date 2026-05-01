from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.agent_consumers import (
    capture_agent_response,
    render_package_for_agent,
)
from state_system.contracts import load_json, validate_schema
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]


class AgentConsumerContractTests(unittest.TestCase):
    def test_render_package_for_agent_is_free_text_with_evidence_and_guardrails(self):
        package = load_json(
            ROOT / "examples" / "laura-southern-abrasives-opportunity-context-package.json"
        )

        text = render_package_for_agent(package)

        self.assertIn("State System Agent Package", text)
        self.assertIn("Package: context.laura.southern-abrasives-won-opportunity", text)
        self.assertIn("Persona: persona.laura", text)
        self.assertIn("Review goal:", text)
        self.assertIn("Southern Abrasives moved from proposal to won", text)
        self.assertIn("Why relevant:", text)
        self.assertIn("state.lfw.deal.southern-abrasives", text)
        self.assertIn("linear:event:southern-abrasives-stage-won-2026-04-28", text)
        self.assertIn("governance.external-copy-approval", text)
        self.assertIn("Requires refresh before external action.", text)
        self.assertIn("Excluded context:", text)
        self.assertIn("Available actions:", text)
        self.assertIn("Do not:", text)

    def test_capture_agent_response_persists_raw_text_and_package_evidence(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            package = load_json(
                ROOT / "examples" / "laura-southern-abrasives-opportunity-context-package.json"
            )
            stores.context_packages.create(package)
            schemas = {
                "agent_response": load_json(
                    ROOT / "schemas" / "agent-response.schema.json"
                )
            }
            response_text = (
                "Laura would draft an internal proof-point note, but she would not "
                "publish externally until approval and public naming permission exist."
            )

            record = capture_agent_response(
                stores,
                schemas,
                package_id=package["id"],
                consumer_ref="consumer.codex",
                response_text=response_text,
                created_at="2026-05-01T20:30:00Z",
            )

            self.assertEqual(
                "response.context.laura.southern-abrasives-won-opportunity.consumer.codex.20260501T203000Z",
                record["id"],
            )
            self.assertEqual(package["id"], record["package_id"])
            self.assertEqual("consumer.codex", record["consumer_ref"])
            self.assertEqual(response_text, record["response_text"])
            self.assertEqual("captured", record["status"])
            self.assertIn(package["id"], record["evidence_refs"])
            self.assertIn(
                "linear:event:southern-abrasives-stage-won-2026-04-28",
                record["evidence_refs"],
            )
            self.assertEqual(record, stores.agent_responses.read(record["id"]))
            self.assertEqual([], validate_schema(record, schemas["agent_response"]))

    def test_cli_renders_package_and_captures_response(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            package = load_json(
                ROOT / "examples" / "laura-southern-abrasives-opportunity-context-package.json"
            )
            stores.context_packages.create(package)

            rendered = StringIO()
            render_code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "render-package",
                    package["id"],
                ],
                stdout=rendered,
            )

            self.assertEqual(0, render_code)
            self.assertIn("State System Agent Package", rendered.getvalue())
            self.assertIn("Persona: persona.laura", rendered.getvalue())

            response_path = Path(directory) / "response.txt"
            response_path.write_text(
                "Draft internally. Hold external publication for approval.\n",
                encoding="utf-8",
            )
            captured = StringIO()
            capture_code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "capture-response",
                    package["id"],
                    str(response_path),
                    "--consumer",
                    "consumer.codex",
                    "--created-at",
                    "2026-05-01T20:31:00Z",
                ],
                stdout=captured,
            )

            self.assertEqual(0, capture_code)
            payload = json.loads(captured.getvalue())
            self.assertEqual("consumer.codex", payload["consumer_ref"])
            self.assertEqual(
                "Draft internally. Hold external publication for approval.\n",
                payload["response_text"],
            )
            self.assertEqual([payload["id"]], stores.agent_responses.list_ids())


if __name__ == "__main__":
    unittest.main()
