# AIProductBench CN

**Practical Chinese LLM Model Selection Benchmark for AI Product Teams**

**面向中国 AI 产品团队的模型选型基准**

AIProductBench CN is a practical model-selection benchmark for Chinese LLMs. It
is built for AI product managers, LLM product teams, AI engineers, and
model-selection / evaluation teams who have to choose a model under real
quality, cost, and latency constraints.

It is **not primarily a leaderboard.** The core product question is:

> Which model should a Chinese AI product team choose for a given workload,
> quality target, cost budget, and latency requirement?

The deliverable is a decision surface — a Pareto view over quality × cost ×
latency — not a single winner.

## V1 at a glance

| 10 Models | 6 Providers | 50 Production Tasks | 5 Workload Domains |
| --- | --- | --- | --- |
| **500 Candidate Evaluations** | **990 Cross-family Judge Evaluations** | **1,490 Formal Evaluation Units** | **¥109.73 Canonical API Spend** |

## V1 results

Canonical run `official-v1-20260911T103838Z` — 10 models, 6 providers, 50 real
production tasks, 5 workload domains.

| Result | Value |
| --- | --- |
| Best overall quality | **Kimi K3 — 96.3334** |
| Near-equal quality, strongest cost/latency trade-off | **DeepSeek V4 Flash — 96.3326** |
| DeepSeek V4 Flash | **¥1.48 / 100 tasks**, **11.0s median candidate latency** |
| Official Pareto frontier (quality × cost, and quality × cost × latency) | **Kimi K3 + DeepSeek V4 Flash** |
| Officially ranked | **4 / 10 models** |

Kimi K3 holds the highest official overall quality. DeepSeek V4 Flash is the
cheaper, faster choice on the frontier; it is **not** claimed to have higher
quality than Kimi K3.

## Product insight

Kimi K3 achieved the highest official overall quality. DeepSeek V4 Flash was
only 0.0008 points lower in exact overall score while being dramatically
cheaper and faster in this benchmark. A 0.0008-point gap is not a meaningful
separation on its own — V1 does not run repeated sampling or significance
testing, and it does not claim this difference is statistically significant.
The point is the decision: near-equal measured quality came with roughly an 18×
cost difference and a 4× latency difference, so model selection should not be
based on quality ranking alone.

## Benchmark design

Full detail in [docs/METHODOLOGY_V1.md](docs/METHODOLOGY_V1.md) and
[docs/CASE_DESIGN_STANDARD_V1.md](docs/CASE_DESIGN_STANDARD_V1.md).

**50 frozen production tasks**, 10 per domain, across five workload domains:

| # | Domain | Key |
| --- | --- | --- |
| 1 | Instruction & Constraint Following | `instruction_constraint_following` |
| 2 | Structured Information Analysis | `structured_information_analysis` |
| 3 | Product Reasoning & Decision | `product_reasoning_decision` |
| 4 | Chinese Business Communication | `chinese_business_communication` |
| 5 | Agent Workflow Planning | `agent_workflow_planning` |

**Hybrid evaluation.** Deterministic checks score every objectively
machine-checkable constraint, and cross-family dual LLM judges score every
response. Neither overrides the other; both are reported.

* **Judge dimensions:** Task Completion, Reasoning Quality, Instruction
  Following.
* **Cross-family dual judging:** every response is scored by two judges from
  other model families — there is no same-family judge substitution.
* **21 deterministic check types**, reported as `constraint_pass_rate`
  alongside the judged quality score.

## Model pool

10 candidate models across 6 provider API integrations, declared in
[data/model_registry_snapshot_v1.json](data/model_registry_snapshot_v1.json).
No benchmark logic branches on a model name or provider name.

| Provider | Models |
| --- | --- |
| Qwen | `qwen3.8-max`, `qwen3.8-flash` |
| DeepSeek | `deepseek-v4-pro`, `deepseek-v4-flash` |
| Kimi | `kimi-k3`, `kimi-k2.6` |
| MiniMax | `MiniMax-M3` |
| GLM | `glm-5.3`, `glm-5.3-flash` |
| Doubao | `doubao-seed-2-1-pro-260628` |

## Official ranking (complete models)

Only models complete under the frozen strict completeness rule are ranked.
Exact quality is the audited value; cost and latency are per-model aggregates
over the same 50 production tasks.

| Rank | Model | Overall Quality (exact) | Cost / 100 Tasks | Median Latency | Constraint Pass Rate | Pareto |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Kimi K3 (`kimi-k3`) | 96.3334 | ¥26.59 | 48.3s | 0.9953 | yes |
| 2 | DeepSeek V4 Flash (`deepseek-v4-flash`) | 96.3326 | ¥1.48 | 11.0s | 0.9858 | yes |
| 3 | Doubao Seed 2.1 Pro (`doubao-seed-2-1-pro-260628`) | 92.667 | ¥19.98 | 102.1s | 0.9858 | — |
| 4 | Kimi K2.6 (`kimi-k2.6`) | 92.583 | ¥7.69 | 50.1s | 0.9858 | — |

Rounded presentation values above. The exact figures are in
[release/v1/leaderboard.csv](release/v1/leaderboard.csv) and
[release/v1/leaderboard.json](release/v1/leaderboard.json) — for example
DeepSeek V4 Flash is ¥1.4783062 and Kimi K3 is ¥26.58924966 per 100 tasks.

### Incomplete models

V1 ranks **4 of 10** models. Six are INCOMPLETE under the frozen strict
completeness rule and are **not** Pareto-eligible and **not** ranked:

`deepseek_flagship`, `qwen_flagship`, `qwen_value`, `minimax_flagship`,
`glm_flagship`, `glm_value`.

