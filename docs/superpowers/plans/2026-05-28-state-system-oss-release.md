# State System OSS Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Get State System to a clean, publicly releasable state with no personal data, proper packaging, CI, and a readable README.

**Architecture:** Depersonalization replaces hardcoded personal/company references with neutral example identifiers (`acme`, `examplecorp`, `user@example.com`). Deployment-specific helper functions in core code become data-driven or move to tests/fixtures. Packaging adds `pyproject.toml` for installability.

**Tech Stack:** Python 3.14 (stdlib only), GitHub Actions CI, hatchling build

---

## Scope

148 files touch: 5 code, 38 tests, 74 examples, 31 docs. Plus 3 new files (LICENSE, pyproject.toml, CI).

The plan groups work into 8 tasks by dependency order. Each task is independently committable and testable.

---

## Renaming Convention

All personal identifiers get mapped to neutral equivalents:

| Original | Replacement |
|---|---|
| `braydon`, `acme_ops` | `acme_user`, `acme_ops` |
| `lfw`, `lightforgeworks` | `acme` |
| `examplecorp` | `examplecorp` |
| `demo_co` | `demo_co` |
| `southern-abrasives` | `southern-abrasives` (fictional — keep) |
| `laura`, `patrick`, `miriam` | Keep (fictional personas) |
| `/path/to/user/...` | `/path/to/...` or env var |
| `person.acme_user` | `person.acme_user` |
| `company.lfw` | `company.acme` |
| `state_instance.acme_ops` | `state_instance.acme_ops` |
| `state_instance.examplecorp` | `state_instance.examplecorp` |
| `state_instance.demo_co` | `state_instance.demo_co` |
| `intempio.com`, `mcco.us`, etc. | `acme.com`, `example.com` |

---

### Task 1: Add LICENSE and pyproject.toml

**Files:**
- Create: `LICENSE`
- Create: `pyproject.toml`
- Modify: `.gitignore`

- [ ] **Step 1: Create MIT LICENSE**

```
MIT License

Copyright (c) 2026 Acme User McElroy

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 2: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "state-system"
version = "0.1.0"
description = "A generic model-mediated substrate for tracking organizational state."
requires-python = ">=3.11"
license = "MIT"

[project.scripts]
state-system = "state_system.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

Note: `requires-python = ">=3.11"` (not 3.14) for broader OSS compatibility. Verify code doesn't use 3.14-only features (it shouldn't — it's stdlib-only).

- [ ] **Step 3: Update .gitignore**

Add:
```
dist/
build/
*.egg-info/
```

- [ ] **Step 4: Verify package installs**

Run: `cd /path/to/state-system && pip install -e . 2>&1 | tail -3`
Expected: `Successfully installed state-system-0.1.0`

- [ ] **Step 5: Verify tests still pass**

Run: `cd /path/to/state-system && python3 -m unittest discover -s tests 2>&1 | tail -3`
Expected: 224 tests, same 1 pre-existing failure (bstate LFW gap refs)

- [ ] **Step 6: Commit**

```bash
git add LICENSE pyproject.toml .gitignore
git commit -m "chore: add MIT license and pyproject.toml for OSS packaging"
```

---

### Task 2: Depersonalize core code (3 files)

**Files:**
- Modify: `state_system/instance_agent_packages.py` (lines 695-1030)
- Modify: `state_system/instance_understanding_surface.py` (lines 255-280)
- Modify: `state_system/paia_bootstrap.py` (lines 16, 61-62)

This is the highest-severity work. These 3 files have hardcoded personal refs in production code paths.

- [ ] **Step 1: Depersonalize `paia_bootstrap.py`**

Replace:
```python
DEFAULT_PAIA_STATE_ROOT = Path("/path/to/state-system-runtime")
```
With:
```python
DEFAULT_PAIA_STATE_ROOT = Path(os.environ.get("STATE_SYSTEM_ROOT", ""))
```

Replace:
```python
load_json(directory / "company-acme.json"),
```
With:
```python
load_json(directory / "company-acme.json"),
```

Replace:
```python
load_json(directory / "company-examplecorp.json"),
```
With:
```python
load_json(directory / "company-examplecorp.json"),
```

- [ ] **Step 2: Depersonalize `instance_agent_packages.py`**

The personal refs are in two helper functions:
- `_sam_package()` — builds a Samantha agent package for `acme_ops`. Rename to `_example_personal_assistant_package()` and replace all `acme_ops` → `acme_ops`, `braydon` → `acme_user`.
- `_navicyte_synthyta_federation_pack()` — builds a federation pack for examplecorp/demo_co. Rename to `_example_portfolio_federation_pack()` and replace `demo_co` → `demo_co`, `examplecorp` → `examplecorp`.
- The `if instance_ref in {"state_instance.demo_co", "state_instance.examplecorp"}` guard at line 1012 becomes `if instance_ref in {"state_instance.demo_co", "state_instance.examplecorp"}`.
- All `acme_ops` refs → `acme_ops`.

- [ ] **Step 3: Depersonalize `instance_understanding_surface.py`**

Same pattern as above — 4 personal refs in deployment-specific federation pack logic:
- `state_instance.acme_ops` → `state_instance.acme_ops`
- `state_instance.demo_co` → `state_instance.demo_co`
- `state_instance.examplecorp` → `state_instance.examplecorp`
- `instance_federation_pack.portfolio_to_navicyte_synthyra` → `instance_federation_pack.portfolio_to_demo_co_examplecorp`

- [ ] **Step 4: Run full test suite**

Run: `python3 -m unittest discover -s tests 2>&1 | tail -5`
Expected: Same pass/fail count as before (tests still reference old names — that's Task 3)

- [ ] **Step 5: Commit**

```bash
git add state_system/instance_agent_packages.py state_system/instance_understanding_surface.py state_system/paia_bootstrap.py
git commit -m "refactor: depersonalize core code for OSS release"
```

---

### Task 3: Depersonalize test files (38 files)

**Files:**
- Modify: All 38 files in `tests/` that contain personal refs

This is the bulk mechanical work. Every personal identifier gets the same mapping from the table above.

- [ ] **Step 1: Do a bulk find-and-replace across tests**

```bash
cd /path/to/state-system

