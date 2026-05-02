# Trace 001: Prospect Package To Outreach Candidate

**Pressure test:** Prospect Opportunity Package becomes Outreach Engine
candidate.

## Scenario

Prospect Researcher identifies an account/person/opportunity combination that
appears aligned to an active campaign. Outreach Engine should receive a qualified
package only after the fit, evidence, uncertainty, and contact refs are visible.

## Artifact Chain

```text
source event:
  prospect.source.campaign-research.001

context package:
  context.prospect-opportunity-package.001

model proposal output:
  model.prospect-opportunity-to-outreach.001

governance / approval:
  governance.human-review.external-outreach.001

commit result:
  commit.prospect-to-outreach-candidate.001

downstream artifact:
  outreach.candidate-package.001

conformance note:
  conformance.no-hidden-fit-scoring.001
```

## What Must Be Proven

- The campaign goal and ICP come from shared company/campaign state, not app
  local prompt text.
- Opportunity Fit Probability is a model interpretation with evidence and
  uncertainty, not a BANT score or threshold.
- Contact identity uses shared contact refs that CRM can reconcile later.
- Outreach Engine receives a package that includes why the prospect is suitable,
  what is missing, what cannot be claimed, and what needs human review before
  sending.
- Accepted doctrine is represented as state, not code changes in either app.

## Failure Conditions

- Prospect Researcher emits a lead with no evidence refs.
- Outreach Engine recomputes fit using hidden rules.
- Contact ids differ across Prospect Researcher, Outreach Engine, and CRM.
- Human approval happens outside the trace and cannot be learned from.
