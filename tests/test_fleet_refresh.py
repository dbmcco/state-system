from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time
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
            # the strategic-staleness read model is produced on every refresh
            # (honest empty until a reviewer is wired) so agents always have a
            # current projection to read
            self.assertTrue(
                (
                    state_root
                    / "strategic-staleness"
                    / "strategic-staleness-read-model.json"
                ).exists()
            )
            self.assertIn(
                "strategic_staleness", instance["read_model_paths"]
            )
            package = load_json(Path(instance["package_path"]))
            kb = _source(package, "connector.personal.kb")
            self.assertEqual("fresh", kb["freshness_status"])
            self.assertEqual("ready", kb["understanding_status"])

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

    def test_adapter_timeout_terminates_child_process_group(self):
        with TemporaryDirectory() as directory:
            state_root = Path(directory)
            _seed_personal_state(state_root)
            child_pid_path = state_root / "child.pid"
            manifest = _manifest(
                state_root,
                adapter_commands=[
                    {
                        "id": "adapter.timeout",
                        "argv": [
                            sys.executable,
                            "-c",
                            (
                                "import pathlib, subprocess, sys, time; "
                                "child = subprocess.Popen(['sleep', '30'], start_new_session=True); "
                                "pathlib.Path(sys.argv[1]).write_text(str(child.pid)); "
                                "time.sleep(30)"
                            ),
                            str(child_pid_path),
                        ],
                        "required": True,
                        "timeout_seconds": 1,
                    }
                ],
            )

            report = run_fleet_refresh(
                manifest,
                project_root=ROOT,
                checked_at="2026-05-19T20:00:00Z",
                stale_after="2026-05-19T21:00:00Z",
            )

            command = report["instances"][0]["adapter_commands"][0]
            self.assertEqual("failed", command["status"])
            self.assertIn("timed out", command["error"])
            child_pid = int(child_pid_path.read_text())
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                try:
                    os.kill(child_pid, 0)
                except ProcessLookupError:
                    break
                time.sleep(0.05)
            else:
                self.fail(f"timed-out adapter child still running: {child_pid}")

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
                    / "instance_agent_package.sample_personal.nova.json"
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
                                "id": "package_pressure_question.fleet_knowledge_store_ready",
                                "status": "ready",
                                "question": "Is Knowledge Store ready?",
                                "intent": "Knowledge Store source readiness should survive refresh.",
                                "package_id": "instance_agent_package.sample_personal.nova",
                                "assertions": {
                                    "required_source_status": [
                                        {
                                            "connector_ref": "connector.personal.kb",
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
    pack = load_json(ROOT / "examples" / "instance-capability" / "instance-sample-personal.json")
    InstanceCapabilityRuntime(stores).seed([pack])
    InstancePreflightRuntime(stores).record(
        {
            "preflight_ref": "preflight.state_instance.sample_personal.connector.personal.kb",
            "instance_ref": "state_instance.sample_personal",
            "connector_ref": "connector.personal.kb",
            "source_ref": "kb:tenant:personal",
            "connector_type": "kb",
            "status": "passed",
            "checked_at": "2026-05-19T19:59:00Z",
            "stale_after": "2026-05-19T21:00:00Z",
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
            "stale_after": "2026-05-19T21:00:00Z",
            "watermark_basis": "source_index",
            "latest_indexed_at": "2026-05-19T19:58:00Z",
            "status_reason": "latest indexed corpus timestamp is inside policy",
            "evidence_refs": ["freshness:kb:fresh"],
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
                "instance_ref": "state_instance.sample_personal",
                "agent_ref": "agent.nova",
                "persona_ref": "persona.nova",
                "package_id": "instance_agent_package.sample_personal.nova",
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
