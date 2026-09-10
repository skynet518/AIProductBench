# AIProductBench CN V1 — Case Design Standard

**Status: APPROVED FOR PHASE 3B AUTHORING (Gate 3A.1 passed). The production
dataset itself is not approved; no production case is written yet.**

This document defines how every production benchmark case must be authored. It
is binding for Phase 3B. A case that does not satisfy this standard does not
enter the dataset.

Related documents: `METHODOLOGY_V1.md` (evaluation design), `CASE_MATRIX_V1.md`
(the 50-slot coverage matrix this standard is applied to), `DECISIONS.md`
(rationale for each rule).

---

## 1. Purpose

Cases must represent **realistic AI product-team workloads**, not trivia,
academic exams, or coding benchmarks.

A case is a task a competent AI product manager, product engineer, or business
lead might genuinely hand to a model during a working week: prioritising a
backlog, turning a noisy ticket into structured data, writing a report to
management, planning a workflow, or rewriting an update for a different
audience.

The benchmark measures whether a model is useful for that work at a defensible
cost and latency. It does not measure whether a model can win a puzzle.

---

## 2. Case schema

### Required fields

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | Stable, unique, domain-prefixed (`IF-01`, `SA-07`, `PR-03`, `BC-09`, `AW-02`) |
| `title` | string | Short working title; the case's name in reports |
| `domain` | string | One of the five frozen domains |
| `difficulty` | string | `easy` \| `medium` \| `hard` (see §4) |
| `language` | string | `zh` \| `en` \| `mixed` (see §5) |
| `test_intent` | string | One sentence: what capability this case isolates and what a good answer must demonstrate |
| `prompt` | string | The user-facing task. Self-contained; no external lookup required |
| `evaluation_criteria` | list of strings | Explicit, concrete, judge-facing criteria |
| `deterministic_checks` | list of objects | Machine-checkable constraints, or `[]` when none apply |
| `tags` | list of strings | Capability and format tags for coverage auditing |

The validator in `src/cases.py` enforces every required field. There is no
"production mode" that relaxes the schema and no separate fixture schema:
fixtures satisfy the same contract so the two cannot drift.

### Optional fields

| Field | Purpose |
| --- | --- |
| `reference_facts` | Facts that a correct answer must preserve, and grader metadata for checking preservation. Every entry must be derivable from candidate-visible input (see §3) |
| `expected_structure` | The output shape a correct answer should take (sections, keys, ordering) |
| `ambiguity_notes` | Deliberate ambiguity in the case and what a good answer is expected to do about it |
| `author_notes` | Authoring rationale, known trade-offs, calibration notes for reviewers |
| `word_count_justification` | Required for a `mixed`-language case that uses `max_words` / `min_words` (see §5) |

---

## 3. Case quality rules

Each case tests **one clear capability**. Secondary capability is allowed and
recorded, but a case that tests five things at once cannot diagnose any of them.

### Must avoid

- **Duplicated capability coverage.** Two cases in the same domain must not test
  the same capability in the same output shape. The matrix records a
  distinctiveness statement per case for exactly this reason.
- **Trivia or external-knowledge dependence** unless the required facts are
  included in the prompt.
- **Prompts whose correct answer depends on current web information.** The
  benchmark is a static snapshot; anything time-varying is unanswerable and
  unfair.
- **Coding tasks.** Out of V1 scope.
- **Obscure domain expertise unrelated to AI product work.** No specialist
  medicine, law, or finance knowledge unless it is supplied in the prompt.
- **Intentionally adversarial prompt-injection tasks.** Deferred beyond V1.
- **Pure creative-writing quality contests.** Style preferences cannot be scored
  reliably.
- **Subjective prompts with no meaningful scoring criteria.** If two reviewers
  could not agree on what a good answer contains, the case is not scoreable.

### Self-containment

Every case must be answerable from the prompt alone. Where the task is
deliberately under-specified, the *correct behaviour* is to notice the gap and
say so — and that behaviour is stated in `evaluation_criteria`.

**The benchmark must never evaluate a candidate against source information the
candidate was not given.** Any source fact required to perform the task must be
available in the candidate-visible prompt or input. A case that needs an
external fact, a hidden document, or current web data is not a valid V1 case;
the fix is to put the required material in the visible input, not to add it to
grading metadata.

### Reference facts (`reference_facts`)

`reference_facts` exists to make fact preservation *auditable*, not to smuggle
in facts the candidate never saw. Grading must stay a check of the answer
against the visible material plus objectively derivable ground truth.

`reference_facts` **may** contain:

- normalized copies of facts already supplied to the candidate
- factual invariants extracted from the visible source material
- derived ground-truth values that are computable from candidate-visible data
- grader metadata used to verify preservation or correctness

`reference_facts` **must not** contain:

