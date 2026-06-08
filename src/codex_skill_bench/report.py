from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


PREVIEW_LIMIT = 30_000


def write_html_report(results_dir: Path, summary: dict[str, Any]) -> Path:
    results_dir = results_dir.resolve()
    report_path = results_dir / "report.html"
    report_data = build_report_data(results_dir, summary)
    report_path.write_text(render_html(report_data), encoding="utf-8")
    return report_path


def build_report_data(results_dir: Path, summary: dict[str, Any]) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    totals = {"passed": 0, "failed": 0, "errored": 0, "flaky": 0, "skipped": 0, "unknown": 0}

    for fixture_id, fixture in summary.get("fixtures", {}).items():
        for case_id, case in fixture.get("cases", {}).items():
            for model_id, model in case.get("models", {}).items():
                variants = model.get("variants", {})
                status = aggregate_status(
                    variant.get("aggregate", {}).get("status", "unknown") for variant in variants.values()
                )
                totals[status if status in totals else "unknown"] += 1
                case_record = {
                    "id": f"{fixture_id} / {case_id} / {model_id}",
                    "fixture": fixture_id,
                    "case": case_id,
                    "model": model_id,
                    "status": status,
                    "variants": {},
                    "comparisons": [
                        comparison
                        for comparison in summary.get("comparisons", [])
                        if comparison.get("fixture") == fixture_id
                        and comparison.get("case") == case_id
                        and comparison.get("model") == model_id
                    ],
                    "comparisonImprovements": [],
                }
                for variant_id, variant in variants.items():
                    case_record["variants"][variant_id] = enrich_variant(results_dir, variant)
                case_record["comparisonImprovements"] = build_improvements(case_record)
                cases.append(case_record)

    return {
        "generatedBy": "codex-skill-bench",
        "schemaVersion": 1,
        "summary": {"totals": totals, "caseCount": len(cases), "comparisonCount": len(summary.get("comparisons", []))},
        "cases": cases,
        "raw": {
            "summaryYaml": yaml.safe_dump(summary, sort_keys=False, allow_unicode=True),
            "summaryJson": summary,
        },
    }


def aggregate_status(statuses: Any) -> str:
    order = ["errored", "failed", "flaky", "skipped", "unknown", "passed"]
    seen = set(statuses)
    for status in order:
        if status in seen:
            return status
    return "unknown"


