# AIProductBench CN V1 — Methodology

**Status: frozen design. Dataset not yet built. No live runs authorized.**

This document defines how AIProductBench CN V1 measures models. It is the
authoritative methodology reference. If code and this document disagree, the
disagreement is a bug in one of them.

---

## 1. Dataset

### Size

50 total cases.

### Domains

Five domains, 10 cases each:

| # | Domain | What it measures |
| --- | --- | --- |
| 1 | `instruction_constraint_following` | Obeying explicit format, length, structure, and negative constraints |
| 2 | `structured_information_analysis` | Turning messy or tabular input into fixed, machine-readable structure |
| 3 | `product_reasoning_decision` | Prioritisation, measurement design, and launch judgment |
| 4 | `chinese_business_communication` | Chinese business register, tone, and audience adaptation |
| 5 | `agent_workflow_planning` | Decomposing a goal into a correct, ordered, executable workflow |

### Language composition

- Approximately 40 Chinese-first cases
- Approximately 10 English or cross-lingual cases

### Difficulty composition

Within every domain: 2 easy, 5 medium, 3 hard.

### Case schema

Every case must support:

| Field | Required | Notes |
| --- | --- | --- |
| `id` | yes | Stable, unique, domain-prefixed |
| `domain` | yes | One of the five frozen domains |
| `difficulty` | yes | `easy` \| `medium` \| `hard` |
| `language` | yes | `zh` \| `en` \| `mixed` |
| `prompt` | yes | Self-contained |
| `evaluation_criteria` | yes | Case-specific criteria supplied to every judge |
| `deterministic_checks` | when applicable | Machine-checkable constraints |

**The final 50 cases are a Phase 3 deliverable.** Phase 2 defines and validates
the schema only. Synthetic fixtures used to exercise the framework are labelled
synthetic and are not the dataset.

---

## 2. Evaluation design

V1 uses **hybrid evaluation**: deterministic checks where a constraint is
objectively testable, LLM evaluation where judgment is required.

### A. Deterministic checks

The evaluator implements **18 check types**, applied when a case declares
machine-checkable constraints:

| Group | Check types |
| --- | --- |
| Structure | `valid_json`, `required_keys`, `forbidden_keys` |
| Item count | `exact_item_count`, `max_items`, `min_items`, `exact_bullet_count` |
| Length | `max_words`, `min_words`, `max_chars`, `min_chars` |
| Content | `required_phrases`, `forbidden_phrases`, `required_regex`, `forbidden_regex` |
| Order and format | `ordering`, `no_markdown_fence` |
| Numeric | `numeric_range` |

Cases declare checks; cases that need none declare none. The evaluator reports
`null` for a case with no checks rather than a fabricated pass rate.

Deterministic evaluation produces:

```
constraint_pass_rate = passed_checks / total_checks
```

It is reported per case and aggregated per model. It is never used to override
LLM judgment, and LLM judgment never overrides a failed deterministic check.
They answer different questions and are reported side by side.

### B. LLM evaluation

Three shared judge dimensions, each scored as an integer from 1 to 5:

| Dimension | Question |
| --- | --- |
| `task_completion` | Did the response fully do what the case asked, using only the information given? |
| `reasoning_quality` | Is the reasoning correct, specific, and decision-ready? |
| `instruction_following` | Did it obey every explicit constraint, including negative ones? |

Judges receive **both** the shared rubric and the case-level
`evaluation_criteria`. Case-specific criteria are authoritative where they are
more concrete.

Judge output must be strict, machine-readable JSON. Invalid judge output is
rejected, never repaired.

### C. Dual-judge design

V1 has **one shared model registry**, and the judge pool is a set of
judge-eligible entries in it. A model may be both an evaluated candidate and a
judge; there are no judge-only duplicate copies of an existing model. The judge
role and the candidate role produce strictly separate metrics — judge
evaluation cost is never added to candidate inference cost, and judge latency is
never mixed with candidate latency.

Target judge families:

- Qwen flagship
- DeepSeek flagship
- GLM flagship

**Leave-one-provider-out rule:** a candidate response must not be evaluated by a
judge from the same model family or provider when an alternative is available.

**Exactly two** valid cross-family judge evaluations are produced per candidate
response.

**Fixed-priority selection.** Judges are ordered by an explicit priority list
declared in configuration, not by hashing the candidate:

```
qwen_flagship > deepseek_flagship > glm_flagship
```

The candidate's own family and provider are excluded, then the first two
remaining cross-family judges are selected. A same-family judge is never
substituted to obtain a second score; if fewer than two eligible judges remain,
the response is recorded as judge-unavailable.

| Candidate family | Judges |
| --- | --- |
| Qwen | DeepSeek + GLM |
| DeepSeek | Qwen + GLM |
| GLM | Qwen + DeepSeek |
| Kimi, MiniMax, Doubao | Qwen + DeepSeek |

