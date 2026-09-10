# AIProductBench CN

**A practical model-selection benchmark for Chinese LLMs, built for AI product
teams choosing models under real quality, cost, and latency constraints.**

> **Status: AIProductBench CN V1 is in development and has not been released.**
> No live benchmark has been run. Every artifact currently produced by this
> repository is synthetic dry-run output. The 50-case production dataset does not
> exist yet.

## Version status

| Version | Status |
| --- | --- |
| V0.1 | Internal engineering scaffold. Complete. Not for public release. |
| AIProductBench CN V1 | In development. The intended public release. |

V0.1 proved the pipeline could run end to end with 2 models, 3 domains, 1 judge,
and 10 cases. It is preserved in git history as the
`chore: checkpoint v0.1 benchmark scaffold` commit and is not a published
result.

## What V1 answers

> Which model should an AI product team choose for a given workload, budget,
> quality requirement, and latency requirement?

The deliverable is a decision surface, not a single winner: which models are
defensible choices, what each one costs in RMB, and what quality and latency you
give up by choosing it. Results are presented as a Pareto frontier over
quality × cost rather than a rank-only list.

## Project documentation

| Document | Contents |
| --- | --- |
| [docs/PRODUCT_SPEC_V1.md](docs/PRODUCT_SPEC_V1.md) | Frozen V1 scope, positioning, out-of-scope list |
| [docs/METHODOLOGY_V1.md](docs/METHODOLOGY_V1.md) | Dataset design, judges, metrics, Pareto analysis |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Pipeline, module responsibilities, config schema |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Chronological decision log with rationale |
| [docs/HANDOFF.md](docs/HANDOFF.md) | Current operational status — read first |

## Repository layout

```
.
├── run_benchmark.py                     # CLI
├── data/
│   ├── models_v1.json                   # configurable candidate + judge pool
│   ├── fixtures/synthetic_v1_cases.json # synthetic, framework-validation only
│   └── archive/test_cases_v0_1.json     # preserved V0.1 dataset
├── src/
│   ├── config.py          # paths, versions, 5 domains, rubric, request policy
│   ├── models.py          # model pool load + validation, family vs provider
│   ├── cases.py           # case schema load + validation
│   ├── providers.py       # one provider-native HTTP client + offline client
│   ├── deterministic.py   # machine-checkable constraint evaluation
│   ├── judge.py           # judge pool, leave-one-provider-out, strict parsing
│   ├── pricing.py         # native price, tiering, time-of-day, CNY normalization
│   ├── analytics.py       # latency percentiles, cost metrics, Pareto frontier
│   ├── runner.py          # orchestration and snapshot assembly
│   └── leaderboard.py     # standalone leaderboard.html renderer
├── tests/                 # standard-library unittest suite
└── results/               # local artifacts, git-ignored
```

## Quickstart

Requires Python 3.10 or newer. The only dependency is `requests`.

```bash
pip install -r requirements.txt

python3 run_benchmark.py --validate-only   # check model pool + case schema, no network
python3 run_benchmark.py --estimate        # projected call count and cost, no network
python3 run_benchmark.py --dry-run         # full pipeline offline, synthetic output only
python3 run_benchmark.py --confirm         # real run against native provider APIs

python3 -m unittest discover -s tests -v   # framework test suite
```

Credentials come from environment variables only — one per provider, named in
`data/models_v1.json` (`DASHSCOPE_API_KEY`, `DEEPSEEK_API_KEY`,
`MOONSHOT_API_KEY`, `MINIMAX_API_KEY`, `ZHIPU_API_KEY`, `ARK_API_KEY`). Nothing
in this repository reads API keys from Codex configuration files, shell history,
or any other file on disk.

## Evaluation design (summary)

Full detail in [docs/METHODOLOGY_V1.md](docs/METHODOLOGY_V1.md).

- **50 cases** across **5 domains**, 10 per domain: `instruction_constraint_following`,
  `structured_information_analysis`, `product_reasoning_decision`,
  `chinese_business_communication`, `agent_workflow_planning`. Approximately 40
  Chinese-first. Each domain is 2 easy / 5 medium / 3 hard.
