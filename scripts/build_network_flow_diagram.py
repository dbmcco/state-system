#!/usr/bin/env python3
"""Generate the State System data-flow network diagram in two forms:

  - docs/state-system-network-flow.html   full page (header, captions, legend)
  - docs/assets/state-system-network-flow.svg  standalone, embeddable SVG
    (styles embedded so it renders identically anywhere)

Node-and-edge network: the ingestion pipeline, the update-lifecycle cycle
(visible loop), and the read/answer path, plus feedback, governance, memory,
and federation edges. Each node carries a native SVG <title> tooltip giving
its schema name(s) + one-line responsibility.

Geometry (node border-intersection, curved back-edges, halo'd labels) is
computed here so both artifacts are clean and self-contained.

Run:  python3 scripts/build_network_flow_diagram.py
"""
from __future__ import annotations
import html
from dataclasses import dataclass, field
from pathlib import Path

# ---------- geometry ----------
HW, HH = 93, 37            # node half-width / half-height (186 x 74)
COL = {1: 110, 2: 330, 3: 550, 4: 770, 5: 990, 6: 1210, 7: 1430}
ROW = {"mem": 170, "main": 340, "sub": 510, "bot": 680}

# kind -> (fill, stroke, title-colour, tag)
KIND = {
    "src": ("#e6f0fb", "#2767b1", "#1c4d86", "source/evidence"),
    "evi": ("#eef6fc", "#3a78bf", "#1c4d86", "evidence"),
    "mem": ("#fff3d8", "#b7791f", "#7d5512", "memory"),
    "mdl": ("#efe9fb", "#6f4bb2", "#4a3183", "model"),
    "gov": ("#f9e7e7", "#b33a3a", "#822a2a", "governance"),
    "st":  ("#e6f4ee", "#1f8a5b", "#155f3f", "state kernel"),
    "pkg": ("#fff3d8", "#b7791f", "#7d5512", "packaging"),
    "acc": ("#edf0f3", "#6b7280", "#3c434c", "access"),
    "fed": ("#e6f0fb", "#2767b1", "#1c4d86", "federation"),
}


@dataclass
class Node:
    id: str
    cx: int
    cy: int
    title: str
    sub: str
    kind: str
    schemas: list[str] = field(default_factory=list)
    resp: str = ""


