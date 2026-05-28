# Relationship Substrate Open-Source Readiness

Relationship Substrate is the source-owned module provider for relationship
state. State System declares and federates the interface; it should not become a
second relationship note store. This runbook is operator-facing: it tells you
how to confirm a Relationship Substrate deployment is OSS-farmable from a State
System instance.

The canonical module spec lives in the Relationship Substrate repo at
`docs/SOURCE_MODULE_SPEC.md`. The OSS-safe fixture is
`examples/source_module/relationship_substrate_records.json`. State System
mirrors the boundary here; it does not redefine it.

## Module Boundary

The reusable module surface is:

- durable subjects: `person` and `organization`
- edges: `affiliation` and `interaction`
- contextual corrections: `subject_note`
- read: operating picture, contact and history-backed people search, dossier,
  subject-note list
- correction write: `record_subject_note`

`record_subject_note` is a source-owned correction write. It is not an external
side effect such as sending email, mutating a CRM, or changing a public record.

## Public Contracts

Relationship Substrate publishes typed contracts (Pydantic models in
`relationship_substrate.contracts`) and JSON-shape parity for:

- `person`
- `organization`
- `affiliation`
- `interaction`
- `subject_note`
- `record_subject_note` input/output
- `list_subject_notes` input/output
- search result envelopes that expose subject-note context

The public field name for contextual corrections is `subject_note_context`.
Compatibility aliases `subject_notes` and `person_notes` may remain in search
envelopes for transition consumers; they should be treated as deprecated and
documented as such by the source module.

## Subject Notes

Subject notes carry:

- `subject_type`: `person` or `organization`
- `subject_ref` or source-owned subject id
- `note_kind`
- `applies_to`
- note body
- source and source ref
- evidence refs
- author or writer identity when available
- created/updated timestamps
- supersession or expiry when available

Agent behavior on subject notes:

- use them to demote, explain, or correct relationship judgment
- cite or summarize the relevant note when it affects a recommendation
- do not use them as hidden exclusion filters
- do not promote them to canonical profile facts without a governed promotion
  path

## OSS Readiness Checklist

A Relationship Substrate deployment is farmable when all rows below resolve
yes against the upstream repo. The current upstream state is in place for each
row; this runbook is the State System-side gate.

| Artifact | Where | Status |
|---|---|---|
| Source module spec | `relationship-substrate/docs/SOURCE_MODULE_SPEC.md` | in place |
| Typed record contracts (person, organization, affiliation, interaction, subject_note) | `relationship_substrate.contracts` | in place |
| Subject-note record/list IO contracts | `relationship_substrate.contracts` | in place |
| OSS-safe fixture (no private names, emails, paths) | `examples/source_module/relationship_substrate_records.json` | in place |
| README documents `record-subject-note` and `list-subject-notes` as primary CLI | upstream README | in place |
| Compatibility notes for `record-person-note` and `list-person-notes` | upstream README | in place |
| `ASK_NETWORK_CONTRACT.md` describes demote/explain/not-hide behavior for subject-note context | upstream docs | in place |
| `search_history_backed_people` emits `subject_note_context` with `subject_notes`/`person_notes` aliases | upstream search surface | in place |
| Tests prove subject-note context is surfaced as evidence, not as a hard filter | upstream tests | in place |
| No Acme User-specific defaults, local absolute paths, private emails, or provider env in OSS surface | upstream config and docs | required, audit on each release |

The last row is a release-time audit, not a one-time gate. New defaults,
example paths, or env vars added to the upstream repo must be checked for
leakage before they ship into an OSS-tagged release.

## State System Integration

State System's source module registry declares the relationship connector in
`examples/source-modules/source-module-core-connectors.json` under
`source_module.relationship_substrate`. The registry entry binds:

- supported instance kinds: `company`, `person`, `project`
- module modes: `local_sync` (CLI/database) and `federated_query` (governed
  cross-instance lookup with no raw materialization)
- preflight checks: database reachable, `subject_note` table exists, sample
  person or org query
- freshness watermark: latest interaction or subject-note timestamp,
  suggested stale-after `P7D`
- index ownership: `source_system` over the relationship index, with declared
  record kinds including `relationship_operating_picture`,
  `history_backed_person_search_result`, and `source_summary`

Capability packs reference the module by `connector_type=relationship_substrate`
and may declare the following tool surfaces:

- `tool.relationship_substrate.operating_picture`
- `tool.relationship_substrate.search_small_consulting_firm_contacts`
- `tool.relationship_substrate.search_history_backed_people`
- `tool.relationship_substrate.list_subject_notes`
- `tool.relationship_substrate.record_subject_note`

`search_history_backed_people` is the backing read surface for higher-level
relationship search routes that need email/calendar-derived relationship
evidence plus organization enrichment. Capability packs that expose a narrower
search route should declare it as the backing source, not as an unrelated ad
hoc query.

## Federation Rule

Company instances may federate to a personal relationship index only through an
explicit governed route with `local_materialization=false`. They must not copy
raw personal relationship records (person, organization, affiliation,
interaction, subject_note) into company state. The `federated_query` module
mode is the only sanctioned cross-instance path; its backing tool is the
upstream search surface and its outputs are package references and evidence
cards, not row copies.