def enrich_variant(results_dir: Path, variant: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(variant)
    enriched["attempts"] = [enrich_attempt(results_dir, attempt) for attempt in variant.get("attempts", [])]
    return enriched


def enrich_attempt(results_dir: Path, attempt: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(attempt)
    artifacts = dict(attempt.get("artifacts") or {})
    enriched["artifactLinks"] = {name: artifact_link(results_dir, raw) for name, raw in artifacts.items() if raw}
    enriched["artifactPreviews"] = {
        "resultYaml": read_preview(artifacts.get("result")),
        "final": read_preview(artifacts.get("final")),
        "stderr": read_preview(artifacts.get("stderr")),
        "events": read_preview(artifacts.get("events")),
        "preloadFinal": read_preview(artifacts.get("preloadFinal")),
        "preloadStderr": read_preview(artifacts.get("preloadStderr")),
        "preloadEvents": read_preview(artifacts.get("preloadEvents")),
    }
    enriched["eventItems"] = read_event_items(artifacts.get("events"))
    enriched["preloadEventItems"] = read_event_items(artifacts.get("preloadEvents"))
    return enriched


def build_improvements(case_record: dict[str, Any]) -> list[dict[str, Any]]:
    variants = case_record.get("variants", {})
    baseline_name = "no-skill" if "no-skill" in variants else ""
    if not baseline_name:
        for name, variant in variants.items():
            if variant.get("variantKind") == "control":
                baseline_name = str(name)
                break
    if not baseline_name:
        return []
    control = variants.get(baseline_name, {})
    skill_names = [
        str(name)
        for name, variant in variants.items()
        if variant.get("variantKind") == "skill" and str(name) != baseline_name
    ]
    improvements: list[dict[str, Any]] = []
    for skill_name in skill_names:
        skill = variants.get(skill_name, {})
        control_aggregate = control.get("aggregate", {})
        skill_aggregate = skill.get("aggregate", {})
        control_usage = control_aggregate.get("usage", {})
        skill_usage = skill_aggregate.get("usage", {})
        preload = skill_aggregate.get("preload") or {}
        improvements.append(
            {
                "skillVariant": skill_name,
                "baselineVariant": baseline_name,
                "status": skill_aggregate.get("status", "unknown"),
                "baselineStatus": control_aggregate.get("status", "unknown"),
                "repeatDurationImprovementMs": int(control_aggregate.get("estimatedRepeatDurationMs", 0) or 0)
                - int(skill_aggregate.get("estimatedRepeatDurationMs", 0) or 0),
                "generationTokenImprovement": int(control_usage.get("totalTokens", 0) or 0)
                - int(skill_usage.get("totalTokens", 0) or 0),
                "preloadDurationMs": int(preload.get("durationMs", 0) or 0),
                "preloadTokens": int((preload.get("usage") or {}).get("totalTokens", 0) or 0),
                "baselineRepeatDurationMs": control_aggregate.get("estimatedRepeatDurationMs"),
                "skillRepeatDurationMs": skill_aggregate.get("estimatedRepeatDurationMs"),
                "baselineTotalTokens": control_usage.get("totalTokens"),
                "skillTotalTokens": skill_usage.get("totalTokens"),
            }
        )
    return improvements


def artifact_link(results_dir: Path, raw_path: str) -> dict[str, str]:
    path = Path(raw_path)
    href = raw_path
    if path.is_absolute():
        try:
            href = path.relative_to(results_dir).as_posix()
        except ValueError:
            href = path.as_uri()
    return {"path": raw_path, "href": href}


def read_preview(raw_path: str | None) -> dict[str, Any]:
    if not raw_path:
        return {"available": False, "text": "", "truncated": False}
    path = Path(raw_path)
    if not path.exists() or not path.is_file():
        return {"available": False, "text": "", "truncated": False}
    text = path.read_text(encoding="utf-8", errors="replace")
    truncated = len(text) > PREVIEW_LIMIT
    return {"available": True, "text": text[:PREVIEW_LIMIT], "truncated": truncated, "bytes": path.stat().st_size}


def read_event_items(raw_path: str | None) -> list[dict[str, Any]]:
    if not raw_path:
        return []
    path = Path(raw_path)
    if not path.exists() or not path.is_file():
        return []
    items: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                items.append({"line": line_no, "type": "invalid-json", "summary": line.strip(), "raw": line.strip()})
                continue
            items.extend(flatten_event(line_no, event))
    return items


def flatten_event(line_no: int, event: dict[str, Any]) -> list[dict[str, Any]]:
    flattened = [event_item(line_no, event)]
    for index, item in enumerate(event.get("items") or [], start=1):
        if isinstance(item, dict):
            flattened.append(event_item(line_no, item, index=index))
    return flattened


def event_item(line_no: int, event: dict[str, Any], index: int | None = None) -> dict[str, Any]:
    event_type = str(event.get("type") or "event")
    summary = event_summary(event)
    return {
        "line": line_no,
        "index": index,
        "type": event_type,
        "status": event.get("status"),
        "phase": event.get("phase"),
        "summary": summary,
        "raw": json.dumps(event, ensure_ascii=False, indent=2),
    }


def event_summary(event: dict[str, Any]) -> str:
    for key in ("final_response", "text", "aggregatedOutput", "command"):
        value = event.get(key)
        if isinstance(value, str) and value.strip():
            return compact_text(value)
    content = event.get("content")
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        if parts:
            return compact_text(" ".join(parts))
    if "usage" in event:
        return "usage: " + compact_text(json.dumps(event["usage"], ensure_ascii=False))
    return compact_text(json.dumps(event, ensure_ascii=False))


def compact_text(value: str, limit: int = 220) -> str:
    compacted = " ".join(value.split())
    return compacted[: limit - 1] + "…" if len(compacted) > limit else compacted


def render_html(report_data: dict[str, Any]) -> str:
    data_json = json.dumps(report_data, ensure_ascii=False)
    escaped_json = escape_json_for_script(data_json)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Codex Skill Bench Report</title>
<style>
:root {{
  color-scheme: light;
  --bg: #f7f8fa;
  --panel: #ffffff;
  --text: #1f2933;
  --muted: #627386;
  --line: #d8dee7;
  --pass: #16784a;
  --fail: #b42318;
  --error: #8a2c0d;
  --skip: #58677a;
  --accent: #0f5f8f;
  --warn: #9a6700;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  min-height: 100vh;
  font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: var(--bg);
  color: var(--text);
}}
.shell {{ display: grid; grid-template-columns: 360px 1fr; min-height: 100vh; }}
.sidebar {{ border-right: 1px solid var(--line); background: #fbfcfe; padding: 18px; position: sticky; top: 0; height: 100vh; overflow: auto; }}
.main {{ padding: 24px 28px 48px; overflow: auto; }}
h1 {{ font-size: 20px; margin: 0 0 16px; }}
h2 {{ font-size: 18px; margin: 28px 0 12px; }}
h3 {{ font-size: 15px; margin: 20px 0 10px; }}
.metrics {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-bottom: 16px; }}
.metric {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 12px; }}
.metric b {{ display: block; font-size: 20px; }}
.metric span {{ color: var(--muted); font-size: 12px; }}
.search {{ width: 100%; border: 1px solid var(--line); border-radius: 6px; padding: 9px 10px; margin: 8px 0 12px; font: inherit; }}
.case-list {{ display: grid; gap: 8px; }}
.case-button {{ width: 100%; text-align: left; background: var(--panel); border: 1px solid var(--line); border-left: 5px solid var(--skip); border-radius: 8px; padding: 10px; cursor: pointer; color: inherit; }}
.case-button.active {{ outline: 2px solid #96c7e4; }}
.case-button.passed {{ border-left-color: var(--pass); }}
.case-button.failed {{ border-left-color: var(--fail); }}
.case-button.errored {{ border-left-color: var(--error); }}
.case-title {{ font-weight: 700; line-height: 1.25; }}
.case-meta {{ margin-top: 4px; font-size: 12px; color: var(--muted); overflow-wrap: anywhere; }}
.pill {{ display: inline-flex; align-items: center; border-radius: 999px; padding: 2px 8px; font-size: 12px; font-weight: 700; border: 1px solid currentColor; }}
.pill.passed {{ color: var(--pass); }}
.pill.failed {{ color: var(--fail); }}
.pill.errored {{ color: var(--error); }}
.pill.skipped, .pill.unknown {{ color: var(--skip); }}
.pill.delta-good {{ color: var(--pass); }}
.pill.delta-bad {{ color: var(--fail); }}
.panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 16px; margin-bottom: 14px; }}
table {{ width: 100%; border-collapse: collapse; background: var(--panel); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }}
th, td {{ border-bottom: 1px solid var(--line); padding: 9px 10px; text-align: left; vertical-align: top; font-size: 13px; }}
th {{ background: #eef3f7; color: #344456; }}
tr:last-child td {{ border-bottom: 0; }}
tr.selectable {{ cursor: pointer; }}
tr.selectable:hover {{ background: #f4f8fb; }}
tr.selectable.active {{ background: #e8f3fa; }}
.tabs {{ display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0; }}
.tab {{ border: 1px solid var(--line); border-radius: 6px; padding: 7px 10px; background: #fff; cursor: pointer; }}
.tab.active {{ background: var(--accent); border-color: var(--accent); color: white; }}
pre {{ margin: 0; white-space: pre-wrap; overflow: auto; max-height: 460px; padding: 12px; background: #111827; color: #e5e7eb; border-radius: 8px; font-size: 12px; line-height: 1.45; }}
.artifact-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 8px; }}
.artifact {{ border: 1px solid var(--line); border-radius: 6px; padding: 8px; overflow-wrap: anywhere; background: #fbfcfe; }}
.artifact a {{ color: var(--accent); }}
.event-list {{ display: grid; gap: 8px; }}
.event-item {{ border: 1px solid var(--line); border-radius: 6px; background: #fbfcfe; padding: 9px; }}
.event-head {{ display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-bottom: 6px; }}
.event-summary {{ color: var(--text); font-size: 13px; }}
.button-link {{ display: inline-flex; align-items: center; border: 1px solid var(--accent); color: var(--accent); border-radius: 6px; padding: 7px 10px; text-decoration: none; font-weight: 700; }}
.empty {{ color: var(--muted); }}
@media (max-width: 900px) {{
  .shell {{ grid-template-columns: 1fr; }}
  .sidebar {{ position: static; height: auto; }}
  .metrics {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<script id="report-data" type="application/json">{escaped_json}</script>
<div class="shell">
  <aside class="sidebar">
    <h1>Skill Bench Report</h1>
    <div id="summaryMetrics" class="metrics"></div>
    <input id="search" class="search" placeholder="Filter cases, fixtures, models">
    <div id="caseList" class="case-list"></div>
  </aside>
  <main class="main">
    <section id="detail"></section>
  </main>
</div>
<script>
const report = JSON.parse(document.getElementById('report-data').textContent);
let selectedId = report.cases[0] ? report.cases[0].id : null;
let activeRawKey = 'summaryYaml';
let selectedAttemptKey = null;

function esc(value) {{
  return String(value ?? '').replace(/[&<>"']/g, char => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[char]));
}}
function fmtMs(value) {{
  if (value === null || value === undefined || value === '') return '-';
  const n = Number(value);
  return n >= 1000 ? (n / 1000).toFixed(2) + 's' : n + 'ms';
}}
function fmtNum(value) {{
  if (value === null || value === undefined || value === '') return '-';
  return Number(value).toLocaleString();
}}
function statusPill(status) {{
  return `<span class="pill ${{esc(status || 'unknown')}}">${{esc((status || 'unknown').toUpperCase())}}</span>`;
}}
function deltaPill(value, suffix = '') {{
  const n = Number(value || 0);
  const cls = n >= 0 ? 'delta-good' : 'delta-bad';
  const sign = n > 0 ? '+' : '';
  return `<span class="pill ${{cls}}">${{sign}}${{fmtNum(n)}}${{suffix}}</span>`;
}}

function renderSummary() {{
  const totals = report.summary.totals;
  document.getElementById('summaryMetrics').innerHTML = [
    ['Cases', report.summary.caseCount],
    ['Passed', totals.passed || 0],
    ['Errored', totals.errored || 0],
    ['Comparisons', report.summary.comparisonCount],
    ['Failed', totals.failed || 0],
    ['Skipped', totals.skipped || 0],
  ].map(([label, value]) => `<div class="metric"><b>${{fmtNum(value)}}</b><span>${{esc(label)}}</span></div>`).join('');
}}

function visibleCases() {{
  const q = document.getElementById('search').value.trim().toLowerCase();
  if (!q) return report.cases;
  return report.cases.filter(item => [item.id, item.fixture, item.case, item.model, item.status].join(' ').toLowerCase().includes(q));
}}

function renderCaseList() {{
  const cases = visibleCases();
  document.getElementById('caseList').innerHTML = cases.map(item => `
    <button class="case-button ${{esc(item.status)}} ${{item.id === selectedId ? 'active' : ''}}" data-id="${{esc(item.id)}}">
      <div class="case-title">${{statusPill(item.status)}} ${{esc(item.case)}}</div>
      <div class="case-meta">${{esc(item.fixture)}} / ${{esc(item.model)}}</div>
    </button>
  `).join('') || '<div class="empty">No matching cases.</div>';
  document.querySelectorAll('.case-button').forEach(button => {{
    button.addEventListener('click', () => {{
      selectedId = button.dataset.id;
      activeRawKey = 'summaryYaml';
      selectedAttemptKey = null;
      render();
    }});
  }});
}}

function selectedCase() {{
  return report.cases.find(item => item.id === selectedId) || report.cases[0];
}}

function attemptKey(variantName, index) {{
  return `${{variantName}}:${{index}}`;
}}

function allAttempts(item) {{
  return Object.entries(item.variants).flatMap(([variantName, variant]) => (variant.attempts || []).map((attempt, index) => ({{
    variantName,
    variant,
    attempt,
    index,
    key: attemptKey(variantName, index)
  }})));
}}

function selectedAttempt(item) {{
  const attempts = allAttempts(item);
  if (!attempts.length) return null;
  const selected = attempts.find(entry => entry.key === selectedAttemptKey) || attempts[0];
  selectedAttemptKey = selected.key;
  return selected;
}}

function renderVariantRows(item) {{
  return Object.entries(item.variants).map(([name, variant]) => {{
    const aggregate = variant.aggregate || {{}};
    const usage = aggregate.usage || {{}};
    const preload = aggregate.preload || null;
    const key = attemptKey(name, 0);
    return `<tr class="selectable ${{selectedAttemptKey === key ? 'active' : ''}}" data-attempt-key="${{esc(key)}}">
      <td><b>${{esc(name)}}</b><br><span class="empty">${{esc(variant.variantKind)}}</span></td>
      <td>${{statusPill(aggregate.status)}}</td>
      <td>${{fmtMs(aggregate.durationMs)}}</td>
      <td>${{fmtMs(aggregate.estimatedRepeatDurationMs)}}</td>
      <td>${{fmtNum(usage.totalTokens)}}</td>
      <td>${{fmtNum(usage.inputTokens)}}</td>
      <td>${{fmtNum(usage.cachedInputTokens)}}</td>
      <td>${{fmtNum(usage.outputTokens)}}</td>
      <td>${{preload ? fmtMs(preload.durationMs) + ' / ' + fmtNum((preload.usage || {{}}).totalTokens) + ' tokens' : '-'}}</td>
    </tr>`;
  }}).join('');
}}

function renderComparisonRows(item) {{
  if (!item.comparisonImprovements.length) return '<p class="empty">No no-skill baseline comparison for this case.</p>';
  return `<table><thead><tr><th>Skill</th><th>Baseline</th><th>Status</th><th>Repeated time improvement</th><th>Token improvement</th><th>Repeated time</th><th>Total tokens</th></tr></thead><tbody>
    ${{item.comparisonImprovements.map(c => `<tr>
      <td>${{esc(c.skillVariant)}}</td>
      <td>${{esc(c.baselineVariant)}}</td>
      <td>${{statusPill(c.status)}}</td>
      <td>${{deltaPill(c.repeatDurationImprovementMs, 'ms')}} <span class="empty">(preload +${{fmtMs(c.preloadDurationMs)}})</span></td>
      <td>${{deltaPill(c.generationTokenImprovement, ' tokens')}} <span class="empty">(preload +${{fmtNum(c.preloadTokens)}})</span></td>
      <td>${{fmtMs(c.skillRepeatDurationMs)}} vs ${{fmtMs(c.baselineRepeatDurationMs)}}</td>
      <td>${{fmtNum(c.skillTotalTokens)}} vs ${{fmtNum(c.baselineTotalTokens)}}</td>
    </tr>`).join('')}}
  </tbody></table>`;
}}

function renderArtifacts(attempt) {{
  const links = attempt.artifactLinks || {{}};
  const labels = {{
    workspace: 'Open workspace',
    events: 'Open events',
    final: 'Open final',
    stderr: 'Open stderr',
    preloadEvents: 'Open preload events',
    preloadFinal: 'Open preload final',
    preloadStderr: 'Open preload stderr',
    result: 'Open result YAML',
    materializedSkill: 'Open materialized skill'
  }};
  const entries = Object.entries(links).filter(([name]) => name !== 'runRoot');
  if (!entries.length) return '<p class="empty">No artifacts recorded.</p>';
  return `<div class="artifact-grid">${{entries.map(([name, link]) => `
    <div class="artifact"><a class="button-link" href="${{esc(link.href)}}">${{esc(labels[name] || name)}}</a><div class="case-meta">${{esc(name)}}</div></div>
  `).join('')}}</div>`;
}}

function eventItemsHtml(items) {{
  if (!items || !items.length) return '<p class="empty">No events recorded.</p>';
  return `<div class="event-list">${{items.map((event, index) => `
    <details class="event-item">
      <summary>
        <span class="event-head">
          <span class="pill unknown">#${{esc(event.index || event.line || index + 1)}}</span>
          <b>${{esc(event.type)}}</b>
          ${{event.status ? `<span class="empty">${{esc(event.status)}}</span>` : ''}}
          ${{event.phase ? `<span class="empty">${{esc(event.phase)}}</span>` : ''}}
        </span>
        <span class="event-summary">${{esc(event.summary)}}</span>
      </summary>
      <pre>${{esc(event.raw)}}</pre>
    </details>
  `).join('')}}</div>`;
}}

function rawTabsFor(item, selected) {{
  const tabs = [{{key: 'summaryYaml', label: 'summary.yaml', text: report.raw.summaryYaml}}];
  if (selected) {{
    const previews = selected.attempt.artifactPreviews || {{}};
    Object.entries(previews).forEach(([name, preview]) => {{
      if (preview && preview.available) {{
        tabs.push({{key: `${{selected.variantName}}-${{selected.index}}-${{name}}`, label: name, text: preview.text + (preview.truncated ? '\\n\\n[truncated]' : '')}});
      }}
    }});
  }}
  return tabs;
}}

function renderRawData(item, selected) {{
  const tabs = rawTabsFor(item, selected);
  if (!tabs.find(tab => tab.key === activeRawKey)) activeRawKey = tabs[0].key;
  const active = tabs.find(tab => tab.key === activeRawKey) || tabs[0];
  return `
    <div class="tabs">${{tabs.map(tab => `<button class="tab ${{tab.key === activeRawKey ? 'active' : ''}}" data-raw-key="${{esc(tab.key)}}">${{esc(tab.label)}}</button>`).join('')}}</div>
    <pre>${{esc(active.text)}}</pre>
  `;
}}

function renderDetail() {{
  const item = selectedCase();
  if (!item) {{
    document.getElementById('detail').innerHTML = '<div class="panel empty">No report data.</div>';
    return;
  }}
  const selected = selectedAttempt(item);
  if (!selected) {{
    document.getElementById('detail').innerHTML = '<div class="panel empty">No run attempts for this case.</div>';
    return;
  }}
  document.getElementById('detail').innerHTML = `
    <div class="panel">
      <h2>${{esc(item.case)}} ${{statusPill(item.status)}}</h2>
      <div class="case-meta">${{esc(item.fixture)}} / ${{esc(item.model)}}</div>
    </div>
    <h2>Variants</h2>
    <table>
      <thead><tr><th>Variant</th><th>Status</th><th>Duration</th><th>Repeat estimate</th><th>Total tokens</th><th>Input</th><th>Cached input</th><th>Output</th><th>Preload</th></tr></thead>
      <tbody>${{renderVariantRows(item)}}</tbody>
    </table>
    <h2>Comparison</h2>
    ${{renderComparisonRows(item)}}
    <h2>Selected Result</h2>
    <div class="panel">
      <h3>${{esc(selected.variantName)}} / ${{esc(selected.attempt.id)}}</h3>
      ${{renderArtifacts(selected.attempt)}}
    </div>
    <h2>Events</h2>
    <div class="panel">${{eventItemsHtml(selected.attempt.eventItems)}}</div>
    ${{selected.attempt.preloadEventItems && selected.attempt.preloadEventItems.length ? `<h2>Preload Events</h2><div class="panel">${{eventItemsHtml(selected.attempt.preloadEventItems)}}</div>` : ''}}
    <h2>Raw Data</h2>
    <div class="panel" id="rawPanel">${{renderRawData(item, selected)}}</div>
  `;
  document.querySelectorAll('tr.selectable').forEach(row => {{
    row.addEventListener('click', () => {{
      selectedAttemptKey = row.dataset.attemptKey;
      activeRawKey = 'summaryYaml';
      renderDetail();
    }});
  }});
  document.querySelectorAll('.tab').forEach(button => {{
    button.addEventListener('click', () => {{
      activeRawKey = button.dataset.rawKey;
      document.getElementById('rawPanel').innerHTML = renderRawData(item, selected);
      document.querySelectorAll('.tab').forEach(tab => tab.addEventListener('click', () => {{
        activeRawKey = tab.dataset.rawKey;
        renderDetail();
      }}));
    }});
  }});
}}

function render() {{
  renderSummary();
  renderCaseList();
  renderDetail();
}}
document.getElementById('search').addEventListener('input', renderCaseList);
render();
</script>
</body>
</html>
"""


def escape_json_for_script(data_json: str) -> str:
    return (
        data_json.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
