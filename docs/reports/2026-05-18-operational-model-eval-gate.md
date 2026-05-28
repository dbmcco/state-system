# Operational Model Eval Gate

Date: 2026-05-18

## Summary

Decision: proceed to the federation-pack contract work.

The pending FLIP/evaluator gates could not produce LLM evaluations because the
local evaluator infrastructure is not configured. Both FLIP and direct
evaluation paths failed before grading:

- FLIP: `Claude CLI call failed (exit Some(1))`
- Direct eval: no native Anthropic API key, fallback to Claude CLI, then
  `Claude CLI call failed (exit Some(1))`

This is an evaluator infrastructure blocker, not a contract implementation
finding. The implementation evidence from task logs and focused validation is
strong enough to continue, with evaluator repair tracked separately.

## Gates Attempted

All of these FLIP gates were attempted and classified as evaluator-infra
blocked:

- `state-source-module-contract-v0`
- `state-tool-action-contract-v0`
- `state-route-contract-v0`
- `bstate-daily-use-contract-refresh-v0`
- `lfw-daily-use-contract-refresh-v0`
- `demo_co-state-instance-scaffold-v0`
- `examplecorp-state-instance-scaffold-v0`
- `state-oss-ecosystem-conformance-v0`
- `ecosystem-freshness-repair-backlog-v0`
- `state-instance-scaffold-command-v0`

Direct evaluator smoke checks were also attempted for:

- `state-source-module-contract-v0`
- `bstate-daily-use-contract-refresh-v0`

Both direct checks failed on the same evaluator configuration path.

## Evidence Reviewed

Manual gate review used task logs and fresh validation:

- `state-source-module-contract-v0`: SourceModuleSpec schema, registry,
  package schema openness, docs, and tests completed. Logged validation:
  125 examples and 177 tests at completion.
- `state-tool-action-contract-v0`: ToolActionContract schema and examples
  completed, including runtime adapter mapping, Spotify historical cache,
  relationship fallback, and source-owned correction writes. Follow-up expanded
  required Sam/Caroline tools. Logged validation reached 188 tests and 127
  examples.
- `state-route-contract-v0`: QuestionRouteContract schema and route examples
  completed, including no calendar-only relationship answers, LFW federated
  no-materialization route, subject-note demote/explain policy, and structured
  package route fields. Logged validation reached 188 tests and 127 examples.
- `state-oss-ecosystem-conformance-v0`: Conformance suite checks connector
  modules, tool/module registration, route coverage, and generated package
  fields. Logged validation: focused conformance OK, 193 tests, 127 examples.
- `state-instance-scaffold-command-v0`: `instance-scaffold` CLI writes valid
  instance records, runtime dirs, source module registry subsets, and README
  stubs without claiming live access. Logged validation: focused tests, CLI
  smoke, 195 tests, 127 examples.
- `bstate-daily-use-contract-refresh-v0`: Sam package/read model exposes module
  fields and structured routes. Spotify remains historical-cache stale, Garmin
  ready, Relationship Substrate usable. Fresh repo-root render passed.
- `lfw-daily-use-contract-refresh-v0`: Caroline package/read model exposes
  contracts, federated relationship route, no local personal materialization,
  transcript/Linear/GitHub gap refs, and repo-root render command.
- `demo_co-state-instance-scaffold-v0`: Helena scaffold has state root,
  package, typed readiness fields, guidance, and leakage scan clean.
- `examplecorp-state-instance-scaffold-v0`: Ingrid scaffold has baseline source
  module registry, package/render guidance, privacy boundary, and validation.
- `ecosystem-freshness-repair-backlog-v0`: Freshness backlog exists and
  classifies Spotify, LFW Linear/GitHub, transcripts, Navicyte/Synthyra, and
  evaluator infra gaps.

Fresh validation run during this gate:

```text
python3 -m state_system.cli --project-root . validate
ok, validated_examples=127

python3 -m unittest tests.test_source_module_spec tests.test_tool_action_contract tests.test_question_route_contract tests.test_open_source_ecosystem_conformance tests.test_instance_scaffold tests.test_instance_agent_packages tests.test_instance_understanding_surface
Ran 33 tests OK
```

## Contract-Blocking Findings

None found in this gate.

The next contract work should still be narrow and test-driven, because the
evaluator infrastructure is currently unable to catch semantic drift.

## Follow-Ups

- Repair evaluator infrastructure so FLIP/direct eval can run without manual
  override.
- Continue with `state-instance-federation-pack-contract-v0`.
- Keep `state-high-value-freshness-repair-loop-v0` as an operational repair
  path, not a blocker for defining federation packs.

## Proceed Criteria

The model can proceed to federation-pack implementation because:

- generic validation passes;
- focused contract tests pass;
- deployed b-state and LFW packages render from repo roots;
- Navicyte and Synthyra have first scaffold/package evidence;
- known freshness gaps are explicit, typed, and already backed by repair tasks;
- no evaluated evidence suggests the next schema should be redesigned before
  implementation.
