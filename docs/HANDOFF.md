# AIProductBench — Handoff

Read this file first at the start of every working session.

## CURRENT TARGET

**AIProductBench CN V1** — a practical model-selection benchmark for Chinese
LLMs, for AI product teams choosing under real quality, cost, and latency
constraints. RMB-native presentation, Pareto-based selection analysis.

## STATUS

**In development. Not released. No live paid benchmark has been authorized.**
Every artifact produced so far is synthetic dry-run output.

## COMPLETED

- DeepSeek Codex executor environment configured and validated
- V0.1 framework scaffold completed (2 models, 3 domains, 1 judge, 10 cases)
- Dry-run pipeline validated end to end
- Pricing / accounting prototype implemented (native currency + separation of
  candidate inference cost from judge evaluation cost)
- V1 product direction frozen in documentation

## CURRENT PHASE

**Phase 2 — Framework Upgrade.** Documentation freeze plus the framework
upgrade from the V0.1 scaffold to the V1 architecture.

## NEXT

**Phase 3 — Dataset & Evaluation QA.** Build the 50 production cases (10 per
domain, difficulty 2/5/3 per domain, approximately 40 Chinese-first), write the
case-level `evaluation_criteria` and `deterministic_checks`, and QA the dataset
for realism and non-overlap.

## THEN

**Phase 4 — Native APIs & Live Benchmark.** Verify literal model IDs against
provider-native documentation, verify pricing and FX snapshots, obtain
credentials, run a cost projection, and only then execute a paid run.

## IMPORTANT

- No live paid benchmark has been authorized. Do not run `--confirm`.
- Never read API keys from `~/.codex`, `~/.codex-deepseek`, shell history, or
  other agent configuration files. Credentials come from environment variables
  only, and are never committed.
- Never fabricate token, cost, latency, or calibration data.
- Never convert currencies without an explicit dated FX snapshot.
- Do not commit Phase 2 implementation code without review.

## KEY DOCUMENTS

| Document | Contents |
| --- | --- |
| [PRODUCT_SPEC_V1.md](PRODUCT_SPEC_V1.md) | What AIProductBench CN V1 is, frozen scope, out-of-scope list |
| [METHODOLOGY_V1.md](METHODOLOGY_V1.md) | Frozen evaluation design: dataset, judges, metrics, Pareto |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Pipeline, module responsibilities, data flow, config schema |
| [DECISIONS.md](DECISIONS.md) | Chronological decision log with rationale |

## VERSION NOTES

V0.1 is an internal engineering scaffold, preserved in git history as the
`chore: checkpoint v0.1 benchmark scaffold` commit. It is **not** intended for
public release and its documentation is superseded by the V1 documents above.

## REPOSITORY STATE

- Branch: `main`
- Remote: none configured
- Latest committed state: V0.1 scaffold checkpoint plus the V1 documentation freeze
- The V1 framework upgrade is implemented but intentionally left uncommitted
  pending external review

## STILL OPEN (requires human decision)

| # | Open item |
| --- | --- |
| 1 | Literal model IDs for all V1 candidates and judges must be verified against provider-native documentation before any paid run |
| 2 | Provider credentials for Moonshot, MiniMax, Zhipu, and Volcano Ark are not configured |
| 3 | The pricing snapshot covers only the Qwen and DeepSeek tiers carried over from the V0.1 review; all other providers are unpriced |
| 4 | No FX snapshot (USD/CNY) has been configured, so USD-priced models have no CNY-normalized cost |
| 5 | Human calibration protocol and reviewer assignment are undefined |
| 6 | The 50-case production dataset does not exist yet (Phase 3) |
