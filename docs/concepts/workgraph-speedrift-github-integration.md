# Workgraph, Speedrift, And GitHub Integration

State System should attach to the execution ecosystem without replacing it.

The right boundary is:

```text
Workgraph = execution state
Speedrift / Driftdriver = quality and drift judgment
GitHub = code, review, issue, release, and collaboration record
State System = durable interpreted organizational state and agent memory
```

State System should treat Workgraph, Speedrift, and GitHub as source systems.
It should reference their records as evidence, interpret durable meaning through
the model-mediated update layer, and only send work back through existing task,
directive, or approval interfaces.

## Why This Boundary Matters

Workgraph already owns task execution: tasks, dependencies, claims, assignment,
status, validation, dispatch, and completion.

Speedrift already owns quality judgment: drift findings, convergence pressure,
lane-specific checks, authority budgets, and follow-up task creation.

GitHub already owns collaboration artifacts around code: commits, branches,
pull requests, review comments, checks, issues, releases, and source history.

State System should not duplicate these systems. It should answer a different
question: what does this activity mean for the organization, the work, and the
agents operating inside it?

## Source Events Into State Triggers

Each source system can produce State System triggers.

### Workgraph

Useful Workgraph events include:

- task created
- task claimed
- task blocked
- task completed
- task rejected or reopened
- validation passed or failed
- agent assigned
- task aged or stalled
- dependency unblocked

These are execution facts. They are not automatically durable organizational
interpretation.

Example interpretation:

`wg done` means a task was marked complete. It does not automatically mean the
project is healthy, the milestone is ready, or the agent learned the right
lesson. State System can review the task, evidence, validation, and surrounding
state before proposing a project-state or agent-memory update.

### Speedrift / Driftdriver

Useful Speedrift events include:

- drift lane finding
- recurring finding pattern
- validation or quality gate result
- authority budget cap
- follow-up task recommendation
- ecosystem review finding
- prompt evolution signal
- convergence or scope-risk report

These are judgment facts. They should become evidence, not direct state
mutation.

Example interpretation:

A `specdrift` finding can trigger review of a project state object. The model
might conclude that the project has unresolved scope ambiguity, but the finding
itself is not the state object. The state update should cite the finding and
record uncertainty if the evidence is incomplete.

### GitHub

Useful GitHub events include:

- commit pushed
- branch created or deleted
- pull request opened, updated, merged, or closed
- review requested
- review approved or changes requested
- review comment added
- check suite passed or failed
- issue opened, updated, labeled, assigned, closed, or reopened
- release created
- deployment status changed

These are collaboration and code-history facts. They can be strong evidence,
but they still need interpretation.

Example interpretation:

A merged pull request may be evidence that implementation work landed. It does
not automatically mean the capability is operationally deployed, accepted by a
stakeholder, reflected in onboarding, or aligned with mission. State System can
use the PR, commits, checks, and linked Workgraph tasks as evidence for a
project-state update.

## GitHub Commits Versus Commitments

GitHub adds an important ambiguity: a commit is not always a commitment.

State System should distinguish:

- **code commits**: source-control facts, such as a SHA, author, branch, diff,
  and timestamp
- **review commitments**: promises or requirements captured in PR review,
  issue comments, requested changes, or approvals
- **delivery commitments**: claims that something will be shipped, fixed,
  supported, deployed, or handed off
- **governance commitments**: approvals, exceptions, policy decisions, or
  constraints recorded in issues, PRs, releases, or protected-branch workflows

The raw GitHub record belongs in the evidence layer. The interpreted commitment
belongs in state only after model review and governance checks.

Example:

```text
GitHub PR comment:
  "We will add audit logging before launch."

State System interpretation:
  obligation state: audit logging is a launch-blocking commitment
  evidence refs: PR comment, linked issue, Workgraph task
  uncertainty: owner and deadline may be unclear
  next action: create or link Workgraph task
```

## Attachment Pattern

The generic flow should be:

```text
source event
  -> State System trigger
  -> evidence refs back to source system
  -> model review packet
  -> model proposal output
  -> governance/committer
  -> state journal + memory + review signal
  -> optional proposed action back to Workgraph or GitHub
```

The direction matters. Source systems do not mutate State System snapshots
directly. They produce triggers and evidence. The model interprets meaning.
The committer enforces authority. Existing execution systems own any resulting
work.

