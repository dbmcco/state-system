# State Instance Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add canonical StateInstance and InstanceCapabilityPack contracts so company, personal, and project state roots share the same substrate without forcing personal state through company-shaped fields.

**Architecture:** Introduce `StateInstance` as the deployed runtime identity and `InstanceCapabilityPack` as the canonical capability declaration keyed by `instance_ref`, `primary_entity_ref`, and `entity_kind`. Keep existing company capability behavior as a compatibility/specialization layer while new understanding and index contracts move toward instance refs.

**Tech Stack:** Python standard library, JSON Schema draft 2020-12, existing `state_system` file-backed stores, `unittest`, existing CLI validation flow.

---

### Task 1: Add StateInstance Schema And Fixtures

**Files:**
- Create: `schemas/state-instance.schema.json`
- Create: `examples/instances/state-instance-lfw.json`
- Create: `examples/instances/state-instance-acme-ops.json`
- Modify: `state_system/contracts.py`
- Test: `tests/test_state_instance_contract.py`

- [ ] **Step 1: Write the failing schema validation test**

Add `tests/test_state_instance_contract.py`:

```python
from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]


class StateInstanceContractTests(unittest.TestCase):
    def test_lfw_and_personal_state_instances_are_schema_valid(self):
        schema = _load_json(ROOT / "schemas/state-instance.schema.json")
        validator = Draft202012Validator(schema)

        for filename in (
            "state-instance-lfw.json",
            "state-instance-acme-ops.json",
        ):
            with self.subTest(filename=filename):
                instance = _load_json(ROOT / "examples/instances" / filename)
                errors = sorted(validator.iter_errors(instance), key=str)
                self.assertEqual([], [error.message for error in errors])

    def test_personal_instance_uses_entity_not_company_ref(self):
        instance = _load_json(
            ROOT / "examples/instances/state-instance-acme-ops.json"
        )

        self.assertEqual("state_instance.acme_ops", instance["instance_ref"])
        self.assertEqual("entity.acme_user", instance["primary_entity_ref"])
        self.assertEqual("person", instance["entity_kind"])
        self.assertNotIn("company_ref", instance)


def _load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
python3 -m unittest tests/test_state_instance_contract.py
```

Expected: fail because `schemas/state-instance.schema.json` and fixtures do not exist.

- [ ] **Step 3: Add the minimal schema and fixtures**

Create `schemas/state-instance.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://state-system.local/schemas/state-instance.schema.json",
  "title": "StateInstance",
  "type": "object",
  "required": [
    "id",
    "instance_ref",
    "kind",
    "display_name",
    "runtime_root",
    "primary_entity_ref",
    "entity_kind",
    "governance_refs",
    "sensitivity_default",
    "created_at",
    "updated_at"
  ],
  "properties": {
    "id": { "type": "string" },
    "instance_ref": { "type": "string", "pattern": "^state_instance\\.[a-z0-9_.-]+$" },
    "kind": {
      "type": "string",
      "enum": ["company", "personal", "project", "portfolio", "household", "research", "other"]
    },
    "display_name": { "type": "string" },
    "runtime_root": { "type": "string" },
    "primary_entity_ref": { "type": "string", "pattern": "^entity\\.[a-z0-9_.-]+$" },
    "entity_kind": {
      "type": "string",
      "enum": ["company", "person", "project", "portfolio", "household", "research", "other"]
    },
    "governance_refs": {
      "type": "array",
      "items": { "type": "string" }
    },
    "sensitivity_default": {
      "type": "string",
      "enum": ["public", "internal", "confidential", "private", "restricted"]
    },
    "federates_with": {
      "type": "array",
      "items": { "type": "string", "pattern": "^state_instance\\.[a-z0-9_.-]+$" },
      "default": []
    },
    "created_at": { "type": "string", "format": "date-time" },
    "updated_at": { "type": "string", "format": "date-time" },
    "notes": { "type": "string" }
  },
  "additionalProperties": false
}
```

Create `examples/instances/state-instance-lfw.json`:

```json
{
  "id": "state_instance.lfw",
  "instance_ref": "state_instance.lfw",
  "kind": "company",
  "display_name": "Lightforge Works State",
  "runtime_root": "/path/to/state-system-runtime",
  "primary_entity_ref": "entity.lfw",
  "entity_kind": "company",
  "governance_refs": [
    "governance.lfw.external_action",
    "governance.lfw.crm_mutation"
  ],
  "sensitivity_default": "confidential",
  "federates_with": [],
  "created_at": "2026-05-16T18:00:00Z",
  "updated_at": "2026-05-16T18:00:00Z"
}
```

Create `examples/instances/state-instance-acme-ops.json`:

```json
{
  "id": "state_instance.acme_ops",
  "instance_ref": "state_instance.acme_ops",
  "kind": "personal",
  "display_name": "Acme User Personal State",
  "runtime_root": "/path/to/personal-state",
  "primary_entity_ref": "entity.acme_user",
  "entity_kind": "person",
  "governance_refs": [
    "governance.acme_user.personal_default"
  ],
  "sensitivity_default": "private",
  "federates_with": [
    "state_instance.lfw",
    "state_instance.synthyra",
    "state_instance.navicyte",
    "state_instance.plum"
  ],
  "created_at": "2026-05-16T18:00:00Z",
  "updated_at": "2026-05-16T18:00:00Z"
}
```

- [ ] **Step 4: Register the schema in validation if needed**

Inspect `state_system/contracts.py`. If it uses an explicit filename list, add `state-instance.schema.json`. If it discovers all schemas automatically, make no change.

- [ ] **Step 5: Run the focused test**

Run:

```bash
python3 -m unittest tests/test_state_instance_contract.py
```

Expected: pass.

### Task 2: Add InstanceCapabilityPack Schema And Fixture

**Files:**
- Create: `schemas/instance-capability-pack.schema.json`
- Create: `examples/instance-capability/instance-acme-ops.json`
- Create: `examples/instance-capability/instance-lfw.json`
- Test: `tests/test_instance_capability_pack.py`

- [ ] **Step 1: Write the failing validation tests**

Add `tests/test_instance_capability_pack.py`:

```python
from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]


class InstanceCapabilityPackTests(unittest.TestCase):
    def test_personal_and_lfw_instance_packs_are_schema_valid(self):
        schema = _load_json(ROOT / "schemas/instance-capability-pack.schema.json")
        validator = Draft202012Validator(schema)

        for filename in ("instance-acme-ops.json", "instance-lfw.json"):
            with self.subTest(filename=filename):
                pack = _load_json(ROOT / "examples/instance-capability" / filename)
                errors = sorted(validator.iter_errors(pack), key=str)
                self.assertEqual([], [error.message for error in errors])

    def test_personal_pack_declares_workboard_agentmem_relationships_and_federated_work_instances(self):
        pack = _load_json(
            ROOT / "examples/instance-capability/instance-acme-ops.json"
        )

        connector_types = {connector["connector_type"] for connector in pack["source_connectors"]}
        self.assertIn("paia_workboard", connector_types)
        self.assertIn("agentmem", connector_types)
        self.assertIn("relationship_substrate", connector_types)
        self.assertIn("state_system_instance", connector_types)
        self.assertEqual("entity.acme_user", pack["primary_entity_ref"])
        self.assertEqual("person", pack["entity_kind"])
        self.assertNotIn("company_ref", pack)

    def test_index_scopes_include_federated_vector_taxonomy(self):
        pack = _load_json(
            ROOT / "examples/instance-capability/instance-acme-ops.json"
        )
        scopes = {manifest["scope"] for manifest in pack["index_manifests"]}

        self.assertIn("raw_source_index", scopes)
        self.assertIn("memory_index", scopes)
        self.assertIn("operational_index", scopes)
        self.assertIn("interpreted_state_index", scopes)
        relationship_index = next(
            manifest
            for manifest in pack["index_manifests"]
            if manifest["index_ref"] == "index.personal.relationship_substrate.network"
        )
        self.assertEqual("relationship_index", relationship_index["scope"])


def _load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
python3 -m unittest tests/test_instance_capability_pack.py
```

Expected: fail because the schema and fixtures do not exist.

- [ ] **Step 3: Add minimal schema**

