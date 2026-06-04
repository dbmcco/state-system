# State-Backed Mission Control Design

**Date:** 2026-05-04
**Status:** Draft
**Scope:** Generic mission records in State System, with agent-runtime/Speedrift repo-audit as the first consumer fixture

## Problem

Multi-agent work is currently visible mostly through transient chat transcripts,
terminal panes, Workgraph task status, and agent logs. That makes active work
hard to inspect while it is happening and harder to turn into durable state
afterward.

The desired operator experience is a live mission board where a human can see:

- which agents are involved
- what each agent is responsible for
- what each agent is doing now
- what evidence has been collected
- what findings, stumbles, artifacts, and follow-ups exist
- what changed in durable organizational state
- what the system learned
- what requires approval before action

The live board should not become a separate source of truth. It should be a
projection over State System records, agent runtime/agent-runtime events, Workgraph
execution facts, Speedrift findings, and evidence references.

## Goal

Define a reusable State System substrate for mission-oriented multi-agent work.

The first concrete use case is a agent-runtime/Speedrift repo-audit mission similar to a
multi-agent code audit: a coordinator starts a mission, specialist agents inspect
different concerns, findings are gathered, stumbles are recorded, follow-up work
is proposed, and durable state is updated only through journaled, evidenced,
governed commits.

The generic substrate should also support non-agent runtime use cases such as marketing
opportunity review, operations cleanup, launch-readiness review, relationship
follow-up review, onboarding review, and future organizational state reviews.

## Non-Goals

- Do not build the agent runtime shell UI in this spec.
- Do not add live GitHub, Workgraph, Speedrift, or agent runtime adapters in the first
  State System implementation.
- Do not make State System depend on Samantha, Derek, agent runtime shell, or agent runtime event
  names.
- Do not treat a mission transcript as durable truth.
- Do not let source systems or live UI mutate snapshots directly.
- Do not encode mission salience, finding severity, or action choice as hidden
  hardcoded business logic.

## Design Choice

Use **generic State System mission records first**, with agent runtime shell as the first
consumer.

This keeps the reusable contracts in `state-system`:

- `MissionRun`
- `MissionAgentRun`
- `MissionEvent`
- `MissionObservation`
- `MissionFinding`
- `MissionStumble`
- `MissionArtifact`
- `MissionGovernanceReceipt`

agent runtime shell can then render a Jesse-style live mission board as a projection over
those records. agent-runtime-specific agents, surfaces, and execution events become one
adapter family, not the generic model.

## Model And Code Boundary

The model decides:

- whether a mission is meaningful
- which agents or personas should be involved
- what each observation means
- whether a finding is important
- whether a stumble reflects a reusable lesson
- whether a memory proposal is warranted
- whether a state patch, rollup, action, or follow-up should be proposed
- whether no durable update is warranted

Code decides:

- schema validity
- idempotency
- evidence reference presence
- source reference resolution
- read and write authority
- context package assembly
- freshness checks
- governance enforcement
- append-only persistence
- snapshot materialization
- event streaming to access surfaces

Code may route by explicit metadata such as persona watched domains, mission
type, source refs, state refs, and governance scope. Code must not decide hidden
business conclusions such as "this finding is severe enough to fix" or "this
capability is marketable." Those are model judgments over evidence and context.

## Relationship To Existing State System Concepts

Mission Control does not replace existing State System records. It connects
them.

| Existing concept | Role in Mission Control |
|---|---|
| `Trigger` | Starts a mission or adds a mission-relevant event |
| `RecentChangeEntry` | Makes mission-relevant source changes discoverable |
| `ContextPackage` | Provides bounded context to a coordinator or agent |
| `ModelReviewPacket` | Frames a specific model review inside the mission |
| `ModelProposalOutput` | Captures proposed state, memory, action, and rollup effects |
| `CommitResult` | Records what the committer accepted, rejected, or held for approval |
| `ReviewSignal` | Summarizes the durable result of a review |
| `StateJournalEntry` | Records accepted state transitions |
| `StateObject` | Holds the current interpreted state affected by the mission |
| `AgentMemoryEntry` | Stores agent-specific lessons and patterns |
| `GovernancePolicy` | Controls durable writes, approvals, and risky actions |

Mission records are the connective tissue for live, multi-agent execution. State
objects and journals remain the durable truth.

## Proposed Record Types

These records should be added as JSON schemas after this design is approved.
Field names are intentionally close to existing State System schemas.

### MissionRun

A `MissionRun` is a bounded unit of coordinated work.

Required fields:

- `id`
- `mission_type`
- `created_at`
- `created_by_ref`
- `status`
- `summary`
- `objective`
- `source_refs`
- `trigger_refs`
- `root_state_refs`
- `context_package_refs`
- `coordinator_agent_run_ref`
- `agent_run_refs`
- `event_refs`
- `finding_refs`
- `stumble_refs`
- `artifact_refs`
- `governance_receipt_refs`
- `review_signal_refs`
- `freshness`

Initial `mission_type` values:

- `repo_audit`
- `security_review`
- `launch_readiness_review`
- `marketing_opportunity_review`
- `operations_cleanup_review`
- `relationship_followup_review`
- `onboarding_review`
- `custom`

Initial `status` values:

- `created`
- `context_packaging`
- `routing`
- `running`
- `blocked`
- `waiting_on_approval`
- `summarizing`
- `committing`
- `completed`
- `failed`
- `canceled`

`MissionRun` should not contain full transcripts or large source blobs. It
should reference events, artifacts, evidence, and durable state records.

### MissionAgentRun

A `MissionAgentRun` is one participant's role in a mission.

Required fields:

- `id`
- `mission_run_id`
- `agent_ref`
- `persona_ref`
- `role`
- `responsibility`
- `status`
- `model_ref`
- `started_at`
- `completed_at`
- `context_package_refs`
- `review_packet_refs`
- `event_refs`
- `observation_refs`
- `finding_refs`
- `stumble_refs`
- `artifact_refs`
- `memory_entry_refs`
- `token_usage`
- `cost`

Initial `role` values:

- `coordinator`
- `observer`
- `project_explorer`
- `specialist_reviewer`
- `implementer`
- `verifier`
- `summarizer`

Initial `status` values:

- `planned`
- `assigned`
- `starting`
- `running`
- `blocked`
- `waiting`
- `complete`
- `failed`
- `canceled`

Token and cost accounting are optional fields in the generic contract. When an
adapter has usage data, it must write it to `MissionAgentRun.token_usage` and
`MissionAgentRun.cost` so the read model can display it without parsing
transcripts.

### MissionEvent

A `MissionEvent` is an append-only live event in a mission timeline.

Required fields:

- `id`
- `mission_run_id`
- `agent_run_id`
- `created_at`
- `event_type`
- `summary`
- `source_refs`
- `evidence_refs`
- `artifact_refs`

Initial `event_type` values:

- `mission_created`
- `context_package_created`
- `agent_assigned`
- `agent_started`
- `agent_message`
- `tool_call_started`
- `tool_call_completed`
- `tool_call_failed`
- `file_read`
- `evidence_collected`
- `observation_recorded`
- `finding_recorded`
- `stumble_recorded`
- `artifact_created`
- `review_packet_created`
- `model_output_created`
- `commit_result_created`
- `approval_requested`
- `approval_granted`
- `approval_rejected`
- `follow_up_proposed`
- `mission_completed`
- `mission_failed`

Events should support live UI streaming and replay. They are not a substitute
for journal entries. A journal entry is created only when the committer accepts
a model proposal.

### MissionObservation

A `MissionObservation` is a model or agent interpretation recorded during a
mission before it becomes a finding or durable state update.

Required fields:

- `id`
- `mission_run_id`
- `agent_run_id`
- `created_at`
- `summary`
- `interpretation`
- `evidence_refs`
- `related_state_refs`
- `confidence`
- `status`

Initial `status` values:

- `draft`
- `promoted_to_finding`
- `used_in_model_output`
- `superseded`
- `discarded`

Observations are useful for operator visibility and traceability. They do not
mutate state.

### MissionFinding

A `MissionFinding` is a mission-scoped issue, risk, opportunity, or conclusion.

Required fields:

- `id`
- `mission_run_id`
- `agent_run_id`
- `created_at`
- `finding_type`
- `severity`
- `summary`
- `details`
- `evidence_refs`
- `related_state_refs`
- `proposed_action_refs`
- `review_signal_refs`
- `status`

Initial `finding_type` values:

- `security_risk`
- `quality_risk`
- `architecture_risk`
- `dependency_risk`
- `scope_drift`
- `missing_evidence`
- `launch_blocker`
- `operational_gap`
- `opportunity`
- `lesson`

Initial `severity` values:

- `critical`
- `high`
- `medium`
- `low`
- `informational`
- `unknown`

Severity may be proposed by the model and accepted as a finding attribute, but
code should not decide severity from hidden thresholds.

### MissionStumble

A `MissionStumble` records something an agent got wrong, nearly got wrong, had
to correct, or learned from during execution.

Required fields:

- `id`
- `mission_run_id`
- `agent_run_id`
- `created_at`
- `summary`
- `stumble_class`
- `evidence_refs`
- `correction`
- `lesson_candidate`
- `memory_proposal_refs`
- `status`

Initial `stumble_class` values:

- `bad_assumption`
- `missed_context`
- `tool_error`
- `schema_error`
- `routing_error`
- `evidence_gap`
- `overreach`
- `duplicated_work`
- `prompt_gap`
- `unknown`

Initial `status` values:

- `recorded`
- `corrected`
- `memory_proposed`
- `memory_committed`
- `superseded`

Stumbles are one of the main reusable improvements over a session-only
multi-agent UI. They provide a bridge from live execution to agent memory,
prompt evolution, and State System learning.

### MissionArtifact

A `MissionArtifact` references a durable output created or collected during a
mission.

Required fields:

- `id`
- `mission_run_id`
- `agent_run_id`
- `created_at`
- `artifact_type`
- `summary`
- `uri`
- `content_ref`
- `evidence_refs`
- `related_state_refs`
- `status`

Initial `artifact_type` values:

- `transcript`
- `report`
- `patch`
- `diff`
- `test_output`
- `screenshot`
- `log_excerpt`
- `source_excerpt`
- `model_output`
- `commit_result`
- `approval_record`

Large artifact content should live outside the mission record. Mission records
should store stable refs and compact summaries.

### MissionGovernanceReceipt

A `MissionGovernanceReceipt` records a governance check or approval boundary
encountered during a mission.

Required fields:

- `id`
- `mission_run_id`
- `agent_run_id`
- `created_at`
- `policy_refs`
- `controlled_effect`
- `risk`
- `status`
- `summary`
- `approval_refs`
- `commit_result_refs`

Initial `status` values:

- `allowed`
- `pending_approval`
- `rejected`
- `requires_refresh`
- `blocked_by_policy`

This record gives the live UI a concise way to show why an action is blocked
without burying that information inside model output or committer logs.

## First Fixture: agent-runtime/Speedrift Repo-Audit Mission

The first fixture should model a repo-audit mission without live adapters.

Fixture objective:

```text
Audit a repository for security, architecture, dependency, and quality risks.
Preserve evidence, record agent stumbles, propose follow-up work, and update
durable state only through governed State System commits.
```

Candidate mission:

- `MissionRun`: `mission.repo_audit.streamlinear`
- coordinator: `agent_run.repo_audit.coordinator`
- project explorer: `agent_run.repo_audit.project_explorer`
- security reviewer: `agent_run.repo_audit.security`
- architecture reviewer: `agent_run.repo_audit.architecture`
- dependency reviewer: `agent_run.repo_audit.dependencies`
- quality reviewer: `agent_run.repo_audit.quality`

Candidate root state refs:

- `state.repo.streamlinear.project`
- `state.repo.streamlinear.capability.linear-mcp-bridge`
- `state.repo.streamlinear.obligation.security-review`
- `state.repo.streamlinear.operating_picture.delivery`
- `state.agent.security-reviewer`

Candidate source refs:

- `github:repo:example/streamlinear`
- `workgraph:repo:streamlinear:task:audit-linear-mcp`
- `speedrift:repo:streamlinear:review:security-audit-2026-05-04`

Expected fixture outputs:

- one mission run
- six agent runs
- context package refs for coordinator and each specialist
- mission events for assignment, file reads, tool calls, observations, findings,
  stumbles, artifacts, model outputs, and commit results
- at least one security finding with evidence refs
- at least one missing-evidence finding
- at least one stumble that proposes agent memory
- one model proposal output that proposes a project-state update
- one commit result that accepts internal state updates
- one governance receipt that blocks or holds a risky external action
- one review signal that summarizes follow-up work

The fixture should be deterministic and file-backed. It should not require live
GitHub, Workgraph, Speedrift, agent runtime, or model calls.

## Runtime Flow

The generic runtime flow is:

```text
source event or human request
  -> trigger
  -> mission run created
  -> coordinator context package
  -> coordinator model routes mission roles
  -> agent runs created
  -> agent context packages
  -> mission events stream while agents work
  -> observations, findings, stumbles, artifacts recorded
  -> model review packets created for durable interpretation
  -> model proposal outputs
  -> governance and committer
  -> journals, memory entries, review signals, commit results
  -> mission summary and final read model
```

For live agent-runtime/Speedrift execution, Workgraph still owns task execution,
Speedrift still owns drift judgment, and agent runtime agent-runtime still owns agent
tool execution. State System records the interpreted mission state and provides
the access-surface read model.

## agent runtime shell Read Model

agent runtime shell should consume a compact read model rather than query every raw
record directly.

Initial read model sections:

- mission header: objective, status, elapsed time, created by, freshness
- agent roster: role, status, responsibility, current activity, model, cost,
  turns, token usage
