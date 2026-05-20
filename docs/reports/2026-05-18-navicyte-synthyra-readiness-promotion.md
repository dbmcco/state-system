# Navicyte/Synthyra Readiness Promotion

Date: 2026-05-18

## Summary

Navicyte and Synthyra now have repo-root renderable instance agent packages for
Helena and Ingrid. Both packages expose source readiness, source module linkage,
freshness/gap metadata, private route contracts, and the planned
Navicyte/Synthyra portfolio federation pack.

The package builder now ingests private state-root `question-routes/*.json` and
`tool-actions/*.json` registries, normalizes them into the public package shape,
and keeps generic package consumers from depending on hardcoded Sam/Caroline
routes only.

## Package Artifacts

Navicyte:

- State root: `/Users/braydon/projects/work/navicyte/navicyte-workspace/state-system`
- Package: `/Users/braydon/projects/work/navicyte/navicyte-workspace/state-system/state/instance-agent-packages/instance_agent_package.navicyte.helena.json`
- Read model: `/Users/braydon/projects/work/navicyte/navicyte-workspace/state-system/instance-agent-package/instance-agent-packages-read-model.json`
- Repo-root render:

```bash
cd /Users/braydon/projects/work/navicyte
PYTHONPATH=/Users/braydon/projects/experiments/state-system \
python3 -m state_system.cli \
  --project-root /Users/braydon/projects/experiments/state-system \
  --state-root /Users/braydon/projects/work/navicyte/navicyte-workspace/state-system \
  instance-agent-package-render \
  instance_agent_package.navicyte.helena
```

Synthyra:

- State root: `/Users/braydon/projects/work/synth/state-system`
- Package: `/Users/braydon/projects/work/synth/state-system/state/instance-agent-packages/instance_agent_package.synthyra.ingrid.scaffold.v0.json`
- Read model: `/Users/braydon/projects/work/synth/state-system/instance-agent-package/instance-agent-packages-read-model.json`
- Repo-root render:

```bash
cd /Users/braydon/projects/work/synth
PYTHONPATH=/Users/braydon/projects/experiments/state-system \
python3 -m state_system.cli \
  --project-root /Users/braydon/projects/experiments/state-system \
  --state-root /Users/braydon/projects/work/synth/state-system \
  instance-agent-package-render \
  instance_agent_package.synthyra.ingrid.scaffold.v0
```

## Readiness State

Navicyte package:

- Folio, Drive, and msgvault are declared but access/freshness are missing.
- Local, repo, and state-system instance sources are planned/missing.
- Every source carries access/freshness/index status and explicit gap refs.
- No `checked_at` is present because no live Navicyte instance preflight or
  freshness records are available yet.
- Private routes are present:
  `question_route.navicyte.source_readiness` and
  `question_route.navicyte.bd_evidence_lookup`.

Synthyra package:

- Local workspace is ready/fresh.
- Folio, Drive, msgvault, and GitHub repos are declared with failed access and
  unknown freshness from the last recorded checks.
- Docs/transcripts are planned with a document-processing pipeline dependency.
- Every source carries `checked_at`, source watermark, stale policy, status, and
  explicit gap refs.
- Private routes are present:
  `question_route.synthyra.company_context_review`,
  `question_route.synthyra.transcript_and_docs_review`, and
  `question_route.synthyra.federated_relationship_context`.

Both packages expose
`instance_federation_pack.portfolio_to_navicyte_synthyra` as planned with
`local_materialization=false` and raw corpus replication prohibited.

## Validation

Commands run:

```bash
python3 -m unittest tests.test_instance_agent_packages
python3 -m unittest tests.test_package_pressure_questions tests.test_instance_understanding_surface
python3 /Users/braydon/projects/work/synth/state-system/tests/validate_synthyra_scaffold.py
python3 -m state_system.cli --project-root . validate
python3 -m unittest discover -s tests
git diff --check
```

Results:

- Focused instance package tests: 5 OK.
- Focused pressure/understanding tests: 11 OK.
- Synthyra scaffold validator: passed.
- Generic example validation: 129 examples OK.
- Full core test suite: 209 OK.
- `git diff --check`: clean.

Package pressure:

- `--include-planned` passed the Navicyte and Synthyra readiness cases.
- One existing LFW planned case still fails because the current Caroline package
  does not expose the expected Linear/GitHub/transcript stale/index gap refs:
  `gap.state_instance.lfw.connector.lfw.linear.freshness_failed`,
  `gap.state_instance.lfw.connector.lfw.github.freshness_failed`,
  `gap.state_instance.lfw.connector.lfw.transcripts.raw.index_planned`, and
  `gap.state_instance.lfw.connector.lfw.transcripts.processed.index_planned`.

