"""Render a standalone leaderboard.html from a V1 results document.

The output is one self-contained file: inline CSS, inline data, no CDN, no
JavaScript, no build step. It opens directly from the filesystem.
"""

from __future__ import annotations

import html
from pathlib import Path

from src import config


def _escape(value) -> str:
    return html.escape("" if value is None else str(value))


def _score(value) -> str:
    return f"{value:.2f}" if isinstance(value, (int, float)) else "n/a"


def _number(value) -> str:
    return f"{value:,}" if isinstance(value, (int, float)) else "n/a"


def _ms(value) -> str:
    return f"{value:,.0f} ms" if isinstance(value, (int, float)) else "n/a"


def _cny(value) -> str:
    return f"¥{value:,.4f}" if isinstance(value, (int, float)) else "unpriced"


def render(document: dict, *, banner: str | None = None) -> str:
    summary = document["summary"]
    model_rows = summary["models"]
    overhead = summary["judge_overhead"]
    pareto = summary.get("pareto", {})
    dataset = document.get("dataset", {})
    pool = document.get("model_pool", {})
    pricing_snapshot = document.get("pricing_snapshot", {})
    fx = pricing_snapshot.get("fx_snapshot") or {}

    leaderboard_rows = []
    for row in model_rows:
        domain_cells = "".join(
            f"<td class='num'>{_score(row['dimension_scores'].get(dimension))}</td>"
            for dimension in config.RUBRIC_DIMENSIONS
        )
        flags = []
        if row.get("pareto_quality_cost"):
            flags.append("<span class='pill ok'>Q×C</span>")
        if row.get("pareto_quality_cost_latency"):
            flags.append("<span class='pill ok'>Q×C×L</span>")
        if row.get("dominated_by"):
            flags.append(
                f"<span class='pill muted-pill'>beaten by {_escape(row['dominated_by'])}</span>"
            )
        leaderboard_rows.append(
            "<tr>"
            f"<td class='rank'>{row['rank']}</td>"
            f"<td class='model'>{_escape(row['model_name'])}"
            f"<span class='model-id'>{_escape(row['model_id'] or 'model ID unverified')}"
            f" · {_escape(row['provider'])} · {_escape(row['product_tier'])}</span></td>"
            f"<td class='num score'>{_score(row['overall_score'])}</td>"
            f"{domain_cells}"
            f"<td class='num'>{_score(row['constraint_pass_rate'])}</td>"
            f"<td class='num'>{_ms(row['latency']['p50_latency_ms'])}</td>"
            f"<td class='num'>{_ms(row['latency']['p95_latency_ms'])}</td>"
            f"<td class='num'>{_cny(row['cost_per_100_tasks_cny'])}</td>"
            f"<td class='num'>{_number(row['tokens']['total'])}</td>"
            f"<td class='flags'>{' '.join(flags) or '—'}</td>"
            "</tr>"
        )

    model_headers = "".join(
        f"<th class='num'>{_escape(row['model_name'])}</th>" for row in model_rows
    )
    case_ids = sorted({row["case_id"] for row in document["results"]})
    case_rows = []
    for case_id in case_ids:
        case_results = [row for row in document["results"] if row["case_id"] == case_id]
        first = case_results[0]
        cells = []
        for model in model_rows:
            match = next(
                (row for row in case_results if row["model_key"] == model["model_key"]), None
            )
            aggregate = match.get("aggregate") if match else None
            if not aggregate or aggregate.get("quality_score") is None:
                cells.append("<td class='num muted'>n/a</td>")
            else:
                constraint = (
                    f"{match['deterministic']['constraint_pass_rate']:.2f}"
                    if match.get("deterministic")
                    and match["deterministic"]["constraint_pass_rate"] is not None
                    else "—"
                )
                cells.append(
                    f"<td class='num'>{aggregate['quality_score']:.1f} "
                    f"<span class='muted'>/ {aggregate['overall_score']:.0f} · c:{constraint}</span></td>"
                )
        case_rows.append(
            f"<tr><td class='mono'>{_escape(case_id)}</td>"
            f"<td class='muted'>{_escape(config.DOMAIN_SHORT_LABELS.get(first['domain'], first['domain']))}</td>"
            f"<td class='muted'>{_escape(first.get('difficulty'))}</td>"
            f"<td class='muted'>{_escape(first.get('language'))}</td>{''.join(cells)}</tr>"
        )

    dimension_list = "".join(
        f"<li><code>{_escape(dimension)}</code></li>" for dimension in config.RUBRIC_DIMENSIONS
    )
    domain_list = "".join(
        f"<li><code>{_escape(domain)}</code> — "
        f"{dataset.get('domain_distribution', {}).get(domain, 0)} case(s)</li>"
        for domain in config.DOMAINS
    )
    judge_list = "".join(
        f"<li>{_escape(judge['display_name'])} "
        f"<span class='muted'>({_escape(judge['model_family'])}, {_escape(judge['provider'])})</span></li>"
        for judge in pool.get("judge_pool", [])
    )

    if fx.get("fx_rate"):
        fx_note = (
            f"FX snapshot {_escape(fx.get('fx_pair'))} = {_escape(fx.get('fx_rate'))} "
            f"on {_escape(fx.get('fx_snapshot_date'))} ({_escape(fx.get('status'))})."
        )
    else:
        fx_note = (
            "No FX snapshot is configured, so models priced in a non-CNY currency have no "
            "CNY value. Costs are never converted silently."
        )

    synthetic_notice = ""
    if document.get("synthetic"):
        synthetic_notice = (
            '<div class="banner">SYNTHETIC DRY-RUN — every number on this page was generated '
            "offline. Synthetic pricing and FX fixtures are placeholders, not published values.</div>"
        )
    elif banner:
        synthetic_notice = f'<div class="banner">{_escape(banner)}</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AIProductBench CN V1 — Leaderboard</title>
