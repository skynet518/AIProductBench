# AIProductBench CN V1 — Methodology

**Status: RELEASED — V1.0.0**

**Canonical run: `official-v1-20260911T103838Z`**

This document defines the evaluation methodology used by the released
AIProductBench CN V1 benchmark.

It is the authoritative methodology reference for V1.0.0. If the released
benchmark implementation, canonical artifacts, and this document disagree, the
disagreement should be treated as a documentation or implementation defect
rather than silently reconciled.

The V1 methodology, dataset, registry, pricing, FX snapshot, runtime envelope,
and execution provenance are frozen for the published release.

---

## 1. Dataset

### Size

V1 contains:

**50 frozen production cases**

These cases are the released benchmark dataset, not synthetic fixtures.

Synthetic fixtures may still exist for testing the evaluation framework, but
they are explicitly separated from the production benchmark and must never be
presented as official benchmark evidence.

### Domains

The 50 production cases are divided across five workload domains, with 10 cases
per domain:

| # | Domain | What it measures |
| --- | --- | --- |
| 1 | `instruction_constraint_following` | Obeying explicit format, length, structure, and negative constraints |
| 2 | `structured_information_analysis` | Turning messy or tabular input into fixed, machine-readable structure |
| 3 | `product_reasoning_decision` | Prioritisation, measurement design, and launch judgment |
| 4 | `chinese_business_communication` | Chinese business register, tone, and audience adaptation |
| 5 | `agent_workflow_planning` | Decomposing a goal into a correct, ordered, executable workflow |

### Language composition

The dataset is Chinese-first:

- approximately 40 Chinese-first cases
- approximately 10 English or cross-lingual cases

### Difficulty composition

Within every domain:

- 2 easy
- 5 medium
- 3 hard

This distribution is frozen for V1.

### Case schema

Every production case supports the following schema:

| Field | Required | Notes |
| --- | --- | --- |
| `id` | yes | Stable, unique, domain-prefixed |
| `domain` | yes | One of the five frozen domains |
| `difficulty` | yes | `easy` \| `medium` \| `hard` |
| `language` | yes | `zh` \| `en` \| `mixed` |
| `prompt` | yes | Self-contained |
| `evaluation_criteria` | yes | Case-specific criteria supplied to every judge |
| `deterministic_checks` | when applicable | Machine-checkable constraints |

The production cases were authored, reviewed, validated, and frozen before the
canonical paid execution.

Dataset governance is documented in:

- `CASE_DESIGN_STANDARD_V1.md`
- `CASE_MATRIX_V1.md`
- `DATASET_QA_V1.md`
- `DATASET_FREEZE_V1.md`

Canonical dataset semantic manifest:

`6b450383e528a5a0a6b813112f96182a3625c04c948839fc551c8ded63da513c`

---

## 2. Evaluation Design

V1 uses **hybrid evaluation**:

- deterministic checks where a constraint is objectively machine-testable
- LLM evaluation where semantic judgment is required

The two systems measure different properties and are reported side by side.

Neither is allowed to silently override the other.

---

### A. Deterministic Checks

The released evaluator supports **21 deterministic check types**.

| Group | Check types |
| --- | --- |
| Structure | `valid_json`, `required_keys`, `forbidden_keys`, `exact_keys` |
| Item count | `exact_item_count`, `max_items`, `min_items`, `exact_bullet_count`, `section_bullet_count` |
| Length | `max_words`, `min_words`, `max_chars`, `min_chars`, `section_max_chars` |
| Content | `required_phrases`, `forbidden_phrases`, `required_regex`, `forbidden_regex` |
| Order and format | `ordering`, `no_markdown_fence` |
| Numeric | `numeric_range` |

Cases declare deterministic checks only where the requested constraint can be
objectively evaluated.

A case that legitimately requires no deterministic checks reports no fabricated
pass rate.

#### Section-scoped checks

`section_max_chars` and `section_bullet_count` isolate a specific section using:

- required `start_marker`
- optional `end_marker`

and then apply their constraint only to that section.

A missing, duplicate, or out-of-order marker fails safely.

`exact_keys` requires a JSON object whose key set exactly matches the declared
set.

The following all fail:

- missing keys
- unexpected keys
- invalid JSON
- a non-object JSON root

These operators were added after production-case review and are documented in
`DECISIONS.md`.

