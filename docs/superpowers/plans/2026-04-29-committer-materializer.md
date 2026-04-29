# Committer Materializer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first local commit path from model output to durable journals, memory entries, snapshots, rollup queue records, commit receipts, and review signals.

**Architecture:** `Committer` owns validation, evidence checks, pending/rejected decisions, idempotent receipts, and store writes. `materialize_snapshot` owns mechanical patch application and provenance updates; it does not reinterpret model meaning.

**Tech Stack:** Python standard library, existing JSON schemas, `StateStoreBundle`, `unittest`.

---

## File Structure

- Create `state_system/materializer.py`: derive a snapshot from an existing snapshot plus an accepted journal entry.
- Create `state_system/committer.py`: validate model outputs, enforce gates, persist durable records, and return commit results.
- Create `tests/test_committer_materializer.py`: cover accepted, pending, rejected, protected patch, no-op, and duplicate paths.
- Modify `README.md`: document the expanded local test command.

## TDD Tasks

### Task 1: Materializer

- [ ] Write `test_materializer_applies_patch_and_preserves_provenance`.
- [ ] Run `python3 -m unittest tests/test_committer_materializer.py`; expect import failure for missing materializer.
- [ ] Implement `materialize_snapshot(snapshot, journal_entry)` with replacement patch semantics, protected field rejection, `as_of` update, `latest_journal_entry_id` update, and evidence ref merge.
- [ ] Re-run the focused test; expect pass.

### Task 2: Accepted Commit

- [ ] Write `test_committer_accepts_supported_state_and_memory_proposals`.
- [ ] Run the focused test; expect import failure for missing committer.
- [ ] Implement `Committer.commit(...)` for supported state and memory proposals:
  - validate model output schema
  - create journal records from state proposals
  - create memory records from memory proposals
  - materialize affected snapshots
  - queue rollup requests in the commit result
  - persist commit and review-signal receipts
- [ ] Re-run focused tests; expect pass.

### Task 3: Governance Gates

- [ ] Add tests for approval-required action, missing evidence, protected snapshot patch, and no-op output.
- [ ] Run focused tests; expect failures for missing gate behavior.
- [ ] Implement narrow gates:
  - approval-required or high-risk actions become `pending_approval`
  - missing proposal evidence becomes `rejected`
  - protected snapshot patch fields become `rejected`
  - no-op outputs write only commit/review-signal receipts
- [ ] Re-run focused tests; expect pass.

### Task 4: Idempotency

- [ ] Add `test_committer_duplicate_model_output_returns_existing_commit`.
- [ ] Run focused tests; expect duplicate write failure.
- [ ] Return the existing deterministic commit receipt when a model output has already committed.
- [ ] Re-run focused tests; expect pass.

### Task 5: Verification And Landing

- [ ] Run `python3 -m unittest tests/test_contracts.py tests/test_stores.py tests/test_source_events.py tests/test_runner_reviewer.py tests/test_committer_materializer.py`.
- [ ] Run `python3 -m compileall state_system`.
- [ ] Run `./.workgraph/drifts check --task ss-committer-materializer --write-log --create-followups`.
- [ ] Mark `ss-committer-materializer` done in Workgraph with validation evidence.
- [ ] Commit and push.
