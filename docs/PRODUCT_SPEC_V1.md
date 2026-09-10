# AIProductBench CN V1 — Product Specification

**Status: IN DEVELOPMENT**

**Release status: not released. No live benchmark has been authorized.**

This document is the frozen product definition for AIProductBench CN V1. It is
persistent project memory: a new GPT, Codex, DeepSeek, or human contributor
should be able to read this file and understand what V1 is, why it exists, and
what it deliberately does not do.

---

## 1. Version status

| Version | Status | Intent |
| --- | --- | --- |
| V0.1 | Complete, internal engineering scaffold | Validate the pipeline end to end. Not intended for public release. |
| AIProductBench CN V1 | In development, unreleased | The public portfolio release. |

V0.1 was never a product. It exists as engineering proof that the pipeline
runs: cases load, candidates answer, a judge scores, costs and latency are
tracked, and a leaderboard renders. Phase 1 and Phase 1.5 completed that
scaffold and it is preserved in git history as a checkpoint.

No live paid benchmark has been run for either version. Every artifact produced
so far is synthetic dry-run output.

---

## 2. Why this project exists

AI product teams in China face a specific and recurring decision: *which model
do we build on?* The public information available to answer that question is
poor. Vendor marketing claims are not comparable. Global leaderboards mix
workloads that do not match local product work, are usually English-first, and
publish quality alone without the cost and latency reality that actually decides
the choice.

AIProductBench CN exists to make that decision evidence-based, using tasks that
resemble real Chinese AI product work and reporting quality, cost, and latency
together in RMB.

---

## 3. Positioning

AIProductBench CN is a **practical model-selection benchmark for Chinese LLMs,
designed for AI product teams choosing models under real quality, cost, and
latency constraints.**

It is **not** intended to claim a permanent "best Chinese model". Any ranking it
produces is a snapshot: dated models, dated prices, a dated dataset, and a
specific workload. A different workload or a later date can legitimately produce
a different answer.

### The question the benchmark answers

> Which model should an AI product team choose for a given workload, budget,
> quality requirement, and latency requirement?

The deliverable is therefore not a single winner. It is a decision surface: for
each workload, which models are defensible choices, what each one costs, and
what quality and latency you give up by choosing it.

---

## 4. Frozen V1 scope

The following is frozen for V1. Changes require an explicit decision logged in
`DECISIONS.md`.

| Dimension | V1 scope |
| --- | --- |
| Candidate models | Approximately 10 |
| Model families / providers | Approximately 6 Chinese providers |
| Tasks | 50 real-world AI product tasks |
| Capability domains | 5 |
| Evaluation | Hybrid: deterministic checks + LLM evaluation |
| Judges | Cross-family dual-judge |
| Human calibration | Base stratified sample of 50 responses plus a risk-based extension of 10–20 (≈50–70 total) |
| Quality metrics | Score, constraint pass rate, task success rate |
| Cost metrics | Per-call cost, cost per 100 tasks, quality per CNY |
| Latency metrics | Average, P50, P95 |
| Currency | RMB / CNY native presentation |
| Selection analysis | Pareto frontier over quality × cost (optionally × latency) |
| Reproducibility | Versioned quarterly snapshot |

---

## 5. Explicitly out of scope for V1

These are **not** V1 deliverables. They must not be implemented while V1 is in
development, even if they appear cheap to add.

- Vision and image understanding
- Multimodal evaluation of any kind
- Coding benchmark
- RAG benchmark
- Live web search benchmark
- Real tool execution
- Multi-agent execution benchmark
- Fine-tuning or training
- Production routing system
- Hosted SaaS backend

### Documented but not implemented: V1.1 / V2 candidates

Recorded so they are not lost, and so nobody mistakes them for V1 scope:

- Multi-turn conversation evaluation
- Context-length stress testing
- Streaming latency (time to first token)
- An aggregated gateway track alongside the native-provider track
- Scheduled quarterly re-runs with published diffs
- Confidence intervals and statistical significance testing

---

## 6. Audience

| Audience | What they need from this project |
| --- | --- |
| AI product managers | A defensible model-selection method and a cost/quality tradeoff view |
| Engineers | A reproducible, inspectable pipeline they could re-run |
| Recruiters / reviewers | Evidence of evaluation design, API integration, and analytical rigor |
| Chinese AI teams | Practical, RMB-native data on models they can actually buy |

---

## 7. What "done" means for V1

V1 is complete when a new reader can:

1. Understand the methodology and its limits without reading the code.
2. See the 50-case dataset and judge the cases as realistic product work.
3. Reproduce the run from documented commands and pinned model versions.
4. Read a leaderboard that reports quality, cost, and latency in RMB.
5. See a Pareto frontier rather than a single "best model" claim.
6. Understand exactly which decisions are defensible for which workload.

---

## 8. Honesty constraints (frozen)

These are product requirements, not stylistic preferences.

- Never fabricate provider metrics. Missing token, cost, or latency data is
  recorded as missing, never estimated into a result.
- Never silently convert currencies. Conversion requires an explicit, dated FX
  snapshot with a named source.
- Never present an unverified model ID or price as verified.
- Never present synthetic dry-run output as a real result.
- Never describe the benchmark as scientifically comprehensive.
- State the judge-family bias limitation wherever results are published.

---

## 9. Related documents

- `METHODOLOGY_V1.md` — frozen evaluation design
- `ARCHITECTURE.md` — pipeline, modules, and data flow
- `DECISIONS.md` — chronological decision log
- `HANDOFF.md` — current operational status
