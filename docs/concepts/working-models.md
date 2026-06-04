# Working Models

Working models are bounded, purpose-specific assemblies over State System
substrate.

They are not durable truth. They are how a human, agent, app, runtime, reviewer,
or surface receives the right working set for a specific job.

## Gordian Knot

The durable substrate is truth-seeking.

Working models are task-seeking.

```text
Durable substrate:
  objects, claims, evidence, accepted state, journals, memory, governance

Working models:
  bounded projections over the substrate for a purpose

Consumers:
  agent runtime packets, CLI agents, apps, reports, wiki views, CRM views, model reviewers
```

This keeps State System from growing separate architectures for CRM, wiki,
company memory, trips, meetings, creative arcs, code review, and agent briefings.
Those are working-model profiles over the same substrate.

## Definition

A working model contains:

- stable identity
- model type
- purpose
- consumer reference
- object refs
- claim refs
- evidence refs
- accepted state refs
- memory refs
- governance refs or governance context
- runtime constraints, when a runtime owns execution
- visible control refs, when a human-facing control plane is involved
- freshness and validity boundaries
- lineage back to sources, packets, artifacts, activations, or prior models
- payload sections owned by the profile

It may be persisted for replay, inspection, or lineage. Persistence does not
make its assembled contents accepted truth.

## Ref Naming Rules

Use narrow names so working context does not collapse into state:

| Ref | Meaning |
| --- | --- |
| `object_refs` | Addressable things: people, documents, code, images, meetings, trips, packets, artifacts |
| `claim_refs` | Assertions about or by objects, whether accepted or still candidate |
| `source_refs` | Origin system/item refs |
| `evidence_refs` | Evidence that supports claims, state, memory, or proposals |
| `state_refs` | Accepted State System state only |
| `memory_refs` | Agent, person, or organizational memory; not truth by default |
| `governance_refs` | Policies, approval boundaries, and authority constraints |
| `runtime_constraints` | Execution limits owned by a runtime, not governance policy |
| `visible_control_refs` | Workboard, task, approval, schedule, or user-control surfaces |
| `artifact_refs` | Outputs, files, drafts, reports, generated media, transcripts |
| `packet_refs` | agent runtime or other runtime packet lineage |

The important narrowing is `state_refs`: it should not mean "anything relevant."
It means accepted working interpretation.

## Current Shapes As Working Models

| Shape | Owner | Working-model role |
| --- | --- | --- |
| `ContextPackage` | State System | Persona/app scoped context projection |
| `ModelReviewPacket` | State System | Interpretation input that may produce durable proposals |
| `AgentActivation` | State System | Audited invocation boundary using a package |
| `PacketEnvelope` | agent runtime | Runtime/workboard wire envelope over substrate refs |
| `ArcPacket` | agent runtime | Working context for ongoing human/agent arcs |
| Company Memory read model | State System | Organizational operating projection |
| CRM Operating Picture | State System | Relationship/opportunity projection, not CRM replacement |
| Wiki/report/dashboard page | Surface/app | Human-readable projection over a working model |

These should converge by invariant, not by forcing all payloads into one rigid
schema.

## Packet Boundary

agent runtime packets are a working-model implementation.

`PacketEnvelope` should remain a agent runtime wire/runtime envelope, not a State System
record type.

Packet ids, lineage, source refs, evidence refs, artifacts, and emitted events
may be durable. Packet assembled contents are working context and must not be
treated as durable truth unless reviewed and committed through State System.

## Compile Matrix

agent runtime packets and other working models should compile to State System primitives
only when the intent requires it:

| Path | Use when |
| --- | --- |
| `PacketEnvelope -> ContextPackage` | agent runtime needs bounded state/evidence/memory context from State System |
| `ContextPackage -> PacketEnvelope` | agent runtime wraps State System context with runtime and Workboard controls |
| `PacketEnvelope -> ModelReviewPacket` | The packet asks a model to interpret something that may create durable state, memory, approval, action, or review signal |
| `PacketEnvelope -> AgentActivation` | State System must audit the invocation boundary |
| `PacketEnvelope -> SourceEvent` | Packet input/output should enter durable review as evidence or a trigger |

Do not force every packet to compile to every State System shape.

## Invariants

1. A working model is not durable truth.
2. A working model must cite refs for meaningful claims.
3. A working model may contain candidate claims, but candidate claims are not
   accepted state.
4. Accepted state changes require journaled commit through State System.
5. Memory remains private or draft unless explicit promotion is reviewed and
   accepted.
6. Governance decides claim promotion, memory promotion, protected action, and
   external-use boundaries.
7. Runtime constraints do not replace governance.
8. Human-visible surfaces are projections, not truth sources by default.
9. Packet lineage may be durable even when packet contents are not.
10. Code assembles and validates; models interpret salience, meaning,
    relevance, and next action.

## Object And Claim Substrate

Working models reveal the need for a lower substrate:

```text
ObjectRecord
ClaimRecord
RelationshipRecord
ProjectionProfile / WorkingModel
```

Everything addressable can be an object: person, document, image, code file,
meeting, trip, CRM record, packet, or artifact. Not every object deserves
durable state.

Claims are assertions about or by objects. Some claims remain candidates. Some
become accepted state after evidence and governance review.

The next corrective implementation lane should add object and claim substrate
records, then map existing company memory, CRM operating picture, app fixtures,
and agent runtime packet lineage onto them.
