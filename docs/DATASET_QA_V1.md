# AIProductBench CN V1 — Dataset QA Ledger

**Status: all five domains (`instruction_constraint_following`,
`structured_information_analysis`, `product_reasoning_decision`,
`chinese_business_communication`, `agent_workflow_planning`) are FROZEN /
EXTERNALLY APPROVED. The 50-case V1 production dataset is approved for final
freeze; `production_status` is `"complete"` and the freeze manifest
(`docs/DATASET_FREEZE_V1.md`) is the immutable case baseline. No live paid
benchmark is authorized.**

This is the persistent QA ledger for production benchmark case authoring. It
tracks each of the five frozen domains through the authoring lifecycle. It is
append-only in spirit: a status is moved forward with evidence, never rewritten
to imply a review that did not happen.

Authoring rules: `CASE_DESIGN_STANDARD_V1.md` (approved for Phase 3B).
Planned coverage: `CASE_MATRIX_V1.md` (approved for Phase 3B).
Production dataset file: `data/cases_v1.json`.

---

## Lifecycle

| State | Meaning |
| --- | --- |
| `not started` | No case authored for this domain |
| `authoring in progress` | Cases are being written; domain not yet self-reviewed |
| `authored` | All planned slots for the domain are written |
| `self-reviewed` | Domain-level audit in Part H completed and recorded below |
| `external-review-pending` | Submitted for external review; **not** approved |
| `externally-approved` | External reviewer approved every case in the domain |
| `frozen` | Approved cases committed and locked as the production dataset for that domain |

**No external approval may be recorded without an actual review.** A domain may
not be marked `externally-approved` or `frozen` by the authoring agent.

## Domain status summary

| # | Domain | Prefix | Cases | Domain status | Last updated |
| --- | --- | --- | --- | --- | --- |
| 1 | `instruction_constraint_following` | IF | 10 | FROZEN / EXTERNALLY APPROVED | 2026-09-11 |
| 2 | `structured_information_analysis` | SA | 10 | FROZEN / EXTERNALLY APPROVED | 2026-09-11 |
| 3 | `product_reasoning_decision` | PR | 10 | FROZEN / EXTERNALLY APPROVED | 2026-09-11 |
| 4 | `chinese_business_communication` | BC | 10 | FROZEN / EXTERNALLY APPROVED | 2026-09-11 |
| 5 | `agent_workflow_planning` | AW | 10 | FROZEN / EXTERNALLY APPROVED | 2026-09-11 |

---

## Domain 1 — `instruction_constraint_following`

| Field | Value |
| --- | --- |
| Domain status | FROZEN / EXTERNALLY APPROVED |
| Case IDs | IF-01 … IF-10 |
| Authoring date | 2026-09-11 |
| Authoring agent | Codex (Phase 3B-1; six cases revised in Phase 3B-1.1; IF-03/IF-06 patched in Phase 3B-1.2) |
| Dataset file | `data/cases_v1.json` |
| Validation result | PASS — `python3 run_benchmark.py --validate-only --production-cases` exits 0; schema errors 0; warnings flag the partial dataset (10/50 cases, 4 domains not yet authored). All deterministic-check declarations pass declaration validation. |
| External review status | Final semantic review PASSED on all 10 cases. Domain 1 was reopened in Phase 3B-5R solely to repair IF-06's deterministic plan and has now **re-passed** Matrix-compliance review (IF-06 PASS — MATRIX COMPLIANT). |
| Final approval status | **APPROVED — Domain 1 frozen (10/10 cases PASS)** |

### Phase 3B-5R — IF-06 Matrix Compliance Repair (2026-09-11)

The Phase 3B-5 global 50-case Matrix audit exposed a **historical
deterministic-plan drift** in IF-06. Historical facts:

- IF-06 had previously been semantically approved and frozen; its **prompt
  semantics were not the problem**.
- Its deterministic plan incorrectly remained **Partial** after integration: it
  carried four structural checks (`required_phrases`, `ordering`,
  `section_max_chars`, `required_regex`).
- The APPROVED `CASE_MATRIX_V1.md` (and its Phase 3A.1 deterministic-quality
  audit, which changed IF-06 Partial → None) requires **None** for IF-06,
  because correct conflict resolution must be judged from which instruction
  wins, whether the output follows the winner, and whether the stated
  precedence basis is correct.
- Domain 1 was reopened **only** for this deterministic-plan repair. IF-06 was
  restored to the approved judge-only contract (`deterministic_checks == []`);
  all other IF cases were untouched. `CASE_MATRIX_V1.md` was **not** edited.

Current status:

| ID | Status |
| --- | --- |
| IF-01 | PASS |
| IF-02 | PASS |
| IF-03 | PASS |
| IF-04 | PASS |
| IF-05 | PASS |
| IF-06 | PASS — MATRIX COMPLIANT (approved None contract; `deterministic_checks == []`) |
| IF-07 | PASS |
| IF-08 | PASS |
| IF-09 | PASS |
| IF-10 | PASS |

The IF-06 Matrix-compliance re-review **PASSED**; Domain 1 is
**FROZEN / EXTERNALLY APPROVED** again. The Phase 3B-5R repair provenance above
is preserved.

### First external review result (2026-09-11)

| ID | First external result | Action | Current status |
| --- | --- | --- | --- |
| IF-01 | PASS | none | PASS — unchanged |
| IF-02 | PATCH | replaced with canonical definition | REVISED — EXTERNAL RE-REVIEW PENDING |
| IF-03 | PATCH | replaced with canonical definition | REVISED — EXTERNAL RE-REVIEW PENDING |
| IF-04 | PASS | none | PASS — unchanged |
| IF-05 | PASS | none | PASS — unchanged |
| IF-06 | PATCH | replaced with canonical definition | REVISED — EXTERNAL RE-REVIEW PENDING |
| IF-07 | PATCH | replaced with canonical definition | REVISED — EXTERNAL RE-REVIEW PENDING |
| IF-08 | PASS | none | PASS — unchanged |
| IF-09 | PATCH | replaced with canonical definition | REVISED — EXTERNAL RE-REVIEW PENDING |
| IF-10 | PATCH | replaced with canonical definition | REVISED — EXTERNAL RE-REVIEW PENDING |

The six PATCH cases were replaced with externally authored canonical JSON and
were **not** rewritten by the executing agent. The four PASS cases (IF-01,
IF-04, IF-05, IF-08) are unchanged.

### Final external review result (2026-09-11)