NODES = [
    Node("SRC", COL[1], ROW["main"], "Source Systems", "Linear · GitHub · Docs · CRM · Mail · Cal", "src",
         ["source-event.schema.json", "trigger.schema.json", "source-module-spec.schema.json"],
         "Systems of record emit factual events. They never decide durable meaning."),
    Node("PRE", COL[2], ROW["main"], "Preflight", "reachable?", "evi",
         ["instance-preflight-result.schema.json"],
         "Proves live connector access (passed) or records why not (failed/planned)."),
    Node("FRE", COL[2], ROW["sub"], "Freshness", "recent? fresh/stale/…", "evi",
         ["instance-source-freshness-record.schema.json"],
         "Proves source recency: fresh/stale/failed/unknown/planned. probe_only ≠ fresh."),
    Node("EVT", COL[3], ROW["main"], "Evidence Packet", "refs, not blobs", "evi",
         ["model-review-packet.schema.json"],
         "Bounded packet of references (not blobs) + actor + timestamp + governance state."),
    Node("MEM", COL[3] - 120, ROW["mem"], "Memory Kernel", "not truth by default", "mem",
         ["agent-memory-entry.schema.json", "company-memory.schema.json"],
         "Task-seeking memory; not truth by default. Promoted to state only via governance."),
    Node("PSN", COL[4], ROW["mem"], "Personas / Facets", "interpretive lens", "mdl",
         ["persona.schema.json", "facet.schema.json"],
         "Interpretive lens: what an agent notices, how it reads ambiguity, when it escalates."),
    Node("MOD", COL[4], ROW["main"], "Model Interpreter", "what changed · what matters", "mdl",
         ["model-proposal-output.schema.json"],
         "Interprets evidence → emits a journal proposal (or no-op). The model decides meaning."),
    Node("GOV", COL[5], ROW["main"], "Governance Gate", "committer · no silent fallback", "gov",
         ["governance-policy.schema.json", "commit-result.schema.json"],
         "Committer: valid/allowed/persisted/pending/rejected. Each check yields an explicit result."),
    Node("JRN", COL[6], ROW["main"], "State Journal", "append-only · TRUTH", "st",
         ["state-journal-entry.schema.json"],
         "Append-only source of truth. Corrections are new entries; full replay is always possible."),
    Node("SNP", COL[6], ROW["sub"], "Snapshot", "materialized current view", "st",
         ["state-object.schema.json", "entity-current-state-record.schema.json"],
         "Materialized current view of journal history. Compact reads; drill journal for provenance."),
    Node("ROL", COL[4], ROW["sub"], "Rollup Queue", "affected parents", "st",
         ["review-signal.schema.json"],
         "Queue affected parents for rollup review (same lifecycle as the original update)."),
    Node("RCR", COL[4] - 200, ROW["bot"], "Recent-Change Registry", "what changed recently", "st",
         ["recent-change-entry.schema.json"],
         "Access surface over accepted commits for human/agent review. Not the source of truth."),
    Node("FED", COL[5], ROW["bot"], "Federation Pack", "governed cross-instance reads", "fed",
         ["instance-federation-pack.schema.json"],
         "Governed cross-instance reads; local_materialization=false by default. No raw data sync."),
    Node("PKG", COL[6], ROW["bot"], "Context Packager", "bounded projection", "pkg",
         ["context-package.schema.json"],
         "Bounded projection: persona-scoped, freshness-stamped, with excluded-context summaries."),
    Node("AGP", COL[7], ROW["sub"], "Instance Agent Package", "routes · tools · gaps", "pkg",
         ["instance-agent-package.schema.json", "question-route-contract.schema.json"],
         "Primary agent packet: routes, source readiness, tool/action refs, freshness gaps, governance."),
    Node("CON", COL[7], ROW["bot"], "Consumers", "agents · apps · CLI · reports", "acc",
         ["north-star-answer.schema.json"],
         "Agents, apps, CLI, reports read rendered artifacts. They never scrape the runtime root."),
]
N = {n.id: n for n in NODES}

EDGES = [
    ("SRC", "PRE", "source events", "flow"),
    ("SRC", "FRE", "probe", "fwd"),
    ("PRE", "EVT", "reachable ✓", "flow"),
    ("FRE", "EVT", "recent ✓", "flow"),
    ("MEM", "EVT", "memory refs", "fwd"),
    ("PSN", "MOD", "persona / facet", "fwd"),
    ("EVT", "MOD", "evidence packet", "flow"),
    ("MOD", "GOV", "journal proposal", "flow"),
    ("GOV", "JRN", "✓ append (immutable)", "ok"),
    ("JRN", "SNP", "materialize", "flow"),
    ("SNP", "ROL", "queue parents", "flow"),
    ("ROL", "MOD", "rollup review", "flow"),
    ("GOV", "MOD", "✗ rejected · ⏳ pending · ∅ no-op", "dashed", "gov_back"),
    ("MEM", "GOV", "promote (governed)", "dashed"),
    ("SNP", "RCR", "index", "fwd"),
    ("SNP", "PKG", "project", "flow"),
    ("FRE", "PKG", "freshness metadata", "fwd"),
    ("PKG", "AGP", "render · pressure-test ✓", "flow"),
    ("AGP", "CON", "read model", "flow"),
    ("FED", "PKG", "governed query", "bi"),
]


