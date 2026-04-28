# State Objects

A state object is a scoped current-state view for an organizational, operating,
work, relationship, knowledge, role, onboarding, or governance entity.

It should be small enough to read quickly and specific enough to act on.

## Type Versus Family

`type` describes what the object is. `primary_family` describes where it belongs
in the ontology.

For example, a campaign has `type: campaign` and usually
`primary_family: work`. It may also have secondary families such as
`relationship`, `knowledge`, or `organizational_identity` when it carries
audience, insight, or narrative implications.

This prevents the ontology from becoming a brittle inheritance tree. One state
object has one primary home, but it can participate in several rollups.

## Common Types

- `project`
- `deal`
- `client`
- `relationship`
- `campaign`
- `meeting`
- `obligation`
- `person`
- `organization`
- `mission`
- `strategy`
- `principle`
- `role`
- `onboarding`
- `norm`
- `decision_area`
- `capability`
- `agent`
- `operating_picture`

## State Families

- `organizational_identity`
- `operating`
- `work`
- `relationship`
- `knowledge`
- `role_and_persona`
- `onboarding`
- `governance`

## State Traits

`state_traits` describe how the object changes over time.

- `slow_changing`: mission, principles, durable strategy
- `dynamic`: campaigns, deals, risks, active priorities
- `developmental`: onboarding and role ramp state
- `rollup`: synthesized operating pictures

Traits should guide update cadence and review policy. They should not replace
model judgment about what changed or what matters.

## Required Shape

Each state object needs:

- stable id
- type
- primary family
- secondary families
- state traits
- scope
- owner or responsible actor
- current summary
- active situations
- goals
- blockers
- open questions
- next actions
- evidence references
- parent and child state references
- latest journal reference

## Principle

Each state object owns its local truth. Rollups synthesize state across objects,
but they do not replace the child objects.

## Model-Mediated Update Rule

Code should gather factual inputs and expose update tools. The model should
decide what changed, which family relationships matter, what is uncertain, and
whether a proposed update is worth recording.

The schema should make those decisions explicit after they are made; it should
not hide them inside prompt prose.
