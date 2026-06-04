from __future__ import annotations

import io
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from state_system.cli import main
from state_system.contracts import load_json, validate_all_examples
from state_system.instance_federation_packs import (
    InstanceFederationPackValidationError,
    render_instance_federation_pack_registry,
    validate_instance_federation_pack_registry,
)


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = (
    ROOT
    / "examples"
    / "instance-federation-packs"
    / "instance-federation-pack-core-examples.json"
)


class InstanceFederationPackTests(unittest.TestCase):
    def test_registry_example_validates(self):
        schema = load_json(ROOT / "schemas" / "instance-federation-pack.schema.json")
        registry = load_json(REGISTRY)
        errors = sorted(Draft202012Validator(schema).iter_errors(registry), key=str)

        self.assertEqual([], [error.message for error in errors])

    def test_validate_all_examples_includes_registry(self):
        results = validate_all_examples(ROOT)
        federation_results = [
            result
            for result in results
            if "instance-federation-packs" in result.path.parts
        ]

        self.assertEqual(
            ["instance-federation-pack-core-examples.json"],
            [result.path.name for result in federation_results],
        )
        self.assertEqual([], [result for result in federation_results if not result.ok])

    def test_examples_cover_required_federation_shapes(self):
        packs = _packs_by_id(load_json(REGISTRY))

        self.assertEqual(
            "instance_read",
            packs["instance_federation_pack.personal_to_sampleco_state"]["federation_mode"],
        )
        self.assertEqual(
            "source_substrate_query",
            packs[
                "instance_federation_pack.sampleco_to_personal_relationship_substrate"
            ]["federation_mode"],
        )
        self.assertEqual(
            "portfolio_rollup",
            packs["instance_federation_pack.portfolio_to_portfolio_co_researchco"][
                "federation_mode"
            ],
        )
        self.assertEqual(
            ["state_instance.portfolio_co", "state_instance.researchco"],
            packs["instance_federation_pack.portfolio_to_portfolio_co_researchco"][
                "remote_instance_refs"
            ],
        )

    def test_no_pack_materializes_raw_remote_data_by_default(self):
        registry = load_json(REGISTRY)
        schema = load_json(ROOT / "schemas" / "instance-federation-pack.schema.json")
        validate_instance_federation_pack_registry(registry, schema)

        for pack in registry["packs"]:
            with self.subTest(pack=pack["id"]):
                self.assertFalse(pack["materialization_policy"]["local_materialization"])
                self.assertNotIn(
                    "raw_corpus",
                    pack["materialization_policy"]["allowed_artifact_types"],
                )
                self.assertTrue(pack["invariant"]["pack_does_not_copy_raw_remote_data"])

    def test_semantic_validation_rejects_raw_materialization(self):
        registry = load_json(REGISTRY)
        schema = load_json(ROOT / "schemas" / "instance-federation-pack.schema.json")
        registry["packs"][0]["materialization_policy"]["local_materialization"] = True
        registry["packs"][0]["materialization_policy"]["allowed_artifact_types"].append(
            "raw_corpus"
        )

        with self.assertRaises(InstanceFederationPackValidationError) as raised:
            validate_instance_federation_pack_registry(registry, schema)

        self.assertIn("raw remote corpus cannot be materialized", raised.exception.errors[0])

    def test_renderer_surfaces_boundaries_and_gap_policy(self):
        rendered = render_instance_federation_pack_registry(load_json(REGISTRY))

        self.assertIn("instance_federation_pack.sampleco_to_personal_relationship_substrate", rendered)
        self.assertIn("Local materialization: False", rendered)
        self.assertIn("No raw personal relationship records may be copied", rendered)
        self.assertIn("gap.state_instance.portfolio_co.package_readiness_unproved", rendered)

    def test_cli_validate_and_render(self):
        validate_output = io.StringIO()
        validate_exit = main(
            [
                "--project-root",
                str(ROOT),
                "instance-federation-pack-validate",
                str(REGISTRY),
            ],
            stdout=validate_output,
        )
        render_output = io.StringIO()
        render_exit = main(
            [
                "--project-root",
                str(ROOT),
                "instance-federation-pack-render",
                str(REGISTRY),
            ],
            stdout=render_output,
        )

        self.assertEqual(0, validate_exit)
        self.assertIn('"ok": true', validate_output.getvalue())
        self.assertEqual(0, render_exit)
        self.assertIn("State System Instance Federation Packs", render_output.getvalue())


def _packs_by_id(registry: dict) -> dict[str, dict]:
    return {pack["id"]: pack for pack in registry["packs"]}


if __name__ == "__main__":
    unittest.main()