def border(c, p):
    dx, dy = p[0] - c[0], p[1] - c[1]
    tx = HW / abs(dx) if dx else 1e9
    ty = HH / abs(dy) if dy else 1e9
    t = min(tx, ty)
    return (c[0] + dx * t, c[1] + dy * t)


def straight(a, b):
    return border((a.cx, a.cy), (b.cx, b.cy)), border((b.cx, b.cy), (a.cx, a.cy))


def midpoint(p, q):
    return ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)


def _tooltip(nd: Node) -> str:
    """Native SVG <title> text: schemas · responsibility."""
    sch = ", ".join(nd.schemas)
    return f"{sch} — {nd.resp}" if sch else nd.resp


# ---------- SVG-internal CSS (shared by page + standalone) ----------
SVG_STYLE = """
.node{cursor:default}
.node:hover rect{stroke-width:2.6;filter:drop-shadow(0 2px 5px rgba(0,0,0,.12))}
.ntitle{font-size:14px;font-weight:800;letter-spacing:-.005em}
.nsub{font-size:10.5px;fill:#5b6572}
.ntag{font-size:8.5px;letter-spacing:.1em;text-transform:uppercase;fill:#9aa4b0;font-weight:700}
.edge{fill:none;stroke-width:1.8}
.edge.fwd{stroke:#5b6572}
.edge.flow{stroke:#1f8a5b;stroke-width:2.3;stroke-dasharray:9 6;animation:ants 1.05s linear infinite}
.edge.ok{stroke:#1f8a5b;stroke-width:2.4}
.edge.dashed{stroke:#b33a3a;stroke-dasharray:6 5}
.edge.bi{stroke:#2767b1;stroke-dasharray:2 5;stroke-width:2}
.elabel{font-size:11px;font-weight:700;fill:#39434f;paint-order:stroke;stroke:#f7f8fa;stroke-width:4;stroke-linejoin:round}
@keyframes ants{to{stroke-dashoffset:-15}}
@media (prefers-reduced-motion:reduce){.edge.flow{animation:none;stroke-dasharray:none}}
"""


def defs() -> str:
    return """
    <defs>
      <marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#5b6572"/></marker>
      <marker id="ah-flow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#1f8a5b"/></marker>
      <marker id="ah-ok" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#1f8a5b"/></marker>
      <marker id="ah-dash" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#b33a3a"/></marker>
      <marker id="ah-bi" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#2767b1"/></marker>
    </defs>"""


