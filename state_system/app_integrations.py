from __future__ import annotations

from html import escape
import json
from pathlib import Path

from state_system.contracts import ExampleIndex, JsonObject, load_json, validate_all_examples


CHAIN_DEFINITIONS: tuple[JsonObject, ...] = (
    {
        "id": "prospect-to-outreach",
        "title": "Prospect Researcher -> Outreach Engine",
        "source": "source-prospect-campaign-research-001.json",
        "package": "prospect-opportunity-context-package-001.json",
        "model_output": "prospect-to-outreach-model-proposal-output-001.json",
        "commit": "prospect-to-outreach-commit-result-001.json",
        "artifacts": ["outreach-candidate-package-001.json"],
        "conformance": "conformance-no-hidden-fit-scoring-001.json",
        "conformance_label": "No hidden scoring",
    },
    {
        "id": "outreach-reply-to-crm-secondary-contacts",
        "title": "Outreach reply -> CRM and secondary contacts",
        "source": "source-outreach-email-reply-002.json",
        "package": "outreach-engagement-context-package-002.json",
        "model_output": "outreach-reply-routing-model-proposal-output-002.json",
        "commit": "outreach-reply-crm-secondary-contacts-commit-result-002.json",
        "artifacts": [
            "crm-relationship-update-002.json",
            "prospect-secondary-contact-candidates-002.json",
            "outreach-engagement-intelligence-002.json",
        ],
        "conformance": "conformance-no-regex-reply-routing-002.json",
        "conformance_label": "No regex routing",
    },
)


def run_app_integration_fixtures(*, project_root: Path, output_dir: Path) -> JsonObject:
    output_dir.mkdir(parents=True, exist_ok=True)
    examples_dir = project_root / "examples"
    app_dir = examples_dir / "app-integrations"
    index = ExampleIndex.load(examples_dir)
    schema_failures = _schema_failures(project_root)
    chains = [_run_chain(app_dir, index, definition) for definition in CHAIN_DEFINITIONS]
    status = "passed" if not schema_failures and _chains_pass(chains) else "failed"

    report: JsonObject = {
        "id": "report.app-integrations",
        "title": "State System App Integration Report",
        "status": status,
        "output_dir": str(output_dir),
        "schema_failures": schema_failures,
        "chains": chains,
    }
    _write_json(output_dir / "app-integration-report.json", report)
    (output_dir / "index.html").write_text(
        render_app_integration_report_html(report),
        encoding="utf-8",
    )
    return report


