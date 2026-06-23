from __future__ import annotations

import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from state_system.contracts import load_json, validate_schema
from state_system.instance_agent_packages import InstanceAgentPackageRuntime
from state_system.instance_capability import InstanceCapabilityRuntime
from state_system.instance_preflight import InstancePreflightRuntime
from state_system.instance_source_freshness import InstanceSourceFreshnessRuntime
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]

OSS_CONTRACT_FIXTURE_DIRS = (
    "examples/source-modules",
    "examples/tool-actions",
    "examples/question-routes",
    "examples/instance-federation-packs",
    "examples/pressure-questions",
    "examples/instance-agent-package",
)

EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9_.+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+\b")
PRIVATE_DEPLOYMENT_MARKERS = (
    "/Users/example_user",
    "local:/Users/",
    "local-path:/Users/",
    "example_user@",
    "msgvault:account:",
    "agentmem:tenant:example_user",
    "garmin-connect:account:example_user",
    "spotify:account:example_user",
    "entity.example_user",
    "B" + "raydon",
)


class OpenSourceEcosystemConformanceTests(unittest.TestCase):
    def test_capability_connector_types_have_source_modules(self):
        modules = _source_modules()
        connector_types: set[str] = set()

        for directory in ("instance-capability", "company-capability"):
            for path in sorted((ROOT / "examples" / directory).glob("*.json")):
                pack = load_json(path)
                connector_types.update(
                    connector["connector_type"]
                    for connector in pack.get("source_connectors", [])
                )

        module_connector_types = {
            module["connector_type"]
            for module in modules.values()
        }
        self.assertLessEqual(connector_types, module_connector_types)

    def test_tool_actions_reference_known_source_modules_and_connector_types(self):
        modules = _source_modules()
        tool_actions = _tool_actions()

        self.assertEqual(len(tool_actions), len(set(tool_actions)))
        for action in tool_actions.values():
            module_ref = action["source_module_ref"]
            self.assertIn(module_ref, modules)
            self.assertEqual(
                modules[module_ref]["connector_type"],
                action["connector_type"],
            )
            self.assertTrue(action["deployment_adapters"])

    def test_question_routes_reference_known_tools_and_modules(self):
        modules = _source_modules()
        tool_actions = _tool_actions()
        route_registry = load_json(
            ROOT / "examples/question-routes/question-route-core-agent-routes.json"
        )

        for route in route_registry["routes"]:
            route_tools = set(route.get("required_tools", []))
            route_tools.update(route.get("optional_tools", []))
            route_tools.update(route.get("fallback_policy", {}).get("fallback_tool_refs", []))
            self.assertLessEqual(route_tools, set(tool_actions), route["route_id"])

            module_refs = {
                module_ref
                for coverage in route.get("required_source_coverage", [])
                for module_ref in coverage.get("source_module_refs", [])
            }
            module_refs.update(
                mode["source_module_ref"]
                for mode in route.get("module_modes", [])
            )
            self.assertLessEqual(module_refs, set(modules), route["route_id"])

            if route.get("federated_query"):
                self.assertFalse(route["federated_query"]["local_materialization"])

    def test_generated_packages_emit_contract_linkage_fields(self):
        schema = load_json(ROOT / "schemas/instance-agent-package.schema.json")
        package = _generated_personal_package()
        self.assertEqual([], validate_schema(package, schema))

        for source in package["source_context"]["source_readiness"]:
            self.assertTrue(source["source_module_ref"])
            self.assertEqual(
                "source_module_registry.core_connectors",
                source["module_registry_ref"],
            )
            self.assertTrue(source["module_mode"])
            self.assertIn("preflight_contract_ref", source)
            self.assertIn("freshness_contract_ref", source)
            self.assertIn("gap_behavior_ref", source)
            self.assertIn("usable_access_status", source)

        for route in package["question_routes"]:
            self.assertTrue(route.get("route_contract_ref"))
            self.assertTrue(route.get("required_source_coverage"))
            self.assertTrue(route.get("required_tools"))
            self.assertIn("fallback_policy", route)
            self.assertIn("gap_behavior", route)
            self.assertIn("answer_contract_policy", route)

    def test_oss_contract_fixtures_have_no_email_addresses(self):
        offenders: list[str] = []
        for directory in OSS_CONTRACT_FIXTURE_DIRS:
            for path in sorted((ROOT / directory).glob("*.json")):
                for match in EMAIL_PATTERN.findall(path.read_text(encoding="utf-8")):
                    offenders.append(f"{path.relative_to(ROOT)}: {match}")
        self.assertEqual(
            [],
            offenders,
            "OSS contract fixtures must not embed real email addresses; "
            "deployment-specific accounts belong in private instance state roots.",
        )

    def test_oss_contract_fixtures_have_no_credential_values(self):
        credential_pattern = re.compile(
            r'"(?:password|secret|api[_-]?key|access[_-]?token|bearer|client[_-]?secret)"\s*:\s*"[^"]+"',
            re.IGNORECASE,
        )
        offenders: list[str] = []
        for directory in OSS_CONTRACT_FIXTURE_DIRS:
            for path in sorted((ROOT / directory).glob("*.json")):
                for match in credential_pattern.findall(path.read_text(encoding="utf-8")):
                    offenders.append(f"{path.relative_to(ROOT)}: {match}")
        self.assertEqual([], offenders)

    def test_public_examples_have_no_private_deployment_markers(self):
        offenders: list[str] = []
        for path in sorted((ROOT / "examples").rglob("*.json")):
            text = path.read_text(encoding="utf-8")
            for marker in PRIVATE_DEPLOYMENT_MARKERS:
                if marker in text:
                    offenders.append(f"{path.relative_to(ROOT)}: {marker}")
        self.assertEqual(
            [],
            offenders,
            "Public examples must use neutral deployment refs; private runtime "
            "paths, account refs, and personal names belong in state roots.",
        )

    def test_schemas_do_not_lock_in_connector_type_enum(self):
        offenders: list[str] = []
        for path in sorted((ROOT / "schemas").glob("*.json")):
            schema = load_json(path)
            for location in _find_connector_type_schemas(schema):
                if "enum" in location:
                    offenders.append(
                        f"{path.relative_to(ROOT)}: connector_type enum {location['enum']}"
                    )
        self.assertEqual(
            [],
            offenders,
            "connector_type must remain an open string so new source modules can be "
            "registered without editing shipped schemas.",
        )

    def test_generated_package_tool_action_refs_are_known(self):
        package = _generated_personal_package()
        tool_action_refs = {
            ref
            for route in package["question_routes"]
            for ref in route.get("tool_action_refs", [])
        }
        known_action_ids = {
            action["id"]
            for action in load_json(
                ROOT / "examples/tool-actions/tool-action-core-source-tools.json"
            )["actions"]
        }

        self.assertLessEqual(tool_action_refs, known_action_ids)


