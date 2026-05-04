# App Integration Fixture Traces

These fixtures pressure test handoffs between the new application repos before
implementation begins.

Each trace is backed by schema-valid JSON artifacts once it becomes an
implementation gate. Prose anchors can still be used for later scenarios, but
the first five traces now have concrete source events, context packages, model
outputs, commit results, downstream app artifacts, and conformance notes.

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
3. Meeting coordination fixture chain - meeting-derived commitment, referral,
   and essay idea become task/work, CRM, Prospect Researcher, and Thoughtforge
   artifacts without keyword extraction or source-free ideas.
4. Thoughtforge provenance fixture chain - meeting-derived idea candidate
   becomes an interview prompt and longform candidate without hardcoded author
   assignment or source-free publication.
5. Visual Forge qualitative learning fixture chain - human creative feedback
   becomes revision and corpus-memory candidates without style scores or hidden
   prompt rewrites.

These traces are the first build gate because Prospect Researcher, Outreach
Engine, Meeting Manager, Thoughtforge, work/task systems, and LFW AI Graph CRM
share the same contact, campaign, relationship, content, and doctrine spine.

Schema-valid fixture chains:

- `source-prospect-campaign-research-001.json` ->
  `prospect-opportunity-context-package-001.json` ->
  `prospect-to-outreach-model-proposal-output-001.json` ->
  `prospect-to-outreach-commit-result-001.json` ->
  `outreach-candidate-package-001.json` ->
  `conformance-no-hidden-fit-scoring-001.json`
- `source-outreach-email-reply-002.json` ->
  `outreach-engagement-context-package-002.json` ->
  `outreach-reply-routing-model-proposal-output-002.json` ->
  `outreach-reply-crm-secondary-contacts-commit-result-002.json` ->
  `crm-relationship-update-002.json`,
  `prospect-secondary-contact-candidates-002.json`,
  `outreach-engagement-intelligence-002.json` ->
  `conformance-no-regex-reply-routing-002.json`
- `source-meeting-coordination-003.json` ->
  `meeting-coordination-context-package-003.json` ->
  `meeting-coordination-model-proposal-output-003.json` ->
  `meeting-coordination-commit-result-003.json` ->
  `work-follow-up-task-package-003.json`,
  `crm-referral-update-003.json`,
  `prospect-referral-signal-003.json`,
  `thoughtforge-idea-candidate-003.json` ->
  `conformance-no-keyword-extraction-source-free-ideas-003.json`
- `source-thoughtforge-meeting-idea-004.json` ->
  `thoughtforge-author-context-package-004.json` ->
  `thoughtforge-meeting-idea-model-proposal-output-004.json` ->
  `thoughtforge-meeting-idea-commit-result-004.json` ->
  `thoughtforge-interview-prompt-candidate-004.json`,
  `thoughtforge-longform-candidate-004.json` ->
  `conformance-no-hardcoded-author-source-free-publication-004.json`
- `source-visual-forge-creative-review-005.json` ->
  `visual-forge-workspace-context-package-005.json` ->
  `visual-forge-creative-review-model-proposal-output-005.json` ->
  `visual-forge-creative-review-commit-result-005.json` ->
  `visual-forge-revision-candidate-005.json`,
  `visual-forge-corpus-memory-candidate-005.json` ->
  `conformance-no-style-score-hidden-prompt-rewrite-005.json`