Create `schemas/instance-capability-pack.schema.json` by adapting the existing company capability shape, but make these fields canonical:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://state-system.local/schemas/instance-capability-pack.schema.json",
  "title": "InstanceCapabilityPack",
  "type": "object",
  "required": [
    "id",
    "instance_ref",
    "primary_entity_ref",
    "entity_kind",
    "generated_at",
    "identity",
    "source_connectors",
    "raw_corpus",
    "evidence_index",
    "index_manifests",
    "memory_refs",
    "operating_picture_refs",
    "action_surface",
    "tool_capability_bindings",
    "governance",
    "connector_preflight",
    "runtime_constraints",
    "freshness",
    "invariant"
  ],
  "properties": {
    "id": { "type": "string" },
    "instance_ref": { "type": "string", "pattern": "^state_instance\\.[a-z0-9_.-]+$" },
    "primary_entity_ref": { "type": "string", "pattern": "^entity\\.[a-z0-9_.-]+$" },
    "entity_kind": {
      "type": "string",
      "enum": ["company", "person", "project", "portfolio", "household", "research", "other"]
    },
    "generated_at": { "type": "string" },
    "identity": {
      "type": "object",
      "required": ["name", "summary", "primary_agent_refs"],
      "properties": {
        "name": { "type": "string" },
        "summary": { "type": "string" },
        "primary_agent_refs": { "type": "array", "items": { "type": "string" } },
        "oversight_agent_refs": { "type": "array", "items": { "type": "string" }, "default": [] }
      }
    },
    "source_connectors": { "type": "array", "items": { "$ref": "#/$defs/source_connector" } },
    "raw_corpus": { "$ref": "#/$defs/ref_list_with_definition" },
    "evidence_index": { "$ref": "#/$defs/ref_list_with_definition_index" },
    "index_manifests": { "type": "array", "items": { "$ref": "#/$defs/index_manifest" } },
    "memory_refs": { "type": "array", "items": { "type": "string" } },
    "operating_picture_refs": { "type": "array", "items": { "type": "string" } },
    "action_surface": { "$ref": "#/$defs/ref_list_with_definition_action" },
    "tool_capability_bindings": { "type": "array", "items": { "$ref": "#/$defs/tool_capability_binding" } },
    "governance": {
      "type": "object",
      "required": ["definition", "governance_refs"],
      "properties": {
        "definition": { "type": "string" },
        "governance_refs": { "type": "array", "items": { "type": "string" } }
      }
    },
    "connector_preflight": {
      "type": "object",
      "required": ["definition", "required_checks"],
      "properties": {
        "definition": { "type": "string" },
        "required_checks": { "type": "array", "items": { "$ref": "#/$defs/preflight_check" } }
      }
    },
    "runtime_constraints": {
      "type": "object",
      "required": ["definition", "constraints"],
      "properties": {
        "definition": { "type": "string" },
        "constraints": { "type": "array", "items": { "type": "string" } }
      }
    },
    "freshness": {
      "type": "object",
      "required": ["as_of", "stale_after", "watermark_refs"],
      "properties": {
        "as_of": { "type": "string" },
        "stale_after": { "type": "string" },
        "watermark_refs": { "type": "array", "items": { "type": "string" } }
      }
    },
    "invariant": {
      "type": "object",
      "required": ["declares_context", "proves_live_access", "authorizes_execution", "live_access_proven_by", "protected_action_authorized_by"],
      "properties": {
        "declares_context": { "type": "boolean" },
        "proves_live_access": { "type": "boolean" },
        "authorizes_execution": { "type": "boolean" },
        "live_access_proven_by": { "type": "string" },
        "protected_action_authorized_by": { "type": "string" }
      }
    }
  },
  "$defs": {
    "ref_list_with_definition": {
      "type": "object",
      "required": ["definition", "source_refs"],
      "properties": {
        "definition": { "type": "string" },
        "source_refs": { "type": "array", "items": { "type": "string" } }
      }
    },
    "ref_list_with_definition_index": {
      "type": "object",
      "required": ["definition", "index_refs"],
      "properties": {
        "definition": { "type": "string" },
        "index_refs": { "type": "array", "items": { "type": "string" } }
      }
    },
    "ref_list_with_definition_action": {
      "type": "object",
      "required": ["definition", "action_refs"],
      "properties": {
        "definition": { "type": "string" },
        "action_refs": { "type": "array", "items": { "type": "string" } }
      }
    },
    "source_connector": {
      "type": "object",
      "required": ["id", "connector_type", "source_ref", "owner"],
      "properties": {
        "id": { "type": "string" },
        "connector_type": {
          "type": "string",
          "enum": ["folio", "msgvault", "gws_drive", "gws_account", "linear", "local_path", "zulip", "repo", "crm", "docs", "agentmem", "paia_workboard", "relationship_substrate", "state_system_instance"]
        },
        "source_ref": { "type": "string" },
        "owner": { "type": "string", "enum": ["state_system", "paia_runtime", "source_system", "agentmem"] },
        "declared": { "type": "boolean" },
        "access_mode": { "type": "string", "enum": ["read", "write", "read_write"] },
        "governance_refs": { "type": "array", "items": { "type": "string" } }
      }
    },
    "index_manifest": {
      "type": "object",
      "required": ["index_ref", "instance_ref", "owner", "backend", "scope", "record_kinds", "source_refs", "connector_refs", "query_surface", "status"],
      "properties": {
        "index_ref": { "type": "string" },
        "instance_ref": { "type": "string" },
        "primary_entity_ref": { "type": "string" },
        "owner": { "type": "string", "enum": ["state_system", "source_system", "paia_runtime", "agentmem"] },
        "backend": { "type": "string" },
        "scope": { "type": "string", "enum": ["raw_source_index", "memory_index", "relationship_index", "interpreted_state_index", "artifact_index", "operational_index"] },
        "record_kinds": { "type": "array", "items": { "type": "string" } },
        "source_refs": { "type": "array", "items": { "type": "string" } },
        "connector_refs": { "type": "array", "items": { "type": "string" } },
        "query_surface": {
          "type": "object",
          "required": ["type"],
          "properties": {
            "type": { "type": "string", "enum": ["paia_tool", "state_system_runtime", "source_adapter", "agentmem_service"] },
            "tool_ref": { "type": "string" },
            "endpoint_ref": { "type": "string" }
          }
        },
        "status": { "type": "string", "enum": ["declared", "planned", "disabled"] },
        "notes": { "type": "string" }
      }
    },
    "tool_capability_binding": {
      "type": "object",
      "required": ["id", "capability_ref", "tool_ref", "action_ref", "connector_refs", "required_preflight_refs", "governance_refs", "allowed_agent_refs", "exposure_policy", "proves_live_access", "authorizes_execution"],
      "properties": {
        "id": { "type": "string" },
        "capability_ref": { "type": "string" },
        "tool_ref": { "type": "string" },
        "action_ref": { "type": "string" },
        "connector_refs": { "type": "array", "items": { "type": "string" } },
        "required_preflight_refs": { "type": "array", "items": { "type": "string" } },
        "governance_refs": { "type": "array", "items": { "type": "string" } },
        "allowed_agent_refs": { "type": "array", "items": { "type": "string" } },
        "exposure_policy": { "type": "string" },
        "proves_live_access": { "type": "boolean" },
        "authorizes_execution": { "type": "boolean" }
      }
    },
    "preflight_check": {
      "type": "object",
      "required": ["id", "connector_ref", "check", "proves_live_access", "authorizes_execution"],
      "properties": {
        "id": { "type": "string" },
        "connector_ref": { "type": "string" },
        "check": { "type": "string" },
        "proves_live_access": { "type": "boolean" },
        "authorizes_execution": { "type": "boolean" }
      }
    }
  }
}
```

- [ ] **Step 4: Add minimal fixtures**

Create personal and LFW fixtures that validate against the schema. Keep them small: one or two connectors per source class is enough. The personal fixture must include `agentmem`, `paia_workboard`, `relationship_substrate`, `msgvault`, `folio`, `local_path`, and one `state_system_instance` connector to LFW.

- [ ] **Step 5: Run the focused test**

Run:

```bash
python3 -m unittest tests/test_instance_capability_pack.py
```

Expected: pass.

### Task 3: Add Instance Capability Read Model Runtime

**Files:**
- Create: `state_system/instance_capability.py`
- Modify: `state_system/stores.py`
- Modify: `state_system/cli.py`
- Test: `tests/test_instance_capability_runtime.py`

- [ ] **Step 1: Write the failing runtime test**

Add `tests/test_instance_capability_runtime.py` with a test that seeds the LFW and personal instance fixtures into a temporary state root, reads the generated read model, and asserts:

```python
self.assertEqual(
    ["state_instance.acme_ops", "state_instance.lfw"],
    [instance["instance_ref"] for instance in read_model["instances"]],
)
self.assertIn("index.personal.agentmem.memory", read_model["index_refs"])
self.assertIn("index.personal.relationship_substrate.network", read_model["index_refs"])
self.assertIn("state-system-instance:state_instance.lfw", read_model["source_refs"])
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
python3 -m unittest tests/test_instance_capability_runtime.py
```

Expected: fail because `state_system.instance_capability` and store wiring do not exist.

- [ ] **Step 3: Implement minimal read model builder**

Create `state_system/instance_capability.py` with:

```python
from __future__ import annotations

