# AIProductBench — Handoff

Read this file and `AGENTS.md` first at the start of every working session.

## CURRENT TARGET

**AIProductBench CN V1** — a practical model-selection benchmark for Chinese
LLMs, for AI product teams choosing under real quality, cost, and latency
constraints. RMB/CNY presentation, Pareto-based selection analysis.

## STATUS

**AIProductBench CN V1: RELEASE READY.**
**The 50-case V1 production dataset is FROZEN / EXTERNALLY APPROVED.** All five
domains (`instruction_constraint_following`, `structured_information_analysis`,
`product_reasoning_decision`, `chinese_business_communication`,
`agent_workflow_planning`), 10 cases each, passed the Matrix, Semantic,
Deterministic-contract, and global coverage/invariant Gates
(50 PASS / 0 PATCH / 0 REJECT). `production_status` is `"complete"` and the
semantic freeze manifest is `docs/DATASET_FREEZE_V1.md`.

**The canonical official full benchmark has been executed, aggregated, and
published.** Canonical run `official-v1-20260911T103838Z`: 500 / 500 candidate
units attempted, 990 / 990 judge units attempted, `execution_complete = true`.
Only 4 / 10 models are COMPLETE and rank-eligible under the frozen strict
completeness rule (`all_models_complete = false`); the other six are INCOMPLETE
and are never ranked or Pareto-eligible. Canonical API spend is 109.73182552
CNY. Public release artifacts are committed under `release/v1/`.

**Release state: local release prepared; remote push pending.** The target is
the existing GitHub repository `skynet518/AIProductBench`.

> Historical note (superseded): before the canonical run, V1 was in development
> and unreleased, the full 50-case paid benchmark had not been executed, and all
> full-run artifacts were synthetic dry-run output. That is no longer the state.
> The canonical run above is a real paid execution with real results, and the
> Phase 4D / 4D.1 smoke and probe artifacts remain historically accurate as
> pre-run runtime validation only.

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
- Phase 4A/4B/C/4D: provider adapter fatal/billing error policy hardened (402
  never retried; billing-marker bodies treated as fatal), `run_smoke.py` and
  `run_probe.py` harnesses added with a cross-invocation CNY spend ledger, and
  regression coverage added for provider error policy and the smoke harness.
- Phase 4D controlled live smoke (first attempt) and Phase 4D.1 blocker
  clearance: the first smoke exposed account/auth and billing blockers plus a
  DeepSeek runtime output-budget issue; each blocker was then cleared with
  targeted probes. All of that failure history is preserved in the Phase 4D /
  4D.1 results artifacts and in D-052.
- Phase 4D final live runtime checkpoint: Qwen executor auth PASS; Qwen
  candidates (`qwen3.8-max`, `qwen3.8-flash`) PASS on IF-07 with literal model
  IDs verified by provider echo, `enable_thinking=true` accepted, usage /
  reasoning / cached-token / latency / native-cost / CNY-cost captured, and the
  deterministic evaluator executing; judge route **Qwen + DeepSeek PASS** (2/2
  valid verdicts on the stored MiniMax-M3 China IF-07 response); judge route
  **DeepSeek + GLM PASS** (2/2 valid verdicts on the Qwen IF-07 response). No
  candidate response was regenerated for either judge route.

## CURRENT PHASE

**Phase 5 — Analysis & Presentation: COMPLETE. Release preparation: DONE.**
Case authoring (Phases 3A/3B), live runtime validation (Phase 4D), the canonical
official full run, aggregation, Pareto analysis, RMB/CNY presentation, and the
human calibration sample are all complete. Case authoring is COMPLETE, the 50
production cases are frozen, the official model registry, pricing, FX, and
execution configuration are locked, and the canonical result set is published
under `release/v1/`.

> This supersedes the earlier statement that a full 50-case paid benchmark run
> had not been executed.

## CURRENT STATE

**Canonical official full run COMPLETE under the final D-054 runtime envelope.**
The first official attempt was aborted and retained as diagnostic evidence
(`results/official_run_v1_20260911T075351Z`, status
**ABORTED_RUNTIME_ENVELOPE**: 150 candidate attempts, 134 completed responses,
0 judge calls, 7.20081125 CNY). It proved the previous 2048 / 8192 generation
envelope caused systemic empty-final-answer truncation for reasoning models.

All five domains
are FROZEN / EXTERNALLY APPROVED and the 50-case manifest is the immutable case
baseline (`docs/DATASET_FREEZE_V1.md`, aggregate SHA-256
`6b450383e528a5a0a6b813112f96182a3625c04c948839fc551c8ded63da513c`). The ten
logical slots carry verified literal model IDs (`as_of` 2026-09-11), an immutable
pricing snapshot, a fixed ECB FX snapshot, provider thinking/request configs, and
a complete run manifest.

**D-054 final execution envelope (applied).** Candidate generation ceiling 32768
tokens for all ten slots; a separate judge generation ceiling of 16384 tokens;
client read timeout 600 s; Moonshot/Kimi max in-flight 1; global concurrency 6
and default per-provider 2 unchanged. Registry revision
`v1-registry-2026-09-11.3`
(`259b02adb05f73ab2d800c8f41d9b2608b8eddb17ae97e9d3f31ecff79409eab`); pricing
snapshot unchanged (`v1-pricing-2026-09-11.1`). **32768 is the final V1 ceiling:
no adaptive per-case budget and no further automatic escalation.**

