# Catch Points

The State System should catch different kinds of things at different layers.

The core rule is:

```text
catch facts early
catch meaning with the model
catch risk late
catch broad implications through rollups
```

Do not catch "marketing opportunity" at source ingestion. Catch the source fact
early, preserve evidence, route and package it, then let Laura judge whether it
is a marketing opportunity with the right constraints.

## Catch Point Map

```text
source adapter
  -> dedupe / idempotency
  -> trigger / evidence packet
  -> state review
  -> committer
  -> recent-change registry
  -> persona routing
  -> context package
  -> opportunity review
  -> governance / approval
  -> rollups
  -> audits
```

Each layer catches a different class of issue.

## 1. Source Adapter Catches Facts

Source adapters catch raw changes from systems of record.

The draft source event contract is `schemas/source-event.schema.json`; see
`docs/concepts/source-events-and-idempotency.md`.

Examples:

- Linear task done
- Linear deal moved stages
- GitHub PR merged
- Workgraph task completed
- Speedrift finding created
- Drive document updated
- meeting completed

This layer should capture:

- source system
- source event type
- stable source event id
- actor
- timestamp
- old value and new value, when available
- source refs
- raw payload summary

This layer should not decide:

- whether a deal win is post-worthy
- whether a task completion means project health improved
- whether a PR merge means launch readiness
- whether Laura should act

## 2. Dedupe Catches Replays

Many source events can arrive twice.

Examples:

- webhook and scheduled sync report the same Linear deal stage change
- GitHub webhook retries after timeout
- Workgraph event replay happens during recovery

Dedupe should catch:

- identical source event ids
- same source ref and timestamp
- same state transition already committed
- semantic duplicate when the model or committer can identify it safely

The goal is to avoid duplicate journal entries, duplicate recent-change cards,
and duplicate agent opportunities.

## 3. Trigger And Evidence Catch Provenance

The trigger and evidence packet catch provenance.

They answer:

- what started this review?
- what source refs support it?
- what evidence was resolved?
- what evidence is missing?
- which state objects might be affected?
- which governance policies might apply?

This layer makes the later model decision auditable.

## 4. State Review Catches Durable Meaning

The model review catches whether a source fact changes durable state.

Examples:

- Linear deal moved to won -> deal state can update
- GitHub review comment says "before launch" -> obligation candidate
- repeated Speedrift finding -> project risk or agent memory candidate
- task done without evidence -> operational follow-up, not necessarily project
  health

This is where fact becomes interpretation.

The model may decide:

- update state
- write memory
- request evidence
- queue rollup
- propose action
- no-op

## 5. Committer Catches Contract And Authority Problems

The committer catches whether proposed effects are allowed.

It checks:

- schema validity
- target state write permission
- evidence refs
- actor authority
- approval requirements
- risk class
- duplicate journal append
- stale package constraints for external action

The committer does not reinterpret the business meaning. It accepts, rejects, or
holds effects based on contracts and governance.

## 6. Recent-Change Registry Catches Attention Candidates

After accepted commits and relevant source events, the recent-change registry
catches "this may deserve attention."

It records:

- what changed
- affected state refs
- source refs
- commit and journal refs
- candidate personas
- routing reasons
- relevance tiers
- freshness metadata
- unresolved follow-up refs

This is not an agent inbox yet. It is the shared attention index.

## 7. Persona Routing Catches Who Should Care

Routing catches likely audience.

Examples:

- Patrick gets operational handoff and source-of-truth issues as `primary`
- Laura gets deal wins as `primary` or `secondary` if marketing-relevant
- Laura gets low-level software tasks as `excluded` or `ambient` unless they
  affect proof, campaign, launch, relationship, public claim, or market-facing
  capability

Routing should record reasons. Hidden routing is hidden business logic.

## 8. Context Package Catches What The Agent Needs

The context package catches the bounded working set.

For Laura, a package may include:

- deal summary
- relationship sensitivity
- marketing operating picture
- proof-point gaps
- external-copy policy
- relevant memory
- excluded operational context summary

It should not include every operational task or private negotiation detail.

For Patrick, a package may include:

- source-of-truth records
- owner and next-action gaps
- contract or obligation context
- stale records
- approval boundaries
- operations operating picture

The package prepares the workbench. The model still decides.

## 9. Opportunity Review Catches Salience

The model catches whether a routed, packaged change is actually an opportunity.

Examples:

- Laura sees a deal win and proposes an internal proof-point note
- Laura no-ops because the relationship is private
- Laura drafts LinkedIn copy for approval only
- Patrick opens internal follow-up for missing handoff detail

Code should not contain rules like:

- if deal is won, create LinkedIn post
- if PR merged, mark launch-ready
- if task done, mark project healthy

Those are model decisions.

## 10. Governance Catches Risk

Governance catches whether proposed actions can happen.

It applies to:

- external publication
- customer naming
- relationship-sensitive claims
- legal or contract commitments
- protected mission or strategy changes
- memory promotion to shared state
- package read permissions and redaction

Governance can allow internal drafts while blocking external execution.

## 11. Rollups Catch Broader Implications

Rollups catch the broader picture after child state changes.

Examples:

- deal won affects revenue/pipeline operating picture
- deal won may affect marketing operating picture
- GitHub review commitment affects launch readiness
- repeated task failures affect project risk and agent memory

Rollups should not cascade blindly. They should be queued and reviewed.

## 12. Audits Catch Misses

Audits catch what routing and packaging missed.

Audits should inspect:

- excluded recent-change entries
- ambient entries no agent reviewed
- duplicate source events
- stale context packages
- overdue rollups
- pending approvals
- repeated model no-ops later contradicted by outcomes

This is how the system improves routing and packaging without hiding mistakes.

## Southern Abrasives Example

The Southern Abrasives fixture exercises the catch points, starting with
`examples/source-linear-southern-abrasives-won.json`:

1. Linear adapter catches deal moved from proposal to won.
2. Dedupe uses the Linear source event id.
3. Trigger and evidence packet preserve Linear refs.
4. Model updates deal state to won.
5. Committer accepts deal state update and queues rollups.
6. Recent-change registry catches attention candidate.
7. Routing sends Patrick `primary`, Laura `secondary`.
8. Laura package includes marketing context and excludes operational handoff
   detail.
9. Laura model proposes internal proof note and approval-gated LinkedIn draft.
10. Governance holds external publication pending approval and fresh evidence.
11. Rollups review operations and marketing operating pictures.

## Design Rule

Catch the earliest reliable fact at the earliest layer.

Catch the meaning only when the model has enough context.

Catch the action only after governance has enough authority and freshness.
