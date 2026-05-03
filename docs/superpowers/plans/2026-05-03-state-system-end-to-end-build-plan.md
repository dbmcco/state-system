# State System End-To-End Build Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move State System from contract prototype to a user-testable, trace-driven substrate for agent-operated apps.

**Architecture:** State System remains the source of durable interpreted state. Apps and agents consume bounded context packages and activation records; humans inspect through agent-mediated judgment and report surfaces. Every new capability must land as a runnable trace plus pressure test before downstream app breadth.

**Tech Stack:** Python standard library, JSON schemas, file-backed stores, Workgraph, Speedrift drift checks, static HTML reports.

---

## Task Graph

1. `state-user-report-v0`: generate a user-testable static report from trace-run artifacts.
2. `state-stale-context-pressure-v0`: add a trace proving refresh-before-external-action behavior.
3. `state-prospect-outreach-crm-contract-v0`: add cross-app fixture traces for Prospecting Partner -> Outreach Engine -> CRM handoff.
4. `state-model-mediated-drift-suite-v0`: add pressure tests that catch hidden rules, scoring, and qualitative-judgment collapse.
5. `state-reporting-surface-v1`: expand the static report into a multi-trace reporting surface after the pressure traces are stable.

## Current Slice: User-Testable Static Trace Report

**Files:**

- Create: `state_system/reporting.py`
- Modify: `state_system/trace_runner.py`
- Modify: `scripts/demo_state_system.sh`
- Modify: `README.md`
- Create: `tests/test_trace_reporting.py`

**Behavior:**

- `trace-run` writes `index.html` in the trace output directory.
- The report shows trace status and ordered steps.
- If an activation artifact exists, the report shows activation goal, expected
  response type, allowed action refs, prohibited action refs, capture policy,
  and freshness.
- If an agent response artifact exists, the report shows response status and
  response text.
- The demo script runs `examples/traces/laura-agent-activation.trace.json` and
  prints the generated report path.

**Verification:**

```bash
python3 -m state_system.cli --project-root . validate
python3 -m state_system.cli --project-root . trace-run examples/traces/laura-agent-activation.trace.json --output-dir /tmp/state-system-user-report
python3 -m unittest tests/test_trace_reporting.py tests/test_trace_runner.py tests/test_agent_activation.py
python3 -m unittest tests/test_contracts.py tests/test_stores.py tests/test_source_events.py tests/test_runner_reviewer.py tests/test_committer_materializer.py tests/test_governance_pressure.py tests/test_recent_context_packaging.py tests/test_cli.py tests/test_e2e_pressure_harness.py tests/test_cli_runtime.py tests/test_git_source_adapter.py tests/test_live_git_runtime.py tests/test_agent_consumers.py tests/test_trace_runner.py tests/test_agent_activation.py tests/test_trace_reporting.py
./.workgraph/drifts check --task state-user-report-v0 --write-log --create-followups
```

## Pressure And Integration Loops

- Stale context loop: create a trace where an activation package is stale before
  an external action and the expected report makes refresh required.
- Prospecting loop: create a Prospect Opportunity Package fixture with evidence,
  campaign state, ICP reasoning, and opportunity fit probability as model
  judgment.
- Outreach loop: consume the prospect package, activate an outreach agent, and
  capture a response/handoff artifact without sending real email.
- CRM loop: represent a qualified handoff and secondary contacts as retained
  engagement intelligence and CRM-bound state proposals.
- Model-mediated drift loop: test that code does not hardcode qualitative
  scoring, tone, readiness, or relationship judgments.
