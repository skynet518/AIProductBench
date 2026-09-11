# AIProductBench CN V1 — Product Specification

**Status: RELEASED — V1.0.0**

**Release status: public V1 released. Canonical paid benchmark execution completed.**

This document is the frozen product definition for AIProductBench CN V1. It is
persistent project memory: a new GPT, Codex, DeepSeek, or human contributor
should be able to read this file and understand what V1 is, why it exists, what
was released, and what it deliberately does not do.

Canonical official run:

`official-v1-20260911T103838Z`

---

## 1. Version status

| Version | Status | Intent |
| --- | --- | --- |
| V0.1 | Complete, internal engineering scaffold | Validate the pipeline end to end. Not intended for public release. |
| AIProductBench CN V1.0.0 | Released | Public portfolio release with canonical paid benchmark results. |

V0.1 was never the public product. It existed as engineering proof that the
pipeline could run end to end: cases load, candidates answer, judges score,
costs and latency are tracked, and a leaderboard renders.

AIProductBench CN V1.0.0 is the first public benchmark release.

Its canonical paid execution is:

`official-v1-20260911T103838Z`

The canonical run attempted all planned paid evaluation units:

- 500 / 500 candidate evaluation units
- 990 / 990 judge evaluation units
- 1,490 formal evaluation units in total

The execution is therefore complete:

`execution_complete = true`

Not every candidate model satisfied the frozen completeness contract:

`all_models_complete = false`

Under the strict equal-denominator rule, 4 of 10 models are complete and
rank-eligible. Incomplete models retain diagnostic evidence but are excluded
from the official ranking and Pareto frontier.

Canonical paid API spend:

`¥109.73182552`

The released benchmark artifacts are real paid-run results, not synthetic
dry-run output.

---

## 2. Why this project exists

AI product teams in China face a specific and recurring decision: *which model
do we build on?*

The public information available to answer that question is often poorly aligned
with real product work. Vendor marketing claims are not directly comparable.
Global leaderboards can mix workloads that do not match Chinese product
scenarios, are frequently English-first, and commonly emphasize quality without
the cost and latency constraints that materially affect product decisions.

AIProductBench CN exists to make that decision more evidence-based, using tasks
that resemble real Chinese AI product work and reporting quality, cost, latency,
and constraint adherence together.

---

## 3. Positioning

AIProductBench CN is a **practical model-selection benchmark for Chinese LLMs,
designed for AI product teams choosing models under real quality, cost, and
latency constraints.**

It is **not** intended to claim a permanent "best Chinese model".

Any ranking is a snapshot based on:

- dated benchmark cases
- dated provider/model configuration
- dated pricing
- dated FX data
- a specific evaluation methodology
- a specific workload distribution

A different workload, model revision, price, or later benchmark version can
legitimately produce a different answer.

### The question the benchmark answers

> Which model should an AI product team choose for a given workload, budget,
> quality requirement, and latency requirement?

The deliverable is therefore not a single universal winner.

It is a decision surface showing which models are defensible choices, what each
one costs, and what quality or latency trade-offs are associated with choosing
them.

---

## 4. Frozen V1 scope

The following defines the released V1 scope.

Changes to these assumptions belong in a later benchmark version and should be
recorded explicitly in `DECISIONS.md`.

| Dimension | V1 scope |
| --- | --- |
| Candidate models | 10 |
| Provider integrations | 6 |
| Tasks | 50 frozen real-world AI product tasks |
| Capability domains | 5 |
| Evaluation | Hybrid: deterministic checks + LLM evaluation |
| Deterministic checks | 21 supported check types |
| Judges | Cross-family dual-judge |
| Human calibration | Sampling design prepared; human review not completed in V1.0.0 |
| Quality metrics | Overall quality, constraint pass rate, task success diagnostics |
| Cost metrics | Candidate inference cost, cost per 100 tasks, quality / cost analysis |
| Latency metrics | Mean, P50, P95 candidate latency |
| Currency | RMB / CNY presentation with frozen FX snapshot |
| Selection analysis | Pareto frontier over quality × cost and quality × cost × latency |
| Reproducibility | Frozen dataset, registry, pricing, FX, runtime, and execution provenance |

### Canonical V1 execution envelope

| Setting | V1 value |
| --- | --- |
| Candidate generation ceiling | 32,768 tokens |
| Judge generation ceiling | 16,384 tokens |
| Client read timeout | 600 seconds |
| Global concurrent paid calls | 6 |
| Default per-provider concurrency | 2 |
| Kimi max in-flight | 1 |
| Hard cost ceiling | ¥150.00 |

