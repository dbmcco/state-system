from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.contracts import load_json, validate_schema
from state_system.fleet_refresh import run_fleet_refresh
from state_system.instance_capability import InstanceCapabilityRuntime
from state_system.instance_preflight import InstancePreflightRuntime
from state_system.instance_source_freshness import InstanceSourceFreshnessRuntime
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]


class FleetRefreshTests(unittest.TestCase):
    def test_manifest_example_validates(self):
        manifest = load_json(
            ROOT / "examples" / "fleet-refresh" / "fleet-refresh-core-example.json"
        )
        schema = load_json(ROOT / "schemas" / "fleet-refresh-manifest.schema.json")
        self.assertEqual([], validate_schema(manifest, schema))

    def test_refresh_regenerates_instance_package_and_report(self):
        with TemporaryDirectory() as directory:
            state_root = Path(directory)
            _seed_personal_state(state_root)
            manifest = _manifest(state_root)

            report = run_fleet_refresh(
                manifest,
                project_root=ROOT,
                checked_at="2026-05-19T20:00:00Z",
                stale_after="2026-05-19T21:00:00Z",
                output_dir=state_root / "fleet-refresh",
            )

            self.assertTrue(report["ok"], report)
            instance = report["instances"][0]
            self.assertEqual("refreshed", instance["status"])
            self.assertTrue(Path(instance["package_path"]).exists())
            self.assertTrue(
                (state_root / "instance-understanding" / "instance-understanding-surface-read-model.json").exists()
            )
            self.assertTrue((state_root / "fleet-refresh" / "fleet-refresh-report.json").exists())
            package = load_json(Path(instance["package_path"]))
            folio = _source(package, "connector.personal.folio")
            self.assertEqual("fresh", folio["freshness_status"])
            self.assertEqual("ready", folio["understanding_status"])

    def test_required_adapter_failure_fails_instance_without_shell(self):
        with TemporaryDirectory() as directory:
            state_root = Path(directory)
            _seed_personal_state(state_root)
            manifest = _manifest(
                state_root,
                adapter_commands=[
                    {
                        "id": "adapter.fail",
                        "argv": ["python3", "-c", "import sys; sys.exit(7)"],
                        "required": True,
                    }
                ],
            )

            report = run_fleet_refresh(
                manifest,
                project_root=ROOT,
                checked_at="2026-05-19T20:00:00Z",
                stale_after="2026-05-19T21:00:00Z",
            )

            self.assertFalse(report["ok"])
            command = report["instances"][0]["adapter_commands"][0]
            self.assertEqual("failed", command["status"])
            self.assertEqual(7, command["returncode"])

    def test_dry_run_skips_adapter_and_package_write(self):
        with TemporaryDirectory() as directory:
            state_root = Path(directory)
            _seed_personal_state(state_root)
            manifest = _manifest(
                state_root,
                adapter_commands=[
                    {
                        "id": "adapter.not_run",
                        "argv": ["python3", "-c", "raise SystemExit(9)"],
                    }
                ],
            )

            report = run_fleet_refresh(
                manifest,
                project_root=ROOT,
                checked_at="2026-05-19T20:00:00Z",
                stale_after="2026-05-19T21:00:00Z",
                dry_run=True,
            )

            self.assertTrue(report["ok"], report)
            self.assertEqual("planned", report["instances"][0]["status"])
            self.assertEqual(
                "planned",
                report["instances"][0]["adapter_commands"][0]["status"],
            )
            self.assertFalse(
                (
                    state_root
                    / "state"
                    / "instance-agent-packages"
                    / "instance_agent_package.braydon_personal.samantha.json"
                ).exists()
            )

    def test_cli_runs_pressure_after_refresh(self):
        with TemporaryDirectory() as directory:
            state_root = Path(directory)
            _seed_personal_state(state_root)
            pressure_path = state_root / "pressure.json"
            pressure_path.write_text(
                json.dumps(
                    {
                        "id": "package_pressure_question_registry.fleet_test",
                        "generated_at": "2026-05-19T20:00:00Z",
                        "invariant": {
                            "assertions_check_package_fields_not_answer_text": True,
                            "private_corpora_not_required": True,
                            "gap_visibility_is_tested": True
                        },
                        "cases": [
                            {
                                "id": "package_pressure_question.fleet_folio_ready",
                                "status": "ready",
                                "question": "Is Folio ready?",
                                "intent": "Folio source readiness should survive refresh.",
                                "package_id": "instance_agent_package.braydon_personal.samantha",
                                "assertions": {
                                    "required_source_status": [
                                        {
                                            "connector_ref": "connector.personal.folio",
                                            "freshness_status": "fresh",
                                            "understanding_status": "ready"
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            manifest = _manifest(state_root)
            manifest["pressure"] = {"registry": str(pressure_path)}
            manifest_path = state_root / "fleet-refresh.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            output = _run_cli(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    str(state_root),
                    "fleet-refresh-run",
                    str(manifest_path),
                    "--checked-at",
                    "2026-05-19T20:00:00Z",
                    "--stale-after",
                    "2026-05-19T21:00:00Z",
                ]
            )

            self.assertTrue(output["ok"], output)
            self.assertEqual(0, output["pressure_report"]["failed_count"])


def _seed_personal_state(state_root: Path) -> None:
    stores = StateStoreBundle(state_root)
    pack = load_json(ROOT / "examples" / "instance-capability" / "instance-braydon-personal.json")
    InstanceCapabilityRuntime(stores).seed([pack])
    InstancePreflightRuntime(stores).record(
        {
            "preflight_ref": "preflight.state_instance.braydon_personal.connector.personal.folio",
            "instance_ref": "state_instance.braydon_personal",
            "connector_ref": "connector.personal.folio",
            "source_ref": "folio:tenant:personal",
            "connector_type": "folio",
            "status": "passed",
            "checked_at": "2026-05-19T19:59:00Z",
            "stale_after": "2026-05-19T21:00:00Z",
            "evidence_refs": ["preflight:folio:passed"],
        }
    )
    InstanceSourceFreshnessRuntime(stores).record(
        {
            "instance_ref": "state_instance.braydon_personal",
            "connector_ref": "connector.personal.folio",
            "source_ref": "folio:tenant:personal",
            "connector_type": "folio",
            "status": "fresh",
            "checked_at": "2026-05-19T19:59:00Z",
            "source_watermark": "folio.indexed_at:2026-05-19T19:58:00Z",
            "stale_after": "2026-05-19T21:00:00Z",
            "evidence_refs": ["freshness:folio:fresh"],
        }
    )


def _manifest(
    state_root: Path,
    *,
    adapter_commands: list[dict] | None = None,
) -> dict:
    return {
        "id": "fleet_refresh_manifest.test",
        "instances": [
            {
                "id": "fleet_instance.personal",
                "state_root": str(state_root),
                "instance_ref": "state_instance.braydon_personal",
                "agent_ref": "agent.samantha",
                "persona_ref": "persona.samantha",
                "package_id": "instance_agent_package.braydon_personal.samantha",
                "preflight_mode": "export_only",
                "adapter_commands": adapter_commands or [],
            }
        ],
    }


def _source(package: dict, connector_ref: str) -> dict:
    return next(
        source
        for source in package["source_context"]["source_readiness"]
        if source["connector_ref"] == connector_ref
    )


def _run_cli(argv: list[str]) -> dict:
    from io import StringIO

    output = StringIO()
    code = cli.main(argv, stdout=output)
    payload = json.loads(output.getvalue())
    if code != 0:
        raise AssertionError(payload)
    return payload
