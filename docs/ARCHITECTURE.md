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
| `src/models.py` | Load, validate, and expose the configurable model pool (candidates and judges) | Hard-code model names into logic |
| `src/cases.py` | Load and validate case files against the V1 schema | Contain the production dataset |
| `src/providers.py` | One OpenAI-compatible HTTP client plus a synthetic offline client; provider differences are configuration | Branch on provider name in benchmark logic |
| `src/deterministic.py` | Run machine-checkable constraints and produce `constraint_pass_rate` | Judge subjective quality |
| `src/judge.py` | Judge pool, leave-one-provider-out selection, strict JSON parsing, dual-judge aggregation | Repair or clamp invalid scores |
| `src/pricing.py` | Native price lookup, tier and time-of-day rules, currency normalisation to CNY | Silently convert currencies |
| `src/analytics.py` | Latency percentiles, cost metrics, quality per CNY, Pareto frontier | Write files |
| `src/runner.py` | Orchestrate the pipeline and assemble the versioned results document | Contain provider-specific behavior |
| `src/leaderboard.py` | Render one self-contained HTML report | Require a network, CDN, or build step |
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
6. **Cross-family judge selector** excludes judges from the candidate's own
   family or provider, then selects exactly two eligible judges.
7. **Dual LLM evaluation** scores the response twice, once per selected judge,
   against the shared rubric and the case criteria.
8. **Score aggregation** averages the two judges and normalises to 0-100 while
   preserving each judge's scores for agreement analysis.
9. **Cost / latency analytics** compute averages, P50, P95, cost per 100 tasks,
   and quality per CNY.
10. **Pareto analysis** marks non-dominated models on quality × cost, and
    optionally quality × cost × latency.
11. **Snapshot results** are written as one versioned JSON document containing
    dataset version, model IDs, pricing snapshot, FX snapshot, and judge pool.
12. **Leaderboard / reports** render a single self-contained HTML file.

---

## 4. Configuration-driven model pool

The model pool is data, not code. It lives in a JSON file and is validated on
load. No benchmark logic may reference a specific model name.

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
| `pricing` | Native price, currency, snapshot date, source |

### Model family vs inference provider

The public benchmark must distinguish these two concepts. A model family is who
trained the model; an inference provider / channel is who serves it. The same
family can be reached through a native API or through an aggregated gateway, and
those paths have different latency, price, and reliability. V1 prefers native
APIs and reports which channel was used.

### Judge selection rule

Given a candidate response:

1. Build the eligible judge list by removing every judge whose `model_family` or
   `provider_key` matches the candidate's.
2. If fewer than two judges remain, the response is recorded as
   judge-unavailable rather than scored by a same-family judge.
3. Otherwise select exactly two, deterministically, using a stable hash of the
   candidate key to rotate the starting position in the sorted eligible list.
   Rotation keeps the pool balanced across candidates across a run, and the
   stable hash keeps the selection reproducible.
4. Assert the two selected judges come from different families.

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
