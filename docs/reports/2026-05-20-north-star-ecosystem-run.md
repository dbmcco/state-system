# North Star Ecosystem Run

## Summary

The schema-backed `north-star-answer` surface was run against the four current
ecosystem instance agent packages: b-state/Samantha, LFW/Caroline,
NaviCyte/Helena, and Synthyra/Ingrid.

Result: schema-valid and operationally usable with visible gaps.

```json
{
  "answerability": {
    "status": "usable_with_gaps",
    "source_count": 35,
    "gap_count": 28
  },
  "schema_valid": true
}
```

Generated artifact:

`/tmp/state-system-north-star-ecosystem/north-star-answer.json`

## Command

```bash
python3 -m state_system.cli --project-root . north-star-answer \
  --query "What is the current cross-instance ecosystem state?" \
  --package bstate=/path/to/personal-state/state/instance-agent-packages/instance_agent_package.acme_ops.samantha.json \
  --package lfw=/path/to/state-system-runtime/state/instance-agent-packages/instance_agent_package.lfw.caroline.json \
  --package navicyte=/path/to/user/projects/work/navicyte/navicyte-workspace/state-system/state/instance-agent-packages/instance_agent_package.navicyte.helena.json \
  --package synthyra=/path/to/user/projects/work/synth/state-system/state/instance-agent-packages/instance_agent_package.synthyra.ingrid.scaffold.v0.json \
  --output-dir /tmp/state-system-north-star-ecosystem
```

## North Star Coverage

The generated artifact answers the required dimensions as structured substrate:

- Current state: four current instance package summaries with agent, persona,
  entity, and review goal.
- Why this state: 35 source-readiness records with access, freshness, index,
  understanding, evidence refs, and gap refs.
- What changed recently: package/freshness generation timestamp
  `2026-05-20T15:12:00Z` and 35 watermark refs.
- Evidence: 36 index refs, 75 evidence refs, and federated instance refs.
- Uncertainty: 28 source gaps, 16 open questions, and 16 not-ready sources.
- Responsibility: Samantha, Caroline, Helena, and Ingrid plus 13 governance refs
  and 33 available action refs.
- Next actions: refresh/repair is required before external action; all 28 gap
  refs are surfaced as repair targets.
- Broader effects: four federation packs and two federated query routes.

## Instance Readiness

| Package | Sources | Ready | Usable with gap | Planned | Searchable/access unproven |
|---|---:|---:|---:|---:|---:|
| `instance_agent_package.acme_ops.samantha` | 14 | 12 | 2 | 0 | 0 |
| `instance_agent_package.lfw.caroline` | 7 | 5 | 0 | 2 | 0 |
| `instance_agent_package.navicyte.helena` | 6 | 1 | 0 | 2 | 3 |
| `instance_agent_package.synthyra.ingrid.scaffold.v0` | 8 | 1 | 3 | 1 | 3 |

## Federation

The broader-effects section includes federated refs for:

- `state_instance.acme_ops`
- `state_instance.lfw`
- `state_instance.navicyte`
- `state_instance.synthyra`

Federated query routes remain non-materializing:

| Route | Source instance | Query surface | Local materialization |
|---|---|---|---|
| `question_route.lfw.federated_relationship_index` | `state_instance.acme_ops` | `query_surface.federated.relationship_index.search` | `false` |
| `question_route.synthyra.federated_relationship_context` | `state_instance.acme_ops` | `query_surface.federated.relationship_index.search` | `false` |

## Operational Finding

The North Star read surface is strong enough to inspect ecosystem state and
triage next actions, but it is not yet a final human-readable answer surface.
The next product step is a renderer that turns `north-star-answer.json` into an
agent/human-readable answer while preserving evidence, uncertainty, and
execution boundaries.

The next operational repair focus remains source readiness:

- b-state: Spotify stale; Beeper/iMessage freshness unknown.
- LFW: transcript raw/processed sources planned or freshness/index-gapped.
- NaviCyte: folio/drive/msgvault access unproven; repo/local index/freshness
  gaps remain.
- Synthyra: folio/drive/msgvault access failed or unknown freshness; repo
  sources stale; transcript docs still planned.

## Validation

```bash
python3 -m state_system.cli --project-root . north-star-answer ... --output-dir /tmp/state-system-north-star-ecosystem
python3 -m unittest tests.test_north_star_answer
python3 -m unittest tests.test_open_source_ecosystem_conformance
python3 -m state_system.cli --project-root . validate
```

All validation commands above completed successfully in this session.
