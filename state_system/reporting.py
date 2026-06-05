from __future__ import annotations

from html import escape
import json
from pathlib import Path

from state_system.stores import JsonObject


def run_report_suite(*, project_root: Path, output_dir: Path) -> JsonObject:
    from state_system.app_integrations import run_app_integration_fixtures
    from state_system.mission_records import (
        MissionStoreBundle,
        build_mission_read_model,
        replay_mission_fixture,
    )
    from state_system.trace_runner import run_trace_manifest

    output_dir.mkdir(parents=True, exist_ok=True)

    trace_dir = output_dir / "agent-activation-trace"
    app_dir = output_dir / "app-integrations"
    mission_dir = output_dir / "mission-records"
    trace_report = run_trace_manifest(
        project_root=project_root,
        manifest_path=(
            project_root
            / "examples"
            / "traces"
            / "maya-agent-activation.trace.json"
        ),
        output_dir=trace_dir,
    )
    app_report = run_app_integration_fixtures(
        project_root=project_root,
        output_dir=app_dir,
    )
    mission_dir.mkdir(parents=True, exist_ok=True)
    mission_stores = MissionStoreBundle(mission_dir)
    mission_replay = replay_mission_fixture(
        project_root / "examples" / "missions" / "repo-audit-streamlinear.json",
        mission_stores,
    )
    mission_read_model = build_mission_read_model(
        mission_stores,
        mission_replay["mission_run_id"],
    )
    mission_read_model_path = mission_dir / "mission-read-model.json"
    _write_json(mission_read_model_path, mission_read_model)
    mission_report_path = mission_dir / "index.html"
    mission_report_path.write_text(
        render_mission_report_html(
            read_model=mission_read_model,
            read_model_path=mission_read_model_path,
        ),
        encoding="utf-8",
    )

    reports = [
        {
            "id": "agent-activation-trace",
            "title": "Agent Activation Trace",
            "status": trace_report["status"],
            "report_path": str(trace_dir / "index.html"),
            "summary": "Trace-run report for Maya activation, action boundaries, freshness, and captured response.",
        },
        {
            "id": "app-integrations",
            "title": "App Integration Report",
            "status": app_report["status"],
            "report_path": str(app_dir / "index.html"),
            "summary": "Fixture-backed Prospect/Outreach/CRM contract inspection report.",
        },
        {
            "id": "mission-records",
            "title": "Mission Records Read Model",
            "status": "passed",
            "report_path": str(mission_report_path),
            "summary": "Replay-backed mission read model for the Streamlinear repo-audit fixture.",
        },
    ]
    status = "passed" if all(report["status"] == "passed" for report in reports) else "failed"
    suite: JsonObject = {
        "id": "report.suite",
        "title": "State System Report Suite",
        "status": status,
        "output_dir": str(output_dir),
        "reports": reports,
    }
    _write_json(output_dir / "report-suite.json", suite)
    (output_dir / "index.html").write_text(
        render_report_suite_html(suite),
        encoding="utf-8",
    )
    return suite