# Dry run first
find tests/ -name "*.py" -exec sed -n '
  s/acme_ops/acme_ops/gp
  s/braydon@/user@/gp
' {} +

# Then apply (after verifying dry run looks right):
find tests/ -name "*.py" -exec sed -i '' '
  s/acme_ops/acme_ops/g
  s/braydon@example\.com/user@example.com/g
  s/person\.braydon/person.acme_user/g
  s/entity\.braydon/entity.acme_user/g
  s/state_instance\.examplecorp/state_instance.examplecorp/g
  s/state_instance\.demo_co/state_instance.demo_co/g
  s/company\.examplecorp/company.examplecorp/g
  s/company\.demo_co/company.demo_co/g
  s/company\.lfw/company.acme/g
  s/connector\.federated\.acme_ops/connector.federated.acme_ops/g
  s/index\.federated\.acme_ops/index.federated.acme_ops/g
  s/relationship_index:braydon_long_history/relationship_index:acme_long_history/g
  s/portfolio_to_navicyte_synthyra/portfolio_to_demo_co_examplecorp/g
' {} +
```

Note: `braydon` appears in `braydon@example.com` (git fixture author email). Replace with `user@example.com`. Do NOT blindly replace `braydon` everywhere — some may be in comments or strings that need individual judgment.

- [ ] **Step 2: Run test suite, fix breakages**

Run: `python3 -m unittest discover -s tests 2>&1 | tail -5`

Expect: Most tests pass. Fix any that break from incomplete renaming (e.g., a string literal that didn't get caught by sed).

- [ ] **Step 3: Commit**

```bash
git add tests/
git commit -m "refactor: depersonalize test fixtures for OSS release"
```

---

### Task 4: Depersonalize example JSON files (74 files)

**Files:**
- Rename + modify: All 74 files in `examples/` with personal refs
- Rename: files with personal names in filenames (e.g., `instance-acme-ops.json` → `instance-acme-ops.json`)

- [ ] **Step 1: Rename files with personal names in filenames**

```bash
cd /path/to/state-system

# Rename example files
mv examples/instance-preflight/instance-preflight-braydon-personal-folio.json \
   examples/instance-preflight/instance-preflight-acme-ops-folio.json

mv examples/instance-capability/instance-acme-ops.json \
   examples/instance-capability/instance-acme-ops.json

mv examples/company-capability/company-acme.json \
   examples/company-capability/company-acme.json

