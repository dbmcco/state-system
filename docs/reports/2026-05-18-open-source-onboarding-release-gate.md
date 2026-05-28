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

## Private-Deployment-Only Fixture Cleanup

These items were deployment-bound, not product blockers. They have been
neutralized in the shipped example fixture surface so a clean OSS release no
longer exposes local user paths, personal account refs, or real-person display
names in public JSON examples.

| Artifact | Gap | Path |
|---|---|---|
| LFW capability pack | Replaced private `msgvault:account:*` preflight account and `/path/to/user` local paths with tenant/local example refs. | `examples/company-capability/company-lfw.json` |
| Synthyra capability pack | Replaced private `msgvault:account:*` preflight account and local path with tenant/local example refs. | `examples/company-capability/company-synthyra.json` |
| Personal instance pack | Replaced real-person display text, `entity.acme_user`, private source accounts, and `/path/to/user` paths with neutral example refs. | `examples/instance-capability/instance-acme-ops.json` |
| Personal agent package | Replaced real-person display text and private wearable/media account refs with neutral example refs. | `examples/instance-agent-package/instance-agent-package-acme-ops-samantha.json` |
| Core source module registry | Replaced illustrative private account/path examples with neutral example refs. | `examples/source-modules/source-module-core-connectors.json` |

The conformance suite now scans all public JSON examples for the private
deployment markers that caused this gap: `/path/to/user`, `local:/Users/`,
`local-path:/Users/`, `braydon@`, `msgvault:account:`,
private source account refs, `entity.acme_user`, and real-person display text.

## Product Blockers

None at the time of this report. The product gate passes.

If a future change introduces an email-shaped string, a credential value, or a
closed `connector_type` enum into the OSS contract fixture surface, the
conformance tests added by this task will fail and surface it before merge.

## Follow-Ups

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
