# AIProductBench — Handoff

Read this file and `AGENTS.md` first at the start of every working session.

## CURRENT TARGET

**AIProductBench CN V1** — a practical model-selection benchmark for Chinese
LLMs, for AI product teams choosing under real quality, cost, and latency
constraints. RMB/CNY presentation, Pareto-based selection analysis.

## STATUS

**In development. Not released. No live paid benchmark has been authorized.**
Domain 1 (`instruction_constraint_following`, IF-01 … IF-10) is frozen and
externally approved. Domain 2 (`structured_information_analysis`, SA-01 …
SA-10) is frozen and externally approved after the Phase 3B-2.1 patch round.
Domain 3 (`product_reasoning_decision`, PR-01 … PR-10) is authored from
externally authored canonical definitions. It was **reopened** in Phase 3B-3R
after an external audit found the earlier frozen set drifted from APPROVED
`CASE_MATRIX_V1.md` slots; the full domain was replaced with Matrix-compliant
definitions and, after the Phase 3B-3R.1 PR-10 patch, passed both the Matrix
Gate and the Semantic Gate and is **re-frozen / externally approved**.
Domain 4 (`chinese_business_communication`, BC-01 … BC-10) is authored from
externally authored Matrix-compliant definitions; after the Phase 3B-4.1
deterministic-contract repair it passed the Matrix, Semantic, and
Deterministic-contract Gates and is **frozen / externally approved**. Domain 5
(AW) is not authored. There
is no complete V1 production dataset (40 of 50 cases), no verified V1 model ID,
no verified V1 price, and no benchmark
result. Every run artifact produced so far is synthetic dry-run output.

## COMPLETED

- DeepSeek Codex executor environment configured and validated
- V0.1 framework scaffold completed — historical internal scaffold only
  (2 models, 3 domains, 1 judge, 10 cases)
- V1 product direction frozen in documentation
- V1 framework implemented: one shared model registry, deterministic evaluator
  (21 check types), fixed-priority cross-family dual-judge selection, pricing /
  CNY normalization framework, Pareto analytics, standalone leaderboard
- Test suite and network-isolated dry run passing (348 tests)
- Phase 3A case design standard and 50-slot coverage matrix (awaiting external
  review; no production prompt written)
- Case Design Standard approved for Phase 3B authoring (Gate 3A.1 passed)
- 50-slot Case Matrix approved for Phase 3B authoring (Gate 3A.1 passed)
- Phase 3A.1 methodology corrections approved
- Phase 3A.1 semantic/methodology correction: self-containment / `reference_facts`
  rule, no-private-chain-of-thought rule, IF-03 audience adaptation without
  factual drift, IF-06 outcome-based conflict resolution, SA-08 authority
  judgment, BC-07 observable audience roles, AW-04 side-effect-aware retry,
  deterministic-check quality audit (14 Strong / 25 Partial / 11 None),
  quantitative correctness plan, incomplete-run comparative-metric suppression,
  and the base-50 + risk-based human calibration policy
- Phase 3B-1 Domain-1 authoring and first external review (IF-01/04/05/08 PASS;
  IF-02/03/06/07/09/10 PATCH)
- Phase 3B-1.1: the six PATCH cases replaced with externally authored canonical
  definitions, and three generic deterministic operators added
  (`section_max_chars`, `section_bullet_count`, `exact_keys`), raising the
  operator count 18 → 21
- Phase 3B-1.2: second (final) external review returned 8 PASS / IF-03 + IF-06
  PATCH / 0 REJECT; IF-03 and IF-06 patched, and deterministic-check
  declaration validation added for all 21 operators (operator count unchanged)
- Domain 1 production cases IF-01 … IF-10 authored, externally reviewed, and
  **frozen** (external final review PASSED after the Phase 3B-1.2 patches)
- 21 deterministic operators, with centralized deterministic-check declaration
  validation enforced by `run_benchmark.py --validate-only`
- Domain 2 production cases SA-01 … SA-10 integrated from externally authored
  canonical definitions (integration only)
- External Gate 3B-2 result: SA-01/02/03/04/06/07 PASS; SA-05/08/09/10 PATCH;
  0 REJECT
- Phase 3B-2.1: the four PATCH cases replaced with externally authored canonical
  patches (integration only; no new operator)
- Domain 2 production cases SA-01 … SA-10 externally reviewed and **frozen**
  (final external review PASSED after the Phase 3B-2.1 patches)
- Domain 3 production cases PR-01 … PR-10 integrated from externally authored
  canonical definitions (integration only; no new operator, no winner regexes)
- External Gate 3B-3 result: PR-02/03/04/08/09 PASS; PR-01/05/06/07/10 PATCH;
  0 REJECT
- Phase 3B-3.1: the five PATCH cases replaced with externally authored canonical
  full objects (integration only; no new operator, no winner regexes)
