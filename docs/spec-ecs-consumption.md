# Spec: Entity-Current-State Consumption Architecture

**Status:** Approved — decisions locked 2026-06-26 (Braydon delegated).
**Purpose:** Spec drift anchor. This is the canonical statement of what the ECS
consumption architecture *is*. `specdrift` measures subsequent code against this.
Not a deliverable — a reference.

The full design document with phases, rollback, and risks lives at
`wkm/status/handoffs/plan-ecs-consumption-wiring-2026-06-26.md`.

---

## The five locked decisions

1. **Connect point: the `context` string via an injectable `context_enricher`
   hook on the shared `Responder.respond`.** The ECS packet is deterministic
   current-state evidence and appends to the pre-assembled `context` string
   (`paia-agent-runtime/src/paia_agent_runtime/chief_of_staff/current_state.py:477`
   `with_current_state_packet(context, packet)` was built for this seam). It does
   NOT go through `typed_context` (a fixed 5-part model-mediated list in
   `prompt_sections.render_typed_context_sections`) and NOT through the dead
   `ContextAssembler` (`context.py:305`, zero production call sites). The shared
   `Responder.respond` (`responder.py:227` → `:276` → `_build_system_prompt`
   at `:1439`) is the single connect point both runtimes
   (`AgentOperatorRuntime.run`, `WakeableWorkSessionRuntime.run`) call.

2. **Source freshness stays in the paia-program subprocess tool.** Only
   strategic state (north_star / current_priority + the staleness rating) moves
   into the runtime. Freshness is reached today via `CompanyStateTool.execute`
   (`tools/company_state.py:~95`) shelling out to `bin/pg company-refresh`.
   Migrating freshness is a separate, later decision.

3. **The fleet-refresh launchd daemon (every 30 min) runs the strategic-staleness
   runner and emits the read model.** It is already alive, already runs every 30
   min, already materializes the sibling `source-freshness-read-model.json`. No
   new process to babysit.

4. **Decommissioning is a per-module deadness audit, not a batch deletion.**
   `CompanyScope` in `company_scopes.py` is LIVE account-routing policy for
   `EmailDraftTool` (`tools/email_draft.py:12`) and STAYS. Only verified-dead
   freshness logic is removed, module by module, behind a per-module
   live-importer gate.

5. **Strategic staleness is entity-level first.** The `entity_id` bridge
   (commit `7a01541`) ships clean. A `scope_key` index for non-entity judgments
   (company_mission / company_strategy / operating_decision) is deferred as an
   explicit follow-up — not in the validation gate.

---

## The staleness read-model shape

`strategic-staleness-read-model.json`, keyed by `entity_id`, mirroring
`source-freshness-read-model.json`:

```json
{
  "latest_by_entity_id": {
    "<entity_id>": {
      "entity_id": "...",
      "classification": "objective_drift",
      "recommended_action": "revise",
      "confidence": 0.62,
      "rationale": "...",
      "nl_question": "...",
      "reviewed_at": "<ISO, mapped from output created_at>",
      "review_packet_id": "..."
    }
  }
}
```

**Non-negotiable shape rules:**

- `confidence` is the model's **numeric** value (0–1), carried verbatim
  (`schemas/strategic-review-output.schema.json` requires `number`, min 0, max 1).
  Code must NEVER bucket it into a string category — that would be code
  reinterpreting a model judgment.
- `nl_question` is included (a required model-owned field).
- `reviewed_at` maps from the runner output's `created_at` / `review_signal.created_at`.
- Only entity-current-state entries carry `entity_id` (enriched by
  `_enrich_entries_with_entity_id`, `strategic_staleness.py:724`). Non-entity
  entries are excluded from `latest_by_entity_id` (deferred to the scope_key index).

---

## The model-mediation boundary (must hold)

- **Code owns:** evidence, structure, gates, arithmetic (load read models, join by
  `entity_id`, render, the mechanical `is_stale`/`decay_warning`/`not_yet_effective`
  flags computed from each card's declared `stale_after`).
- **The model owns:** every semantic judgment — `classification`
  (`objective_drift|uncertain`), `recommended_action` (`validate|revise|retire`),
  `confidence`, `rationale`, `nl_question`. Code carries these verbatim from the
  review output; it never assigns them.

---

## The human-validation gate

Non-bypassable. Before ANY decommissioning (Phase 5), Braydon personally runs a
live turn against the ECS-enabled agent (Samantha on b-state) and confirms he sees
the ECS claims (north_star / current_priority) and the model-mediated staleness
rating carried verbatim for entities whose validity window has expired. Entities
still in-window legitimately show no rating — that is correct, not a bug.