- hidden source evidence required for a correct answer but unavailable to the
  candidate
- an expected answer the candidate could not derive from the visible input

A hidden expected answer or derived grader reference is acceptable **only when
the candidate could derive it from visible input**. For example, a grader may
store the exact CNY total recomputed from a table that appears in the prompt;
that is legitimate because the candidate has everything needed to produce it.
Storing a figure that appears nowhere in the prompt and cannot be computed from
it is a self-containment defect that must be fixed by making the fact visible,
not by dropping the requirement.

When a case deliberately withholds information, the rewarded behaviour is to
state the gap and bound the answer — not to reproduce a hidden fact. That
behaviour is written into `evaluation_criteria`, never left implicit.

---

## 4. Difficulty definition

Difficulty reflects **reasoning and constraint complexity**, not prompt length. A
long prompt describing a simple task is still easy; a short prompt with
competing objectives is hard.

### EASY

- One primary task
- Few constraints
- Low ambiguity
- Little or no trade-off reasoning
- A competent model should succeed without a strategy

### MEDIUM

- Multiple constraints
- Some prioritisation or inference required
- Realistic ambiguity
- Requires structured judgment and an explicit rationale
- A model can fail by answering generically rather than incorrectly

### HARD

- Competing objectives
- Multi-step reasoning
- Incomplete or noisy information
- Real trade-offs that cannot all be satisfied simultaneously
- Ambiguity handling: the model must decide and justify, not hedge
- Strict output or business constraints on top of the reasoning load

Distribution per domain is frozen at 2 easy / 5 medium / 3 hard.

---

## 5. Language rule

Target dataset composition:

- approximately 40 Chinese-first cases
- approximately 10 English or mixed/cross-lingual cases

Chinese business semantics are a **first-class test target**, not a translation
exercise. Do not write an English prompt and mechanically translate it into
Chinese: Chinese business communication has its own register, register shifts
between audiences, and information density, and a translated prompt tests
translation artifacts rather than the target capability.

Audience adaptation is scored against **observable communication requirements**
(who the reader is, what they must decide, which facts they need, how much
detail is appropriate), never against a generalized idea of hierarchy,
deference, or "Chinese style". The same anti-stereotype rule applies across the
whole Chinese-language domain: judge what the answer communicates to a stated
audience, not whether it matches a stereotype about how Chinese business
writing is assumed to work.

### Length constraints by language

Word counting splits on whitespace, which is meaningless for Chinese text.

| `language` | `max_words` / `min_words` | Allowed length checks |
| --- | --- | --- |
| `zh` | **Forbidden** | `max_chars` / `min_chars` |
| `en` | Allowed | `max_words` / `min_words` / `max_chars` / `min_chars` |
| `mixed` | Allowed only with `word_count_justification` | Any, with justification recorded |

A Chinese case that declares a word-count check is a **validation error**, not a
warning. This is enforced in `src/cases.py` and covered by tests.

---

## 6. Evaluation design

### Case-level criteria

Every case carries explicit `evaluation_criteria` supplied to both judges.
Criteria must be concrete enough that two competent human reviewers understand
what a high-quality answer contains. "Be helpful and accurate" is not a
criterion; "names the deferred item and justifies the deferral from the stated
rule" is.

Criteria should be checkable statements, phrased so a reviewer can mark them met
or not met.

### Judging reasoning without private chain-of-thought

V1 does **not** require a model to expose private chain-of-thought, and never
asks for it. Phrases such as "show your reasoning", "step-by-step reasoning",
or "transparent reasoning" must not appear in a prompt or an
`evaluation_criteria` item.

What may be requested and judged is the **observable answer and its stated
justification**:

- a concise decision rationale
- evidence cited from the supplied facts
- a trade-off explanation
- stated assumptions
- the basis of a recommendation

`reasoning_quality` is scored from that observable material, never from a hidden
reasoning trace that the candidate was not asked to produce and the judge never
receives. A correct final answer with no stated basis is not automatically
high-scoring, and a fluent rationale that is unsupported is not high-scoring
either; both judgments are made on the answer the candidate actually delivered.

### Deterministic checks

Use deterministic checks whenever an objective constraint can be tested
programmatically:

- structural: valid JSON, exact key sets, required keys, forbidden keys
- counting: exact item count, bullet count, min/max items, per-section bullet counts
- length: character limits (all languages), per-section character limits, word limits (English only)
- content: required or forbidden phrases, required or forbidden patterns
- order: required ordering of elements
- numeric: a value within a required range

**A production case cannot pass dataset validation if any deterministic-check
declaration is malformed.** Every check is validated against a centralized
per-operator schema: the `type` must be one of the supported operators, required
parameters must be present with the correct type, regexes must compile, list
parameters must be non-empty lists of unique non-empty strings, counts must be
integers of the correct sign, and section markers must be valid and distinct.
This runs inside `run_benchmark.py --validate-only`, so a malformed declaration
is rejected before any execution rather than failing silently at run time.