| ID | Final external result | Action | Current status |
| --- | --- | --- | --- |
| IF-01 | PASS | none | PASS |
| IF-02 | PASS | none | PASS |
| IF-03 | PATCH | patched in Phase 3B-1.2 (audience coverage wording + criterion) | REVISED — EXTERNAL FINAL REVIEW PENDING |
| IF-04 | PASS | none | PASS |
| IF-05 | PASS | none | PASS |
| IF-06 | PATCH | patched in Phase 3B-1.2 (removed two whole-response forbidden-phrase checks) | REVISED — EXTERNAL FINAL REVIEW PENDING |
| IF-07 | PASS | none | PASS |
| IF-08 | PASS | none | PASS |
| IF-09 | PASS | none | PASS |
| IF-10 | PASS | none | PASS |

The other eight IF cases were confirmed PASS in the second review.

### Final external approval (after Phase 3B-1.2)

| ID | Final status |
| --- | --- |
| IF-01 | PASS |
| IF-02 | PASS |
| IF-03 | PASS |
| IF-04 | PASS |
| IF-05 | PASS |
| IF-06 | PASS |
| IF-07 | PASS |
| IF-08 | PASS |
| IF-09 | PASS |
| IF-10 | PASS |

The final external review passed after the Phase 3B-1.2 patches. Domain 1
(`instruction_constraint_following`, IF-01 … IF-10) is **FROZEN / EXTERNALLY
APPROVED**. No case requires further semantic revision.

**Scope.** This approval covers **Domain 1 only**. Domains 2–5 are not authored,
and the full 50-case production dataset is **not** approved.

### Planned slots

| ID | Difficulty | Language | Planned capability (from matrix) |
| --- | --- | --- | --- |
| IF-01 | easy | zh | Exact-count + negative "no solution" constraint |
| IF-02 | easy | en | Several simultaneous simple constraints in English |
| IF-03 | medium | zh | Audience adaptation without factual drift |
| IF-04 | medium | zh | Clarification instead of unjustified execution |
| IF-05 | medium | zh | Meeting notes to action-item table without invention |
| IF-06 | medium | zh | Resolvable conflicting instructions with stated precedence |
| IF-07 | medium | zh | Strict serialization contract, input pre-structured |
| IF-08 | hard | zh | Information-preserving compression under a budget |
| IF-09 | hard | mixed | Multi-part instruction tracking with a resolvable conflict |
| IF-10 | hard | zh | Rewriting under dense negative constraints |

### Known issues

1. **Owner provenance in IF-05 is not fully mechanical.** The framework cannot verify by regex
   that every owner name came from the notes, so the case requires the literal placeholder
   `未指定` for unknowns and leaves name provenance to judges.
2. **IF-02 banned-word check is case-insensitive phrase matching.** It is binding because the
   prompt literally enumerates the banned words; it is not used as evidence of tone or quality.
3. **IF-06 salutation/signature compliance and rule-selection correctness are judge-evaluated.**
   The whole-response `forbidden_phrases` checks for 「尊敬的客户」 and 「简报销客服中心」 were
   removed in Phase 3B-1.2: those phrases may legitimately appear inside the internal
   「规则判断」 section while being correctly absent from the customer-visible 「通知正文」, so a
   whole-response match created false failures. The remaining deterministic checks (section
   labels, ordering, the 120-character notice bound, the maintenance-time regex) are unchanged.
   Whether the customer-visible body omits any salutation or signature, and whether the text
   *chose* rule B, stay semantic judgments.

The three false-pass risks raised by the first external review are closed by Phase 3B-1.1:

- IF-03's per-section length budget previously used a tolerance-based regex; it is now enforced
  exactly by `section_max_chars` (`len()` on the isolated, whitespace-stripped section body).
- IF-09's counting check previously only summed bullets globally, so a wrong 4/3/2 split could
  pass; `section_bullet_count` now verifies each section's own count.
- IF-07 previously used required keys plus a forbidden-legacy-key list, which could not reject
  arbitrary extra fields; `exact_keys` now requires the exact key set.

### Revisions requested (Phase 3B-1.1)

| ID | Requested change | Status |
| --- | --- | --- |
| IF-02 | Replace with the canonical definition | DONE — canonical text applied |
| IF-03 | Replace with the canonical definition; enforce the 120-character section budget exactly | DONE — canonical text applied; `section_max_chars` added |
| IF-06 | Replace with the canonical definition | DONE — canonical text applied |
| IF-07 | Replace with the canonical definition; require the exact key set | DONE — canonical text applied; `exact_keys` added |
| IF-09 | Replace with the canonical definition; verify the per-section 3/4/2 split | DONE — canonical text applied; `section_bullet_count` added |
| IF-10 | Replace with the canonical definition | DONE — canonical text applied |

### Revisions requested (Phase 3B-1.2)

| ID | Requested change | Status |
| --- | --- | --- |
| IF-03 | Make explicit in the candidate-visible prompt that each section must cover every fact category and omit nothing; state the full-coverage criterion | DONE — prompt requirement wording and one evaluation criterion replaced; `section_max_chars` declarations unchanged |
| IF-06 | Remove the two whole-response `forbidden_phrases` checks that produced false failures; keep the semantic requirement judge-evaluated | DONE — the two checks removed; required phrases, ordering, `section_max_chars`, and the maintenance-time regex unchanged |

### Self-review (Part H audit, 2026-09-11)

| # | Check | Result |
| --- | --- | --- |
| 1 | Exactly 10 IF cases | ✅ IF-01 … IF-10 |
| 2 | Difficulty 2 easy / 5 medium / 3 hard | ✅ easy IF-01/IF-02; medium IF-03…IF-07; hard IF-08…IF-10 |
| 3 | Language matches the approved matrix | ✅ 8 `zh`, 1 `en` (IF-02), 1 `mixed` (IF-09) |
| 4 | No two cases test the same failure mode | ✅ distinct: count+no-solution, multi-constraint English, audience drift, premature execution, invented owners, precedence, schema contract, lossy compression, multi-part tracking, negative rewriting |
| 5 | IF-05 does not drift into structured analysis | ✅ format transformation of notes with explicit output columns; no data interpretation or arithmetic |
| 6 | IF-07 input is already structured | ✅ JSON record supplied; task is field mapping only |
| 7 | IF-03 tests factual invariance + adaptation, not verbatim copying | ✅ invariants are numbers/dates/entities/statuses; wording and density may differ |
| 8 | IF-06 precedence is objectively resolvable | ✅ prompt states "专项活动要求优先于通用规范"; winning instruction identifiable |
| 9 | IF-08 difficulty is trade-off-driven, not length alone | ✅ dense source, hard character budget, 9 required invariants; success feasible (~35 chars of invariants in 240) |
| 10 | IF-09 mixed language is natural | ✅ Chinese parts for the domestic ops team, English checklist for the Singapore team |
| 11 | IF-10 is not a gimmick | ✅ banned items are realistic corporate style rules; meaning must survive |
| 12 | No case leaks evaluation criteria | ✅ no rubric/judge language in any prompt |
| 13 | No case needs current web information | ✅ all facts supplied in-prompt |
| 14 | No case requires chain-of-thought | ✅ only concise rule/assumption statements requested |
| 15 | Every deterministic check is defensible | ✅ checked with a correct-answer pass run and a targeted-violation fail run (see below) |

