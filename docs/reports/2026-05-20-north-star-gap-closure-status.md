# North Star Gap Closure Status - 2026-05-20

## Summary

The PlanForge/Speedrift gap-closure run reduced the cross-instance North Star
answer from 28 source gaps to 9 source gaps while preserving explicit
uncertainty and non-materializing federation boundaries.

- Baseline: `/tmp/state-system-coordination/north-star-baseline.json`
- Final: `/tmp/state-system-coordination/north-star-final.json`
- Final answer artifact: `/tmp/state-system-north-star-ecosystem/north-star-answer.json`
- Final rendered answer: `/tmp/state-system-north-star-ecosystem/north-star-answer.txt`

Final answerability:

```json
{
  "status": "usable_with_gaps",
  "source_count": 35,
  "gap_count": 9
}
```

## Completed Lanes

Product substrate and renderer:

- Added the formal `north-star-answer` schema gate and validation path.
- Added deterministic `north-star-answer-render` with `--check`.
- Renderer validates schema and invariants before writing text.
- Renderer does not fetch sources, authorize actions, or hide uncertainty.

b-state and LFW:

- LFW raw transcript access/freshness/index gaps were repaired from safe
  transcript metadata over 159 source-owned transcript files.
- LFW processed transcript access/freshness/index gaps were repaired.
- b-state Beeper iMessage access was probed, but freshness remains unknown
  because the local Beeper source had zero iMessage threads/messages.
- b-state Spotify remains stale because no live OAuth/source-owned refresh
  evidence exists.

NaviCyte:

- Drive, msgvault, local index, and repo index/access gaps were repaired from
  source-owned probe evidence.
- Folio freshness and repo freshness remain explicit typed gaps.

Synthyra:

- Drive source ownership was resolved to `gws:mcco:drive:examplecorp-corpus-search`.
- Drive, msgvault, and repo freshness gaps were repaired from source-owned probe
  evidence.
- Folio remains failed/unknown because localhost Folio timed out.
- Transcript docs remain planned because no real read-model pipeline was found.

## Remaining Gaps

```text
gap.state_instance.acme_ops.connector.personal.beeper.imessage.freshness_unknown
gap.state_instance.acme_ops.connector.personal.spotify.freshness_stale
gap.state_instance.demo_co.connector.demo_co.folio.freshness_stale
gap.state_instance.demo_co.connector.demo_co.repo.freshness_stale
gap.state_instance.examplecorp.connector.examplecorp.docs.transcripts.access_planned
gap.state_instance.examplecorp.connector.examplecorp.docs.transcripts.freshness_unknown
gap.state_instance.examplecorp.connector.examplecorp.docs.transcripts.index_planned
gap.state_instance.examplecorp.connector.examplecorp.folio.access_failed
gap.state_instance.examplecorp.connector.examplecorp.folio.freshness_unknown
```

## Federation Boundary

The final answer retains two federated relationship routes. Both keep
`local_materialization` false:

- LFW federated relationship-index search queries personal relationship context
  on demand.
- Synthyra federated relationship-context search queries personal relationship
  context on demand.

No lane copied raw private source corpora into generic examples, and the final
North Star artifact remains a JSON substrate rather than an execution authority.

## Verification

Final acceptance commands passed:

```bash
python3 -m unittest tests.test_north_star_answer
python3 -m unittest tests.test_open_source_ecosystem_conformance
python3 -m state_system.cli --project-root . validate
python3 -m state_system.cli --project-root . north-star-answer \
  --query "What is the current cross-instance ecosystem state?" \
  --package bstate=/path/to/personal-state/state/instance-agent-packages/instance_agent_package.acme_ops.samantha.json \
  --package lfw=/path/to/state-system-runtime/state/instance-agent-packages/instance_agent_package.lfw.caroline.json \
  --package demo_co=/path/to/user/projects/work/demo_co/demo_co-workspace/state-system/state/instance-agent-packages/instance_agent_package.demo_co.helena.json \
  --package examplecorp=/path/to/user/projects/work/synth/state-system/state/instance-agent-packages/instance_agent_package.examplecorp.ingrid.scaffold.v0.json \
  --output-dir /tmp/state-system-north-star-ecosystem
python3 -m state_system.cli --project-root . north-star-answer-render \
  /tmp/state-system-north-star-ecosystem/north-star-answer.json \
  --check \
  --output-path /tmp/state-system-north-star-ecosystem/north-star-answer.txt
```

Result:

- `tests.test_north_star_answer`: 5 tests OK.
- `tests.test_open_source_ecosystem_conformance`: 9 tests OK.
- Validation: 130 examples OK.
- Final `north-star-answer`: `schema_valid=true`.
- Final render: `schema_valid=true`, `render_valid=true`.