def render_app_integration_report_html(report: JsonObject) -> str:
    chain_sections = [
        _chain_section(chain)
        for chain in report["chains"]
    ]
    return "\n".join(
        [
            "<!doctype html>",
            "<html lang=\"en\">",
            "<head>",
            "  <meta charset=\"utf-8\">",
            "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
            f"  <title>{escape(str(report['title']))}</title>",
            "  <style>",
            "    :root { --bg:#f6f7f9; --paper:#fff; --ink:#1f2933; --muted:#526170; --line:#d8dee6; --ok:#1f7a4d; --bad:#a22f3b; --code:#eef2f6; }",
            "    * { box-sizing: border-box; }",
            "    body { margin:0; background:var(--bg); color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,\"Segoe UI\",sans-serif; line-height:1.45; }",
            "    main { width:min(1120px, calc(100vw - 32px)); margin:0 auto; padding:32px 0 48px; }",
            "    header, section { margin-bottom:16px; padding:18px; background:var(--paper); border:1px solid var(--line); border-radius:8px; }",
            "    h1,h2,h3,p { margin-top:0; } h1 { margin-bottom:8px; font-size:30px; letter-spacing:0; } h2 { margin-bottom:12px; font-size:20px; letter-spacing:0; } h3 { margin-bottom:8px; font-size:15px; letter-spacing:0; }",
            "    .eyebrow { margin-bottom:6px; color:var(--muted); font-size:12px; font-weight:760; text-transform:uppercase; }",
            "    .lede { max-width:840px; color:var(--muted); }",
            "    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:10px; }",
            "    .metric { padding:12px; border:1px solid var(--line); border-radius:8px; background:#fbfcfd; }",
            "    .metric strong { display:block; margin-bottom:4px; font-size:12px; color:var(--muted); text-transform:uppercase; }",
            "    .passed { color:var(--ok); font-weight:760; } .failed { color:var(--bad); font-weight:760; }",
            "    ul { margin:0; padding-left:20px; } li { margin:5px 0; } code { padding:2px 5px; border-radius:5px; background:var(--code); }",
            "  </style>",
            "</head>",
            "<body>",
            "<main>",
            "<header>",
            "<p class=\"eyebrow\">State System</p>",
            "<h1>App Integration Report</h1>",
            "<p class=\"lede\">Fixture-backed inspection surface for Prospect Researcher, Outreach Engine, and CRM handoff contracts.</p>",
            "</header>",
            "<section>",
            "<h2>Run Summary</h2>",
            "<div class=\"grid\">",
            _metric("Status", report["status"], str(report["status"])),
            _metric("Chains", len(report["chains"])),
            _metric("Schema failures", len(report["schema_failures"]), "failed" if report["schema_failures"] else "passed"),
            _metric("Output directory", report["output_dir"]),
            "</div>",
            "</section>",
            *chain_sections,
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _run_chain(app_dir: Path, index: ExampleIndex, definition: JsonObject) -> JsonObject:
    source = load_json(app_dir / definition["source"])
    package = load_json(app_dir / definition["package"])
    model_output = load_json(app_dir / definition["model_output"])
    commit = load_json(app_dir / definition["commit"])
    artifacts = [load_json(app_dir / path) for path in definition["artifacts"]]
    conformance = load_json(app_dir / definition["conformance"])

    checks = [
        _check(
            "source included in package evidence",
            source["source_refs"][0] in package["evidence_context"]["evidence_refs"],
        ),
        _check(
            "artifact source packages match package",
            all(artifact["source_package_ref"] == package["id"] for artifact in artifacts),
        ),
        _check(
            "artifact model outputs match model output",
            all(artifact["model_output_ref"] == model_output["id"] for artifact in artifacts),
        ),
        _check(
            "artifact commits match commit result",
            all(artifact["commit_result_ref"] == commit["id"] for artifact in artifacts),
        ),
        _check(
            "commit follow-up refs include artifacts",
            {
                artifact["id"]
                for artifact in artifacts
            }.issubset(set(commit["review_signal"]["follow_up_refs"])),
        ),
        _check(
            "artifact evidence refs resolve",
            all(
                ref in index.by_id
                for artifact in artifacts
                for ref in artifact["evidence_refs"]
            ),
        ),
        _check(
            definition["conformance_label"],
            conformance["passed"]
            and conformance["deterministic_judgment_rules"] == [],
        ),
    ]
    status = "passed" if all(check["status"] == "passed" for check in checks) else "failed"
    return {
        "id": definition["id"],
        "title": definition["title"],
        "status": status,
        "source_event_id": source["id"],
        "package_id": package["id"],
        "model_output_id": model_output["id"],
        "commit_id": commit["id"],
        "commit_status": commit["status"],
        "artifact_ids": [artifact["id"] for artifact in artifacts],
        "conformance_id": conformance["id"],
        "conformance_label": definition["conformance_label"],
        "checks": checks,
    }


def _schema_failures(project_root: Path) -> list[JsonObject]:
    return [
        {
            "path": str(result.path),
            "schema": result.schema,
            "errors": list(result.errors),
        }
        for result in validate_all_examples(project_root)
        if "app-integrations" in result.path.parts and not result.ok
    ]


def _chains_pass(chains: list[JsonObject]) -> bool:
    return all(chain["status"] == "passed" for chain in chains)


def _check(name: str, passed: bool) -> JsonObject:
    return {"name": name, "status": "passed" if passed else "failed"}


def _chain_section(chain: JsonObject) -> str:
    checks = [
        f"<li><span class=\"{escape(str(check['status']))}\">{escape(str(check['status']))}</span> - {escape(str(check['name']))}</li>"
        for check in chain["checks"]
    ]
    artifacts = [f"<li><code>{escape(str(artifact_id))}</code></li>" for artifact_id in chain["artifact_ids"]]
    return "\n".join(
        [
            "<section>",
            f"<h2>{escape(str(chain['title']))}</h2>",
            "<div class=\"grid\">",
            _metric("Status", chain["status"], str(chain["status"])),
            _metric("Source", chain["source_event_id"]),
            _metric("Package", chain["package_id"]),
            _metric("Commit", f"{chain['commit_id']} ({chain['commit_status']})"),
            _metric(chain["conformance_label"], chain["conformance_id"], "passed"),
            "</div>",
            "<h3>Downstream Artifacts</h3>",
            "<ul>",
            *artifacts,
            "</ul>",
            "<h3>Checks</h3>",
            "<ul>",
            *checks,
            "</ul>",
            "</section>",
        ]
    )


def _metric(label: str, value: object, class_name: str = "") -> str:
    class_attr = f" class=\"{class_name}\"" if class_name else ""
    return (
        "<div class=\"metric\">"
        f"<strong>{escape(str(label))}</strong>"
        f"<span{class_attr}>{escape(str(value))}</span>"
        "</div>"
    )


def _write_json(path: Path, payload: JsonObject) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
