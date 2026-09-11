"""Pipeline orchestration for AIProductBench CN V1.

Flow (docs/ARCHITECTURE.md §1): cases -> candidate runner -> native provider
adapters -> raw responses -> deterministic evaluator -> cross-family judge
selector -> dual LLM evaluation -> score aggregation -> cost/latency analytics
-> Pareto analysis -> snapshot document.
"""

from __future__ import annotations

import datetime as dt
import json
import platform
from pathlib import Path

from src import analytics, cases as cases_module, config, deterministic, judge, models, pricing, providers


def _git_commit() -> str | None:
    """Best-effort local git commit id for the run manifest (no network)."""
    try:
        import subprocess

        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(config.PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=5,
        )
        commit = result.stdout.strip()
        return commit or None
    except Exception:  # pragma: no cover - defensive
        return None


# --------------------------------------------------------------------------
# Loading and validation
# --------------------------------------------------------------------------


def load_test_cases(path: Path | None = None) -> dict:
    return cases_module.load_cases(path)


def load_model_pool(path: Path | None = None) -> dict:
    return models.load_model_pool(path)


def validate_all(cases_document: dict, pool: dict) -> dict:
    """Return {"errors": [...], "warnings": [...]} across pool and cases."""
    pool_result = models.validate_model_pool(pool)
    cases_result = cases_module.validate_cases(cases_document)
    return {
        "errors": pool_result["errors"] + cases_result["errors"],
        "warnings": pool_result["warnings"] + cases_result["warnings"],
    }


def check_pricing_ready(pool: dict) -> list[str]:
    """Blockers for cost reporting. V1 requires cost, so unresolved pricing blocks."""
    unresolved = [
        model["key"]
        for model in pool["models"]
        if model["pricing"].get("status") != "verified"
        or not models.pricing_has_rates(model["pricing"])
    ]
    if not unresolved:
        return []
    return [
        f"Unresolved active V1 pricing for {len(unresolved)} model(s): "
        + ", ".join(unresolved)
    ]


def check_ready_for_paid_run(pool: dict, *, require_pricing: bool = True) -> list[str]:
    """Blockers that must be cleared before any real provider call."""
    blockers = []
    unverified = models.unverified_models(pool)
    if unverified:
        blockers.append(
            "Unverified model IDs: "
            + ", ".join(f"{model['key']} ({model['display_name']})" for model in unverified)
        )
    if require_pricing:
        blockers.extend(check_pricing_ready(pool))
    return blockers


def credential_status(pool: dict) -> list[dict]:
    """Report, without contacting anything, which API keys are present."""
    import os

    rows = []
    for model in pool["models"]:
        rows.append(
            {
                "key": model["key"],
                "display_name": model["display_name"],
                "env_var": model["api_key_env"],
                "present": bool(os.environ.get(model["api_key_env"], "").strip()),
            }
        )
    return rows


# --------------------------------------------------------------------------
# Execution
# --------------------------------------------------------------------------


def _base_record(case: dict, model: dict, dry_run: bool) -> dict:
    return {
        "case_id": case["id"],
        "domain": case["domain"],
        "difficulty": case.get("difficulty"),
        "language": case.get("language"),
        "model_key": model["key"],
        "model_name": model["display_name"],
        "model_id": model.get("model_id"),
        "model_family": model["model_family"],
        "provider": model["provider"],
        "product_tier": model["product_tier"],
        "inference_channel": model["inference_channel"],
        "thinking_mode": model["thinking_mode"],
        "response_text": None,
        "latency_ms": None,
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
        "reasoning_tokens": None,
        "cached_input_tokens": None,
        "native_cost": None,
        "native_currency": None,
        "normalized_cost_cny": None,
        "normalization_method": None,
        "cost_basis": None,
        "cost_error": None,
        "called_at": None,
        "synthetic": dry_run,
        "error": None,
        "deterministic": None,
        "judges_attempted": [],
        "judge_unavailable_reason": None,
        "judgements": [],
        "aggregate": None,
        "judge_agreement": None,
        "judge_cost_cny": None,
    }


