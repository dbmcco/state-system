<!-- WG-managed -->
# WG (project-specific guide)

This file is the **layer-2** project guide for agents working in this
WG project. It is NOT the universal chat-agent / worker-agent
contract — that is bundled inside the `wg` binary and emitted by:

```
wg agent-guide
```

Run `wg agent-guide` at session start (or read its output from a previous
session) to get the universal role contract: chat agent vs dispatcher vs worker
distinction, `## Validation` requirement, smoke-gate, cycle handling, git
hygiene, worktree isolation, "no built-in Task tool" rules, etc.

This file only covers things specific to this project. Add project-specific
build commands, test commands, architecture notes, and service recipes here.

**At the start of each session, run `wg quickstart` in your terminal to orient yourself.**
Use `wg service start` to dispatch work — do not manually claim tasks.

This guide is written to both `CLAUDE.md` and `AGENTS.md` and kept in
lock-step. The two files exist because Claude Code and Codex CLI look for
different filenames, but they should never drift in content. Any divergence is
a bug. Update both together.

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
