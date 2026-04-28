# Ontology

The State System ontology defines the major families of state an organization
needs to understand itself and its work.

Ontology comes before lifecycle and infrastructure. If the state families are
wrong, lifecycle machinery will encode the wrong assumptions.

## Top-Level State Families

### Organizational Identity State

Slow-changing state that defines what the organization is trying to become and
how it understands itself.

Examples:

- mission
- vision
- principles
- organizational narrative
- strategy
- values
- strategic tradeoffs

This state should change carefully and with explicit evidence or leadership
review. It influences many downstream states.

### Operating State

The current operating picture of the organization.

Examples:

- priorities
- risks
- capacity
- cadence
- active tensions
- current focus
- operating picture rollups

Operating state is more dynamic than identity state. It answers "what is going
on right now?"

### Work State

State for concrete work objects.

Examples:

- projects
- campaigns
- deals
- tasks
- obligations
- decisions
- deliverables
- milestones

Work state is where most daily activity lands, but it should still connect back
to identity, operating, relationship, and knowledge state.

### Relationship State

State about people and organizations the system needs to understand.

Examples:

- clients
- partners
- stakeholders
- accounts
- collaborators
- internal team members
- relationship health
- trust and communication context

Relationship state should distinguish evidence-backed facts from interpretations
such as "temperature seems colder" or "trust appears stronger."

### Knowledge State

State about what the organization believes or is learning.

Examples:

- market beliefs
- customer insights
- research findings
- assumptions
- open questions
- evidence quality
- confidence changes

Knowledge state is allowed to contain uncertainty. It should label confidence
and evidence clearly.

### Role And Persona State

State about how humans and agents participate in the organization.

Examples:

- human roles
- agent personas
- facets
- authority boundaries
- responsibilities
- watched domains
- communication posture
- anti-patterns

Personas are not only prompts. They are stateful interpretive lenses.

### Onboarding State

State about humans or agents becoming effective in a role.

Examples:

- human onboarding
- agent onboarding
- role ramp
- context acquisition
- capability checks
- unanswered setup questions
- readiness signals

Onboarding state is developmental. It should show what the person or agent
understands, what they still lack, and what needs to happen next.

### Governance State

State about what the system is allowed to do and how decisions are controlled.

Examples:

- policies
- permissions
- approval boundaries
- evidence standards
- risk classes
- audit requirements
- data access rules

Governance state constrains model-mediated action without replacing model
judgment.

## Cross-Family Relationships

State families are not silos.

Examples:

- A campaign is work state, but Laura may compare it against organizational
  narrative and mission state.
- Human onboarding is onboarding state, but it depends on role state, governance
  state, and knowledge state.
- A deal is work state and relationship state at the same time.
- Strategy is organizational identity state, but it should shape operating
  priorities and work selection.
- Agent onboarding depends on persona state, governance state, and evidence
  about tool capability.

The ontology should support multiple parent references and multiple rollup
paths.

## First-Cut Hierarchy

```text
Organizational State
  Organizational Identity State
    mission
    vision
    principles
    narrative
    strategy
  Operating State
    operating_picture
    priorities
    risks
    capacity
    cadence
  Work State
    project
    campaign
    deal
    task
    obligation
    decision
  Relationship State
    client
    partner
    stakeholder
    account
    person
  Knowledge State
    market_belief
    customer_insight
    research_finding
    assumption
    open_question
  Role And Persona State
    role
    persona
    facet
    authority_boundary
  Onboarding State
    human_onboarding
    agent_onboarding
    role_ramp
  Governance State
    policy
    permission
    approval_boundary
    evidence_standard
```

## Design Rule

When adding a state type, first ask:

1. Which family owns it?
2. Which other families can it reference?
3. Is it slow-changing, fast-changing, or developmental?
4. Does it represent facts, interpretations, or both?
5. Which persona is likely to interpret it differently?