def _evaluate_case(
    case: dict, model: dict, response: dict, pool: dict, *, dry_run: bool, fx_snapshot
) -> dict:
    record = _base_record(case, model, dry_run)
    record.update(
        {
            "model_id": response.get("model_id"),
            "response_text": response["text"],
            "latency_ms": response["latency_ms"],
            "input_tokens": response["input_tokens"],
            "output_tokens": response["output_tokens"],
            "total_tokens": response["total_tokens"],
            "reasoning_tokens": response.get("reasoning_tokens"),
            "cached_input_tokens": response.get("cached_input_tokens"),
            "native_cost": response["native_cost"],
            "native_currency": response["native_currency"],
            "normalized_cost_cny": response["normalized_cost_cny"],
            "normalization_method": response["normalization_method"],
            "cost_basis": response["basis"],
            "cost_error": response["cost_error"],
            "called_at": response["called_at"],
            "synthetic": response["synthetic"],
            "deterministic": deterministic.evaluate(case, response["text"]),
        }
    )

    selected = judge.select_judges(
        model, models.judges(pool), models.judge_priority(pool)
    )
    record["judges_attempted"] = [item["key"] for item in selected]
    if not selected:
        record["judge_unavailable_reason"] = (
            "fewer than two cross-family judges are eligible for this candidate"
        )
        return record

    verdicts = judge.evaluate(
        case, model, response["text"], selected, dry_run=dry_run, fx_snapshot=fx_snapshot
    )
    record["judgements"] = verdicts
    record["aggregate"] = judge.aggregate_verdicts(verdicts)
    record["judge_agreement"] = judge.judge_agreement(verdicts)

    judge_costs = [
        verdict["normalized_cost_cny"]
        for verdict in verdicts
        if verdict.get("normalized_cost_cny") is not None
    ]
    record["judge_cost_cny"] = round(sum(judge_costs), 8) if judge_costs else None
    return record


def run_benchmark(
    cases_document: dict,
    pool: dict,
    *,
    dry_run: bool = False,
    fx_snapshot: dict | None = None,
) -> dict:
    case_list = cases_module.all_cases(cases_document)
    candidate_models = models.candidates(pool)
    results: list[dict] = []
    failures: list[dict] = []

    for case in case_list:
        for model in candidate_models:
            messages = [{"role": "user", "content": case["prompt"]}]
            try:
                if dry_run:
                    response = providers.synthetic_call(
                        model,
                        messages,
                        seed=f"{case['id']}|{model['key']}",
                        fx_snapshot=fx_snapshot,
                    )
                else:
                    response = providers.chat(model, messages, fx_snapshot=fx_snapshot)
            except providers.ProviderError as exc:
                record = _base_record(case, model, dry_run)
                record["error"] = str(exc)
                results.append(record)
                failures.append(
                    {
                        "case_id": case["id"],
                        "model_key": model["key"],
                        "model_name": model["display_name"],
                        "stage": "candidate",
                        "error": str(exc),
                    }
                )
                continue

            results.append(
                _evaluate_case(
                    case, model, response, pool, dry_run=dry_run, fx_snapshot=fx_snapshot
                )
            )

    return build_document(
        cases_document, pool, results, failures, dry_run=dry_run, fx_snapshot=fx_snapshot
    )


# --------------------------------------------------------------------------
# Aggregation
# --------------------------------------------------------------------------


def _mean(values: list) -> float | None:
    present = [value for value in values if value is not None]
    return round(sum(present) / len(present), 3) if present else None


def _mean_exact(values: list) -> float | None:
    """Unrounded mean, used for ordering decisions.

    Ranking must not be decided by a rounded display value: two models whose
    3-decimal scores coincide can still differ in the underlying data, and
    ordering them by list position would be an accident of the registry order
    rather than a benchmark result. The frozen methodology defines no tie-break
    rule, so ordering uses the full-precision value while the rounded value
    remains the published display metric.
    """
    present = [value for value in values if value is not None]
    return sum(present) / len(present) if present else None


def _sum(values: list) -> float | None:
    present = [value for value in values if value is not None]
    return round(sum(present), 8) if present else None


