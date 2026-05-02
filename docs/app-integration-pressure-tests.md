# Application Integration Pressure Tests

**Status:** Planning contract  
**Scope:** State System, Prospect Researcher, Outreach Engine, Meeting Manager, Thoughtforge, Visual Forge, LFW AI Graph CRM, PAIA memory, Folio, and task/work systems

## Purpose

These pressure tests keep the new application repos from becoming disconnected apps with local state, hidden heuristics, and brittle handoffs.

Every app plan should include at least one pressure test from this document. Any integration that cannot pass with fixtures should not move to implementation.

## Pass Criteria

An integration is ready for implementation when it can answer:

1. What source evidence triggered the app workflow?
2. Which bounded context package did the model receive?
3. What did the model interpret, and what uncertainty did it preserve?
4. What did the app propose rather than directly mutate?
5. Which governance policy determined approval, rejection, or direct acceptance?
6. What commit result proves what changed?
7. Which downstream app receives the accepted state or context?
8. How does the next app avoid hidden heuristics, regexes, thresholds, or local scoring?
9. How does human qualitative judgment become model-interpretable evidence?
10. How is rollback, correction, or later disagreement represented?

## Scenario 1: Prospect Package Becomes Outreach Candidate

**Trigger:** Prospect Researcher identifies an account/person/opportunity combination with credible campaign fit.

**Expected path:**

```text
external/source evidence
  -> prospect_opportunity_package
  -> model proposal: qualified candidate or needs more evidence
  -> human review at first
  -> accepted contact/campaign/prospect state
  -> Outreach Engine receives qualified package
```

**Pressure risks:**

- Prospect Researcher uses hidden BANT weights or keyword rules.
- Outreach Engine receives a lead without evidence or uncertainty.
- Contact identity fragments between Prospect Researcher and CRM.

**Pass condition:** the package includes evidence refs, Opportunity Fit Probability as model interpretation, missing evidence, contact refs, and a commit result that makes the handoff visible.

## Scenario 2: Outreach Reply Produces CRM Handoff And New Contacts

**Trigger:** a prospect sends a real reply and CCs two colleagues.

**Expected path:**

```text
email source event
  -> outreach_engagement_package
  -> model interprets reply, CCs, routing cues, and relationship significance
  -> human approves qualified CRM handoff at first
  -> CRM receives relationship update
  -> Prospect Researcher receives secondary contacts
  -> Outreach Engine retains engagement intelligence
```

**Pressure risks:**

- Regex classifies replies as positive/negative.
- CCs are dropped because they are not the original prospect.
- CRM is mutated before handoff approval.
- Prospect Researcher never learns from reply-derived contacts.

**Pass condition:** real engagement, secondary contacts, routing cues, CRM handoff, and prospect-research updates are separate proposals with shared evidence refs.

## Scenario 3: Meeting Creates Cross-App Coordination Updates

**Trigger:** a meeting transcript includes a follow-up commitment, a referral, and a promising essay idea.

**Expected path:**

```text
meeting transcript / notes / artifacts
  -> meeting_context_package and coordination_update_package
  -> model proposes task, CRM update, Prospect Researcher signal, Thoughtforge idea
  -> human reviews sensitive transitions
  -> accepted updates route to the right systems
```

**Pressure risks:**

- Action-item keyword extraction silently creates tasks.
- Relationship interpretation is written to CRM without approval.
- Thoughtforge receives a source-free idea.
- Prospect Researcher receives a referral without contact provenance.

**Pass condition:** each proposed downstream update has evidence refs, uncertainty, approval status, and a commit result.

## Scenario 4: Thoughtforge Uses Meeting-Derived Idea Without Losing Provenance

**Trigger:** Meeting Manager sends a meeting-derived idea candidate to Thoughtforge.

**Expected path:**

```text
coordination update accepted
  -> thoughtforge_author_package
  -> model decides whether idea fits Braydon/DBMCCO or Sam Ashford corpus
  -> interview prompt or longform candidate proposal
  -> human approval before public publication
  -> published corpus update after release
```

**Pressure risks:**

- The idea is assigned to the wrong author by hardcoded topic matching.
- Published claims are created without transcript/note evidence.
- Short-form promotion becomes the product instead of longform thought.

**Pass condition:** author fit, idea maturity, and editorial direction are model interpretations with source refs and human approval gates.

## Scenario 5: Visual Forge Learns From Qualitative Creative Judgment

**Trigger:** a human reviews a generated campaign visual and says, "This matches the brand but not the campaign; keep the texture from version two."

**Expected path:**

