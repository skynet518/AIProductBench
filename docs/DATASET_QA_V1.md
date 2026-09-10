# AIProductBench CN V1 — Dataset QA Ledger

**Status: Domains 1 and 2 (`instruction_constraint_following`,
`structured_information_analysis`) are FROZEN / EXTERNALLY APPROVED. Domains 3–5
are not authored. The full 50-case production dataset (20/50 cases) is NOT
approved. No live paid benchmark is authorized.**

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
| 3 | `product_reasoning_decision` | PR | 10 | not started | 2026-09-11 |
| 4 | `chinese_business_communication` | BC | 10 | not started | 2026-09-11 |
| 5 | `agent_workflow_planning` | AW | 10 | not started | 2026-09-11 |

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
| External review status | Final external review PASSED on all 10 cases, after the Phase 3B-1.2 patches to IF-03 and IF-06. No case requires further semantic revision. |
| Final approval status | **APPROVED — Domain 1 frozen (10/10 cases PASS)** |

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
| Domain status | not started |
| Case IDs | PR-01 … PR-10 (planned) |
| Authoring date | — |
| Validation result | — |
| External review status | not submitted |
| Final approval status | **not approved** |

No known issues. Not started.

---

## Domain 4 — `chinese_business_communication`

| Field | Value |
| --- | --- |
| Domain status | not started |
| Case IDs | BC-01 … BC-10 (planned) |
| Authoring date | — |
| Validation result | — |
| External review status | not submitted |
| Final approval status | **not approved** |

No known issues. Not started.

---

## Domain 5 — `agent_workflow_planning`

| Field | Value |
| --- | --- |
| Domain status | not started |
| Case IDs | AW-01 … AW-10 (planned) |
| Authoring date | — |
| Validation result | — |
| External review status | not submitted |
| Final approval status | **not approved** |

No known issues. Not started.

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