def summarize(results: list[dict], pool: dict, required_cases: int | None = None) -> dict:
    """Aggregate results.

    `required_cases` is the number of production benchmark cases. A model may
    only enter the official ranking when it has a valid scored result for every
    one of them (see docs/METHODOLOGY_V1.md §3). Partial results remain visible
    as diagnostics but never produce an official rank from a reduced
    denominator.
    """
    if required_cases is None:
        required_cases = len({row["case_id"] for row in results})

    model_rows = []

    for model in models.candidates(pool):
        rows = [row for row in results if row["model_key"] == model["key"]]
        scored = [row for row in rows if row.get("aggregate") and row.get("error") is None]

        det_checks = [
            check
            for row in rows
            if row.get("deterministic")
            for check in row["deterministic"]["checks"]
        ]
        det_passed = sum(1 for check in det_checks if check["passed"])

        native_costs: dict[str, float] = {}
        for row in rows:
            if row.get("native_cost") is not None and row.get("native_currency"):
                currency = row["native_currency"]
                native_costs[currency] = round(
                    native_costs.get(currency, 0.0) + row["native_cost"], 8
                )

        model_rows.append(
            {
                "model_key": model["key"],
                "model_name": model["display_name"],
                "model_id": model.get("model_id"),
                "model_family": model["model_family"],
                "provider": model["provider"],
                "provider_key": model["provider_key"],
                "region": model.get("region"),
                "product_tier": model["product_tier"],
                "inference_channel": model["inference_channel"],
                "thinking_mode": model["thinking_mode"],
                "cases_total": len(rows),
                "cases_attempted": len(rows),
                "cases_scored": len(scored),
                "cases_failed": len(rows) - len(scored),
                "cases_required": required_cases,
                "overall_score": _mean([row["aggregate"]["overall_score"] for row in scored]),
                "overall_score_exact": _mean_exact(
                    [row["aggregate"]["overall_score"] for row in scored]
                ),
                "quality_score": _mean([row["aggregate"]["quality_score"] for row in scored]),
                "dimension_scores": {
                    dimension: _mean(
                        [row["aggregate"]["dimension_scores"][dimension] for row in scored]
                    )
                    for dimension in config.RUBRIC_DIMENSIONS
                },
                "constraint_pass_rate": round(det_passed / len(det_checks), 4)
                if det_checks
                else None,
                "deterministic_checks": f"{det_passed}/{len(det_checks)}"
                if det_checks
                else None,
                "task_success_rate": _mean(
                    [
                        1.0 if row["deterministic"]["all_passed"] else 0.0
                        for row in rows
                        if row.get("deterministic")
                        and row["deterministic"]["all_passed"] is not None
                    ]
                ),
                "latency": analytics.latency_stats(
                    [row["latency_ms"] for row in rows if row.get("latency_ms") is not None]
                ),
                "tokens": {
                    "input": _sum([row["input_tokens"] for row in rows]),
                    "output": _sum([row["output_tokens"] for row in rows]),
                    "reasoning": _sum([row["reasoning_tokens"] for row in rows]),
                    "cached_input": _sum([row["cached_input_tokens"] for row in rows]),
                    "total": _sum([row["total_tokens"] for row in rows]),
                },
                "candidate_cost_native": native_costs or None,
                "candidate_cost_cny": _sum([row["normalized_cost_cny"] for row in rows]),
                "judge_cost_cny": _sum([row["judge_cost_cny"] for row in rows]),
                "judge_agreement_mean_abs_difference": _mean(
                    [
                        row["judge_agreement"]["overall_mean_abs_difference"]
                        for row in rows
                        if row.get("judge_agreement")
                    ]
                ),
                "judge_agreement_samples": sum(
                    1 for row in rows if row.get("judge_agreement")
                ),
                "judges_used": sorted(
                    {
                        verdict["judge_key"]
                        for row in rows
                        for verdict in row["judgements"]
                    }
                ),
                "judge_unavailable_cases": sum(
                    1 for row in rows if row.get("judge_unavailable_reason")
                ),
                "cost_warnings": sum(1 for row in rows if row.get("cost_error")),
            }
        )

    # Equal-denominator rule: only a model with a valid score for every required
    # case may enter the official ranking or the official Pareto frontier.
    for row in model_rows:
        row["rank_eligible"] = row["cases_scored"] == required_cases and required_cases > 0
        if row["rank_eligible"]:
            row["incomplete_reason"] = None
        else:
            reasons = [f"{row['cases_scored']} of {required_cases} cases have a valid score"]
            if row["judge_unavailable_cases"]:
                reasons.append(
                    f"{row['judge_unavailable_cases']} case(s) were judge-unavailable"
                )
            if row["cases_failed"]:
                reasons.append(f"{row['cases_failed']} case(s) failed")
            row["incomplete_reason"] = "; ".join(reasons)

    # Cross-model comparative metrics require equal denominators. For an
    # incomplete run they are suppressed rather than computed over a reduced
    # or unequal base. Per-model diagnostics (actual spend, completed calls and
    # cases, partial tokens, partial latency) stay visible.
    for row in model_rows:
        if row["rank_eligible"]:
            row["cost_per_100_tasks_cny"] = analytics.cost_per_100_tasks(
                row["candidate_cost_cny"], row["cases_total"]
            )
            row["quality_per_cny"] = analytics.quality_per_cny(
                row["overall_score_exact"], row["candidate_cost_cny"]
            )
            row["comparative_metrics_available"] = True
            row["unavailable_metrics"] = []
        else:
            row["cost_per_100_tasks_cny"] = None
            row["quality_per_cny"] = None
            row["comparative_metrics_available"] = False
            row["unavailable_metrics"] = [
                "cost_per_100_tasks_cny",
                "quality_per_cny",
                "official_rank",
                "official_pareto_eligibility",
            ]
        row["actual_spend_cny"] = row["candidate_cost_cny"]
        row["calls_completed"] = sum(1 for row_result in results
                                     if row_result["model_key"] == row["model_key"]
                                     and row_result.get("error") is None)
        row["cases_completed"] = row["cases_scored"]

    eligible_rows = [row for row in model_rows if row["rank_eligible"]]

    quality_cost = analytics.pareto_frontier(
        eligible_rows,
        [("overall_score_exact", "max"), ("cost_per_100_tasks_cny", "min")],
    )
    three_axis_rows = [
        row for row in eligible_rows if row["latency"]["p95_latency_ms"] is not None
    ]
    if three_axis_rows:
        quality_cost_latency = analytics.pareto_frontier(
            [
                {**row, "p95_latency_ms": row["latency"]["p95_latency_ms"]}
                for row in eligible_rows
            ],
            [
                ("overall_score_exact", "max"),
                ("cost_per_100_tasks_cny", "min"),
                ("p95_latency_ms", "min"),
            ],
        )
    else:
        quality_cost_latency = {"objectives": [], "frontier": [], "dominated": {}, "not_evaluated": []}

    for row in model_rows:
        if not row["rank_eligible"]:
            row["pareto_quality_cost"] = False
            row["pareto_quality_cost_latency"] = False
            row["dominated_by"] = None
            continue
        row["pareto_quality_cost"] = row["model_key"] in quality_cost["frontier"]
        row["pareto_quality_cost_latency"] = (
            row["model_key"] in quality_cost_latency["frontier"]
        )
        row["dominated_by"] = quality_cost["dominated"].get(row["model_key"])

    ranked = sorted(
        model_rows,
        key=lambda row: (
            row["overall_score_exact"] is None,
            -(row["overall_score_exact"] or 0),
        ),
    )

    rank = 0
    for row in ranked:
        if row["rank_eligible"]:
            rank += 1
            row["rank"] = rank
        else:
            row["rank"] = None

    verdict_rows = [verdict for row in results for verdict in row["judgements"]]
    # A judge verdict can legitimately be a failure record (provider error or
    # unparseable judge output) and therefore carry no success-only telemetry.
    # Token and latency fields are read optionally here so aggregation never
    # crashes on a real failure record; unknown values stay absent rather than
    # being fabricated as zero. Failure records remain failures.
    judge_overhead = {
        "judge_calls": len(verdict_rows),
        "judge_models_used": sorted({verdict["judge_key"] for verdict in verdict_rows}),
        "judge_total_tokens": {
            "input": _sum([verdict.get("input_tokens") for verdict in verdict_rows]),
            "output": _sum([verdict.get("output_tokens") for verdict in verdict_rows]),
            "total": _sum([verdict.get("total_tokens") for verdict in verdict_rows]),
        },
        "judge_cost_cny": _sum([row["judge_cost_cny"] for row in results]),
        "judge_avg_latency_ms": _mean(
            [verdict.get("latency_ms") for verdict in verdict_rows]
        ),
        "judge_p95_latency_ms": analytics.percentile(
            [verdict.get("latency_ms") for verdict in verdict_rows], 0.95
        ),
        "judge_failure_records": sum(
            1 for verdict in verdict_rows if verdict.get("error")
        ),
    }

    return {
        "models": ranked,
        "judge_overhead": judge_overhead,
        "pareto": {
            "quality_cost": quality_cost,
            "quality_cost_latency": quality_cost_latency,
        },
        "official_ranking": {
            "rule": (
                "A model holds an official rank only when it has a valid scored result "
                "for every production benchmark case. Partial results are diagnostic "
                "only and are never ranked from a reduced denominator."
            ),
            "ordering_rule": (
                "Ranked models are ordered by full-precision mean overall quality "
                "(descending). The published overall_score is rounded to 3 decimals for "
                "display; where rounded values coincide, full precision still determines "
                "the order (see overall_score_exact). The frozen methodology defines no "
                "tie-break rule, so no arbitrary ordering is applied."
            ),
            "required_cases": required_cases,
            "ranked_models": [row["model_key"] for row in ranked if row["rank_eligible"]],
            "incomplete_models": [
                {
                    "model_key": row["model_key"],
                    "model_name": row["model_name"],
                    "cases_scored": row["cases_scored"],
                    "cases_required": required_cases,
                    "reason": row["incomplete_reason"],
                }
                for row in ranked
                if not row["rank_eligible"]
            ],
            "complete_run": all(row["rank_eligible"] for row in ranked) and bool(ranked),
        },
        "metric_availability": {
            "rule": (
                "Cross-model comparative metrics need equal denominators. When a run is "
                "incomplete they are reported as null rather than computed over a reduced "
                "or unequal base. Diagnostic metrics remain visible."
            ),
            "run_complete": all(row["rank_eligible"] for row in ranked) and bool(ranked),
            "comparative_metrics": [
                "cost_per_100_tasks_cny",
                "quality_per_cny",
                "official_rank",
                "official_pareto_eligibility",
            ],
            "diagnostic_metrics": [
                "actual_spend_cny",
                "calls_completed",
                "cases_completed",
                "tokens",
                "latency",
            ],
            "suppressed_for_incomplete_models": [
                row["model_key"] for row in ranked if not row["rank_eligible"]
            ],
        },
        "totals": {
            "candidate_calls": sum(row["cases_total"] for row in model_rows),
            "judge_calls": len(verdict_rows),
            "candidate_cost_cny": _sum([row["candidate_cost_cny"] for row in model_rows]),
            "judge_cost_cny": judge_overhead["judge_cost_cny"],
            "cost_estimation_complete": not any(row["cost_warnings"] for row in model_rows),
        },
    }


