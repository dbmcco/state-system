# System Pressure Test

This document pressure-tests the State System as a whole, after adding recent
changes, persona routing, and agent context packages.

The question is no longer only "can one trigger become one state update?" The
system now has multiple moving parts:

```text
source systems
  -> triggers
  -> evidence
  -> recent-change registry
  -> relevance routing
  -> context packages
  -> model review
  -> governance
  -> journals / memory / snapshots
  -> rollups / review signals / action proposals
```

The pressure test asks where this architecture can fail.

## Pass Criteria

The system is strong enough to start implementation when it can answer:

1. How does a source event become durable state without direct mutation?
2. How does an agent receive enough context without scanning everything?
3. How do we avoid hiding important events through over-filtering?
4. How do we prevent irrelevant changes from flooding every agent?
5. How do we keep source facts, model interpretations, and actions separate?
6. How do we preserve provenance through routing, packaging, review, and commit?
7. How do we handle stale packages, duplicate events, and conflicting agents?
8. How do we keep external actions approval-gated?

## Scenario 1: Laura Is Flooded By Software Tasks

**Trigger:** ten Linear software tasks are completed in one day.

**Failure mode:** Laura receives all ten because they are recent work changes.

**Expected behavior:**

- route low-level software tasks to Patrick or a technical/project agent first
- mark Laura relevance as `excluded` or `ambient` unless a task affects launch,
  proof, relationship, campaign, public claim, or market-facing capability
- include an excluded-context summary in Laura's package
- allow explicit escalation if Patrick or a human sees marketing relevance

**Pressure result:** passes with the recent-change routing model.

**Gap:** the first implementation needs a concrete `recent-change-entry`
contract with candidate persona refs, routing reason, relevance tier, and
excluded-context support.

## Scenario 2: Laura Misses A Marketable Capability

**Trigger:** a GitHub PR merges a customer-facing capability, but it is recorded
as a software task completion.

**Failure mode:** routing excludes Laura because the source event looks
technical.

**Expected behavior:**

- package logic should consider affected state refs and parent rollups, not only
  source-system event type
- if the task updates a market-facing capability, Laura can receive it as
  `secondary` or `escalated`
- model decides whether the capability is actually marketable
- publication remains approval-gated

**Pressure result:** partially passes.

**Gap:** routing needs inspectable reasons and periodic audit. If a source event
is excluded from Laura, the package should say why and which crossing condition
would make it visible.

## Scenario 3: Deal Moves To Won

**Trigger:** Linear deal stage changes from proposal to won.

**Expected behavior:**

- update deal state as a source-backed work/relationship state change
- queue operating-picture rollups for revenue, relationship, and operations
- create recent-change entry visible to Patrick and Laura
- Patrick receives operational handoff context
- Laura receives opportunity context, not all operational task detail
- Laura may propose internal LinkedIn draft, customer story draft, or no-op
- external publication is pending approval

**Pressure result:** passes conceptually.

**Gap:** this should become the next fixture trace because it exercises the
recent-change registry, context package, opportunity review, and governance in
one chain.

## Scenario 4: Same Source Event Arrives Twice

**Trigger:** a Linear webhook and scheduled sync both report the same deal stage
change.

**Failure mode:** duplicate triggers create duplicate journal entries, duplicate
recent-change entries, and duplicate agent opportunities.

**Expected behavior:**

- source refs and source event ids should dedupe before commit where possible
- committer should be idempotent around trigger/source ids
- recent-change registry should collapse duplicate entries or link them as
  duplicates
- model can no-op if duplicate evidence is semantically detected

**Pressure result:** partially passes.

**Gap:** file-backed idempotency and source-event identity are not yet defined.
This was already a current gap, but recent-change indexing makes it more urgent.

## Scenario 5: Context Package Goes Stale

**Trigger:** Laura receives an opportunity package for a deal win, but the deal
is later marked private before Laura reviews the package.

**Failure mode:** Laura drafts external copy from stale package context.

**Expected behavior:**

- context packages should include `created_at`, source refs, and freshness
  metadata
- review should check whether protected state or governance changed after the
  package was built
- committer should block external publication if approval or privacy state is
  stale or missing
- stale package can still support internal no-op or refresh request

**Pressure result:** partially passes.

**Gap:** context packages need freshness/watermark semantics before they are
used for action proposals with external consequences.

## Scenario 6: Patrick And Laura Disagree

**Trigger:** Laura sees a deal win as a marketing opportunity. Patrick sees the
same deal as operationally incomplete because contract paperwork is missing.

**Failure mode:** Laura proposes external announcement while Patrick's state
shows the relationship is not ready.

**Expected behavior:**

- both agents can produce separate interpretations with evidence
- governance blocks publication until relationship and approval requirements are
  satisfied
- operating-picture rollup should preserve the tension
- review signal should show conflict or pending coordination

**Pressure result:** passes if governance and rollups are used correctly.

**Gap:** review signals may need richer conflict semantics later. For now,
uncertainty and pending approval are enough for fixture work.