#### Declaration validation

A production case cannot pass dataset validation if any deterministic-check
declaration is malformed.

Validation rejects, among other errors:

- unknown operators
- missing fields
- unexpected fields
- invalid parameter types
- non-compiling regular expressions
- invalid or duplicate list members
- invalid count parameters
- malformed section markers

Declarations are validated before a paid benchmark run.

This prevents an invalid check definition from silently becoming a runtime
evaluation failure.

#### Check-quality rule

A deterministic check must test the intended constraint rather than a
superficial proxy.

For example:

- requiring the word `risk` is not evidence of risk analysis
- requiring a phrase is not evidence that prioritisation is correct
- confirming that a number appears is not evidence that a computation is correct

Structural, exact, enum, count, invariant, or objectively derived checks are
preferred.

Genuinely semantic requirements are left to the LLM judges.

#### Language rule for length checks

`max_words` and `min_words` operate on whitespace-separated tokens and are not
appropriate for Chinese-first responses.

Therefore:

- `zh` cases use character-based checks such as `max_chars` / `min_chars`
- English cases may use word-count checks
- mixed-language cases require an explicit justification if word-count checks
  are used

This rule is enforced during dataset validation.

#### Deterministic metric

For cases containing deterministic checks:

```text
constraint_pass_rate = passed_checks / total_checks
```

The metric is reported independently from LLM quality evaluation.

A failed deterministic constraint is not silently repaired by a high judge
score.

Likewise, deterministic compliance alone does not imply high semantic quality.

---

### B. LLM Evaluation

Every valid candidate response is evaluated using three shared judge
dimensions.

Each dimension uses an integer score from 1 to 5:

| Dimension | Question |
| --- | --- |
| `task_completion` | Did the response fully do what the case asked, using only the information given? |
| `reasoning_quality` | Is the observable answer correct, specific, decision-ready, and supported by its stated justification? |
| `instruction_following` | Did it obey every explicit constraint, including negative constraints? |

Judges receive both:

1. the shared benchmark rubric
2. the case-level `evaluation_criteria`

Case-specific evaluation criteria are authoritative where they are more
concrete.

#### No private chain-of-thought

V1 never asks candidate models to expose hidden chain-of-thought and never
scores private reasoning.

`reasoning_quality` is evaluated only from observable output, such as:

- decision rationale
- evidence based on supplied facts
- explicit trade-offs
- stated assumptions
- support for the recommendation

Prompts and evaluation criteria must not require:

- “show your reasoning”
- “step-by-step reasoning”
- “transparent reasoning”

A fluent but unsupported explanation is not automatically a high-quality
answer.

A correct answer without an adequate observable basis is also not automatically
high-scoring when justification is part of the task.

Judge output must be strict machine-readable JSON.

Invalid judge output is rejected rather than silently repaired.

---

### C. Cross-family Dual-Judge Design

V1 uses one shared model registry.

Judge-eligible models are entries in that registry rather than separate
judge-only copies.

Candidate and judge roles remain operationally separate:

- candidate inference cost is reported separately from judge evaluation cost
- candidate latency is reported separately from judge latency

The canonical judge families are:

- Qwen flagship
- DeepSeek flagship
- GLM flagship

#### Leave-one-provider-out rule

A candidate response is not evaluated by a judge from the same model family or
provider when valid cross-family alternatives are available.

The intended design uses **two valid cross-family judge verdicts** for every
valid candidate response.

A same-family judge is never substituted merely to obtain a second score.

If the required verdict cannot be obtained under the frozen retry policy, that
evaluation remains invalid and may affect model completeness.

#### Fixed-priority judge selection

Judge selection uses the frozen priority:

```text
qwen_flagship > deepseek_flagship > glm_flagship
```

The candidate's own family/provider is excluded, after which the first two
eligible cross-family judges are selected.

Canonical family mapping:

| Candidate family | Judges |
| --- | --- |
| Qwen | DeepSeek + GLM |
| DeepSeek | Qwen + GLM |
| GLM | Qwen + DeepSeek |
| Kimi, MiniMax, Doubao | Qwen + DeepSeek |

Per-candidate hash rotation was rejected because assigning unrelated candidates
different judge pairs would introduce an avoidable evaluation confound.

The purpose of dual judging is not to claim elimination of judge bias.

