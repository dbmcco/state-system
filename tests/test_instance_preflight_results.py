from __future__ import annotations

from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system import cli
from state_system.contracts import load_json, schema_for_example, validate_schema
from state_system.instance_capability import InstanceCapabilityRuntime
from state_system.instance_preflight import (
    InstancePreflightRuntime,
    build_instance_preflight_read_model,
    run_instance_preflight,
)
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = (
    ROOT
    / "examples"
    / "instance-preflight"
    / "instance-preflight-braydon-personal-folio.json"
)


class InstancePreflightResultTests(unittest.TestCase):
    def test_example_is_schema_validated_as_instance_preflight_result(self):
        schema_name = schema_for_example(EXAMPLE.name)

        self.assertEqual("instance-preflight-result.schema.json", schema_name)
        errors = validate_schema(
            load_json(EXAMPLE),
            load_json(ROOT / "schemas" / schema_name),
        )
        self.assertEqual([], errors)

    def test_record_persists_instance_preflight_as_live_access_evidence_only(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            runtime = InstancePreflightRuntime(stores)

            record = runtime.record(
                {
                    "preflight_ref": (
                        "preflight.state_instance.braydon_personal."
                        "connector.personal.folio"
                    ),
                    "instance_ref": "state_instance.braydon_personal",
                    "connector_ref": "connector.personal.folio",
                    "source_ref": "folio:tenant:personal",
                    "connector_type": "folio",
                    "status": "passed",
                    "checked_at": "2026-05-16T19:42:47Z",
                    "stale_after": "2026-05-16T20:42:47Z",
                    "evidence_refs": [
                        "local-path:/Users/braydon/projects/experiments/folio"
                    ],
                    "detail": "folio_root exists.",
                }
            )

            self.assertEqual(
                "state_instance.braydon_personal|connector.personal.folio|"
                "folio:tenant:personal|preflight.state_instance.braydon_personal."
                "connector.personal.folio||||",
                record["scope_key"],
            )
            self.assertTrue(
                record["id"].startswith(
                    "instance_preflight_result.state_instance.braydon_personal"
                )
            )
            self.assertTrue(record["proves_live_access"])
            self.assertFalse(record["authorizes_execution"])
            self.assertEqual(record, runtime.read(record["id"]))

    def test_read_model_exports_latest_results_by_preflight_ref(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            runtime = InstancePreflightRuntime(stores)
            base = {
                "preflight_ref": (
                    "preflight.state_instance.braydon_personal."
                    "connector.personal.folio"
                ),
                "instance_ref": "state_instance.braydon_personal",
                "connector_ref": "connector.personal.folio",
                "source_ref": "folio:tenant:personal",
                "connector_type": "folio",
                "stale_after": "2026-05-16T20:42:47Z",
            }
            runtime.record(
                {
                    **base,
                    "status": "failed",
                    "checked_at": "2026-05-16T19:00:00Z",
                    "evidence_refs": ["preflight:folio:failed"],
                    "error": {"code": "missing_root", "message": "Folio root missing."},
                }
            )
            runtime.record(
                {
                    **base,
                    "status": "passed",
                    "checked_at": "2026-05-16T19:42:47Z",
                    "evidence_refs": ["preflight:folio:passed"],
                }
            )

            read_model = build_instance_preflight_read_model(stores)

            self.assertEqual("instance_preflight_result_read_model", read_model["id"])
            latest = read_model["latest_by_preflight_ref"][base["preflight_ref"]]
            self.assertEqual("passed", latest["status"])
            self.assertFalse(read_model["invariant"]["authorizes_execution"])

    def test_planned_preflight_is_not_live_access_evidence(self):
        with TemporaryDirectory() as directory:
            stores = StateStoreBundle(Path(directory))
            runtime = InstancePreflightRuntime(stores)

            record = runtime.record(
                {
                    "preflight_ref": (
                        "preflight.state_instance.braydon_personal."
                        "connector.personal.agentmem"
                    ),
                    "instance_ref": "state_instance.braydon_personal",
                    "connector_ref": "connector.personal.agentmem",
                    "source_ref": "agentmem:tenant:braydon",
                    "connector_type": "agentmem",
                    "status": "planned",
                    "checked_at": "2026-05-16T19:42:47Z",
                    "stale_after": "2026-05-16T20:42:47Z",
                    "evidence_refs": ["preflight:agentmem:planned"],
                }
            )

            errors = validate_schema(
                record,
                load_json(ROOT / "schemas" / "instance-preflight-result.schema.json"),
            )
            self.assertEqual([], errors)
            self.assertFalse(record["proves_live_access"])

    def test_runner_checks_local_path_and_plans_delegated_connectors(self):
        with TemporaryDirectory() as directory, TemporaryDirectory() as source_root:
            stores = StateStoreBundle(Path(directory))
            InstanceCapabilityRuntime(stores).seed(
                [
                    _instance_pack(
                        source_root=source_root,
                        connectors=[
                            {
                                "id": "connector.personal.projects",
                                "connector_type": "local_path",
                                "source_ref": f"local:{source_root}",
                            },
                            {
                                "id": "connector.personal.msgvault",
                                "connector_type": "msgvault",
                                "source_ref": "msgvault:tenant:personal-email",
                            },
                        ],
                    )
                ]
            )

            summary = run_instance_preflight(
                stores,
                instance_ref="state_instance.braydon_personal",
                checked_at="2026-05-17T10:25:00Z",
                stale_after="2026-05-17T10:40:00Z",
            )

            self.assertEqual(2, summary["count"])
            results = InstancePreflightRuntime(stores).list_results()
            by_connector = {result["connector_ref"]: result for result in results}
            self.assertEqual(
                "passed",
                by_connector["connector.personal.projects"]["status"],
            )
            self.assertTrue(
                by_connector["connector.personal.projects"]["proves_live_access"]
            )
            self.assertEqual(
                "planned",
                by_connector["connector.personal.msgvault"]["status"],
            )
            self.assertFalse(
                by_connector["connector.personal.msgvault"]["proves_live_access"]
            )
            self.assertIn(
                "delegated",
                by_connector["connector.personal.msgvault"]["detail"],
            )

    def test_cli_records_lists_and_exports_instance_preflight_results(self):
        with TemporaryDirectory() as directory, TemporaryDirectory() as output_dir:
            output = StringIO()
            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "instance-preflight-record",
                    "--preflight-ref",
                    "preflight.state_instance.braydon_personal.connector.personal.folio",
                    "--instance-ref",
                    "state_instance.braydon_personal",
                    "--connector-ref",
                    "connector.personal.folio",
                    "--source-ref",
                    "folio:tenant:personal",
                    "--connector-type",
                    "folio",
                    "--status",
                    "passed",
                    "--checked-at",
                    "2026-05-16T19:42:47Z",
                    "--stale-after",
                    "2026-05-16T20:42:47Z",
                    "--evidence-ref",
                    "preflight:folio:passed",
                ],
                stdout=output,
            )

            self.assertEqual(0, code, output.getvalue())
            payload = json.loads(output.getvalue())
            self.assertEqual("passed", payload["preflight_result"]["status"])

            list_output = StringIO()
            list_code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "instance-preflight-list",
                ],
                stdout=list_output,
            )

            self.assertEqual(0, list_code, list_output.getvalue())
            self.assertEqual(1, len(json.loads(list_output.getvalue())["results"]))

            export_output = StringIO()
            export_code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "instance-preflight-export",
                    "--output-dir",
                    output_dir,
                ],
                stdout=export_output,
            )

            self.assertEqual(0, export_code, export_output.getvalue())
            read_model_path = Path(json.loads(export_output.getvalue())["read_model_path"])
            read_model = json.loads(read_model_path.read_text(encoding="utf-8"))
            self.assertEqual(1, len(read_model["results"]))

    def test_cli_bounds_record_filename_for_long_optional_scope_fields(self):
        with TemporaryDirectory() as directory:
            output = StringIO()
            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "instance-preflight-record",
                    "--preflight-ref",
                    "preflight.state_instance.braydon_personal.connector.personal.garmin_connect",
                    "--instance-ref",
                    "state_instance.braydon_personal",
                    "--connector-ref",
                    "connector.personal.garmin_connect",
                    "--source-ref",
                    "garmin-connect:account:braydon",
                    "--connector-type",
                    "garmin_connect",
                    "--tool-ref",
                    "tool.garmin_connect.read.long.optional.surface.identifier",
                    "--action-ref",
                    "action_surface.personal.read_garmin_connect.with.extra.scope",
                    "--agent-ref",
                    "persona.samantha.personal_state_agent.with.long.qualifier",
                    "--runner-ref",
                    "runner.paia.codex.local_runtime.with.long.qualifier",
                    "--status",
                    "planned",
                    "--checked-at",
                    "2026-05-17T15:16:52Z",
                    "--stale-after",
                    "2026-05-17T16:16:52Z",
                    "--evidence-ref",
                    "capability-pack:braydon-personal:garmin-connect:planned",
                ],
                stdout=output,
            )

            self.assertEqual(0, code, output.getvalue())
            payload = json.loads(output.getvalue())
            record = payload["preflight_result"]
            self.assertLessEqual(len(f"{record['id']}.json"), 160)
            self.assertIn(
                "tool.garmin_connect.read.long.optional.surface.identifier",
                record["scope_key"],
            )
            path = (
                Path(directory)
                / "state"
                / "instance-preflight-results"
                / f"{record['id']}.json"
            )
            self.assertTrue(path.exists())

    def test_cli_runs_instance_preflight_for_declared_connectors(self):
        with TemporaryDirectory() as directory, TemporaryDirectory() as source_root:
            stores = StateStoreBundle(Path(directory))
            InstanceCapabilityRuntime(stores).seed(
                [
                    _instance_pack(
                        source_root=source_root,
                        connectors=[
                            {
                                "id": "connector.personal.projects",
                                "connector_type": "local_path",
                                "source_ref": f"local:{source_root}",
                            }
                        ],
                    )
                ]
            )

            output = StringIO()
            code = cli.main(
                [
                    "--project-root",
                    str(ROOT),
                    "--state-root",
                    directory,
                    "instance-preflight-run",
                    "--instance-ref",
                    "state_instance.braydon_personal",
                    "--checked-at",
                    "2026-05-17T10:25:00Z",
                    "--stale-after",
                    "2026-05-17T10:40:00Z",
                ],
                stdout=output,
            )

            self.assertEqual(0, code, output.getvalue())
            payload = json.loads(output.getvalue())
            self.assertEqual(1, payload["count"])
            self.assertEqual("passed", payload["results"][0]["status"])


