#!/usr/bin/env python3
"""AIProductBench V0.1 command line interface.

Usage:
    python3 run_benchmark.py --validate-only   # check configuration and cases, no network
    python3 run_benchmark.py --estimate        # projected call count and cost, no network
    python3 run_benchmark.py --dry-run         # full pipeline offline, synthetic output only
    python3 run_benchmark.py --confirm         # real run against both providers

A real run refuses to start without --confirm. That gate exists so that the
projected API cost is reviewed before any money is spent.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

from src import config, leaderboard, runner


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run_benchmark.py",
        description="AIProductBench V0.1 — a lightweight LLM benchmark for AI product work.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--validate-only",
        action="store_true",
        help="validate configuration and the 10 test cases, then exit without network access",
    )
    mode.add_argument(
        "--estimate",
        action="store_true",
        help="print projected call count and API cost, then exit without network access",
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="run the full pipeline offline with synthetic responses; writes only synthetic artifacts",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="required for a real paid run against the configured providers",
    )
    parser.add_argument("--cases", type=Path, default=config.TEST_CASES_FILE)
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
    return parser.parse_args(argv)


def print_configuration() -> None:
    print(f"Benchmark version : {config.BENCHMARK_VERSION}")
    print("Evaluated models  :")
    for model in config.MODELS:
        print(
            f"  - {model['display_name']:<18} provider={model['provider']:<9} "
            f"model={model['model']}  key=${model['api_key_env']}"
        )
    print(
        f"Judge             : {config.JUDGE['display_name']} "
        f"(model={config.JUDGE['model']}, prompt v{config.JUDGE_PROMPT_VERSION})"
    )
    repro = config.REPRODUCIBILITY
    print(
        f"Snapshots         : Qwen candidate {repro['qwen_candidate_snapshot']}, "
        f"Qwen judge {repro['qwen_judge_snapshot']}, "
        f"DeepSeek {repro['deepseek_api_model_id']} (not date-pinned)"
    )
    print(f"Domains           : {', '.join(config.DOMAINS)}")
    print(f"Rubric dimensions : {', '.join(config.RUBRIC_DIMENSIONS)}")


def run_validation(path: Path) -> int:
    print("== Configuration ==")
    print_configuration()
    print()

    print("== Test cases ==")
    try:
        document = runner.load_test_cases(path)
    except FileNotFoundError:
        print(f"FAIL: test case file not found: {path}")
        return 1
    except ValueError as exc:
        print(f"FAIL: test case file is not valid JSON: {exc}")
        return 1

    case_errors = runner.validate_test_cases(document)
    config_errors = runner.validate_configuration()
    errors = case_errors + config_errors

    distribution = runner.domain_distribution(document)
    print(f"  loaded           : {len(document.get('test_cases', []))} test cases from {path}")
    for domain in config.DOMAINS:
        print(f"  {domain:<22}: {distribution[domain]}")

    print()
    print("== Credentials (presence only, values are never read into results) ==")
    for row in runner.credential_status():
        state = "present" if row["present"] else "NOT SET"
        print(f"  {row['display_name']:<18} {row['env_var']:<20} {state}")

    print()
    print("== Pricing ==")
    region = runner.pricing_region()
    print(f"  base URL          : {region['base_url']}")
    print(f"  DashScope region  : {region['label']} ({region['key'] or 'unidentified'})")
    print(f"  snapshot date     : {config.PRICING_SNAPSHOT_DATE} (official list pricing)")
    for entry in config.pricing_snapshot()["resolved_rates"]:
        if entry["pricing_model"] == "time_of_day":
            if not entry["windows"]:
                print(f"  {entry['display_name']:<18}: UNRESOLVED — {entry['basis']}")
                continue
            off_peak = entry["windows"]["off_peak"]
            peak = entry["windows"]["peak"]
            print(
                f"  {entry['display_name']:<18}: input ${off_peak['input']}/1M off-peak, "
                f"${peak['input']}/1M peak; output ${off_peak['output']}/1M off-peak, "
                f"${peak['output']}/1M peak"
            )
        elif entry["input"] is None:
            print(f"  {entry['display_name']:<18}: UNRESOLVED — {entry['basis']}")
        else:
            print(
                f"  {entry['display_name']:<18}: input ${entry['input']}/1M, "
                f"output ${entry['output']}/1M"
            )
            if entry["input_tier_limit_tokens"]:
                print(
                    f"    note: valid for request inputs at or below "
                    f"{entry['input_tier_limit_tokens']:,} tokens"
                )

    print()
    if errors:
        print("== Validation failed ==")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("== Validation passed ==")
    print("  10 cases across 3 domains, exactly 2 evaluated models, exactly 1 judge.")
    return 0


def project_run(document: dict) -> dict:
    """Rough, clearly-labelled projection. Never written into result artifacts."""
    cases = document["test_cases"]
    model_count = len(config.MODELS)

    # Rough English heuristic: about four characters per token. Responses are
    # assumed to be comfortably below the configured output cap.
    assumed_candidate_output = 400
    assumed_judge_output = 120
    rubric_overhead_tokens = 700

    candidate_input = sum(max(1, len(case["prompt"]) // 4) for case in cases) * model_count
    candidate_output = assumed_candidate_output * len(cases) * model_count
    judge_input = (
        sum(
            max(1, len(case["prompt"]) // 4)
            + assumed_candidate_output
            + rubric_overhead_tokens
            for case in cases
        )
        * model_count
    )
    judge_output = assumed_judge_output * len(cases) * model_count

    peak_at, off_peak_at = config.weekday_window_times()
    errors: list[str] = []
    per_model = []

    for model in config.MODELS:
        input_tokens = candidate_input / model_count
        output_tokens = candidate_output / model_count
        row = {"display_name": model["display_name"], "model_id": model["model"], "windows": {}}
        try:
            if model["provider"] == "deepseek":
                row["windows"]["peak"] = config.price_call(
                    model["model"], input_tokens, output_tokens, at=peak_at
                )["cost_usd"]
                row["windows"]["off-peak"] = config.price_call(
                    model["model"], input_tokens, output_tokens, at=off_peak_at
                )["cost_usd"]
            else:
                row["windows"]["standard"] = config.price_call(
                    model["model"], input_tokens, output_tokens, at=peak_at
                )["cost_usd"]
        except config.PricingError as exc:
            errors.append(f"{model['display_name']}: {exc}")
        values = [value for value in row["windows"].values() if value is not None]
        row["cost_min"] = min(values) if values else None
        row["cost_max"] = max(values) if values else None
        per_model.append(row)

    try:
        judge_cost = config.price_call(
            config.JUDGE["model"], judge_input, judge_output, at=peak_at
        )["cost_usd"]
    except config.PricingError as exc:
        errors.append(f"{config.JUDGE['display_name']}: {exc}")
        judge_cost = None

    candidate_min = (
        round(sum(row["cost_min"] for row in per_model), 6)
        if per_model and all(row["cost_min"] is not None for row in per_model)
        else None
    )
    candidate_max = (
        round(sum(row["cost_max"] for row in per_model), 6)
        if per_model and all(row["cost_max"] is not None for row in per_model)
        else None
    )
    total_min = (
        round(candidate_min + judge_cost, 6)
        if candidate_min is not None and judge_cost is not None
        else None
    )
    total_max = (
        round(candidate_max + judge_cost, 6)
        if candidate_max is not None and judge_cost is not None
        else None
    )

    return {
        "candidate_calls": len(cases) * model_count,
        "judge_calls": len(cases) * model_count,
        "total_calls": len(cases) * model_count * 2,
        "candidate_input_tokens": candidate_input,
        "candidate_output_tokens": candidate_output,
        "judge_input_tokens": judge_input,
        "judge_output_tokens": judge_output,
        "per_model": per_model,
        "candidate_cost_min_usd": candidate_min,
        "candidate_cost_max_usd": candidate_max,
        "judge_cost_usd": judge_cost,
        "total_cost_min_usd": total_min,
        "total_cost_max_usd": total_max,
        "errors": errors,
    }


def print_projection(document: dict) -> int:
    projection = project_run(document)
    snapshot = config.pricing_snapshot()
    region = runner.pricing_region()

    print("== Projected real-run cost ==")
    print(f"  candidate model calls : {projection['candidate_calls']} "
          f"({len(document['test_cases'])} cases x {len(config.MODELS)} models)")
    print(f"  judge calls           : {projection['judge_calls']}")
    print(f"  total API calls       : {projection['total_calls']}")
    print()
    print(f"  est. candidate tokens : {projection['candidate_input_tokens']:,} in / "
          f"{projection['candidate_output_tokens']:,} out")
    print(f"  est. judge tokens     : {projection['judge_input_tokens']:,} in / "
          f"{projection['judge_output_tokens']:,} out")
    print()

    if projection["errors"]:
        print("  est. cost             : NOT AVAILABLE")
        for error in projection["errors"]:
            print(f"  Reason: {error}")
    else:
        for row in projection["per_model"]:
            windows = ", ".join(f"{k} ${v:.6f}" for k, v in row["windows"].items())
            print(f"  {row['display_name']:<18}: {windows}")
        print()
        if projection["candidate_cost_min_usd"] == projection["candidate_cost_max_usd"]:
            print(f"  est. candidate cost   : ${projection['candidate_cost_min_usd']:.6f}")
        else:
            print(f"  est. candidate cost   : ${projection['candidate_cost_min_usd']:.6f} "
                  f"- ${projection['candidate_cost_max_usd']:.6f}")
        print(f"  est. judge cost       : ${projection['judge_cost_usd']:.6f} "
              "(evaluation overhead, reported separately)")
        if projection["total_cost_min_usd"] == projection["total_cost_max_usd"]:
            print(f"  est. total cost       : ${projection['total_cost_min_usd']:.6f}")
        else:
            print(f"  est. total cost       : ${projection['total_cost_min_usd']:.6f} "
                  f"- ${projection['total_cost_max_usd']:.6f} "
                  "(range spans DeepSeek peak and off-peak pricing)")

    print()
    print(f"  pricing snapshot      : {snapshot['date']}, official list pricing")
    print(f"  DashScope region      : {region['label']}")
    print(f"  DeepSeek peak (UTC)   : {', '.join(snapshot['deepseek_peak_windows_utc'])}, Mon-Fri")
    print()
    print("  Note: token counts above are rough estimates for planning only.")
    print("        Only real provider usage reported by the APIs is recorded in results.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        document = runner.load_test_cases(args.cases)
    except FileNotFoundError:
        print(f"FAIL: test case file not found: {args.cases}")
        return 1
    except ValueError as exc:
        print(f"FAIL: test case file is not valid JSON: {exc}")
        return 1

    errors = runner.validate_test_cases(document) + runner.validate_configuration()

    if args.validate_only:
        return run_validation(args.cases)

    if errors:
        print("== Validation failed ==")
        for error in errors:
            print(f"  - {error}")
        return 1

    if args.estimate:
        print_configuration()
        print()
        return print_projection(document)

    if args.dry_run:
        print("== Dry run (offline, synthetic) ==")
        print("  No network calls are made and no API cost is incurred.")
        print()
        results = runner.run_benchmark(document, dry_run=True)
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        results_path = config.RESULTS_DIR / f"dry_run_{stamp}.json"
        leaderboard_path = config.RESULTS_DIR / f"dry_run_{stamp}_leaderboard.html"

        runner.write_json(results, results_path)
        leaderboard.write(
            results,
            leaderboard_path,
            banner="Synthetic dry-run artifact. Not a real benchmark result.",
        )
        runner.print_summary(results)
        print()
        print(f"  synthetic results   : {results_path}")
        print(f"  synthetic leaderboard: {leaderboard_path}")
        print()
        print("  sample_results.json and leaderboard.html were NOT written.")
        return 0 if not results["failures"] else 1

    if not args.confirm:
        print("== Real run requires approval ==")
        print("  This would call both providers and incur real API cost.")
        print()
        print_configuration()
        print()
        print_projection(document)
        print()
        print("  Stopped before spending. Re-run with --confirm once the projected")
        print("  cost above has been reviewed and approved.")
        return 2

    print("== Real benchmark run ==")
    print_configuration()
    print()
    results = runner.run_benchmark(document, dry_run=False)
    runner.write_json(results, args.output)
    leaderboard.write(results, args.leaderboard_output)
    runner.print_summary(results)
    print()
    print(f"  results     : {args.output}")
    print(f"  leaderboard : {args.leaderboard_output}")
    return 0 if not results["failures"] else 1


if __name__ == "__main__":
    sys.exit(main())