It is to reduce dependence on a single judge family and make judge disagreement
observable.

Published disagreement evidence is available in:

`release/v1/judge_disagreement.json`

---

### D. Human Calibration

V1 defines a human-calibration sampling policy, but **human calibration review
was not completed for the V1.0.0 release**.

Therefore:

- V1.0.0 is **not human-calibrated**
- no Human-vs-Judge agreement metric is claimed
- no human agreement number is fabricated or inferred
- official V1 ranking does not depend on unperformed human review

The designed calibration policy remains documented for future execution.

#### Planned base sample

The intended base sample contains approximately 50 candidate responses and is
designed to cover:

- all candidate models
- all five workload domains
- easy, medium, and hard cases

#### Planned risk-based extension

Approximately 10–20 additional responses may be added when warranted.

Priority areas include:

- hard cases
- cases without deterministic checks
- responses with high Judge A / Judge B disagreement
- Kimi, MiniMax, and Doubao responses because they share the same judge-family pair
- responses near close ranking boundaries
- anomalous or surprising failures

The intended practical review size is therefore approximately 50–70 responses.

This section documents a **sampling design**, not a completed V1 evaluation
artifact.

A later version may execute and publish human calibration, but V1.0.0 does not
claim that this occurred.

---

## 3. Aggregation

### Per candidate response

```text
judge_mean      = mean of the three dimensions, per judge
quality_score   = mean of judge_mean across the two valid judges   (1-5)
overall_score   = (quality_score - 1) / (5 - 1) * 100              (0-100)
```

### Per model

```text
overall_score        = mean of overall_score across scored cases
constraint_pass_rate = passed deterministic checks / total deterministic checks
task_success_rate    = scored cases with every deterministic check passed / scored cases
judge_agreement      = disagreement/agreement evidence between the two judges
```

---

### Equal-denominator Rule

Official rankings require **equal denominators**.

A candidate model is rank-eligible only when all 50 production cases have valid
required evaluation results.

If any required case remains invalid after the frozen retry policy because of
candidate failure, judge-unavailable state, invalid required verdict, or another
terminal evaluation failure:

- the model is marked **INCOMPLETE**
- the failed case is never silently dropped
- no official rank is computed using a reduced denominator
- the model is excluded from `ranked_models`
- the model is excluded from the official Pareto frontier

Partial diagnostic evidence remains visible.

This distinction is critical:

> A completed benchmark execution does not require every candidate model to be
> complete.

The canonical V1 execution attempted every planned paid unit, but only 4 of 10
candidate models satisfied the strict ranking-completeness contract.

---

### Incomplete-run Comparative Metrics

An incomplete candidate retains operational diagnostics for work that actually
completed.

Examples include:

- actual candidate spend
- calls completed
- cases completed
- observed token usage
- observed latency
- observed partial-quality diagnostics where applicable

However, comparative metrics requiring equal denominators are suppressed or
treated as unavailable.

These include:

- official rank
- membership in `ranked_models`
- official Pareto eligibility
- `cost_per_100_tasks_cny` when the required equal-denominator contract is not satisfied
- `quality_per_cny` when the required comparative basis is unavailable

The benchmark must explain that these values are unavailable because the model
is incomplete rather than publishing misleading reduced-denominator
comparisons.

---

## 4. Metrics

| Metric | Definition |
| --- | --- |
| `quality_score` | Mean of the three judge dimensions, 1–5 |
| `constraint_pass_rate` | Deterministic checks passed / checks run |
| `task_success_rate` | Share of scored cases passing all declared deterministic checks |
| `overall_score` | Judge quality normalized to 0–100 |
| `avg_latency` | Mean candidate wall-clock response time |
| `p50_latency` | Median candidate response time |
| `p95_latency` | 95th-percentile candidate response time |
| `input_tokens` | Provider-reported input tokens |
| `output_tokens` | Provider-reported output tokens |
| `reasoning_tokens` | Provider-reported reasoning tokens when available |
| `candidate_inference_cost` | Cost of candidate calls only |
| `judge_evaluation_cost` | Cost of judge calls only, reported separately |
| `cost_per_100_tasks` | Candidate inference cost scaled to 100 tasks for eligible complete models |
| `quality_per_cny` | Overall score relative to candidate inference cost when comparable |
| `judge_agreement` | Agreement / disagreement evidence between the two judges |