def body() -> str:
    out = []
    out.append('<rect x="455" y="252" width="855" height="316" rx="26" '
               'fill="#e6f4ee" fill-opacity="0.45" stroke="#1f8a5b" '
               'stroke-opacity="0.30" stroke-dasharray="3 7"/>')
    out.append('<text x="882" y="244" text-anchor="middle" '
               'fill="#155f3f" font-size="13" font-weight="800" '
               'letter-spacing="1.5">⟳ UPDATE LIFECYCLE — model interprets, code commits, journal is truth</text>')

    for e in EDGES:
        a, b = N[e[0]], N[e[1]]
        label, style = e[2], e[3]
        variant = e[4] if len(e) > 4 else None
        if variant == "gov_back":
            f = border((a.cx, a.cy), (a.cx - 20, a.cy - 110))
            t = border((b.cx, b.cy), (b.cx + 20, b.cy - 110))
            cx, cy = ((a.cx + b.cx) / 2), 215
            d = f'M{f[0]:.0f},{f[1]:.0f} Q{cx:.0f},{cy} {t[0]:.0f},{t[1]:.0f}'
            cls, mk, (lx, ly) = "edge dashed", "url(#ah-dash)", (cx, cy - 6)
        elif style == "bi":
            f, t = straight(a, b)
            d = f'M{f[0]:.0f},{f[1]:.0f} L{t[0]:.0f},{t[1]:.0f}'
            cls, mk = "edge bi", "url(#ah-bi)"
            lx, ly = midpoint(f, t)
        else:
            f, t = straight(a, b)
            d = f'M{f[0]:.0f},{f[1]:.0f} L{t[0]:.0f},{t[1]:.0f}'
            cls = {"flow": "edge flow", "ok": "edge ok", "fwd": "edge fwd"}.get(style, "edge dashed")
            mk = {"flow": "url(#ah-flow)", "ok": "url(#ah-ok)", "fwd": "url(#ah)"}.get(style, "url(#ah-dash)")
            lx, ly = midpoint(f, t)
        out.append(f'<path d="{d}" class="{cls}" marker-end="{mk}"/>')
        out.append(f'<text x="{lx:.0f}" y="{ly:.0f}" text-anchor="middle" class="elabel">{html.escape(label)}</text>')

    for nd in NODES:
        fill, stroke, tcol, tag = KIND[nd.kind]
        x, y = nd.cx - HW, nd.cy - HH
        tip = html.escape(_tooltip(nd))
        out.append('<g class="node">')
        out.append(f'<title>{tip}</title>')
        out.append(f'<rect x="{x}" y="{y}" width="{HW*2}" height="{HH*2}" rx="13" '
                   f'fill="{fill}" stroke="{stroke}" stroke-width="1.6"/>')
        out.append(f'<text x="{nd.cx}" y="{nd.cy-8}" text-anchor="middle" class="ntitle" fill="{tcol}">{html.escape(nd.title)}</text>')
        out.append(f'<text x="{nd.cx}" y="{nd.cy+11}" text-anchor="middle" class="nsub">{html.escape(nd.sub)}</text>')
        out.append(f'<text x="{nd.cx}" y="{y+HH*2+13}" text-anchor="middle" class="ntag">{html.escape(tag)}</text>')
        out.append('</g>')
    return "\n".join(out)


def svg_markup(standalone: bool) -> str:
    """Full <svg>...</svg>. If standalone, embed SVG_STYLE + a font-family on the root."""
    font = ' font-family="Inter, ui-sans-serif, system-ui, -apple-system, sans-serif"'
    style = f'<style>{SVG_STYLE}</style>' if standalone else ""
    return (f'<svg viewBox="0 0 1540 770" xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="State System data-flow network" class="diagram"{font if standalone else ""}>'
            f'{style}{defs()}{body()}</svg>')


PAGE_CSS = """
*{box-sizing:border-box}
body{margin:0;background:#f7f8fa;color:#17202a;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.5}
.wrap{max-width:1560px;margin:0 auto;padding:26px 28px 70px}
header.h{display:flex;align-items:flex-start;gap:22px;flex-wrap:wrap;margin-bottom:14px}
header.h .t1{font-size:13px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:#6f4bb2}
header.h h1{margin:1px 0 4px;font-size:24px;font-weight:800;letter-spacing:-.01em}
header.h .sub{font-size:13.5px;color:#5b6572;max-width:760px}
.legend{display:flex;gap:6px;flex-wrap:wrap;margin-left:auto;align-items:flex-start}
.lg{display:inline-flex;align-items:center;gap:6px;font-size:11.5px;font-weight:600;color:#41506a;background:#fff;border:1px solid #cfd7df;border-radius:999px;padding:4px 10px}
.lg i{width:11px;height:11px;border-radius:3px;display:inline-block}
.lg .ln{width:18px;height:0;border-top:2.5px solid;display:inline-block;border-radius:2px}
.tip{font-size:12px;color:#5b6572;margin:-6px 0 16px}
.cap{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:8px 0 18px}
.cap .c{background:#fff;border:1px solid #cfd7df;border-left:5px solid #6f4bb2;border-radius:11px;padding:12px 16px}
.cap .c.ans{border-left-color:#1f8a5b}
.cap .c h3{margin:0 0 4px;font-size:14px;font-weight:800}
.cap .c p{margin:0;font-size:13px;color:#39434f}
.frame{background:#fff;border:1px solid #cfd7df;border-radius:16px;padding:14px;box-shadow:0 1px 0 rgba(0,0,0,.02);overflow-x:auto}
.diagram{width:100%;height:auto;display:block}
footer.f{margin-top:26px;padding-top:16px;border-top:1px solid #cfd7df;font-size:12px;color:#5b6572;display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.92em;background:#eef1f4;padding:1px 5px;border-radius:4px;color:#27405c}
@media print{@page{size:A3 landscape;margin:10mm}body{background:#fff}.frame{break-inside:avoid}}
""" + SVG_STYLE  # page gets both page + svg classes


