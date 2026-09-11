# AIProductBench CN — Project Instructions

## CURRENT TARGET

**AIProductBench CN V1** — a practical model-selection benchmark for Chinese
LLMs, built for AI product teams choosing models under real quality, cost, and
latency constraints.

V1 uses RMB/CNY user-facing cost presentation and Pareto-based model-selection
analysis to translate benchmark results into product decisions.

## STATUS

**V1 published.**

The canonical paid benchmark run
`official-v1-20260911T103838Z` has been executed, aggregated, and published.
Public release artifacts live under `release/v1/`.

The frozen V1 dataset contains **50 production tasks across 5 workload domains**.

The canonical run attempted:

- **500 / 500 candidate evaluation units**
- **990 / 990 cross-family judge evaluation units**
- **1,490 formal evaluation units in total**

`execution_complete = true`.

Under the frozen strict completeness rule, **4 / 10 models are COMPLETE and
rank-eligible**. The remaining six models are INCOMPLETE and are not ranked or
Pareto-eligible.

Canonical API spend: **109.73182552 CNY**.

Human calibration labels are still pending. V1 must not be described as
human-calibrated until real human review has been completed.

## V0.1

V0.1 was an internal historical engineering scaffold:

- 2 models
- 3 domains
- 1 judge
- 10 cases

It is preserved in git history as a development checkpoint.

V0.1 is **not the released benchmark** and its constraints no longer apply.
AIProductBench CN V1 and its frozen V1 specification are authoritative.

## V1 FROZEN SCOPE

- 10 candidate models
- 6 provider integrations
- 50 real-world AI product tasks
- exactly 5 workload domains
- hybrid deterministic + LLM evaluation
- cross-family dual-judge evaluation
- human calibration planning
- quality / cost / latency metrics
- RMB/CNY user-facing cost presentation
- Pareto model-selection analysis
- reproducible snapshot-oriented results

## AUTHORITATIVE DOCUMENTS

| Document | Role |
| --- | --- |
| [docs/PRODUCT_SPEC_V1.md](docs/PRODUCT_SPEC_V1.md) | What V1 is and what is out of scope |
| [docs/METHODOLOGY_V1.md](docs/METHODOLOGY_V1.md) | Frozen evaluation design |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Pipeline, modules, data flow, config schema |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Chronological decision log |
| [docs/HANDOFF.md](docs/HANDOFF.md) | Current operational status |

**Reading order.** Every future agent must read `AGENTS.md` and
`docs/HANDOFF.md` before modifying the repository.

**Precedence.** For product or methodology decisions, the V1 specification
documents above are authoritative.

If implementation and a frozen specification disagree, treat that as a defect
to investigate and resolve rather than silently choosing one.

Changes to frozen V1 scope require an explicit versioned decision recorded in
`docs/DECISIONS.md`.

## DO NOT EXPAND V1 INTO

Unless explicitly approved:

- coding benchmark
- RAG
- vision / multimodal evaluation
- live web search
- real tool execution
- multi-agent benchmark
- hosted SaaS

Also outside V1 scope:

- fine-tuning
- production routing systems
- databases
- authentication
- containers
- cloud infrastructure
- dashboards
- frontend frameworks

Future capabilities belong in a new versioned scope rather than being silently
added to V1.

## PRODUCT PRINCIPLES

Prioritize, in order:

1. working end-to-end execution
2. reproducibility
3. readable benchmark design
4. credible public presentation
5. minimal implementation complexity

Prefer the smallest change that fully satisfies the task.

Do not add abstraction, dependencies, or generality that the active version does
not require.

## MANDATORY HONESTY RULES

- Never fabricate token, cost, latency, score, calibration, or benchmark data.
- Missing provider metrics are recorded as `null`, never estimated into a result.
- Never convert currencies without an explicit, dated FX snapshot with a source.
- Never present an unverified model ID or price as verified.
- Never present synthetic dry-run output as a real benchmark result.
- Never silently include an INCOMPLETE model in an official ranking or Pareto
  frontier.
- Do not claim statistical significance from the V1 ranking; V1 does not run
  repeated sampling or significance testing.
- Do not claim human calibration results until real human labels exist.
- Never describe the benchmark as scientifically comprehensive.
- Preserve the distinction between measured benchmark evidence and product
  interpretation.

## ENGINEERING CONSTRAINTS

- Python is used for benchmark execution.
- Dependencies stay minimal; the current external runtime dependency is
  `requests`.
- Prefer structured JSON for inputs, outputs, and configuration.
- Configuration drives the model pool.
- Benchmark logic must not branch on a specific model name or provider name.
- Candidate execution and judge execution are distinct roles.
- Candidate inference cost and judge evaluation cost must never be mixed.
- Candidate latency and judge latency must never be mixed.
- Incomplete-model handling must remain explicit and auditable.
- Published canonical release artifacts must remain reproducible from their
  recorded configuration and provenance snapshots.
- Credentials come from environment variables only.
- Never read API keys from `~/.codex`, `~/.codex-deepseek`, shell history, or
  any other agent configuration file.
- Never commit credentials.

## GIT SAFETY

- Do not push to a remote unless explicitly instructed.
- Do not create a remote unless explicitly instructed.
- Do not rewrite published history.
- Do not force-push.
- Do not amend published commits unless explicitly instructed.
- Do not delete or merge branches unless explicitly instructed.
- Do not modify global Git configuration or global Git identity.
- Before reporting repository changes complete, inspect `git status` and
  `git diff`.

## VALIDATION

For future code, dataset, methodology, or benchmark-runtime changes, run at
least:

```bash
python3 -m unittest discover -s tests -v
python3 run_benchmark.py --validate-only
python3 run_benchmark.py --dry-run
