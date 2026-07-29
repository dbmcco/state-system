from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system.contracts import load_json, validate_schema
from state_system.fleet_refresh import run_fleet_refresh
from state_system.instance_capability import InstanceCapabilityRuntime
from state_system.instance_preflight import InstancePreflightRuntime
from state_system.instance_source_freshness import InstanceSourceFreshnessRuntime
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]


def _seed_placeholder_instance(state_root: Path) -> None:
    """Seed a minimal instance so the per-instance refresh path succeeds."""
    stores = StateStoreBundle(state_root)
    InstanceCapabilityRuntime(stores).seed(
        [
            {
                "id": "instance_capability_pack.placeholder",
                "instance_ref": "state_instance.placeholder",
                "primary_entity_ref": "entity.placeholder",
                "entity_kind": "project",
                "generated_at": "2026-06-25T11:00:00Z",
                "identity": {
                    "name": "Placeholder",
                    "summary": "Minimal placeholder instance.",
                    "primary_agent_refs": ["agent.placeholder"],
                },
                "source_connectors": [],
                "raw_corpus": {"definition": "", "source_refs": []},
                "evidence_index": {"definition": "", "index_refs": []},
                "index_manifests": [],
                "memory_refs": [],
                "operating_picture_refs": [],
                "action_surface": {"definition": "", "action_refs": []},
                "tool_capability_bindings": [],
                "governance": {
                    "definition": "",
                    "governance_refs": [],
                },
                "connector_preflight": {
                    "definition": "",
                    "required_checks": [],
                },
                "runtime_constraints": {
                    "definition": "",
                    "constraints": [],
                },
                "freshness": {
                    "as_of": "2026-06-25T11:00:00Z",
                    "stale_after": "2026-06-25T13:00:00Z",
                    "watermark_refs": [],
                },
                "invariant": {
                    "declares_context": True,
                    "proves_live_access": False,
                    "authorizes_execution": False,
                    "live_access_proven_by": "connector_preflight",
                    "protected_action_authorized_by": "governance",
                },
            }
        ]
    )


def _seed_navicyte_state(state_root: Path) -> None:
    """Seed a Navicyte-shaped state root with declared capability and freshness."""
    stores = StateStoreBundle(state_root)
    pack = load_json(ROOT / "examples" / "instance-capability" / "instance-navicyte.json")
    InstanceCapabilityRuntime(stores).seed([pack])
    InstancePreflightRuntime(stores).record(
        {
            "preflight_ref": "preflight.state_instance.navicyte.connector.navicyte.notion",
            "instance_ref": "state_instance.navicyte",
            "connector_ref": "connector.navicyte.notion",
            "source_ref": "notion:workspace:navicyte-grant",
            "connector_type": "notion",
            "status": "passed",
            "checked_at": "2026-06-25T11:00:00Z",
            "stale_after": "2026-06-25T13:00:00Z",
            "evidence_refs": ["preflight:notion:passed"],
        }
    )
    InstancePreflightRuntime(stores).record(
        {
            "preflight_ref": "preflight.state_instance.navicyte.connector.navicyte.email",
            "instance_ref": "state_instance.navicyte",
            "connector_ref": "connector.navicyte.email",
            "source_ref": "email:mailbox:navicyte-mike",
            "connector_type": "email",
            "status": "passed",
            "checked_at": "2026-06-25T11:00:00Z",
            "stale_after": "2026-06-25T13:00:00Z",
            "evidence_refs": ["preflight:email:passed"],
        }
    )
    InstanceSourceFreshnessRuntime(stores).record(
        {
            "instance_ref": "state_instance.navicyte",
            "connector_ref": "connector.navicyte.notion",
            "source_ref": "notion:workspace:navicyte-grant",
            "connector_type": "notion",
            "status": "stale",
            "checked_at": "2026-06-25T11:00:00Z",
            "source_watermark": "notion:workspace:navicyte-grant:last_modified=2026-06-23T09:00:00Z",
            "stale_after": "2026-06-24T00:00:00Z",
            "watermark_basis": "source_content",
            "latest_source_modified_at": "2026-06-23T09:00:00Z",
            "status_reason": "Notion grant workspace last modified 2026-06-23; past declared stale-after.",
            "evidence_refs": ["agent-runtime:freshness:notion:navicyte-grant:stale"],
            "index_refs": ["index.navicyte.notion.grant"],
        }
    )
    InstanceSourceFreshnessRuntime(stores).record(
        {
            "instance_ref": "state_instance.navicyte",
            "connector_ref": "connector.navicyte.email",
            "source_ref": "email:mailbox:navicyte-mike",
            "connector_type": "email",
            "status": "fresh",
            "checked_at": "2026-06-25T11:00:00Z",
            "source_watermark": "email:mailbox:navicyte-mike:last_event=2026-06-25T09:00:00Z",
            "stale_after": "2026-07-02T00:00:00Z",
            "watermark_basis": "source_event",
            "latest_source_event_at": "2026-06-25T09:00:00Z",
            "status_reason": "Navicyte Mike mailbox ingested events today; source is fresh.",
            "evidence_refs": ["agent-runtime:freshness:email:navicyte-mike:fresh"],
            "index_refs": ["index.navicyte.email.mike"],
        }
    )


