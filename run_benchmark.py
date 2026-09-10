#!/usr/bin/env python3
"""AIProductBench CN V1 command line interface.

Usage:
    python3 run_benchmark.py --validate-only   # check pool + cases, no network
    python3 run_benchmark.py --estimate        # projected call count and cost, no network
    python3 run_benchmark.py --dry-run         # full pipeline offline, synthetic output only
    python3 run_benchmark.py --confirm         # real run against native provider APIs

A real run refuses to start without --confirm, and refuses to start while any
configured model ID is unverified. Both gates exist so that spending is reviewed
before any money is spent.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

from src import config, judge, leaderboard, models, pricing, runner


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run_benchmark.py",
        description="AIProductBench CN V1 — Chinese LLM selection benchmark for AI product teams.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--validate-only",
        action="store_true",
        help="validate the model pool and case schema, then exit without network access",
    )
    mode.add_argument(
        "--estimate",
        action="store_true",
        help="print projected call count and API cost, then exit without network access",
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="run the full pipeline offline with synthetic data; writes synthetic artifacts only",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="required for a real paid run against the configured native providers",
    )
    parser.add_argument("--cases", type=Path, default=config.DEFAULT_CASES_FILE)
    parser.add_argument(
        "--production-cases",
        action="store_true",
        help=(
            "use the production dataset path (data/cases_v1.json) instead of the "
            "synthetic framework fixture"
        ),
    )
    parser.add_argument("--models", type=Path, default=config.MODEL_POOL_FILE)
    parser.add_argument(
        "--output",
        type=Path,
        default=config.SAMPLE_RESULTS_FILE,
        help="results JSON path for a real run (default: sample_results.json)",
    )
    parser.add_argument(
        "--leaderboard-output",
        type=Path,
        default=config.LEADERBOARD_FILE,
        help="leaderboard HTML path for a real run (default: leaderboard.html)",
    )
    args = parser.parse_args(argv)
    if args.production_cases:
        args.cases = config.PRODUCTION_CASES_FILE
    return args


# --------------------------------------------------------------------------
# Reporting helpers
# --------------------------------------------------------------------------


def print_pool(pool: dict) -> None:
    facts = models.pool_facts(pool)
    print(f"Benchmark         : {config.BENCHMARK_NAME} {config.BENCHMARK_VERSION}")
    print(f"Model pool        : {facts['pool_version']}")
    print(
        f"Candidates        : {facts['candidate_count']} "
        f"across {len(facts['providers'])} provider(s), {len(facts['families'])} family(ies)"
    )
    print(f"  families        : {', '.join(facts['families'])}")
    print(f"  providers       : {', '.join(facts['providers'])}")
    print(f"  channels        : {', '.join(facts['inference_channels'])}")
    print(
        f"Judge pool        : {facts['judge_count']} judge(s) across families "
        f"{', '.join(facts['judge_families'])}"
    )
    print(f"  judge priority  : {' > '.join(facts['judge_priority']) or 'NOT CONFIGURED'}")
    print(f"  judges per response: {config.JUDGES_PER_RESPONSE} (leave-one-provider-out)")
    print(
        f"Registry          : {facts['registry_size']} shared model entries "
        "(candidates and judges are roles over one registry)"
    )
    print(f"Domains           : {len(config.DOMAINS)} — {', '.join(config.DOMAINS)}")
    print(f"Rubric dimensions : {', '.join(config.RUBRIC_DIMENSIONS)}")


def print_dataset(case_document: dict) -> None:
    from src import cases as cases_module

    case_list = cases_module.all_cases(case_document)
    print(f"Dataset           : {case_document.get('dataset_name')}")
    print(f"Dataset version   : {case_document.get('dataset_version')}")
    if case_document.get("synthetic"):
        print("Dataset type      : SYNTHETIC FIXTURE — not the production dataset")
    print(f"Cases loaded      : {len(case_list)} (production target: {config.TARGET_CASES})")
    for domain, count in cases_module.domain_distribution(case_list).items():
        print(f"  {domain:<36}: {count}")
    print(f"  difficulty      : {cases_module.distribution(case_list, 'difficulty')}")
    print(f"  language        : {cases_module.distribution(case_list, 'language')}")
    checks = sum(len(case.get('deterministic_checks') or []) for case in case_list)
    print(f"  deterministic checks declared: {checks}")


def print_credentials(pool: dict) -> None:
    print("Credentials (presence only, values are never read into results):")
    seen: set[str] = set()
    for row in runner.credential_status(pool):
        if row["env_var"] in seen:
            continue
        seen.add(row["env_var"])
        state = "present" if row["present"] else "NOT SET"
        print(f"  {row['env_var']:<22} {state}")


def print_pricing(pool: dict, fx_snapshot: dict | None, *, synthetic: bool) -> None:
    snapshot = pricing.pricing_snapshot(pool["models"], fx_snapshot, synthetic=synthetic)
    print(f"Display currency  : {snapshot['display_currency']}")
    fx = snapshot.get("fx_snapshot") or {}
    if fx.get("fx_rate"):
        print(
            f"FX snapshot       : {fx.get('fx_pair')} = {fx.get('fx_rate')} "
            f"({fx.get('fx_snapshot_date')}, {fx.get('status')})"
        )
    else:
        print("FX snapshot       : NOT CONFIGURED — non-CNY costs have no CNY value")
    verified = [entry for entry in snapshot["models"] if entry["status"] in ("verified", "synthetic")]
    unverified = [entry for entry in snapshot["models"] if entry["status"] not in ("verified", "synthetic")]
    print(f"Priced models     : {len(verified)} of {len(snapshot['models'])}")
    for entry in verified:
        schedule = entry.get("time_of_day")
        if schedule:
            print(
                f"  {entry['display_name']:<26} {entry['native_currency']} "
                f"peak {schedule['peak']['input']}/{schedule['peak']['output']}, "
                f"off-peak {schedule['off_peak']['input']}/{schedule['off_peak']['output']} per 1M"
            )
        else:
            print(
                f"  {entry['display_name']:<26} {entry['native_currency']} "
                f"{entry['input']}/{entry['output']} per 1M"
            )
    if unverified:
        print(f"Unpriced models   : {len(unverified)} — {', '.join(e['model_key'] for e in unverified)}")
    archive = models.historical_pricing(pool)
    if archive:
        print(
            f"Historical pricing: {len(archive.get('entries') or [])} retired V0.1-era "
            f"entr(y/ies), status '{archive.get('status')}' — NOT used for V1 cost"
        )


def print_judge_selection(pool: dict) -> None:
    priority = models.judge_priority(pool)
    print("== Judge selection ==")
    print(f"  fixed priority  : {' > '.join(priority) or 'NOT CONFIGURED'}")
    print("  rule            : exclude the candidate's own family/provider, then take the first two")
    seen_families: set[str] = set()
    for candidate in models.candidates(pool):
        family = candidate["model_family"]
        if family in seen_families:
            continue
        seen_families.add(family)
        selected = judge.select_judges(
            candidate, models.judges(pool), models.judge_priority(pool)
        )
        names = " + ".join(item["display_name"] for item in selected) or "UNAVAILABLE"
        print(f"  {family:<10} candidate -> {names}")


def run_validation(args: argparse.Namespace, pool: dict, case_document: dict, result: dict) -> int:
    print("== Model pool ==")
    print_pool(pool)
    print()
    print("== Dataset ==")
    print_dataset(case_document)
    print()
    print("== Credentials ==")
    print_credentials(pool)
    print()
    print("== Pricing ==")
    print_pricing(pool, config.FX_SNAPSHOT, synthetic=False)
    print()
    print_judge_selection(pool)
    print()

    if result["warnings"]:
        print("== Warnings ==")
        for warning in result["warnings"]:
            print(f"  - {warning}")
        print()

    if result["errors"]:
        print("== Validation failed ==")
        for error in result["errors"]:
            print(f"  - {error}")
        return 1

    print("== Validation passed ==")
    print("  Model pool and case schema are valid for the V1 framework.")
    blockers = runner.check_ready_for_paid_run(pool)
    if blockers:
        print("  Paid run status: BLOCKED")
        for blocker in blockers:
            print(f"    - {blocker}")
    else:
        print("  Paid run status: model IDs verified (credentials still required).")
    return 0


# --------------------------------------------------------------------------
# Projection
# --------------------------------------------------------------------------


def project_run(pool: dict, case_document: dict, fx_snapshot: dict | None, *, synthetic: bool) -> dict:
    """Rough, clearly-labelled projection. Never written into result artifacts."""
    from src import cases as cases_module

    case_list = cases_module.all_cases(case_document)
    candidate_models = models.candidates(pool)
    judge_models = models.judges(pool)

    assumed_candidate_output = 600
    assumed_judge_output = 150
    rubric_overhead_tokens = 800

    per_model = []
    errors: list[str] = []
    unpriced: list[str] = []

    for model in candidate_models:
        input_tokens = sum(max(1, len(case["prompt"]) // 4) for case in case_list)
        output_tokens = assumed_candidate_output * len(case_list)
        try:
            at = pricing_reference_time() if model["pricing"].get("time_of_day") else None
            native = pricing.native_price_call(
                model, input_tokens, output_tokens, at=at, synthetic=synthetic
            )
            native_cost = native["native_cost"]
        except pricing.PricingError as exc:
            native_cost = None
            unpriced.append(model["key"])
            if "time of day" in str(exc):
                errors.append(f"{model['key']}: {exc}")
        per_model.append(
            {
                "key": model["key"],
                "display_name": model["display_name"],
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "native_cost": native_cost,
                "native_currency": model["pricing"].get("native_currency"),
            }
        )

    judge_calls = len(case_list) * len(candidate_models) * config.JUDGES_PER_RESPONSE
    judge_input_tokens = (
        sum(
            max(1, len(case["prompt"]) // 4) + assumed_candidate_output + rubric_overhead_tokens
            for case in case_list
        )
        * len(candidate_models)
    )
    judge_output_tokens = assumed_judge_output * judge_calls

    judge_cost = None
    if judge_models:
        judge_input_per_judge = judge_input_tokens / max(1, len(candidate_models))
        judge_output_per_judge = judge_output_tokens / max(1, judge_calls)
        totals = []
        for judge in judge_models:
            try:
                native = pricing.native_price_call(
                    judge,
                    judge_input_per_judge,
                    judge_output_per_judge,
                    at=pricing_reference_time() if judge["pricing"].get("time_of_day") else None,
                    synthetic=synthetic,
                )
            except pricing.PricingError:
                continue
            if native["native_cost"] is not None:
                totals.append(native["native_cost"])
        judge_cost = round(sum(totals) / len(totals) * judge_calls, 8) if totals else None

    candidate_total = None
    if per_model and all(row["native_cost"] is not None for row in per_model):
        candidate_total = round(sum(row["native_cost"] for row in per_model), 8)

    normalized = pricing.normalize_to_cny(candidate_total, "USD", fx_snapshot)

    return {
        "candidate_calls": len(case_list) * len(candidate_models),
        "judge_calls": judge_calls,
        "total_calls": len(case_list) * len(candidate_models) + judge_calls,
        "per_model": per_model,
        "candidate_input_tokens": sum(row["input_tokens"] for row in per_model),
        "candidate_output_tokens": sum(row["output_tokens"] for row in per_model),
        "judge_input_tokens": judge_input_tokens,
        "judge_output_tokens": judge_output_tokens,
        "candidate_cost_native_total": candidate_total,
        "judge_cost_native_total": judge_cost,
        "candidate_cost_cny": normalized["normalized_cost_cny"],
        "cny_note": normalized["normalization_note"],
        "unpriced_models": unpriced,
        "errors": errors,
    }


def pricing_reference_time() -> dt.datetime:
    """A weekday instant inside any published peak window, for projections."""
    day = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)
    while day.weekday() != 0:
        day += dt.timedelta(days=1)
    return day.replace(hour=2)


def print_projection(projection: dict, pool: dict, fx_snapshot: dict | None, *, synthetic: bool) -> int:
    print("== Projected real-run cost ==")
    print(
        f"  candidate calls : {projection['candidate_calls']} "
        f"({projection['candidate_calls'] // max(1, len(models.candidates(pool)))} cases x "
        f"{len(models.candidates(pool))} models)"
    )
    print(f"  judge calls     : {projection['judge_calls']} "
          f"({config.JUDGES_PER_RESPONSE} judges per response)")
    print(f"  total API calls : {projection['total_calls']}")
    print()
    print(
        f"  est. candidate tokens : {projection['candidate_input_tokens']:,} in / "
        f"{projection['candidate_output_tokens']:,} out"
    )
    print(
        f"  est. judge tokens     : {projection['judge_input_tokens']:,} in / "
        f"{projection['judge_output_tokens']:,} out"
    )
    print()

    if projection["candidate_cost_native_total"] is None:
        print("  est. candidate cost   : NOT AVAILABLE")
        print(
            f"  Reason: {len(projection['unpriced_models'])} of "
            f"{len(projection['per_model'])} candidate models have no verified pricing."
        )
        print("  Action: complete the pricing snapshot in data/models_v1.json before a paid run.")
    else:
        print(
            f"  est. candidate cost   : {projection['candidate_cost_native_total']:.6f} "
            "(native currency total across all candidates)"
        )
    if projection["judge_cost_native_total"] is not None:
        print(
            f"  est. judge cost       : {projection['judge_cost_native_total']:.6f} "
            "(native currency, evaluation overhead, reported separately)"
        )
    else:
        print("  est. judge cost       : NOT AVAILABLE (judge pricing not verified)")

    if projection["candidate_cost_cny"] is not None:
        print(f"  est. candidate cost   : CNY {projection['candidate_cost_cny']:.6f}")
    else:
        print(f"  est. candidate cost in CNY : UNAVAILABLE — {projection['cny_note']}")

    print()
    print("  Note: token counts above are rough planning estimates only.")
    print("        Only real provider usage reported by the APIs is recorded in results.")
    return 0


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        pool = runner.load_model_pool(args.models)
    except FileNotFoundError:
        print(f"FAIL: model pool not found: {args.models}")
        return 1
    except ValueError as exc:
        print(f"FAIL: model pool is not valid JSON: {exc}")
        return 1

    try:
        case_document = runner.load_test_cases(args.cases)
    except FileNotFoundError:
        print(f"FAIL: case file not found: {args.cases}")
        return 1
    except ValueError as exc:
        print(f"FAIL: case file is not valid JSON: {exc}")
        return 1

    result = runner.validate_all(case_document, pool)

    if args.validate_only:
        return run_validation(args, pool, case_document, result)

    if result["errors"]:
        print("== Validation failed ==")
        for error in result["errors"]:
            print(f"  - {error}")
        return 1

    if args.estimate:
        print_pool(pool)
        print()
        print_dataset(case_document)
        print()
        projection = project_run(pool, case_document, config.FX_SNAPSHOT, synthetic=False)
        return print_projection(projection, pool, config.FX_SNAPSHOT, synthetic=False)

    if args.dry_run:
        from src import leaderboard as leaderboard_module

        print("== Dry run (offline, synthetic) ==")
        print("  No network calls are made and no API cost is incurred.")
        print("  Synthetic pricing and FX fixtures are used so cost paths are exercised.")
        print()
        document = runner.run_benchmark(
            case_document,
            pool,
            dry_run=True,
            fx_snapshot=config.SYNTHETIC_FX_SNAPSHOT,
        )
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        results_path = config.RESULTS_DIR / f"dry_run_{stamp}.json"
        leaderboard_path = config.RESULTS_DIR / f"dry_run_{stamp}_leaderboard.html"

        runner.write_json(document, results_path)
        leaderboard_module.write(
            document,
            leaderboard_path,
            banner="Synthetic dry-run artifact. Not a real benchmark result.",
        )
        runner.print_summary(document)
        print()
        print(f"  synthetic results    : {results_path}")
        print(f"  synthetic leaderboard: {leaderboard_path}")
        print()
        print("  sample_results.json and leaderboard.html were NOT written.")
        return 0 if not document["failures"] else 1

    if not args.confirm:
        print("== Real run requires approval ==")
        print("  This would call native provider APIs and incur real API cost.")
        print()
        print_pool(pool)
        print()
        projection = project_run(pool, case_document, config.FX_SNAPSHOT, synthetic=False)
        print_projection(projection, pool, config.FX_SNAPSHOT, synthetic=False)
        print()
        blockers = runner.check_ready_for_paid_run(pool)
        if blockers:
            print("  BLOCKED:")
            for blocker in blockers:
                print(f"    - {blocker}")
        print("  Stopped before spending. Re-run with --confirm once approved.")
        return 2

    blockers = runner.check_ready_for_paid_run(pool)
    if blockers:
        print("== Paid run refused ==")
        for blocker in blockers:
            print(f"  - {blocker}")
        return 3

    print("== Real benchmark run ==")
    print_pool(pool)
    print()
    document = runner.run_benchmark(
        case_document, pool, dry_run=False, fx_snapshot=config.FX_SNAPSHOT
    )
    runner.write_json(document, args.output)
    leaderboard.write(document, args.leaderboard_output)
    runner.print_summary(document)
    print()
    print(f"  results     : {args.output}")
    print(f"  leaderboard : {args.leaderboard_output}")
    return 0 if not document["failures"] else 1


if __name__ == "__main__":
    sys.exit(main())
