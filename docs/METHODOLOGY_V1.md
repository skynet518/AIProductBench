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

The evaluator implements **21 check types**, applied when a case declares
machine-checkable constraints:

| Group | Check types |
| --- | --- |
| Structure | `valid_json`, `required_keys`, `forbidden_keys`, `exact_keys` |
| Item count | `exact_item_count`, `max_items`, `min_items`, `exact_bullet_count`, `section_bullet_count` |
| Length | `max_words`, `min_words`, `max_chars`, `min_chars`, `section_max_chars` |
| Content | `required_phrases`, `forbidden_phrases`, `required_regex`, `forbidden_regex` |
| Order and format | `ordering`, `no_markdown_fence` |
| Numeric | `numeric_range` |

Cases declare checks; cases that need none declare none. The evaluator reports
`null` for a case with no checks rather than a fabricated pass rate.

**Section-scoped checks.** `section_max_chars` and `section_bullet_count`
isolate one section of a response using a required `start_marker` and an
optional `end_marker` (null for the final section), then apply a length ceiling
or an exact hyphen-bullet count to the isolated body. A missing, duplicate, or
out-of-order marker fails the check safely. `exact_keys` requires a JSON object
whose key set equals the declared set exactly: order is irrelevant, and a
missing key, an extra key, invalid JSON, or a non-object root fails. These three
operators were added in Phase 3B-1.1 after production-case review; see
`DECISIONS.md` D-039.

**Deterministic-check declaration validation. A production case cannot pass
dataset validation if any deterministic-check declaration is malformed.** Every
declaration is checked against a centralized per-operator schema before a run.
An unknown operator, a missing or unexpected field, a wrong parameter type, a
non-compiling regex, an invalid or duplicate list member, a non-integer or
out-of-range count, or an invalid section marker (including identical
start/end markers) is a dataset-validation error. Declarations are validated by
`src/deterministic.py` and surfaced by `run_benchmark.py --validate-only`, so a
broken check fails before any paid execution is possible rather than becoming a
silent runtime failure. This changes no operator's runtime semantics.

**Check-quality rule.** A deterministic check must test the intended
constraint, not a superficial proxy. Requiring the word "risk" is not evidence
of risk analysis; requiring a fixed phrase is not evidence of correct
prioritisation; and confirming that a number appears is not evidence that a
computation is correct. Prefer structural, exact, enum, count, invariant, or
objectively derived checks, and leave genuinely subjective or semantic
constraints to judges. The rewrite and audit of the planned Strong/Partial
labels is recorded in `CASE_MATRIX_V1.md` §7 and `DECISIONS.md` D-034.

**Language rule for length checks.** `max_words` / `min_words` count
whitespace-separated tokens, which is meaningless for Chinese. Cases with
`language: "zh"` must use `max_chars` / `min_chars`; a word-count check on a
Chinese case is a validation error. English cases may use word counts.
Mixed-language cases may use word counts only with an explicit
`word_count_justification` recorded on the case. See `DECISIONS.md` D-024.

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
| `reasoning_quality` | Is the *observable* answer correct, specific, and decision-ready, and is its stated justification supported? |
| `instruction_following` | Did it obey every explicit constraint, including negative ones? |

Judges receive **both** the shared rubric and the case-level
`evaluation_criteria`. Case-specific criteria are authoritative where they are
more concrete.

**No private chain-of-thought.** V1 never asks a candidate to expose hidden
reasoning and never scores one. `reasoning_quality` is judged from what the
candidate actually delivered: a concise decision rationale, evidence cited from
the supplied facts, trade-offs, stated assumptions, and the basis of a
recommendation. A prompt or criterion must not request "show your reasoning",
"step-by-step reasoning", or "transparent reasoning". A correct answer with no
stated basis is not automatically high-scoring, and a fluent but unsupported
rationale is not high-scoring; both are judged on the observable answer. See
`CASE_DESIGN_STANDARD_V1.md` §6.

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

V1 does **not** cap human review at a fixed 10% of responses. The planned
calibration is a base stratified sample plus a risk-based extension.

**Base sample: 50 candidate responses.** The base sample covers:

- all candidate models
- all five domains
- easy, medium, and hard cases

**Risk-based extension: approximately 10–20 additional responses when
warranted.** Oversampling prioritises:

- hard cases
- cases with no deterministic checks
- responses with high Judge A / Judge B disagreement
- Kimi, MiniMax, and Doubao responses, because those three families share the
  same judge pair (Qwen flagship + DeepSeek flagship)
- responses near a close ranking boundary
- anomalous or surprising failures

