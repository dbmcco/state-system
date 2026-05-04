# Model-Mediated Drift Pressure Suite

**Status:** active fixture gate

## Purpose

This suite protects State System from a specific failure mode: an app appears to
work because deterministic code silently takes over model-owned judgment.

The system can use deterministic code for parsing, validation, identity lookup,
schema checks, replay ordering, idempotency, rendering, and mechanical routing.
It should not use deterministic code to decide qualitative salience, business
meaning, relationship significance, audience fit, urgency, tone, or readiness
unless that exception is explicit, approved, scoped, and revisitable.

## Model-Owned Judgment

Model-owned judgment is interpretation over evidence where meaning is uncertain
or contextual. Examples include:

- whether a prospect is a credible outreach candidate
- whether an email reply is commercially meaningful
- whether a copied contact is relationship evidence
- whether a proposed external action is ready for review
- whether human feedback should become reusable doctrine

These judgments belong in model proposal outputs, review packets, conformance
notes, and accepted state. They should preserve uncertainty, evidence refs,
approval requirements, and the reason the judgment matters.

## Deterministic Code Boundary

Deterministic code may move and verify records. It may not hide the judgment
inside fields such as scores, thresholds, regex matches, keyword rules, or
category maps that become the real decision maker.

Allowed deterministic work:

- validate schema shape and required fields
- check evidence refs resolve to known examples
- replay records in a stable order
- render reports from already accepted artifacts
- block an action when an explicit governance policy requires it

Disallowed hidden judgment:

- hidden scoring for prospect fit, campaign fit, tone, or priority
- regex routing that decides whether a reply is positive or important
- thresholds that replace model explanation of readiness or salience
- keyword rules that assign author, audience, relationship, or task meaning
- app-local state mutation that bypasses State System proposals and commits

## Approved Deviation

An approved deviation is the only acceptable way for deterministic code to take
over a judgment-heavy path. The deviation must name:

- the exact judgment being moved into deterministic code
- why model mediation is not appropriate for that judgment
- the owner and review date
- the evidence that justified the exception
- the rollback path if the deterministic behavior proves brittle

Without an approved deviation, deterministic shortcuts should be treated as
model-mediated drift.

## Pressure-Suite Rule

Every app-integration fixture chain must make the model-mediated boundary
visible in three places:

1. The model output names the interpretation and the deterministic drift risk it
   avoids.
2. The conformance note lists model-owned judgments and has no deterministic
   judgment rules.
3. The downstream artifact carries accepted state or context; it does not add
   app-local hidden scoring, regex routing, thresholds, or keyword rules.

The suite should fail when a future fixture collapses qualitative judgment into
an app-local field that looks convenient but becomes the decision owner.
