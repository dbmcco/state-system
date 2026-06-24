from __future__ import annotations

from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.context_personal import (
    PersonalContextPackageValidationError,
    build_personal_context_package,
)
from state_system.contracts import load_json, validate_schema
from state_system.instance_capability import InstanceCapabilityRuntime
from state_system.instance_preflight import InstancePreflightRuntime
from state_system.instance_source_freshness import InstanceSourceFreshnessRuntime
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]
CAPABILITY_PACK = ROOT / "examples" / "instance-capability" / "instance-sample-personal.json"
SCHEMA_PATH = ROOT / "schemas" / "personal-context-package.schema.json"


def _seed_personal(stores: StateStoreBundle) -> None:
    InstanceCapabilityRuntime(stores).seed([load_json(CAPABILITY_PACK)])
    InstancePreflightRuntime(stores).record(
        {
            "preflight_ref": (
                "preflight.state_instance.sample_personal.connector.personal.kb"
            ),
            "instance_ref": "state_instance.sample_personal",
            "connector_ref": "connector.personal.kb",
            "source_ref": "kb:tenant:personal",
            "connector_type": "kb",
            "status": "passed",
            "checked_at": "2026-05-17T10:15:00Z",
            "stale_after": "2026-05-17T11:15:00Z",
            "evidence_refs": ["preflight:kb:passed"],
        }
    )
    InstancePreflightRuntime(stores).record(
        {
            "preflight_ref": (
                "preflight.state_instance.sample_personal.connector.personal.msgvault"
            ),
            "instance_ref": "state_instance.sample_personal",
            "connector_ref": "connector.personal.msgvault",
            "source_ref": "msgvault:tenant:personal-email",
            "connector_type": "msgvault",
            "status": "passed",
            "checked_at": "2026-05-17T10:16:00Z",
            "stale_after": "2026-05-17T11:16:00Z",
            "evidence_refs": ["preflight:msgvault:passed"],
        }
    )
    InstanceSourceFreshnessRuntime(stores).record(
        {
            "instance_ref": "state_instance.sample_personal",
            "connector_ref": "connector.personal.kb",
            "source_ref": "kb:tenant:personal",
            "connector_type": "kb",
            "status": "fresh",
            "checked_at": "2026-05-17T10:15:00Z",
            "source_watermark": "kb.indexed_at:2026-05-17T10:14:00Z",
            "stale_after": "2026-05-17T11:15:00Z",
            "watermark_basis": "source_index",
            "latest_indexed_at": "2026-05-17T10:14:00Z",
            "status_reason": "latest indexed corpus timestamp is inside policy",
            "lag_seconds": 60,
            "evidence_refs": ["agent-runtime:freshness:kb:fresh"],
        }
    )