---

## 5. Explicitly out of scope for V1

The following capabilities were **not included in V1.0.0**:

- Vision and image understanding
- Multimodal evaluation
- Coding benchmark
- RAG benchmark
- Live web search benchmark
- Real tool execution
- Multi-agent execution benchmark
- Fine-tuning or training
- Production routing system
- Hosted SaaS backend

They remain outside the released V1 scope unless a later version explicitly
introduces them.

### Documented future candidates

Potential later-version extensions include:

- Multi-turn conversation evaluation
- Context-length stress testing
- Streaming latency / time to first token
- Aggregated gateway tracks alongside native-provider tracks
- Scheduled benchmark re-runs with published diffs
- Confidence intervals and statistical significance testing
- Expanded human calibration

These are future candidates, not claims about V1.0.0.

---

## 6. Audience

| Audience | What they need from this project |
| --- | --- |
| AI product managers | A defensible model-selection method and a quality / cost / latency trade-off view |
| Engineers | A reproducible and inspectable evaluation pipeline |
| Recruiters / reviewers | Evidence of benchmark design, model integration, evaluation governance, and analytical rigor |
| Chinese AI teams | Practical evidence about models available in the Chinese AI ecosystem |

---

## 7. V1 release criteria

V1 was designed so that a new reader can:

1. Understand the methodology and its limitations without reading the code.
2. Inspect the frozen 50-case dataset and judge whether the cases resemble real product work.
3. Inspect the frozen dataset, registry, pricing, FX, runtime, and execution provenance.
4. Read official results reporting quality, cost, and candidate latency.
5. See Pareto analysis instead of relying only on a single quality ranking.
6. Understand which models are complete and rank-eligible and why incomplete models are excluded.
7. Trace published conclusions back to canonical public artifacts.

The released public evidence is stored under:

`release/v1/`

---

## 8. Honesty constraints

These are product requirements, not stylistic preferences.

- Never fabricate provider metrics. Missing token, cost, or latency data is
  recorded as missing, never estimated into a result.
- Never silently convert currencies. Conversion requires an explicit, dated FX
  snapshot with a named source.
- Never present an unverified model ID or price as verified.
- Never present synthetic dry-run output as a real result.
- Never describe the benchmark as scientifically comprehensive.
- Never rank an incomplete model using a reduced denominator.
- Never place an incomplete model on the official Pareto frontier.
- State judge-family bias and other material limitations wherever results are
  published.
- Do not interpret the 0.0008 measured quality difference between Kimi K3 and
  DeepSeek V4 Flash as statistically significant; V1 does not perform repeated
  sampling or significance testing.
- Human calibration review was not completed for V1.0.0 and must not be
  presented as completed.

---

## 9. Released V1 provenance

The canonical public release is tied to the following frozen evidence:

| Field | Canonical V1 |
| --- | --- |
| Canonical run | `official-v1-20260911T103838Z` |
| Execution commit | `f3225f51824f4e3c047b2df3c15092a803231291` |
| Runtime baseline | `e10ceb0aa89483050ec0b09eb96e7d16c37e4e09` |
| Dataset semantic manifest | `6b450383e528a5a0a6b813112f96182a3625c04c948839fc551c8ded63da513c` |
| Registry | `v1-registry-2026-09-11.3` |
| Registry SHA | `259b02adb05f73ab2d800c8f41d9b2608b8eddb17ae97e9d3f31ecff79409eab` |
| Pricing | `v1-pricing-2026-09-11.1` |
| Pricing SHA | `9f7af42243e5e0b78b1776934de5483f0e3e650765a19dd929e78af10aa15c42` |
| FX snapshot | `ecb-2026-09-10-usd-cny` |
| USD / CNY | `6.706267217630854` |

Published V1 artifacts should be treated as immutable historical evidence.

A future benchmark that changes models, dataset, pricing, methodology, runtime
configuration, or evaluation logic should be published as a new version rather
than silently replacing V1.

---

## 10. Related documents

- `METHODOLOGY_V1.md` — released V1 evaluation methodology
- `ARCHITECTURE.md` — pipeline, modules, and data flow
- `CASE_DESIGN_STANDARD_V1.md` — production-case authoring standard
- `CASE_MATRIX_V1.md` — frozen 50-case coverage design
- `DATASET_QA_V1.md` — production dataset QA record
- `DATASET_FREEZE_V1.md` — frozen dataset manifest
- `DECISIONS.md` — chronological decision log
- `HANDOFF.md` — current post-release operational status
- `../release/v1/run_manifest.json` — canonical execution and provenance record