### Deterministic-check behavior evidence

The six revised cases (IF-02, IF-03, IF-06, IF-07, IF-09, IF-10) were re-exercised against a
canonical expected-success answer: every declared check passes. Targeted failures were then
injected and the intended check fired for each new operator — an over-budget section body
(`section_max_chars`), a wrong per-section split with an unchanged global total
(`section_bullet_count`), and an added legacy key (`exact_keys`). Covering test:
`tests/test_production_if_checks.py`. The unchanged cases retain their earlier authoring-time
evidence: missing/excess bullet counts (IF-01), extra table row (IF-05), dropped required figure
+ over-budget text (IF-08). This is authoring-time evidence, not external review.

### Domain-1 framework changes

`src/cases.py` emits a warning when `production_status` is present and not `complete`, so a
partial authoring dataset is explicitly flagged as "not eligible as the final V1 benchmark
dataset". No final production rule was weakened, and the full 50-case requirement remains a
warning rather than an error only so partial authoring can be validated offline.

`run_benchmark.py` gained a `--production-cases` flag that points `--cases` at the intended
production path (`data/cases_v1.json`) without changing the default, which remains the
synthetic framework fixture. Covering test: `tests/test_cli_cases.py`.

`src/deterministic.py` gained three generic operators in Phase 3B-1.1 —
`section_max_chars`, `section_bullet_count`, and `exact_keys` — raising the operator count from
18 to 21. They are generic (no case-specific branches) and exist to close the concrete
false-pass risks the first external review exposed. See `DECISIONS.md` D-039 and
`METHODOLOGY_V1.md` §2A.

Phase 3B-1.2 added deterministic-check **declaration validation** in
`src/deterministic.py` (`SUPPORTED_CHECK_TYPES`, `validate_check_declaration`), wired into
`src/cases.py`. All 21 operators now have a centralized parameter contract; a malformed
declaration is a dataset-validation error surfaced by `run_benchmark.py --validate-only`
before any paid execution. Operator count is unchanged at 21 and no operator's runtime
semantics changed. Covering tests: `tests/test_check_declarations.py`.

**Archived V0.1 data.** `data/archive/test_cases_v0_1.json` is the preserved V0.1 dataset. It
predates the V1 case schema (it omits `difficulty`, `language`, `test_intent`, and `tags`) and
declares **no** deterministic checks at all, so it cannot redefine V1 operator semantics. It is
historical and is deliberately outside active V1 dataset validation; V1 validation was not
weakened to accommodate it. See `tests/test_check_declarations.py`.

---

## Domain 2 — `structured_information_analysis`

| Field | Value |
| --- | --- |
| Domain status | FROZEN / EXTERNALLY APPROVED |
| Case IDs | SA-01 … SA-10 |
| Authoring date | 2026-09-11 |
| Authoring agent | External canonical authorship; Codex/DeepSeek performed integration only (Phase 3B-2 integration, Phase 3B-2.1 patch round) |
| Dataset file | `data/cases_v1.json` |
| Validation result | PASS — `python3 run_benchmark.py --validate-only --production-cases` exits 0; schema errors 0; all 10 SA cases' deterministic declarations validate; no new operator was required (operator count remains 21) |
| External review status | Final external review PASSED on all 10 cases, after the Phase 3B-2.1 patches to SA-05, SA-08, SA-09, and SA-10. No SA case requires further semantic revision. |
| Final approval status | **APPROVED — Domain 2 frozen (10/10 cases PASS)** |

### Case status

| ID | Status |
| --- | --- |
| SA-01 | PASS |
| SA-02 | PASS |
| SA-03 | PASS |
| SA-04 | PASS |
| SA-05 | PASS |
| SA-06 | PASS |
| SA-07 | PASS |
| SA-08 | PASS |
| SA-09 | PASS |
| SA-10 | PASS |

### External Gate 3B-2 result (2026-09-11)

| ID | Gate result | Action | Current status |
| --- | --- | --- | --- |
| SA-01 | PASS | none | PASS |
| SA-02 | PASS | none | PASS |
| SA-03 | PASS | none | PASS |
| SA-04 | PASS | none | PASS |
| SA-05 | PATCH | replaced with externally authored canonical patch (verbatim contiguous evidence-span rule) | REVISED — EXTERNAL RE-REVIEW PENDING |
| SA-06 | PASS | none | PASS |
| SA-07 | PASS | none | PASS |
| SA-08 | PATCH | replaced with externally authored canonical patch (fixed reporting order) | REVISED — EXTERNAL RE-REVIEW PENDING |
| SA-09 | PATCH | replaced with externally authored canonical patch (missing + known-failure interaction) | REVISED — EXTERNAL RE-REVIEW PENDING |
| SA-10 | PATCH | replaced with externally authored canonical patch (ROUND_HALF_UP + tie-break) | REVISED — EXTERNAL RE-REVIEW PENDING |

The four PATCH cases were replaced with externally authored canonical JSON and
were **not** rewritten by the executing agent. The six PASS cases (SA-01,
SA-02, SA-03, SA-04, SA-06, SA-07) are unchanged. This earlier PATCH round is
preserved here as QA provenance.

### Final external approval (after Phase 3B-2.1)

| ID | Final status |
| --- | --- |
| SA-01 | PASS |
| SA-02 | PASS |
| SA-03 | PASS |
| SA-04 | PASS |
| SA-05 | PASS |
| SA-06 | PASS |
| SA-07 | PASS |
| SA-08 | PASS |
| SA-09 | PASS |
| SA-10 | PASS |