Custom-defined or unavailable metrics are reported as unavailable rather than
estimated into the result.

Metric availability is part of the benchmark's reporting contract.

### Candidate vs judge telemetry

Candidate and judge telemetry must not be merged.

For product model selection:

- candidate inference cost is the relevant model cost
- candidate latency is the relevant response-latency signal

Judge cost and judge latency describe benchmark evaluation overhead and are
reported separately.

---

## 5. Pareto Analysis

AIProductBench CN presents Pareto analysis rather than relying only on a single
quality ranking.

Only **complete, rank-eligible models** may enter an official Pareto frontier.

Incomplete models are excluded regardless of their observed partial scores.

### Primary frontier: Quality × Cost

Objectives:

```text
overall_score_exact        → maximize
cost_per_100_tasks_cny     → minimize
```

A model is dominated if another eligible model is:

- at least as good in measured quality
- at least as good in cost
- strictly better in at least one of those dimensions

### Secondary frontier: Quality × Cost × Latency

The released V1 three-objective Pareto analysis uses:

```text
overall_score_exact        → maximize
cost_per_100_tasks_cny     → minimize
p95_latency_ms             → minimize
```

**P95 latency is the official latency objective used in the released
three-dimensional Pareto calculation.**

This is distinct from product-facing comparisons in the README that may use
P50 / median latency for easier interpretation.

The canonical Pareto artifact is:

`release/v1/pareto.json`

For V1.0.0, the official Pareto frontier contains:

- Kimi K3
- DeepSeek V4 Flash

The purpose of this analysis is not to create another universal leaderboard.

It is to expose the decision trade-off:

> How much measured quality are we buying, at what cost and latency?

---

## 6. Reproducibility and Provenance

V1.0.0 records a frozen reproducibility snapshot.

A reproducible benchmark record includes:

- literal provider model identifiers
- model registry snapshot
- dataset version and semantic manifest
- judge pool and judge-selection rule
- pricing snapshot
- FX snapshot
- runtime envelope
- execution commit
- canonical run identifier

### Canonical V1 provenance

| Field | Canonical value |
| --- | --- |
| Canonical run | `official-v1-20260911T103838Z` |
| Execution commit | `f3225f51824f4e3c047b2df3c15092a803231291` |
| Runtime baseline | `e10ceb0aa89483050ec0b09eb96e7d16c37e4e09` |
| Dataset version | `v1-authoring-2026-09-11` |
| Dataset semantic manifest | `6b450383e528a5a0a6b813112f96182a3625c04c948839fc551c8ded63da513c` |
| Registry | `v1-registry-2026-09-11.3` |
| Registry SHA | `259b02adb05f73ab2d800c8f41d9b2608b8eddb17ae97e9d3f31ecff79409eab` |
| Pricing | `v1-pricing-2026-09-11.1` |
| Pricing SHA | `9f7af42243e5e0b78b1776934de5483f0e3e650765a19dd929e78af10aa15c42` |
| FX snapshot | `ecb-2026-09-10-usd-cny` |
| USD / CNY | `6.706267217630854` |

### Canonical runtime envelope

| Setting | V1 value |
| --- | --- |
| Candidate generation ceiling | 32,768 tokens |
| Judge generation ceiling | 16,384 tokens |
| Client read timeout | 600 seconds |
| Global concurrent paid calls | 6 |
| Default per-provider concurrency | 2 |
| Kimi max in-flight | 1 |
| Hard cost ceiling | ¥150.00 |

The canonical run is checkpointed and resumable.

Completed paid work is preserved so retries do not intentionally repeat already
completed paid calls.

### Rolling aliases

If a provider model identifier resolves to a rolling model alias rather than
immutable weights, later reproduction may not execute against exactly the same
underlying weights.

Such provider behavior is a reproducibility limitation and must not be hidden.

---

## 7. Canonical V1 Execution Status

The released V1 benchmark is based on a real paid API execution.

Canonical run:

`official-v1-20260911T103838Z`

Execution semantics:

```text
execution_complete = true
all_models_complete = false
```

The canonical execution attempted:

```text
Candidate units: 500 / 500
Judge units:     990 / 990
Total formal evaluation units: 1,490
```

Canonical API spend:

```text
Candidate spend: ¥45.05535164
Judge spend:     ¥64.67647388
Total spend:     ¥109.73182552
```

`execution_complete = true` means every planned paid evaluation unit was
attempted and persisted.

`all_models_complete = false` means not every candidate model satisfied the
strict 50-case + required-valid-judge-verdict completeness contract.

These statements are not contradictory.

Under the frozen completeness rule:

**4 of 10 models are complete and rank-eligible.**

The remaining six preserve diagnostic evidence but are excluded from official
ranking and Pareto analysis.

The canonical execution record is:

`release/v1/run_manifest.json`

---

## 8. Known Limitations

V1.0.0 has the following material limitations.

- **Benchmark scope.** Ten models and 50 production tasks form a practical
  product benchmark, not a scientifically comprehensive evaluation of all LLM
  capability.

- **No repeated sampling.** V1 does not perform repeated stochastic sampling or
  statistical significance testing. Small score differences must therefore not
  be interpreted as statistically significant.

- **Judge-family bias.** Cross-family dual judging reduces dependence on a
  single judge family but does not eliminate judge bias.

- **Correlated judges for tail families.** Kimi, MiniMax, and Doubao candidates
  use the same judge-family pair under the frozen mapping. Shared systematic
  bias in those judges can therefore correlate evaluations across those
  candidate families.

- **Human calibration not completed.** A human-calibration sampling policy was
  designed, but the review was not completed for V1.0.0. The released benchmark
  is therefore not human-calibrated.

- **Incomplete candidate models.** Six of ten candidate models did not satisfy
  the strict completeness contract and are excluded from official ranking and
  Pareto analysis.

- **Pricing is dated.** Pricing uses a frozen snapshot rather than a live
  provider billing feed. Provider pricing may change after the benchmark date.

- **Latency is environment-dependent.** Response latency depends on provider
  load, region, network path, and other runtime conditions. It is not a
  controlled laboratory measurement.

- **Provider model mutability.** A rolling provider alias may later resolve to
  different underlying model weights.

- **Scope exclusions.** V1 does not benchmark multimodal input, coding, RAG,
  live web search, real tool execution, multi-agent execution, fine-tuning, or
  production routing.

---

## 9. Frozen V1.0.0 Contract

The following are frozen for the published V1.0.0 benchmark:

- 50-case production dataset
- five workload domains
- case distribution
- deterministic-check semantics
- deterministic-check validation rules
- Chinese length-check rule
- three LLM judge dimensions
- 1–5 judge scale
- no-private-chain-of-thought rule
- cross-family dual-judge design
- fixed-priority judge selection
- candidate / judge telemetry separation
- equal-denominator ranking rule
- incomplete-model comparative-metric suppression
- RMB / CNY presentation
- quality × cost Pareto analysis
- quality × cost × P95 latency Pareto analysis
- model registry snapshot
- pricing snapshot
- FX snapshot
- runtime envelope
- execution provenance

The human-calibration sampling **design** is documented, but human calibration
execution is not part of the completed V1.0.0 evidence.

The following are no longer “open Phase 3 / Phase 4” items:

- production case content
- candidate model registry
- judge model registry
- pricing
- FX values
- canonical execution configuration

They were frozen for the released benchmark.

Any future change to benchmark-defining inputs or evaluation semantics should be
published under a new benchmark version rather than silently modifying the
meaning of V1.0.0.

Published canonical V1 artifacts should be treated as immutable historical
evidence.

---

## 10. Related Evidence

Product definition:

`PRODUCT_SPEC_V1.md`

Dataset design and governance:

- `CASE_DESIGN_STANDARD_V1.md`
- `CASE_MATRIX_V1.md`
- `DATASET_QA_V1.md`
- `DATASET_FREEZE_V1.md`

Architecture and decisions:

- `ARCHITECTURE.md`
- `DECISIONS.md`
- `HANDOFF.md`

Canonical public result artifacts:

- `../release/v1/leaderboard.csv`
- `../release/v1/leaderboard.json`
- `../release/v1/pareto.json`
- `../release/v1/cost_summary.json`
- `../release/v1/latency_summary.json`
- `../release/v1/judge_disagreement.json`
- `../release/v1/run_manifest.json`

The canonical V1 release should be interpreted through these frozen artifacts
together rather than through any single metric in isolation.
