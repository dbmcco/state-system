# Governance Policy

Governance policy is durable state about what the system may commit, execute,
publish, promote, or require approval for.

Governance does not replace model judgment. It constrains what can become
durable state or external action after the model has made a proposal.

## Policy Purpose

A governance policy should answer:

- what action or state transition is controlled?
- who or what is allowed to perform it?
- when is approval required?
- who can approve it?
- what evidence is required?
- what risk class applies?
- what happens when the policy blocks a proposal?

## Policy Scope

Policies may apply to:

- state writes
- memory writes
- memory promotion
- external communication
- protected mission or strategy changes
- relationship-sensitive claims
- tool or capability execution
- publication

## First Policy Shape

The draft schema is `schemas/governance-policy.schema.json`.

The schema is intentionally simple:

- id
- scope
- applies_to
- controlled_action
- risk
- approval
- allowed_actor_refs
- approver_refs
- evidence_requirements
- blocked_effect

The committer can evaluate this without deciding whether the underlying proposal
is strategically good.

## Maya External Copy Policy

The first pressure-test policy is:

- Maya may draft internal campaign recommendations.
- Maya may propose external copy.
- Maya may not publish external-facing copy without approval.

The fixture is `examples/governance-external-copy-policy.json`.

Pressure-test result:

- `examples/maya-pending-approval-commit-result.json` should cite the same
  approval reason captured by this policy.
- The action is pending, not executed.
- No snapshot or memory entry is mutated while approval is pending.

## Policy As State

Governance policies should eventually be represented as Governance State, not
buried in code conditionals.

Code enforces the policy, but policy content should be inspectable, journaled,
and reviewable.