## Proposed State Objects

These integrations imply several state objects the ontology already supports:

- `project`: current interpreted status of a repo, feature, milestone, or work
  stream
- `obligation`: delivery, review, launch, contract, or governance commitment
- `capability`: durable capability that may span tasks, code, docs, and runtime
- `decision_area`: unresolved product, architecture, governance, or delivery
  decision
- `operating_picture`: rollup of active work, risks, commitments, and follow-up
- `agent`: agent capability, learned pattern, or recurring behavior
- `onboarding`: human or agent readiness to operate inside the system

GitHub-specific examples:

- a PR can be evidence for a `project`, `capability`, or `obligation`
- a review comment can be evidence for an `obligation` or `decision_area`
- a failed check can be evidence for `project` risk or a Speedrift finding
- a release can be evidence for a `capability` becoming operational
- a repeated commit/revert pattern can become agent memory or project risk state

## Proposed Integration Interfaces

### Source Reference Shape

State System should use stable source refs rather than copying large blobs:

```text
github:repo:<owner>/<repo>
github:commit:<owner>/<repo>@<sha>
github:pr:<owner>/<repo>#<number>
github:pr-comment:<owner>/<repo>#<number>:<comment-id>
github:issue:<owner>/<repo>#<number>
github:check:<owner>/<repo>@<sha>:<check-run-id>
workgraph:repo:<repo-id>:task:<task-id>
speedrift:repo:<repo-id>:finding:<finding-id>
speedrift:repo:<repo-id>:review:<review-id>
```

The exact URI format can change later, but the principle should not: evidence
refs must preserve source, identity, and enough lookup information to resolve
the record.

### Trigger Sources

The current trigger schema has generic sources like `tool_result`,
`task_update`, and `agent_reasoning`. That is enough for early fixtures.

Later, we may want more specific source values or a nested source-system field:

```json
{
  "source": "tool_result",
  "source_system": "github",
  "source_event": "pull_request.merged"
}
```

Do not add those fields until the first harness shows the generic shape is too
weak.

## Agent Behavior Examples

Patrick can watch Workgraph, Speedrift, and GitHub for operational clarity:

- stale Workgraph tasks
- PRs merged without linked tasks
- review comments that imply obligations
- failed checks blocking delivery
- issues with no owner or next action
- Speedrift findings that recur across work streams

Laura can watch GitHub and Workgraph when technical delivery affects marketing:

- a capability merged but not yet externally describable
- release notes that imply market-facing claims
- PR evidence that supports a proof point
- issue or customer feedback that changes campaign readiness

Neither agent should directly mutate Workgraph or GitHub state. They should
propose actions through State System review signals or governed action proposals.

## First Implementation Implication

The first harness should not implement live GitHub, Workgraph, or Speedrift
adapters yet.

Instead, it should treat them as evidence-ref families in fixtures and ensure
the pipeline preserves provenance:

1. trigger carries source refs
2. review packet resolves or marks refs unresolved
3. model output cites refs in proposals
4. journal and memory entries preserve refs
5. commit result records accepted effects
6. optional action proposal names the target system

This lets us test the boundary before we bind to real APIs.

## Pressure-Test Scenario

A GitHub PR is merged for an LFW capability, but the PR review includes a
comment: "Add audit logging before launch."

Expected State System behavior:

- treat the merge as implementation evidence
- treat the review comment as a possible delivery obligation
- avoid marking the capability launch-ready until audit logging evidence exists
- create or link a Workgraph follow-up task
- update Patrick's operating picture if launch readiness changed
- possibly update agent memory if an agent repeatedly misses review commitments

This scenario would test the difference between code completion, delivery
commitment, launch readiness, and agent learning.

The first fixture version of this scenario lives in:

```text
examples/patrick-github-launch-readiness-trigger.json
  -> examples/patrick-github-launch-readiness-model-review-packet.json
  -> examples/patrick-github-launch-readiness-model-proposal-output.json
  -> examples/patrick-github-launch-readiness-commit-result.json
  -> examples/patrick-github-capability-journal-entry.json
  -> examples/patrick-github-obligation-journal-entry.json
  -> examples/patrick-github-launch-readiness-agent-memory-entry.json
  -> examples/patrick-github-launch-readiness-review-signal.json
```