mv examples/company-capability/company-examplecorp.json \
   examples/company-capability/company-examplecorp.json

mv examples/company-capability/company-demo-co.json \
   examples/company-capability/company-demo-co.json
```

- [ ] **Step 2: Bulk find-and-replace inside JSON content**

```bash
find examples/ -name "*.json" -exec sed -i '' '
  s/acme_ops/acme_ops/g
  s/braydon@/user@/g
  s/person\.braydon/person.acme_user/g
  s/entity\.braydon/entity.acme_user/g
  s/company\.lfw/company.acme/g
  s/company-lfw/company-acme/g
  s/company\.examplecorp/company.examplecorp/g
  s/company-examplecorp/company-examplecorp/g
  s/company\.demo_co/company.demo_co/g
  s/company-demo_co/company-demo-co/g
  s/state_instance\.examplecorp/state_instance.examplecorp/g
  s/state_instance\.demo_co/state_instance.demo_co/g
  s/connector\.federated\.acme_ops/connector.federated.acme_ops/g
  s/index\.federated\.acme_ops/index.federated.acme_ops/g
  s/portfolio_to_navicyte_synthyra/portfolio_to_demo_co_examplecorp/g
' {} +
```

- [ ] **Step 3: Run conformance tests specifically**

Run: `python3 -m unittest tests.test_open_source_ecosystem_conformance -v 2>&1`
Expected: All pass (they scan for specific markers like `braydon@`, `/path/to/user`, etc.)

- [ ] **Step 4: Run validate command**

Run: `python3 -m state_system.cli --project-root . validate 2>&1`
Expected: `{"ok": true, ...}`

- [ ] **Step 5: Commit**

```bash
git add examples/
git commit -m "refactor: depersonalize example fixtures for OSS release"
```

---

### Task 5: Update conformance test markers

**Files:**
- Modify: `tests/test_open_source_ecosystem_conformance.py`

The conformance test `PRIVATE_DEPLOYMENT_MARKERS` tuple currently scans for `braydon`-specific patterns. After depersonalization, update it to scan for generic private-data patterns (any email, any `/Users/` path, any real domain).

- [ ] **Step 1: Update marker patterns**

Replace the current `PRIVATE_DEPLOYMENT_MARKERS` with:

```python
PRIVATE_DEPLOYMENT_MARKERS = (
    "/Users/",
    "local:/Users/",
    "local-path:/Users/",
    "msgvault:account:",
    "agentmem:tenant:",
    "garmin-connect:account:",
    "spotify:account:",
)
```

Remove `braydon@` and `Acme User` and `entity.acme_user` since those specific strings are gone. The generic `/Users/` catch-all handles any future path leaks. The existing `EMAIL_PATTERN` regex already catches any remaining email addresses.

- [ ] **Step 2: Run conformance tests**

Run: `python3 -m unittest tests.test_open_source_ecosystem_conformance -v 2>&1`
Expected: All pass

- [ ] **Step 3: Commit**

```bash
git add tests/test_open_source_ecosystem_conformance.py
git commit -m "refactor: update conformance markers for depersonalized fixtures"
```

---

### Task 6: Depersonalize docs (31 files)

**Files:**
- Modify: All 31 `.md` files in `docs/` with personal refs

- [ ] **Step 1: Bulk find-and-replace in docs**

```bash
find docs/ -name "*.md" -exec sed -i '' '
  s|/path/to/state-system-runtime|/path/to/state-system-runtime|g
  s|/path/to/personal-state|/path/to/personal-state|g
  s|/path/to/paia-agent-runtime/config/cognition-presets\.toml|/path/to/cognition-presets.toml|g
  s|/path/to/state-system|/path/to/state-system|g
  s|/path/to/relationship-substrate|/path/to/relationship-substrate|g
  s|/path/to/|/path/to/|g
  s|/path/to/acme-operations/|/path/to/acme-operations/|g
  s|/path/to/personal/|/path/to/personal/|g
  s|/path/to/user/\.paia/state-system|/path/to/state-system-runtime|g
  s|/path/to/user|/path/to/user|g
  s|acme_ops|acme_ops|g
  s|state_instance\.examplecorp|state_instance.examplecorp|g
  s|state_instance\.demo_co|state_instance.demo_co|g
  s|company\.lfw|company.acme|g
  s|company\.examplecorp|company.examplecorp|g
  s|company\.demo_co|company.demo_co|g
  s|company-lfw|company-acme|g
  s|company-examplecorp|company-examplecorp|g
  s|company-demo_co|company-demo-co|g