**Do not invent deterministic checks for subjective qualities merely to raise
the automation percentage.** A check that a reasonable expert answer could fail
while still being correct is a bad check. "Answer mentions the word 风险" is not
a test of risk awareness.

A case with no objectively testable constraint declares `deterministic_checks: []`
and is scored purely by judges. That is a valid and honest outcome; the evaluator
reports `null` rather than a fabricated pass rate.

#### Deterministic-check quality rule

A deterministic check **must test the intended constraint, not a superficial
proxy.** A check that can pass while the constraint is violated, or fail while
the answer is correct, is worse than no check: it injects noise into
`constraint_pass_rate` and makes an automatic number look like evidence.

Weak proxies that are not acceptable as the primary evidence for a capability:

- requiring the word "risk" (or 风险) to prove risk analysis
- requiring a fixed phrase to prove correct prioritisation or resolution
- checking that a number appears without checking whether the computation is
  correct
- requiring a label to prove the underlying content exists

Acceptable deterministic evidence is structural, exact, enum-based, count-based,
invariant-based, or objectively derived:

- schema validity, exact key sets, forbidden keys, enum membership
- exact / minimum / maximum counts of items, rows, bullets, or sections
- explicitly stated character or word budgets
- required ordering where the order is objectively derivable
- set relations, e.g. owners named are a subset of owners stated in the input
- exact derived values recomputed from candidate-visible data, within a stated
  tolerance where the case defines one
- absence of phrases that the prompt itself literally enumerates as forbidden

Where correctness cannot be robustly checked mechanically, it is left to
case-level criteria and judges. A required literal phrase or a presence-only
numeric check may support a structural test, but it may not be the primary
evidence that a semantic capability was exercised. This rule governs the
Strong/Partial/None opportunities recorded in `CASE_MATRIX_V1.md`.

#### Numeric and threshold correctness

Where a case requires arithmetic, a threshold decision, or an aggregation, the
authored case must state how correctness is established:

- **objectively derivable expected values** — recomputable from the
  candidate-visible data, with the derivation closed over the visible input
- **factual invariants** — relations that must hold regardless of method, e.g.
  parts sum to the stated total
- **decision rules** — the case supplies the rule, so the correct outcome is a
  function of the visible data plus that rule
- **tolerances** — stated where rounding or floating-point presentation is
  expected

Confirming that *a* number appears is not evidence of arithmetic correctness.
If the existing deterministic framework cannot honestly verify a planned
numeric constraint, that component is marked for judge/reference-based
evaluation rather than presented as deterministic. The per-case plan for
quantitatively grounded slots is recorded in `CASE_MATRIX_V1.md` §7.

---

## 7. Anti-leakage and benchmark quality

- **Do not embed judge scoring language in the user prompt.** The prompt is the
  task; the rubric is not part of the task. Phrases like "score 5 if…" or
  "the judge will check…" must not appear.
- **Supply the facts the candidate needs; withhold the answer.** Any source
  fact required to perform the task belongs in the candidate-visible
  prompt/input. What must not be pre-stated is the deliverable itself: naming
  the answer to be produced turns the case into a transcription test.
- **Avoid answers trivially recoverable from case metadata.** If `title`,
  `tags`, or `expected_structure` give away the content of a correct answer, the
  case measures metadata reading rather than capability.
- **`reference_facts` never introduces new source evidence.** It holds
  normalized copies of visible facts, invariants, and objectively derivable
  ground truth used to check preservation. A fact that is required for a
  correct answer but missing from the visible input is a self-containment bug,
  not something to hide in `reference_facts` (see §3).

---

## 8. Dataset balance

No domain may be dominated by a single output format. Across the final dataset
there must be a healthy mix of:

- prose
- bullet structures
- tables
- JSON / structured outputs
- prioritisation and ranking
- classification and extraction
- executive communication
- decision recommendations
- planning and sequencing

The `CASE_MATRIX_V1.md` document records the expected output shape and
deterministic-check opportunity for every slot, and its Coverage Audit section
reports the resulting distributions. Phase 3B review must confirm that the
authored cases match their planned shape.

---

## 9. Authoring workflow

1. Take a slot from `CASE_MATRIX_V1.md`. Do not invent new slots during authoring.
2. Write the case against the schema in §2.
3. Self-check against §3, §4, §5, §6, §7, and §8.
4. Run `python3 run_benchmark.py --validate-only` — schema and language-rule
   errors must be zero.
5. Have a second reviewer confirm the case tests its planned `test_intent` and
   is distinct from the other nine cases in its domain.
6. Only then does the case enter the production dataset.