The final external review passed after the Phase 3B-2.1 patches. Domain 2
(`structured_information_analysis`, SA-01 … SA-10) is **FROZEN / EXTERNALLY
APPROVED**. No SA case requires further semantic revision.

**Scope.** This approval covers **Domain 2 only**. Domains 3–5 are not authored,
and the full 50-case production dataset is **not** approved.

### Integration provenance

- The canonical case definitions (prompts, evaluation criteria, deterministic
  checks, reference facts, tags, titles, test intents, and notes) were authored
  **externally** and treated as authoritative.
- The integration agent performed **integration only**: no semantic rewriting,
  paraphrasing, rebalancing, or case redesign was permitted.
- Every deterministic declaration validated against the existing 21-operator
  schema. **No new operator was required** and no operator's runtime semantics
  changed.
- The integrated SA objects were verified object-for-object against the supplied
  canonical definitions, and the frozen Domain 1 objects were verified unchanged
  by hash before and after integration.

### Known issues

No known issues recorded. Domain 2 is frozen; no SA case requires further
semantic revision.

---

## Domain 3 — `product_reasoning_decision`

| Field | Value |
| --- | --- |
| Domain status | FROZEN / EXTERNALLY APPROVED |
| Case IDs | PR-01 … PR-10 |
| Authoring date | 2026-09-11 |
| Authoring agent | External canonical authorship; Codex/DeepSeek performed integration only (Phase 3B-3 integration, Phase 3B-3.1 patch round, Phase 3B-3R full-domain replacement, Phase 3B-3R.1 PR-10 patch) |
| Dataset file | `data/cases_v1.json` |
| Validation result | PASS — `python3 run_benchmark.py --validate-only --production-cases` exits 0; schema errors 0; all 10 PR cases' deterministic declarations validate; no new operator was required (operator count remains 21) |
| External review status | Final Matrix Gate: PASS. Final Semantic Gate: PASS. The repaired Matrix-compliant set passed after the Phase 3B-3R.1 PR-10 patch. |
| Final approval status | **APPROVED — Domain 3 re-frozen (10/10 cases PASS)** |

### Case status

| ID | Status |
| --- | --- |
| PR-01 | PASS |
| PR-02 | PASS |
| PR-03 | PASS |
| PR-04 | PASS |
| PR-05 | PASS |
| PR-06 | PASS |
| PR-07 | PASS |
| PR-08 | PASS |
| PR-09 | PASS |
| PR-10 | PASS |

### External Gate 3B-3R result (2026-09-11)

| ID | Gate result | Action | Current status |
| --- | --- | --- | --- |
| PR-01 | PASS | none | PASS |
| PR-02 | PASS | none | PASS |
| PR-03 | PASS | none | PASS |
| PR-04 | PASS | none | PASS |
| PR-05 | PASS | none | PASS |
| PR-06 | PASS | none | PASS |
| PR-07 | PASS | none | PASS |
| PR-08 | PASS | none | PASS |
| PR-09 | PASS | none | PASS |
| PR-10 | PATCH | replaced in Phase 3B-3R.1 (new-model candidate vs rollback-baseline role separation) | REVISED — EXTERNAL RE-REVIEW PENDING |

The Matrix-compliant replacement passed review on PR-01 … PR-09 at Gate 3B-3R.
PR-10 was patched in Phase 3B-3R.1 to resolve one contradiction:
Aster/Birch/Cedar are new-model candidates subject to the new-model hard gates,
while Legacy is the current production baseline and feature-flag rollback target
only and is not a new-model candidate; Cedar cannot be a recommendation or
runner-up because it fails the p95 and cost hard gates. PR-01 … PR-09 are
unchanged. PR-10 then passed the final Matrix + Semantic Gate (see below).

### Final external re-approval — Matrix + Semantic Gate (after Phase 3B-3R.1)

| ID | Final status |
| --- | --- |
| PR-01 | PASS |
| PR-02 | PASS |
| PR-03 | PASS |
| PR-04 | PASS |
| PR-05 | PASS |
| PR-06 | PASS |
| PR-07 | PASS |
| PR-08 | PASS |
| PR-09 | PASS |
| PR-10 | PASS |

The Phase 3B-3R Matrix Gate and the Semantic Gate both passed on the repaired
set after the Phase 3B-3R.1 PR-10 patch. Domain 3
(`product_reasoning_decision`, PR-01 … PR-10) is **RE-FROZEN / EXTERNALLY
APPROVED**. No further PR semantic change is authorized.

**Scope.** This approval covers **Domain 3 only**. Domains 4–5 are not authored,
and the full 50-case production dataset is **not** approved.

### Phase 3B-3R — Matrix Compliance Repair (2026-09-11)

An external audit found that the Phase 3B-3/3B-3.1 PR set (historical commit
`e859a6d`) passed semantic quality review but **drifted materially from the
APPROVED `CASE_MATRIX_V1.md` Domain-3 slot definitions**.

- The historical commit `e859a6d` remains intact and auditable; Git history was
  **not** reset, reverted, amended, squashed, or rewritten.
- Domain 3 production status was **reopened**.
- All ten PR cases were **replaced** by externally authored Matrix-compliant
  canonical definitions. The superseded definitions remain recoverable from
  `e859a6d`; no duplicate or archive copy was added to `data/cases_v1.json`.
- The replacement asserts slot/title, difficulty (2 easy / 5 medium / 3 hard),
  language (8 zh / 1 en / 1 mixed), output shape, and deterministic plan
  (8 Partial / 2 None, 0 Strong) compliance with the Matrix.
- IF and SA remain **FROZEN / EXTERNALLY APPROVED**.
- No methodology or Matrix change was made — `CASE_MATRIX_V1.md` was already
  authoritative and unchanged.

Domain status at the end of Phase 3B-3R.1: **REOPENED — MATRIX COMPLIANCE
EXTERNAL RE-REVIEW PENDING** (PR-01 … PR-09 PASS; PR-10 REVISED). This is
superseded by the final Matrix + Semantic Gate approval recorded above; the
provenance is retained.

#### Historical (superseded) PR review record

The records below document the earlier Phase 3B-3 / 3B-3.1 round. They are
preserved as QA provenance and are **superseded** by the Phase 3B-3R reopen.

### External Gate 3B-3 result (2026-09-11)

