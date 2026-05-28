# LightForge Works Ontology Pressure Test

This document pressure-tests the generic State System ontology using
LightForge Works as a concrete example.

This is example material, not canonical State System ontology. The goal is to
see where the ontology feels natural, where it duplicates concepts, and where it
needs new state families or sharper boundaries.

## Source Material

Primary LFW sources inspected:

- `/path/to/acme-operations/CLAUDE.md`
- `/path/to/acme-operations/lfw-process/README.md`
- `/path/to/acme-operations/lfw-process/pipeline/current-delivery-model.md`
- `/path/to/acme-operations/lfw-process/pipeline/ops-manager-operating-model.md`
- `/path/to/acme-operations/lfw-process/pipeline/shy-role-and-focus.md`
- `/path/to/acme-operations/lfw-process/positioning/category-pov.md`
- `/path/to/acme-operations/lfw-process/positioning/2026-03-09-the-model-is-not-the-product.md`
- `/path/to/acme-operations/lfw-process/methodologies/prism-framework.md`
- `/path/to/acme-operations/lfw-process/methodologies/requirements-clarity.md`
- `/path/to/acme-operations/lfw-salesforge/CLAUDE.md`
- `/path/to/acme-operations/lfw-salesforge/PROJECT_STATUS_SUMMARY.md`

## Thin Vertical Slice

```text
LFW Mission State
  -> LFW Strategy State
  -> LFW Operating Principles / Norms
  -> LFW Role State
  -> LFW Persona State: Laura
  -> LFW Onboarding State: Shy / agent onboarding
  -> LFW Work State: SalesForge and marketing campaigns
  -> LFW Operating Picture
```

## 1. Mission State

**State family:** Organizational Identity State

**Candidate state object:** `state.lfw.mission`

**Working interpretation:**
LightForge Works exists to build focused, single-purpose back-office business
applications for mid-market clients, using LLM-era development abundance to
deliver practical business capabilities with clear boundaries, fast timelines,
and measurable ROI.

**Evidence refs:**

- `lfw/CLAUDE.md`: LFW is a micro-application development business building
  single-purpose, back-office business applications for mid-market clients.
- `lfw-process/positioning/category-pov.md`: LLM-ready microapplication
  development converts development abundance into predictable ROI.
- `lfw-process/pipeline/current-delivery-model.md`: 4 discovery sessions, 1
  signed scope, 30 days to working software.

**Uncertainty:**

- Whether the mission should emphasize "microapplications," "single-purpose
  applications," "configured AI capabilities," or "back-office workflow
  transformation" as the primary public language.
- Whether partner/channel growth is central to mission or a strategy layer.

**Ontology note:**
Mission state is not just marketing copy. It should constrain strategy, roles,
work selection, persona behavior, and onboarding.

## 2. Strategy State

**State family:** Organizational Identity State and Operating State

**Candidate state object:** `state.lfw.strategy`

**Working interpretation:**
LFW's current strategy centers on predictable, scope-controlled SPA delivery:
free structured discovery, SOW and mockups before signing, 30-day build,
$2,500/month per application, portfolio growth through repeatable modules,
partner channels, and AI-assisted business development.

**Evidence refs:**

- `lfw-process/pipeline/current-delivery-model.md`: delivery model and pricing.
- `lfw/CLAUDE.md`: $2,500/month app model, 1 hr/week support, $10K rebuild
  cycle, module library, active client prototypes.
- `lfw-salesforge/PROJECT_STATUS_SUMMARY.md`: SalesForge strategy to scale from
  1,100 to 10,000+ qualified prospects and generate 150-200 qualified leads per
  month.

**Open questions:**

- Is SalesForge a core strategy or one strategic bet?
- Does the module library represent internal operating leverage, public product
  strategy, or both?
- Which active client segments matter most now: manufacturing, professional
  services, healthcare, legal, financial services, or partner-led verticals?

**Ontology note:**
Strategy state crosses identity and operating state. It is slower than a weekly
operating picture but faster than mission.

## 3. Operating Principles And Norms

**State family:** Organizational Identity State and Governance State

**Candidate state objects:**

- `state.lfw.principle.boundaries-before-features`
- `state.lfw.principle.roi-in-weeks`
- `state.lfw.norm.linear-github-drive`
- `state.lfw.norm.just-enough-requirements`

**Working interpretation:**
LFW's operating principles include:

- single-purpose focus
- boundaries before features
- ROI discipline
- just-enough requirements for LLMs
- client sees scope and mockups before signing
- Linear tracks operational work
- GitHub/Git hold source and repeatable artifacts
- Drive holds signed, exported, and externally shared documents

**Evidence refs:**

- `lfw-process/positioning/category-pov.md`: principles such as "do one thing
  right," "boundaries before features," "measure in weeks, decide in days," and
  "sequence for compounding ROI."
- `lfw-process/methodologies/requirements-clarity.md`: requirements clarity
  dimensions and assessment framework.
- `lfw-process/pipeline/ops-manager-operating-model.md`: system-of-record rules
  for Linear, Git, and Drive.

**Ontology note:**
Principles and norms are distinct. Principles shape judgment; norms shape
routine behavior. Both need state because they can become stale or violated.

## 4. Role State

**State family:** Role And Persona State

**Candidate state object:** `state.lfw.role.ops-manager`

**Working interpretation:**
The operations manager role exists to centralize operational discipline around
contracts, project tracking, sales follow-up, finance admin, and document
control without owning founder-level selling, legal approval, or technical
delivery.

**Evidence refs:**