import json

from state_system.contracts import JsonObject
from state_system.stores import RecordNotFoundError, StateStoreBundle


def build_instance_capability_read_model(packs: list[JsonObject]) -> JsonObject:
    sorted_packs = sorted(packs, key=lambda pack: pack["instance_ref"])
    return {
        "id": "instance_capability_read_model",
        "artifact_type": "json_substrate",
        "generated_at": max(pack["generated_at"] for pack in sorted_packs),
        "instances": [_instance_summary(pack) for pack in sorted_packs],
        "source_refs": sorted(
            {
                source_ref
                for pack in sorted_packs
                for source_ref in pack["raw_corpus"]["source_refs"]
            }
        ),
        "evidence_index_refs": sorted(
            {
                index_ref
                for pack in sorted_packs
                for index_ref in pack["evidence_index"]["index_refs"]
            }
        ),
        "index_manifests": [
            manifest
            for pack in sorted_packs
            for manifest in pack.get("index_manifests", [])
        ],
        "index_refs": sorted(
            {
                manifest["index_ref"]
                for pack in sorted_packs
                for manifest in pack.get("index_manifests", [])
            }
        ),
        "invariant": {
            "instance_capability_pack_declares_context": True,
            "instance_capability_pack_proves_live_access": False,
            "instance_capability_pack_authorizes_execution": False,
            "live_access_proven_by": "connector_preflight",
            "protected_action_authorized_by": "governance",
        },
    }


