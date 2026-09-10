# AIProductBench CN V1 — Architecture

**Status: implemented at framework level. No live runs authorized.**

This document describes the target pipeline, module responsibilities, and data
flow. The architecture is intentionally small. It is a benchmark, not a
framework product.

---

## 1. Pipeline

```
case definitions
    ↓
candidate runner
    ↓
provider-native adapters
    ↓
raw candidate responses
    ↓
deterministic evaluator
    ↓
cross-family judge selector
    ↓
dual LLM evaluation
    ↓
score aggregation
    ↓
cost / latency analytics
    ↓
Pareto analysis
    ↓
snapshot results
    ↓
leaderboard / reports
```

---

## 2. Module responsibilities

| Module | Responsibility | Must not do |
| --- | --- | --- |
| `src/config.py` | Paths, versions, the five domains, rubric dimensions, scoring bounds, request policy | Hold model-specific business logic |
| `src/models.py` | Load, validate, and expose the single shared model registry (candidate and judge roles) | Hard-code model names into logic |
| `src/cases.py` | Load and validate case files against the V1 schema | Contain the production dataset |
| `src/providers.py` | One OpenAI-compatible HTTP client plus a synthetic offline client; provider differences are configuration | Branch on provider name in benchmark logic |
| `src/deterministic.py` | Run the 21 machine-checkable constraint types and produce `constraint_pass_rate` | Judge subjective quality |
| `src/judge.py` | Judge role, fixed-priority selection, leave-one-provider-out exclusion, strict JSON parsing, dual-judge aggregation | Repair or clamp invalid scores; mix judge metrics with candidate metrics |
| `src/pricing.py` | Native price lookup, tier and time-of-day rules, currency normalisation to CNY | Silently convert currencies |
| `src/analytics.py` | Latency percentiles, cost metrics, quality per CNY, Pareto frontier | Write files |
| `src/runner.py` | Orchestrate the pipeline, assemble the versioned results document, gate cross-model comparative metrics on equal denominators | Contain provider-specific behavior |
| `src/leaderboard.py` | Render one self-contained HTML report, labelling metrics that are unavailable because a run is incomplete | Require a network, CDN, or build step |
| `run_benchmark.py` | CLI: validate, estimate, dry-run, confirm | Spend money without explicit confirmation |

---

## 3. Data flow

1. **Case definitions** are loaded from a JSON dataset and validated against the
   five-domain V1 schema.
2. **Candidate runner** iterates cases × candidate models.
3. **Provider-native adapters** issue one request per (case, model) pair using
   the model's configured native provider endpoint.
4. **Raw candidate responses** are stored with provider-reported tokens and
   measured latency. Missing provider metrics stay `null`.
5. **Deterministic evaluator** runs any case-defined machine checks and produces
   a per-response `constraint_pass_rate`.
6. **Cross-family judge selector** applies the configured fixed judge priority,
   excludes judges from the candidate's own family or provider, then selects the
   first two eligible cross-family judges.
7. **Dual LLM evaluation** scores the response twice, once per selected judge,
   against the shared rubric and the case criteria.
8. **Score aggregation** averages the two judges and normalises to 0-100 while
   preserving each judge's scores for agreement analysis.
9. **Cost / latency analytics** compute averages, P50, P95, cost per 100 tasks,
   and quality per CNY. Cross-model metrics require equal denominators: when a
   model is incomplete, `actual_spend_cny`, `calls_completed`,
   `cases_completed`, partial tokens, and partial latency are kept as
   diagnostics while `cost_per_100_tasks_cny`, `quality_per_cny`, Pareto
   eligibility, and rank are suppressed to `null`. The summary records this in
   its `metric_availability` block.
10. **Pareto analysis** marks non-dominated models on quality × cost, and
    optionally quality × cost × latency. Incomplete models are excluded.
11. **Snapshot results** are written as one versioned JSON document containing
    dataset version, model IDs, pricing snapshot, FX snapshot, and judge pool.
12. **Leaderboard / reports** render a single self-contained HTML file.

---

## 4. One shared model registry

V1 has exactly **one** model registry. It is data, not code: it lives in
`data/models_v1.json` and is validated on load. No benchmark logic may reference
a specific model name.

A registry entry is a real model entry, and a model may be both an evaluated
candidate and a judge:

```
candidate = true
judge_eligible = true
```

There are **no judge-only duplicate entries** for a model that already exists as
a candidate. The validator rejects two entries sharing a `model_family` and
`product_tier`, which is the shape a duplicate judge copy takes. Adding a judge
means marking an existing entry `judge_eligible`, not cloning it.

### Candidate role vs judge role

Candidate execution and judge execution are distinct **roles** over the same
registry, and the two roles produce strictly separate metrics:

| | Candidate role | Judge role |
| --- | --- | --- |
| Cost | `candidate_cost_cny` | `judge_cost_cny` |
| Latency | `latency_ms` on the response record | `latency_ms` on the judgement record |
| Aggregate | `summary.models[].latency` | `summary.judge_overhead` |

Candidate inference cost is never mixed with judge evaluation cost, and
candidate latency is never mixed with judge latency. A model serving both roles
contributes to both series, and they stay separate.

