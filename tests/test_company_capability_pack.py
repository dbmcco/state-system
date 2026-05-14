from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.company_capability import build_company_capability_read_model
from state_system.contracts import load_json, validate_all_examples


ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = ROOT / "examples" / "company-capability"


class CompanyCapabilityPackTests(unittest.TestCase):
    def test_company_capability_fixtures_validate(self):
        results = validate_all_examples(ROOT)
        pack_results = [
            result
            for result in results
            if "company-capability" in result.path.parts and result.path.suffix == ".json"
        ]

        self.assertEqual(
            {
                "company-lfw.json",
                "company-synthyra.json",
                "company-navicyte.json",
            },
            {result.path.name for result in pack_results},
        )
        self.assertEqual([], [result for result in pack_results if not result.ok])

    def test_packs_preserve_runtime_and_governance_boundary(self):
        lfw = load_json(PACK_DIR / "company-lfw.json")
        synthyra = load_json(PACK_DIR / "company-synthyra.json")
        navicyte = load_json(PACK_DIR / "company-navicyte.json")

        for pack in (lfw, synthyra, navicyte):
            invariant = pack["invariant"]
            self.assertFalse(invariant["proves_live_access"])
            self.assertFalse(invariant["authorizes_execution"])
            self.assertEqual("paia_connector_preflight", invariant["live_access_proven_by"])
            self.assertEqual("governance", invariant["protected_action_authorized_by"])
            self.assertIn("runtime_constraints", pack)
            self.assertIn("governance", pack)

        self.assertTrue(
            any(connector["connector_type"] == "linear" for connector in lfw["source_connectors"])
        )
        self.assertFalse(
            any(connector["connector_type"] == "linear" for connector in synthyra["source_connectors"])
        )
        self.assertFalse(
            any(connector["connector_type"] == "linear" for connector in navicyte["source_connectors"])
        )

    def test_read_model_rolls_up_company_capability_packs(self):
        read_model = build_company_capability_read_model(
            [
                load_json(PACK_DIR / "company-lfw.json"),
                load_json(PACK_DIR / "company-synthyra.json"),
                load_json(PACK_DIR / "company-navicyte.json"),
            ]
        )

        self.assertEqual("company_capability_read_model", read_model["id"])
        self.assertEqual("json_substrate", read_model["artifact_type"])
        self.assertEqual(
            ["company.lfw", "company.navicyte", "company.synthyra"],
            [company["company_ref"] for company in read_model["companies"]],
        )
        lfw = _company(read_model, "company.lfw")
        synthyra = _company(read_model, "company.synthyra")
        navicyte = _company(read_model, "company.navicyte")

        self.assertIn("company_memory.lfw", lfw["company_memory_refs"])
        self.assertIn("operating_picture.crm.lfw", lfw["operating_picture_refs"])
        self.assertIn("operating_picture.finance.synthyra", synthyra["operating_picture_refs"])
        self.assertIn("operating_picture.regulatory.navicyte", navicyte["operating_picture_refs"])
        self.assertIn("folio:tenant:lfw", read_model["source_refs"])
        self.assertIn("gws:mcco:shared-drive:navicyte-biotechnologies", read_model["source_refs"])

    def test_cli_writes_company_capability_read_model(self):
        with TemporaryDirectory() as directory:
            output = StringIO()
            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "company-capability-build",
                    str(PACK_DIR / "company-lfw.json"),
                    str(PACK_DIR / "company-synthyra.json"),
                    str(PACK_DIR / "company-navicyte.json"),
                    "--output-dir",
                    directory,
                ],
                stdout=output,
            )

            self.assertEqual(0, code, output.getvalue())
            payload = json.loads(output.getvalue())
            read_model_path = Path(payload["read_model_path"])
            self.assertEqual("company-capability-read-model.json", read_model_path.name)
            self.assertTrue(read_model_path.exists())
            read_model = json.loads(read_model_path.read_text(encoding="utf-8"))
            self.assertEqual(3, len(read_model["companies"]))


def _company(read_model, company_ref):
    return next(
        company for company in read_model["companies"] if company["company_ref"] == company_ref
    )


if __name__ == "__main__":
    unittest.main()