def render_report_suite_html(report: JsonObject) -> str:
    report_cards = [_report_suite_card(entry) for entry in report["reports"]]
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
            "    * { box-sizing:border-box; } body { margin:0; background:var(--bg); color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,\"Segoe UI\",sans-serif; line-height:1.45; }",
            "    main { width:min(1100px, calc(100vw - 32px)); margin:0 auto; padding:32px 0 48px; }",
            "    header, section { margin-bottom:16px; padding:18px; background:var(--paper); border:1px solid var(--line); border-radius:8px; }",
            "    h1,h2,p { margin-top:0; } h1 { margin-bottom:8px; font-size:30px; letter-spacing:0; } h2 { margin-bottom:8px; font-size:20px; letter-spacing:0; }",
            "    .eyebrow { margin-bottom:6px; color:var(--muted); font-size:12px; font-weight:760; text-transform:uppercase; } .lede { max-width:820px; color:var(--muted); }",
            "    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:12px; } .card { padding:14px; border:1px solid var(--line); border-radius:8px; background:#fbfcfd; }",
            "    .passed { color:var(--ok); font-weight:760; } .failed { color:var(--bad); font-weight:760; } code { padding:2px 5px; border-radius:5px; background:var(--code); } a { color:#275f9f; font-weight:700; }",
            "  </style>",
            "</head>",
            "<body>",
            "<main>",
            "<header>",
            "<p class=\"eyebrow\">State System</p>",
            "<h1>State System Report Suite</h1>",
            "<p class=\"lede\">Single inspection entry point for current user-testable traces and app-substrate reports.</p>",
            "</header>",
            "<section>",
            "<h2>Suite Summary</h2>",
            f"<p>Status: <span class=\"{escape(str(report['status']))}\">{escape(str(report['status']))}</span></p>",
            f"<p>Output directory: <code>{escape(str(report['output_dir']))}</code></p>",
            "</section>",
            "<section>",
            "<h2>Reports</h2>",
            "<div class=\"grid\">",
            *report_cards,
            "</div>",
            "</section>",
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def render_mission_report_html(*, read_model: JsonObject, read_model_path: Path) -> str:
    mission = read_model["mission"]
    state_effects = read_model.get("state_effects", {})
    return "\n".join(
        [
            _html_head("Mission Records Report"),
            "<body>",
            "<main>",
            "<header>",
            "<p class=\"eyebrow\">State System</p>",
            "<h1>Mission Records Report</h1>",
            f"<p class=\"lede\">{escape(str(mission['summary']))}</p>",
            "</header>",
            "<section>",
            "<h2>Mission Summary</h2>",
            "<div class=\"grid\">",
            _metric("Mission", mission["id"]),
            _metric("Type", mission["mission_type"]),
            _metric("Status", mission["status"], "status"),
            _metric("Freshness", mission["freshness"]),
            "</div>",
            f"<p>{escape(str(mission['objective']))}</p>",
            f"<p>Machine read model: <a href=\"{escape(read_model_path.name)}\">{escape(read_model_path.name)}</a></p>",
            "</section>",
            _mission_record_section(
                "Agent Roster",
                read_model.get("agent_roster", []),
                ["agent_ref", "role", "status", "responsibility"],
            ),
            _mission_record_section(
                "Timeline",
                read_model.get("timeline", []),
                ["occurred_at", "event_type", "summary"],
            ),
            _mission_record_section(
                "Findings",
                read_model.get("findings", []),
                ["finding_type", "severity", "summary", "status"],
            ),
            _mission_record_section(
                "Stumbles",
                read_model.get("stumbles", []),
                ["stumble_type", "summary", "resolution_status"],
            ),
            _mission_record_section(
                "Governance",
                read_model.get("governance", []),
                ["policy_ref", "decision", "summary"],
            ),
            _mission_record_section(
                "Artifacts",
                read_model.get("artifacts", []),
                ["artifact_type", "summary", "artifact_ref"],
            ),
            _list_block("Follow-ups", read_model.get("follow_ups", [])),
            _mission_record_section(
                "Review Signals",
                state_effects.get("review_signals", []),
                ["status", "summary"],
            ),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def write_trace_report_html(*, output_dir: Path, report: JsonObject) -> Path:
    path = output_dir / "index.html"
    path.write_text(
        render_trace_report_html(output_dir=output_dir, report=report),
        encoding="utf-8",
    )
    return path


def render_trace_report_html(*, output_dir: Path, report: JsonObject) -> str:
    artifacts = _load_artifacts(report)
    activation = artifacts.get("agent-activation")
    response = artifacts.get("agent-response")
    rendered_activation = artifacts.get("render-activation")

    sections = [
        _html_head(str(report["title"])),
        "<body>",
        "<main>",
        "<header>",
        "<p class=\"eyebrow\">State System</p>",
        "<h1>State System User Test Report</h1>",
        f"<p class=\"lede\">{escape(str(report['title']))}</p>",
        "</header>",
        _summary_section(report),
        _steps_section(report),
    ]
    if isinstance(activation, dict):
        sections.append(_activation_section(activation))
    if isinstance(response, dict):
        sections.append(_response_section(response))
    if isinstance(rendered_activation, str):
        sections.append(_rendered_section(rendered_activation))
    sections.extend(
        [
            "<section>",
            "<h2>Artifact Directory</h2>",
            f"<p><code>{escape(str(output_dir))}</code></p>",
            "</section>",
            "</main>",
            "</body>",
            "</html>",
        ]
    )
    return "\n".join(sections)


def _html_head(title: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)} - State System Report</title>
  <style>
    :root {{
      --bg: #f6f7f9;
      --paper: #ffffff;
      --ink: #1f2933;
      --muted: #526170;
      --line: #d8dee6;
      --ok: #1f7a4d;
      --warn: #a05a00;
      --hold: #a22f3b;
      --code: #eef2f6;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
    }}
    main {{
      width: min(1100px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 32px 0 48px;
    }}
    header, section {{
      margin-bottom: 16px;
      padding: 18px;
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    h1, h2, h3, p {{ margin-top: 0; }}
    h1 {{ margin-bottom: 8px; font-size: 30px; letter-spacing: 0; }}
    h2 {{ margin-bottom: 12px; font-size: 20px; letter-spacing: 0; }}
    h3 {{ margin-bottom: 8px; font-size: 15px; letter-spacing: 0; }}
    .eyebrow {{
      margin-bottom: 6px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 760;
      text-transform: uppercase;
    }}
    .lede {{ max-width: 820px; color: var(--muted); }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; }}
    .metric {{ padding: 12px; border: 1px solid var(--line); border-radius: 8px; background: #fbfcfd; }}
    .metric strong {{ display: block; margin-bottom: 4px; font-size: 12px; color: var(--muted); text-transform: uppercase; }}
    .status {{ color: var(--ok); font-weight: 760; }}
    .warn {{ color: var(--warn); font-weight: 760; }}
    .hold {{ color: var(--hold); font-weight: 760; }}
    ul {{ margin: 0; padding-left: 20px; }}
    li {{ margin: 5px 0; }}
    code {{ padding: 2px 5px; border-radius: 5px; background: var(--code); }}
    pre {{
      overflow: auto;
      max-height: 360px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfd;
      white-space: pre-wrap;
    }}
    .two-col {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }}
  </style>
</head>"""


def _summary_section(report: JsonObject) -> str:
    validated = report.get("validated", {})
    return "\n".join(
        [
            "<section>",
            "<h2>Run Summary</h2>",
            "<div class=\"grid\">",
            _metric("Trace", report["trace_id"]),
            _metric("Status", report["status"], "status"),
            _metric("Activation", validated.get("agent_activation_id", "None")),
            _metric("Response", validated.get("agent_response_id", "None")),
            "</div>",
            "</section>",
        ]
    )


def _steps_section(report: JsonObject) -> str:
    items = []
    for step in report["steps"]:
        label = f"{step['name']} - {step['artifact_type']}"
        path = Path(step["artifact_path"]).name
        items.append(
            f"<li><strong>{escape(label)}</strong>: "
            f"<code>{escape(path)}</code></li>"
        )
    return "\n".join(
        ["<section>", "<h2>Trace Steps</h2>", "<ul>", *items, "</ul>", "</section>"]
    )


def _activation_section(activation: JsonObject) -> str:
    freshness = activation.get("freshness", {})
    refresh = "Yes" if freshness.get("requires_refresh_before_external_action") else "No"
    stale = "Yes" if freshness.get("stale_at_activation") else "No"
    return "\n".join(
        [
            "<section>",
            "<h2>Agent Activation</h2>",
            "<div class=\"grid\">",
            _metric("Goal", activation["activation_goal"]),
            _metric("Expected response type", activation["expected_response_type"]),
            _metric("Consumer", activation["consumer_ref"]),
            _metric("Valid until", freshness.get("valid_until", "Unknown")),
            _metric(
                "Package stale at activation",
                stale,
                "warn" if stale == "Yes" else "",
            ),
            _metric(
                "Requires refresh before external action",
                refresh,
                "warn" if refresh == "Yes" else "",
            ),
            "</div>",
            "<div class=\"two-col\">",
            _list_block("Allowed Actions", activation.get("allowed_action_refs", [])),
            _list_block(
                "Prohibited Actions",
                activation.get("prohibited_action_refs", []),
                "hold",
            ),
            "</div>",
            _list_block("Evidence Refs", activation.get("evidence_refs", [])),
            _list_block("Freshness Watermarks", freshness.get("watermark_refs", [])),
            _list_block("Activation Instructions", activation.get("instructions", [])),
            "</section>",
        ]
    )


def _response_section(response: JsonObject) -> str:
    return "\n".join(
        [
            "<section>",
            "<h2>Captured Agent Response</h2>",
            "<div class=\"grid\">",
            _metric("Response", response["id"]),
            _metric("Status", response["status"], "status"),
            _metric("Extraction", response["extraction_status"]),
            _metric("Activation", response.get("activation_id", "None")),
            "</div>",
            f"<pre>{escape(response['response_text'])}</pre>",
            "</section>",
        ]
    )


def _rendered_section(rendered_activation: str) -> str:
    return "\n".join(
        [
            "<section>",
            "<h2>Rendered Agent Instructions</h2>",
            f"<pre>{escape(rendered_activation)}</pre>",
            "</section>",
        ]
    )


def _report_suite_card(entry: JsonObject) -> str:
    path = Path(str(entry["report_path"]))
    link_path = f"{path.parent.name}/{path.name}"
    return "\n".join(
        [
            "<div class=\"card\">",
            f"<h2>{escape(str(entry['title']))}</h2>",
            f"<p>Status: <span class=\"{escape(str(entry['status']))}\">{escape(str(entry['status']))}</span></p>",
            f"<p>{escape(str(entry['summary']))}</p>",
            f"<p><a href=\"{escape(link_path)}\">Open report</a></p>",
            f"<p><code>{escape(str(path))}</code></p>",
            "</div>",
        ]
    )


def _mission_record_section(
    title: str,
    records: list[JsonObject],
    fields: list[str],
) -> str:
    if not records:
        return "\n".join(["<section>", f"<h2>{escape(title)}</h2>", "<p>None</p>", "</section>"])

    items = []
    for record in records:
        details = [
            f"<li><strong>{escape(field.replace('_', ' ').title())}</strong>: "
            f"{escape(str(record.get(field, 'None')))}</li>"
            for field in fields
        ]
        items.append(
            "\n".join(
                [
                    "<div class=\"metric\">",
                    f"<strong>{escape(str(record.get('id', title)))}</strong>",
                    "<ul>",
                    *details,
                    "</ul>",
                    "</div>",
                ]
            )
        )

    return "\n".join(
        [
            "<section>",
            f"<h2>{escape(title)}</h2>",
            "<div class=\"grid\">",
            *items,
            "</div>",
            "</section>",
        ]
    )


def _metric(label: str, value: object, class_name: str = "") -> str:
    class_attr = f" class=\"{class_name}\"" if class_name else ""
    return (
        "<div class=\"metric\">"
        f"<strong>{escape(label)}</strong>"
        f"<span{class_attr}>{escape(str(value))}</span>"
        "</div>"
    )


def _list_block(title: str, values: list[object], class_name: str = "") -> str:
    if values:
        items = [f"<li>{escape(str(value))}</li>" for value in values]
    else:
        items = ["<li>None</li>"]
    class_attr = f" class=\"{class_name}\"" if class_name else ""
    return "\n".join(
        [f"<div{class_attr}>", f"<h3>{escape(title)}</h3>", "<ul>", *items, "</ul>", "</div>"]
    )


def _load_artifacts(report: JsonObject) -> dict[str, JsonObject | str]:
    artifacts: dict[str, JsonObject | str] = {}
    for step in report["steps"]:
        path = Path(step["artifact_path"])
        if not path.exists():
            continue
        if step["artifact_type"] == "json":
            artifacts[step["name"]] = json.loads(path.read_text(encoding="utf-8"))
        elif step["artifact_type"] == "text":
            artifacts[step["name"]] = path.read_text(encoding="utf-8")
    return artifacts


def _write_json(path: Path, payload: JsonObject) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
