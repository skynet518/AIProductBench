# AIProductBench — Handoff

Read this file and `AGENTS.md` first at the start of every working session.

## CURRENT TARGET

**AIProductBench CN V1** — a practical model-selection benchmark for Chinese
LLMs, for AI product teams choosing under real quality, cost, and latency
constraints. RMB/CNY presentation, Pareto-based selection analysis.

## STATUS

**In development. Not released. No live paid benchmark has been authorized.**
**The 50-case V1 production dataset is FROZEN / EXTERNALLY APPROVED.** All five
domains (`instruction_constraint_following`, `structured_information_analysis`,
`product_reasoning_decision`, `chinese_business_communication`,
`agent_workflow_planning`), 10 cases each, passed the Matrix, Semantic,
Deterministic-contract, and global coverage/invariant Gates
(50 PASS / 0 PATCH / 0 REJECT). `production_status` is `"complete"` and the
semantic freeze manifest is `docs/DATASET_FREEZE_V1.md`. There is still no
verified V1 model ID, no verified V1 price, and no benchmark result; every run
artifact produced so far is synthetic dry-run output.

## COMPLETED

- DeepSeek Codex executor environment configured and validated
- V0.1 framework scaffold completed — historical internal scaffold only
  (2 models, 3 domains, 1 judge, 10 cases)
- V1 product direction frozen in documentation
- V1 framework implemented: one shared model registry, deterministic evaluator
  (21 check types), fixed-priority cross-family dual-judge selection, pricing /
  CNY normalization framework, Pareto analytics, standalone leaderboard
- Test suite and network-isolated dry run passing (400 tests)
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
- Domain 5 production cases AW-01 … AW-10 integrated from externally authored
  Matrix-compliant canonical definitions (integration only; planning-only; no
  new operator, no proxy checks; AW-02/05/07/09/10 remain
  deterministic-check-free)
- Phase 3B-5R: IF-06 repaired to the approved Matrix None contract
  (`deterministic_checks == []`); Domain 1 reopened for IF-06 Matrix-compliance
  re-review. Realized deterministic distribution restored to 14 / 25 / 11.
- External IF-06 Matrix re-review PASSED (Domain 1 re-frozen). AW Matrix Gate
  PASS; AW Semantic + Deterministic-contract Gate 8 PASS / 2 PATCH (AW-03,
  AW-04). Phase 3B-5.1 revised AW-03/AW-04 (unique-label execution-plan
  contract; digits-only retry-budget cell).
- **Final V1 dataset freeze: 50 / 50 production cases, all five domains FROZEN /
  EXTERNALLY APPROVED (50 PASS / 0 PATCH / 0 REJECT).** Matrix Gate, Semantic
  Gate, Deterministic-contract Gate, and global coverage/invariant Gate all
  PASS.
- Semantic freeze manifest created (`docs/DATASET_FREEZE_V1.md`); aggregate
  SHA-256 `6b450383e528a5a0a6b813112f96182a3625c04c948839fc551c8ded63da513c`.
- Deterministic / judge-boundary audit and global Matrix coverage audit
  complete (14 Strong / 25 Partial / 11 None; 40 zh / 6 en / 4 mixed;
  10 easy / 25 medium / 15 hard).
- Phase 4A offline readiness audit (`docs/PHASE4A_READINESS_AUDIT.md`): model
  registry, provider adapter, pricing/FX architecture, judge mapping,
  incomplete-model handling, and run-manifest shape reviewed; no network calls.
- Model-registry contract extended (backward-compatible) with `enabled`,
  `thinking_config`, `model_id_verified_as_of`, and pricing `reasoning` /
  `cached_input`; FX snapshots gained a `snapshot_id`; snapshot schema
  validators and Phase 4A readiness tests added.
- Phase 4B/C: ten logical slots locked to verified literal model IDs; official
  pricing snapshot (`v1-pricing-2026-09-11`) and fixed ECB FX snapshot
  (`ecb-2026-09-10-usd-cny`) created; provider-default thinking/request configs
  implemented and the global temperature=0 override removed; run-manifest gaps
  closed; registry snapshot (`v1-registry-2026-09-11`) added.

## CURRENT PHASE

**Phase 4B/C — Official Registry + Execution Readiness: COMPLETE.** Case
authoring (Phases 3A/3B) is COMPLETE, the 50 production cases are frozen, and
the official model registry, pricing, FX, and execution configuration are locked
offline.

## CURRENT STATE

**Execution configuration frozen for controlled live smoke.** All five domains
are FROZEN / EXTERNALLY APPROVED and the 50-case migration manifest is the
immutable case baseline (`docs/DATASET_FREEZE_V1.md`, aggregate SHA-256
`6b450383e528a5a0a6b813112f96182a3625c04c948839fc551c8ded63da513c`). The ten
logical slots carry verified literal model IDs (`as_of` 2026-09-11), an immutable
pricing snapshot, a fixed ECB FX snapshot, provider-default thinking configs, and
a complete run manifest. `--validate-only` reports "model IDs verified
(credentials still required)".

## NEXT

**Controlled live provider/model/judge smoke test** once provider credentials are
configured and an explicit paid-run authorization is given. **No full benchmark
run yet.** Confirm source URLs and provider thinking/usage field names during the
smoke test.

## THEN

Run the calibrated benchmark once credentials, verified model IDs, verified
pricing, and an FX snapshot exist — and only after an explicit paid-run
authorization.

## AFTER THAT

**Phase 4 — Native APIs & Live Benchmark.** Verify literal model IDs against
provider-native documentation, verify active pricing and an FX snapshot, obtain
credentials, run a cost projection, and only then execute a paid run.

## IMPORTANT

- No live paid benchmark has been authorized. Do not run `--confirm`.
- **The frozen production cases must not be modified by provider/runtime work.**
  Production case semantic authorship is externally controlled; any future case
  change requires an explicit versioned reopening plus Matrix, semantic, and
  deterministic/judge-boundary review and a new freeze hash.
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
- Latest committed state: the final V1 dataset freeze
  (`feat: freeze AIProductBench CN V1 production dataset`). It holds the V1
  framework, the Phase 3A/3A.1 design documents, all 50 frozen production cases
  (IF/SA/PR/BC/AW, 10 each), the 21 deterministic operators, deterministic-check
  declaration validation, the semantic freeze manifest
  (`docs/DATASET_FREEZE_V1.md`), and the dataset-freeze regression tests.
- Historical commit `e859a6d` (the earlier, superseded PR freeze) remains intact
  and auditable; it was not reset, reverted, amended, squashed, or rewritten.
- The Phase 4A/4B/C work (registry contract + official model IDs, pricing/FX
  snapshots, provider thinking/request configs, run-manifest gaps, audit doc,
  and readiness tests) is **uncommitted** pending review.

## STILL OPEN (requires human decision)

| # | Open item |
| --- | --- |
| 1 | Provider credentials for Moonshot, MiniMax, Zhipu, and Volcano Ark (and Qwen/DeepSeek) are not configured |
| 2 | No paid-run authorization has been given; the next step is a controlled live smoke test, not the full run |
| 3 | Official documentation URLs for model IDs/prices, and provider thinking/usage field names, still need confirmation against provider-native docs |
| 4 | Human calibration protocol and reviewer assignment are undefined |
| 5 | The full candidate+judge benchmark run is not authorized until the smoke test passes |
| 6 | Any future semantic case modification requires an explicit versioned reopening plus Matrix, semantic, and deterministic/judge-boundary review and a new freeze hash |