| ID | Gate result | Action | Current status |
| --- | --- | --- | --- |
| PR-01 | PATCH | replaced with externally authored canonical full object (exactly-two scope + no hidden feature pair) | REVISED — EXTERNAL RE-REVIEW PENDING |
| PR-02 | PASS | none | PASS |
| PR-03 | PASS | none | PASS |
| PR-04 | PASS | none | PASS |
| PR-05 | PATCH | replaced with externally authored canonical full object (unambiguous contribution formula) | REVISED — EXTERNAL RE-REVIEW PENDING |
| PR-06 | PATCH | replaced with externally authored canonical full object (explicit week-8 time-to-learning) | REVISED — EXTERNAL RE-REVIEW PENDING |
| PR-07 | PATCH | replaced with externally authored canonical full object (strategy-neutral output heading) | REVISED — EXTERNAL RE-REVIEW PENDING |
| PR-08 | PASS | none | PASS |
| PR-09 | PASS | none | PASS |
| PR-10 | PATCH | replaced with externally authored canonical full object (buffer-vs-option-value trade-off) | REVISED — EXTERNAL RE-REVIEW PENDING |

The five PATCH cases were replaced with externally authored canonical full
objects and were **not** rewritten by the executing agent. The five PASS cases
(PR-02, PR-03, PR-04, PR-08, PR-09) are unchanged. Domain 3 remains **EXTERNAL
RE-REVIEW PENDING** at that point in the history (this PATCH round is preserved
as QA provenance).

### Final external approval (after Phase 3B-3.1)

| ID | Final status |
| --- | --- |
| PR-01 | PASS |
| PR-02 | PASS |
| PR-03 | PASS |
| PR-04 | PASS |
| PR-05 | PASS |
| PR-06 | PASS |
| PR-07 | PASS |
| PR-08 | PASS |
| PR-09 | PASS |
| PR-10 | PASS |

The final external review passed after the Phase 3B-3.1 patches. Domain 3
(`product_reasoning_decision`, PR-01 … PR-10) is **FROZEN / EXTERNALLY
APPROVED**. No PR case requires further semantic revision.

**Scope.** This approval covers **Domain 3 only**. Domains 4–5 are not authored,
and the full 50-case production dataset is **not** approved.

### Integration provenance

- The canonical case definitions (prompts, evaluation criteria, deterministic
  checks, reference facts, tags, titles, test intents, and notes) were authored
  **externally** and treated as authoritative.
- The execution agent performed **integration only**: no semantic rewriting,
  paraphrasing, rebalancing, or case redesign was permitted.
- Every deterministic declaration validated against the existing 21-operator
  schema. **No new operator was required** and no operator's runtime semantics
  changed (operator count remains 21).
- **Open product recommendations were deliberately not converted into
  deterministic winner checks.** PR-04, PR-05, PR-06, and PR-10 declare only
  their canonical quantitative-baseline regex plus the supplied structural
  (section presence/order) checks; no winner regex was added. In particular,
  PR-10 does not deterministically require `A+D` or `A+C+D`: both portfolios may
  be defensible when the reasoning correctly handles the explicit
  buffer-vs-option-value trade-off. The final product decision remains
  judge-evaluated, exactly as the canonical JSON specifies.
- The integrated PR objects were verified object-for-object against the supplied
  canonical definitions, and the 20 frozen IF/SA objects were verified unchanged
  by hash before and after integration.

### Known issues

No known issues recorded. Domain 3 is frozen; no PR case requires further
semantic revision.

---

## Domain 4 — `chinese_business_communication`

| Field | Value |
| --- | --- |
| Domain status | FROZEN / EXTERNALLY APPROVED |
| Case IDs | BC-01 … BC-10 |
| Authoring date | 2026-09-11 |
| Authoring agent | External canonical authorship; Codex/DeepSeek performed integration only (Phase 3B-4 integration, Phase 3B-4.1 deterministic-contract patch) |
| Dataset file | `data/cases_v1.json` |
| Validation result | PASS — `python3 run_benchmark.py --validate-only --production-cases` exits 0; schema errors 0; all 10 BC cases' deterministic declarations validate; no new operator was required (operator count remains 21) |
| External review status | Final Matrix Gate: PASS. Final Semantic Gate: PASS. Final Deterministic-contract Gate: PASS. Approved after the Phase 3B-4.1 deterministic-contract repair. |
| Final approval status | **APPROVED — Domain 4 frozen (10/10 cases PASS)** |

### Case status

| ID | Status |
| --- | --- |
| BC-01 | PASS |
| BC-02 | PASS |
| BC-03 | PASS |
| BC-04 | PASS |
| BC-05 | PASS |
| BC-06 | PASS |
| BC-07 | PASS |
| BC-08 | PASS |
| BC-09 | PASS |
| BC-10 | PASS |

### External Phase 3B-4 Gate result (2026-09-11)

| ID | Gate result | Action | Current status |
| --- | --- | --- | --- |
| BC-01 | PATCH | replaced in Phase 3B-4.1 (order-independent numeric checks + 7-day check) | REVISED — EXTERNAL RE-REVIEW PENDING |
| BC-02 | PASS | none | PASS |
| BC-03 | PASS | none | PASS |
| BC-04 | PATCH | replaced in Phase 3B-4.1 (no-jargon instruction aligned to response-wide checker) | REVISED — EXTERNAL RE-REVIEW PENDING |
| BC-05 | PASS | none | PASS |
| BC-06 | PASS | none | PASS |
| BC-07 | PASS | none | PASS |
| BC-08 | PASS | none | PASS |
| BC-09 | PASS | none | PASS |
| BC-10 | PATCH | replaced in Phase 3B-4.1 (independent key-figure presence checks) | REVISED — EXTERNAL RE-REVIEW PENDING |

The three PATCH cases were replaced with externally authored canonical objects
and were **not** rewritten by the executing agent. The seven PASS cases are
unchanged. The deterministic plan is unchanged: 3 Strong / 4 Partial /
3 None, with BC-03, BC-06, and BC-09 still `deterministic_checks == []`.

### Final external approval — Matrix + Semantic + Deterministic-contract Gates (after Phase 3B-4.1)

| ID | Final status |
| --- | --- |
| BC-01 | PASS |
| BC-02 | PASS |
| BC-03 | PASS |
| BC-04 | PASS |
| BC-05 | PASS |
| BC-06 | PASS |
| BC-07 | PASS |
| BC-08 | PASS |
| BC-09 | PASS |
| BC-10 | PASS |

The final Matrix Gate, Semantic Gate, and Deterministic-contract Gate all passed
after the Phase 3B-4.1 repair. Domain 4
(`chinese_business_communication`, BC-01 … BC-10) is **FROZEN / EXTERNALLY
APPROVED**. No further BC production-case semantic change is authorized.

