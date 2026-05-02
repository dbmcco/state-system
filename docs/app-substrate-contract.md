# Application Substrate Contract

**Status:** Planning contract  
**Scope:** Outreach Engine, Prospect Researcher, Meeting Manager, Thoughtforge, Visual Forge, LFW AI Graph CRM, PAIA memory, and State System

## Purpose

This contract defines the minimum State System substrate the new application repos should build against before full runtime implementation exists.

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

These package names can be represented through `ContextPackage.package_type` extensions later. Until schemas change, they can live in `review_goal`, `persona_context.watched_domains`, and `state_context.snapshots`.

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

1. **Fixture the substrate first.** Create example context packages, model proposal outputs, governance policies, commit results, and cross-app refs for the five apps. These fixtures prove the contract before app implementation.
2. **Pressure test integrations.** Use `docs/app-integration-pressure-tests.md` to prove handoffs, approval gates, qualitative learning, stale-package behavior, CRM updates, and hidden-heuristic drift with fixture traces.
3. **Plan Prospect Researcher and Outreach Engine together.** They share campaign state, contact state, Prospect Opportunity Packages, Engagement Intelligence, and CRM handoff contracts.
4. **Plan the CRM/contact intelligence improvements.** LFW AI Graph CRM remains the relationship system of record, but it needs shared contact refs and app-facing handoff/update contracts.
5. **Plan Meeting Manager.** Meeting Manager should consume the contact/relationship spine and then feed coordination updates back into State System, CRM, Prospect Researcher, Outreach Engine, Thoughtforge, Folio, memory, and task systems.
6. **Plan Thoughtforge.** Thoughtforge can build on author, idea, meeting-derived idea, and corpus state once the app package pattern is proven.
7. **Plan Visual Forge.** Visual Forge can build on the same qualitative learning/proposal pattern, with visual workspace state and execution orchestration as its special concern.
8. **Only then move into implementation slices.** Each app should start with one vertical slice that uses source evidence, a bounded context package, model interpretation, proposal/approval, commit result, and a visible app outcome.

This sequence does not require a complete State System runtime. It does require contract fixtures, integration pressure-test traces, and conformance checks so app teams do not invent local state, hidden heuristics, or bypassed approval flows.

## Minimum Readiness Before App Implementation

Before serious app implementation, State System should provide:

1. Example context packages for Prospect Researcher, Outreach Engine, Meeting Manager, Thoughtforge, and Visual Forge.
2. Example model proposal outputs for each app package type.
3. Governance policy examples for human approval gates.
4. Commit result examples for accepted, pending, rejected, and no-op outcomes.
5. A cross-app reference convention for app-local ids, CRM ids, artifact ids, and state object ids.
6. Fixture traces for the required scenarios in `docs/app-integration-pressure-tests.md`.
7. A short conformance checklist proving apps are not bypassing proposal, approval, evidence, or state-commit flows.

The apps can build against fixtures first. A complete State System runtime is not required before app planning, but these contract fixtures are.
