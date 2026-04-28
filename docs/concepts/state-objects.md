# State Objects

A state object is a scoped current-state view for a work entity.

It should be small enough to read quickly and specific enough to act on.

## Examples

- `project`
- `deal`
- `client`
- `relationship`
- `campaign`
- `meeting`
- `obligation`
- `person`
- `organization`
- `agent`
- `operating_picture`

## Required Shape

Each state object needs:

- stable id
- type
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

