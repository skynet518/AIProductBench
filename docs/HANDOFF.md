# AIProductBench CN — Handoff

Read this file and `../AGENTS.md` before modifying the repository.

This document describes the current operational state of AIProductBench CN
after the public V1 release.

---

## CURRENT RELEASE

**AIProductBench CN V1 is PUBLISHED.**

AIProductBench CN is a practical model-selection benchmark for Chinese LLMs,
built for AI product teams choosing models under real quality, cost, and latency
constraints.

The benchmark focuses on product trade-offs rather than producing a universal
“best model” ranking.

Public repository: `skynet518/AIProductBench`

Canonical public release artifacts: `release/v1/`

---

## CANONICAL V1 RUN

Canonical run: `official-v1-20260911T103838Z`

Execution state:

- `execution_complete = true`
- `all_models_complete = false`
- 500 / 500 candidate evaluation units attempted
- 990 / 990 cross-family judge evaluation units attempted
- 1,490 formal evaluation units in total
- canonical API spend: 109.73182552 CNY

Benchmark scope:

- 10 candidate models
- 6 provider integrations
- 50 production tasks
- 5 workload domains

Under the frozen strict completeness rule:

- 4 / 10 models are COMPLETE and rank-eligible
- 6 / 10 models are INCOMPLETE
- INCOMPLETE models are not officially ranked
- INCOMPLETE models are not eligible for the official Pareto frontier

Execution completion must never be confused with model completeness.

---

## OFFICIAL V1 RESULT

Highest measured overall quality:

**Kimi K3 — 96.3334**

DeepSeek V4 Flash:

- overall quality: 96.3326
- cost / 100 tasks: approximately ¥1.48
- median candidate latency: approximately 11.0 s

Kimi K3:

- cost / 100 tasks: approximately ¥26.59
- median candidate latency: approximately 48.3 s

The measured quality gap is 0.0008 points.

V1 does not claim that this difference is statistically significant because it
does not perform repeated sampling or significance testing.

Product interpretation:

- Kimi K3 achieved the highest measured overall quality
- DeepSeek V4 Flash delivered near-equal measured quality at substantially lower
  cost and latency
- model selection should consider quality, cost, latency, and workload fit rather
  than quality ranking alone

Official Pareto frontier for both quality × cost and
quality × cost × latency:

- Kimi K3
- DeepSeek V4 Flash

Canonical result artifacts include:

- `release/v1/leaderboard.csv`
- `release/v1/leaderboard.json`
- `release/v1/leaderboard.html`
- `release/v1/pareto.json`
- `release/v1/cost_summary.json`
- `release/v1/latency_summary.json`
- `release/v1/judge_disagreement.json`
- `release/v1/sample_results.json`
- `release/v1/run_manifest.json`

---

## FROZEN V1 DATASET

The V1 production dataset is frozen.

It contains 50 production tasks across five workload domains, 10 tasks per
domain:

1. `instruction_constraint_following`
2. `structured_information_analysis`
3. `product_reasoning_decision`
4. `chinese_business_communication`
5. `agent_workflow_planning`

Final dataset review state:

- 50 PASS
- 0 PATCH
- 0 REJECT

Frozen dataset manifest:

`docs/DATASET_FREEZE_V1.md`

Aggregate semantic freeze SHA-256:

`6b450383e528a5a0a6b813112f96182a3625c04c948839fc551c8ded63da513c`

The frozen V1 production cases must not be silently modified.

Any future semantic dataset change requires a versioned reopening, appropriate
review gates, and a new freeze manifest and hash.

Such work should normally become V1.1 or a later benchmark version.

---

## EVALUATION DESIGN

V1 uses a hybrid evaluation architecture.

Deterministic evaluation covers objectively machine-checkable constraints using
21 deterministic check types.

LLM evaluation uses two cross-family judges for each candidate response.

Judge dimensions:

- Task Completion
- Reasoning Quality
- Instruction Following

Candidate inference and judge evaluation are separate roles.

Candidate cost must never be mixed with judge cost.

Candidate latency must never be mixed with judge latency.

Judge disagreement is published in:

`release/v1/judge_disagreement.json`

Dual-judge evaluation reduces dependence on a single judge family but does not
eliminate judge bias.

---

## HUMAN CALIBRATION

A human calibration sample has been prepared.

Human labels are still pending.

Therefore:

**V1 is NOT human-calibrated.**

Do not publish human agreement metrics until real human review has been
completed.

---

## CANONICAL PROVENANCE