class EcsManifestMultiRootTests(unittest.TestCase):
    def test_fleet_manifest_accepts_multiple_entity_current_state_roots(self):
        with TemporaryDirectory() as directory:
            first = Path(directory) / "first"
            second = Path(directory) / "second"
            manifest = {
                "id": "fleet_refresh_manifest.multi_ecs",
                "instances": [
                    {
                        "id": "fleet_instance.placeholder",
                        "state_root": str(Path(directory) / "instance"),
                        "instance_ref": "state_instance.placeholder",
                        "agent_ref": "agent.placeholder",
                        "package_id": "instance_agent_package.placeholder",
                    }
                ],
                "entity_current_state": {
                    "roots": [
                        {"state_root": str(first), "label": "personal"},
                        {"state_root": str(second), "label": "portfolio"},
                    ],
                    "output_dir": "entity-current-state",
                },
            }
            schema = load_json(ROOT / "schemas" / "fleet-refresh-manifest.schema.json")

            errors = validate_schema(manifest, schema)

        self.assertEqual([], errors)

    def test_fleet_refresh_reports_each_entity_current_state_root(self):
        with TemporaryDirectory() as directory:
            first = Path(directory) / "first"
            second = Path(directory) / "second"
            manifest = {
                "id": "fleet_refresh_manifest.multi_ecs",
                "instances": [
                    {
                        "id": "fleet_instance.placeholder",
                        "state_root": str(Path(directory) / "instance"),
                        "instance_ref": "state_instance.placeholder",
                        "agent_ref": "agent.placeholder",
                        "package_id": "instance_agent_package.placeholder",
                    }
                ],
                "entity_current_state": {
                    "roots": [
                        {"state_root": str(first), "label": "personal"},
                        {"state_root": str(second), "label": "portfolio"},
                    ],
                    "output_dir": "entity-current-state",
                },
            }

            report = run_fleet_refresh(
                manifest,
                project_root=ROOT,
                checked_at="2026-06-25T12:00:00Z",
                stale_after="2026-06-25T13:00:00Z",
                dry_run=True,
            )

        ecs = report["entity_current_state"]
        self.assertEqual("planned", ecs["status"])
        self.assertEqual(
            {"personal", "portfolio"},
            {root["label"] for root in ecs["roots"]},
        )
        self.assertEqual(
            {str(first), str(second)},
            {root["state_root"] for root in ecs["roots"]},
        )

    def test_fleet_refresh_supports_b_state_plus_company_shape(self):
        with TemporaryDirectory() as directory:
            b_state = Path(directory) / "b-state"
            company = Path(directory) / "company"
            manifest = {
                "id": "fleet_refresh_manifest.b_state_and_company",
                "instances": [
                    {
                        "id": "fleet_instance.placeholder",
                        "state_root": str(Path(directory) / "instance"),
                        "instance_ref": "state_instance.placeholder",
                        "agent_ref": "agent.placeholder",
                        "package_id": "instance_agent_package.placeholder",
                    }
                ],
                "entity_current_state": {
                    "roots": [
                        {"state_root": str(b_state), "label": "b_state"},
                        {"state_root": str(company), "label": "company"},
                    ],
                    "output_dir": "entity-current-state",
                },
            }

            report = run_fleet_refresh(
                manifest,
                project_root=ROOT,
                checked_at="2026-06-25T12:00:00Z",
                stale_after="2026-06-25T13:00:00Z",
                dry_run=True,
            )

        ecs = report["entity_current_state"]
        self.assertEqual("planned", ecs["status"])
        self.assertEqual(
            {"b_state", "company"},
            {root["label"] for root in ecs["roots"]},
        )

    def test_missing_entity_current_state_root_is_reported_as_gap(self):
        with TemporaryDirectory() as directory:
            existing = Path(directory) / "existing"
            existing.mkdir()
            missing = Path(directory) / "missing"
            instance_root = Path(directory) / "instance"
            _seed_placeholder_instance(instance_root)
            manifest = {
                "id": "fleet_refresh_manifest.missing_ecs_root",
                "instances": [
                    {
                        "id": "fleet_instance.placeholder",
                        "state_root": str(instance_root),
                        "instance_ref": "state_instance.placeholder",
                        "agent_ref": "agent.placeholder",
                        "package_id": "instance_agent_package.placeholder",
                    }
                ],
                "entity_current_state": {
                    "roots": [
                        {"state_root": str(existing), "label": "existing"},
                        {"state_root": str(missing), "label": "missing"},
                    ],
                    "output_dir": "entity-current-state",
                },
            }

            report = run_fleet_refresh(
                manifest,
                project_root=ROOT,
                checked_at="2026-06-25T12:00:00Z",
                stale_after="2026-06-25T13:00:00Z",
            )

        self.assertFalse(report["ok"], report)
        ecs = report["entity_current_state"]
        self.assertEqual("failed", ecs["status"])
        missing_root = next(
            root for root in ecs["roots"] if root["label"] == "missing"
        )
        self.assertEqual("failed", missing_root["status"])
        self.assertTrue(
            any("state_root_missing" in gap for gap in missing_root["gap_refs"]),
            missing_root,
        )
        existing_root = next(
            root for root in ecs["roots"] if root["label"] == "existing"
        )
        self.assertEqual("refreshed", existing_root["status"])

    def test_navicyte_fleet_refresh_manifest_validates(self):
        manifest = load_json(
            ROOT / "examples" / "fleet-refresh" / "fleet-refresh-navicyte.json"
        )
        schema = load_json(ROOT / "schemas" / "fleet-refresh-manifest.schema.json")

        errors = validate_schema(manifest, schema)

        self.assertEqual([], errors)

    def test_navicyte_refresh_exposes_source_gaps(self):
        with TemporaryDirectory() as directory:
            state_root = Path(directory)
            _seed_navicyte_state(state_root)
            manifest = {
                "id": "fleet_refresh_manifest.navicyte",
                "instances": [
                    {
                        "id": "fleet_instance.navicyte",
                        "state_root": str(state_root),
                        "instance_ref": "state_instance.navicyte",
                        "agent_ref": "agent.navicyte",
                        "package_id": "instance_agent_package.navicyte",
                    }
                ],
            }

            report = run_fleet_refresh(
                manifest,
                project_root=ROOT,
                checked_at="2026-06-25T12:00:00Z",
                stale_after="2026-06-25T13:00:00Z",
            )

        instance = report["instances"][0]
        self.assertEqual("refreshed", instance["status"])
        gap_refs = instance["source_gap_refs"]
        self.assertTrue(
            any(
                "connector.navicyte.notion" in ref and "freshness_stale" in ref
                for ref in gap_refs
            ),
            gap_refs,
        )


if __name__ == "__main__":
    unittest.main()
