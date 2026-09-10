# AIProductBench CN — Project Instructions

## CURRENT TARGET

**AIProductBench CN V1** — a practical model-selection benchmark for Chinese
LLMs, for AI product teams choosing models under real quality, cost, and latency
constraints. RMB/CNY user-facing presentation, Pareto-based selection analysis.

## STATUS

**In development.** Not released. **No live paid benchmark has been authorized.**
Every artifact produced so far is synthetic dry-run output.

## V0.1

V0.1 was an internal historical engineering scaffold: 2 models, 3 domains, 1
judge, 10 cases. It is preserved in git history as a checkpoint. It is **not**
the product, is not for public release, and its constraints no longer apply.

## V1 FROZEN SCOPE

- approximately 10 candidate models
- approximately 6 Chinese model families/providers
- 50 real-world AI product tasks
- exactly 5 capability domains
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

**Reading order.** Every future agent must read `AGENTS.md` and `docs/HANDOFF.md`
first, before touching the repository.

**Precedence.** For product or methodology decisions, the V1 specification
documents above are authoritative. If code and a frozen specification disagree,
that is a bug in one of them — stop and resolve it rather than picking one.
Changes to frozen scope require an explicit decision appended to
`docs/DECISIONS.md`.

## DO NOT EXPAND V1 INTO

Unless explicitly approved:

- coding benchmark
- RAG
- vision / multimodal
- live search
- real tool execution
- multi-agent benchmark
- hosted SaaS

Also out of scope: fine-tuning, production routing systems, databases,
authentication, containers, cloud infrastructure, dashboards, and frontend
frameworks.

## PRODUCT PRINCIPLES

Prioritize, in order:

1. working end-to-end execution
2. reproducibility
3. readable benchmark design
4. credible public presentation
5. minimal implementation complexity

Prefer the smallest change that fully satisfies the task. Do not add
abstraction, dependencies, or generality that V1 does not need.

## MANDATORY HONESTY RULES

- Never fabricate token, cost, latency, score, or calibration data.
- Missing provider metrics are recorded as `null`, never estimated into a result.
- Never convert currencies without an explicit, dated FX snapshot with a source.
- Never present an unverified model ID or price as verified.
- Never present synthetic dry-run output as a real result.
- Never claim final model IDs, final pricing, benchmark scores, human calibration
  results, or final leaderboard results while they do not exist.
- Never describe the benchmark as scientifically comprehensive.

## ENGINEERING CONSTRAINTS

- Python for benchmark execution; dependencies stay minimal (`requests` only).
- Prefer structured JSON for inputs, outputs, and configuration.
- Configuration drives the model pool. No benchmark logic may branch on a
  specific model name or provider name.
- Candidate execution and judge execution are distinct roles. Candidate
  inference cost and judge evaluation cost are never mixed, and candidate
  latency and judge latency are never mixed.
- Credentials come from environment variables only. Never read API keys from
  `~/.codex`, `~/.codex-deepseek`, shell history, or any other agent
  configuration file. Never commit credentials.

## GIT SAFETY

- Do not push to a remote unless explicitly instructed.
- Do not create a remote unless explicitly instructed.
- Do not rewrite history, merge branches, or delete branches.
- Do not amend published commits unless explicitly instructed.
- Do not modify global Git configuration or global Git identity.
- Before completion, inspect `git status` and `git diff`.

## VALIDATION

Before reporting completion, run at least:

```
python3 -m unittest discover -s tests -v
python3 run_benchmark.py --validate-only
python3 run_benchmark.py --dry-run
```

`--validate-only`, `--estimate`, and `--dry-run` must make zero network calls.
A real paid run requires `--confirm` and is refused while any model ID or any
active pricing entry is unresolved.

## SCOPE CONTROL

If something is useful but unnecessary for V1, do not implement it. Record it as
a future improvement in `docs/PRODUCT_SPEC_V1.md` or `docs/DECISIONS.md` instead.