- Domain 3 production cases PR-01 … PR-10 externally reviewed and **frozen**
  (final semantic review PASSED after the Phase 3B-3.1 patches)
- Phase 3B-3R: Domain 3 **reopened** for Matrix compliance; all ten PR cases
  replaced with externally authored Matrix-compliant canonical definitions
  (integration only; awaiting semantic + Matrix review). Historical commit
  `e859a6d` left intact.
- External Gate 3B-3R result: PR-01…PR-09 PASS; PR-10 PATCH. Phase 3B-3R.1
  replaced only PR-10 (new-model candidate vs Legacy rollback-baseline
  separation); PR-10 awaits re-review.
- Phase 3B-3R Matrix Gate PASS + Semantic Gate PASS on the repaired PR set;
  Domain 3 (PR-01 … PR-10) **re-frozen / externally approved**
- Matrix-compliance regression coverage for PR (`tests/test_pr_cases.py`):
  slot/title, difficulty, language, and deterministic-plan guards
- Domain 4 production cases BC-01 … BC-10 integrated from externally authored
  Matrix-compliant canonical definitions (integration only; no new operator, no
  proxy checks; BC-03/06/09 remain deterministic-check-free)
- External Phase 3B-4 Gate result: BC-02/03/05/06/07/08/09 PASS; BC-01/04/10
  PATCH. Phase 3B-4.1 replaced only those three (order-independent numeric
  checks; response-wide no-jargon scope); they await re-review.
- Phase 3B-4 final Matrix + Semantic + Deterministic-contract Gate PASS; Domain
  4 (BC-01 … BC-10) **frozen / externally approved**
- Matrix-compliance regression coverage through Domain 4
  (`tests/test_bc_cases.py`)

## CURRENT PHASE

**Phase 3B-5 — Agent Workflow Planning.**

## CURRENT STATE

**Waiting for externally authored canonical AW-01 through AW-10 definitions.**
Domains 1–4 are frozen; Domain 5 (AW) is not authored.

## NEXT

Integrate the externally authored Matrix-compliant AW definitions, then perform
the Matrix + Semantic external Gate Review.

## THEN

If AW is approved, freeze it to complete the 50-case V1 production dataset.

## AFTER THAT

**Phase 4 — Native APIs & Live Benchmark.** Verify literal model IDs against
provider-native documentation, verify active pricing and an FX snapshot, obtain
credentials, run a cost projection, and only then execute a paid run.

## IMPORTANT

- No live paid benchmark has been authorized. Do not run `--confirm`.
- **Do not independently author production cases** for any remaining domain
  (BC/AW). Production case semantic authorship is externally controlled;
  execution agents integrate the externally authored canonical definitions only
  and must not redesign them.
- BC and AW have **not** been authored.
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
| [CASE_DESIGN_STANDARD_V1.md](CASE_DESIGN_STANDARD_V1.md) | Binding rules for authoring production cases |
| [CASE_MATRIX_V1.md](CASE_MATRIX_V1.md) | Planned coverage of all 50 production slots |

## VERSION NOTES

V0.1 is an internal engineering scaffold, preserved in git history as the
`chore: checkpoint v0.1 benchmark scaffold` commit. It is **not** intended for
public release, and its documentation is superseded by the V1 documents above.
Its pricing review is retained only as `historical_pricing_archive` metadata.

## REPOSITORY STATE

- Branch: `main`
- Remote: none configured
- Latest committed state: the Chinese-business-communication freeze checkpoint
  (`feat: freeze chinese-business-communication benchmark cases`). It holds the
  V1 framework, the Phase 3A/3A.1 design documents, the frozen production cases
  IF-01 … IF-10, SA-01 … SA-10, PR-01 … PR-10, and BC-01 … BC-10, the 21
  deterministic operators (`section_max_chars`, `section_bullet_count`,
  `exact_keys` added in Phase 3B-1.1), deterministic-check declaration
  validation, and Matrix-compliance regression coverage through Domain 4.
- Historical commit `e859a6d` (the earlier, superseded PR freeze) remains intact
  and auditable; it was not reset, reverted, amended, squashed, or rewritten.

## STILL OPEN (requires human decision)

| # | Open item |
| --- | --- |
| 1 | Literal model IDs for the 10 candidates and 3 judges must be verified against provider-native documentation before any paid run |
| 2 | All active V1 pricing is unresolved; every model is unpriced until each literal model ID's price is verified |
| 3 | Provider credentials for Moonshot, MiniMax, Zhipu, and Volcano Ark are not configured |
| 4 | No FX snapshot (USD/CNY) is configured, so USD-priced models would have no CNY-normalized cost |
| 5 | Human calibration protocol and reviewer assignment are undefined |
| 6 | Domains 1–4 are frozen; Domain 5 (AW) remains to be authored from externally supplied canonical definitions (dataset is 40/50 cases) |
| 7 | AW requires externally authored canonical definitions before it can be integrated; DeepSeek must not author production cases |
