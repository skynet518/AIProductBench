# AIProductBench CN

### Practical Chinese LLM Model Selection Benchmark for AI Product Teams

**面向中国 AI 产品团队的中文大模型选型基准**

**[English](./README.md) | [简体中文](./README.zh-CN.md)**

**10 Models · 6 Providers · 50 Production Tasks · 1,490 Evaluation Units**

**Quality × Cost × Latency · Hybrid Evaluation · Cross-family Dual Judges · Pareto Analysis**

> Which model should an AI product team choose for a specific workload,
> quality target, cost budget, and latency requirement?

AIProductBench CN is a practical LLM evaluation and model-selection benchmark
designed for real AI product decisions.

It does **not** try to answer “Which model is universally best?”

Instead, it evaluates how model quality changes against cost, latency,
constraint adherence, and workload requirements — and turns benchmark results
into a product decision surface.

**V1 Status: Released**

Canonical run: `official-v1-20260911T103838Z`

[**V1 Results**](release/v1/README.md) ·
[**Methodology**](docs/METHODOLOGY_V1.md) ·
[**Case Design**](docs/CASE_DESIGN_STANDARD_V1.md) ·
[**Run Manifest**](release/v1/run_manifest.json)

---

## V1 Decision Summary

| | Result |
| --- | --- |
| **Highest measured quality** | **Kimi K3 — 96.3334** |
| **Near-equal quality with strongest measured cost / latency trade-off** | **DeepSeek V4 Flash — 96.3326** |
| **DeepSeek V4 Flash cost** | **¥1.48 / 100 tasks** |
| **DeepSeek V4 Flash median candidate latency** | **11.0s** |
| **Official Pareto frontier** | **Kimi K3 + DeepSeek V4 Flash** |
| **Officially ranked** | **4 / 10 models** |

![AIProductBench CN V1 Quality × Cost Pareto](docs/assets/aiproductbench_v1_quality_cost_pareto.png)

*Official Quality × Cost Pareto view for the four COMPLETE, rank-eligible V1 models.*

### The product decision

Kimi K3 achieved the highest measured overall quality.

DeepSeek V4 Flash scored only **0.0008 points lower** while costing roughly
**18× less** and showing roughly **4× lower median candidate latency** in this
benchmark.

That 0.0008-point difference should **not** be interpreted as a statistically
significant quality advantage. V1 does not perform repeated sampling or
significance testing.

The useful conclusion is therefore not:

> “Model A ranks #1.”

It is:

> **When measured quality is nearly equal, cost and latency can completely
> change the best product choice.**

For quality-maximizing workloads, Kimi K3 is the strongest measured option in
V1.

For workloads where near-equal measured quality is acceptable and cost /
latency matter materially, DeepSeek V4 Flash is the more attractive product
trade-off on the official Pareto frontier.

![AIProductBench CN V1 Product Trade-off](docs/assets/aiproductbench_v1_product_tradeoff.png)

*DeepSeek V4 Flash retains almost the same measured quality while requiring a
fraction of Kimi K3's cost and median candidate latency in this benchmark.*

---

## V1 at a Glance

| Benchmark Scope | Evaluation Scale |
| --- | --- |
| **10 candidate models** | **500 candidate evaluations** |
| **6 provider integrations** | **990 cross-family judge evaluations** |
| **50 frozen production tasks** | **1,490 formal evaluation units** |
| **5 workload domains** | **¥109.73 canonical API spend** |

V1 is based on real paid API execution.

`execution_complete = true`

However:

`all_models_complete = false`

Under the frozen strict completeness rule, **4 of 10 models are complete and
rank-eligible**. Six models are retained as diagnostic evidence but are not
included in the official ranking or Pareto frontier.

---

## Why This Benchmark Exists

Public LLM leaderboards are useful for understanding general model capability,
but product teams usually face a different question:

> Which model should we actually ship for this workload?

A production model decision may depend on:

- output quality
- instruction and constraint adherence
- inference cost
- response latency
- workload characteristics
- operational reliability
- acceptable quality / cost trade-offs

A model with the highest quality score may not be the best product choice.

AIProductBench CN turns evaluation into a model-selection workflow:

