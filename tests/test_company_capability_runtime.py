from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.company_capability import (
    CompanyCapabilityRuntime,
    build_company_capability_read_model_from_runtime,
)
from state_system.contracts import load_json
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = ROOT / "examples" / "company-capability"


class CompanyCapabilityRuntimeTests(unittest.TestCase):
    def test_seed_persists_company_capability_packs_in_runtime_state_root(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            runtime = CompanyCapabilityRuntime(stores)

            result = runtime.seed(
                [
                    load_json(PACK_DIR / "company-sampleco.json"),
                    load_json(PACK_DIR / "company-researchco.json"),
                    load_json(PACK_DIR / "company-portfolio-co.json"),
                ]
            )

            self.assertEqual(3, len(result["seeded"]))
            self.assertEqual(
                ["company.portfolio_co", "company.researchco", "company.sampleco"],
                [pack["company_ref"] for pack in runtime.list_packs()],
            )
            sampleco_inst = runtime.read("company_capability_pack.sampleco")
            self.assertEqual("company.sampleco", sampleco_inst["company_ref"])
            self.assertFalse(sampleco_inst["invariant"]["proves_live_access"])
            self.assertFalse(sampleco_inst["invariant"]["authorizes_execution"])

    def test_seed_is_idempotent_and_updates_existing_runtime_record(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            runtime = CompanyCapabilityRuntime(stores)
            sampleco_inst = load_json(PACK_DIR / "company-sampleco.json")
            runtime.seed([sampleco_inst])

            updated_sampleco = {**sampleco_inst, "generated_at": "2026-05-14T18:00:00Z"}
            updated_sampleco["identity"] = {
                **sampleco_inst["identity"],
                "summary": "Updated runtime declaration for SampleCo.",
            }
            result = runtime.seed([updated_sampleco])

            self.assertEqual(["company_capability_pack.sampleco"], result["updated"])
            self.assertEqual([], result["created"])
            self.assertEqual(
                "Updated runtime declaration for SampleCo.",
                runtime.read("company_capability_pack.sampleco")["identity"]["summary"],
            )

    def test_read_model_builds_from_runtime_without_example_inputs(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            runtime = CompanyCapabilityRuntime(stores)
            runtime.seed(
                [
                    load_json(PACK_DIR / "company-sampleco.json"),
                    load_json(PACK_DIR / "company-researchco.json"),
                    load_json(PACK_DIR / "company-portfolio-co.json"),
                ]
            )

            read_model = build_company_capability_read_model_from_runtime(stores)

            self.assertEqual("company_capability_read_model", read_model["id"])
            self.assertEqual(
                ["company.portfolio_co", "company.researchco", "company.sampleco"],
                [company["company_ref"] for company in read_model["companies"]],
            )
            self.assertFalse(
                read_model["invariant"]["company_capability_pack_proves_live_access"]
            )
            self.assertIn(
                "company_memory.researchco",
                _company(read_model, "company.researchco")["company_memory_refs"],
            )
            self.assertIn(
                "index.researchco.state_system.evidence_cards",
                read_model["index_refs"],
            )
            self.assertEqual(
                "planned",
                next(
                    manifest
                    for manifest in _company(read_model, "company.researchco")[
                        "index_manifests"
                    ]
                    if manifest["index_ref"]
                    == "index.researchco.state_system.evidence_cards"
                )["status"],
            )
            self.assertIn(
                "tool.paia.gws_drive.read",
                [
                    binding["tool_ref"]
                    for binding in _company(read_model, "company.portfolio_co")[
                        "tool_capability_bindings"
                    ]
                ],
            )
            portfolio_co_connectors = _company(read_model, "company.portfolio_co")[
                "source_connectors"
            ]
            self.assertIn(
                {
                    "id": "connector.portfolio_co.folio",
                    "connector_type": "folio",
                    "source_ref": "folio:tenant:portfolio_co",
                    "owner": "source_system",
                    "declared": True,
                },
                portfolio_co_connectors,
            )

    def test_cli_seeds_and_reads_company_capability_from_state_root(self):
        with TemporaryDirectory() as directory, TemporaryDirectory() as output_dir:
            seed_output = StringIO()
            seed_code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "company-capability-seed",
                    str(PACK_DIR / "company-sampleco.json"),
                    str(PACK_DIR / "company-researchco.json"),
                    str(PACK_DIR / "company-portfolio-co.json"),
                ],
                stdout=seed_output,
            )

            self.assertEqual(0, seed_code, seed_output.getvalue())
            seed_payload = json.loads(seed_output.getvalue())
            self.assertEqual(3, len(seed_payload["seeded"]))

            read_output = StringIO()
            read_code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "company-capability-read",
                    "--output-dir",
                    output_dir,
                ],
                stdout=read_output,
            )

            self.assertEqual(0, read_code, read_output.getvalue())
            payload = json.loads(read_output.getvalue())
            read_model_path = Path(payload["read_model_path"])
            self.assertEqual("company-capability-read-model.json", read_model_path.name)
            read_model = json.loads(read_model_path.read_text(encoding="utf-8"))
            self.assertEqual(3, len(read_model["companies"]))
            self.assertIn("folio:tenant:sampleco", read_model["source_refs"])
            self.assertIn("index.sampleco.folio.corpus", read_model["index_refs"])


def _company(read_model, company_ref):
    return next(
        company for company in read_model["companies"] if company["company_ref"] == company_ref
    )


if __name__ == "__main__":
    unittest.main()
