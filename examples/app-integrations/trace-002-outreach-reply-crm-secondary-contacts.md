# Trace 002: Outreach Reply To CRM And Secondary Contacts

**Pressure test:** real reply creates a CRM handoff, secondary contact proposals,
and retained engagement intelligence.

## Scenario

A prospect sends a substantive reply and CCs two colleagues. Outreach Engine
must recognize the reply as a real engagement, propose a CRM handoff, retain the
engagement intelligence, and send the new contacts back to Prospect Researcher.

## Artifact Chain

```text
source event:
  outreach.source.email-reply.002

context package:
  context.outreach-engagement-package.002

model proposal output:
  model.outreach-reply-routing.002

governance / approval:
  governance.human-review.crm-handoff.002

commit result:
  commit.outreach-reply-crm-secondary-contacts.002

downstream artifacts:
  crm.relationship-update.002
  prospect.secondary-contact-candidates.002
  outreach.engagement-intelligence.002

conformance note:
  conformance.no-regex-reply-routing.002
```

## What Must Be Proven

- Real reply classification is a model interpretation over evidence, not a
  deterministic positive/negative parser.
- CC'd people are retained as relationship evidence even if they are not
  immediately actioned.
- CRM receives a handoff proposal and approved relationship update, not a silent
  direct mutation.
- Prospect Researcher receives secondary contacts with provenance and routing
  cues.
- Outreach Engine keeps the engagement intelligence for future campaign and
  doctrine learning.
- Human approval and later qualitative judgment are available to the learning
  loop.

## Failure Conditions

- Out-of-office, emergency-routing, and real-engagement messages are handled by
  fixed keyword lists.
- CC'd contacts are dropped or stored only in Outreach Engine.
- CRM handoff success is not represented as a measurable commit result.
- Relationship learning becomes a hidden code path instead of accepted doctrine.