**Scope.** This approval covers **Domain 4 only**. Domain 5 (AW) is not
authored, and the full 50-case production dataset is **not** approved.

### Integration provenance (Phase 3B-4)

- **Semantic authorship is external.** The canonical BC definitions (prompts,
  evaluation criteria, deterministic checks, reference facts, tags, titles,
  test intents, and notes) were authored externally and treated as
  authoritative. Codex/DeepSeek performed **integration only**; no semantic
  rewriting, paraphrasing, or case redesign was permitted.
- **Slot identity was checked before authoring/integration.** The BC cases match
  the APPROVED `CASE_MATRIX_V1.md` Domain-4 slots (working title, difficulty,
  output shape, deterministic plan).
- All 10 BC cases are `zh`; difficulty = 2 easy / 5 medium / 3 hard.
- Deterministic plan = 3 Strong (BC-01, BC-02, BC-10) / 4 Partial (BC-04,
  BC-05, BC-07, BC-08) / 3 None (BC-03, BC-06, BC-09). **BC-03, BC-06, and
  BC-09 intentionally have `deterministic_checks == []`** and were not given
  checks.
- **BC-07 follows the explicit-role anti-stereotype rule**: audience adaptation
  is based only on the stated work responsibilities (business-unit decision
  maker vs. project execution team) and explicitly forbids inferring
  personality, power-distance, or cultural stereotypes.
- **Operator count remains 21.** No new operator and no deterministic runtime
  change.
- **No semantic proxy checks were added.** Objective/structural checks are
  exactly the supplied canonical declarations; open or subjective communication
  quality stays judge-evaluated (no winner regex, no hidden canonical answer).
- The 30 frozen IF/SA/PR objects were verified unchanged by hash before and
  after integration.

### Known issues

No known issues recorded. Domain 4 is frozen; no BC case requires further
semantic revision.

---

## Domain 5 — `agent_workflow_planning`

| Field | Value |
| --- | --- |
| Domain status | FROZEN / EXTERNALLY APPROVED |
| Case IDs | AW-01 … AW-10 |
| Authoring date | 2026-09-11 |
| Authoring agent | External canonical authorship; Codex/DeepSeek performed integration only (Phase 3B-5) |
| Dataset file | `data/cases_v1.json` |
| Validation result | PASS — `python3 run_benchmark.py --validate-only --production-cases` exits 0; schema errors 0; all 10 AW cases' deterministic declarations validate; no new operator was required (operator count remains 21) |
| External review status | Final Matrix Gate: PASS. Final Semantic Gate: PASS. Final Deterministic-contract Gate: PASS. Approved after the Phase 3B-5.1 AW-03/AW-04 repair. |
| Final approval status | **APPROVED — Domain 5 frozen (10/10 cases PASS)** |

### Case status

| ID | Status |
| --- | --- |
| AW-01 | PASS |
| AW-02 | PASS |
| AW-03 | PASS |
| AW-04 | PASS |
| AW-05 | PASS |
| AW-06 | PASS |
| AW-07 | PASS |
| AW-08 | PASS |
| AW-09 | PASS |
| AW-10 | PASS |

### External Phase 3B-5 result (2026-09-11)

| ID | Gate result | Action | Current status |
| --- | --- | --- | --- |
| AW-01 | PASS | none | PASS |
| AW-02 | PASS | none | PASS |
| AW-03 | PATCH | replaced in Phase 3B-5.1 (unique-label execution-plan contract; letters-only critical path) | REVISED — EXTERNAL RE-REVIEW PENDING |
| AW-04 | PATCH | replaced in Phase 3B-5.1 (digits-only retry-budget cell contract) | REVISED — EXTERNAL RE-REVIEW PENDING |
| AW-05 | PASS | none | PASS |
| AW-06 | PASS | none | PASS |
| AW-07 | PASS | none | PASS |
| AW-08 | PASS | none | PASS |
| AW-09 | PASS | none | PASS |
| AW-10 | PASS | none | PASS |

The two PATCH cases were replaced with externally authored canonical objects
and were **not** rewritten by the executing agent. The eight PASS cases are
unchanged. The deterministic plan is unchanged: 2 Strong / 3 Partial / 5 None.

### Final external approval (after Phase 3B-5.1)

| ID | Final status |
| --- | --- |
| AW-01 | PASS |
| AW-02 | PASS |
| AW-03 | PASS |
| AW-04 | PASS |
| AW-05 | PASS |
| AW-06 | PASS |
| AW-07 | PASS |
| AW-08 | PASS |
| AW-09 | PASS |
| AW-10 | PASS |

The final Matrix Gate, Semantic Gate, Deterministic-contract Gate, and global
coverage/invariant Gate all passed. Domain 5 (`agent_workflow_planning`,
AW-01 … AW-10) is **FROZEN / EXTERNALLY APPROVED**. No further AW production-case
semantic change is authorized.

**Scope.** With this approval all five domains are frozen and the full 50-case
V1 production dataset is approved for final freeze.

### Integration provenance (Phase 3B-5)

- **Semantic authorship is external.** The canonical AW definitions (prompts,
  evaluation criteria, deterministic checks, reference facts, tags, titles,
  test intents, and notes) were authored externally and treated as
  authoritative. Codex/DeepSeek performed **integration only**; no semantic
  rewriting, paraphrasing, or case redesign was permitted.
- **Matrix compliance was checked before integration.** The AW cases match the
  APPROVED `CASE_MATRIX_V1.md` Domain-5 slots (working title, difficulty,
  language, output shape, deterministic plan).
- **Planning only.** These cases plan agent workflows; the benchmark does not
  execute real tools, code tasks, multi-agent implementations, or network calls.
- Difficulty = 2 easy / 5 medium / 3 hard; language = 7 `zh` / 1 `en` /
  2 `mixed`; deterministic plan = 2 Strong (AW-01, AW-08) / 3 Partial (AW-03,
  AW-04, AW-06) / 5 None (AW-02, AW-05, AW-07, AW-09, AW-10). The five None
  cases are intentionally `deterministic_checks == []`.
- **AW-04** retry semantics are side-effect-aware and do **not** assume a
  universal retry count; retry-count appropriateness remains judge-evaluated.
- **AW-05** separates technical tool availability from business **authority**;
  the boundary is judged by consequence/permission, not by a keyword classifier.
- **AW-08** tests explicit inter-tool data contracts (8 fields; validation and
  mismatch handling).
