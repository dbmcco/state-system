from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.company_memory import (
    build_agent_context_packages,
    build_company_memory_read_model,
)
from state_system.contracts import load_json, validate_all_examples


ROOT = Path(__file__).resolve().parents[1]
COMPANY_FIXTURE = ROOT / "examples" / "company-memory" / "lfw-company-memory.json"
CRM_FIXTURE = ROOT / "examples" / "company-memory" / "lfw-crm-operating-picture.json"


class CompanyMemoryTests(unittest.TestCase):
    def test_company_memory_examples_validate(self):
        results = validate_all_examples(ROOT)
        company_results = [
            result
            for result in results
            if "company-memory" in result.path.parts and result.path.suffix == ".json"
        ]

        self.assertGreaterEqual(len(company_results), 4)
        self.assertEqual([], [result for result in company_results if not result.ok])

    def test_read_model_preserves_crm_as_source_of_record(self):
        read_model = build_company_memory_read_model(
            load_json(COMPANY_FIXTURE),
            load_json(CRM_FIXTURE),
        )

        self.assertEqual("company_memory_read_model.lfw", read_model["id"])
        self.assertEqual("json_substrate", read_model["artifact_type"])
        self.assertEqual("lfw_ai_graph_crm", read_model["crm"]["system_of_record_ref"])
        self.assertEqual("state_system_interpretation", read_model["crm"]["state_system_role"])
        self.assertGreaterEqual(len(read_model["crm"]["relationships"]), 2)
        self.assertGreaterEqual(len(read_model["crm"]["opportunities"]), 1)
        self.assertIn("crm:relationship:southern-abrasives", read_model["evidence_refs"])
        self.assertNotIn("html", json.dumps(read_model).lower())

    def test_agent_context_packages_slice_same_substrate_differently(self):
        read_model = build_company_memory_read_model(
            load_json(COMPANY_FIXTURE),
            load_json(CRM_FIXTURE),
        )
        packages = build_agent_context_packages(read_model)

        laura = packages["persona.laura.marketing"]
        patrick = packages["persona.patrick.operations"]

        self.assertEqual(read_model["id"], laura["source_read_model_ref"])
        self.assertEqual(read_model["id"], patrick["source_read_model_ref"])
        self.assertIn("marketable proof", laura["review_goal"])
        self.assertIn("open loops", patrick["review_goal"])
        self.assertIn("relationship_story", laura["included_slices"])
        self.assertIn("crm_open_loop", patrick["included_slices"])
        self.assertNotEqual(laura["included_slices"], patrick["included_slices"])

    def test_cli_writes_json_read_model(self):
        with TemporaryDirectory() as directory:
            output = StringIO()
            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "company-memory-build",
                    str(COMPANY_FIXTURE),
                    str(CRM_FIXTURE),
                    "--output-dir",
                    directory,
                ],
                stdout=output,
            )

            self.assertEqual(0, code)
            payload = json.loads(output.getvalue())
            read_model_path = Path(payload["read_model_path"])
            self.assertTrue(read_model_path.exists())
            self.assertEqual("company-memory-read-model.json", read_model_path.name)
            read_model = json.loads(read_model_path.read_text(encoding="utf-8"))
            self.assertEqual("company_memory_read_model.lfw", read_model["id"])


if __name__ == "__main__":
    unittest.main()
