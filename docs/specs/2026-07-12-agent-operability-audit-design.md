# Agent-Operability Audit — Design

**Status:** Design recovered & durably captured (resurrection artifact)
**Origin:** pi session `019f56a2` (cwd `/Users/braydon/projects`), which crashed 2026-07-12 ~13:01 EDT at turn 30, mid-approval. This document reconstructs the design that lived only in that session's live context so the work survives any further crash.
**Recovered:** 2026-07-12 by Avery from session history + `pi-crash.log`.
**Reference implementation:** `paia-supernote` — "verbose guidance is part of the product."

---

## 1. Problem

There is a scattered estate of agent-callable surfaces (CLIs, HTTP APIs, MCP tools, operational scripts) under `/Users/braydon/projects`. A first pass found **71 repositories** with **21 clear API/CLI projects** — enough to confirm the problem is real, not enough to distinguish a maintained product from an old experiment or a library that merely exposes an entry point.

"Exists in a repo" and "can actually be used" are treated as **separate facts**. This prevents dead experiments from masquerading as live tooling.

## 2. Outcome of this phase

An **audit, not a redesign.** The output is:

1. **Registry** — one canonical record per agent-callable surface.
2. **Overlap map** — where two tools do the same job, and the handoffs between them.
3. **Conformance matrix** — each surface scored against the standard (§4).
4. **Prioritized gaps** — what to fix first, and why.

The common-interface design comes *afterward*, based on what the estate actually contains.

## 3. Method

Build an **estate registry and conformance matrix** (chosen over per-repo reports and over a direct diff-against-supernote). `paia-supernote` is the reference evidence; conformance rules are separated by surface type — **CLI, HTTP API, MCP, operational script** — so principles stay shared without forcing identical mechanics.

For each surface, record: repository, entry point, installation/runtime state, current consumers, documentation, last meaningful activity, likely canonical owner.

Then run **safe, non-mutating probes**: capability discovery, `--help` / schema inspection, health checks, harmless invalid calls. Preserve exact output as evidence; assess whether the surface teaches an agent how to recover.

**Will not:** start unknown services, install packages, change data, archive code, or declare anything dead merely because it is old.

## 4. Agent-operability standard (10 criteria)

Scored as factual states — **present / partial / absent / unknown** — never a synthetic number. A single score hides the difference between "poor help text" and "a write command can silently damage data."

1. **Discovery** — Can an agent find the tool via a skill, registry, package entry point, service schema, or obvious top-level help?
2. **Capability guidance** — Does it explain what each operation does, when to use it, and what *not* to use it for?
3. **Contract clarity** — Are required inputs, allowed values, limits, defaults, and worked examples visible before execution?
4. **Operational narration** — Does success output say what changed, what was skipped, why, and what evidence/identifiers were created?
5. **Safe mutation** — Where relevant: dry-run, idempotency, backup, confirmation, honest partial-failure behavior?
6. **Machine-readable mode** — Stable JSON/schema output alongside prose, with meaningful exit status or HTTP status?
7. **Repair handshake** — On failure: stable error, exact mismatch, expected shape, valid example, retryability, safest next command/call?
8. **Authentication & permissions** — Can an agent distinguish missing credentials vs expired session vs insufficient permission vs needs-a-human?
9. **Workflow continuation** — Does the surface tell the agent what to do next, instead of leaving it to guess?
10. **Traceability** — Version, owner, source repo, logs, affected resources, consumers identifiable?

`paia-supernote`'s safety pipeline applies where writes are destructive; it is **not** imposed on read-only or stateless tools without reason.

## 5. Recovered plan (from crashed session's todo list)

1. ✅ Explore API and CLI landscape *(71 repos, 21 clear API/CLI projects)*
2. ✅ Offer visual companion if useful
3. ✅ Clarify audit outcome *(audit, not redesign)*
4. ✅ Compare audit approaches *(estate registry + matrix chosen)*
5. ✅ Present audit design *(this document)*
6. ✅ Write audit design document *(this file)*
7. ☐ Review audit specification
8. ☐ Obtain specification approval
9. ☐ Plan audit execution → build registry → probe → conformance matrix → gaps

## 6. Open scope question

The crashed session was auditing the **full estate**. The triggering request referenced "crm," which may mean Braydon wants the CRM-adjacent surfaces (Synthyra CRM, graph-CRM, `state-system/crm_operating_picture`) audited **first as a focused slice**. Default if no redirect: proceed full-estate, since that is the work that was in flight.