Leakage scans:

```bash
find /Users/braydon/projects/work/navicyte/navicyte-workspace/state-system -type f -size +1M -print
find /Users/braydon/projects/work/synth/state-system -type f -size +1M -print
rg -n "BEGIN [A-Z ]*PRIVATE KEY|refresh_token|access_token|client_secret|password" . --glob '!runbooks/navicyte-state-instance.md'
```

Results:

- No files larger than 1MB in either state root.
- No secret/token matches in Navicyte state root, excluding the runbook's example
  leakage-scan command.
- No secret/token matches in Synthyra state root.

## Follow-up

As of 2026-05-19, the cross-repo package pressure suite passes for Sam,
Caroline, Helena, and Ingrid with `--include-planned`.

## 2026-05-19 Refresh

Navicyte:

- Runtime instance preflight and freshness records were seeded into
  `/Users/braydon/projects/work/navicyte/navicyte-workspace/state-system/state`
  instead of only living as scaffold-side read models.
- Helena package regenerated at `2026-05-19T19:32:31Z`.
- `connector.navicyte.local` is access passed, freshness fresh, index planned,
  and usable.
- `connector.navicyte.repo` is access passed with a stale GitHub `pushed_at`
  watermark (`2026-05-09T15:25:55Z`) and remains usable with a freshness gap.
- `connector.navicyte.state_system` is access passed, freshness fresh, index
  declared, and ready. The self state-system connector now declares its
  `runtime_root`, so the earlier false federation-missing gap is gone.
- Folio, Drive, and msgvault remain visible gaps: Folio and Drive are declared
  but stale/unproven; msgvault freshness is failed until account/sync proof is
  recorded.

Synthyra:

- Ingrid package regenerated at `2026-05-19T19:31:34Z`.
- Local workspace freshness was refreshed from
  `/Users/braydon/projects/work/synth/sync/state.json`.
- GitHub repo access is now proven for `Synthyra/atlas`,
  `Synthyra/synthyra-decks`, and `dbmcco/synthyra-ai-org`; all three remain
  stale by their GitHub `pushed_at` watermarks.
- Folio, Drive, and msgvault remain failed/unknown because no live source-owned
  checks were run. Docs/transcripts remain planned behind the document
  processing pipeline.

Validation on 2026-05-19:

```bash
python3 -m state_system.cli --project-root /Users/braydon/projects/experiments/state-system --state-root /Users/braydon/projects/work/navicyte/navicyte-workspace/state-system validate
python3 -m state_system.cli --project-root /Users/braydon/projects/experiments/state-system --state-root /Users/braydon/projects/work/synth/state-system validate
python3 /Users/braydon/projects/work/synth/state-system/tests/validate_synthyra_scaffold.py
python3 -m state_system.cli --project-root /Users/braydon/projects/experiments/state-system package-pressure-run examples/pressure-questions/package-pressure-core-real-questions.json --include-planned --package instance_agent_package.braydon_personal.samantha=/Users/braydon/projects/personal/b-state/state/instance-agent-packages/instance_agent_package.braydon_personal.samantha.json --package instance_agent_package.lfw.caroline=/Users/braydon/projects/work/lfw/state-system/state/instance-agent-packages/instance_agent_package.lfw.caroline.json --package instance_agent_package.navicyte.helena=/Users/braydon/projects/work/navicyte/navicyte-workspace/state-system/state/instance-agent-packages/instance_agent_package.navicyte.helena.json --package instance_agent_package.synthyra.ingrid.scaffold.v0=/Users/braydon/projects/work/synth/state-system/state/instance-agent-packages/instance_agent_package.synthyra.ingrid.scaffold.v0.json
python3 -m unittest tests.test_instance_agent_packages tests.test_instance_understanding_surface tests.test_package_pressure_questions
```

Results:

- Navicyte state-root validation: 129 examples OK.
- Synthyra state-root validation: 129 examples OK.
- Synthyra scaffold validator: passed.
- Package pressure: 8 cases, 0 failures.
- Focused core tests: 16 OK.
- JSON parse over both state roots: OK.
- State-root leakage scan: no files over 1MB and no secret/token matches other
  than the runbook's example scan command.
