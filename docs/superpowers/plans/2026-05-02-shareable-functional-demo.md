# Shareable Functional Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make State System easier to review by adding a README-visible diagram, a clear implemented-vs-designed explanation, and a one-command runtime demo.

**Architecture:** Keep the runtime unchanged. Add a static SVG overview, a shell demo that drives the existing CLI through the functional source-event-to-agent-context loop, and README sections that direct first-time reviewers through the system.

**Tech Stack:** Markdown, SVG, POSIX shell, Python standard library CLI already present in `state_system`.

---

### Task 1: Add Diagram Asset

**Files:**
- Create: `docs/assets/state-system-overview.svg`

- [ ] Add a static SVG overview suitable for GitHub README rendering.
- [ ] Keep the HTML diagram as the richer local reference.

### Task 2: Add One-Command Demo

**Files:**
- Create: `scripts/demo_state_system.sh`

- [ ] Drive the existing CLI against a temporary runtime.
- [ ] Show each major step: validate, seed, trigger, review, commit, index recent, build package, render package, capture response.
- [ ] Print output file locations so reviewers can inspect JSON artifacts.

### Task 3: Update README

**Files:**
- Modify: `README.md`

- [ ] Explain what is functional today.
- [ ] Explain what is designed but not implemented.
- [ ] Add a reviewer path.
- [ ] Embed `docs/assets/state-system-overview.svg`.
- [ ] Add the one-command demo.

### Task 4: Verify

**Files:**
- No source edits expected.

- [ ] Run `python3 -m state_system.cli --project-root . validate`.
- [ ] Run `./scripts/demo_state_system.sh`.
- [ ] Run the focused unit test suite from the README.
