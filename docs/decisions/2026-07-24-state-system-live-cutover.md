# State System Live Cutover — 2026-07-24

## Status

The State System upgrade is live in the local PAIA fleet. The runtime and State
System primary branches contain the accepted integration commits and have been
pushed to origin.

| Surface | Commit | Result |
|---|---:|---|
| `paia-agent-runtime` | `608c8b6` | Typed package loading, content-aware freshness decisions, policy headers, bounded model proposals, and opt-in route gating are live. |
| `state-system` | `7da74a3` | Canonical schemas, freshness dimensions, append-only audit ledger, model-operable CLI envelopes, and documentation are live. |

The agent services use the editable runtime dependency from:

```text
/Users/braydon/projects/experiments/paia-agent-runtime
```

Samantha, Derek, Ingrid, Caroline, Helena, Spine, and the Spine adapter were
restarted after cutover. The four State System fleet refresh jobs were also
restarted and each reported `ok: true` with `status: refreshed`.

## Validation evidence

- The integrated runtime suite passed: **1,650 tests passed, 4 skipped**.
- The integrated State System suite passed: **336 tests passed, 1 skipped**.
- The model-operable State System CLI handshake and inspect canaries returned
  `state-system.v1` JSON envelopes with no traceback.
- The running agent environments resolve `paia_agent_runtime` from the primary
  runtime checkout, not from an older installed copy.

## What is enabled

- Instance-agent package loading is typed, bounded, hash-aware, and observe-only.
- Source-content freshness is distinguished from event, index, probe, package,
  and process status.
- State context decisions and gap acknowledgements are retained in the State
  System's redacted, append-only ledger for 400 days by default.
- Model proposals may select only declared routes, sources, evidence, operations,
  and action references. Code owns freshness, governance, authorization,
  connector choice, and user intent.
- State-dependent route gating is available as an injected policy and remains
  disabled by default until a separate human approval reference is configured.

## What is deliberately not enabled

- The fail-closed messaging action gate is not active.
- No calendar, email, publishing, commit, delivery, or other protected external
  action is authorized by package loading, gap acknowledgement, model output, or
  route evaluation.
- Workgraph supervision remains in observe mode with dispatch disabled. This is
  intentional while the queue contains stale placeholder adoption tasks.

## Freshness posture

All four fleet refreshes completed successfully, but successful process execution
is not treated as proof of fresh content. Current reports retain stale and
unknown source gaps, including transcript, Folio, Linear, repository, and local
read-model sources. Agents must surface those limitations rather than silently
turning package generation into content proof.

## Remaining commitments

The following commitments remain in Workgraph rather than in informal notes:

- `agents.pi-bindings`: bind Pi task materialization to declared model routes and
  Agency fallback receipts.
- `paiaos.external-effect-receipts`: make paia-os the owner of external-effect
  receipts and retention.
- `tests.e2e-canary`: rerun the end-to-end inspect → package decision → model
  proposal → governance → observe messaging canary after its wrapper failure is
  repaired.
- `state.inspect-reports`: expose process health and content health separately
  through the read-only inspect/report surfaces.
- `final.handoff`: produce the final rollback and ownership packet after the
  canary and drift gates are complete.

## Rollback

Do not reset the dirty primary checkouts. If rollback is required, use a reviewed
revert of the cutover range in the relevant repository, then restart the affected
services and rerun the health and import-path probes:

```bash
cd /Users/braydon/projects/experiments/paia-agent-runtime
# Review first, then revert the commits after 5f0a580.
git log --oneline 5f0a580..main

cd /Users/braydon/projects/experiments/state-system
# Review first, then revert the commits after 2e90cfb.
git log --oneline 2e90cfb..main
```

The protected-action posture must remain observe-only until the explicit approval
record and the remaining Workgraph commitments are complete.
