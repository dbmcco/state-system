# Agent Context Packages

Agents should not have to discover all relevant context from scratch.

The State System should provide bounded, persona-specific context packages that
give each agent enough state, memory, evidence, recent changes, and governance
to do its work without rummaging through the whole organization.

## Purpose

A context package answers:

- who is this agent?
- what domains is the agent responsible for watching?
- what changed recently that is relevant to this agent?
- what current state snapshots matter?
- what recent journals or review signals matter?
- what private agent memory should be recalled?
- what organizational context constrains interpretation?
- what governance policies constrain action?
- what decisions is the model being asked to make?
- what can the agent do, propose, or request next?

This is not meant to make the agent passive. It gives the model the right
working set and tools. The model still decides salience, interpretation,
uncertainty, proposed actions, and no-ops.

## Why Packaging Matters

Without context packages, agents face two bad options:

1. Search too broadly and waste attention on irrelevant operational noise.
2. Search too narrowly and miss important state, memory, or governance context.

Laura should not need to inspect every software task to find marketing
opportunities. Patrick should not need to inspect every campaign draft to keep
operations clean. Each agent should receive a working package shaped by persona,
watched domains, recent-change routing, current state, memory, and governance.

## Relationship To Existing Packets

The current model review packet is event-specific:

```text
trigger
  -> evidence packet
  -> state context
  -> model proposal output
```

An agent context package is agent-specific:

```text
persona
  -> standing context
  -> recent relevant changes
  -> current state snapshots
  -> agent memory
  -> governance constraints
  -> available tools/actions
```

The two should work together. A context package can produce one or more model
review packets when the agent decides a specific change deserves review.

## Package Types

### Standing Package

The baseline package an agent gets at the start of a session or scheduled run.

Includes:

- persona and facets
- authority boundaries
- watched domains
- current operating picture relevant to the agent
- active state objects in the agent's lane
- high-confidence memory and active draft memory
- governance policies for likely actions

Example: Laura's standing package includes marketing operating picture, active
campaigns, relevant deals and relationships, external-copy policy, and Laura's
private marketing memories.

### Recent-Change Package

A package built from the recent-change registry.

Includes:

- recent entries routed to the agent
- relevance tier and routing reason
- affected state refs
- source refs
- review signals and commit results
- unresolved follow-ups or approvals

Example: Laura gets recent deal, relationship, campaign, proof-point, launch,
and market-facing capability changes. Low-level software tasks are excluded or
ambient unless they become marketing-relevant.

### Opportunity Package

A package built when a candidate opportunity deserves deeper review.

Includes:

- the candidate change card
- relevant state snapshots
- evidence refs and resolved summaries
- relationship sensitivity
- campaign or positioning context
- applicable governance policies
- prior similar memory
- allowed output types

Example: a deal moves to won. Laura receives an opportunity package asking
whether to propose a LinkedIn draft, internal proof-point note, customer story
draft, or no-op.

### Deep-Dive Package

A package built after the model asks for more context or a human explicitly
requests deeper review.

Includes:

- expanded journal history
- source excerpts
- related state graph
- prior decisions
- counterevidence
- unresolved approvals

Deep-dive packages should be explicit. They are more expensive and should not be
the default context every agent receives.

## Package Contents

A useful package should have these sections:

```text
package_id
package_type
created_at
persona_context
task_or_review_goal
recent_change_context
state_context
journal_context
memory_context
evidence_context
governance_context
relationship_sensitivity
available_actions
excluded_context_summary
open_questions
```

`excluded_context_summary` matters. The system should be able to say, for
example, "Low-level software tasks were excluded unless routed as launch,
relationship, campaign, or proof-point relevant." This makes omissions explicit
without forcing the model to inspect irrelevant detail.

## Packaging Is Not Decision Logic

Code can package context by:

- persona watched domains
- explicit state refs
- source refs
- recency window
- relevance tier
- governance scope
- parent/child state refs
- memory refs

Code should not decide:

- whether a deal win deserves a LinkedIn post
- whether a software task is marketable
- whether a PR proves launch readiness
- whether a relationship update should become external copy

Those are model decisions.

The package gives the model the right inputs and the right available actions.

## Laura Example

Laura's recent-change package should include:

- recent campaign state changes
- deal stage changes with marketing or relationship relevance
- relationship updates that may affect messaging or proof
- market-facing capability updates
- customer proof or metric changes
- marketing operating-picture rollups
- external-copy governance policy
- Laura's relevant private memory

It should usually exclude:

- internal software implementation tasks
- contract document control
- finance admin tracking
- low-level delivery chores
- source-of-truth cleanup records

Those excluded items can still reach Laura through escalation if they become
marketing-relevant.

## Patrick Example

Patrick's recent-change package should include:

- operational tasks and stage changes
- obligations and contracts
- GitHub review commitments
- Workgraph completions without evidence
- stale or ownerless records
- launch-readiness blockers
- operations operating-picture rollups
- source-of-truth governance

It should usually exclude:

- campaign copy exploration
- social post drafts
- broad narrative experiments
- marketing creative variants

Those can still reach Patrick if they create commitments, approvals, delivery
handoffs, or operational follow-up.

## First Implementation Implication

The first implementation should include a `ContextPackager` interface before
live integrations.

Minimum behavior:

1. Build a standing package from a persona file and current snapshots.
2. Build a recent-change package from `FileRecentChangeStore`.
3. Build an opportunity package from one recent-change entry.
4. Preserve excluded-context summaries.
5. Return package JSON that can be passed into the model reviewer.

The first fixture extends the Linear deal-won scenario:

```text
Linear deal stage changed to won
  -> source event captured and deduped
  -> deal state updated
  -> recent-change entry routed to Laura
  -> Laura opportunity context package
  -> model reviews package
  -> LinkedIn draft action proposal pending approval, or no-op
```

That would test whether packaging can give Laura enough context to act without
making her scan unrelated operations.

The first fixture version is:

```text
examples/recent-linear-southern-abrasives-won.json
  -> examples/laura-southern-abrasives-opportunity-context-package.json
  -> examples/laura-southern-abrasives-opportunity-review-packet.json
  -> examples/laura-southern-abrasives-opportunity-model-output.json
  -> examples/laura-southern-abrasives-opportunity-commit-result.json
```

## Design Rule

Agents should be given enough context to exercise judgment, not so much context
that they become a search engine over the whole company.

The package is the prepared workbench. The model is still the craftsperson.