- timeline: mission events grouped by agent and event type
- findings: severity, type, status, evidence, proposed follow-up
- stumbles: class, correction, memory status
- artifacts: reports, diffs, transcripts, logs, screenshots
- state effects: accepted journals, snapshots, memory entries, rollups
- governance: pending approvals, blocked effects, refresh requirements
- follow-ups: Workgraph task refs, GitHub issue refs, review signal refs

The UI may look like a live multi-agent board, but every visible card should
have a record id and provenance path.

## Ownership Boundaries

### `state-system`

Owns:

- generic mission schemas
- deterministic fixtures
- file-backed stores for mission records in the first deployment
- validation and fixture replay harness
- mission read model contract
- documentation of generic lifecycle and governance boundaries

Does not own:

- agent runtime shell UI
- live agent subprocess execution
- Workgraph task execution
- Speedrift drift-lane implementation
- GitHub API adapters in the first slice

### `agent-runtime`

Owns:

- emitting agent lifecycle events that can be mapped into mission events
- tool execution and model loops
- risk evaluation at action execution boundaries
- adapter code that can write mission events when running under agent runtime

### `driftdriver` / Speedrift

Owns:

- drift findings
- lane-specific quality/security/spec/dependency judgment
- Workgraph follow-up task creation through existing guarded pathways
- optional adapter events into State System mission records

### Workgraph

Owns:

- execution tasks
- dependencies
- claims
- completion
- validation status
- worker dispatch state

### `agent-runtime-shell`

Owns:

- Mission Control UI
- live rendering
- approval surfaces
- user interactions that request deeper packages, approve proposals, or open
  source artifacts

## Idempotency And Replay

Mission records must be replayable.

Required idempotency rules:

- the same trigger id must not create duplicate mission runs
- the same source event id must not create duplicate mission events
- the same model output id must not create duplicate journal entries
- mission events are append-only
- derived read models can be regenerated from mission records
- canceled or failed missions remain inspectable

Fixture replay should prove that duplicate input does not create duplicate
mission runs, agent runs, events, findings, stumbles, artifacts, journals,
memory entries, or review signals.

## Freshness And Governance

Mission runs and read models must carry freshness metadata.

Before any high-impact or external action, the committer or agent runtime approval layer
must check:

- whether the mission context package is stale
- whether protected state changed after package creation
- whether governance policy changed after package creation
- whether approval state changed after package creation
- whether unresolved evidence remains

If any check fails, the action should become `requires_refresh`,
`pending_approval`, or `rejected`. Code enforces this boundary without deciding
whether the proposed action is strategically good.

## Acceptance Gates

The first implementation is ready when:

- mission schemas validate
- repo-audit fixture files validate
- fixture replay creates the expected mission, agent, event, finding, stumble,
  artifact, governance, commit, journal, memory, and review-signal records
- replaying the same fixture is idempotent
- mission read model can be regenerated from records
- no agent-runtime-specific names are required by generic schemas
- agent-runtime-specific fixture data is isolated to examples or adapters
- every finding, journal, memory entry, and approval references evidence
- stumbles can produce memory proposals without automatically promoting them to
  shared state
- external or high-risk actions are blocked or held pending approval when
  governance requires it
- routing and packaging remain explicit and auditable

## Implementation Sequence

1. Add mission JSON schemas.
2. Add deterministic repo-audit fixture examples.
3. Add schema validation and fixture consistency checks.
4. Add file-backed mission stores.
5. Add fixture replay for mission creation and event ingestion.
6. Add mission read model generation.
7. Connect mission findings and stumbles to existing model proposal and commit
   result flows.
8. Add agent-runtime/Speedrift adapter design after the generic fixture passes.
9. Build agent runtime shell Mission Control against the read model.

## Design Decisions For First Implementation

These decisions are fixed for the first implementation plan:

1. `MissionEvent` is its own schema. It may reference `SourceEvent` records, but
   it is not a source-system envelope. Its job is mission timeline replay.
2. Token and cost accounting live on `MissionAgentRun`. A future adapter may add
   per-event usage details, but the first read model uses agent-run totals.
3. Findings and stumbles are first-class top-level records. Matching mission
   events point to them by ref so the timeline and summary views share the same
   underlying records.
4. The first read model is generated by a State System CLI command from
   file-backed records. A small API adapter can follow after fixture replay is
   stable.
5. Workgraph follow-up refs enter the mission through model action proposals
   first. Speedrift may create guarded follow-up tasks through its existing
   path, then report the resulting Workgraph task refs back into the mission as
   events and review-signal refs.

## Recommendation

Implement first-class mission schemas in State System and keep them generic.
Use a deterministic agent-runtime/Speedrift repo-audit fixture as the first pressure
test. Build agent runtime shell Mission Control only after the read model can be
generated from durable mission records.

This preserves State System as the reusable substrate while still creating a
direct path to a live multi-agent operator surface.