def build_document(
    cases_document: dict,
    pool: dict,
    results: list[dict],
    failures: list[dict],
    *,
    dry_run: bool,
    fx_snapshot: dict | None,
) -> dict:
    start_time = dt.datetime.now(dt.timezone.utc)
    case_list = cases_module.all_cases(cases_document)
    snapshot_id = (
        f"{config.BENCHMARK_VERSION}-"
        f"{'synthetic-' if dry_run else ''}"
        f"{start_time.strftime('%Y%m%dT%H%M%SZ')}"
    )

    dataset_manifest_hash = cases_module.semantic_manifest_hash(case_list)
    try:
        registry_snapshot = models.build_registry_snapshot(pool)
        registry_snapshot_id = registry_snapshot["snapshot_id"]
        registry_snapshot_hash = registry_snapshot["content_sha256"]
    except Exception:  # pragma: no cover - defensive; registry contract is validated
        registry_snapshot_id = None
        registry_snapshot_hash = None
    try:
        pricing_snapshot_doc = pricing.build_pricing_snapshot(pool["models"])
        pricing_snapshot_id = pricing_snapshot_doc["snapshot_id"]
        pricing_snapshot_hash = pricing_snapshot_doc["content_sha256"]
    except Exception:  # pragma: no cover - defensive
        pricing_snapshot_id = None
        pricing_snapshot_hash = None
    judge_config_snapshot_id = cases_module.canonical_hash(
        {
            "priority": models.judge_priority(pool),
            "judges": [
                {"key": m["key"], "model_id": m.get("model_id"), "family": m["model_family"]}
                for m in models.judges(pool)
            ],
            "judge_prompt_version": config.JUDGE_PROMPT_VERSION,
        }
    )

    return {
        "benchmark": config.BENCHMARK_NAME,
        "benchmark_version": config.BENCHMARK_VERSION,
        "snapshot_id": snapshot_id,
        "synthetic": dry_run,
        "synthetic_notice": (
            "SYNTHETIC DRY-RUN OUTPUT. Responses, tokens, latency, scores and costs in "
            "this document were generated offline and do not come from any real model. "
            "Synthetic pricing and FX fixtures are placeholders, not published values."
        )
        if dry_run
        else None,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "dataset": {
            "name": cases_document.get("dataset_name"),
            "version": cases_document.get("dataset_version"),
            "synthetic": bool(cases_document.get("synthetic")),
            "case_count": len(case_list),
            "semantic_manifest_sha256": dataset_manifest_hash,
            "domain_distribution": cases_module.domain_distribution(case_list),
            "difficulty_distribution": cases_module.distribution(case_list, "difficulty"),
            "language_distribution": cases_module.distribution(case_list, "language"),
        },
        "domains": list(config.DOMAINS),
        "model_pool": {
            "pool_version": pool.get("pool_version"),
            **models.pool_facts(pool),
            "candidates": [
                {
                    "key": model["key"],
                    "logical_model_id": model["key"],
                    "display_name": model["display_name"],
                    "model_id": model.get("model_id"),
                    "provider_model_id": model.get("model_id"),
                    "model_id_status": model["model_id_status"],
                    "model_id_verified_as_of": model.get("model_id_verified_as_of"),
                    "model_family": model["model_family"],
                    "provider": model["provider"],
                    "provider_key": model["provider_key"],
                    "region": model.get("region"),
                    "product_tier": model["product_tier"],
                    "inference_channel": model["inference_channel"],
                    "thinking_mode": model["thinking_mode"],
                    "thinking_config": model.get("thinking_config"),
                    "request_config": providers.effective_request_config(model),
                    "pricing_record": model.get("pricing"),
                }
                for model in models.candidates(pool)
            ],
            "judge_pool": [
                {
                    "key": model["key"],
                    "display_name": model["display_name"],
                    "model_id": model.get("model_id"),
                    "model_id_status": model["model_id_status"],
                    "model_family": model["model_family"],
                    "provider": model["provider"],
                    "provider_key": model["provider_key"],
                    "product_tier": model["product_tier"],
                    "also_candidate": bool(model.get("candidate")),
                }
                for model in models.judges(pool)
            ],
            "judge_priority": models.judge_priority(pool),
            "registry_note": pool.get("registry_note"),
        },
        "run_manifest": {
            "run_id": snapshot_id,
            "benchmark_version": config.BENCHMARK_VERSION,
            "dataset_version": cases_document.get("dataset_version"),
            "dataset_manifest_hash": dataset_manifest_hash,
            "git_commit": _git_commit(),
            "model_registry_snapshot_id": registry_snapshot_id,
            "model_registry_snapshot_hash": registry_snapshot_hash,
            "pricing_snapshot_id": pricing_snapshot_id,
            "pricing_snapshot_hash": pricing_snapshot_hash,
            "fx_snapshot_id": (fx_snapshot or {}).get("snapshot_id"),
            "judge_config_snapshot_id": judge_config_snapshot_id,
            "start_time": start_time.isoformat(timespec="seconds"),
            "runtime": {
                "python_version": platform.python_version(),
                "platform": platform.platform(),
                "benchmark_version": config.BENCHMARK_VERSION,
            },
        },
        "rubric": {
            "dimensions": list(config.RUBRIC_DIMENSIONS),
            "scale": f"integer {config.SCORE_MIN}-{config.SCORE_MAX} per dimension",
            "aggregation": "equal-weight mean of the three dimensions, normalised to 0-100",
            "judge_prompt_version": config.JUDGE_PROMPT_VERSION,
            "judges_per_response": config.JUDGES_PER_RESPONSE,
            "selection_rule": (
                "fixed judge priority from configuration, then leave-one-family/provider-out "
                "exclusion, then the first two eligible cross-family judges"
            ),
            "role_separation": (
                "Candidate execution and judge execution are distinct roles over one shared "
                "model registry. Candidate inference cost and judge evaluation cost are never "
                "mixed, and candidate latency and judge latency are never mixed."
            ),
        },
        "pricing_snapshot": pricing.pricing_snapshot(
            pool["models"], fx_snapshot, synthetic=dry_run
        ),
        "historical_pricing": {
            "status": models.historical_pricing(pool).get("status"),
            "note": models.historical_pricing(pool).get("note"),
            "entry_count": len(models.historical_pricing(pool).get("entries") or []),
            "model_ids": sorted(models.archived_pricing_model_ids(pool)),
            "used_for_v1_cost": False,
        },
        "results": results,
        "failures": failures,
        "summary": summarize(results, pool, required_cases=len(case_list)),
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

    header = (
        f"{'#':>2}  {'model':<24} {'score':>7}  {'p50':>8}  {'p95':>8}  "
        f"{'constr':>7}  {'CNY/100':>10}  pareto"
    )
    print(header)
    print("-" * len(header))
    for row in summary["models"]:
        score = f"{row['overall_score']:.2f}" if row["overall_score"] is not None else "n/a"
        p50 = (
            f"{row['latency']['p50_latency_ms']:.0f}ms"
            if row["latency"]["p50_latency_ms"] is not None
            else "n/a"
        )
        p95 = (
            f"{row['latency']['p95_latency_ms']:.0f}ms"
            if row["latency"]["p95_latency_ms"] is not None
            else "n/a"
        )
        constraint = (
            f"{row['constraint_pass_rate']:.2f}"
            if row["constraint_pass_rate"] is not None
            else "n/a"
        )
        if row["cost_per_100_tasks_cny"] is not None:
            per_100 = f"{row['cost_per_100_tasks_cny']:.4f}"
        elif not row["rank_eligible"]:
            per_100 = "n/a"
        else:
            per_100 = "unpriced"
        flags = []
        if row["pareto_quality_cost"]:
            flags.append("QxC")
        if row["pareto_quality_cost_latency"]:
            flags.append("QxCxL")
        rank_display = str(row["rank"]) if row["rank"] is not None else "-"
        if not row["rank_eligible"]:
            flags.append("INCOMPLETE")
        print(
            f"{rank_display:>2}  {row['model_name']:<24} {score:>7}  {p50:>8}  {p95:>8}  "
            f"{constraint:>7}  {per_100:>10}  {','.join(flags) or '-'}"
        )

    print()
    for row in summary["models"]:
        parts = []
        for dimension in config.RUBRIC_DIMENSIONS:
            value = row["dimension_scores"][dimension]
            parts.append(f"{dimension}={value:.2f}" if value is not None else f"{dimension}=n/a")
        print(f"  {row['model_name']}: " + "  ".join(parts))

    print()
    judge_tokens = overhead["judge_total_tokens"]["total"]
    print(
        f"  judge overhead: {overhead['judge_calls']} calls across "
        f"{len(overhead['judge_models_used'])} judge(s), "
        f"{judge_tokens if judge_tokens is not None else 'n/a'} tokens, "
        f"{overhead['judge_cost_cny'] if overhead['judge_cost_cny'] is not None else 'unpriced'} CNY"
        " (reported separately)"
    )
    print(
        f"  candidate calls: {totals['candidate_calls']}, judge calls: {totals['judge_calls']}, "
        f"candidate cost: "
        f"{totals['candidate_cost_cny'] if totals['candidate_cost_cny'] is not None else 'unpriced'} CNY"
    )
    if document.get("failures"):
        print(f"  failures: {len(document['failures'])}")

    unpriced = sum(row["cost_warnings"] for row in summary["models"])
    if unpriced:
        print(f"  note: {unpriced} response(s) have no usable price and are recorded as null.")
    unavailable = sum(row["judge_unavailable_cases"] for row in summary["models"])
    if unavailable:
        print(
            f"  note: {unavailable} response(s) had fewer than two eligible cross-family judges."
        )

    official = summary["official_ranking"]
    if not official["complete_run"]:
        print()
        print(
            f"  !! OFFICIAL RANKING INCOMPLETE: {len(official['incomplete_models'])} model(s) "
            f"lack a valid score for all {official['required_cases']} case(s)."
        )
        for item in official["incomplete_models"][:10]:
            print(f"     {item['model_key']}: {item['reason']}")
        print(
            "     Incomplete models stay visible as diagnostics but are excluded from the "
            "official ranking and the Pareto frontier."
        )
        print(
            "     Comparative metrics (cost per 100 tasks, quality per CNY) are shown as "
            "n/a for those models because the run is incomplete."
        )
