# Recent Change Registry And Agent Opportunities

The State System needs a recent-change registry.

This registry is not the journal and not a task tracker. It is an index of
things that changed recently across source systems and State System commits, so
agents can ask: what changed, what might matter, and what should I review?

## Why This Matters

Many useful agent actions begin with change awareness, not direct instruction.

Examples:

- a Linear task is marked done
- a Linear project moves from one stage to another
- a deal moves to won, lost, stalled, or at-risk
- a GitHub PR is merged
- a GitHub review comment creates a follow-up obligation
- a Workgraph task is completed or rejected
- a Speedrift finding recurs across multiple tasks
- a campaign metric changes
- a meeting produces a new decision or blocker

Those source events may or may not require durable state updates. They may also
create opportunities for agents.

Example: if a deal moves to won, Laura may want to propose a LinkedIn post,
customer story, founder update, campaign proof point, or internal announcement.
That should not be hardcoded as "deal won means post." It should be a model
review over evidence, relationship context, governance policy, and Laura's
persona.

## Boundary

The recent-change registry stores facts about change.

The model decides whether a change is meaningful.

```text
source event
  -> trigger
  -> model review
  -> state journal / memory / review signal
  -> recent-change registry entry
  -> agent opportunity review
  -> action proposal, no-op, rollup, or approval request
```

The registry should not mutate state directly. It makes changes discoverable.

## Relevance Routing

The registry should not behave like one global inbox where every agent sees
every recent change.

It should support relevance routing:

```text
change entry
  -> domain tags
  -> affected state refs
  -> source-system refs
  -> candidate personas
  -> routing reason
  -> optional escalation path
```

This matters because an agent should not burn attention on changes outside its
role. Laura, as a marketing agent, should not normally review an operational
software-development task just because it changed recently. Patrick, the
operations manager, may care. Laura should see it only if the change crosses
into her watched domains.

Examples of crossing conditions:

- the task completes a capability that can become market-facing proof
- the change affects a campaign, customer story, launch, or public claim
- the change affects a relationship, deal, or named customer
- Patrick or another agent explicitly escalates it as marketing-relevant
- a rollup state Laura watches changes because of the task

This keeps the registry useful without turning it into noise.

## Registry Entries

A registry entry should be small and source-backed.

It should answer:

- what changed?
- when did it change?
- where did it come from?
- which source refs prove it?
- which state objects were affected?
- which journal entries or commit results were produced?
- which agents or personas might care?
- why those agents or personas might care?
- what opportunity class might apply, if any?
- what relevance tier applies for each persona?
- what still needs review?

Early implementation can derive entries from triggers, commit results, journal
entries, and review signals. Later implementation can also ingest source-system
events directly.

## Relevance Tiers

Candidate routing should use a simple relevance tier before a model reviews the
entry.

Suggested tiers:

- `primary`: directly inside the persona's watched domains
- `secondary`: adjacent to a watched domain or parent rollup
- `escalated`: another agent, human, or governance rule flagged it
- `ambient`: visible only in broad review or search
- `excluded`: outside the persona's current scope

These tiers are routing hints, not final judgments. The model can still decide
that a primary item is a no-op or that an escalated item is important.

## What Belongs In The Registry

### Source-System Changes

Examples:

- `linear.task.completed`
- `linear.project.stage_changed`
- `linear.deal.stage_changed`
- `github.pull_request.merged`
- `github.review_comment.added`
- `workgraph.task.done`
- `speedrift.finding.created`

These are facts. They become evidence refs and candidate triggers.

### State-System Changes

Examples:

- state object updated
- journal entry appended
- snapshot materialized
- memory entry written
- rollup requested
- review signal emitted
- approval pending

These are State System facts. They show what the system already interpreted and
what still needs attention.

### Opportunity Signals

Examples:

- marketing opportunity
- sales follow-up opportunity
- relationship follow-up opportunity
- operational cleanup opportunity
- launch-readiness review
- onboarding update opportunity
- agent learning opportunity

These should be treated as hints, not decisions. The model still decides
whether an opportunity is real.

## Agent Watch Queries

Agents should be able to query recent changes from their own perspective.

Laura might ask:

- what changed recently in campaigns, deals, relationships, capabilities, or
  operating pictures?
- did anything become marketable?
- did any proof point become stronger?
- did a deal move to a stage that deserves a public or internal update?
- is there enough evidence and approval to draft external copy?

Patrick might ask:

- what changed recently in contracts, obligations, projects, or operating
  pictures?
- which records moved stage without owner or next action?
- which done tasks did not create expected evidence?
- which changes created follow-up obligations?

The same registry supports both agents, but the model's persona context changes
what each agent notices.

It should also change what the registry returns by default. Laura's default
recent-change query should prefer campaigns, deals, relationships, market-facing
capabilities, proof points, launches, and marketing operating-picture updates.
Patrick's default query should prefer obligations, contracts, operational
projects, missing owners, stale records, follow-up risks, and source-of-truth
gaps.

