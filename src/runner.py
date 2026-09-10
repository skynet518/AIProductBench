"""Benchmark orchestration, aggregation, and result serialisation.

Flow: load the 10 test cases, call each of the 2 candidate models once per case,
send every response to the single judge, then aggregate per model and per domain.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from src import config, judge, providers


# Fixed timestamp used only for pricing lookups in validation.
_SAMPLE_AT = dt.datetime(2026, 9, 11, 0, 0, tzinfo=dt.timezone.utc)


# --------------------------------------------------------------------------
# Loading and validation
# --------------------------------------------------------------------------


def load_test_cases(path: Path | None = None) -> dict:
    path = path or config.TEST_CASES_FILE
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def validate_test_cases(document: dict) -> list[str]:
    """Return a list of human-readable problems. Empty list means valid."""
    errors: list[str] = []
    cases = document.get("test_cases")

    if not isinstance(cases, list):
        return ["'test_cases' must be a list."]
    if len(cases) != 10:
        errors.append(f"Expected exactly 10 test cases, found {len(cases)}.")

    seen_ids: set[str] = set()
    domain_counts: dict[str, int] = {}

    for index, case in enumerate(cases):
        label = case.get("id") or f"index {index}"
        for field in ("id", "domain", "title", "prompt", "evaluation_criteria"):
            if not case.get(field):
                errors.append(f"Case {label} is missing a non-empty '{field}'.")

        case_id = case.get("id")
        if case_id in seen_ids:
            errors.append(f"Duplicate case id: {case_id}.")
        seen_ids.add(case_id)

        domain = case.get("domain")
        if domain and domain not in config.DOMAINS:
            errors.append(f"Case {label} has unknown domain '{domain}'.")
        if domain:
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

        criteria = case.get("evaluation_criteria")
        if criteria is not None and (not isinstance(criteria, list) or not criteria):
            errors.append(f"Case {label} must have a non-empty 'evaluation_criteria' list.")

    present_domains = sorted(domain_counts)
    if present_domains != sorted(config.DOMAINS):
        errors.append(
            f"Expected exactly the 3 domains {list(config.DOMAINS)}, found {present_domains}."
        )

    return errors


def domain_distribution(document: dict) -> dict[str, int]:
    counts = {domain: 0 for domain in config.DOMAINS}
    for case in document.get("test_cases", []):
        domain = case.get("domain")
        if domain in counts:
            counts[domain] += 1
    return counts


def validate_configuration() -> list[str]:
    """Check the model and judge configuration without contacting any provider."""
    errors: list[str] = []

    if len(config.MODELS) != 2:
        errors.append(f"Expected exactly 2 evaluated models, found {len(config.MODELS)}.")
    if len({model["key"] for model in config.MODELS}) != len(config.MODELS):
        errors.append("Evaluated model keys must be unique.")
    if len({model["model"] for model in config.MODELS}) != len(config.MODELS):
        errors.append("The two evaluated models must use different model IDs.")

    for model in list(config.MODELS) + [config.JUDGE]:
        if model["wire_api"] not in ("chat_completions", "responses"):
            errors.append(
                f"{model['display_name']} has unsupported wire_api '{model['wire_api']}'."
            )
        if not model["base_url"].startswith("https://"):
            errors.append(f"{model['display_name']} base_url must use https.")
        if not model["api_key_env"].isupper():
            errors.append(
                f"{model['display_name']} api_key_env must name an environment variable."
            )
        if model["temperature"] != 0.0:
            errors.append(f"{model['display_name']} must run at temperature 0.0.")

    judge_id = config.JUDGE["model"]
    if judge_id in {model["model"] for model in config.MODELS}:
        errors.append("The judge must not be the same model as an evaluated model.")

    for model in list(config.MODELS) + [config.JUDGE]:
        try:
            config.rates_for(model["model"], at=_SAMPLE_AT)
        except config.PricingError as exc:
            errors.append(f"Pricing unresolved for {model['display_name']}: {exc}")

    return errors


def pricing_region() -> dict:
    """Report the DashScope region implied by the configured base URL."""
    base_url = config.MODELS[0]["base_url"]
    key = config.dashscope_region(base_url)
    return {
        "base_url": base_url,
        "key": key,
        "label": config.DASHSCOPE_REGIONS[key]["label"] if key else "unidentified",
    }


def credential_status() -> list[dict]:
    """Report, without contacting anything, which API keys are present."""
    import os

    rows = []
    for model in list(config.MODELS) + [config.JUDGE]:
        name = model["api_key_env"]
        rows.append(
            {
                "display_name": model["display_name"],
                "env_var": name,
                "present": bool(os.environ.get(name, "").strip()),
            }
        )
    return rows


# --------------------------------------------------------------------------
# Execution
# --------------------------------------------------------------------------


def _evaluate_response(case: dict, model: dict, response: dict, dry_run: bool) -> dict:
    record = {
        "case_id": case["id"],
        "domain": case["domain"],
        "case_title": case["title"],
        "model_key": model["key"],
        "model_name": model["display_name"],
        "model_id": model["model"],
        "response_text": response["text"],
        "latency_ms": response["latency_ms"],
        "input_tokens": response["input_tokens"],
        "output_tokens": response["output_tokens"],
        "total_tokens": response["total_tokens"],
        "estimated_cost_usd": response["estimated_cost_usd"],
        "cost_basis": response.get("cost_basis"),
        "cost_error": response.get("cost_error"),
        "called_at": response.get("called_at"),
        "synthetic": response["synthetic"],
        "error": None,
        "judge": None,
    }

    try:
        record["judge"] = judge.evaluate(
            case, model["display_name"], response["text"], dry_run=dry_run
        )
    except (providers.ProviderError, judge.JudgeOutputError) as exc:
        record["error"] = f"judge: {exc}"

    return record


def run_benchmark(document: dict, *, dry_run: bool = False) -> dict:
    cases = document["test_cases"]
    results: list[dict] = []
    failures: list[dict] = []

    for case in cases:
        for model in config.MODELS:
            messages = [{"role": "user", "content": case["prompt"]}]
            try:
                if dry_run:
                    response = providers.synthetic_call(
                        model, messages, seed=f"{case['id']}|{model['key']}"
                    )
                else:
                    response = providers.chat(model, messages)
            except providers.ProviderError as exc:
                failures.append(
                    {
                        "case_id": case["id"],
                        "model_key": model["key"],
                        "model_name": model["display_name"],
                        "error": str(exc),
                    }
                )
                results.append(
                    {
                        "case_id": case["id"],
                        "domain": case["domain"],
                        "case_title": case["title"],
                        "model_key": model["key"],
                        "model_name": model["display_name"],
                        "model_id": model["model"],
                        "response_text": None,
                        "latency_ms": None,
                        "input_tokens": None,
                        "output_tokens": None,
                        "total_tokens": None,
                        "estimated_cost_usd": None,
                        "cost_basis": None,
                        "cost_error": None,
                        "called_at": None,
                        "synthetic": dry_run,
                        "error": str(exc),
                        "judge": None,
                    }
                )
                continue

            results.append(_evaluate_response(case, model, response, dry_run))

    return build_document(document, results, failures, dry_run=dry_run)


# --------------------------------------------------------------------------
# Aggregation
# --------------------------------------------------------------------------


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def _sum_or_none(values: list[int]) -> int | None:
    present = [value for value in values if value is not None]
    return sum(present) if present else None


def _cost_or_none(values: list[float]) -> float | None:
    present = [value for value in values if value is not None]
    return round(sum(present), 6) if present else None


def summarize(results: list[dict]) -> dict:
    """Build per-model and per-domain aggregates plus judge overhead."""
    model_rows = []

    for model in config.MODELS:
        rows = [row for row in results if row["model_key"] == model["key"]]
        scored = [row for row in rows if row.get("judge") and row.get("error") is None]

        domain_scores: dict[str, float | None] = {}
        domain_averages: dict[str, float | None] = {}
        for domain in config.DOMAINS:
            domain_rows = [row for row in scored if row["domain"] == domain]
            domain_scores[domain] = _mean(
                [row["judge"]["normalized_score"] for row in domain_rows]
            )
            domain_averages[domain] = _mean(
                [row["judge"]["mean_score"] for row in domain_rows]
            )

        model_rows.append(
            {
                "model_key": model["key"],
                "model_name": model["display_name"],
                "model_id": model["model"],
                "provider": model["provider"],
                "cases_total": len(rows),
                "cases_scored": len(scored),
                "cases_failed": len(rows) - len(scored),
                "overall_score": _mean(
                    [row["judge"]["normalized_score"] for row in scored]
                ),
                "overall_mean_score": _mean([row["judge"]["mean_score"] for row in scored]),
                "domain_scores": domain_scores,
                "domain_mean_scores": domain_averages,
                "avg_latency_ms": _mean(
                    [row["latency_ms"] for row in scored if row["latency_ms"] is not None]
                ),
                "total_tokens": _sum_or_none([row["total_tokens"] for row in scored]),
                "candidate_cost_usd": _cost_or_none(
                    [row["estimated_cost_usd"] for row in scored]
                ),
                "cost_complete": not any(row.get("cost_error") for row in scored),
                "cost_basis": sorted(
                    {
                        row["cost_basis"]
                        for row in scored
                        if row.get("cost_basis") and row.get("cost_error") is None
                    }
                ),
            }
        )

    ranked = sorted(
        model_rows,
        key=lambda row: (row["overall_score"] is None, -(row["overall_score"] or 0)),
    )
    for index, row in enumerate(ranked, start=1):
        row["rank"] = index

    judge_rows = [row["judge"] for row in results if row.get("judge")]
    judge_overhead = {
        "judge_model": config.JUDGE["model"],
        "judge_display_name": config.JUDGE["display_name"],
        "judge_prompt_version": config.JUDGE_PROMPT_VERSION,
        "judge_calls": len(judge_rows),
        "judge_total_tokens": _sum_or_none([row["total_tokens"] for row in judge_rows]),
        "judge_cost_usd": _cost_or_none([row["estimated_cost_usd"] for row in judge_rows]),
        "judge_cost_complete": not any(row.get("cost_error") for row in judge_rows),
        "judge_avg_latency_ms": _mean(
            [row["latency_ms"] for row in judge_rows if row["latency_ms"] is not None]
        ),
    }

    candidate_cost = _cost_or_none([row["candidate_cost_usd"] for row in model_rows])

    cost_warnings = []
    for row in results:
        if row.get("cost_error"):
            cost_warnings.append(
                {
                    "case_id": row["case_id"],
                    "model_name": row["model_name"],
                    "stage": "candidate inference",
                    "detail": row["cost_error"],
                }
            )
        judge_row = row.get("judge")
        if judge_row and judge_row.get("cost_error"):
            cost_warnings.append(
                {
                    "case_id": row["case_id"],
                    "model_name": config.JUDGE["display_name"],
                    "stage": "judge evaluation",
                    "detail": judge_row["cost_error"],
                }
            )

    return {
        "models": ranked,
        "judge_overhead": judge_overhead,
        "cost_warnings": cost_warnings,
        "totals": {
            "candidate_calls": sum(row["cases_total"] for row in model_rows),
            "judge_calls": judge_overhead["judge_calls"],
            "candidate_cost_usd": candidate_cost,
            "judge_cost_usd": judge_overhead["judge_cost_usd"],
            "cost_estimation_complete": not cost_warnings,
            "run_cost_usd": (
                round(candidate_cost + judge_overhead["judge_cost_usd"], 6)
                if candidate_cost is not None and judge_overhead["judge_cost_usd"] is not None
                else None
            ),
        },
    }


def build_document(
    document: dict, results: list[dict], failures: list[dict], *, dry_run: bool
) -> dict:
    return {
        "benchmark": document.get("benchmark", "AIProductBench"),
        "benchmark_version": config.BENCHMARK_VERSION,
        "synthetic": dry_run,
        "synthetic_notice": (
            "SYNTHETIC DRY-RUN OUTPUT. Responses, tokens, latency, and costs in this "
            "document were generated offline and do not come from any real model."
        )
        if dry_run
        else None,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "domains": document.get("domains", {}),
        "models": [
            {
                "key": model["key"],
                "display_name": model["display_name"],
                "model_id": model["model"],
                "provider": model["provider"],
            }
            for model in config.MODELS
        ],
        "judge": {
            "display_name": config.JUDGE["display_name"],
            "model_id": config.JUDGE["model"],
            "provider": config.JUDGE["provider"],
            "prompt_version": config.JUDGE_PROMPT_VERSION,
        },
        "rubric": {
            "dimensions": list(config.RUBRIC_DIMENSIONS),
            "scale": f"integer {config.SCORE_MIN}-{config.SCORE_MAX} per dimension",
            "aggregation": "equal-weight mean of the three dimensions, normalised to 0-100",
        },
        "reproducibility": config.REPRODUCIBILITY,
        "pricing_snapshot": config.pricing_snapshot(),
        "test_case_count": len(document.get("test_cases", [])),
        "domain_distribution": domain_distribution(document),
        "results": results,
        "failures": failures,
        "summary": summarize(results),
    }


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


def write_json(document: dict, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return path


def print_summary(document: dict) -> None:
    summary = document["summary"]
    overhead = summary["judge_overhead"]
    totals = summary["totals"]

    if document.get("synthetic"):
        print("!! SYNTHETIC DRY-RUN RESULTS — not produced by any real model.\n")

    header = f"{'#':>2}  {'model':<18} {'score':>7}  {'latency':>9}  {'tokens':>8}  {'cost':>10}"
    print(header)
    print("-" * len(header))
    for row in summary["models"]:
        score = f"{row['overall_score']:.2f}" if row["overall_score"] is not None else "n/a"
        latency = (
            f"{row['avg_latency_ms']:.0f} ms" if row["avg_latency_ms"] is not None else "n/a"
        )
        tokens = f"{row['total_tokens']:,}" if row["total_tokens"] is not None else "n/a"
        cost = (
            f"${row['candidate_cost_usd']:.6f}"
            if row["candidate_cost_usd"] is not None
            else "unpriced"
        )
        print(
            f"{row['rank']:>2}  {row['model_name']:<18} {score:>7}  {latency:>9}  "
            f"{tokens:>8}  {cost:>10}"
        )

    print()
    for row in summary["models"]:
        parts = []
        for domain in config.DOMAINS:
            value = row["domain_scores"].get(domain)
            parts.append(f"{domain}={value:.1f}" if value is not None else f"{domain}=n/a")
        print(f"  {row['model_name']}: " + "  ".join(parts))

    print()
    judge_cost = (
        f"${overhead['judge_cost_usd']:.6f}"
        if overhead["judge_cost_usd"] is not None
        else "unpriced"
    )
    print(
        f"  judge overhead: {overhead['judge_calls']} calls, "
        f"{overhead['judge_total_tokens'] if overhead['judge_total_tokens'] is not None else 'n/a'} tokens, "
        f"{judge_cost} (reported separately from candidate cost)"
    )
    print(
        f"  candidate calls: {totals['candidate_calls']}, "
        f"judge calls: {totals['judge_calls']}, "
        f"scored responses: {sum(row['cases_scored'] for row in summary['models'])}"
    )
    if document.get("failures"):
        print(f"  failures: {len(document['failures'])}")
    if summary["cost_warnings"]:
        print()
        print(f"  !! COST ESTIMATION FAILED for {len(summary['cost_warnings'])} call(s):")
        for warning in summary["cost_warnings"][:10]:
            print(f"     {warning['case_id']} [{warning['stage']}] {warning['detail']}")
        print("     Affected costs are recorded as null rather than guessed.")