class InstanceCapabilityRuntime:
    def __init__(self, stores: StateStoreBundle):
        self.store = stores.instance_capabilities

    def seed(self, packs: list[JsonObject]) -> JsonObject:
        created: list[str] = []
        updated: list[str] = []
        seeded: list[JsonObject] = []

        for pack in sorted(packs, key=lambda value: value["instance_ref"]):
            record_id = pack["id"]
            path = self.store.path_for(record_id)
            path.parent.mkdir(parents=True, exist_ok=True)

            if path.exists():
                updated.append(record_id)
            else:
                created.append(record_id)

            with path.open("w", encoding="utf-8") as handle:
                json.dump(pack, handle, indent=2, sort_keys=True)
                handle.write("\n")
            seeded.append({"id": record_id, "instance_ref": pack["instance_ref"]})

        return {"created": created, "updated": updated, "seeded": seeded, "count": len(seeded)}

    def read(self, record_id: str) -> JsonObject:
        return self.store.read(record_id)

    def read_instance(self, instance_ref: str) -> JsonObject:
        for pack in self.list_packs():
            if pack["instance_ref"] == instance_ref:
                return pack
        raise RecordNotFoundError(f"{instance_ref} does not exist in instance-capabilities")

    def list_packs(self) -> list[JsonObject]:
        return sorted(self.store.replay(), key=lambda pack: pack["instance_ref"])


