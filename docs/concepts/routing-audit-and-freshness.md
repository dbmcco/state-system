# Routing Audit And Freshness

Recent-change routing and context packaging introduce two new risks:

1. routing can hide important changes
2. context packages can become stale

This document defines the first audit and freshness rules for the local harness.

## Routing Audit

Routing is allowed to narrow an agent's attention. It is not allowed to become
hidden business judgment.

Every recent-change entry should record routing decisions for relevant personas:

- `persona_ref`
- `relevance_tier`
- `routing_reason`
- `included`
- optional opportunity class hints
- optional excluded-context summary

The first relevance tiers are:

- `primary`
- `secondary`
- `escalated`
- `ambient`
- `excluded`

## Routing Rules

Code may route by explicit metadata:

- persona watched domains
- affected state refs
- state families and traits
- source refs
- source system and event type
- parent/child state refs
- governance scope
- recency window
- explicit human or agent escalation

Code should not route by hidden conclusions such as:

- this deal is post-worthy
- this feature is marketable
- this client should be named
- this project is healthy

Those are model decisions.

## Excluded Context

When context is excluded from a package, the package should say so.

Example:

```text
Delivery handoff details were excluded from Maya's package. Alex owns
operational follow-up unless the detail becomes campaign, proof, launch, or
relationship-message relevant.
```

This lets humans and supervisor agents audit routing without forcing every
agent to read every source record.

## Ambient Review

The system should preserve broad ambient review.

An agent's default package can exclude low-relevance changes, but a human,
supervisor agent, or scheduled audit should be able to query ambient and
excluded entries to find routing misses.

## Freshness

Recent-change entries and context packages should carry freshness metadata.

Minimum fields:

- `watermark_refs`
- `stale_after` or `valid_until`
- `requires_refresh_before_external_action`
- `stale_if_refs_change`

Freshness does not mean the package is unusable after expiration. It means the
model or committer should treat the package as needing refresh before
high-impact or external action.

Agent activations should copy the package freshness metadata and stamp whether
the package was stale at activation time. Reports should make the validity
window, stale status, refresh requirement, and prohibited external actions
visible so the downstream agent does not confuse a stale context package with
permission to act externally.

## External Action Rule

Before external action, the committer should check:

- whether the package requires refresh before external action
- whether protected state changed after package creation
- whether governance policy changed after package creation
- whether approval state changed after package creation
- whether unresolved evidence remains

If any check fails, the action should become pending approval, rejected, or a
refresh request.

## First Fixture

The Southern Abrasives fixture exercises these rules:

- Linear deal moved to won
- recent-change entry routes to Alex as `primary`
- recent-change entry routes to Maya as `secondary`
- Maya context package excludes operational handoff detail
- Maya can draft internal material
- external LinkedIn publication stays pending approval
- package requires refresh before external action
- stale activation surfaces the expired validity window before external action
