# Application Substrate Contract

**Status:** Planning contract with six schema-valid app fixture chains
**Scope:** Outreach Engine, Prospect Researcher, Meeting Manager, Thoughtforge, Visual Forge, LFW AI Graph CRM, PAIA memory, and State System

## Purpose

This contract defines the minimum State System substrate the new application repos should build against before full runtime implementation exists.

Six app-facing contract traces now exist as JSON fixtures under
`examples/app-integrations/`:

- Prospect Researcher -> Outreach Engine candidate handoff
- Outreach reply -> CRM handoff plus secondary contacts and engagement intelligence
- Meeting Manager coordination updates into work, CRM, Prospect Researcher, and Thoughtforge
- Thoughtforge provenance from meeting-derived idea to interview and longform candidates
- Visual Forge qualitative learning into revision and corpus-memory candidates
- CRM relationship outcome learning into Prospect Researcher and Outreach Engine doctrine candidates

The apps should not create parallel state systems. They should produce and consume the existing State System primitives:

- `SourceEvent`
- `StateObject`
- `ContextPackage`
- `ModelProposalOutput`
- `ReviewSignal`
- `CommitResult`
- governance policy
- evidence references
- journal entries
- memory entries

The contract is intentionally app-facing. It names the shared objects and flows each app can rely on while leaving implementation details to the State System runtime.

## Company Capability Packs

`CompanyCapabilityPack` is the company-scoped capability baseline PAIA should
target before local agent/tool wiring.

It declares company identity, source connectors, raw corpus, evidence index,
company memory refs, operating picture refs, action surface, governance,
connector preflight requirements, runtime constraints, freshness, and lineage.

The invariant is:

```text
CompanyCapabilityPack declares and packages company capability context.
It does not prove live access and does not authorize execution.
PAIA preflight proves live access.
Governance authorizes protected action.
```

Term boundaries:

- `raw_corpus`: searchable source set, still owned by source systems.
- `evidence_index`: search/index refs over raw corpus, not truth.
- `company_memory`: interpreted durable organizational memory/state.
- `operating_picture`: projection/read model over state and evidence.
- `action_surface`: actions available in principle, not necessarily credentialed.
- `connector_preflight`: runtime check spec/result boundary.
- `runtime_constraints`: PAIA execution constraints, separate from governance.
- `governance`: approval/authority policy for state promotion and actions.

Ownership boundary:

- State System owns the durable/interpreted middle: company capability packs,
  source refs, evidence refs, company memory, operating picture projections,
  context packages, freshness, proposal/commit, and audit flow.
- Source systems own the raw records and canonical access semantics.
- PAIA runtime owns credentialed connector calls, connector preflight results,
  agent dispatch, approval-gated execution, and per-agent tool exposure.

## Core Principle

Code records evidence, validates schemas, exposes tools, executes accepted effects, and preserves provenance.

Models interpret meaning, decide salience, propose state changes, identify uncertainty, and explain qualitative judgment.

Humans approve judgment-sensitive transitions until a class of proposal earns trust.

## Shared State Objects

The apps should converge on these shared state object types:

| State Object | Primary Users | Purpose |
| --- | --- | --- |
| `company_state` | Prospect Researcher, Outreach Engine, Meeting Manager, Thoughtforge | Durable mission, strategy, offerings, constraints, proof points, current priorities |
| `campaign_state` | Prospect Researcher, Outreach Engine, Thoughtforge | Campaign goal, audience, opportunity type, ICP, channel/surface strategy, accepted doctrine |
| `contact_state` | Prospect Researcher, Outreach Engine, CRM, Meeting Manager | Canonical person/org/contact identity, provenance, confidence, relationships, cross-app refs |
| `relationship_state` | CRM, Meeting Manager, Outreach Engine | Real engagement history, relationship status, open loops, important context |
| `meeting_state` | Meeting Manager, State System, CRM | Meeting identity, attendees, artifacts, prep context, outcomes, continuity |
| `work_state` | Meeting Manager, State System, task/work systems | Commitments, tasks, blockers, follow-ups, workstream continuity |
| `author_state` | Thoughtforge | Author identity, corpus boundaries, voice, topic territories, public/private corpus state |
| `idea_state` | Thoughtforge, Meeting Manager | Claims, frameworks, stories, tensions, open questions, editorial candidates |
| `visual_workspace_state` | Visual Forge | Client/brand/project/campaign/job visual corpus and production memory |
| `doctrine_state` | All apps | Accepted operating learning that changes future model behavior, context packages, or execution options |