**Production Tasks → Candidate Models → Deterministic Checks → Dual LLM Judges → Quality / Cost / Latency → Pareto Analysis → Product Decision**

---

## Benchmark Design

V1 uses **50 frozen production tasks**, with 10 tasks in each of five workload
domains.

| # | Workload Domain | Key |
| --- | --- | --- |
| 1 | Instruction & Constraint Following | `instruction_constraint_following` |
| 2 | Structured Information Analysis | `structured_information_analysis` |
| 3 | Product Reasoning & Decision | `product_reasoning_decision` |
| 4 | Chinese Business Communication | `chinese_business_communication` |
| 5 | Agent Workflow Planning | `agent_workflow_planning` |

The benchmark is designed around practical AI product work rather than academic
knowledge testing.

Full methodology:

[docs/METHODOLOGY_V1.md](docs/METHODOLOGY_V1.md)

Case-authoring standard:

[docs/CASE_DESIGN_STANDARD_V1.md](docs/CASE_DESIGN_STANDARD_V1.md)

Frozen case coverage:

[docs/CASE_MATRIX_V1.md](docs/CASE_MATRIX_V1.md)

---

## Evaluation Framework

AIProductBench uses a hybrid evaluation architecture.

### 1. Deterministic evaluation

Every objectively machine-checkable constraint is evaluated using deterministic
checks.

V1 includes **21 deterministic check types**.

The resulting constraint performance is reported separately as
`constraint_pass_rate`.

### 2. Cross-family dual LLM judging

Every candidate response is evaluated by two judges from other model families.

Judge dimensions:

- **Task Completion**
- **Reasoning Quality**
- **Instruction Following**

There is no same-family judge substitution in the canonical evaluation design.

Dual judging reduces dependence on a single judge family, but it does not
eliminate judge bias.

Judge disagreement is published in:

[release/v1/judge_disagreement.json](release/v1/judge_disagreement.json)

### 3. Cost measurement

Candidate inference cost and judge evaluation cost are tracked separately.

They are never combined into one model cost figure.

Provider-native pricing and currency are preserved, while user-facing benchmark
cost is normalized into RMB/CNY using an explicit dated FX snapshot.

### 4. Latency measurement

Candidate latency and judge latency are also kept separate.

The model-selection analysis uses candidate inference latency rather than
mixing benchmark infrastructure overhead into the product-facing metric.

### 5. Pareto analysis

Instead of declaring one universal winner, V1 computes official Pareto
frontiers over:

- **quality × cost**
- **quality × cost × latency**

A model is Pareto-efficient when no other eligible model is simultaneously
better across all included decision dimensions.

---

## Model Pool

V1 evaluates 10 candidate models across 6 provider integrations.

The model pool is configuration-driven and declared in:

[data/model_registry_snapshot_v1.json](data/model_registry_snapshot_v1.json)

| Provider | Candidate Models |
| --- | --- |
| Qwen | `qwen3.8-max`, `qwen3.8-flash` |
| DeepSeek | `deepseek-v4-pro`, `deepseek-v4-flash` |
| Kimi | `kimi-k3`, `kimi-k2.6` |
| MiniMax | `MiniMax-M3` |
| GLM | `glm-5.3`, `glm-5.3-flash` |
| Doubao | `doubao-seed-2-1-pro-260628` |

Benchmark logic does not branch directly on a specific model name or provider
name.

---

## Official V1 Ranking

Only models that satisfy the frozen strict completeness rule are officially
ranked.

| Rank | Model | Overall Quality | Cost / 100 Tasks | Median Candidate Latency | Constraint Pass Rate | Pareto |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | Kimi K3 (`kimi-k3`) | **96.3334** | ¥26.59 | 48.3s | 0.9953 | **Yes** |
| 2 | DeepSeek V4 Flash (`deepseek-v4-flash`) | **96.3326** | ¥1.48 | 11.0s | 0.9858 | **Yes** |
| 3 | Doubao Seed 2.1 Pro (`doubao-seed-2-1-pro-260628`) | 92.667 | ¥19.98 | 102.1s | 0.9858 | — |
| 4 | Kimi K2.6 (`kimi-k2.6`) | 92.583 | ¥7.69 | 50.1s | 0.9858 | — |

