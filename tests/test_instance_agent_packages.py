from __future__ import annotations

from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.agent_consumers import render_package_for_agent
from state_system.contracts import load_json, validate_schema
from state_system.instance_agent_packages import InstanceAgentPackageRuntime
from state_system.instance_capability import InstanceCapabilityRuntime
from state_system.instance_preflight import InstancePreflightRuntime
from state_system.instance_source_freshness import InstanceSourceFreshnessRuntime
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = ROOT / "examples" / "instance-capability"


class InstanceAgentPackageTests(unittest.TestCase):
    def test_cli_builds_and_renders_instance_agent_package(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            personal_pack = load_json(PACK_DIR / "instance-acme-ops.json")
            folio_connector = next(
                connector
                for connector in personal_pack["source_connectors"]
                if connector["id"] == "connector.personal.folio"
            )
            folio_connector["source_module_ref"] = "source_module.folio"
            folio_connector["module_registry_ref"] = "source_module_registry.core_connectors"
            folio_connector["module_mode"] = "source_owned_query"
            InstanceCapabilityRuntime(stores).seed([personal_pack])
            InstancePreflightRuntime(stores).record(
                {
                    "preflight_ref": "preflight.state_instance.acme_ops.connector.personal.folio",
                    "instance_ref": "state_instance.acme_ops",
                    "connector_ref": "connector.personal.folio",
                    "source_ref": "folio:tenant:personal",
                    "connector_type": "folio",
                    "status": "passed",
                    "checked_at": "2026-05-17T16:40:00Z",
                    "stale_after": "2026-05-17T17:40:00Z",
                    "evidence_refs": ["preflight:folio:passed"],
                }
            )
            InstanceSourceFreshnessRuntime(stores).record(
                {
                    "instance_ref": "state_instance.acme_ops",
                    "connector_ref": "connector.personal.folio",
                    "source_ref": "folio:tenant:personal",
                    "connector_type": "folio",
                    "status": "fresh",
                    "checked_at": "2026-05-17T16:40:00Z",
                    "source_watermark": "folio.indexed_at:2026-05-17T16:39:00Z",
                    "stale_after": "2026-05-17T17:40:00Z",
                    "evidence_refs": ["freshness:folio:fresh"],
                }
            )

            output = StringIO()
            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "instance-agent-package-build",
                    "--instance-ref",
                    "state_instance.acme_ops",
                    "--agent-ref",
                    "agent.samantha",
                    "--persona-ref",
                    "persona.samantha",
                    "--created-at",
                    "2026-05-17T16:41:00Z",
                ],
                stdout=output,
            )

            self.assertEqual(0, code, output.getvalue())
            package = json.loads(output.getvalue())["package"]
            self.assertEqual(
                [],
                validate_schema(
                    package,
                    load_json(ROOT / "schemas" / "instance-agent-package.schema.json"),
                ),
            )
            self.assertIn(
                "gap.state_instance.acme_ops.connector.personal.garmin_connect.access_missing",
                package["source_context"]["source_gap_refs"],
            )
            folio_source = _source(package, "connector.personal.folio")
            self.assertEqual("source_module.folio", folio_source["source_module_ref"])
            self.assertEqual(
                "source_module_registry.core_connectors",
                folio_source["module_registry_ref"],
            )
            self.assertEqual("source_owned_query", folio_source["module_mode"])
            self.assertEqual("2026-05-17T16:40:00Z", folio_source["checked_at"])
            self.assertEqual(
                "folio.indexed_at:2026-05-17T16:39:00Z",
                folio_source["source_watermark"],
            )
            self.assertEqual("2026-05-17T17:40:00Z", folio_source["stale_after"])
            self.assertEqual("source_module.folio.gap_behavior", folio_source["gap_behavior_ref"])
            self.assertIn("preflight:folio:passed", package["evidence_context"]["evidence_refs"])
            self.assertEqual(
                "question_route.personal.relationship_follow_up_triage",
                package["question_routes"][0]["id"],
            )
            small_firm_route = _route(
                package,
                "question_route.personal.small_consulting_firm_contacts",
            )
            follow_up_route = _route(
                package,
                "question_route.personal.relationship_follow_up_triage",
            )
            self.assertEqual(
                "question_route_contract.personal.relationship_follow_up_triage",
                follow_up_route["route_contract_ref"],
            )
            self.assertIn(
                "tool.relationship_substrate.list_subject_notes",
                follow_up_route["required_tools"],
            )
            self.assertIn("calendar", follow_up_route["optional_external_context_tools"])
            self.assertEqual(
                "calendar_is_schedule_context_not_relationship_evidence",
                follow_up_route["fallback_policy"]["external_context_rule"],
            )
            self.assertTrue(
                follow_up_route["answer_contract_policy"][
                    "requires_source_freshness_summary"
                ]
            )
            self.assertIn(
                "tool.relationship_substrate.search_small_consulting_firm_contacts",
                small_firm_route["tool_refs"],
            )
            self.assertEqual(
                "question_route_contract.personal.small_consulting_firm_contacts",
                small_firm_route["route_contract_ref"],
            )
            self.assertIn(
                "tool_action.relationship_substrate.search_small_consulting_firm_contacts",
                small_firm_route["tool_action_refs"],
            )
            self.assertIn(
                "capability.personal.relationship_substrate.search_small_consulting_firm_contacts",
                small_firm_route["capability_refs"],
            )
            self.assertFalse(package["invariant"]["agent_package_authorizes_execution"])
            federation_pack = _federation_pack(
                package,
                "instance_federation_pack.personal_to_acme_state",
            )
            self.assertEqual("instance_read", federation_pack["federation_mode"])
            self.assertFalse(
                federation_pack["materialization_policy"]["local_materialization"]
            )
            self.assertIn(
                "state_instance.acme",
                federation_pack["remote_instance_refs"],
            )

            rendered = StringIO()
            render_code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "instance-agent-package-render",
                    package["id"],
                ],
                stdout=rendered,
            )

            self.assertEqual(0, render_code)
            self.assertIn("State System Instance Agent Package", rendered.getvalue())
            self.assertIn("Source readiness:", rendered.getvalue())
            self.assertIn("connector.personal.garmin_connect", rendered.getvalue())
            self.assertIn("Module: source_module.folio", rendered.getvalue())
            self.assertIn("mode=source_owned_query", rendered.getvalue())
            self.assertIn("Route contract: question_route_contract.personal.relationship_follow_up_triage", rendered.getvalue())
            self.assertIn("Required source coverage:", rendered.getvalue())
            self.assertIn("Tool action refs:", rendered.getvalue())
            self.assertIn("Answer policy:", rendered.getvalue())
            self.assertIn("Fallback policy:", rendered.getvalue())
            self.assertIn("Federation packs:", rendered.getvalue())
            self.assertIn(
                "instance_federation_pack.personal_to_acme_state",
                rendered.getvalue(),
            )
            self.assertIn(
                "tool.relationship_substrate.search_small_consulting_firm_contacts",
                rendered.getvalue(),
            )
            self.assertIn("Do not:", rendered.getvalue())

    def test_renderer_includes_federated_instance_and_governance(self):
        package = load_json(
            ROOT
            / "examples"
            / "instance-agent-package"
            / "instance-agent-package-acme-ops-samantha.json"
        )
        package["source_context"]["source_readiness"][0]["federated_instance"] = {
            "source_instance_ref": "state_instance.acme",
            "status": "available",
        }

        rendered = render_package_for_agent(package)

        self.assertIn("Federated instance: state_instance.acme (available)", rendered)
        self.assertIn("Governance refs:", rendered)
        self.assertIn("Requires refresh before external action.", rendered)

    def test_acme_route_declares_governed_federated_relationship_index(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            InstanceCapabilityRuntime(stores).seed(
                [load_json(PACK_DIR / "instance-acme.json")]
            )
            for connector_ref, source_ref, connector_type in (
                ("connector.acme.folio", "folio:tenant:acme", "folio"),
                ("connector.acme.msgvault", "msgvault:tenant:acme-email", "msgvault"),
                (
                    "connector.acme.state_system",
                    "state-system-instance:state_instance.acme",
                    "local_path",
                ),
            ):
                InstancePreflightRuntime(stores).record(
                    {
                        "preflight_ref": f"preflight.state_instance.acme.{connector_ref}",
                        "instance_ref": "state_instance.acme",
                        "connector_ref": connector_ref,
                        "source_ref": source_ref,
                        "connector_type": connector_type,
                        "status": "passed",
                        "checked_at": "2026-05-17T16:40:00Z",
                        "stale_after": "2026-05-17T17:40:00Z",
                        "evidence_refs": [f"preflight:{connector_ref}:passed"],
                    }
                )
                InstanceSourceFreshnessRuntime(stores).record(
                    {
                        "instance_ref": "state_instance.acme",
                        "connector_ref": connector_ref,
                        "source_ref": source_ref,
                        "connector_type": connector_type,
                        "status": "fresh",
                        "checked_at": "2026-05-17T16:40:00Z",
                        "source_watermark": f"{connector_ref}:2026-05-17T16:39:00Z",
                        "stale_after": "2026-05-17T17:40:00Z",
                        "evidence_refs": [f"freshness:{connector_ref}:fresh"],
                    }
                )

            package = InstanceAgentPackageRuntime(stores).build(
                {
                    "instance_agent_package": load_json(
                        ROOT / "schemas" / "instance-agent-package.schema.json"
                    )
                },
                instance_ref="state_instance.acme",
                agent_ref="agent.caroline",
                persona_ref="persona.caroline",
                created_at="2026-05-17T16:41:00Z",
            )

        relationship_route = _route(
            package,
            "question_route.acme.federated_relationship_index",
        )
        self.assertIn(
            "state_instance.acme_ops",
            package["evidence_context"]["federated_instance_refs"],
        )
        self.assertIn(
            "index.federated.acme_ops.relationship_index",
            package["evidence_context"]["index_refs"],
        )
        self.assertEqual(
            "declared_governed_route",
            relationship_route["query_route"]["status"],
        )
        self.assertEqual(
            "index.federated.acme_ops.relationship_index",
            relationship_route["query_route"]["index_ref"],
        )
        self.assertFalse(relationship_route["query_route"]["local_materialization"])
        self.assertIn(
            "tool.relationship_substrate.search_small_consulting_firm_contacts",
            relationship_route["tool_refs"],
        )
        self.assertIn(
            "query_surface.federated.relationship_index.search",
            relationship_route["source_order"],
        )
        federation_pack = _federation_pack(
            package,
            "instance_federation_pack.acme_to_personal_relationship_substrate",
        )
        self.assertEqual("source_substrate_query", federation_pack["federation_mode"])
        self.assertFalse(
            federation_pack["materialization_policy"]["local_materialization"]
        )
        self.assertIn(
            "No raw personal relationship records may be copied",
            federation_pack["materialization_policy"]["raw_remote_corpus_policy"],
        )
        rendered = render_package_for_agent(package)
        self.assertIn("question_route.acme.federated_relationship_index", rendered)
        self.assertIn("Local materialization: False", rendered)
        self.assertIn("state_instance.acme_ops", rendered)
        self.assertIn(
            "instance_federation_pack.acme_to_personal_relationship_substrate",
            rendered,
        )

    def test_company_scaffold_package_exposes_planned_portfolio_federation(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            navicyte_pack = load_json(PACK_DIR / "instance-acme.json")
            navicyte_pack["id"] = "instance_capability_pack.navicyte"
            navicyte_pack["instance_ref"] = "state_instance.demo_co"
            navicyte_pack["primary_entity_ref"] = "entity.navicyte"
            navicyte_pack["identity"]["name"] = "Navicyte"
            InstanceCapabilityRuntime(stores).seed([navicyte_pack])

            package = InstanceAgentPackageRuntime(stores).build(
                {
                    "instance_agent_package": load_json(
                        ROOT / "schemas" / "instance-agent-package.schema.json"
                    )
                },
                instance_ref="state_instance.demo_co",
                agent_ref="agent.helena",
                persona_ref="persona.helena",
                created_at="2026-05-18T19:30:00Z",
            )

        federation_pack = _federation_pack(
            package,
            "instance_federation_pack.portfolio_to_demo_co_examplecorp",
        )
        self.assertEqual("planned", federation_pack["status"])
        self.assertFalse(
            federation_pack["materialization_policy"]["local_materialization"]
        )
        self.assertIn(
            "gap.state_instance.demo_co.portfolio_federation.package_readiness_unproved",
            federation_pack["freshness_policy"]["gap_refs"],
        )

    def test_build_includes_private_state_root_question_routes(self):
        with TemporaryDirectory() as directory:
            state_root = Path(directory)
            stores = StateStoreBundle(state_root)
            private_routes_dir = state_root / "question-routes"
            private_routes_dir.mkdir(parents=True)
            private_routes_dir.joinpath("question-route-private.json").write_text(
                json.dumps(
                    {
                        "id": "question_route_registry.private",
                        "routes": [
                            {
                                "route_id": "question_route.acme.private_context_review",
                                "intent": "Review private LFW context with visible source gaps.",
                                "source_order": ["connector.acme.folio"],
                                "required_source_coverage": [
                                    {
                                        "coverage_ref": "coverage.acme.private_folio",
                                        "connector_refs": ["connector.acme.folio"],
                                        "source_module_refs": ["source_module.folio"],
                                        "minimum_status": "usable_with_visible_gaps",
                                    }
                                ],
                                "required_tools": ["tool.folio.search"],
                                "answer_contract": {
                                    "requires_evidence_refs": True,
                                    "requires_source_freshness_summary": True,
                                    "direct_evidence_vs_interpretation": True,
                                    "rules": [
                                        "Separate declared coverage from proven live access."
                                    ],
                                },
                                "fallback_policy": {
                                    "policy": "Name the missing Folio source gap."
                                },
                                "gap_behavior": {
                                    "when_required_source_missing": "Declare route undercovered.",
                                    "when_source_stale": "Name stale Folio freshness.",
                                    "relevant_gap_refs": [],
                                },
                            }
                        ],
                    },
                    indent=2,
                )
                + "\n"
            )
            private_tools_dir = state_root / "tool-actions"
            private_tools_dir.mkdir(parents=True)
            private_tools_dir.joinpath("tool-action-private.json").write_text(
                json.dumps(
                    {
                        "id": "tool_action_registry.private",
                        "actions": [
                            {
                                "id": "tool_action.private.folio.search",
                                "tool_ref": "tool.folio.search",
                                "connector_type": "folio",
                            }
                        ],
                    },
                    indent=2,
                )
                + "\n"
            )

            InstanceCapabilityRuntime(stores).seed(
                [load_json(PACK_DIR / "instance-acme.json")]
            )

            package = InstanceAgentPackageRuntime(stores).build(
                {
                    "instance_agent_package": load_json(
                        ROOT / "schemas" / "instance-agent-package.schema.json"
                    )
                },
                instance_ref="state_instance.acme",
                agent_ref="agent.caroline",
                persona_ref="persona.caroline",
                created_at="2026-05-18T20:10:00Z",
            )

        private_route = _route(package, "question_route.acme.private_context_review")
        self.assertEqual(
            "question_route_contract.acme.private_context_review",
            private_route["route_contract_ref"],
        )
        self.assertEqual(
            ["Separate declared coverage from proven live access."],
            private_route["answer_contract"],
        )
        self.assertTrue(
            private_route["answer_contract_policy"]["requires_evidence_refs"]
        )
        self.assertIn("tool.folio.search", private_route["tool_refs"])
        self.assertIn(
            "tool_action.private.folio.search",
            private_route["tool_action_refs"],
        )


def _route(package: dict, route_id: str):
    matches = [route for route in package["question_routes"] if route["id"] == route_id]
    if not matches:
        raise AssertionError(f"{route_id} not found")
    return matches[0]


def _source(package: dict, connector_ref: str):
    matches = [
        source
        for source in package["source_context"]["source_readiness"]
        if source["connector_ref"] == connector_ref
    ]
    if not matches:
        raise AssertionError(f"{connector_ref} not found")
    return matches[0]


def _federation_pack(package: dict, pack_id: str):
    matches = [pack for pack in package.get("federation_packs", []) if pack["id"] == pack_id]
    if not matches:
        raise AssertionError(f"{pack_id} not found")
    return matches[0]


if __name__ == "__main__":
    unittest.main()