Expected practical review size is therefore **approximately 50–70 responses**.
The base sample guarantees coverage of models, domains, and difficulty; the
extension spends additional review where judge error is most likely to change a
conclusion. Kimi, MiniMax, and Doubao coverage is mandatory in the base sample
so the correlated-judge risk in §7 is checked against human judgment rather than
merely disclosed.

Future reporting should include:

- Judge A vs Judge B agreement
- Human vs Judge agreement

The sampling *policy* is defined here. Executing the sample is a Phase 3/4 task.
Calibration data must not be fabricated; no agreement figures are invented, and
if human review has not been performed the report says so and publishes none.
See `DECISIONS.md` D-037.

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

### Equal-denominator rule

Official rankings require **equal denominators**. A candidate model holds an
official rank only when it has a valid scored result for every production
benchmark case — for a 50-case dataset, exactly 50 case-level scores.

If any case is judge-unavailable, permanently failed, or otherwise lacks a
required evaluation result after the allowed retry policy:

- the model/run is marked **INCOMPLETE**
- the case is never silently dropped
- no official overall ranking is computed from a reduced denominator
- the model is excluded from `ranked_models` and from the Pareto frontier

Partial diagnostic results remain visible for debugging, but an incomplete model
does not appear as a valid ranked model. This is enforced in `src/runner.py` and
covered by `tests/test_ranking_invariant.py`. See `DECISIONS.md` D-021 and D-022.

### Incomplete-run comparative metrics

An incomplete candidate run keeps its diagnostics and suppresses every metric
that only means something across equal denominators.

**Kept as diagnostics:** `actual_spend_cny` (real candidate spend), and
`calls_completed`, `cases_completed`, partial token usage (`tokens`), and
partial latency (`latency`) for the work that did complete.

**Suppressed for the incomplete run (reported as `null` / N/A):**

- `cost_per_100_tasks_cny`
- `quality_per_cny`
- official Pareto eligibility (`pareto_quality_cost`,
  `pareto_quality_cost_latency`)
- official rank (`rank`, and membership in `ranked_models`)

The reason is the same as the equal-denominator rule: these quantities are
comparisons between models, so a reduced or unequal base makes them
non-comparable rather than approximately comparable. The report must say the
metric is unavailable **because the run is incomplete**, not publish a number
computed over a smaller denominator. The summary carries a
`metric_availability` block naming the suppressed metrics and the affected
models. Enforced in `src/runner.py`, rendered by `src/leaderboard.py`, and
covered by `tests/test_ranking_invariant.py`. See `DECISIONS.md` D-036.

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
estimated into the result. Cross-model comparative metrics are additionally
`null` for any model in an incomplete run (see the incomplete-run rule above):
availability, not just value, is part of the honest report.

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
- **Correlated judges for tail families.** Kimi, MiniMax, and Doubao candidates
  are all scored by the same judge pair (Qwen flagship + DeepSeek flagship). If
  those two judges share a systematic bias, the three families' scores are
  correlated with each other rather than independent. This is disclosed rather
  than corrected, and human calibration sampling targets these families
  explicitly. See `DECISIONS.md` D-023.
- Pricing is a dated manual snapshot, not a live billing feed. Real invoices
  differ.
- Latency depends on provider load, region, and network path, and is not a
  controlled laboratory measurement.
- Human calibration covers a base sample of 50 responses plus a risk-based
  extension of roughly 10-20 when warranted (about 50-70 in practice), so it
  bounds judge error rather than proving judge correctness.
- Any model that cannot be pinned to a dated snapshot may change between runs.

---

## 8. Frozen vs open

**Frozen:** domain set and count, domain case counts, difficulty distribution,
language composition, three judge dimensions, the 1-5 integer scale, the
dual-judge cross-family rule, leave-one-provider-out, fixed-priority judge
selection over one shared registry, the deterministic-then-LLM hybrid, RMB
presentation, Pareto presentation, the equal-denominator ranking rule, the
incomplete-run comparative-metric suppression rule, the deterministic
check-quality rule, the no-private-chain-of-thought rule, the human calibration
sampling policy (base 50 plus risk-based extension), and the Chinese
length-check rule.

**Open for Phase 3/4:** the literal content of the 50 cases, the literal judge
model IDs, the literal candidate model IDs, and the pricing and FX values.

Case authoring is governed by `CASE_DESIGN_STANDARD_V1.md`; the planned coverage
of all 50 slots is in `CASE_MATRIX_V1.md`.

**Active V1 pricing is currently unresolved for every model.** V0.1-era prices
were retired rather than reused, because they were verified for different model
IDs and different tiers (see `DECISIONS.md` D-019). No V1 rate may be inferred
from an earlier tier.
