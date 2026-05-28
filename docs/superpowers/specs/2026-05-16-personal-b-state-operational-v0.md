# Personal b-state Operational Plan v0

## Objective

Build `/path/to/personal-state` as a first-class personal State System instance for Acme User. The instance should cover personal life and work obligations by federating to source-owned systems instead of copying their raw corpora.

## Core Interpretation

Acme User is a State System entity. LFW, Synthyra, Navicyte, Plum, and future systems are also state instances with their own roots, indexes, governance, and source ownership. Personal b-state should be the coordinating personal abstraction that can ask each owned source for evidence, freshness, and bounded context.

The system should not model Acme User by forcing him into a company ontology. It should use the generic state-instance contract and let models own salience, synthesis, and attention proposals over explicit evidence packages.

## Source Boundaries

- `folio`: personal knowledge and notes.
- `msgvault`: email archive and email vector retrieval; personal b-state references/query-surfaces this store and does not duplicate email embeddings by default.
- `agentmem`: agent memory source; personal b-state records readiness/freshness and consumes bounded read outputs.
- `paia_workboard`: personal and agent task source of truth for workboard tasks.
- `relationship_substrate`: personal network substrate under `/path/to/relationship-substrate`.
- `state_system_instance`: federated read surfaces for LFW, Synthyra, Navicyte, Plum, and future work instances.
- `local_path`: local personal files or project roots when explicitly declared.

## Design Constraints

- No raw corpus duplication into `/personal/b-state`.
- No new pgvector database unless a source has no owner and an explicit index decision justifies it.
- Multiple vector stores are acceptable when they are source-owned and declared by connector contract; the personal instance should maintain a routing/catalog layer, not a shadow universal embedding sink.
- Existing LFW/company flows must remain compatible.
- Runtime checks should be mechanical; model synthesis should consume their outputs but not replace them.
- Model outputs should be captured as proposals with evidence refs, not accepted state by default.

## Execution Shape

Speedrift should execute this as a dependency-ordered Workgraph, starting with instance-level readiness/freshness contracts, then personal connectors, then federation, then context packaging and model proposal loops.

Implementation should use isolated git worktrees for each wave. The main branch remains the integration point after tests and drift checks pass.

## Acceptance

- Workgraph contains a concrete dependency graph for the next implementation wave.
- Each implementation task has a `wg-contract` with objective, non-goals, touch list, acceptance, and validation.
- `/personal/b-state` remains a runtime root with capability/read models only; no raw corpora are copied there.
- The plan explicitly includes workboard tasks, agentmem, msgvault, relationship-substrate, and work-instance federation.