Canonical run:

`official-v1-20260911T103838Z`

Execution commit:

`f3225f51824f4e3c047b2df3c15092a803231291`

Runtime baseline:

`e10ceb0aa89483050ec0b09eb96e7d16c37e4e09`

Registry:

`v1-registry-2026-09-11.3`

Registry SHA:

`259b02adb05f73ab2d800c8f41d9b2608b8eddb17ae97e9d3f31ecff79409eab`

Pricing snapshot:

`v1-pricing-2026-09-11.1`

Pricing SHA:

`9f7af42243e5e0b78b1776934de5483f0e3e650765a19dd929e78af10aa15c42`

FX snapshot:

`ecb-2026-09-10-usd-cny`

Canonical USD/CNY:

`6.706267217630854`

These snapshots belong to the historical V1 result and must not be silently
replaced with current pricing, FX, or model configuration.

---

## RUNTIME ENVELOPE

Canonical V1 runtime configuration:

- candidate generation ceiling: 32,768 tokens
- judge generation ceiling: 16,384 tokens
- client timeout: 600 seconds
- global provider concurrency: 6
- default per-provider concurrency: 2
- Moonshot / Kimi maximum in-flight requests: 1
- hard run cost ceiling: ¥150.00

Do not introduce adaptive per-case token escalation into the published V1
configuration.

---

## RELEASE INTEGRITY

The canonical V1 public result set under `release/v1/` should be treated as
immutable evidence.

Do not silently regenerate or overwrite the published V1 results.

A future benchmark run that changes model versions, pricing, provider
configuration, dataset content, methodology, runtime envelope, or evaluation
logic should be represented as a new versioned benchmark.

Preserve these distinctions:

- execution complete ≠ all models complete
- highest quality ≠ best product choice
- candidate cost ≠ judge cost
- candidate latency ≠ judge latency
- benchmark ranking ≠ statistical significance
- dual-judge evaluation ≠ human calibration

---

## PAID RUN SAFETY

The canonical V1 paid benchmark is already complete.

Do not run `python3 run_benchmark.py --confirm` again without:

1. explicit paid-run authorization
2. a new cost projection
3. an approved versioned execution plan

Completed paid work must not be unnecessarily regenerated.

---

## CREDENTIAL SAFETY

Provider credentials must come from environment variables only.

Never read or copy API keys from:

- `~/.codex`
- `~/.codex-deepseek`
- shell history
- unrelated agent configuration
- unrelated credential stores

Never commit credentials.

---

## KEY DOCUMENTS

- `../AGENTS.md` — project instructions and release-integrity rules
- `PRODUCT_SPEC_V1.md` — frozen V1 scope
- `METHODOLOGY_V1.md` — evaluation methodology
- `ARCHITECTURE.md` — benchmark architecture and data flow
- `CASE_DESIGN_STANDARD_V1.md` — production case-authoring standard
- `CASE_MATRIX_V1.md` — 50-task coverage design
- `DATASET_QA_V1.md` — dataset QA record
- `DATASET_FREEZE_V1.md` — frozen dataset manifest
- `DECISIONS.md` — chronological decision log
- `../release/v1/README.md` — canonical release summary

---

## CURRENT OPEN ITEMS

The core V1 benchmark is complete.

Remaining work is post-release improvement, not unfinished V1 benchmark work.

Open items:

1. Complete human calibration review when real reviewers and labels are
   available.
2. Add explicit official documentation URLs for model IDs and pricing metadata
   where still marked `requires_official_verification`.
3. Improve public presentation: README, Chinese README, visualizations, GitHub
   Release, repository metadata, and profile integration.
4. Define any future benchmark expansion as V1.1, V2, or another explicit
   versioned scope.

---

## OUT OF SCOPE FOR V1

V1 does not benchmark:

- multimodal / vision input
- coding
- RAG
- live web search
- actual tool execution
- multi-agent execution
- fine-tuning
- production routing systems

Do not imply otherwise in public documentation.

---

## NEXT

The benchmark itself is complete.

The immediate next phase is:

**Post-release presentation and documentation polish.**

Priority order:

1. maintain release-document consistency
2. improve the public README first-screen experience
3. add `README.zh-CN.md`
4. add benchmark result visualizations
5. create the formal GitHub V1 release / tag
6. improve repository metadata and Topics
7. integrate AIProductBench CN into the GitHub profile

Do not reopen benchmark engineering work unless a real V1 defect is discovered
or a new benchmark version is explicitly approved.
