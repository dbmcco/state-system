# Open-Source Onboarding

This runbook is the operator path for a fresh adopter standing up a State System
instance with no prior context. It walks through install, scaffold, source
module declaration, preflight and freshness recording, package render, federation
pack declaration, and a pressure test against the rendered package.

Throughout, paths shown for `--runtime-root` and `--state-root` are illustrative.
Replace them with the local runtime root for the instance you are building.
`SampleCo`, `ResearchCo`, and `PortfolioCo` are synthetic fixture names used by public
examples. They are not required deployment names and do not refer to the
personal state, SampleCo, PortfolioCo, or ResearchCo runtime roots.

## 1. Install

State System ships as a Python package with a CLI exposed at
`state_system.cli`. From a clean checkout:

```bash
cd state-system
python3 -m unittest discover -s tests        # confirm baseline passes
python3 -m state_system.cli --project-root . validate
```

`validate` walks every shipped JSON example against its schema and is the first
gate that the install is functional. The expected output is
`{"ok": true, ...}`.

## 2. Scaffold a State Instance

`instance-scaffold` creates the runtime root, the state-instance record, and an
instance-local source module registry subset:

```bash
mkdir -p /tmp/state-system-onboarding
python3 -m state_system.cli --project-root . \
  instance-scaffold \
  --runtime-root /tmp/state-system-onboarding \
  --instance-ref state_instance.sampleco \
  --kind company \
  --display-name "SampleCo Operations" \
  --primary-entity-ref entity.sampleco \
  --entity-kind organization \
  --created-at 2026-05-18T12:00:00Z \
  --governance-ref governance.sampleco.default \
  --connector-type folio \
  --connector-type local_path
```

The scaffold writes:

- `state/instances/state-instance-sampleco.json` — the durable instance record
- `state/source-modules/source-module-registry-sampleco.json` — a subset of the
  generic module registry filtered to the declared `--connector-type` values
- `README.md` (in the runtime root) if one is not already present

`--kind` accepts `company`, `person`, or `project`. `--connector-type` is
repeated, once per declared connector type. Connector types are free-form
strings backed by `examples/source-modules/source-module-core-connectors.json`;
the contract intentionally has no closed enum so adopters can register new
modules without editing core schemas.

## 3. Declare Source Modules

The shipped registry at
`examples/source-modules/source-module-core-connectors.json` is the canonical
source module catalog. To add a new module:

1. Append an entry to the registry (or to an instance-local override under
   `state/source-modules/`) with `id`, `connector_type`, supported instance
   kinds, module modes, preflight contract, freshness contract, index manifest,
   and gap behavior.
2. Declare the module in the instance capability pack under
   `examples/instance-capability/instance-<slug>.json` (or the runtime-root
   variant) and reference it from `source_connectors[].connector_type`.
3. Re-run `python3 -m state_system.cli --project-root . validate` to confirm
   the registry, capability pack, and module spec stay schema-clean.

Capability pack `source_connectors[].connector_type` is an open string. The
conformance test `test_capability_connector_types_have_source_modules` ensures
every declared connector type has a matching module entry, and
`test_no_connector_enum_lock_in` enforces that no shipped schema introduces a
closed enum for connector type.

## 4. Record Preflight and Freshness

Preflight proves live access. Freshness proves recency. Neither authorizes
protected action — that remains governance's job.

```bash
python3 -m state_system.cli --project-root . \
  --state-root /tmp/state-system-onboarding \
  instance-preflight-record \
  --preflight-ref preflight.state_instance.sampleco.connector.sampleco.folio \
  --instance-ref state_instance.sampleco \
  --connector-ref connector.sampleco.folio \
  --source-ref folio:tenant:sampleco \
  --connector-type folio \
  --status passed \
  --checked-at 2026-05-18T12:05:00Z \
  --stale-after 2026-05-18T13:05:00Z \
  --evidence-ref local-path:/srv/folio/sampleco

python3 -m state_system.cli --project-root . \
  --state-root /tmp/state-system-onboarding \
  instance-source-freshness-record \
  --instance-ref state_instance.sampleco \
  --connector-ref connector.sampleco.folio \
  --source-ref folio:tenant:sampleco \
  --connector-type folio \
  --status fresh \
  --checked-at 2026-05-18T12:05:00Z \
  --source-watermark folio.indexed_at:2026-05-18T12:04:00Z \
  --stale-after 2026-05-18T13:05:00Z \
  --evidence-ref freshness:folio:fresh:20260518T120500Z
```

`--status` for preflight is `passed`, `failed`, or `planned`. Only `passed`
sets `proves_live_access: true`. `planned` keeps the connector visible as a
declared access gap. Freshness `--status` is `fresh`, `stale`, `failed`, or
`unknown`.

