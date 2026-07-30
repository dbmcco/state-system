# Agent Guide

This repository defines the State System product surface: schemas, CLI runtime,
example contracts, source-module contracts, package rendering, freshness
audits, federation packs, and tests. It is not a deployed state root and should
not contain private corpora, credentials, mutable source indexes, or local
runtime artifacts.

## Start Here

For implementation work:

1. Read `README.md` for the human quickstart and validation commands.
2. Read `docs/agent-integration.md` for how agents consume State System
   packages.
3. Read `docs/source-modules.md` before adding or changing connectors.
4. Run `python3 -m state_system.cli --project-root . validate` after changing
   schemas or examples.
5. Run `python3 -m unittest discover -s tests` before claiming the repo is
   healthy.

## Agent Consumption Contract

Agents should consume State System through rendered artifacts, not by scraping
source systems or private runtime directories directly.

- Use `InstanceAgentPackage` / `instance-agent-packages-read-model.json` as the
  primary agent-facing packet for an instance.
- Check source readiness, preflight status, freshness status, stale-after
  expiry, source gaps, route gaps, and federation gaps before answering.
- Treat stale, unknown, failed, planned, or expired freshness refs as visible
  caveats. Do not silently answer as if those sources are current.
- Use question routes, tool action refs, source module refs, and federation pack
  refs from the package. Do not invent connector behavior from names.
- Do not locally materialize raw federated sources unless a federation pack
  explicitly permits it. The normal policy is no raw local materialization.
- Do not treat captured agent output as truth. It is evidence for later review.
- Do not authorize protected external actions from freshness or preflight
  alone. Governance remains a separate boundary.

## Canonical Claims

Canonical claims hold current canon (priorities, decisions, framings, approved
artifacts, scientific claims) with supersession, validity windows, and honest
re-evaluation. This is how "is this still our current thinking?" is represented.

- Read canon through `canonical-claim-read` / the `canon` API operation, or the
  `canonical_claims` block in a context package. Each active claim carries a
  re-evaluation directive; honor `due_for_reconfirmation`/`overdue` as a caveat.
- A claim marked current is a recency-of-declaration, not a verified truth.
  Code never judges whether a claim still holds — that is the live reviewer's
  job (`canonical-claim-review-run --reviewer live`).
- Propose canon changes through the governed path (`canonical-claim-record` /
  `canonical-claim-supersede`) with evidence and provenance. Direct human edits
  are caught by the canon-edit watcher and reconciled by the live reviewer
  (`canon-edit-reconcile-run`).
- `uncertain` or invalid judgments are held for human review (`pending_human_review`)
  and surface in chat. Do not treat a held item as canon.
- Review is model-mediated and non-anthropic: the `model_client` rejects
  anthropic routes. Default route is `zai/glm-5.2`; override per root with the
  `STATE_SYSTEM_CANON_MODEL` environment variable.

## Source Integration Rule

Every new source needs a declared source module, a capability connector,
preflight evidence, freshness evidence, optional index refs, and package or
pressure coverage where it affects answers. The short path is documented in
`README.md` under "Integrating Sources"; the detailed contract is in
`docs/source-modules.md`.

## Fixture Names

`SampleCo`, `ResearchCo`, and `PortfolioCo` are public synthetic fixtures unless a file
explicitly says it is deployment-specific. They are not required runtime names.
Real deployments should use their own instance refs, connector refs, source
refs, and package IDs.

## Local Artifact Hygiene

Do not commit:

- `.workgraph/`
- `.wg-worktrees/`
- private state roots
- credential files
- local source indexes
- generated package exports from private deployments