Per-candidate hash rotation was considered and rejected (see `DECISIONS.md`
D-018): giving unrelated candidates different judge pairs introduces an
avoidable evaluation confound.

The reason for two judges rather than one: a single judge from one family
produces a number nobody can audit. Two independent cross-family judges let the
project publish judge agreement, which is the honest measure of how much the
score depends on the judge.

### D. Human calibration

A stratified human review sample of approximately 10% of candidate responses is
planned. Sampling covers:

- all candidate models
- all five domains
- easy, medium, and hard cases

Future reporting should include:

- Judge A vs Judge B agreement
- Human vs Judge agreement

Calibration data must not be fabricated. If human review has not been performed,
the report says so and publishes no agreement figures.

---

## 3. Aggregation

Per candidate response:

```
judge_mean      = mean of the three dimensions, per judge
quality_score   = mean of judge_mean across the two judges   (1-5)
overall_score   = (quality_score - 1) / (5 - 1) * 100        (0-100)
```

Per model:

```
overall_score        = mean of overall_score across scored cases
constraint_pass_rate = passed deterministic checks / total deterministic checks
task_success_rate    = scored cases with every deterministic check passed / scored cases
judge_agreement      = agreement between the two judges (see §4)
```

---

## 4. Metrics

| Metric | Definition |
| --- | --- |
| `quality_score` | Mean of the three rubric dimensions, 1-5 |
| `constraint_pass_rate` | Deterministic checks passed / checks run |
| `task_success_rate` | Share of cases passing all deterministic checks |
| `overall_score` | Rubric score normalised to 0-100 |
| `avg_latency` | Mean wall-clock response time |
| `p50_latency` | Median response time |
| `p95_latency` | 95th percentile response time |
| `input_tokens` | Provider-reported input tokens |
| `output_tokens` | Provider-reported output tokens |
| `reasoning_tokens` | Provider-reported reasoning tokens when available |
| `candidate_inference_cost` | Cost of the candidate calls only |
| `judge_evaluation_cost` | Cost of the judge calls only, reported separately |
| `cost_per_100_tasks` | Candidate inference cost scaled to 100 tasks |
| `quality_per_cny` | Overall score per CNY of candidate inference cost |
| `judge_agreement` | Agreement between the two judges for the same response |

Custom-defined or absent metrics are reported as `null`. They are never
estimated into the result.

---

## 5. Pareto analysis

V1 presents a Pareto frontier rather than a rank-only table.

**Primary analysis: quality × cost.** A model is on the frontier when no other
model is at least as good on both axes and strictly better on one. Practically:
a model is dominated if another model has an equal or higher `overall_score` at
an equal or lower `cost_per_100_tasks`, with at least one strict improvement.

**Optional secondary analysis: quality × cost × latency.** The same dominance
rule extended to three axes.

Models not on the frontier are still reported, with the dominating model named.
This is what turns a leaderboard into a purchasing decision: a model can lose
the quality ranking and still be the correct choice under a cost or latency
constraint.

---

## 6. Reproducibility

A reproducible quarterly snapshot requires recording:

- literal provider model IDs, with snapshot/version identifiers where the
  provider publishes them
- which models are pinned snapshots and which are rolling aliases
- the dataset version used
- judge pool, judge prompt version, and judge selection rule
- pricing snapshot date, native currency, and source
- FX snapshot pair, rate, date, and source (when conversion was required)

Any model that is a rolling alias rather than a dated snapshot must be labelled
as such. A rolling alias means the run is not reproducible against the same
weights at a later date.

---

## 7. Known limitations (must be published with results)

- Approximately 10 models and 50 cases is a practical benchmark, not a
  scientific one. Confidence intervals require repeated sampling that V1 does
  not perform.
- Judge-family bias cannot be eliminated. Two cross-family judges reduce it and
  make it measurable; they do not remove it.
- Pricing is a dated manual snapshot, not a live billing feed. Real invoices
  differ.
- Latency depends on provider load, region, and network path, and is not a
  controlled laboratory measurement.
- Human calibration covers roughly 10% of responses, so it bounds judge error
  rather than proving judge correctness.
- Any model that cannot be pinned to a dated snapshot may change between runs.

---

## 8. Frozen vs open

**Frozen:** domain set and count, domain case counts, difficulty distribution,
language composition, three judge dimensions, the 1-5 integer scale, the
dual-judge cross-family rule, leave-one-provider-out, fixed-priority judge
selection over one shared registry, the deterministic-then-LLM hybrid, RMB
presentation, Pareto presentation.

**Open for Phase 3/4:** the literal content of the 50 cases, the literal judge
model IDs, the literal candidate model IDs, and the pricing and FX values.

**Active V1 pricing is currently unresolved for every model.** V0.1-era prices
were retired rather than reused, because they were verified for different model
IDs and different tiers (see `DECISIONS.md` D-019). No V1 rate may be inferred
from an earlier tier.