' {} +
```

- [ ] **Step 2: Manual review of NORTH_STAR.md and key design docs**

Some docs reference PAIA, LFW, and other ecosystem concepts that need judgment calls, not just sed. Read through:
- `docs/NORTH_STAR.md`
- `docs/app-substrate-contract.md`
- `docs/concepts/first-deployment-implementation-blueprint.md`
- `docs/runbooks/open-source-onboarding.md`
- `docs/runbooks/personal-b-state.md`

Remove or generalize references that only make sense in your personal deployment context.

- [ ] **Step 3: Commit**

```bash
git add docs/
git commit -m "docs: depersonalize documentation for OSS release"
```

---

### Task 7: Depersonalize README and remove agent files

**Files:**
- Modify: `README.md`
- Delete: `AGENTS.md`
- Delete: `CLAUDE.md`

- [ ] **Step 1: Rewrite README intro (top section)**

Replace the current top with something like:

```markdown
# State System

State System is a generic model-mediated substrate for tracking organizational
state — people, projects, deals, missions, relationships, obligations, and
agent actions.

State is not a note, a prompt, or a transient context dump. State is a durable,
scoped record of what appears to be true, why that view changed, what evidence
supports it, what is uncertain, and what needs attention.

## Quick Start

```bash
git clone https://github.com/<you>/state-system.git
cd state-system
python3 -m unittest discover -s tests   # verify install
python3 -m state_system.cli --project-root . validate
./scripts/demo_state_system.sh           # run the demo
```

See [docs/runbooks/open-source-onboarding.md](docs/runbooks/open-source-onboarding.md)
for the full adopter path.

## What It Does

- ...
```

Keep the "What Works Today" and "Reviewer Path" sections — they're good. Just depersonalize any `/path/to/user` paths and company-specific names.

- [ ] **Step 2: Delete AGENTS.md and CLAUDE.md**

```bash
git rm AGENTS.md CLAUDE.md
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: rewrite README for OSS release, remove agent-internal files"
```

---

### Task 8: Add CI and final validation

**Files:**
- Create: `.github/workflows/test.yml`

- [ ] **Step 1: Create GitHub Actions workflow**

```yaml
name: Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Run tests
        run: python3 -m unittest discover -s tests -v

      - name: Validate schemas and examples
        run: python3 -m state_system.cli --project-root . validate

      - name: Conformance checks
        run: python3 -m unittest tests.test_open_source_ecosystem_conformance -v
```

- [ ] **Step 2: Run full test suite one final time**

Run: `python3 -m unittest discover -s tests 2>&1 | tail -5`
Expected: 224+ tests, 0 failures (the pre-existing bstate/LFW failure should be fixed by depersonalization)

- [ ] **Step 3: Run validate**

Run: `python3 -m state_system.cli --project-root . validate 2>&1`
Expected: `{"ok": true, ...}`

- [ ] **Step 4: Run demo**

Run: `./scripts/demo_state_system.sh 2>&1 | tail -5`
Expected: Report suite written successfully

- [ ] **Step 5: Commit**

```bash
git add .github/
git commit -m "ci: add GitHub Actions test workflow"
```

---

## Post-Plan Checklist

After all 8 tasks are complete, run this final verification:

- [ ] `grep -r "braydon" state_system/ tests/ examples/ --include="*.py" --include="*.json"` returns 0 hits
- [ ] `grep -r "/path/to/user" state_system/ tests/ examples/ docs/ README.md` returns 0 hits
- [ ] `grep -r "intempio\|mcco\.us\|examplecorp\|demo_co\|lfw" state_system/ --include="*.py"` returns 0 hits
- [ ] `python3 -m unittest discover -s tests` passes clean (0 failures)
- [ ] `python3 -m state_system.cli --project-root . validate` passes
- [ ] `./scripts/demo_state_system.sh` runs successfully
- [ ] LICENSE file exists
- [ ] pyproject.toml exists and `pip install -e .` works
- [ ] No AGENTS.md or CLAUDE.md in repo root
- [ ] `.github/workflows/test.yml` exists
