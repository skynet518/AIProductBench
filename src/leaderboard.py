"""Render a standalone leaderboard.html from a results document.

The output is a single self-contained file: inline CSS, inline data, no CDN,
no JavaScript, no build step. It opens directly from the filesystem.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

from src import config


def _escape(value) -> str:
    return html.escape("" if value is None else str(value))


def _score(value) -> str:
    return f"{value:.2f}" if isinstance(value, (int, float)) else "n/a"


def _number(value) -> str:
    return f"{value:,}" if isinstance(value, int) else "n/a"


def _money(value) -> str:
    return f"${value:.6f}" if isinstance(value, (int, float)) else "unpriced"


def _latency(value) -> str:
    return f"{value:,.0f} ms" if isinstance(value, (int, float)) else "n/a"


def render(document: dict, *, banner: str | None = None) -> str:
    summary = document["summary"]
    models = summary["models"]
    overhead = summary["judge_overhead"]
    pricing = document.get("pricing_snapshot", {})

    rows = []
    for row in models:
        domain_cells = "".join(
            f"<td class='num'>{_score(row['domain_scores'].get(domain))}</td>"
            for domain in config.DOMAINS
        )
        rows.append(
            "<tr>"
            f"<td class='rank'>{row['rank']}</td>"
            f"<td class='model'>{_escape(row['model_name'])}"
            f"<span class='model-id'>{_escape(row['model_id'])}</span></td>"
            f"<td class='num score'>{_score(row['overall_score'])}</td>"
            f"{domain_cells}"
            f"<td class='num'>{_latency(row['avg_latency_ms'])}</td>"
            f"<td class='num'>{_number(row['total_tokens'])}</td>"
            f"<td class='num'>{_money(row['candidate_cost_usd'])}</td>"
            "</tr>"
        )

    model_headers = "".join(
        f"<th class='num'>{_escape(row['model_name'])}</th>" for row in models
    )
    case_ids = sorted({row["case_id"] for row in document["results"]})
    case_rows = []
    for case_id in case_ids:
        case_results = [row for row in document["results"] if row["case_id"] == case_id]
        domain = case_results[0]["domain"] if case_results else ""
        cells = []
        for model in models:
            match = next(
                (row for row in case_results if row["model_key"] == model["model_key"]), None
            )
            verdict = match.get("judge") if match else None
            if verdict is None:
                cells.append("<td class='num muted'>n/a</td>")
            else:
                cells.append(
                    f"<td class='num'>{verdict['mean_score']:.1f} "
                    f"<span class='muted'>/ {verdict['normalized_score']:.0f}</span></td>"
                )
        case_rows.append(
            f"<tr><td class='mono'>{_escape(case_id)}</td>"
            f"<td class='muted'>{_escape(domain)}</td>{''.join(cells)}</tr>"
        )

    dimension_list = "".join(
        f"<li><code>{_escape(dimension)}</code></li>" for dimension in config.RUBRIC_DIMENSIONS
    )
    domain_list = "".join(
        f"<li><code>{_escape(domain)}</code> — {count} case(s)</li>"
        for domain, count in document.get("domain_distribution", {}).items()
    )

    sources = pricing.get("sources") or []
    if pricing.get("verified"):
        pricing_note = (
            f"Costs use the {_escape(pricing.get('date'))} pricing snapshot "
            f"(official list pricing only), sourced from "
            f"{_escape('; '.join(sources))}."
        )
    else:
        pricing_note = (
            "Pricing snapshot is unverified, so cost columns render as “unpriced”. "
            "AIProductBench never fabricates pricing."
        )

    repro = document.get("reproducibility") or {}
    if repro:
        reproducibility_line = (
            "<p class=\"meta\">Reproducibility: Qwen 3.7 Flash snapshot "
            f"{_escape(repro.get('qwen_candidate_snapshot'))} · Qwen 3.7 Max judge snapshot "
            f"{_escape(repro.get('qwen_judge_snapshot'))} · DeepSeek API model ID "
            f"{_escape(repro.get('deepseek_api_model_id'))} "
            f"(documented version {_escape(repro.get('deepseek_documented_model_version'))}, "
            "not date-pinned).</p>"
        )
    else:
        reproducibility_line = ""

    synthetic_notice = ""
    if document.get("synthetic"):
        synthetic_notice = (
            '<div class="banner">SYNTHETIC DRY-RUN — every number on this page was '
            "generated offline and does not come from a real model.</div>"
        )
    elif banner:
        synthetic_notice = f'<div class="banner">{_escape(banner)}</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AIProductBench V0.1 — Leaderboard</title>
<style>
  :root {{
    --ink: #14161a; --muted: #6b7280; --line: #e5e7eb; --bg: #ffffff;
    --accent: #1f6feb; --soft: #f7f8fa;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--bg); color: var(--ink);
    font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
  main {{ max-width: 980px; margin: 0 auto; padding: 48px 24px 72px; }}
  h1 {{ font-size: 28px; margin: 0 0 4px; letter-spacing: -0.01em; }}
  h2 {{ font-size: 17px; margin: 40px 0 12px; letter-spacing: -0.01em; }}
  p {{ margin: 0 0 10px; }}
  .lede {{ color: var(--muted); margin-bottom: 4px; }}
  .meta {{ color: var(--muted); font-size: 13px; }}
  .banner {{ margin: 20px 0; padding: 12px 14px; border: 1px solid #f0c36d;
    background: #fff8e6; border-radius: 6px; font-size: 13px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
  th, td {{ text-align: left; padding: 9px 10px; border-bottom: 1px solid var(--line); }}
  th {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); font-weight: 600; }}
  td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  td.rank {{ width: 34px; color: var(--muted); }}
  td.score {{ font-weight: 600; }}
  .model-id {{ display: block; font-size: 11px; color: var(--muted); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
  .muted {{ color: var(--muted); }}
  .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13px; }}
  table.cases td, table.cases th {{ padding: 6px 10px; font-size: 13px; }}
  code {{ background: var(--soft); border: 1px solid var(--line); border-radius: 4px; padding: 1px 5px; font-size: 12px; }}
  ul {{ margin: 6px 0 0; padding-left: 20px; }}
  li {{ margin-bottom: 4px; }}
  footer {{ margin-top: 44px; padding-top: 16px; border-top: 1px solid var(--line);
    color: var(--muted); font-size: 12px; }}
</style>
</head>
<body>
<main>
  <h1>AIProductBench V0.1</h1>
  <p class="lede">A lightweight, practical comparison of LLMs on AI product work — not a scientific benchmark.</p>
  <p class="meta">
    Generated {_escape(document['generated_at'])} (UTC) · benchmark v{_escape(document['benchmark_version'])} ·
    {_escape(document['test_case_count'])} test cases ·
    {len(models)} evaluated models · judge: {_escape(document['judge']['display_name'])}
  </p>
  {synthetic_notice}

  <h2>Leaderboard</h2>
  <table>
    <thead>
      <tr>
        <th>#</th><th>Model</th><th class="num">Overall</th>
        <th class="num">Instruction</th><th class="num">Product</th><th class="num">Structured</th>
        <th class="num">Avg latency</th><th class="num">Tokens</th><th class="num">Cost</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
  <p class="meta">Overall score is the equal-weight mean of the three rubric dimensions, normalised to 0-100.
  Cost is candidate inference cost only; judge cost is reported separately below.</p>

  <h2>Score per test case</h2>
  <p class="meta">Each cell shows the mean rubric score (1-5) and the normalised score (0-100).</p>
  <table class="cases">
    <thead>
      <tr><th>Case</th><th>Domain</th>{model_headers}</tr>
    </thead>
    <tbody>
      {''.join(case_rows)}
    </tbody>
  </table>

  <h2>Judge overhead</h2>
  <p class="meta">
    {_escape(overhead['judge_display_name'])} ({_escape(overhead['judge_model'])}) ·
    prompt version {_escape(overhead['judge_prompt_version'])} ·
    {_escape(overhead['judge_calls'])} judge calls ·
    {_number(overhead['judge_total_tokens'])} tokens ·
    {_money(overhead['judge_cost_usd'])} evaluation overhead
  </p>

  <h2>Methodology</h2>
  <p>Every candidate model answers the same {_escape(document['test_case_count'])} test cases once. A single judge model
  then scores each response against a shared rubric and the case-specific evaluation criteria.</p>
  {reproducibility_line}
  <p>Rubric dimensions:</p>
  <ul>{dimension_list}</ul>
  <p style="margin-top:10px">Capability domains:</p>
  <ul>{domain_list}</ul>

  <h2>Known limitations</h2>
  <ul>
    <li>The judge belongs to the Qwen family and one evaluated model is also from that family, so judge-family bias cannot be ruled out.</li>
    <li>Ten cases and a single run per case make this indicative, not statistically robust.</li>
    <li>Cost figures use a dated, manually curated pricing snapshot. {pricing_note}</li>
    <li>DeepSeek input cost assumes cache-miss pricing, which is the conservative choice, because cache-hit token accounting is not used in V0.1.</li>
  </ul>

  <footer>
    AIProductBench V0.1 · generated from {_escape(document.get('benchmark', 'AIProductBench'))} result JSON ·
    reproduce with <code>python3 run_benchmark.py</code>
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


def embedded_data(document: dict) -> str:
    """Small helper used by validation to confirm data is inline."""
    return json.dumps(document["summary"]["totals"], sort_keys=True)