## Scenario 7: Sensitive Relationship Data Enters A Marketing Package

**Trigger:** relationship state contains private negotiation context. A deal
stage change routes to Laura.

**Failure mode:** Laura's context package includes sensitive operational detail
that should not be used in marketing copy.

**Expected behavior:**

- context packager should include relationship sensitivity and governance
  constraints
- package may include a redacted summary instead of full source detail
- model can request missing evidence or approval, but should not publish
  sensitive details
- committer enforces external-copy and relationship-sensitive policies

**Pressure result:** partially passes.

**Gap:** governance currently covers external copy, but relationship-sensitive
redaction and package-level read permissions are not yet defined.

## Scenario 8: Agent Memory Pollutes Shared State

**Trigger:** Laura repeatedly sees deal wins followed by LinkedIn drafts and
forms a memory that "deal wins should be posted."

**Failure mode:** private memory becomes a hard rule or shared organizational
truth without enough evidence or approval.

**Expected behavior:**

- Laura memory remains private/draft until promotion is explicit
- model can use memory as a hypothesis, not policy
- promotion to shared marketing or governance state requires evidence and
  approval
- no code rule converts deal wins into posts

**Pressure result:** passes with current memory promotion design.

**Gap:** memory confidence decay and stale-memory review are still future work.

## Scenario 9: Rollup Queue Falls Behind

**Trigger:** many child states change, but operating-picture rollups are delayed.

**Failure mode:** context packages include stale operating pictures and agents
make decisions from outdated summaries.

**Expected behavior:**

- packages should include pending rollup signals when parent state may be stale
- recent-change registry can surface "rollup overdue" as operational context
- model can request rollup before making a high-impact recommendation
- low-risk internal actions can proceed with uncertainty noted

**Pressure result:** partially passes.

**Gap:** rollup freshness and overdue rollup semantics need definition before
real scheduled operation.

## Scenario 10: Routing Becomes Hidden Business Logic

**Trigger:** engineers implement routing rules that decide which agent sees
which changes.

**Failure mode:** code silently decides salience by excluding or escalating
items with hardcoded business assumptions.

**Expected behavior:**

- code can route by explicit metadata: persona watched domains, state refs,
  source refs, recency, relevance tier, governance scope, and parent/child refs
- routing reason must be recorded
- excluded-context summary must be visible
- model decides salience and opportunity
- humans can audit routing misses

**Pressure result:** passes only if routing stays inspectable.

**Gap:** routing audit should be a first-class verification concern in the
first harness.

## System Findings

### Finding 1: The Architecture Holds, But Packaging Is Now Core

Context packaging is not optional plumbing. It is the mechanism that keeps
agents focused while preserving enough context for judgment.

Implementation should not jump straight from recent-change entries to model
review. It should build packages first.

### Finding 2: Recent-Change Entries Need A Contract

The registry cannot remain purely conceptual much longer.

Minimum contract fields:

- id
- source event refs
- occurred_at / observed_at
- summary
- affected state refs
- source refs
- journal refs
- commit refs
- candidate persona refs
- routing reasons
- relevance tiers
- opportunity class hints
- unresolved follow-ups

### Finding 3: Context Packages Need A Contract

The package should become a schema before implementation.

Minimum contract fields:

- package id
- package type
- persona context
- review goal
- recent-change context
- state context
- journal context
- memory context
- evidence context
- governance context
- available actions
- excluded-context summary
- freshness metadata

### Finding 4: Freshness Is A First-Class Risk

Packages can become stale. Rollups can become stale. Source records can change
after package assembly.

Before external actions, the committer should check whether protected state,
approval state, or relevant source refs changed after the package was built.

### Finding 5: Routing Needs Auditability

Relevance routing is necessary, but it can hide important events. Every
excluded or escalated item should have a reason that can be inspected later.

The system should support broad ambient review for humans or supervisor agents
to find routing misses.

### Finding 6: Governance Must Apply To Packages And Actions

Governance cannot only inspect final state patches.

It must also constrain:

- what context a persona may see
- what private details are redacted
- which actions can be proposed
- which actions can be executed
- what publication requires approval

### Finding 7: Next Fixture Should Be Linear Deal Won To Laura Package

The next trace should exercise the whole new chain:

```text
Linear deal stage changed to won
  -> deal state update
  -> recent-change registry entry
  -> routing to Laura and Patrick
  -> Laura opportunity context package
  -> model review
  -> internal LinkedIn draft proposal
  -> pending approval for external publication
```

This will test whether the architecture can move from operational fact to
persona-specific opportunity without hardcoding the opportunity.

## Result

The system still holds, but the implementation sequence should change.

Before building live source-system adapters, define and validate:

1. recent-change-entry contract
2. context-package contract
3. routing audit rules
4. freshness/watermark behavior
5. Linear deal-won opportunity fixture

Those pieces are more important than adding another live integration because
they decide whether agents receive the right context and whether the system can
explain why.