- **AW-09** and **AW-10** intentionally remain judge-only: stop/budget discipline
  and stop-and-escalate-on-missing-input behaviour are judged, not proxy-checked.
- The 40 frozen IF/SA/PR/BC objects were verified unchanged by hash before and
  after integration. Operator count remains 21; no runtime change.

### Known issues

No AW integration issues. **Matrix/data divergence (resolved in Phase 3B-5R):**
the Phase 3B-5 audit found IF-06 realized as a Partial although
`CASE_MATRIX_V1.md` requires None. Phase 3B-5R restored IF-06 to the approved
judge-only contract, so the realized dataset now has exactly **11** `[]` cases
and the approved **14 Strong / 25 Partial / 11 None** distribution. See Domain 1.
Domain 5 remains **not approved**.

---

## Change log

| Date | Change |
| --- | --- |
| 2026-09-11 | Ledger created. Domain 1 set to authoring in progress; domains 2–5 not started. |
| 2026-09-11 | Domain 1 authored (IF-01…IF-10), self-reviewed, and set to AUTHORED — EXTERNAL REVIEW PENDING. Validation passed. Not approved. |
| 2026-09-11 | First external review of Domain 1 completed: IF-01/04/05/08 PASS; IF-02/03/06/07/09/10 PATCH. Domain 1 moved to EXTERNAL RE-REVIEW PENDING. |
| 2026-09-11 | Phase 3B-1.1 executed: the six PATCH cases were replaced with externally authored canonical JSON (no agent rewriting); three generic operators (`section_max_chars`, `section_bullet_count`, `exact_keys`) added, raising the operator count 18 → 21. Domain 1 remains EXTERNAL RE-REVIEW PENDING; not approved. |
| 2026-09-11 | Second (final) external review completed: 8 IF cases PASS; IF-03 and IF-06 PATCH; 0 REJECT. Domain 1 moved to EXTERNAL FINAL REVIEW PENDING. |
| 2026-09-11 | Phase 3B-1.2 executed: IF-03 prompt now requires each section to cover every fact category (no omission for the length budget) with a matching criterion; IF-06 lost the two whole-response forbidden-phrase checks that produced false failures. Deterministic-check declaration validation added for all 21 operators. Domain 1 remains EXTERNAL FINAL REVIEW PENDING; not approved. |
| 2026-09-11 | Final external review PASSED on all 10 IF cases after the Phase 3B-1.2 patches. Domain 1 (`instruction_constraint_following`, IF-01…IF-10) set to FROZEN / EXTERNALLY APPROVED. Domains 2–5 remain not started; the full 50-case dataset is not approved. |
| 2026-09-11 | Phase 3B-2 integrated the externally authored canonical SA-01…SA-10 (integration only; no semantic rewriting, no new operator). Domain 2 (`structured_information_analysis`) set to AUTHORED — EXTERNAL REVIEW PENDING. Dataset is now 20/50 cases. Domain 1 remains FROZEN. SA is not approved. |
| 2026-09-11 | External Gate 3B-2 completed: SA-01/02/03/04/06/07 PASS; SA-05/08/09/10 PATCH; 0 REJECT. Domain 2 moved to EXTERNAL RE-REVIEW PENDING. |
| 2026-09-11 | Phase 3B-2.1 executed: the four PATCH cases were replaced with externally authored canonical patches (integration only; no semantic rewriting, no new operator). SA-05/08/09/10 set to REVISED — EXTERNAL RE-REVIEW PENDING; the six PASS cases retained. Domain 2 remains EXTERNAL RE-REVIEW PENDING; not approved or frozen. |
| 2026-09-11 | Final external review PASSED on all 10 SA cases after the Phase 3B-2.1 patches. Domain 2 (`structured_information_analysis`, SA-01…SA-10) set to FROZEN / EXTERNALLY APPROVED. Domains 3–5 remain not authored; the full 50-case dataset is not approved. |
| 2026-09-11 | Phase 3B-3 integrated the externally authored canonical PR-01…PR-10 (integration only; no semantic rewriting, no new operator, no winner regexes added). Domain 3 (`product_reasoning_decision`) set to AUTHORED — EXTERNAL REVIEW PENDING. Dataset is now 30/50 cases. Domains 1–2 remain FROZEN. PR is not approved. |
| 2026-09-11 | External Gate 3B-3 completed: PR-02/03/04/08/09 PASS; PR-01/05/06/07/10 PATCH; 0 REJECT. Domain 3 moved to EXTERNAL RE-REVIEW PENDING. |
| 2026-09-11 | Phase 3B-3.1 executed: the five PATCH cases were replaced with externally authored canonical full objects (integration only; no semantic rewriting, no new operator, no winner regexes). PR-01/05/06/07/10 set to REVISED — EXTERNAL RE-REVIEW PENDING; the five PASS cases retained. Domain 3 remains EXTERNAL RE-REVIEW PENDING; not approved or frozen. |
| 2026-09-11 | Final external review PASSED on all 10 PR cases after the Phase 3B-3.1 patches. Domain 3 (`product_reasoning_decision`, PR-01…PR-10) set to FROZEN / EXTERNALLY APPROVED. Domains 4–5 remain not authored; the full 50-case dataset is not approved. |
| 2026-09-11 | Phase 3B-3R — Matrix Compliance Repair. External audit found the frozen PR set (historical commit `e859a6d`) had drifted from APPROVED `CASE_MATRIX_V1.md` slot definitions despite passing semantic review. Domain 3 reopened; all ten PR cases replaced by externally authored Matrix-compliant canonical definitions (integration only; no new operator, no winner regexes, no hidden thresholds). `e859a6d` left intact. Domain 3 = REOPENED — MATRIX COMPLIANCE EXTERNAL REVIEW PENDING; PR-01…PR-10 = AUTHORED — EXTERNAL REVIEW PENDING. IF/SA remain frozen; Domains 4–5 unauthored; dataset 30/50; not approved. |
| 2026-09-11 | External Gate 3B-3R completed: PR-01…PR-09 PASS; PR-10 PATCH; 0 REJECT. Domain 3 = REOPENED — MATRIX COMPLIANCE EXTERNAL RE-REVIEW PENDING. |
| 2026-09-11 | Phase 3B-3R.1 executed: PR-10 replaced with the externally authored canonical object that separates new-model candidates (Aster/Birch/Cedar) from the Legacy rollback baseline and bars Cedar from recommendation/runner-up. PR-01…PR-09 unchanged. PR-10 = REVISED — EXTERNAL RE-REVIEW PENDING. Also corrected a Phase 3B-3R documentation error that had left Domain 1's QA status mislabeled as reopened. Domain 3 remains EXTERNAL RE-REVIEW PENDING; not approved or frozen. |
| 2026-09-11 | Final Matrix Gate PASS and final Semantic Gate PASS on the repaired PR set after the Phase 3B-3R.1 patch. Domain 3 (`product_reasoning_decision`, PR-01…PR-10) set to FROZEN / EXTERNALLY APPROVED (re-frozen). Domains 1–2 remain frozen; domains 4–5 unauthored; dataset 30/50; the full dataset is not approved. |
| 2026-09-11 | Phase 3B-4 integrated the externally authored canonical BC-01…BC-10 from approved Domain-4 Matrix slots (integration only; no semantic rewriting, no new operator, no proxy checks). Domain 4 (`chinese_business_communication`) set to AUTHORED — MATRIX + SEMANTIC EXTERNAL REVIEW PENDING; each BC case AUTHORED — EXTERNAL REVIEW PENDING. Dataset is now 40/50 cases. Domains 1–3 remain frozen; Domain 5 (AW) unauthored. BC is not approved or frozen. |
| 2026-09-11 | External Phase 3B-4 Gate completed: BC-02/03/05/06/07/08/09 PASS; BC-01/04/10 PATCH; 0 REJECT. Domain 4 moved to MATRIX + SEMANTIC EXTERNAL RE-REVIEW PENDING. |
| 2026-09-11 | Phase 3B-4.1 executed: BC-01, BC-04, and BC-10 replaced with externally authored canonical objects (integration only; no semantic rewriting, no new operator). BC-01 numeric checks are now order-independent with the missing 7-day check added; BC-04's no-jargon instruction now matches the response-wide forbidden_phrases checker; BC-10 uses independent key-figure presence checks instead of order-sensitive paired regexes. BC-01/04/10 = REVISED — EXTERNAL RE-REVIEW PENDING; the seven PASS cases retained. Domain 4 remains EXTERNAL RE-REVIEW PENDING; not approved or frozen. |
| 2026-09-11 | Final Matrix Gate PASS, Semantic Gate PASS, and Deterministic-contract Gate PASS on the BC domain after the Phase 3B-4.1 repair. Domain 4 (`chinese_business_communication`, BC-01…BC-10) set to FROZEN / EXTERNALLY APPROVED. Domains 1–3 remain frozen; Domain 5 (AW) unauthored; dataset 40/50; the full dataset is not approved. |
| 2026-09-11 | Phase 3B-5 integrated the externally authored canonical AW-01…AW-10 from approved Domain-5 Matrix slots (integration only; no semantic rewriting, no new operator, no proxy checks). All 50 of 50 slots are now authored. Domain 5 (`agent_workflow_planning`) set to AUTHORED — MATRIX + SEMANTIC EXTERNAL REVIEW PENDING; each AW case AUTHORED — EXTERNAL REVIEW PENDING. AW-04 has no universal retry-count assumption; AW-05 separates access from authority; AW-09/AW-10 remain judge-only. Domains 1–4 remain frozen; the dataset is not yet production-frozen. Also recorded a pre-existing Matrix/data divergence: IF-06 is a Matrix None slot but the frozen IF-06 carries four structural checks, so the realized dataset has 10 `[]` cases, not 11. |
| 2026-09-11 | Phase 3B-5R — IF-06 Matrix Compliance Repair. The Phase 3B-5 audit's IF-06 divergence (Matrix None vs. realized Partial) was repaired by replacing IF-06 with the externally authored canonical object whose `deterministic_checks == []`; prompt semantics unchanged and the other 49 cases untouched. Domain 1 reopened to REOPENED — IF-06 MATRIX COMPLIANCE EXTERNAL RE-REVIEW PENDING; IF-06 = REVISED — MATRIX COMPLIANCE EXTERNAL RE-REVIEW PENDING. Realized deterministic distribution restored to the approved 14 Strong / 25 Partial / 11 None. Domain 5 (AW) still awaits external review. No Matrix amendment. |
| 2026-09-11 | External IF-06 Matrix re-review PASSED; Domain 1 returned to FROZEN / EXTERNALLY APPROVED (IF-06 = PASS — MATRIX COMPLIANT). Full 50-case Matrix invariants PASS. External Phase 3B-5 AW review: AW Matrix Gate PASS; Semantic + Deterministic-contract Gate 8 PASS / 2 PATCH; 0 REJECT. |
| 2026-09-11 | Phase 3B-5.1 executed: AW-03 and AW-04 replaced with externally authored canonical deterministic-contract objects (integration only; no semantic rewriting, no new operator, no hidden canonical values). AW-03 now requires each complete task label exactly once with A/B/C as one parallel batch and a letters-only critical path; AW-04's retry-budget cell contract is now digits-only and consistent with the wildcard checker. AW-03/AW-04 = REVISED — EXTERNAL RE-REVIEW PENDING; the eight AW PASS cases retained. Domain 5 remains MATRIX + SEMANTIC + DETERMINISTIC-CONTRACT EXTERNAL RE-REVIEW PENDING; not approved or frozen. Distribution unchanged at 14 / 25 / 11. |
| 2026-09-11 | **FINAL V1 DATASET FREEZE.** External gates: IF-06 Matrix re-review PASS; full 50-case Matrix Gate PASS; Semantic Gate PASS; Deterministic-contract Gate PASS; global coverage/invariant Gate PASS; AW-03/AW-04 final re-review PASS. Result: 50 PASS / 0 PATCH / 0 REJECT. Domain 5 (`agent_workflow_planning`) set to FROZEN / EXTERNALLY APPROVED; AW-01…AW-10 all PASS. All five domains frozen; `production_status` set to `"complete"` (the already-supported production-ready value). Semantic freeze manifest created at `docs/DATASET_FREEZE_V1.md`; aggregate SHA-256 `6b450383e528a5a0a6b813112f96182a3625c04c948839fc551c8ded63da513c`. |
| 2026-09-11 | Recorded a documentation-level title-text divergence (not a slot/identity drift): 43 of 50 frozen case titles equal the `CASE_MATRIX_V1.md` working titles; IF-01, IF-02, IF-04, IF-09, IF-10, SA-01, and SA-08 carry their own externally approved display titles. Identifiers, domains, difficulty, language, and deterministic level match the Matrix for all 50 cases. Frozen case titles were not edited. |