Presentation values above are rounded.

Exact audited values are available in:

- [release/v1/leaderboard.csv](release/v1/leaderboard.csv)
- [release/v1/leaderboard.json](release/v1/leaderboard.json)

For example:

- DeepSeek V4 Flash: `¥1.4783062 / 100 tasks`
- Kimi K3: `¥26.58924966 / 100 tasks`

---

## Why Only 4 of 10 Models Are Ranked

V1 applies a strict completeness rule.

An official ranking requires:

- all 50 candidate task executions
- both intended valid cross-family judge verdicts for every required response

A candidate generation failure, transport failure, or invalid required judge
verdict can make a model **INCOMPLETE**.

Six V1 candidate slots are therefore excluded from official ranking and Pareto
analysis:

- `deepseek_flagship`
- `qwen_flagship`
- `qwen_value`
- `minimax_flagship`
- `glm_flagship`
- `glm_value`

Observed blockers included:

- candidate generation-envelope exhaustion
- transport failure
- required judge invalid-output failure

This does **not** mean the benchmark execution itself is unfinished.

Every planned paid evaluation unit was attempted and persisted:

`execution_complete = true`

But not every model satisfied the ranking-completeness contract:

`all_models_complete = false`

Incomplete models retain diagnostic evidence but are never silently averaged
into official comparative results.

See:

- [release/v1/run_manifest.json](release/v1/run_manifest.json)
- [docs/METHODOLOGY_V1.md](docs/METHODOLOGY_V1.md)

---

## Pareto Frontier

| Frontier | Official Models |
| --- | --- |
| **Quality × Cost** | Kimi K3, DeepSeek V4 Flash |
| **Quality × Cost × Latency** | Kimi K3, DeepSeek V4 Flash |

Incomplete models are never placed on the official frontier.

The purpose of the Pareto layer is not to create another leaderboard.

It is to expose the product trade-off surface:

**How much quality are we buying, at what cost and latency?**

---

## Reproducibility & Provenance

The canonical result is tied to frozen dataset, model-registry, pricing, FX,
runtime, and execution snapshots.

| Field | Canonical V1 Value |
| --- | --- |
| Canonical run | `official-v1-20260911T103838Z` |
| Execution commit | `f3225f51824f4e3c047b2df3c15092a803231291` |
| Runtime baseline | `e10ceb0aa89483050ec0b09eb96e7d16c37e4e09` |
| Dataset semantic manifest | `6b450383e528a5a0a6b813112f96182a3625c04c948839fc551c8ded63da513c` |
| Registry | `v1-registry-2026-09-11.3` |
| Registry SHA | `259b02adb05f73ab2d800c8f41d9b2608b8eddb17ae97e9d3f31ecff79409eab` |
| Pricing | `v1-pricing-2026-09-11.1` |
| Pricing SHA | `9f7af42243e5e0b78b1776934de5483f0e3e650765a19dd929e78af10aa15c42` |
| FX | `ecb-2026-09-10-usd-cny` |
| USD / CNY | `6.706267217630854` |

### Canonical runtime envelope

| Setting | Value |
| --- | --- |
| Candidate generation ceiling | 32,768 tokens |
| Judge generation ceiling | 16,384 tokens |
| Client timeout | 600 seconds |
| Global provider concurrency | 6 |
| Default per-provider concurrency | 2 |
| Hard cost ceiling | ¥150.00 |

The run is checkpointed and resumable.

Completed paid calls are preserved, and bounded retries apply only to unfinished
work so completed paid calls are not unnecessarily duplicated.

---

## Public V1 Artifacts

The canonical public result set is stored under:

`release/v1/`

Key artifacts:

| Artifact | Purpose |
| --- | --- |
| [leaderboard.html](release/v1/leaderboard.html) | Standalone result presentation |
| [leaderboard.csv](release/v1/leaderboard.csv) | Tabular benchmark output |
| [leaderboard.json](release/v1/leaderboard.json) | Structured leaderboard data |
| [pareto.json](release/v1/pareto.json) | Pareto frontier output |
| [cost_summary.json](release/v1/cost_summary.json) | Candidate cost aggregation |
| [latency_summary.json](release/v1/latency_summary.json) | Candidate latency aggregation |
| [judge_disagreement.json](release/v1/judge_disagreement.json) | Dual-judge disagreement analysis |
| [sample_results.json](release/v1/sample_results.json) | Public result samples |
| [run_manifest.json](release/v1/run_manifest.json) | Canonical execution and provenance record |