### Registry fields

Each model entry carries:

| Field | Purpose |
| --- | --- |
| `key` | Stable internal identifier used in results |
| `display_name` | Human-readable label for reports |
| `model_family` | Model family, e.g. Qwen, DeepSeek, GLM |
| `provider` | Inference provider / channel owner |
| `provider_key` | Stable provider identifier used for judge exclusion |
| `product_tier` | flagship / balanced / value |
| `inference_channel` | `native` or a gateway identifier |
| `thinking_mode` | `disabled`, `enabled`, or `provider_default` |
| `model_id` | Literal API model identifier |
| `model_id_status` | `verified` or `unverified` |
| `base_url` | Provider-native endpoint |
| `api_key_env` | Environment variable holding the credential |
| `wire_api` | `chat_completions` or `responses` |
| `judge_eligible` | Whether the model may serve as a judge |
| `candidate` | Whether the model is an evaluated candidate |
| `pricing` | Native price, currency, snapshot date, source |

### Model family vs inference provider

The public benchmark must distinguish these two concepts. A model family is who
trained the model; an inference provider / channel is who serves it. The same
family can be reached through a native API or through an aggregated gateway, and
those paths have different latency, price, and reliability. V1 prefers native
APIs and reports which channel was used.

### Judge selection rule

V1 uses **deterministic fixed-priority selection**, not per-candidate hashing.
The priority list is declared in configuration:

```json
"judge_priority": ["qwen_flagship", "deepseek_flagship", "glm_flagship"]
```

Given a candidate response:

1. Order the judge pool by the configured priority list. Judges not named in the
   list follow in key order, so the ordering is always total and stable.
2. Remove every judge whose `model_family` or `provider_key` matches the
   candidate's.
3. Take the first two remaining judges. Skip any judge whose family is already
   represented, so the selected pair is always cross-family.
4. If fewer than two eligible cross-family judges remain, the response is
   recorded as judge-unavailable. A same-family judge is **never** substituted
   merely to obtain a second score.

Resulting pairs, which the test suite asserts explicitly:

| Candidate family | Selected judges |
| --- | --- |
| Qwen | DeepSeek + GLM |
| DeepSeek | Qwen + GLM |
| GLM | Qwen + DeepSeek |
| Kimi | Qwen + DeepSeek |
| MiniMax | Qwen + DeepSeek |
| Doubao | Qwen + DeepSeek |

The reason hashing was rejected: giving unrelated candidate models different
judge pairs introduces an avoidable evaluation confound. With fixed priority,
every candidate family is scored by the same judges, so a difference between two
models reflects the models rather than the judging.

---

## 5. Pricing and currency

Every price keeps its native form:

```
native_price, native_currency
```

and gains a normalized display form:

```
display_currency = CNY
normalized_cost_cny
```

Rules:

- If the provider publishes in CNY, use it directly. No conversion.
- If conversion is required, an explicit FX snapshot must supply `fx_pair`,
  `fx_rate`, `fx_snapshot_date`, and source metadata.
- If no FX snapshot is configured, the CNY value is `null` with a stated reason.
  The pipeline never invents a rate and never hard-codes a permanent one.
- Active V1 pricing must be verified against the provider for the literal
  configured model ID. Retired V0.1-era prices live in
  `historical_pricing_archive` with status `historical_inactive`; that block is
  never read for cost estimation, and the validator rejects an active model
  entry that references an archived pricing model ID.

Cost separation is structural: candidate inference cost and judge evaluation
cost are separate fields all the way through aggregation to the leaderboard.

---

## 6. File layout

```
.
├── run_benchmark.py            # CLI
├── data/
│   ├── models_v1.json          # configurable model pool (+ judge pool)
│   ├── fixtures/
│   │   └── synthetic_v1_cases.json   # synthetic, framework-validation only
│   └── archive/
│       └── test_cases_v0_1.json      # preserved V0.1 dataset
├── docs/                       # product spec, methodology, architecture, decisions
├── src/                        # pipeline modules (see §2)
├── tests/                      # unittest suite
└── results/                    # local artifacts, git-ignored
```

---

## 7. Deliberate non-goals

To keep V1 small and readable, the following are explicitly **not** built:

- a plugin or adapter registry
- a provider abstraction hierarchy
- a database or ORM
- a web backend or API service
- a frontend framework or build step
- containers or deployment infrastructure
- a scheduler, queue, or distributed runner
- retries beyond a single small in-process policy

Provider differences stay in configuration. If a future provider needs a
genuinely different wire protocol, the correct change is one more branch in
`src/providers.py`, not a new layer.

---

## 8. Execution modes

| Mode | Network | Cost | Writes |
| --- | --- | --- | --- |
| `--validate-only` | none | none | nothing |
| `--estimate` | none | none | nothing |
| `--dry-run` | none, socket-blocked in tests | none | synthetic artifacts under `results/` only |
| `--confirm` | provider APIs | real money | `sample_results.json`, `leaderboard.html` |

A real run refuses to start without `--confirm`, and refuses to start while any
configured model ID is unverified.
