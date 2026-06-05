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
            personal_pack = load_json(PACK_DIR / "instance-sample-personal.json")
            ks_connector = next(
                connector
                for connector in personal_pack["source_connectors"]
                if connector["id"] == "connector.personal.kb"
            )
            ks_connector["source_module_ref"] = "source_module.kb"
            ks_connector["module_registry_ref"] = "source_module_registry.core_connectors"
            ks_connector["module_mode"] = "source_owned_query"
            InstanceCapabilityRuntime(stores).seed([personal_pack])
            InstancePreflightRuntime(stores).record(
                {
                    "preflight_ref": "preflight.state_instance.sample_personal.connector.personal.kb",
                    "instance_ref": "state_instance.sample_personal",
                    "connector_ref": "connector.personal.kb",
                    "source_ref": "kb:tenant:personal",
                    "connector_type": "kb",
                    "status": "passed",
                    "checked_at": "2026-05-17T16:40:00Z",
                    "stale_after": "2026-05-17T17:40:00Z",
                    "evidence_refs": ["preflight:kb:passed"],
                }
            )
            InstanceSourceFreshnessRuntime(stores).record(
                {
                    "instance_ref": "state_instance.sample_personal",
                    "connector_ref": "connector.personal.kb",
                    "source_ref": "kb:tenant:personal",
                    "connector_type": "kb",
                    "status": "fresh",
                    "checked_at": "2026-05-17T16:40:00Z",
                    "source_watermark": "kb.indexed_at:2026-05-17T16:39:00Z",
                    "stale_after": "2026-05-17T17:40:00Z",
                    "evidence_refs": ["freshness:kb:fresh"],
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
                    "state_instance.sample_personal",
                    "--agent-ref",
                    "agent.nova",
                    "--persona-ref",
                    "persona.nova",
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
                "gap.state_instance.sample_personal.connector.personal.garmin_connect.access_missing",
                package["source_context"]["source_gap_refs"],
            )
            ks_source = _source(package, "connector.personal.kb")
            self.assertEqual("source_module.kb", ks_source["source_module_ref"])
            self.assertEqual(
                "source_module_registry.core_connectors",
                ks_source["module_registry_ref"],
            )
            self.assertEqual("source_owned_query", ks_source["module_mode"])
            self.assertEqual("2026-05-17T16:40:00Z", ks_source["checked_at"])
            self.assertEqual(
                "kb.indexed_at:2026-05-17T16:39:00Z",
                ks_source["source_watermark"],
            )
            self.assertEqual("2026-05-17T17:40:00Z", ks_source["stale_after"])
            self.assertEqual("source_module.kb.gap_behavior", ks_source["gap_behavior_ref"])
            self.assertIn("preflight:kb:passed", package["evidence_context"]["evidence_refs"])
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
                "instance_federation_pack.personal_to_sampleco_state",
            )
            self.assertEqual("instance_read", federation_pack["federation_mode"])
            self.assertFalse(
                federation_pack["materialization_policy"]["local_materialization"]
            )
            self.assertIn(
                "state_instance.sampleco",
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
            self.assertIn("Module: source_module.kb", rendered.getvalue())
            self.assertIn("mode=source_owned_query", rendered.getvalue())
            self.assertIn("Route contract: question_route_contract.personal.relationship_follow_up_triage", rendered.getvalue())
            self.assertIn("Required source coverage:", rendered.getvalue())
            self.assertIn("Tool action refs:", rendered.getvalue())
            self.assertIn("Answer policy:", rendered.getvalue())
            self.assertIn("Fallback policy:", rendered.getvalue())
            self.assertIn("Federation packs:", rendered.getvalue())
            self.assertIn(
                "instance_federation_pack.personal_to_sampleco_state",
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
            / "instance-agent-package-sample-personal-nova.json"
        )
        package["source_context"]["source_readiness"][0]["federated_instance"] = {
            "source_instance_ref": "state_instance.sampleco",
            "status": "available",
        }

        rendered = render_package_for_agent(package)

        self.assertIn("Federated instance: state_instance.sampleco (available)", rendered)
        self.assertIn("Governance refs:", rendered)
        self.assertIn("Requires refresh before external action.", rendered)

    def test_build_marks_fresh_source_expired_when_stale_after_precedes_created_at(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            InstanceCapabilityRuntime(stores).seed(
                [load_json(PACK_DIR / "instance-sampleco.json")]
            )
            InstancePreflightRuntime(stores).record(
                {
                    "preflight_ref": "preflight.state_instance.sampleco.connector.sampleco.kb",
                    "instance_ref": "state_instance.sampleco",
                    "connector_ref": "connector.sampleco.kb",
                    "source_ref": "kb:tenant:sampleco",
                    "connector_type": "kb",
                    "status": "passed",
                    "checked_at": "2026-05-17T16:40:00Z",
                    "stale_after": "2026-05-17T17:40:00Z",
                    "evidence_refs": ["preflight:kb:passed"],
                }
            )
            InstanceSourceFreshnessRuntime(stores).record(
                {
                    "instance_ref": "state_instance.sampleco",
                    "connector_ref": "connector.sampleco.kb",
                    "source_ref": "kb:tenant:sampleco",
                    "connector_type": "kb",
                    "status": "fresh",
                    "checked_at": "2026-05-17T16:40:00Z",
                    "source_watermark": "kb.indexed_at:2026-05-17T16:39:00Z",
                    "stale_after": "2026-05-17T17:40:00Z",
                    "evidence_refs": ["freshness:kb:fresh"],
                }
            )

            package = InstanceAgentPackageRuntime(stores).build(
                {
                    "instance_agent_package": load_json(
                        ROOT / "schemas" / "instance-agent-package.schema.json"
                    )
                },
                instance_ref="state_instance.sampleco",
                agent_ref="agent.iris",
                persona_ref="persona.iris",
                created_at="2026-05-17T18:00:00Z",
            )

        self.assertTrue(
            package["freshness"]["requires_refresh_before_external_action"]
        )
        expired_refs = package["freshness"]["expired_freshness_refs"]
        self.assertEqual(1, len(expired_refs))
        self.assertIn("connector.sampleco.kb", expired_refs[0])
        self.assertIn("stale_after.2026-05-17T17:40:00Z", expired_refs[0])

    def test_sampleco_route_declares_governed_federated_relationship_index(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            InstanceCapabilityRuntime(stores).seed(
                [load_json(PACK_DIR / "instance-sampleco.json")]
            )
            for connector_ref, source_ref, connector_type in (
                ("connector.sampleco.kb", "kb:tenant:sampleco", "kb"),
                ("connector.sampleco.msgvault", "msgvault:tenant:sampleco-email", "msgvault"),
                (
                    "connector.sampleco.state_system",
                    "state-system-instance:state_instance.sampleco",
                    "local_path",
                ),
            ):
                InstancePreflightRuntime(stores).record(
                    {
                        "preflight_ref": f"preflight.state_instance.sampleco.{connector_ref}",
                        "instance_ref": "state_instance.sampleco",
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
                        "instance_ref": "state_instance.sampleco",
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
                instance_ref="state_instance.sampleco",
                agent_ref="agent.iris",
                persona_ref="persona.iris",
                created_at="2026-05-17T16:41:00Z",
            )

        relationship_route = _route(
            package,
            "question_route.sampleco.federated_relationship_index",
        )
        self.assertIn(
            "state_instance.sample_personal",
            package["evidence_context"]["federated_instance_refs"],
        )
        self.assertIn(
            "index.federated.sample_personal.relationship_index",
            package["evidence_context"]["index_refs"],
        )
        self.assertEqual(
            "declared_governed_route",
            relationship_route["query_route"]["status"],
        )
        self.assertEqual(
            "index.federated.sample_personal.relationship_index",
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
            "instance_federation_pack.sampleco_to_personal_relationship_substrate",
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
        self.assertIn("question_route.sampleco.federated_relationship_index", rendered)
        self.assertIn("Local materialization: False", rendered)
        self.assertIn("state_instance.sample_personal", rendered)
        self.assertIn(
            "instance_federation_pack.sampleco_to_personal_relationship_substrate",
            rendered,
        )

    def test_company_scaffold_package_exposes_planned_portfolio_federation(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            portfolio_co_pack = load_json(PACK_DIR / "instance-sampleco.json")
            portfolio_co_pack["id"] = "instance_capability_pack.portfolio_co"
            portfolio_co_pack["instance_ref"] = "state_instance.portfolio_co"
            portfolio_co_pack["primary_entity_ref"] = "entity.portfolio_co"
            portfolio_co_pack["identity"]["name"] = "PortfolioCo"
            InstanceCapabilityRuntime(stores).seed([portfolio_co_pack])

            package = InstanceAgentPackageRuntime(stores).build(
                {
                    "instance_agent_package": load_json(
                        ROOT / "schemas" / "instance-agent-package.schema.json"
                    )
                },
                instance_ref="state_instance.portfolio_co",
                agent_ref="agent.helena",
                persona_ref="persona.helena",
                created_at="2026-05-18T19:30:00Z",
            )

        federation_pack = _federation_pack(
            package,
            "instance_federation_pack.portfolio_to_portfolio_co_researchco",
        )
        self.assertEqual("planned", federation_pack["status"])
        self.assertFalse(
            federation_pack["materialization_policy"]["local_materialization"]
        )
        self.assertIn(
            "gap.state_instance.portfolio_co.portfolio_federation.package_readiness_unproved",
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
                                "route_id": "question_route.sampleco.private_context_review",
                                "intent": "Review private SampleCo context with visible source gaps.",
                                "source_order": ["connector.sampleco.kb"],
                                "required_source_coverage": [
                                    {
                                        "coverage_ref": "coverage.sampleco.private_knowledge_store",
                                        "connector_refs": ["connector.sampleco.kb"],
                                        "source_module_refs": ["source_module.kb"],
                                        "minimum_status": "usable_with_visible_gaps",
                                    }
                                ],
                                "required_tools": ["tool.kb.search"],
                                "answer_contract": {
                                    "requires_evidence_refs": True,
                                    "requires_source_freshness_summary": True,
                                    "direct_evidence_vs_interpretation": True,
                                    "rules": [
                                        "Separate declared coverage from proven live access."
                                    ],
                                },
                                "fallback_policy": {
                                    "policy": "Name the missing Knowledge Store source gap."
                                },
                                "gap_behavior": {
                                    "when_required_source_missing": "Declare route undercovered.",
                                    "when_source_stale": "Name stale Knowledge Store freshness.",
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
                                "id": "tool_action.private.kb.search",
                                "tool_ref": "tool.kb.search",
                                "connector_type": "kb",
                            }
                        ],
                    },
                    indent=2,
                )
                + "\n"
            )

            InstanceCapabilityRuntime(stores).seed(
                [load_json(PACK_DIR / "instance-sampleco.json")]
            )

            package = InstanceAgentPackageRuntime(stores).build(
                {
                    "instance_agent_package": load_json(
                        ROOT / "schemas" / "instance-agent-package.schema.json"
                    )
                },
                instance_ref="state_instance.sampleco",
                agent_ref="agent.iris",
                persona_ref="persona.iris",
                created_at="2026-05-18T20:10:00Z",
            )

        private_route = _route(package, "question_route.sampleco.private_context_review")
        self.assertEqual(
            "question_route_contract.sampleco.private_context_review",
            private_route["route_contract_ref"],
        )
        self.assertEqual(
            ["Separate declared coverage from proven live access."],
            private_route["answer_contract"],
        )
        self.assertTrue(
            private_route["answer_contract_policy"]["requires_evidence_refs"]
        )
        self.assertIn("tool.kb.search", private_route["tool_refs"])
        self.assertIn(
            "tool_action.private.kb.search",
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
