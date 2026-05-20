# Open-Source Onboarding Release Gate

Date: 2026-05-18
Task: `state-open-source-onboarding-release-gate-v0`

## Result

Release gate is GREEN for the open-source product surface. A fresh adopter can,
following `docs/runbooks/open-source-onboarding.md`, scaffold an instance, add
modules, run preflight/freshness, generate a package, declare a federation
pack, and pressure-test the package against real operational questions — all
without needing private prompting.

The gate is not green for shipping the in-tree LFW and Synthyra deployment
fixtures unmodified as OSS examples. Those carry deployment-bound identifiers
and are listed below as private-deployment-only gaps, separate from product
blockers.

## Gate Evidence

| Gate | Command | Status |
|---|---|---|
| Schema and example validation | `python3 -m state_system.cli --project-root . validate` | 129 examples ok |
| Full unit test suite | `python3 -m unittest discover -s tests` | full suite ok |
| Conformance tests | `python3 -m unittest tests.test_open_source_ecosystem_conformance` | 8/8 ok |
| Federation pack validation | `python3 -m state_system.cli --project-root . instance-federation-pack-validate examples/instance-federation-packs/instance-federation-pack-core-examples.json` | 3 packs ok |
| Package pressure (shipped registry) | `python3 -m state_system.cli --project-root . package-pressure-run examples/pressure-questions/package-pressure-core-real-questions.json --package <ids>=<paths>` | passes when given deployment-rendered packages; runbook documents `package not supplied` as the expected adopter signal |

The runbook gate includes a final `Verify the Release Gate` section listing the
same commands so a new adopter can replay them locally.

## Conformance Tests Added

`tests/test_open_source_ecosystem_conformance.py` already covered capability
connector type coverage, tool action linkage, question route linkage, and
generated-package contract fields. The release gate added:

1. `test_oss_contract_fixtures_have_no_email_addresses` — scans
   `examples/source-modules/`, `examples/tool-actions/`,
   `examples/question-routes/`, `examples/instance-federation-packs/`,
   `examples/pressure-questions/`, and `examples/instance-agent-package/`
   for email-address-shaped strings. Real account identifiers belong in
   private instance state roots, not OSS contract fixtures.
2. `test_oss_contract_fixtures_have_no_credential_values` — scans the same set
   for `password`, `secret`, `api_key`, `access_token`, `bearer`, or
   `client_secret` keys with non-empty values.
3. `test_schemas_do_not_lock_in_connector_type_enum` — walks every
   `schemas/*.json` and confirms no `connector_type` property declares a closed
   enum. This is the contract guarantee that new source modules can be
   registered without editing core schemas.

All three pass without modifying the shipped OSS contract fixtures.

## Remaining Private-Deployment-Only Gaps

These items are deployment-bound, not product blockers. They are tracked here
so a clean OSS release can anonymize or relocate them, but the product
contracts and release gate do not depend on them.

| Artifact | Gap | Path |
|---|---|---|
| LFW capability pack | `msgvault:account:braydon@lightforgeworks.com` in `source_connectors[].source_ref` | `examples/company-capability/company-lfw.json` |
| Synthyra capability pack | `msgvault:account:braydon@synthyra.com` in `source_connectors[].source_ref` | `examples/company-capability/company-synthyra.json` |
| Personal instance pack | Real name and `/Users/braydon` absolute paths in declared source refs | `examples/instance-capability/instance-braydon-personal.json` |
| Personal agent package | Generated against the personal pack above; carries the same identifiers | `examples/instance-agent-package/instance-agent-package-braydon-personal-samantha.json` |
| Core source module registry | `local:/Users/braydon/projects/work/lfw` shown as an illustrative `source_ref` example | `examples/source-modules/source-module-core-connectors.json` |

Recommended path before an external OSS-tagged release:

- Move LFW, Synthyra, and personal capability packs out of `examples/` into a
  deployment-private directory or into runtime state roots, leaving an
  anonymized `examples/instance-capability/instance-acme.json` and matching
  generated agent package as the OSS reference fixture.
- Replace the `/Users/braydon/projects/work/lfw` illustrative path in the
  source module registry with a neutral placeholder such as
  `/srv/lfw` or `local:/{absolute_path}`.

None of these gaps block the product gate. The conformance tests above pass
because they target the OSS-shareable contract fixture surface
(modules, tools, routes, federation packs, pressure questions, generated
package contracts) and intentionally exclude deployment-bound capability
packs.

## Product Blockers

None at the time of this report. The product gate passes.

If a future change introduces an email-shaped string, a credential value, or a
closed `connector_type` enum into the OSS contract fixture surface, the
conformance tests added by this task will fail and surface it before merge.

## Follow-Ups

- Anonymize the deployment-bound packs listed above before any external OSS
  release tag (out of scope here; will be a separate workgraph task).
- Continue tracking unresolved connector freshness issues
  (Spotify OAuth, transcript raw/processed pipeline) under
  `docs/runbooks/source-freshness-repair-backlog.md`; those are deployment
  freshness gaps, not OSS product blockers.

## Validation Commands Run

```
python3 -m state_system.cli --project-root . validate
python3 -m unittest tests.test_open_source_ecosystem_conformance
python3 -m state_system.cli --project-root . instance-federation-pack-validate examples/instance-federation-packs/instance-federation-pack-core-examples.json
python3 -m state_system.cli --project-root . package-pressure-run examples/pressure-questions/package-pressure-core-real-questions.json
```