An official rank requires all 50 candidate cases plus **both** intended valid
cross-family judge verdicts. A candidate failure, a transport failure, or an
invalid required judge verdict makes that model INCOMPLETE. Observed blockers
included candidate generation-envelope exhaustion, transport failure, and
required judge invalid-output failure.

This is a **benchmark result, not unfinished execution**:
`execution_complete = true` (every planned paid unit was attempted and
persisted) while `all_models_complete = false`. Incomplete models keep their
diagnostics but are never silently averaged into a rank or a comparative cost
metric. See [release/v1/run_manifest.json](release/v1/run_manifest.json) and
[docs/METHODOLOGY_V1.md](docs/METHODOLOGY_V1.md) for details.

## Cost, latency, and Pareto

AIProductBench evaluates **quality × cost × latency** and produces Pareto
analysis over it.

| Frontier | Models |
| --- | --- |
| Official quality × cost | Kimi K3, DeepSeek V4 Flash |
| Official quality × cost × latency | Kimi K3, DeepSeek V4 Flash |

Incomplete models are never placed on an official frontier. Candidate
inference cost and judge evaluation cost are kept strictly separate, and
candidate latency and judge latency are never mixed. Costs are presented in
RMB/CNY; native provider price and currency are always preserved, and any
conversion uses an explicit, dated FX snapshot.

## Reproducibility and provenance

| Field | Value |
| --- | --- |
| Canonical run | `official-v1-20260911T103838Z` |
| Execution commit | `f3225f51824f4e3c047b2df3c15092a803231291` |
| Runtime baseline | `e10ceb0aa89483050ec0b09eb96e7d16c37e4e09` |
| Dataset semantic manifest | `6b450383e528a5a0a6b813112f96182a3625c04c948839fc551c8ded63da513c` |
| Registry | `v1-registry-2026-09-11.3` |
| Registry SHA | `259b02adb05f73ab2d800c8f41d9b2608b8eddb17ae97e9d3f31ecff79409eab` |
| Pricing | `v1-pricing-2026-09-11.1` |
| Pricing SHA | `9f7af42243e5e0b78b1776934de5483f0e3e650765a19dd929e78af10aa15c42` |
| FX | `ecb-2026-09-10-usd-cny`, USD/CNY 6.706267217630854 |

### Runtime policy

| Setting | Value |
| --- | --- |
| Candidate generation ceiling | 32,768 tokens |
| Judge generation ceiling | 16,384 tokens |
| Client timeout | 600 seconds |
| Global provider concurrency | 6 (per-provider default 2) |
| Hard cost ceiling | ¥150.00 |

The run is checkpointed and resumable; every completed paid call is preserved
and only unfinished work is retried (bounded retries), so no paid call is
duplicated.

## Limitations

V1 does **not** benchmark:

* multimodal / vision input
* coding
* RAG or live web search
* actual tool execution
* multi-agent execution
* fine-tuning
* production routing

Additional honest caveats:

* 10 models and 50 cases is a practical benchmark, not a scientifically
  comprehensive one. V1 does not perform repeated sampling or significance
  testing.
* Two cross-family judges reduce judge-family bias and make it measurable; they
  do not eliminate it. Judge disagreement is published in
  [release/v1/judge_disagreement.json](release/v1/judge_disagreement.json).
* **Human calibration sample prepared. Human review pending.** V1 is not
  human-calibrated, and no agreement figures are published.
* Pricing is a dated manual snapshot, not a live billing feed.
* Latency depends on provider load, region, and network path.

## Project structure

```
.
├── run_benchmark.py        # CLI: validate-only / estimate / dry-run / confirm
├── data/                   # case dataset, model registry, pricing + FX snapshots
├── docs/                   # product spec, methodology, case design, decisions
├── src/                    # benchmark modules (config, providers, judge, analytics)
├── tests/                  # standard-library unittest suite
└── release/v1/             # canonical V1 public release artifacts
```

Key documents:

| Document | Contents |
| --- | --- |
| [docs/PRODUCT_SPEC_V1.md](docs/PRODUCT_SPEC_V1.md) | Frozen V1 scope and out-of-scope list |
| [docs/METHODOLOGY_V1.md](docs/METHODOLOGY_V1.md) | Frozen evaluation design: dataset, judges, metrics, Pareto |
| [docs/CASE_DESIGN_STANDARD_V1.md](docs/CASE_DESIGN_STANDARD_V1.md) | Binding rules for authoring production cases |
| [docs/CASE_MATRIX_V1.md](docs/CASE_MATRIX_V1.md) | Planned coverage of all 50 production slots |
| [docs/DATASET_QA_V1.md](docs/DATASET_QA_V1.md) | Dataset quality-assurance record |
| [docs/DATASET_FREEZE_V1.md](docs/DATASET_FREEZE_V1.md) | Immutable dataset freeze manifest |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Chronological decision log with rationale |

## Running it yourself

Requires Python 3.10 or newer. The only dependency is `requests`.

These commands are offline and make **zero network calls**:

```bash
pip install -r requirements.txt

python3 run_benchmark.py --validate-only
python3 run_benchmark.py --validate-only --production-cases
python3 run_benchmark.py --dry-run
python3 -m unittest discover -s tests -v
```

`--dry-run` produces synthetic, clearly banner-flagged output only and never
overwrites published results.

A **real paid run** is a different operation. It requires provider API
credentials supplied through environment variables (one per provider, named in
the model registry) and it spends real money, so it is refused unless launched
with `--confirm`. Do not run it without an explicit cost projection and
authorization.

## License

MIT — see [LICENSE](LICENSE).
