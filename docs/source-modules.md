# Source Modules

Source modules are the open-source extension point for State System connectors.
They define what a connector type means before any deployed instance claims it
has usable data.

A source module does not prove live access. It declares the interface that a
capability pack may use: source ref shape, access mode, preflight contract,
freshness contract, index ownership, tool bindings, and governance defaults.

The current registry example is
`examples/source-modules/source-module-core-connectors.json`.

## Contract

Each module declares:

- `connector_type`: the stable connector key used by capability packs.
- `allowed_instance_kinds`: where the connector can appear.
- `source_ref`: the source reference pattern and safe examples.
- `access`: runtime access mode and owner.
- `preflight_contract`: checks required before an agent treats the source as
  reachable.
- `freshness_contract`: watermark strategy and freshness record schema.
- `index_contract`: index ownership, scopes, and record kinds.
- `tool_contract`: tool refs plus capability/action ref patterns.
- `module_modes`: live API, historical cache, local sync, export, or
  federated-query modes supported by the connector.
- `read_surfaces`, `write_surfaces`, and `correction_surfaces`: distinguish
  read-only retrieval, source-owned correction writes, and protected external
  side effects.
- `output_policy`: summary/redaction/evidence behavior expected from agents.
- `gap_behavior`: what agents should do when access, freshness, index, or
  credential gaps are present.
- `governance_defaults`: privacy boundary and prohibited uses.

Capability-pack schemas intentionally allow open `connector_type` strings.
Conformance should validate connector types against registered source modules
instead of hardcoding connector enums into every pack schema.

## Adding A Connector

1. Add or update a module in the source module registry.
2. Include open-source safe `source_ref.examples`.
3. Declare preflight and freshness requirements even if the deployed adapter is
   not implemented yet.
4. Add tool/action/capability ref patterns.
5. Add the connector to a deployed instance capability pack.
6. Run schema validation and conformance tests.

Private corpora, credentials, tenant-specific records, and local absolute paths
belong in deployed instances, not in open-source source-module examples.

## Tool And Route Contracts

Source modules define the connector interface. Tool action contracts define how
canonical tools map to deployment-specific backing tools, including mode-specific
adapters such as Spotify historical cache versus live API.

Question route contracts define source coverage, required tools, fallback
policy, answer contracts, and gap behavior. Routes should name required source
coverage explicitly so an agent can avoid narrow answers, such as calendar-only
relationship reasoning when relationship substrate and email evidence are
available.

## Instance Federation Packs

`InstanceFederationPack` is the boundary object for governed cross-instance
queries. It does not sync raw data. It declares that one local instance can use a
remote instance or source substrate through named routes, query surfaces, tool
actions, source modules, freshness policy, output policy, and repair behavior.

Use federation packs for b-state reading LFW interpreted state, LFW querying
personal Relationship Substrate without materializing personal records, and
portfolio rollups across company instances such as Navicyte and Synthyra.

Required policies:

- identity boundary: which subjects/entities remain owned by the remote source;
- materialization policy: normally `local_materialization=false`;
- freshness policy: checked time, watermark, stale-after, and visible gap refs;
- subject-note policy: subject notes can demote or explain context, not become
  hidden broad filters;
- output policy: safe summaries with evidence refs, no raw remote corpora;
- repair policy: what the agent should say when the route is stale or missing.

Validate and render a federation pack registry with:

```bash
python3 -m state_system.cli --project-root /path/to/state-system instance-federation-pack-validate examples/instance-federation-packs/instance-federation-pack-core-examples.json
python3 -m state_system.cli --project-root /path/to/state-system instance-federation-pack-render examples/instance-federation-packs/instance-federation-pack-core-examples.json
```

The conformance suite in `tests/test_open_source_ecosystem_conformance.py`
checks the open-source extension boundary:

- capability-pack connector types must have source modules;
- tool actions must reference known source modules and matching connector types;
- question-route tools must have tool action contracts;
- question-route source module refs must exist;
- generated packages must emit source-module, route-contract, tool-action, and
  gap-policy linkage fields.

## Package Pressure Questions

Package pressure questions are real operational questions with structural
assertions against package JSON. They do not grade exact answer text. They check
that a package exposes the route, source coverage, tool/action refs, answer
policy, freshness gaps, and federation boundaries an agent would need before it
answers.

The core registry is
`examples/pressure-questions/package-pressure-core-real-questions.json`.

Run it with package JSON files:

```bash
python3 -m state_system.cli --project-root /path/to/state-system package-pressure-run examples/pressure-questions/package-pressure-core-real-questions.json \
  --package instance_agent_package.braydon_personal.samantha=/path/to/instance_agent_package.braydon_personal.samantha.json \
  --package instance_agent_package.lfw.caroline=/path/to/instance_agent_package.lfw.caroline.json
```

Use `--include-planned` when checking scaffolded Helena/Ingrid readiness or
known planned gaps such as LFW Linear/GitHub/transcript coverage. Planned cases
are still executable, but the default run focuses on ready daily-use package
contracts.

## Relationship Substrate

Relationship Substrate is a source module, not a b-state-only assumption. Its
open-source capability should cover people, organizations, affiliations,
interactions, and subject-level notes. Subject notes are contextual relationship
evidence: they can demote or explain a candidate, but they must not become
hidden filters or canonical profile facts unless a governed promotion path does
that explicitly.

`record_subject_note` is a source-owned correction write. It is not the same as
an external side effect such as emailing a contact or mutating a CRM. Capability
packs should expose that distinction so agents can remember relationship
corrections while still requiring governance for protected external actions.