Export the joined understanding surface to inspect what the agent will see:

```bash
python3 -m state_system.cli --project-root . \
  --state-root /tmp/state-system-onboarding \
  instance-understanding-surface-read \
  --output-dir /tmp/state-system-onboarding/instance-understanding
```

## 5. Render an Agent Package

Build a persona-bounded package over the instance, then render it as the
agent-facing artifact:

```bash
python3 -m state_system.cli --project-root . \
  --state-root /tmp/state-system-onboarding \
  instance-agent-package-build \
  --instance-ref state_instance.sampleco \
  --agent-ref agent.sampleco.operator \
  --persona-ref persona.sampleco.operator \
  --created-at 2026-05-18T12:10:00Z

python3 -m state_system.cli --project-root . \
  --state-root /tmp/state-system-onboarding \
  instance-agent-package-render \
  instance_agent_package.sampleco.sampleco.operator
```

The rendered output exposes source readiness, freshness, gaps, question
routes, tool action refs, federation packs, governance refs, and
no-materialization boundaries in typed fields. Adopters should be able to read
the rendered output and answer "which sources are live, which are gaps, and
which questions can I route" without private prompting.

## 6. Declare a Federation Pack

Federation packs declare governed cross-instance reads. They must not copy raw
remote rows into the local instance.

The canonical registry at
`examples/instance-federation-packs/instance-federation-pack-core-examples.json`
holds three reference packs: personal-to-SampleCo state, SampleCo-to-personal Relationship
Substrate, and a portfolio-to-PortfolioCo-ResearchCo example. To add a pack for a
new instance:

1. Append an entry under `packs[]` with `local_instance_ref`,
   `source_instance_ref`, `materialization_policy.local_materialization=false`,
   freshness policy, gap policy, and repair owner.
2. Reference the pack from the relevant question route in
   `examples/question-routes/question-route-core-agent-routes.json` via
   `federated_query.federation_pack_ref`.
3. Validate the registry:

   ```bash
   python3 -m state_system.cli --project-root . \
     instance-federation-pack-validate \
     examples/instance-federation-packs/instance-federation-pack-core-examples.json
   ```

The validator confirms each pack carries the required materialization, freshness,
gap, and governance fields.

## 7. Pressure Test the Package

`package-pressure-run` evaluates a rendered package against operational
questions from a pressure-question registry. Assertions inspect package
contracts, gaps, routes, and federation boundaries rather than exact answer
text.

The shipped registry at
`examples/pressure-questions/package-pressure-core-real-questions.json` is
keyed to the maintained personal state, SampleCo, PortfolioCo, and ResearchCo package contracts;
it is the reference for case shape, not an OSS adopter's own test set. Some
older public example package files still use synthetic SampleCo fixture IDs.
Adopters typically write a registry sibling for their instance with cases that
name their own
`package_id`, expected routes, source coverage refs, tool action refs, and
federation packs.

To exercise the shape against the shipped reference registry:

```bash
python3 -m state_system.cli --project-root . \
  --state-root /tmp/state-system-onboarding \
  instance-agent-package-export \
  --output-dir /tmp/state-system-onboarding/instance-agent-package

python3 -m state_system.cli --project-root . \
  package-pressure-run \
  examples/pressure-questions/package-pressure-core-real-questions.json
```

The pressure harness emits a JSON summary listing each case's status, the
required route IDs, source coverage refs, tool action refs, answer policy
flags, federation pack IDs, and materialization expectations. Cases targeting
packages the runner cannot resolve report as `failed` with `package not
supplied`, which is the expected output for an adopter not supplying the
referenced deployment packages. Use `--package <id>=<path>` to supply the
adopter's own rendered package, and `--include-planned` to exercise
planned-status cases as known gaps.

## 8. Verify the Release Gate

A new adopter walking this runbook end-to-end should also be able to run the
shipped validations:

```bash
python3 -m unittest discover -s tests
python3 -m state_system.cli --project-root . validate
python3 -m state_system.cli --project-root . \
  instance-federation-pack-validate \
  examples/instance-federation-packs/instance-federation-pack-core-examples.json
python3 -m state_system.cli --project-root . \
  package-pressure-run \
  examples/pressure-questions/package-pressure-core-real-questions.json \
  --package <package_id>=/path/to/rendered.json
```

These four commands are the release gate. The first three confirm contracts,
registries, and federation packs are green for the OSS surface without
depending on private deployment artifacts. The pressure-run command requires
either deployment-rendered packages or the adopter's own rendered package
supplied via `--package`. They confirm contracts, registries,
federation packs, and pressure expectations remain green for the OSS surface
without depending on private deployment artifacts.

For the current publishing gate, run the commands in `README.md` under
"Development Gates".