Naming can evolve, but the responsibilities should not fragment across app-local stores without a planned migration back to shared state.

## Shared Evidence Contract

Every app-facing proposal should cite evidence references instead of duplicating source blobs.

Evidence refs may point to:

- email/message ids
- CRM engagement ids
- meeting ids, transcript ids, or note ids
- document, spreadsheet, deck, repo, issue, or artifact ids
- generated asset ids
- source URLs or crawler records
- prior state journal entries
- human review decisions

Interpretations are allowed, but they must remain labeled as interpretations. External facts require evidence.

## App Context Packages

Each app should request or receive bounded context packages instead of searching the whole ecosystem.

Minimum app package types:

| Package | Consuming App | Review Goal |
| --- | --- | --- |
| `prospect_opportunity_package` | Prospect Researcher, Outreach Engine | Decide whether an account/person/opportunity combination is worth human review and outreach |
| `outreach_engagement_package` | Outreach Engine, Prospect Researcher, CRM | Interpret replies, CCs, referrals, routing cues, and qualified handoff candidates |
| `meeting_context_package` | Meeting Manager | Prepare a meeting with people, relationship, work, artifact, and prior-meeting context |
| `coordination_update_package` | Meeting Manager, State System, CRM, task systems | Review proposed updates after a meeting |
| `thoughtforge_author_package` | Thoughtforge | Develop author-specific ideas from private and published corpora |
| `visual_forge_workspace_package` | Visual Forge | Produce or revise visual assets from a workspace visual corpus |

The first six app package types are now schema extensions. Later package names
can live in `review_goal`, `persona_context.watched_domains`, and
`state_context.snapshots` until they are promoted into the enum.

## Proposal And Approval Flow

All apps should use the same proposal flow:

1. App emits `SourceEvent` for a meaningful input or outcome.
2. State System assembles a bounded `ContextPackage`.
3. Model interprets the package and emits `ModelProposalOutput`.
4. Governance policy decides whether proposals are accepted, pending approval, rejected, or blocked.
5. Human reviews judgment-sensitive proposals while the system is early.
6. Accepted proposals become journal entries, memory entries, materialized state snapshots, work items, or cross-app events.
7. `CommitResult` records exactly what happened.
8. Future context packages include the accepted update and relevant review outcome.

No app should silently mutate shared state, CRM relationship history, tasks, external communication, public publication, or approved corpora without this flow or an explicit deviation.

## App Responsibilities

### Prospect Researcher

Produces:

- campaign and ICP proposals
- Prospect Opportunity Packages
- opportunity-fit interpretations
- contact readiness and research gap proposals
- contact intelligence updates

Consumes:

- company and campaign state
- CRM outcomes
- Outreach Engine engagement intelligence
- Meeting Manager coordination updates
- shared contact state

### Outreach Engine

Produces:

- engagement intelligence
- qualified CRM handoff proposals
- secondary contact and routing cues
- outreach doctrine candidates
- suppression and follow-up proposals

Consumes:

- Prospect Opportunity Packages
- campaign state
- contact state
- CRM relationship state
- state-approved outreach doctrine

### Meeting Manager

Produces:

- Meeting Context Packages
- Coordination Update Proposals
- meeting-derived action, CRM, contact, prospecting, and Thoughtforge proposals
- commitment and artifact links

Consumes:

- State System context packages
- CRM relationship context
- PAIA memory
- Folio notes
- task/work state
- contact and project state

### Thoughtforge

Produces:

- author corpus updates
- idea and claim proposals
- interview prompts
- longform editorial candidates
- published corpus updates after release

Consumes:

- author state
- private and published corpus state
- Folio notes and transcripts
- meeting-derived idea candidates
- personal dossier and voice evidence

### Visual Forge

Produces:

- visual workspace updates
- finished asset records
- qualitative creative memory
- corpus promotion proposals
- production history and revision paths

Consumes:

- visual workspace state
- human-created and generated assets
- project/client/campaign state
- qualitative review decisions
- provider execution artifacts

### LFW AI Graph CRM

Produces:

- relationship and engagement state
- people/org graph updates
- post-handoff relationship outcomes

Consumes:

- qualified outreach handoffs
- meeting relationship updates
- shared contact intelligence

CRM remains the system of record for real relationship history after qualified handoff.

## Judgment, Learning, And Doctrine

Accepted learning should be represented as state, not hardcoded behavior.

Examples:

- campaign ICP changes
- opportunity-fit interpretation guidance
- outreach tone or handoff interpretation
- meeting commitment approval patterns
- author voice and editorial standards
- visual taste, brand, and production understanding

The form of learning may be qualitative. State System should preserve the human judgment and model interpretation, not collapse it into a brittle threshold unless that threshold is an explicit approved policy or tracked deviation.

Accepted doctrine can take effect immediately where the relevant app North Star says so. The commit result must make the effect visible and traceable.

## Next Work Sequence

The next work should happen in this order:

1. **Keep extending the fixture substrate.** The first six app chains exist; continue promoting pressure scenarios into schema-valid traces when they expose new source, state, approval, memory, or doctrine behavior.
2. **Build substrate read models before app UI.** Company memory and CRM operating picture should be deterministic JSON projections over State System records before any wiki, dashboard, or app screen is treated as product.
3. **Plan Prospect Researcher and Outreach Engine together.** They share campaign state, contact state, Prospect Opportunity Packages, Engagement Intelligence, CRM handoff contracts, and CRM outcome doctrine.
4. **Plan the CRM/contact intelligence substrate.** LFW AI Graph CRM remains the relationship system of record, while State System owns interpreted relationship/opportunity state, evidence refs, freshness, open loops, and agent packaging.
5. **Plan Meeting Manager, Thoughtforge, and Visual Forge from the proven pattern.** Meeting Manager feeds coordination updates into shared state; Thoughtforge builds on author/idea/corpus state; Visual Forge builds on qualitative visual workspace and corpus-memory state.
6. **Move into implementation slices only when the substrate contract is boring.** Each app slice should use source evidence, a bounded context package, model interpretation, proposal/approval, commit result, and a visible app outcome without inventing local state.

This sequence does not require a complete State System runtime. It does require contract fixtures, integration pressure-test traces, and conformance checks so app teams do not invent local state, hidden heuristics, or bypassed approval flows.

## Minimum Readiness Before App Implementation

Before serious app implementation, State System should provide:

1. Example context packages for Prospect Researcher, Outreach Engine, Meeting Manager, Thoughtforge, Visual Forge, and CRM outcome learning.
2. Example model proposal outputs for each app package type.
3. Governance policy or approval examples for human approval gates.
4. Commit result examples for accepted, pending, rejected, and no-op outcomes.
5. A cross-app reference convention for app-local ids, CRM ids, artifact ids, and state object ids.
6. Fixture traces for the required scenarios in `docs/app-integration-pressure-tests.md`.
7. A short conformance checklist proving apps are not bypassing proposal, approval, evidence, or state-commit flows.
8. Substrate read models for company memory and CRM operating picture before durable app UI is built.
9. Company capability pack fixtures before PAIA implements company-scoped tool/corpus access.

The apps can build against fixtures first. A complete State System runtime is not required before app planning, but these contract fixtures are.