```text
review artifact
  -> visual_forge_workspace_package
  -> model interprets qualitative judgment
  -> revision proposal and corpus memory proposal
  -> accepted finished asset or revised candidate
  -> approved corpus update if human promotes it
```

**Pressure risks:**

- Feedback becomes a numeric style score.
- Prompt rewriting is hidden and untraceable.
- Rejected assets are discarded instead of retained as informative private corpus.

**Pass condition:** qualitative feedback is preserved, model interpretation is visible, and corpus updates distinguish private from approved visual material.

## Scenario 6: CRM Relationship Outcome Feeds Prospect And Outreach Doctrine

**Trigger:** CRM shows that a prior handoff became a valuable relationship, but only after a referral path emerged.

**Expected path:**

```text
CRM relationship outcome
  -> source event
  -> context packages for Prospect Researcher and Outreach Engine
  -> model proposes campaign/contact/outreach learning
  -> human approves doctrine at first
  -> accepted doctrine updates future context packages
```

**Pressure risks:**

- CRM outcome is treated as a sales score instead of relationship evidence.
- Prospect Researcher hardcodes referral preference.
- Outreach Engine changes tone/sequence behavior in code.

**Pass condition:** the learning is represented as accepted state/doctrine with evidence refs, not as app-local deterministic behavior.

## Scenario 7: Conflicting App Interpretations

**Trigger:** Outreach Engine sees a reply as promising. CRM history shows the relationship is sensitive. Prospect Researcher sees weak opportunity fit.

**Expected path:**

```text
multiple state refs
  -> shared context package
  -> model preserves disagreement
  -> governance blocks or escalates sensitive action
  -> human judgment resolves next step
  -> commit result records accepted path and unresolved tension
```

**Pressure risks:**

- One app overwrites another app's interpretation.
- Governance treats all positive replies as safe.
- The system hides uncertainty to keep the workflow moving.

**Pass condition:** disagreement remains visible through uncertainty, review signal, or pending approval; no app silently wins by writing first.

## Scenario 8: Package Staleness Before External Action

**Trigger:** an app builds a package, but relationship privacy or campaign state changes before the proposed external action is reviewed.

**Expected path:**

```text
stale context package
  -> freshness check
  -> model or committer requests refresh
  -> external action blocked until package is current
```

**Pressure risks:**

- Apps act from stale context.
- Approval is treated as valid after protected state changes.
- Package freshness is not visible to the human reviewer.

**Pass condition:** freshness watermarks or stale refs block or downgrade external action proposals.

## Scenario 9: App Local Store Drift

**Trigger:** an app stores its own contact, author, visual, or campaign state and diverges from State System.

**Expected path:**

```text
local app state
  -> source event or state sync
  -> state-system reconciliation proposal
  -> accepted shared state or explicit deviation
```

**Pressure risks:**

- Apps become source-of-truth islands.
- Cross-app references break.
- The same person, campaign, author idea, or visual asset has conflicting ids.

**Pass condition:** app-local state is either execution-local/cache state or reconciled through shared state with cross-app refs.

## Scenario 10: Model-Mediation Drift During Build

**Trigger:** implementation adds regexes, thresholds, category maps, or hidden scores for a judgment-heavy path.

**Expected path:**

```text
drift finding
  -> model agency violation review
  -> remove heuristic or log explicit deviation
  -> add conformance fixture
```

**Pressure risks:**

- The app appears to work but judgment has moved into code.
- Human qualitative feedback is no longer visible to models.
- Accepted doctrine is encoded as code, not state.

**Pass condition:** model-owned decisions remain in model proposal/approval flow, or the deviation is explicit, scoped, owned, and revisitable.

## Required Fixture Set

Before any app implementation plan is accepted, create fixture traces for:

1. Prospect Opportunity Package -> Outreach Engine candidate.
2. Outreach engagement reply -> CRM handoff plus secondary contacts.
3. Meeting transcript -> task/CRM/prospect/Thoughtforge proposals.
4. Thoughtforge idea candidate -> author-specific interview or longform plan.
5. Visual Forge qualitative review -> revised asset and corpus memory.
6. CRM outcome -> Prospect/Outreach doctrine proposal.
7. Conflicting interpretations -> pending approval or blocked action.
8. Stale package -> refresh request before external action.

Each fixture trace should include:

- source event
- context package
- model proposal output
- governance policy or approval reason
- commit result
- downstream app-visible artifact
- conformance note for hidden heuristics/rules/scoring

Initial trace anchors live in `examples/app-integrations/`. Convert each anchor
into schema-valid JSON artifacts before the corresponding app implementation
slice begins.

## Implementation Rule

Integration pressure tests are design gates. Passing one with prose is not enough; it needs fixture artifacts before implementation.