Low-level software-development tasks should usually route to Patrick or a
project/technical agent first. Laura should receive them only when a state
change, rollup, or explicit escalation makes them marketing-relevant.

## Routing Examples

### Software Task Done

Source event:

```text
linear.task.completed
task: Add retry handling to webhook worker
project: Internal workflow reliability
```

Likely routing:

- Patrick: `primary` if it affects operating reliability, launch readiness, or
  follow-up state
- Laura: `excluded` or `ambient` by default

Laura should not review this unless the task becomes evidence for a public
claim, customer proof point, launch note, or campaign message.

### Capability Becomes Marketable

Source event:

```text
github.pull_request.merged
capability: Auditable workflows
review: accepted release note says customer-facing audit trail is ready
```

Likely routing:

- Patrick: `primary` for launch readiness and obligations
- Laura: `secondary` or `escalated` if the capability can support external
  positioning, proof, or a launch post

Laura still should not publish directly. She may propose a draft or internal
brief, subject to governance.

### Deal Stage Changed

Source event:

```text
linear.deal.stage_changed
deal: Southern Abrasives
from: proposal
to: won
```

Likely routing:

- Patrick: `primary` for operational handoff, owner, next action, document
  control, and delivery readiness
- Laura: `primary` or `secondary` for proof point, announcement, customer story,
  or relationship-sensitive campaign opportunity

## Linear Deal Example

Source event:

```text
linear.deal.stage_changed
deal: Southern Abrasives
from: proposal
to: won
evidence: linear:deal:southern-abrasives
```

Possible State System interpretation:

- update deal state to won, with evidence
- update relationship state if trust or commercial relationship changed
- queue operating-picture rollup for revenue/pipeline
- add a recent-change registry entry visible to Laura and Patrick

Possible Laura opportunity review:

- maybe propose a LinkedIn post
- maybe propose an internal proof-point note
- maybe propose a customer story draft
- maybe no-op because the relationship is private, sensitive, or not approved

The model should consider:

- whether public announcement is allowed
- whether the client can be named
- whether the deal has proof points
- whether the claim is relationship-sensitive
- whether approval is required
- whether there is a better internal action than external posting

## External Publication Boundary

Laura may draft a LinkedIn post as an internal action proposal.

Laura should not publish it directly.

The existing external-copy governance policy applies:

- drafting is allowed
- recommending is allowed
- publication requires approval
- claims need evidence
- client naming may require explicit permission

This keeps the opportunity loop useful without turning recent-change awareness
into uncontrolled external communication.

## Model-Mediated Opportunity Loop

The opportunity loop should look like this:

```text
agent asks for recent relevant changes
  -> registry returns candidate change cards
  -> context packager builds a persona-specific package
  -> model reviews candidates with persona + governance + state context
  -> model emits no-op, state proposal, memory proposal, action proposal, or
     approval-gated publication proposal
```

The key point: code retrieves candidate changes, but the model decides salience.

Code should not contain rules like:

- if deal stage is won, create LinkedIn post
- if task is done, mark project healthy
- if PR is merged, mark capability launch-ready

Those are interpretive decisions.

## First Implementation Implication

The first harness should add a local `RecentChangeStore` after basic commit and
materialization work.

Minimum useful behavior:

1. record every accepted commit result as a recent change
2. index affected state ids, journal ids, source refs, actor, and timestamp
3. index candidate persona refs, routing reason, opportunity class, and relevance
   tier when known
4. expose a query by persona, state family, source system, relevance tier, and
   recency
5. build persona-specific context packages from selected changes
6. allow a fixture opportunity review for Laura

The first fixture is:

```text
Linear deal stage changed to won
  -> source event captured and deduped
  -> deal state updated
  -> recent-change registry entry
  -> Laura context package
  -> Laura reviews marketing opportunity
  -> Laura proposes internal LinkedIn draft
  -> external publication is pending approval
```

This fixture would test a full chain from operational change to marketing
opportunity while preserving governance.

The first fixture version now lives in:

```text
examples/source-linear-southern-abrasives-won.json
  -> examples/linear-southern-abrasives-won-trigger.json
  -> examples/linear-southern-abrasives-won-model-review-packet.json
  -> examples/linear-southern-abrasives-won-model-proposal-output.json
  -> examples/linear-southern-abrasives-won-commit-result.json
  -> examples/recent-linear-southern-abrasives-won.json
  -> examples/laura-southern-abrasives-opportunity-context-package.json
  -> examples/laura-southern-abrasives-opportunity-review-packet.json
  -> examples/laura-southern-abrasives-opportunity-model-output.json
  -> examples/laura-southern-abrasives-opportunity-commit-result.json
```

## Design Rule

Do not confuse recency with importance.

The registry should surface what changed recently. The model, using persona,
state, evidence, and governance context, decides what matters.

Also do not confuse global awareness with agent attention.

State System can know about a software task. Laura does not need to see it
unless it becomes relevant to marketing state, relationship state, campaign
state, proof, launch readiness, or a human/agent escalation.