<style>
  :root {{
    --ink: #14161a; --muted: #6b7280; --line: #e5e7eb; --bg: #ffffff;
    --soft: #f7f8fa; --ok: #0f7b3f; --okbg: #e8f6ee;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--bg); color: var(--ink);
    font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
  main {{ max-width: 1120px; margin: 0 auto; padding: 48px 24px 72px; }}
  h1 {{ font-size: 28px; margin: 0 0 4px; letter-spacing: -0.01em; }}
  h2 {{ font-size: 17px; margin: 40px 0 12px; letter-spacing: -0.01em; }}
  p {{ margin: 0 0 10px; }}
  .lede {{ color: var(--muted); margin-bottom: 4px; }}
  .meta {{ color: var(--muted); font-size: 13px; }}
  .banner {{ margin: 20px 0; padding: 12px 14px; border: 1px solid #f0c36d;
    background: #fff8e6; border-radius: 6px; font-size: 13px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
  th, td {{ text-align: left; padding: 9px 8px; border-bottom: 1px solid var(--line); }}
  th {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); font-weight: 600; }}
  td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  td.rank {{ width: 30px; color: var(--muted); }}
  td.score {{ font-weight: 600; }}
  .model-id {{ display: block; font-size: 11px; color: var(--muted);
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
  .muted {{ color: var(--muted); }}
  .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13px; }}
  table.cases td, table.cases th {{ padding: 6px 8px; font-size: 13px; }}
  .pill {{ display: inline-block; padding: 1px 6px; border-radius: 10px; font-size: 11px; }}
  .pill.ok {{ background: var(--okbg); color: var(--ok); }}
  .muted-pill {{ background: var(--soft); color: var(--muted); }}
  code {{ background: var(--soft); border: 1px solid var(--line); border-radius: 4px; padding: 1px 5px; font-size: 12px; }}
  ul {{ margin: 6px 0 0; padding-left: 20px; }}
  li {{ margin-bottom: 4px; }}
  footer {{ margin-top: 44px; padding-top: 16px; border-top: 1px solid var(--line);
    color: var(--muted); font-size: 12px; }}
</style>
</head>
<body>
<main>
  <h1>AIProductBench CN V1</h1>
  <p class="lede">Model selection for Chinese LLMs under real quality, cost, and latency constraints.</p>
  <p class="meta">
    Snapshot {_escape(document.get('snapshot_id'))} · generated {_escape(document.get('generated_at'))} (UTC) ·
    dataset {_escape(dataset.get('name'))} ({_escape(dataset.get('version'))}, {_escape(dataset.get('case_count'))} cases) ·
    {len(model_rows)} candidate models · {overhead['judge_calls']} judge calls
  </p>
  {synthetic_notice}

  <h2>Leaderboard</h2>
  <table>
    <thead>
      <tr>
        <th>#</th><th>Model</th><th class="num">Overall</th>
        <th class="num">Task</th><th class="num">Reasoning</th><th class="num">Instruction</th>
        <th class="num">Constraints</th><th class="num">P50</th><th class="num">P95</th>
        <th class="num">CNY / 100 tasks</th><th class="num">Tokens</th><th>Pareto</th>
      </tr>
    </thead>
    <tbody>
      {''.join(leaderboard_rows)}
    </tbody>
  </table>
  <p class="meta">Overall is the equal-weight mean of the three rubric dimensions, normalised to 0-100.
  Constraints is the deterministic check pass rate. Cost is candidate inference cost only;
  judge cost is reported separately below.</p>

  <h2>Score per test case</h2>
  <p class="meta">Each cell shows the judge mean score (1-5), the normalised score (0-100), and the
  deterministic constraint pass rate. Scores are the average of two cross-family judges.</p>
  <table class="cases">
    <thead>
      <tr><th>Case</th><th>Domain</th><th>Difficulty</th><th>Language</th>{model_headers}</tr>
    </thead>
    <tbody>
      {''.join(case_rows)}
    </tbody>
  </table>

  <h2>Pareto analysis</h2>
  <p>Selection is presented as a frontier rather than a single ranking. A model is on the frontier when
  no other model is at least as good on every objective and strictly better on one. Models that are never
  the right choice under any constraint are marked as dominated and name the model that beats them.</p>
  <ul>
    <li>Quality × Cost frontier: {_escape(', '.join(pareto.get('quality_cost', {}).get('frontier') or []) or 'n/a')}</li>
    <li>Quality × Cost × Latency frontier: {_escape(', '.join(pareto.get('quality_cost_latency', {}).get('frontier') or []) or 'n/a')}</li>
  </ul>

  <h2>Judge overhead</h2>
  <p class="meta">
    {_escape(overhead['judge_calls'])} judge calls across
    {len(overhead['judge_models_used'])} judge(s) ·
    {_number(overhead['judge_total_tokens']['total'])} tokens ·
    {_cny(overhead['judge_cost_cny'])} evaluation overhead (reported separately from candidate cost)
  </p>
  <p>Judge pool (each response is scored by two judges from families other than the candidate's):</p>
  <ul>{judge_list}</ul>

  <h2>Methodology</h2>
  <p>Every candidate model answers the same cases once. Deterministic checks are evaluated where a constraint
  is objectively machine-checkable, and two cross-family judges score every response against a shared rubric
  plus the case-specific evaluation criteria. Candidate cost and judge cost are tracked separately.</p>
  <p>Rubric dimensions:</p>
  <ul>{dimension_list}</ul>
  <p style="margin-top:10px">Capability domains:</p>
  <ul>{domain_list}</ul>
  <p class="meta" style="margin-top:10px">{fx_note}</p>

  <h2>Known limitations</h2>
  <ul>
    <li>Two judges from other families reduce judge-family bias but cannot eliminate it.</li>
    <li>Case counts and model counts are small relative to the claims a ranking usually invites.</li>
    <li>Costs use a dated manual pricing snapshot, not a live billing feed.</li>
    <li>Models whose API model ID is not a dated snapshot are not reproducible against the same weights.</li>
    <li>Latency depends on provider load, region, and network path and is not a controlled measurement.</li>
  </ul>

  <footer>
    AIProductBench CN · {_escape(document.get('benchmark_version'))} · snapshot
    {_escape(document.get('snapshot_id'))} · see docs/METHODOLOGY_V1.md for the frozen evaluation design.
  </footer>
</main>
</body>
</html>
"""


def write(document: dict, path: Path, *, banner: str | None = None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(render(document, banner=banner))
    return path


def has_external_references(path: Path) -> bool:
    """True when the generated HTML references an external asset."""
    text = Path(path).read_text(encoding="utf-8")
    return "http://" in text or "https://" in text or "<script" in text
