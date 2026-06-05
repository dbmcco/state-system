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
                "company-sampleco.json",
                "company-researchco.json",
                "company-portfolio-co.json",
            },
            {result.path.name for result in pack_results},
        )
        self.assertEqual([], [result for result in pack_results if not result.ok])

    def test_packs_preserve_runtime_and_governance_boundary(self):
        sampleco_inst = load_json(PACK_DIR / "company-sampleco.json")
        researchco = load_json(PACK_DIR / "company-researchco.json")
        portfolio_co = load_json(PACK_DIR / "company-portfolio-co.json")

        for pack in (sampleco_inst, researchco, portfolio_co):
            invariant = pack["invariant"]
            self.assertFalse(invariant["proves_live_access"])
            self.assertFalse(invariant["authorizes_execution"])
            self.assertEqual("agent_runtime_connector_preflight", invariant["live_access_proven_by"])
            self.assertEqual("governance", invariant["protected_action_authorized_by"])
            self.assertIn("runtime_constraints", pack)
            self.assertIn("governance", pack)

        self.assertTrue(
            any(connector["connector_type"] == "linear" for connector in sampleco_inst["source_connectors"])
        )
        self.assertFalse(
            any(connector["connector_type"] == "linear" for connector in researchco["source_connectors"])
        )
        self.assertFalse(
            any(connector["connector_type"] == "linear" for connector in portfolio_co["source_connectors"])
        )

    def test_tool_capability_bindings_reference_declared_pack_parts(self):
        for path in sorted(PACK_DIR.glob("company-*.json")):
            pack = load_json(path)
            connector_refs = {connector["id"] for connector in pack["source_connectors"]}
            action_refs = set(pack["action_surface"]["action_refs"])
            governance_refs = set(pack["governance"]["governance_refs"])
            preflight_refs = {
                check["id"]
                for check in pack["connector_preflight"]["required_checks"]
            }

            for binding in pack["tool_capability_bindings"]:
                self.assertIn(binding["action_ref"], action_refs)
                self.assertLessEqual(set(binding["connector_refs"]), connector_refs)
                self.assertLessEqual(set(binding["required_preflight_refs"]), preflight_refs)
                self.assertLessEqual(set(binding["governance_refs"]), governance_refs)
                self.assertFalse(binding["proves_live_access"])
                self.assertFalse(binding["authorizes_execution"])

    def test_index_manifests_reference_declared_pack_parts(self):
        for path in sorted(PACK_DIR.glob("company-*.json")):
            pack = load_json(path)
            connector_refs = {connector["id"] for connector in pack["source_connectors"]}
            source_refs = set(pack["raw_corpus"]["source_refs"])

            self.assertTrue(pack["index_manifests"], path)
            for manifest in pack["index_manifests"]:
                self.assertEqual(pack["company_ref"], manifest["company_ref"])
                self.assertIn(manifest["status"], {"declared", "planned", "disabled"})
                self.assertIn(
                    manifest["scope"],
                    {"raw_source_index", "interpreted_state_index", "company_memory_index"},
                )
                self.assertTrue(manifest["record_kinds"])
                self.assertTrue(manifest["query_surface"]["type"])
                self.assertLessEqual(set(manifest["connector_refs"]), connector_refs)
                non_state_sources = [
                    source_ref
                    for source_ref in manifest["source_refs"]
                    if not source_ref.startswith("state-system:")
                ]
                self.assertLessEqual(set(non_state_sources), source_refs)

    def test_gws_drive_source_refs_include_profile_and_resource_kind(self):
        for path in sorted(PACK_DIR.glob("company-*.json")):
            pack = load_json(path)
            for connector in pack["source_connectors"]:
                if connector["connector_type"] != "gws_drive":
                    continue

                source_ref_parts = connector["source_ref"].split(":", 3)
                self.assertEqual(4, len(source_ref_parts), connector)
                system, profile, resource_kind, lookup_key = source_ref_parts
                self.assertEqual("gws", system)
                self.assertIn(profile, {"sampleco", "example", "demo"})
                self.assertIn(resource_kind, {"drive", "shared-drive"})
                self.assertTrue(lookup_key)

    def test_msgvault_connectors_declare_explicit_preflight_targets(self):
        for path in sorted(PACK_DIR.glob("company-*.json")):
            pack = load_json(path)
            for connector in pack["source_connectors"]:
                if connector["connector_type"] != "msgvault":
                    continue

                source_ref_parts = connector["source_ref"].split(":", 2)
                self.assertEqual(["msgvault", "tenant"], source_ref_parts[:2])
                self.assertTrue(source_ref_parts[2])

                target = connector["preflight_target"]
                self.assertEqual("msgvault_search", target["kind"])
                self.assertTrue(target["query"])
                self.assertGreaterEqual(target["limit"], 1)
                if "account_ref" in target:
                    self.assertTrue(
                        target["account_ref"].startswith("msgvault:account:"),
                        target,
                    )

    def test_read_model_rolls_up_company_capability_packs(self):
        read_model = build_company_capability_read_model(
            [
                load_json(PACK_DIR / "company-sampleco.json"),
                load_json(PACK_DIR / "company-researchco.json"),
                load_json(PACK_DIR / "company-portfolio-co.json"),
            ]
        )

        self.assertEqual("company_capability_read_model", read_model["id"])
        self.assertEqual("json_substrate", read_model["artifact_type"])
        self.assertEqual(
            ["company.portfolio_co", "company.researchco", "company.sampleco"],
            [company["company_ref"] for company in read_model["companies"]],
        )
        sampleco_inst = _company(read_model, "company.sampleco")
        researchco = _company(read_model, "company.researchco")
        portfolio_co = _company(read_model, "company.portfolio_co")

        self.assertIn("company_memory.sampleco", sampleco_inst["company_memory_refs"])
        self.assertIn("operating_picture.crm.sampleco", sampleco_inst["operating_picture_refs"])
        self.assertIn("operating_picture.finance.researchco", researchco["operating_picture_refs"])
        self.assertIn("operating_picture.regulatory.portfolio_co", portfolio_co["operating_picture_refs"])
        self.assertIn("kb:tenant:sampleco", read_model["source_refs"])
        self.assertIn("gws:example:shared-drive:demo-co", read_model["source_refs"])
        self.assertIn("index.sampleco.kb.corpus", read_model["index_refs"])
        self.assertIn("index.sampleco.state_system.evidence_cards", read_model["index_refs"])

        sampleco_ks = _connector(sampleco_inst, "connector.sampleco.kb")
        self.assertEqual("kb", sampleco_ks["connector_type"])
        self.assertEqual("kb:tenant:sampleco", sampleco_ks["source_ref"])
        self.assertEqual("source_system", sampleco_ks["owner"])
        sampleco_ks_index = _index_manifest(sampleco_inst, "index.sampleco.kb.corpus")
        self.assertEqual("postgres_pgvector", sampleco_ks_index["backend"])
        self.assertEqual("raw_source_index", sampleco_ks_index["scope"])
        self.assertEqual("declared", sampleco_ks_index["status"])
        self.assertEqual(
            {"type": "agent_runtime_tool", "tool_ref": "tool.agent_runtime.kb.search"},
            sampleco_ks_index["query_surface"],
        )
        sampleco_state_index = _index_manifest(sampleco_inst, "index.sampleco.state_system.evidence_cards")
        self.assertEqual("state_system", sampleco_state_index["owner"])
        self.assertEqual("interpreted_state_index", sampleco_state_index["scope"])
        self.assertEqual("state_system_interpreted_index", sampleco_state_index["backend"])
        self.assertEqual("declared", sampleco_state_index["status"])
        self.assertEqual(
            {
                "type": "state_system_runtime",
                "tool_ref": "tool.state_system.interpreted_search",
            },
            sampleco_state_index["query_surface"],
        )
        sampleco_understanding_index = _index_manifest(
            sampleco_inst,
            "index.sampleco.state_system.company_understanding_surface",
        )
        self.assertEqual("state_system", sampleco_understanding_index["owner"])
        self.assertEqual("json_read_model", sampleco_understanding_index["backend"])
        self.assertEqual("interpreted_state_index", sampleco_understanding_index["scope"])
        self.assertEqual("declared", sampleco_understanding_index["status"])
        self.assertEqual(
            {
                "type": "state_system_runtime",
                "tool_ref": "tool.state_system.company_understanding_read",
            },
            sampleco_understanding_index["query_surface"],
        )
        sampleco_github_index = _index_manifest(sampleco_inst, "index.sampleco.github_org.repos")
        self.assertEqual("github_native", sampleco_github_index["backend"])
        self.assertEqual("raw_source_index", sampleco_github_index["scope"])
        self.assertEqual("declared", sampleco_github_index["status"])
        sampleco_local_index = _index_manifest(sampleco_inst, "index.sampleco.local.workspace")
        self.assertEqual("local_filesystem", sampleco_local_index["backend"])
        self.assertEqual("raw_source_index", sampleco_local_index["scope"])
        self.assertEqual("declared", sampleco_local_index["status"])
        self.assertEqual(["connector.sampleco.local"], sampleco_local_index["connector_refs"])
        sampleco_transcript_index = _index_manifest(sampleco_inst, "index.sampleco.transcripts.processed")
        self.assertEqual("planned", sampleco_transcript_index["status"])
        self.assertIn("Placeholder only", sampleco_transcript_index["notes"])

    def test_read_model_exposes_mechanical_tool_capability_bindings(self):
        read_model = build_company_capability_read_model(
            [
                load_json(PACK_DIR / "company-sampleco.json"),
                load_json(PACK_DIR / "company-researchco.json"),
                load_json(PACK_DIR / "company-portfolio-co.json"),
            ]
        )

        sampleco_inst = _company(read_model, "company.sampleco")
        binding = _binding(sampleco_inst, "capability.sampleco.linear.read")

        self.assertEqual("tool.agent_runtime.linear.read", binding["tool_ref"])
        self.assertEqual("action_surface.sampleco.read_linear", binding["action_ref"])
        self.assertEqual(["connector.sampleco.linear"], binding["connector_refs"])
        self.assertEqual(["preflight.sampleco.linear"], binding["required_preflight_refs"])
        self.assertEqual([], binding["governance_refs"])
        self.assertEqual(["persona.iris", "persona.nova"], binding["allowed_agent_refs"])
        self.assertEqual("hide_until_preflight_passes", binding["exposure_policy"])
        self.assertFalse(binding["proves_live_access"])
        self.assertFalse(binding["authorizes_execution"])

        zulip_binding = _binding(sampleco_inst, "capability.sampleco.zulip.read")
        self.assertEqual("tool.agent_runtime.zulip.read", zulip_binding["tool_ref"])
        self.assertEqual("action_surface.sampleco.read_zulip", zulip_binding["action_ref"])
        self.assertEqual(["connector.sampleco.zulip"], zulip_binding["connector_refs"])
        self.assertEqual(["preflight.sampleco.zulip"], zulip_binding["required_preflight_refs"])
        self.assertEqual([], zulip_binding["governance_refs"])
        self.assertEqual(
            ["persona.iris", "persona.nova"],
            zulip_binding["allowed_agent_refs"],
        )
        self.assertFalse(zulip_binding["proves_live_access"])
        self.assertFalse(zulip_binding["authorizes_execution"])

        github_binding = _binding(sampleco_inst, "capability.sampleco.github.read")
        self.assertEqual("tool.agent_runtime.github.read", github_binding["tool_ref"])
        self.assertEqual("action_surface.sampleco.read_github", github_binding["action_ref"])
        self.assertEqual(["connector.sampleco.github_org"], github_binding["connector_refs"])
        self.assertEqual(["preflight.sampleco.github"], github_binding["required_preflight_refs"])
        self.assertEqual([], github_binding["governance_refs"])
        self.assertEqual(
            ["persona.iris", "persona.nova"],
            github_binding["allowed_agent_refs"],
        )
        self.assertFalse(github_binding["proves_live_access"])
        self.assertFalse(github_binding["authorizes_execution"])

        local_binding = _binding(sampleco_inst, "capability.sampleco.local.inspect")
        self.assertEqual("tool.agent_runtime.local_path.inspect", local_binding["tool_ref"])
        self.assertEqual(
            "action_surface.sampleco.inspect_local_workspace",
            local_binding["action_ref"],
        )
        self.assertEqual(["connector.sampleco.local"], local_binding["connector_refs"])
        self.assertEqual(["preflight.sampleco.local"], local_binding["required_preflight_refs"])
        self.assertEqual([], local_binding["governance_refs"])
        self.assertEqual(
            ["persona.iris", "persona.nova"],
            local_binding["allowed_agent_refs"],
        )
        self.assertFalse(local_binding["proves_live_access"])
        self.assertFalse(local_binding["authorizes_execution"])

        researchco = _company(read_model, "company.researchco")
        self.assertFalse(
            any(
                "linear" in binding["tool_ref"]
                for binding in researchco["tool_capability_bindings"]
            )
        )

    def test_cli_writes_company_capability_read_model(self):
        with TemporaryDirectory() as directory:
            output = StringIO()
            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "company-capability-build",
                    str(PACK_DIR / "company-sampleco.json"),
                    str(PACK_DIR / "company-researchco.json"),
                    str(PACK_DIR / "company-portfolio-co.json"),
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


def _binding(company, capability_ref):
    return next(
        binding
        for binding in company["tool_capability_bindings"]
        if binding["capability_ref"] == capability_ref
    )


def _connector(company, connector_ref):
    return next(
        connector
        for connector in company["source_connectors"]
        if connector["id"] == connector_ref
    )


def _index_manifest(company, index_ref):
    return next(
        manifest
        for manifest in company["index_manifests"]
        if manifest["index_ref"] == index_ref
    )


if __name__ == "__main__":
    unittest.main()