def _instance_summary(pack: JsonObject) -> JsonObject:
    return {
        "id": pack["id"],
        "instance_ref": pack["instance_ref"],
        "primary_entity_ref": pack["primary_entity_ref"],
        "entity_kind": pack["entity_kind"],
        "name": pack["identity"]["name"],
        "source_connectors": pack["source_connectors"],
        "connector_refs": [connector["id"] for connector in pack["source_connectors"]],
        "connector_types": sorted({connector["connector_type"] for connector in pack["source_connectors"]}),
        "raw_corpus_refs": pack["raw_corpus"]["source_refs"],
        "evidence_index_refs": pack["evidence_index"]["index_refs"],
        "index_manifests": pack.get("index_manifests", []),
        "index_refs": [manifest["index_ref"] for manifest in pack.get("index_manifests", [])],
        "memory_refs": pack["memory_refs"],
        "operating_picture_refs": pack["operating_picture_refs"],
        "governance_refs": pack["governance"]["governance_refs"],
        "freshness": pack["freshness"],
        "invariant": pack["invariant"],
    }
```

- [ ] **Step 4: Wire the store and CLI minimally**

Add an `instance_capabilities` store path to `StateStoreBundle` using the existing store pattern. Add CLI commands mirroring company capability seed/read:

```bash
python3 -m state_system.cli --project-root . --state-root /tmp/state-instance instance-capability-seed examples/instance-capability/instance-lfw.json examples/instance-capability/instance-acme-ops.json
python3 -m state_system.cli --project-root . --state-root /tmp/state-instance instance-capability-read --output-dir /tmp/state-instance-read
```

- [ ] **Step 5: Run focused runtime tests**

Run:

```bash
python3 -m unittest tests/test_instance_capability_runtime.py
```

Expected: pass.

### Task 4: Generalize Understanding Surface

**Files:**
- Create: `state_system/instance_understanding_surface.py`
- Modify: `state_system/cli.py`
- Test: `tests/test_instance_understanding_surface.py`

- [ ] **Step 1: Write failing tests**

Write tests proving the generic surface:

```python
self.assertEqual("instance_understanding_surface_read_model", read_model["id"])
self.assertEqual(["state_instance.acme_ops"], [i["instance_ref"] for i in read_model["instances"]])
self.assertIn("index.personal.agentmem.memory", read_model["index_refs"])
self.assertIn("index.personal.relationship_substrate.network", read_model["index_refs"])
self.assertIn("state-system-instance:state_instance.lfw", read_model["source_gap_refs"])
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
python3 -m unittest tests/test_instance_understanding_surface.py
```

Expected: fail because the generic surface does not exist.

- [ ] **Step 3: Implement generic surface by adapting company surface**

Copy the mechanics from `state_system/company_understanding_surface.py`, but key records by `instance_ref` and preserve `primary_entity_ref` / `entity_kind`.

- [ ] **Step 4: Keep company surface compatibility**

Do not remove `company-understanding-surface-read`. Keep it as the company-specific surface until PAIA callers migrate.

- [ ] **Step 5: Run focused tests**

Run:

```bash
python3 -m unittest tests/test_instance_understanding_surface.py tests/test_company_understanding_surface.py
```

Expected: pass.

### Task 5: Personal b-state Baseline

**Files:**
- Create runtime root: `/path/to/personal-state`
- Create runtime artifacts through CLI only
- Test: CLI smoke commands

- [ ] **Step 1: Seed the personal instance only after generic contracts pass**

Run:

```bash
python3 -m state_system.cli --project-root . --state-root /path/to/personal-state instance-capability-seed examples/instance-capability/instance-acme-ops.json
```

Expected: creates the personal instance capability record under the deployed root.

- [ ] **Step 2: Generate the personal instance read model**

Run:

```bash
python3 -m state_system.cli --project-root . --state-root /path/to/personal-state instance-capability-read --output-dir /path/to/personal-state/instance-capability
```

Expected: writes `/path/to/personal-state/instance-capability/instance-capability-read-model.json`.

- [ ] **Step 3: Generate the personal understanding surface**

Run:

```bash
python3 -m state_system.cli --project-root . --state-root /path/to/personal-state instance-understanding-surface-read --output-dir /path/to/personal-state/instance-understanding
```

Expected: writes `/path/to/personal-state/instance-understanding/instance-understanding-surface-read-model.json`.

- [ ] **Step 4: Verify no raw corpus duplication**

Run:

```bash
find /path/to/personal-state -maxdepth 3 -type f | sort
```

Expected: only State System records/read models are present; no msgvault email corpus, agentmem database, relationship-substrate database, or copied work instance corpus.
