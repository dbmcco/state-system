# PAIA Memory Adapter Boundary

State System should be able to use `paia-memory` without becoming a PAIA-only
system.

The useful boundary is an adapter boundary. `paia-memory` can provide evidence,
facet, semantic recall, digest, and active context primitives. State System
continues to own organizational state semantics, journal commits, materialized
snapshots, governance, routing, and promotion from private memory into shared
truth.

## Why Reuse PAIA Memory

`/Users/braydon/projects/experiments/paia-memory` already contains working
implementations for:

- evidence ingestion and deduplication
- tenant-scoped evidence queries
- facet upserts with history
- facet layers and provenance
- triplets
- digests
- embeddings and semantic retrieval
- active context sections

Those are infrastructure concerns State System should not rebuild unless the
adapter contract proves insufficient.

## Boundary Rule

PAIA memory stores recallable material. State System stores durable interpreted
organizational state.

That means:

- source events may be mirrored into PAIA evidence
- persona and agent memories may map to PAIA facets
- recent context packages may draw from PAIA retrieval
- PAIA active context may supply working context sections
- State System journals remain the source of state mutations
- State System snapshots remain the materialized current view
- State System governance decides promotion and external action

PAIA evidence or facets should never silently mutate a State System snapshot.

## Adapter Shape

The adapter should expose a small capability interface:

```text
ingest_evidence(source_event) -> evidence_ref
query_evidence(filters) -> evidence_refs
upsert_memory_facet(agent_ref, memory_entry) -> memory_ref
query_memory(agent_ref, filters) -> memory_refs
build_recall_context(package_request) -> context_sections
record_digest(scope, period, content) -> digest_ref
```

The concrete PAIA implementation can map those calls to `EvidenceLedger`,
`FacetStore`, digest stores, embedding search, and `ActiveContextStore`. A local
file-backed implementation can satisfy the same interface for tests and
non-PAIA deployments.

## Promotion Path

Promotion from agent memory to shared state is a State System workflow:

```text
agent experience
  -> memory proposal
  -> private or agent-scoped memory write
  -> promotion candidate
  -> review packet
  -> governance check
  -> accepted state journal entry
  -> materialized snapshot
```

The adapter can persist the memory proposal and retrieve supporting evidence.
It cannot approve promotion by itself.

## Tenant And Scope Mapping

PAIA memory uses tenant isolation. State System should map scopes explicitly:

- organization scope -> tenant or tenant namespace
- agent scope -> tenant plus agent namespace
- project scope -> metadata filter or namespace
- source system scope -> evidence metadata and source refs

This prevents Laura's private learned marketing patterns from appearing as
LightForge Works organizational state until they are promoted.

## Non-Goals For The First Adapter

The first adapter should not:

- require a running PAIA deployment for local State System tests
- copy large source artifacts into State System state objects
- let semantic recall override source-backed evidence checks
- treat facets as snapshots
- treat active context as durable state
- promote memory without a journal entry and governance result

## Pressure Test

If Laura learns a positioning pattern from repeated campaign reviews:

1. PAIA memory can store the learning as an agent-scoped facet.
2. State System can include the memory in Laura's context package.
3. Laura can propose promotion into a marketing narrative state object.
4. Governance checks evidence, confidence, authority, and approval needs.
5. The committer writes a state journal only if the proposal is accepted.

If any step is skipped, the system has confused recall with truth.
