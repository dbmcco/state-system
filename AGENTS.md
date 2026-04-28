# AGENTS.md

- Scope: Applies to this `state-system` repo.
- Purpose: Design and build a generic model-mediated work-state system.
- Keep design and implementation separate until contracts are stable.
- Prefer schemas, examples, and explicit docs over implicit prompt behavior.
- Do not import PAIA assumptions as defaults. PAIA may be referenced as prior art.
- Avoid brittle behavioral heuristics. The model interprets state; code validates and persists.
- Keep changes minimal and scoped. Update examples when schemas change.
- Run relevant schema or test checks when adding executable validation.