**D-054 targeted validation PASSED the envelope gate.** All sixteen previously
failed candidate units were attempted under the final homogeneous configuration
(two bounded passes, no completed unit re-run): **13 PASS, 2
REAL_MODEL_FAILURE, 1 TRANSIENT_RUNTIME_FAILURE**, cumulative spend
5.15086572 CNY. The two real model failures are isolated single-unit IF-03
truncations (`minimax_flagship`, `glm_flagship`) at the full 32768 envelope; the
remaining `qwen_flagship` IF-03 unit times out at the fixed 600 s client
allowance across repeated attempts and is flagged for the result Gate. D-053
remains recorded as an attempted revision whose live validation showed 16384 was
still insufficient.

Verified live (Phase 4D / 4D.1 targeted probes, not the 50-case run):

- Qwen candidate: `qwen3.8-max` and `qwen3.8-flash` PASS (IF-07)
- DeepSeek candidate: PASS (AW-04); runtime output-budget issue **resolved** with
  a bounded 8192-token output budget
- Kimi candidate: PASS (IF-07, SA-03, AW-04)
- MiniMax-M3 China candidate: PASS (IF-07); the same `MiniMax-M3` model migrated
  from the international API route to the official China domestic
  pay-as-you-go route
- GLM candidate: PASS (IF-07)
- Doubao candidate: PASS (IF-07, SA-03, AW-04)
- Judge route Qwen + DeepSeek: PASS (2/2 valid verdicts)
- Judge route DeepSeek + GLM: PASS (2/2 valid verdicts)

Canonical-run snapshots: registry `v1-registry-2026-09-11.3`
(`259b02adb05f73ab2d800c8f41d9b2608b8eddb17ae97e9d3f31ecff79409eab`), pricing
`v1-pricing-2026-09-11.1`
(`9f7af42243e5e0b78b1776934de5483f0e3e650765a19dd929e78af10aa15c42`), and FX
`ecb-2026-09-10-usd-cny` (USD/CNY 6.706267217630854). The canonical benchmark
result exists and is published under `release/v1/`; the earlier statement that
no full benchmark result existed and that all full-run artifacts were synthetic
is superseded.

## NEXT

**Publish the existing repository.** The local release is prepared and
committed; the only remaining step is a normal (non-force) push of `main` to the
existing GitHub repository `skynet518/AIProductBench`. Remaining offline
hygiene: official source URLs for model IDs and prices still carry
`requires_official_verification`; the literal model IDs were confirmed live
(provider echo + accepted request).

## THEN

**Human calibration review.** The 60-item calibration sample is prepared and
human labels remain pending; V1 must not be described as human-calibrated until
real labels exist. The full 50-case dataset must not be modified by provider or
runtime work.

## AFTER THAT

Post-release follow-ups (outside the V1 release scope): human calibration
review, official source URLs for model IDs/prices, and any V1.1 work recorded in
`docs/PRODUCT_SPEC_V1.md` / `docs/DECISIONS.md`.

## IMPORTANT

- The canonical full benchmark (`official-v1-20260911T103838Z`) has been
  executed and is published. Do not run `run_benchmark.py --confirm` again
  without a new explicit paid-run authorization.
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
- V1 benchmark scores and the official leaderboard now exist and are published
  in `release/v1/`; never claim human calibration results, which do not exist
  (sample prepared, human review pending).

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
- Remote: `origin` — https://github.com/skynet518/AIProductBench.git (existing
  repository, not created by this project)
- Latest committed state: the V1 release commit
  (`docs: publish AIProductBench CN V1 results`), which rewrote the public
  `README.md` and added the canonical public release artifacts under
  `release/v1/` (leaderboard, Pareto, cost, latency, judge disagreement, sample
  results, run manifest), plus the merge commit that joins the existing GitHub
  `Initial commit` history into local `main`.
- Earlier committed state: the final V1 dataset freeze (`feat: freeze
  AIProductBench CN V1 production dataset`) holds the V1 framework, the Phase
  3A/3A.1 design documents, all 50 frozen production cases (IF/SA/PR/BC/AW, 10
  each), the 21 deterministic operators, deterministic-check declaration
  validation, the semantic freeze manifest (`docs/DATASET_FREEZE_V1.md`), and
  the dataset-freeze regression tests.
- Historical commit `e859a6d` (the earlier, superseded PR freeze) remains intact
  and auditable; it was not reset, reverted, amended, squashed, or rewritten.
- The Phase 4A/4B/C/4D runtime work (registry contract + official model IDs,
  pricing/FX snapshots, MiniMax China migration and domestic pricing, DeepSeek
  bounded output budget, provider error policy, smoke/probe harnesses,
  regression tests, and this handoff/decision update) was committed as
  `fix: validate V1 live benchmark runtime`.
- Live probe artifacts under `results/` (including the preserved Phase 4D /
  4D.1 failures) are gitignored and are **not** committed.

## STILL OPEN (requires human decision)

| # | Open item |
| --- | --- |
| 1 | Provider credentials for Qwen, DeepSeek, Kimi, MiniMax, GLM, and Doubao are now configured and were exercised live; account balances are external to this repo and can change without notice |
| 2 | The **canonical full 50-case paid run** has been executed (`official-v1-20260911T103838Z`); a further paid run would require a new explicit authorization plus a cost projection |
| 3 | Official documentation URLs for model IDs/prices still carry `requires_official_verification`; literal model IDs were instead confirmed live (provider echo + accepted request). Provider thinking/usage field names were confirmed live during Phase 4D |
| 4 | Human calibration sample (60 items) is prepared; reviewer assignment and human labels are still pending, so V1 is not human-calibrated |
| 5 | Local release is prepared and committed; remote push of `main` to the existing GitHub repository is pending |
| 6 | Any future semantic case modification requires an explicit versioned reopening plus Matrix, semantic, and deterministic/judge-boundary review and a new freeze hash |