- `lfw-process/pipeline/ops-manager-operating-model.md`
- `lfw-process/pipeline/shy-role-and-focus.md`

**Role boundaries:**

- Owns maintenance of operational systems and follow-through.
- Supports sales and delivery without owning sales strategy or technical
  delivery decisions.
- Escalates missing owners, stale records, blocked contracts, and unclear next
  steps.

**Ontology note:**
Role state is more durable than onboarding state. Onboarding state should point
to role state as its target.

## 5. Persona State: Laura

**State family:** Role And Persona State

**Candidate state object:** `state.lfw.persona.laura`

**Working interpretation:**
Laura is a marketing agent persona. In an LFW setting, Laura should maintain and
interpret marketing narrative, campaign state, audience fit, proof points,
positioning clarity, and mission alignment.

**Watched state domains:**

- mission
- strategy
- organizational narrative
- market beliefs
- campaign state
- relationship/account state
- SalesForge work state

**Facet implications:**

- If a campaign conflicts with LFW's category POV, Laura should flag the tension.
- If messaging is polished but not tied to ROI or boundaries, Laura should call
  that out.
- If SalesForge emphasizes scale at the expense of quality or fit, Laura should
  surface the strategic risk.

**Ontology note:**
Persona state references role state, mission state, governance state, and watched
domains. It should not be reduced to prompt prose.

## 6. Onboarding State

**State family:** Onboarding State

**Candidate state objects:**

- `state.lfw.onboarding.human.shy`
- `state.lfw.onboarding.agent.laura`

**Working interpretation:**
Human onboarding should track what a person understands about the mission,
roles, systems, norms, active records, and next actions. Agent onboarding should
track the same shape, plus tool access, capability checks, authority boundaries,
and persona readiness.

**Evidence refs:**

- `lfw-process/pipeline/shy-role-and-focus.md`
- `lfw-process/pipeline/ops-manager-operating-model.md`
- `lfw-process/pipeline/team-collaboration-onboarding.md`
- `lfw-process/pipeline/agent-collaboration-setup.md`

**Open questions:**

- Should human onboarding and agent onboarding share one schema with different
  readiness checks?
- What is the first "ready" state for Laura: can read mission/strategy, can
  review campaign state, can append journal entries, or can propose actions?

**Ontology note:**
Onboarding state is developmental. It should include understanding, gaps,
capabilities, permissions, and next learning actions.

## 7. Work State: SalesForge

**State family:** Work State, Relationship State, Knowledge State, Operating State

**Candidate state object:** `state.lfw.work.salesforge`

**Working interpretation:**
SalesForge is LFW's AI-driven business development and scaled sales application.
It is intended to serve as a pre-pipeline engine feeding qualified leads into
Forgeworks, scaling from roughly 1,100 contacts to 10,000+ qualified prospects
and 150-200 qualified leads monthly.

**Evidence refs:**

- `lfw-salesforge/CLAUDE.md`
- `lfw-salesforge/PROJECT_STATUS_SUMMARY.md`

**State relationships:**

- depends on strategy state: growth through systematic AI-assisted BD
- depends on marketing state: content, audience, campaign quality
- depends on relationship state: prospect and account intelligence
- depends on governance state: prospect privacy, external messaging approval
- rolls into operating state: pipeline health and growth risk

**Ontology note:**
Real work objects often belong to multiple families. The base schema should
allow primary family plus secondary family refs or tags.

## 8. Operating Picture

**State family:** Operating State

**Candidate state object:** `state.lfw.operating_picture`

**Working interpretation:**
The operating picture should summarize active delivery, pipeline, contracts,
finance admin, relationship risk, client prototypes, marketing/growth work, and
system hygiene.

**Evidence refs:**

- `lfw/CLAUDE.md`: current initiatives and active directory structure.
- `lfw-process/pipeline/ops-manager-operating-model.md`: weekly ops summary and
  monthly housekeeping review.
- `lfw-process/pipeline/shy-role-and-focus.md`: visible active records and
  practical inspection questions.

**Rollup inputs:**

- active client project state
- active opportunity state
- contract state
- onboarding state
- SalesForge state
- mission/strategy tensions
- relationship risk

**Ontology note:**
Operating picture is a rollup state object. It should not become the canonical
home for details that belong in child states.

## Pressure-Test Findings

### Finding 1: Mission and strategy need first-class state.

The LFW example confirms that mission and strategy are not static preamble.
They actively constrain delivery model, marketing, persona behavior, onboarding,
and work selection.

### Finding 2: Roles and onboarding should be separate.

Shy's materials show the distinction clearly: the role is durable, while
onboarding is the developmental process of becoming effective in that role.

### Finding 3: Work state is often multi-family.

SalesForge is work state, but also strategy, marketing, relationship, knowledge,
and operating state. The ontology needs multiple refs instead of forcing a
single inheritance tree.

### Finding 4: Principles and norms both matter.

The LFW material contains high-level principles, such as boundaries before
features, and practical norms, such as Linear/Git/Drive source-of-truth rules.
Those should be related but distinct.

### Finding 5: Persona state should be evaluated against mission and strategy.

Laura is useful only if she can compare campaign and narrative state against
mission, strategy, principles, and market beliefs. Persona state must therefore
reference upstream organizational state.

## Ontology Adjustments Suggested

These should be considered for the generic ontology:

1. Add `primary_family` and `secondary_families` concepts to state objects.
2. Distinguish `principle` from `norm`.
3. Treat `operating_picture` as a rollup object, not a primary detail store.
4. Treat onboarding as developmental state with readiness signals.
5. Make mission and strategy valid parents of persona and work state.

