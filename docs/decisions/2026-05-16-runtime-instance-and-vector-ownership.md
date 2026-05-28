# Runtime Instance And Vector Ownership

**Status:** Accepted
**Date:** 2026-05-16

## Decision

Separate the State System product repo from deployed State System instances.

`/path/to/state-system` is the product/codebase. It
owns schemas, contracts, migrations, CLI tools, tests, and documentation.

`/path/to/state-system-runtime` is the deployed LFW State System
instance. It owns LFW runtime state, read models, source freshness evidence,
preflight evidence, index manifests, database configuration, and operational
artifacts.

The product repo must not contain private company corpora or mutable vector
indexes. A deployed company instance may and should own the database/vector
runtime substrate needed for that company's State System.

## Vector Boundary

State System should own semantic indexes over State System records:

- accepted state objects
- claims and objects once promoted into the substrate
- evidence cards and source summaries
- journals and commit records
- company memory
- operating pictures
- context packages and activation artifacts where useful

State System should not blindly duplicate every raw source corpus on day one.
Raw corpora remain owned by their source systems or specialized evidence
indexes until adapters promote summaries, evidence cards, claims, or accepted
state into the deployed instance.

Folio, msgvault, paia-memory, Drive, Linear, Zulip, GitHub, transcripts, and
other systems may retain their own raw/source indexes. State System records the
source declarations, freshness, access evidence, provenance, and gaps, and can
federate to those indexes for drill-down.

## Model Boundary

Retrieval is evidence plumbing. It must not become hidden judgment.

Code may:

- maintain indexes
- retrieve by explicit company/source/state scope
- expose freshness, access, provenance, sensitivity, and gaps
- enforce permissions and governance
- assemble evidence packets

The model owns:

- salience
- synthesis
- prioritization
- uncertainty interpretation
- "How is this company doing?" judgment
- next-question and next-action reasoning

Any deterministic company health score, priority rule, or semantic routing rule
would be a model agency deviation unless explicitly approved and documented.

## Production Implication

The next State System production slices should build toward:

1. `state-instance-runtime-layout-v0`: define the deployed instance layout,
   database/vector configuration contract, and inspectable runtime directories.
2. `state-vector-index-baseline-v0`: add the first State System-owned vector
   index contract for interpreted records/evidence cards in the deployed
   instance.
3. `state-company-understanding-surface-v0`: emit a company understanding
   surface that combines accepted state, operating pictures, index manifests,
   source freshness, access evidence, and gaps without synthesizing the answer
   in deterministic code.

PAIA should consume that surface and call the relevant retrieval backends, then
let the model synthesize answers such as "How is LFW doing?" with evidence and
freshness warnings.