- **Hybrid evaluation.** Deterministic checks wherever a constraint is objectively
  machine-checkable (`constraint_pass_rate`), plus LLM evaluation for judgment.
  Neither overrides the other; both are reported. The evaluator implements 18
  check types, listed in [docs/METHODOLOGY_V1.md](docs/METHODOLOGY_V1.md).
- **Cross-family dual judging.** Two judges score every response, never from the
  candidate's own model family or provider. Judge selection follows a fixed
  priority from configuration — Qwen → DeepSeek + GLM, DeepSeek → Qwen + GLM,
  GLM/Kimi/MiniMax/Doubao → Qwen + DeepSeek — so unrelated candidates are never
  scored by different judge pairs. Judge agreement is published.
- **Metrics.** `quality_score`, `constraint_pass_rate`, `task_success_rate`,
  `overall_score`, `avg`/`p50`/`p95` latency, input/output/reasoning tokens,
  `candidate_inference_cost`, `judge_evaluation_cost`, `cost_per_100_tasks`,
  `quality_per_cny`, `judge_agreement`.
- **RMB presentation.** Native provider price and currency are preserved;
  `normalized_cost_cny` is produced only when it can be produced honestly.

## Model pool

The pool is **one shared registry**, not code — 10 model entries across 6 Chinese
providers (Alibaba, DeepSeek, Moonshot, MiniMax, Zhipu, ByteDance), of which 3
are also judge-eligible, declared in [data/models_v1.json](data/models_v1.json).
There are no judge-only duplicate entries: a model may be both a candidate and a
judge, and those two roles produce strictly separate cost and latency metrics.

Each entry distinguishes **model family** (who trained the model) from
**inference provider / channel** (who serves it), and carries product tier,
inference channel, thinking mode, model-ID verification status, and pricing
metadata. No benchmark logic branches on a model name.

> **All literal model IDs must be verified against provider-native documentation
> before any paid run.** Unverified entries are deliberately `null` rather than
> guessed, and a real run refuses to start while any remain unverified.

> **All active V1 pricing is currently unresolved.** Every model is unpriced.
> Prices verified during the V0.1 review were verified for different model IDs
> and are retired into a `historical_pricing_archive` marked
> `historical_inactive`; they are never used for V1 cost reporting. A paid run is
> refused while active pricing is unresolved.

## Currency and cost honesty

- Native price and native currency are always preserved.
- A price published in CNY is used directly. No conversion.
- Any other currency requires an explicit, dated FX snapshot with a named source.
  Without one, the CNY value is `null` with a stated reason — never a silently
  converted number, and never a hard-coded permanent rate.
- Candidate inference cost and judge evaluation cost are separate fields from
  collection through aggregation to the leaderboard.
- Missing provider metrics are recorded as `null`. Nothing is estimated into a
  result.

## Artifacts

| Path | Contents |
| --- | --- |
| `sample_results.json` | Canonical results document from an approved real run (not generated yet) |
| `leaderboard.html` | Self-contained HTML report (not generated yet) |
| `results/` | Local, git-ignored artifacts; dry runs write here |

Dry-run output is flagged `synthetic: true` throughout, carries a synthetic
banner, and never overwrites `sample_results.json` or `leaderboard.html`.
Synthetic pricing and FX fixtures are placeholders for exercising the offline
pipeline and are never presented as published values.

## Known limitations

- Approximately 10 models and 50 cases is a practical benchmark, not a
  scientific one. V1 does not perform repeated sampling or significance testing.
- Two cross-family judges reduce judge-family bias and make it measurable; they
  do not eliminate it.
- Human calibration of roughly 10% of responses is planned, not yet performed.
  No agreement figures are published until real human review exists.
- Pricing is a dated manual snapshot, not a live billing feed.
- Models whose API model ID is not a dated snapshot are not reproducible against
  the same weights.
- Latency depends on provider load, region, and network path.

## Out of scope for V1

Vision and multimodal input, coding, RAG, live web search, real tool execution,
multi-agent execution, fine-tuning, production routing, and any hosted backend.
These are documented as V1.1/V2 candidates in
[docs/PRODUCT_SPEC_V1.md](docs/PRODUCT_SPEC_V1.md).

## License

MIT — see [LICENSE](LICENSE).
