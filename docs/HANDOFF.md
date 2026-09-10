# AIProductBench — Handoff

Read this file and `AGENTS.md` first at the start of every working session.

## CURRENT TARGET

**AIProductBench CN V1** — a practical model-selection benchmark for Chinese
LLMs, for AI product teams choosing under real quality, cost, and latency
constraints. RMB/CNY presentation, Pareto-based selection analysis.

## STATUS

**In development. Not released. No live paid benchmark has been authorized.**
Every artifact produced so far is synthetic dry-run output. There is no
production dataset, no verified V1 model ID, no verified V1 price, and no
benchmark result.

## COMPLETED

- DeepSeek Codex executor environment configured and validated
- V0.1 framework scaffold completed — historical internal scaffold only
  (2 models, 3 domains, 1 judge, 10 cases)
- V1 product direction frozen in documentation
- V1 framework implemented: one shared model registry, deterministic evaluator
  (18 check types), fixed-priority cross-family dual-judge selection, pricing /
  CNY normalization framework, Pareto analytics, standalone leaderboard
- Test suite and network-isolated dry run passing (144 tests)

## CURRENT PHASE

**Phase 2.1 — Consistency patch.** Registry consolidation, fixed-priority judge
selection, V1 pricing reset, documentation consistency, and the framework
checkpoint.

## NEXT

**Phase 3 — Dataset & Evaluation QA.** Build the 50 production cases (10 per
domain, difficulty 2/5/3 per domain, approximately 40 Chinese-first), write the
case-level `evaluation_criteria` and `deterministic_checks`, and QA the dataset
for realism and non-overlap.

## THEN

**Phase 4 — Native APIs & Live Benchmark.** Verify literal model IDs against
provider-native documentation, verify active pricing and an FX snapshot, obtain
credentials, run a cost projection, and only then execute a paid run.

## IMPORTANT

- No live paid benchmark has been authorized. Do not run `--confirm`.
- Never read API keys from `~/.codex`, `~/.codex-deepseek`, shell history, or
  other agent configuration files. Credentials come from environment variables
  only, and are never committed.
- Never fabricate token, cost, latency, score, or calibration data.
- Never convert currencies without an explicit dated FX snapshot.
- Never reuse retired V0.1-era pricing for V1 cost reporting.
- Do not claim final model IDs, final pricing, benchmark scores, calibration
  results, or final leaderboard results.

## KEY DOCUMENTS

| Document | Contents |
| --- | --- |
| [../AGENTS.md](../AGENTS.md) | Project instructions and scope guardrails |
| [PRODUCT_SPEC_V1.md](PRODUCT_SPEC_V1.md) | What AIProductBench CN V1 is, frozen scope, out-of-scope list |
| [METHODOLOGY_V1.md](METHODOLOGY_V1.md) | Frozen evaluation design: dataset, judges, metrics, Pareto |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Pipeline, modules, shared registry, data flow |
| [DECISIONS.md](DECISIONS.md) | Chronological decision log with rationale |

## VERSION NOTES

V0.1 is an internal engineering scaffold, preserved in git history as the
`chore: checkpoint v0.1 benchmark scaffold` commit. It is **not** intended for
public release, and its documentation is superseded by the V1 documents above.
Its pricing review is retained only as `historical_pricing_archive` metadata.

## REPOSITORY STATE

- Branch: `main`
- Remote: none configured
- Latest committed state: V0.1 scaffold checkpoint plus the V1 documentation freeze
- The V1 framework and this Phase 2.1 consistency patch are held in one commit
  pending external review

## STILL OPEN (requires human decision)

| # | Open item |
| --- | --- |
| 1 | Literal model IDs for the 10 candidates and 3 judges must be verified against provider-native documentation before any paid run |
| 2 | All active V1 pricing is unresolved; every model is unpriced until each literal model ID's price is verified |
| 3 | Provider credentials for Moonshot, MiniMax, Zhipu, and Volcano Ark are not configured |
| 4 | No FX snapshot (USD/CNY) is configured, so USD-priced models would have no CNY-normalized cost |
| 5 | Human calibration protocol and reviewer assignment are undefined |
| 6 | The 50-case production dataset does not exist yet (Phase 3) |