Published V1 artifacts should be treated as immutable evidence.

A future benchmark run that changes models, dataset, pricing, methodology,
runtime configuration, or evaluation logic should be published as a new
version rather than silently replacing V1.

---

## Limitations

AIProductBench CN V1 does **not** benchmark:

- multimodal / vision input
- coding
- RAG
- live web search
- actual tool execution
- multi-agent execution
- fine-tuning
- production routing

Additional limitations:

- 10 models and 50 tasks form a practical product benchmark, not a
  scientifically comprehensive benchmark.
- V1 does not perform repeated sampling or statistical significance testing.
- Cross-family dual judging reduces judge-family dependence but does not remove
  judge bias.
- **Human calibration sample prepared; human review pending.**
- V1 is therefore **not human-calibrated**.
- Pricing is based on a dated snapshot rather than a live provider billing feed.
- Latency can vary with provider load, region, and network path.

---

## Project Structure

```text
.
├── run_benchmark.py        # Main benchmark CLI
├── run_official.py         # Canonical execution support
├── run_probe.py            # Targeted provider/runtime probes
├── run_smoke.py            # Controlled live smoke validation
├── data/                   # Cases, model registry, pricing and FX snapshots
├── docs/                   # Product spec, methodology, decisions and handoff
├── src/                    # Benchmark execution and analytics modules
├── tests/                  # Standard-library unittest suite
└── release/v1/             # Canonical public V1 result artifacts
```

### Key Documents

| Document | Purpose |
| --- | --- |
| [PRODUCT_SPEC_V1](docs/PRODUCT_SPEC_V1.md) | Frozen V1 product scope |
| [METHODOLOGY_V1](docs/METHODOLOGY_V1.md) | Evaluation methodology |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | Pipeline, modules and data flow |
| [CASE_DESIGN_STANDARD_V1](docs/CASE_DESIGN_STANDARD_V1.md) | Production-case authoring standard |
| [CASE_MATRIX_V1](docs/CASE_MATRIX_V1.md) | Coverage design for all 50 production tasks |
| [DATASET_QA_V1](docs/DATASET_QA_V1.md) | Dataset QA record |
| [DATASET_FREEZE_V1](docs/DATASET_FREEZE_V1.md) | Frozen dataset manifest |
| [DECISIONS](docs/DECISIONS.md) | Product and engineering decision log |
| [HANDOFF](docs/HANDOFF.md) | Current post-release operational state |

---

## Run It Locally

Requires **Python 3.10+**.

The only external runtime dependency is `requests`.

Install dependencies:

```bash
pip install -r requirements.txt
```

Offline validation:

```bash
python3 run_benchmark.py --validate-only
python3 run_benchmark.py --validate-only --production-cases
python3 run_benchmark.py --dry-run
python3 -m unittest discover -s tests -v
```

These operations make **zero network calls**.

`--dry-run` produces synthetic, clearly marked output and never overwrites the
published V1 result set.

### Paid execution warning

A real provider run requires API credentials supplied through environment
variables and spends real money.

The canonical V1 paid benchmark is already complete.

Do **not** run:

`python3 run_benchmark.py --confirm`

without explicit paid-run authorization, a new cost projection, and an approved
versioned execution plan.

---

## What This Project Demonstrates

AIProductBench CN was built as a product-selection system rather than a model
leaderboard.

The project demonstrates an end-to-end AI product workflow across:

**Problem Framing → Benchmark Design → Dataset Governance → Evaluation Pipeline → Model Integration → Cost / Latency Measurement → Result Analysis → Product Decision**

From an AI product perspective, the key capability is not simply calling
multiple LLM APIs.

It is building a reproducible decision framework that turns model capability
into a defensible product choice.

---

## License

MIT — see [LICENSE](LICENSE).