def _source_modules() -> dict[str, dict]:
    registry = load_json(
        ROOT / "examples/source-modules/source-module-core-connectors.json"
    )
    return {
        module["id"]: module
        for module in registry["modules"]
    }


def _tool_actions() -> dict[str, dict]:
    registry = load_json(
        ROOT / "examples/tool-actions/tool-action-core-source-tools.json"
    )
    return {
        action["tool_ref"]: action
        for action in registry["actions"]
    }


def _generated_personal_package() -> dict:
    with TemporaryDirectory() as directory:
        stores = StateStoreBundle(Path(directory))
        InstanceCapabilityRuntime(stores).seed(
            [load_json(ROOT / "examples/instance-capability/instance-sample-personal.json")]
        )
        InstancePreflightRuntime(stores).record(
            {
                "preflight_ref": "preflight.state_instance.sample_personal.connector.personal.kb",
                "instance_ref": "state_instance.sample_personal",
                "connector_ref": "connector.personal.kb",
                "source_ref": "kb:tenant:personal",
                "connector_type": "kb",
                "status": "passed",
                "checked_at": "2026-05-18T16:00:00Z",
                "stale_after": "2026-05-18T17:00:00Z",
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
                "checked_at": "2026-05-18T16:00:00Z",
                "source_watermark": "kb.indexed_at:2026-05-18T15:59:00Z",
                "stale_after": "2026-05-18T17:00:00Z",
                "watermark_basis": "source_index",
                "latest_indexed_at": "2026-05-18T15:59:00Z",
                "status_reason": "latest indexed corpus timestamp is inside policy",
                "evidence_refs": ["freshness:kb:fresh"],
            }
        )
        return InstanceAgentPackageRuntime(stores).build(
            {
                "instance_agent_package": load_json(
                    ROOT / "schemas/instance-agent-package.schema.json"
                )
            },
            instance_ref="state_instance.sample_personal",
            agent_ref="agent.nova",
            persona_ref="persona.nova",
            created_at="2026-05-18T16:01:00Z",
            package_id="instance_agent_package.test.sample_personal.nova",
        )


def _find_connector_type_schemas(node: object) -> list[dict]:
    found: list[dict] = []
    if isinstance(node, dict):
        properties = node.get("properties")
        if isinstance(properties, dict):
            connector_schema = properties.get("connector_type")
            if isinstance(connector_schema, dict):
                found.append(connector_schema)
        for value in node.values():
            found.extend(_find_connector_type_schemas(value))
    elif isinstance(node, list):
        for value in node:
            found.extend(_find_connector_type_schemas(value))
    return found


if __name__ == "__main__":
    unittest.main()
