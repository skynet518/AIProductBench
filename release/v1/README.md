# AIProductBench CN V1 — Public Release Artifacts

This directory holds the **canonical V1 public release artifacts** for
AIProductBench CN. They are published from one audited official run and are the
figures referenced by the root [README](../../README.md).

## Source run

| Field | Value |
| --- | --- |
| Run ID | `official-v1-20260911T103838Z` |
| Run kind | `official_full_run` (canonical) |
| Execution commit | `f3225f51824f4e3c047b2df3c15092a803231291` |
| Runtime baseline commit | `e10ceb0aa89483050ec0b09eb96e7d16c37e4e09` |
| Dataset semantic manifest | `6b450383e528a5a0a6b813112f96182a3625c04c948839fc551c8ded63da513c` |
| Registry snapshot | `v1-registry-2026-09-11.3` |
| Registry SHA-256 | `259b02adb05f73ab2d800c8f41d9b2608b8eddb17ae97e9d3f31ecff79409eab` |
| Pricing snapshot | `v1-pricing-2026-09-11.1` |
| Pricing SHA-256 | `9f7af42243e5e0b78b1776934de5483f0e3e650765a19dd929e78af10aa15c42` |
| FX snapshot | `ecb-2026-09-10-usd-cny` (USD/CNY 6.706267217630854) |

## Canonical spend

| Component | CNY |
| --- | --- |
| Candidate inference | 45.05535164 |
| Judge evaluation | 64.67647388 |
| **Total canonical API spend** | **109.73182552** |

The hard cost ceiling was 150.00 CNY. Candidate and judge spend are recorded
separately and are never mixed. This canonical spend covers the official run
only; aborted-run, smoke, probe, and runtime-envelope validation spend is
excluded.

## Execution completeness

| Field | Value |
| --- | --- |
| `execution_complete` | `true` |
| `all_models_complete` | `false` |
| Officially ranked models | 4 / 10 |

Every planned paid unit was attempted and persisted: 500/500 candidate
evaluations and 990/990 judge evaluations (1,490 formal evaluation units). A
model is ranked only when all 50 production cases have a valid candidate result
and both intended cross-family judges returned a valid verdict. Six models are
INCOMPLETE under that frozen rule; that is a benchmark result, not unfinished
execution.

Human calibration sample prepared. Human review pending. V1 is **not**
human-calibrated.

## Files

| File | Contents |
| --- | --- |
| `leaderboard.csv` | Official ranking table (complete models) plus incomplete-model diagnostics |
| `leaderboard.json` | Full per-model aggregated metrics |
| `leaderboard.html` | Self-contained HTML report |
| `pareto.json` | Quality × cost and quality × cost × latency frontiers |
| `cost_summary.json` | Candidate / judge / total spend and per-model cost |
| `latency_summary.json` | Candidate and judge latency, reported separately |
| `judge_disagreement.json` | Dual-judge agreement histogram and widest disagreements |
| `sample_results.json` | Compact sample of real official-run outputs |
| `run_manifest.json` | Run provenance, snapshots, execution envelope, cost control |

## Not included

Raw checkpoints, full internal `candidate_results` / `judge_results` dumps, the
aborted earlier official run, smoke and probe artifacts, temporary diagnostics,
and any credential material are intentionally **not** published here. The full
internal run directory is kept locally under `results/`, which is git-ignored.

See [docs/METHODOLOGY_V1.md](../../docs/METHODOLOGY_V1.md) for evaluation
design and [docs/PRODUCT_SPEC_V1.md](../../docs/PRODUCT_SPEC_V1.md) for frozen
scope.
