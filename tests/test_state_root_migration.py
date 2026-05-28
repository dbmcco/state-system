import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system.company_capability import CompanyCapabilityRuntime
from state_system.company_preflight import CompanyPreflightRuntime
from state_system.contracts import load_json
from state_system.state_root_migration import migrate_state_root
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = ROOT / "examples" / "company-capability"


class StateRootMigrationTests(unittest.TestCase):
    def test_migration_replaces_target_symlink_and_writes_compat_symlink(self):
        with TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "hidden" / "state-system"
            target = base / "work" / "acme" / "state-system"
            compat = base / "compat" / "state-system"
            local_path = base / "work" / "acme"
            local_path.mkdir(parents=True)
            compat.parent.mkdir(parents=True)

            stores = StateStoreBundle(source)
            CompanyCapabilityRuntime(stores).seed(
                [
                    _pack_with_local_path("company-acme.json", local_path),
                    load_json(PACK_DIR / "company-examplecorp.json"),
                    load_json(PACK_DIR / "company-demo-co.json"),
                ]
            )
            CompanyPreflightRuntime(stores).record(
                {
                    "preflight_ref": "preflight.acme.linear",
                    "company_ref": "company.acme",
                    "connector_ref": "connector.acme.linear",
                    "tool_ref": "tool.paia.linear.read",
                    "action_ref": "action_surface.acme.read_linear",
                    "agent_ref": "persona.caroline",
                    "runner_ref": "runner.paia.codex",
                    "status": "passed",
                    "checked_at": "2026-05-16T12:00:00Z",
                    "stale_after": "2026-05-16T13:00:00Z",
                    "evidence_refs": ["paia:preflight:linear:acme"],
                }
            )

            target.symlink_to(source, target_is_directory=True)
            compat.mkdir()

            result = migrate_state_root(
                project_root=ROOT,
                source_root=source,
                target_root=target,
                compat_link=compat,
                validate_company_ref="company.acme",
                refresh=True,
                heartbeat_company_ref="company.acme",
                heartbeat_checked_at="2026-05-16T12:30:00Z",
                heartbeat_stale_after="2026-05-16T12:45:00Z",
            )

            self.assertTrue(result["ok"])
            self.assertEqual(str(source), result["source_root"])
            self.assertEqual(str(target), result["target_root"])
            self.assertFalse(target.is_symlink())
            self.assertTrue(target.is_dir())
            self.assertTrue(compat.is_symlink())
            self.assertEqual(target.resolve(), compat.resolve())
            self.assertTrue(source.exists())

            capability_path = (
                target
                / "company-capability"
                / "company-capability-read-model.json"
            )
            preflight_path = (
                target
                / "company-preflight"
                / "company-preflight-results-read-model.json"
            )
            freshness_path = (
                target
                / "source-freshness"
                / "source-freshness-read-model.json"
            )
            self.assertTrue(capability_path.exists())
            self.assertTrue(preflight_path.exists())
            self.assertTrue(freshness_path.exists())

            capability = json.loads(capability_path.read_text(encoding="utf-8"))
            company_refs = {company["company_ref"] for company in capability["companies"]}
            self.assertEqual(
                {"company.acme", "company.demo_co", "company.examplecorp"},
                company_refs,
            )
            preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
            self.assertEqual(1, len(preflight["results"]))
            freshness = json.loads(freshness_path.read_text(encoding="utf-8"))
            latest = freshness["latest_by_scope_key"]
            self.assertTrue(
                any(
                    result["connector_ref"] == "connector.acme.local"
                    and result["status"] == "failed"
                    and result.get("error", {}).get("code") == "path_missing"
                    for result in latest.values()
                )
            )

    def test_migration_refuses_existing_real_target(self):
        with TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            target = base / "target"
            source.mkdir()
            target.mkdir()

            with self.assertRaises(FileExistsError):
                migrate_state_root(
                    project_root=ROOT,
                    source_root=source,
                    target_root=target,
                    compat_link=None,
                    validate_company_ref=None,
                    refresh=False,
                    heartbeat_company_ref=None,
                    heartbeat_checked_at=None,
                    heartbeat_stale_after=None,
                )


def _pack_with_local_path(name: str, local_path: Path):
    pack = load_json(PACK_DIR / name)
    source_ref = f"local:{local_path}"
    for connector in pack["source_connectors"]:
        if connector["connector_type"] == "local_path":
            connector["source_ref"] = source_ref
    pack["raw_corpus"]["source_refs"] = [
        source_ref if value.startswith("local:") else value
        for value in pack["raw_corpus"]["source_refs"]
    ]
    return pack


if __name__ == "__main__":
    unittest.main()
