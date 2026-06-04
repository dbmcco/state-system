from __future__ import annotations

from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from jsonschema import Draft202012Validator

from state_system import cli
from state_system.contracts import load_json
from state_system.instance_scaffold import scaffold_state_instance


ROOT = Path(__file__).resolve().parents[1]


class InstanceScaffoldTests(unittest.TestCase):
    def test_scaffold_creates_state_instance_and_module_registry_subset(self):
        with TemporaryDirectory() as directory:
            runtime_root = Path(directory) / "portfolio_co-state-system"

            result = scaffold_state_instance(
                project_root=ROOT,
                runtime_root=runtime_root,
                instance_ref="state_instance.portfolio_co",
                kind="company",
                display_name="PortfolioCo State",
                primary_entity_ref="entity.portfolio_co",
                entity_kind="company",
                created_at="2026-05-18T17:20:00Z",
                governance_refs=["governance.portfolio_co.default"],
                connector_types=["folio", "gws_drive", "msgvault", "local_path"],
            )

            self.assertTrue(result["ok"])
            instance_path = Path(result["instance_path"])
            registry_path = Path(result["module_registry_path"])
            self.assertTrue(instance_path.exists())
            self.assertTrue(registry_path.exists())

            instance = json.loads(instance_path.read_text(encoding="utf-8"))
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            self.assertEqual("state_instance.portfolio_co", instance["instance_ref"])
            self.assertEqual(
                {"folio", "gws_drive", "msgvault", "local_path"},
                {module["connector_type"] for module in registry["modules"]},
            )

            schema = load_json(ROOT / "schemas/source-module-spec.schema.json")
            errors = sorted(Draft202012Validator(schema).iter_errors(registry), key=str)
            self.assertEqual([], [error.message for error in errors])

    def test_cli_scaffolds_instance(self):
        with TemporaryDirectory() as directory:
            output = StringIO()
            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "instance-scaffold",
                    "--runtime-root",
                    str(Path(directory) / "researchco-state-system"),
                    "--instance-ref",
                    "state_instance.researchco",
                    "--kind",
                    "company",
                    "--display-name",
                    "ResearchCo State",
                    "--primary-entity-ref",
                    "entity.researchco",
                    "--entity-kind",
                    "company",
                    "--created-at",
                    "2026-05-18T17:20:00Z",
                    "--governance-ref",
                    "governance.researchco.default",
                    "--connector-type",
                    "folio",
                    "--connector-type",
                    "local_path",
                ],
                stdout=output,
            )

            self.assertEqual(0, code, output.getvalue())
            payload = json.loads(output.getvalue())
            self.assertTrue(Path(payload["instance_path"]).exists())
            self.assertTrue(Path(payload["module_registry_path"]).exists())


if __name__ == "__main__":
    unittest.main()