def _instance_pack(*, source_root: str, connectors: list[dict]):
    source_refs = [connector["source_ref"] for connector in connectors]
    return {
        "id": "instance_capability_pack.braydon_personal",
        "instance_ref": "state_instance.braydon_personal",
        "primary_entity_ref": "entity.braydon",
        "entity_kind": "person",
        "generated_at": "2026-05-17T10:20:00Z",
        "identity": {
            "name": "Braydon Personal State",
            "summary": "Test fixture.",
            "primary_agent_refs": [],
            "oversight_agent_refs": [],
        },
        "source_connectors": connectors,
        "raw_corpus": {
            "definition": "Test source refs.",
            "source_refs": source_refs,
        },
        "evidence_index": {
            "definition": "Test indexes.",
            "index_refs": [],
        },
        "index_manifests": [],
        "memory_refs": [],
        "operating_picture_refs": [],
        "action_surface": {
            "definition": "Test actions.",
            "action_refs": [],
        },
        "tool_capability_bindings": [],
        "governance": {
            "definition": "Test governance.",
            "governance_refs": [],
        },
        "connector_preflight": {
            "definition": "Preflight proves live access only.",
            "required_checks": [],
        },
        "runtime_constraints": {
            "constraints": ["Do not copy raw corpora."],
        },
        "freshness": {
            "as_of": "2026-05-17T10:20:00Z",
            "stale_after": "2026-05-17T10:40:00Z",
            "watermark_refs": [f"local:{source_root}"],
        },
        "invariant": {
            "declares_context": True,
            "proves_live_access": False,
            "authorizes_execution": False,
            "live_access_proven_by": "connector_preflight",
            "protected_action_authorized_by": "governance",
        },
    }


if __name__ == "__main__":
    unittest.main()