def html_page() -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>State System — Data-Flow Network</title>
<style>{PAGE_CSS}</style>
</head>
<body>
<div class="wrap">
  <header class="h">
    <div>
      <span class="t1">Data-Flow Network</span>
      <h1>State System — how a signal becomes a trustworthy answer</h1>
      <p class="sub">Node-and-edge view of the ingestion pipeline, the update-lifecycle cycle (the central loop), and the read/answer path — with feedback, governance, memory, and federation edges. Follow the <b>green</b> marching-ants for the primary flow.</p>
    </div>
    <div class="legend" aria-label="legend">
      <span class="lg"><i style="background:#e6f0fb"></i>source/evidence</span>
      <span class="lg"><i style="background:#efe9fb"></i>model</span>
      <span class="lg"><i style="background:#f9e7e7"></i>governance</span>
      <span class="lg"><i style="background:#e6f4ee"></i>state kernel</span>
      <span class="lg"><i style="background:#fff3d8"></i>memory/packaging</span>
      <span class="lg"><i style="background:#edf0f3"></i>access</span>
      <span class="lg"><span class="ln" style="border-color:#1f8a5b"></span>primary flow</span>
      <span class="lg"><span class="ln" style="border-color:#b33a3a;border-top-style:dashed"></span>feedback/conditional</span>
      <span class="lg"><span class="ln" style="border-color:#2767b1;border-top-style:dashed"></span>governed/federated</span>
    </div>
  </header>

  <p class="tip">Hover any node for its schema name(s) and one-line responsibility.</p>

  <div class="cap">
    <div class="c">
      <h3>Write path — the update lifecycle (green loop)</h3>
      <p>A source event is deduped; preflight + freshness prove access and recency; the model interprets the evidence packet and emits a <b>journal proposal</b>; the governance gate commits an <b>immutable</b> journal entry; the snapshot is materialized; rollups queue back into the interpreter. Corrections are new entries — full replay is always possible.</p>
    </div>
    <div class="c ans">
      <h3>Read path — the answer pipeline (right)</h3>
      <p>Snapshots (+ memory + freshness metadata) are projected into a bounded <b>context package</b>, pressure-tested for answerability, rendered as an <b>instance agent package</b>, and consumed as a read model. Federation adds governed cross-instance reads — no raw materialization by default.</p>
    </div>
  </div>

  <div class="frame">
{svg_markup(standalone=False)}
  </div>

  <footer class="f">
    <span><b>State System</b> · Data-flow network. Hover nodes for schemas + responsibilities. Cycle backdrop marks the update lifecycle.</span>
    <span>Companions: <code>state-system-architecture.html</code> (layers) · <code>state-system-deck.html</code> (narrative) · <code>system-diagram.html</code> (orientation)</span>
  </footer>
</div>
</body>
</html>
"""


def main():
    root = Path(__file__).resolve().parent.parent
    html_out = root / "docs" / "state-system-network-flow.html"
    svg_out = root / "docs" / "assets" / "state-system-network-flow.svg"
    html_out.write_text(html_page(), encoding="utf-8")
    svg_out.write_text(svg_markup(standalone=True), encoding="utf-8")
    print(f"wrote {html_out} ({html_out.stat().st_size} bytes)")
    print(f"wrote {svg_out} ({svg_out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