class PersonalContextPackageTests(unittest.TestCase):
    def test_package_includes_source_boundaries_and_unresolved_gaps(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            _seed_personal(stores)
            package = build_personal_context_package(
                stores=stores,
                instance_ref="state_instance.sample_personal",
                package_id="personal_context_package.example_user.20260517",
                created_at="2026-05-17T16:00:00Z",
                synthesis_goal="Synthesize personal personal state across declared sources.",
                valid_until="2026-05-17T17:00:00Z",
            )

        self.assertEqual("personal_b_state_synthesis", package["package_type"])
        self.assertEqual("state_instance.sample_personal", package["instance_ref"])
        self.assertEqual("entity.example_person", package["primary_entity_ref"])
        connector_refs = {
            boundary["connector_ref"] for boundary in package["source_boundaries"]
        }
        self.assertIn("connector.personal.kb", connector_refs)
        self.assertIn("connector.personal.msgvault", connector_refs)
        self.assertIn("connector.personal.agentmem", connector_refs)
        gap_reasons = {gap["reason"] for gap in package["unresolved_gaps"]}
        self.assertIn("access_missing", gap_reasons)

    def test_package_represents_msgvault_and_agentmem_through_retrieval_refs(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            _seed_personal(stores)
            package = build_personal_context_package(
                stores=stores,
                instance_ref="state_instance.sample_personal",
                package_id="personal_context_package.example_user.20260517",
                created_at="2026-05-17T16:00:00Z",
                synthesis_goal="Synthesize personal personal state.",
                valid_until="2026-05-17T17:00:00Z",
            )

        retrieval_by_connector = {
            ref["connector_ref"]: ref for ref in package["retrieval_refs"]
        }
        msgvault = retrieval_by_connector["connector.personal.msgvault"]
        agentmem = retrieval_by_connector["connector.personal.agentmem"]
        for ref in (msgvault, agentmem):
            self.assertIn(
                ref["representation"], {"retrieval_ref", "bounded_excerpt"}
            )
            self.assertNotIn("raw_payload", ref)
            self.assertIn("index_ref", ref)
            self.assertIn("query_surface", ref)
            if ref["representation"] == "bounded_excerpt":
                self.assertIn("size_hint", ref["bounded_excerpt"])
                self.assertNotIn("raw_content", ref["bounded_excerpt"])

    def test_package_carries_freshness_governance_and_invariants(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            _seed_personal(stores)
            package = build_personal_context_package(
                stores=stores,
                instance_ref="state_instance.sample_personal",
                package_id="personal_context_package.example_user.20260517",
                created_at="2026-05-17T16:00:00Z",
                synthesis_goal="Synthesize personal personal state.",
                valid_until="2026-05-17T17:00:00Z",
            )

        self.assertIn(
            "kb.indexed_at:2026-05-17T10:14:00Z",
            package["freshness"]["watermark_refs"],
        )
        self.assertTrue(package["freshness"]["requires_refresh_before_synthesis"])
        self.assertEqual("2026-05-17T17:00:00Z", package["freshness"]["valid_until"])
        self.assertIn(
            "governance.example_user.personal_default",
            package["governance"]["governance_refs"],
        )
        self.assertTrue(
            any(
                "raw email" in constraint or "agent memory" in constraint
                for constraint in package["governance"]["constraints"]
            )
        )
        self.assertTrue(package["invariant"]["declares_synthesis_input"])
        self.assertFalse(package["invariant"]["synthesizes_state"])
        self.assertFalse(package["invariant"]["copies_raw_corpora"])

    def test_package_validates_against_schema(self):
        schema = load_json(SCHEMA_PATH)
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            _seed_personal(stores)
            package = build_personal_context_package(
                stores=stores,
                instance_ref="state_instance.sample_personal",
                package_id="personal_context_package.example_user.20260517",
                created_at="2026-05-17T16:00:00Z",
                synthesis_goal="Synthesize personal personal state.",
                valid_until="2026-05-17T17:00:00Z",
            )
        self.assertEqual([], validate_schema(package, schema))

    def test_missing_instance_raises(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            _seed_personal(stores)
            with self.assertRaises(ValueError):
                build_personal_context_package(
                    stores=stores,
                    instance_ref="state_instance.does_not_exist",
                    package_id="personal_context_package.missing",
                    created_at="2026-05-17T16:00:00Z",
                    synthesis_goal="Synthesize personal personal state.",
                    valid_until="2026-05-17T17:00:00Z",
                )

    def test_invalid_package_raises_validation_error(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            _seed_personal(stores)
            strict_schema = {
                "type": "object",
                "required": ["forbidden_field"],
                "properties": {"forbidden_field": {"type": "string"}},
            }
            with self.assertRaises(PersonalContextPackageValidationError) as cm:
                build_personal_context_package(
                    stores=stores,
                    instance_ref="state_instance.sample_personal",
                    package_id="personal_context_package.example_user.invalid",
                    created_at="2026-05-17T16:00:00Z",
                    synthesis_goal="Synthesize personal personal state.",
                    valid_until="2026-05-17T17:00:00Z",
                    schema=strict_schema,
                )
            self.assertTrue(cm.exception.errors)

    def test_cli_writes_personal_context_package(self):
        with TemporaryDirectory() as directory, TemporaryDirectory() as output_dir:
            stores = StateStoreBundle(Path(directory))
            _seed_personal(stores)

            stdout = StringIO()
            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "personal-context-package-build",
                    "--instance-ref",
                    "state_instance.sample_personal",
                    "--package-id",
                    "personal_context_package.example_user.cli",
                    "--created-at",
                    "2026-05-17T16:00:00Z",
                    "--synthesis-goal",
                    "Synthesize personal personal state from declared sources.",
                    "--valid-until",
                    "2026-05-17T17:00:00Z",
                    "--output-dir",
                    output_dir,
                ],
                stdout=stdout,
            )
            self.assertEqual(0, code, stdout.getvalue())
            payload = json.loads(stdout.getvalue())
            package_path = Path(payload["package_path"])
            self.assertTrue(package_path.exists())
            package = json.loads(package_path.read_text(encoding="utf-8"))
            self.assertEqual("personal_context_package.example_user.cli", package["id"])


if __name__ == "__main__":
    unittest.main()
