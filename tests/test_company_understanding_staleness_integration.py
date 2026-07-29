from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system.contracts import load_json
from state_system.instance_agent_packages import InstanceAgentPackageRuntime
from state_system.instance_capability import InstanceCapabilityRuntime
from state_system.instance_preflight import InstancePreflightRuntime
from state_system.instance_source_freshness import InstanceSourceFreshnessRuntime
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]


class CompanyUnderstandingStalenessIntegrationTests(unittest.TestCase):
    def test_package_preserves_failed_status_when_failed_source_is_also_expired(self):
        with TemporaryDirectory() as directory:
            state_root = Path(directory)
            stores = StateStoreBundle(state_root)
            InstanceCapabilityRuntime(stores).seed(
                [
                    load_json(
                        ROOT
                        / "examples"
                        / "instance-capability"
                        / "instance-sample-personal.json"
                    )
                ]
            )
            InstancePreflightRuntime(stores).record(
                {
                    "preflight_ref": "preflight.state_instance.sample_personal.connector.personal.kb",
                    "instance_ref": "state_instance.sample_personal",
                    "connector_ref": "connector.personal.kb",
                    "source_ref": "kb:tenant:personal",
                    "connector_type": "kb",
                    "status": "passed",
                    "checked_at": "2026-05-19T19:58:00Z",
                    "stale_after": "2026-05-21T00:00:00Z",
                    "evidence_refs": ["preflight:kb:passed"],
                }
            )
            InstanceSourceFreshnessRuntime(stores).record(
                {
                    "instance_ref": "state_instance.sample_personal",
                    "connector_ref": "connector.personal.kb",
                    "source_ref": "kb:tenant:personal",
                    "connector_type": "kb",
                    "status": "failed",
                    "checked_at": "2026-05-19T19:59:00Z",
                    "source_watermark": "kb.indexed_at:2026-05-19T19:58:00Z",
                    "stale_after": "2026-05-20T00:00:00Z",
                    "watermark_basis": "source_content",
                    "latest_source_modified_at": "2026-05-19T19:58:00Z",
                    "content_status": "failed",
                    "status_reason": "source freshness adapter failed",
                    "evidence_refs": ["freshness:kb:failed"],
                }
            )

            package = InstanceAgentPackageRuntime(stores).build(
                {
                    "instance_agent_package": load_json(
                        ROOT / "schemas" / "instance-agent-package.schema.json"
                    )
                },
                instance_ref="state_instance.sample_personal",
                agent_ref="agent.nova",
                persona_ref="persona.nova",
                created_at="2026-05-21T12:00:00Z",
                package_id="instance_agent_package.sample_personal.nova.failed_expired",
            )

        kb = next(
            source
            for source in package["source_context"]["source_readiness"]
            if source["connector_ref"] == "connector.personal.kb"
        )
        self.assertEqual("failed", kb["freshness_status"])
        self.assertEqual("failed", kb["content_status"])
        self.assertEqual("failed", package["freshness"]["content_status"])
        self.assertTrue(package["freshness"]["requires_refresh_before_external_action"])

    def test_package_source_status_cannot_be_fresh_when_stale_after_expired(self):
        with TemporaryDirectory() as directory:
            state_root = Path(directory)
            stores = StateStoreBundle(state_root)
            InstanceCapabilityRuntime(stores).seed(
                [
                    load_json(
                        ROOT
                        / "examples"
                        / "instance-capability"
                        / "instance-sample-personal.json"
                    )
                ]
            )
            InstancePreflightRuntime(stores).record(
                {
                    "preflight_ref": "preflight.state_instance.sample_personal.connector.personal.kb",
                    "instance_ref": "state_instance.sample_personal",
                    "connector_ref": "connector.personal.kb",
                    "source_ref": "kb:tenant:personal",
                    "connector_type": "kb",
                    "status": "passed",
                    "checked_at": "2026-05-19T19:58:00Z",
                    "stale_after": "2026-05-21T00:00:00Z",
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
                    "checked_at": "2026-05-19T19:59:00Z",
                    "source_watermark": "kb.indexed_at:2026-05-19T19:58:00Z",
                    "stale_after": "2026-05-20T00:00:00Z",
                    "watermark_basis": "source_index",
                    "latest_indexed_at": "2026-05-19T19:58:00Z",
                    "status_reason": "fresh when checked, but stale-after expires before package generation",
                    "evidence_refs": ["freshness:kb:fresh-at-check"],
                }
            )

            package = InstanceAgentPackageRuntime(stores).build(
                {
                    "instance_agent_package": load_json(
                        ROOT / "schemas" / "instance-agent-package.schema.json"
                    )
                },
                instance_ref="state_instance.sample_personal",
                agent_ref="agent.nova",
                persona_ref="persona.nova",
                created_at="2026-05-21T12:00:00Z",
                package_id="instance_agent_package.sample_personal.nova.staleness",
            )

        kb = next(
            source
            for source in package["source_context"]["source_readiness"]
            if source["connector_ref"] == "connector.personal.kb"
        )
        self.assertLess(kb["stale_after"], package["created_at"])
        self.assertNotEqual("fresh", kb["freshness_status"])
        self.assertIn(
            "expired_freshness",
            "\n".join(package["freshness"]["expired_freshness_refs"]),
        )
        self.assertTrue(package["freshness"]["requires_refresh_before_external_action"])


if __name__ == "__main__":
    unittest.main()
