# App Integration Fixture Traces

These fixtures pressure test handoffs between the new application repos before
implementation begins.

Each trace should eventually be backed by schema-valid JSON artifacts. The first
version may start as a trace anchor, but it must name the artifacts that will be
created and the integration risks it is testing.

Required artifact chain:

```text
source event
  -> app context package
  -> model proposal output
  -> governance policy or approval reason
  -> commit result
  -> downstream app-visible artifact
  -> conformance note
```

## Initial Trace Set

1. `trace-001-prospect-to-outreach.md` - Prospect Opportunity Package becomes
   an Outreach Engine candidate.
2. `trace-002-outreach-reply-crm-secondary-contacts.md` - real outreach reply
   produces a CRM handoff, secondary contact proposals, and retained engagement
   intelligence.

These two traces are the first build gate because Prospect Researcher, Outreach
Engine, and LFW AI Graph CRM share the same contact, campaign, relationship,
and doctrine spine.
