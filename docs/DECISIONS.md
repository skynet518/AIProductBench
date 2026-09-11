# AIProductBench — Decision Log

This is a chronological log of binding project decisions. Each entry records the
date, the decision, the reasoning, the alternatives that were considered, and
the consequences future contributors must live with.

Decisions are appended, never rewritten. If a later decision reverses an earlier
one, the earlier entry stays and the reversal is recorded as a new entry that
references it. Entries must not be backdated to imply a decision existed before
it was actually made.

Dates: the V0.1 scaffold, the V0.1 review, and the V1 reframing all happened on
2026-09-11 in a continuous working session, so entries share that date.

---

## D-001 — Start as a small 10-case / 2-model scaffold
**Date:** 2026-09-11

**Decision.** Begin the project as a deliberately tiny scaffold: 10 test cases,
2 evaluated models, 3 capability domains, 1 LLM-as-Judge.

**Rationale.** The fastest way to learn whether the pipeline is worth building is
to build the smallest one that runs end to end. A large design would have been
unvalidated speculation.

**Alternatives considered.** Designing the full evaluation framework first;
forking an existing benchmark harness; skipping straight to a 10-model run.

**Consequences.** V0.1 is not statistically meaningful and must never be
presented as such. The scaffold is retained in git history as a checkpoint rather
than deleted, because it is the working proof that the pipeline functions.

---

## D-002 — Treat V0.1 as an internal engineering validation, not a product
**Date:** 2026-09-11

**Decision.** V0.1 is an internal engineering scaffold. It is not intended for
public release and makes no public claims.

**Rationale.** A 10-case, 2-model, single-judge comparison cannot support a
public conclusion. Publishing it would trade credibility for speed.

**Alternatives considered.** Shipping V0.1 publicly as a minimal benchmark;
iterating on V0.1 until it was respectable before renaming it.

**Consequences.** V0.1 documentation is superseded. Any artifact produced under
V0.1 is labelled internal or synthetic, never published as a finding.

---

## D-003 — Change the public target to AIProductBench CN V1
**Date:** 2026-09-11

**Decision.** The public portfolio release is a new target, AIProductBench CN
V1, rather than an incremental V0.1.1.

**Rationale.** The scope change is structural: a different dataset size, a
different evaluation design, a different model pool, and a different
presentation. Calling it a patch release would misrepresent the change.

**Alternatives considered.** Continuing V0.1 numbering; shipping V0.1 publicly
and improving in public.

**Consequences.** V1 has its own frozen spec, methodology, architecture, and
decision log. V0.1 remains as a checkpoint and as the source of the working
execution scaffold.

---

## D-004 — Focus on Chinese model selection instead of generic model comparison
**Date:** 2026-09-11

**Decision.** Position the benchmark as a practical model-selection benchmark
for Chinese LLMs, aimed at AI product teams choosing under real quality, cost,
and latency constraints.

**Rationale.** Generic leaderboards already exist and are English-first. The
unmet need is comparable, RMB-native, workload-realistic evidence for the models
a Chinese product team can actually buy.

**Alternatives considered.** A general-purpose multi-vendor benchmark; an
English-first benchmark with a Chinese subset.

**Consequences.** Chinese-first task composition, native Chinese provider APIs,
and RMB as the presentation currency. The benchmark must not claim a permanent
"best Chinese model".

---

## D-005 — Expand from 3 capability domains to 5
**Date:** 2026-09-11

**Decision.** V1 evaluates five domains instead of three:
`instruction_constraint_following`, `structured_information_analysis`,
`product_reasoning_decision`, `chinese_business_communication`,
`agent_workflow_planning`.

**Rationale.** Three domains could not separate the work a Chinese product team
does. Chinese business communication and agent workflow planning were missing
entirely, and both are common production workloads.

**Alternatives considered.** Keeping three domains with more cases each;
domain sets weighted toward coding or general knowledge.

**Consequences.** Domain counts are frozen at 10 cases each. The old three-domain
dataset does not satisfy the V1 schema and is archived rather than extended.

---

## D-006 — Expand the target from 10 tasks to 50
**Date:** 2026-09-11

**Decision.** V1 targets 50 real-world AI product tasks, 10 per domain.

**Rationale.** Ten tasks across five domains gives two tasks per domain, which
cannot distinguish models and cannot be reported honestly per domain.

**Alternatives considered.** 25 cases; 100 cases; adaptive case counts per
domain.

**Consequences.** Dataset construction becomes the largest single work item and
is scheduled as its own phase (Phase 3). Phase 2 builds only the schema and
synthetic fixtures.

---

## D-007 — Adopt hybrid deterministic + LLM evaluation
**Date:** 2026-09-11

**Decision.** Use deterministic checks wherever a constraint is objectively
machine-checkable, and LLM evaluation for judgment-based quality.

**Rationale.** Format, count, ordering, and schema compliance are objective. Handing
them to a probabilistic judge introduces avoidable noise and lets a judge
"reward" a response that violated a hard constraint. LLM judgment is still
required for reasoning quality, which cannot be checked deterministically.

**Alternatives considered.** LLM-only evaluation; deterministic-only evaluation;
human-only evaluation.

**Consequences.** Two quality signals are reported side by side
(`constraint_pass_rate` and rubric score) and neither overrides the other. Every
case must declare `deterministic_checks` where applicable.

---

## D-008 — Reject a single judge for the public V1 methodology
**Date:** 2026-09-11

**Decision.** A single LLM-as-Judge, which was acceptable for the V0.1 scaffold,
is rejected for the public V1 methodology.

**Rationale.** The V0.1 scaffold had one Qwen-family judge scoring a Qwen-family
candidate. That is unauditable: a reader cannot tell how much of the score is
model quality and how much is judge preference. Publishing a single-judge
ranking would overstate confidence.

**Alternatives considered.** Keeping a single judge with a bias disclaimer;
human-only scoring; majority vote across many judges.

**Consequences.** V1 requires two judges per response and publishes judge
agreement. Cost of evaluation roughly doubles, and judge cost is reported
separately so it never inflates candidate cost.

---

## D-009 — Adopt cross-family dual-judge with leave-one-provider-out
**Date:** 2026-09-11

**Decision.** Maintain a judge pool drawn from multiple model families. Each
candidate response is scored by exactly two judges, and no judge may share the
candidate's model family or provider when an alternative exists.

**Rationale.** Cross-family isolation removes the most obvious source of
self-preference bias. Two independent scores let the project measure and publish
agreement rather than asserting reliability.

**Alternatives considered.** Same-family judges with a disclaimer; random judge
selection; fixed judge pairs per run; three or more judges with majority voting.

**Consequences.** Judge availability depends on pool composition. If fewer than
two eligible judges remain for a candidate, the response is recorded as
judge-unavailable instead of being scored by a same-family judge. Target judge
families: Qwen flagship, DeepSeek flagship, GLM flagship.

---

## D-010 — Prefer native provider APIs for the public benchmark
**Date:** 2026-09-11

**Decision.** Reach each model through its native Chinese provider API: Qwen via
Alibaba Model Studio, DeepSeek via the DeepSeek API, Kimi via the Moonshot API,
MiniMax via the MiniMax API, GLM via Zhipu BigModel, and Doubao via Volcano Ark.

**Rationale.** Quality, cost, latency, error behaviour, and rate limits should
reflect a realistic enterprise purchasing and inference path. An aggregated
gateway adds a hop whose latency and margin are not the model's.

**Alternatives considered.** A single aggregated gateway for all models;
mixed native and gateway tracks.

**Consequences.** Each provider needs its own credential and endpoint
configuration. An aggregated gateway track may be added later but must be
labelled separately and must never be mixed into native-provider latency or
economics.

---

## D-011 — Present costs in RMB, preserve native currency
**Date:** 2026-09-11

**Decision.** User-facing cost presentation is RMB / CNY. Native provider
pricing and its currency are preserved alongside the normalized value.

**Rationale.** The target audience buys in RMB. Presenting USD forces every
reader to do their own conversion at an unknown rate and date.

**Alternatives considered.** USD presentation; per-provider native currency with
no normalization; dual-currency columns.

**Consequences.** The pricing system must carry `native_price` and
`native_currency` plus `normalized_cost_cny`. Conversion requires an explicit
dated FX snapshot with a named source. When no FX snapshot is configured, the
CNY value is `null` with a stated reason. A permanent hard-coded conversion rate
is prohibited.

---

## D-012 — Present results as a Pareto frontier, not a rank-only list
**Date:** 2026-09-11

**Decision.** Model selection is presented as a Pareto frontier over quality ×
cost, optionally extended to quality × cost × latency.

**Rationale.** A single ranking answers the wrong question. A cheaper model that
is slightly behind on quality is frequently the correct purchase, and a ranking
hides that. Pareto dominance states plainly which models are never the right
choice and which are defensible under a constraint.

**Alternatives considered.** Rank-only leaderboard; weighted composite score;
per-workload recommendation table only.

**Consequences.** Reports must show dominated models and name the dominating
model rather than hiding them. Composite single-number scoring is not the
primary output.

---

## D-013 — Defer coding, RAG, vision, real tools, and multi-agent evaluation
**Date:** 2026-09-11

**Decision.** Coding, RAG, vision and multimodal input, live web search, real
tool execution, and multi-agent execution are out of scope for V1.

**Rationale.** Each is a substantial evaluation design problem in its own right,
with its own harness requirements. Adding them would either delay V1
indefinitely or produce shallow results for all of them.

**Alternatives considered.** A lightweight coding subset; a RAG smoke test;
tool-calling coverage in V1.

**Consequences.** These items are documented as V1.1/V2 candidates and must not
be implemented while V1 is in development.

---

## D-014 — Treat dataset quality as more important than model count
**Date:** 2026-09-11

**Decision.** When effort must be allocated, improve the dataset before adding
models. The target is approximately 10 models and approximately 6 providers, and
that number may fall rather than rise.

**Rationale.** A benchmark is only as good as its tasks. Adding an eleventh model
to a weak dataset adds a column, not evidence. Model count is also the easiest
quantity to inflate with near-duplicate tiers from the same family, which
produces an illusion of coverage.

**Alternatives considered.** Maximizing model coverage; expanding to more
providers before deepening the dataset.

**Consequences.** Model count is a target, not a commitment. Dropping a model
whose API cannot be pinned or verified is the preferred resolution.

---

## D-015 — Drive the model pool from configuration, not from code
**Date:** 2026-09-11

**Decision.** The candidate pool, judge pool, and pricing metadata are declared
in a JSON configuration file and validated at load time. No benchmark logic may
branch on a specific model or provider name.

**Rationale.** V1 expands from 2 models to approximately 10 across 6 providers.
Model IDs, tiers, and prices change on vendor schedules. Logic that embeds model
names makes every such change a code change and a regression risk.

**Alternatives considered.** Python constants in `config.py`; one module per
provider; a provider class hierarchy.

**Consequences.** Provider differences must be expressible as configuration
fields. A genuinely new wire protocol is handled by one branch in the provider
client, not by a new abstraction layer.

---

## D-016 — Use the standard library `unittest` for the V1 test suite
**Date:** 2026-09-11

**Decision.** V1 framework tests use `unittest` from the standard library.
`pytest` is not added.

**Rationale.** The dependency surface must stay minimal, and the tests here cover
pure functions and deterministic selection logic that `unittest` handles
adequately. A test-runner dependency is not justified by convenience alone.

**Alternatives considered.** Adding `pytest`; no automated tests.

**Consequences.** Tests must be runnable with
`python3 -m unittest discover -s tests -v`. Fixtures are constructed inline
rather than through a pytest fixture system.

---

## D-017 — Keep one shared model registry, with candidate and judge as roles
**Date:** 2026-09-11

**Decision.** V1 maintains exactly one model registry. A model may be both an
evaluated candidate and a judge (`candidate: true`, `judge_eligible: true`). No
judge-only duplicate entry may exist for a model that is already registered as a
candidate. Candidate execution and judge execution are distinct roles over that
one registry, and their metrics are never mixed: candidate inference cost and
judge evaluation cost are separate fields, and candidate latency and judge
latency are separate series.

**Rationale.** The first framework draft registered the Qwen, DeepSeek, and GLM
flagship models twice — once as candidates and again as `judge_*` entries. That
duplicates the same underlying model, creates two sources of truth for one
model's ID, price, and endpoint, and makes it possible for the two copies to
drift apart. It also invites accidental double-counting of cost if the judge
copy is ever counted as a participant.

**Alternatives considered.** Keeping separate judge-only entries for clarity;
introducing a separate judge registry file; allowing either shape and letting
the validator warn.

**Consequences.** The registry shrank from 13 entries to 10, with 3 of them
judge-eligible. The validator now rejects two entries that share a
`model_family` and `product_tier`, which is the shape a duplicate judge copy
takes. Adding a judge means marking an existing entry `judge_eligible`, not
cloning it. Role separation is documented in `ARCHITECTURE.md` §4.

---

## D-018 — Replace hash-rotated judge pairs with fixed-priority selection
**Date:** 2026-09-11

**Decision.** Judge selection uses a fixed priority list declared in
configuration (`qwen_flagship > deepseek_flagship > glm_flagship`), with
leave-one-family/provider-out exclusion and the first two remaining cross-family
judges selected. The earlier candidate-key SHA-256 rotation is removed.

**Rationale.** The hash rotation gave unrelated candidate models different judge
pairs within the same run — for example, one candidate scored by DeepSeek + GLM
and another by Qwen + DeepSeek. That is an avoidable evaluation confound: a
difference between two models could reflect the judges rather than the models.
Rotation was introduced to balance judge usage, which is a smaller benefit than
comparability. Fixed priority is also transparent: a reader can derive the judge
pair for any candidate from configuration alone, without reproducing a hash.

**Alternatives considered.** Keep hash rotation for pool balance; fixed pair for
all candidates; random assignment with a recorded seed; rotating by case index.

**Consequences.** Resulting pairs are Qwen → DeepSeek + GLM; DeepSeek →
Qwen + GLM; GLM, Kimi, MiniMax, Doubao → Qwen + DeepSeek. Because the priority
list has three distinct families and only one can be excluded per candidate, the
selected pair is always cross-family. If fewer than two eligible judges remain,
the response is recorded as judge-unavailable rather than scored by a
same-family judge.

---

## D-019 — Reset active V1 pricing; retire V0.1-era prices to an archive
**Date:** 2026-09-11

**Decision.** All active V1 pricing is reset to unverified. The prices verified
during the V0.1 / Phase 1.5 review are moved into
`historical_pricing_archive` with status `historical_inactive` and are not used
for V1 cost reporting.

**Rationale.** Those prices were verified against specific V0.1-era model IDs
(`qwen3.7-flash-2026-07-15`, `qwen3.7-max-2026-05-20`, `deepseek-v4-flash`) and
had been attached to V1 *tiers* whose literal model IDs are not yet verified.
Carrying a price forward onto a different, unverified model is an inference, not
a fact, and it would let an unverified V1 cost estimate look authoritative. A
V1 price must be verified for the literal V1 model ID.

**Alternatives considered.** Keep the carried-forward prices marked "verified"
with a caveat; keep them as a provisional estimate line; delete them entirely.

**Consequences.** Ten of ten V1 models are unpriced, `--estimate` reports
candidate cost as NOT AVAILABLE, and the paid-run gate now blocks on unresolved
active pricing as well as unverified model IDs. The validator rejects an active
model entry whose pricing references an archived model ID, so archived pricing
cannot silently leak back into a V1 estimate. Historical traceability is
preserved without implying validity.

---

## D-020 — Record the deterministic check count as 18
**Date:** 2026-09-11

**Decision.** The deterministic evaluator implements 18 check types, and every
document that states a count states 18.

**Rationale.** The Phase 2 completion report described "15 check types" while
enumerating 18. The code was audited directly: 18 types are handled by
`_run_check` in `src/deterministic.py`. The mismatch was an error in report
prose, not in the implementation.

**Alternatives considered.** Change the implementation to match the number 15 —
rejected, because the working checks are correct and covering less would be a
regression.

**Consequences.** `METHODOLOGY_V1.md` §2A and `ARCHITECTURE.md` §2 now state the
count and list the types. No check behavior changed.

**Superseded.** The count was raised from 18 to 21 in Phase 3B-1.1; see D-039.

---

## D-021 — Official rankings require equal case denominators
**Date:** 2026-09-11

**Decision.** A candidate model holds an official rank only when it has a valid
scored result for every production benchmark case — for a 50-case dataset,
exactly 50 case-level scores.

**Rationale.** A mean computed over a reduced denominator is not comparable to a
mean computed over the full set. If one model's score silently averages 47 cases
and another's averages 50, any apparent ranking difference is partly an artefact
of which cases happened to fail. Publishing that as a ranking would be
misleading, and the failure would be invisible to the reader.

**Alternatives considered.** Ranking all models on available cases with a
footnote; imputing missing scores; dropping incomplete models entirely and not
reporting them.

**Consequences.** Ranking is now a gate, not just an average. Per-model records
carry `cases_required`, `cases_scored`, `rank_eligible`, and `incomplete_reason`;
the summary carries an `official_ranking` block listing ranked and incomplete
models; the leaderboard shows `INCOMPLETE` instead of a rank. `rank` is `null`
for ineligible models, and ranks stay contiguous across eligible models.

---

## D-022 — Incomplete candidate runs cannot enter the official ranking
**Date:** 2026-09-11

**Decision.** A model that is judge-unavailable, permanently failed, or otherwise
missing a required evaluation result for any case is marked INCOMPLETE. Its
partial results remain visible as diagnostics, but it is excluded from the
official ranking, from the Pareto frontier, and from `ranked_models`.

**Rationale.** The honest response to an incomplete run is to say so. Silently
dropping the case hides a failure; ranking from the remainder misstates
confidence. Keeping the partial numbers visible as diagnostics preserves the
useful information without implying it is comparable.

**Alternatives considered.** Excluding incomplete models from the report
entirely; ranking with a visible warning; retrying indefinitely until a score
exists.

**Consequences.** Partial metrics such as `overall_score` still appear for
incomplete models but carry no rank and no Pareto flags. Cost and latency
diagnostics remain available for debugging. Retry behaviour stays bounded by the
existing provider retry policy; exhaustion produces an explicit incomplete
state rather than an unbounded retry loop.

---

## D-023 — Retain fixed judge pairs and disclose correlated-judge risk
**Date:** 2026-09-11

**Decision.** Keep the fixed-priority judge policy from D-018 unchanged. Kimi,
MiniMax, and Doubao candidates are all scored by Qwen flagship + DeepSeek
flagship. Document correlated-judge bias as a known limitation, and ensure
human calibration sampling explicitly covers Kimi, MiniMax, and Doubao
responses.

**Rationale.** Fixed pairs keep every candidate family comparable, which was the
reason hash rotation was removed. The cost is that three families share the same
two judges: if Qwen and DeepSeek share a systematic bias, those three families'
scores move together. That is a real limitation, but disclosing it is more
honest than reintroducing per-candidate pair variation, which trades a
disclosed, measurable bias for an undisclosed, unmeasurable confound.

**Alternatives considered.** Reintroducing rotation for pool balance; adding a
fourth judge family so tail families get a distinct pair; rotating judge pairs
per domain instead of per candidate.

**Consequences.** Two judges remain sufficient because at most one family is
excluded per candidate. The correlation is named in the methodology limitations
and must appear wherever results are published. Human calibration must sample
Kimi, MiniMax, and Doubao explicitly so the correlated-pair bias can be checked
against human judgment. If a fourth judge family is added later, the priority
list extends without changing the selection rule.

---

## D-024 — Chinese cases cannot use whitespace word-count constraints
**Date:** 2026-09-11

**Decision.** Production cases with `language: "zh"` must use `max_chars` /
`min_chars` for length constraints and must not declare `max_words` /
`min_words`. English cases may use word counts. Mixed-language cases may use
word counts only with an explicit `word_count_justification`. Violations are
validation errors, not warnings.

**Rationale.** The `max_words` / `min_words` checks split on whitespace. Chinese
text is not whitespace-delimited, so a word count on Chinese output measures
segmentation artefacts rather than length. A 200-character Chinese answer can
report as a handful of "words", making the constraint both trivially passing and
meaningless. Character counts are the correct length measure for Chinese.

**Alternatives considered.** Leaving it to author discipline with a documented
recommendation; counting CJK characters as words automatically; dropping length
checks entirely for Chinese cases.

**Consequences.** `src/cases.py` rejects a `zh` case with a word-count check and
requires a justification for `mixed`. Existing fixtures were verified compliant.
Test coverage locks the rule in. Authors writing Chinese cases must express
length budgets in characters, which is also how Chinese writers naturally think
about length.

---

## D-025 — Benchmark case design uses a design-matrix-first workflow
**Date:** 2026-09-11

**Decision.** Production cases are planned as a 50-slot coverage matrix
(`CASE_MATRIX_V1.md`) before any prompt is written, under the rules in
`CASE_DESIGN_STANDARD_V1.md`. Authoring fills planned slots; it does not invent
new ones.

**Rationale.** Writing 50 prompts first and auditing coverage afterwards makes
duplication and gaps expensive to fix: by then the prompts exist and carry
sunk effort that biases the audit toward keeping them. Planning intent, shape,
and difficulty per slot first makes imbalance visible while it is still cheap to
correct, and it makes the distinctiveness of each case an explicit design
decision rather than a retrospective claim.

**Alternatives considered.** Authoring prompts directly and auditing after;
planning only per domain without per-slot intent; generating candidates with a
model and filtering.

**Consequences.** The matrix fixes 5 domains × 10 cases, 2/5/3 difficulty per
domain, and roughly 40 Chinese-first cases, with a recorded output shape and
deterministic-check opportunity per slot. Its Coverage Audit section reports the
actual distributions and the accepted trade-offs. Phase 3B may not silently
change a slot's difficulty, language, or shape.

---

## D-026 — Final production prompts are deferred until matrix review
**Date:** 2026-09-11

**Decision.** Phase 3A produces the design standard and the coverage matrix
only. No production prompt is written until both documents pass external review.

**Rationale.** The matrix is the cheapest artefact to change. Once 50 prompts
exist, editing the plan means editing 50 texts and re-reviewing each. Reviewing
the plan on its own keeps the correction cost proportional to the size of the
evaluation decision.

**Alternatives considered.** Writing prompts alongside the matrix; writing one
domain as a pilot before review.

**Consequences.** The dataset remains empty at the end of Phase 3A. The
framework continues to validate only synthetic fixtures. Any prompt authored
before review cannot be considered part of the production dataset.

---

## D-027 — Cases must be self-contained; `reference_facts` cannot hide source evidence
**Date:** 2026-09-11

**Decision.** Any source fact required to perform a task must be available in
the candidate-visible prompt/input. `reference_facts` may contain normalized
copies of already-visible facts, factual invariants extracted from the visible
material, ground-truth values derivable from candidate-visible data, and grader
metadata used to verify preservation. It must never contain hidden source
evidence required for a correct answer.

**Rationale.** A benchmark that grades a candidate against information the
candidate was never given is measuring clairvoyance, not capability. The earlier
standard said reference facts live in `reference_facts` "not in the prompt",
which could be read as licensing exactly that.

**Alternatives considered.** Allow hidden reference material with a disclosure;
require all facts verbatim in the prompt; drop `reference_facts` entirely.

**Consequences.** A hidden expected answer or derived grader value is acceptable
only when the candidate could derive it from visible input. Deliberately
under-specified cases reward stating the gap, and that behaviour is written into
`evaluation_criteria`. Recorded in `CASE_DESIGN_STANDARD_V1.md` §3 and §7.

---

## D-028 — Do not require private chain-of-thought; judge observable justification
**Date:** 2026-09-11

**Decision.** V1 never requires a candidate to expose private chain-of-thought
and never scores it. Prompts and criteria must not use "show your reasoning",
"step-by-step reasoning", or "transparent reasoning". `reasoning_quality` is
judged from the observable answer and its stated justification: a concise
decision rationale, cited evidence, trade-offs, assumptions, and the basis of a
recommendation.

**Rationale.** Requiring hidden reasoning traces is both unnecessary for
scoring and unreliable to produce. The correct target is a decision-ready
answer whose basis is inspectable in the response the judge actually receives.

**Alternatives considered.** Require an explicit reasoning section; score only
the final answer with no justification; keep "transparent reasoning" as an
informal criterion.

**Consequences.** `CASE_MATRIX_V1.md` IF-06 dropped "transparent reasoning" as a
secondary capability, and `METHODOLOGY_V1.md` §2B states the observable-only
rule. A correct answer with no stated basis is not automatically high-scoring.

---

## D-029 — Audience adaptation preserves facts, not wording (IF-03)
**Date:** 2026-09-11

**Decision.** IF-03 and any comparable audience case require **material factual
claims to remain invariant** — numerical values, dates, named entities,
commitments, and statuses must not change — while wording, terminology,
sentence structure, and information density may change per audience.

**Rationale.** The prior wording ("facts preserved verbatim") described a
copying task and would pass a mechanical duplicate while failing genuine
audience adaptation. The purpose is adaptation without factual drift.

**Alternatives considered.** Verbatim fact preservation; free rewriting judged
only on tone; separate cases per audience.

**Consequences.** Fact preservation is checked on named entities, numbers,
dates, commitments, and statuses, not on literal sentences. This interacts with
D-032, which fixes how the audience difference is scored.

---

## D-030 — Conflict resolution is judged by outcome and precedence, not keywords (IF-06)
**Date:** 2026-09-11

**Decision.** IF-06 evaluates three things: the correct instruction wins
according to the supplied precedence rule, the actual output follows that
winning instruction, and a concise rationale identifies the applicable
precedence. The presence of a literal phrase is not evidence of correct
resolution.

**Rationale.** A required-phrase check can pass while the output obeys the
wrong instruction, and can fail a correct resolution phrased differently. The
capability is what the output does, not how it is worded.

**Alternatives considered.** Keep a required priority-statement phrase;
deterministic-only keyword check; drop the case.

**Consequences.** IF-06's planned deterministic opportunity is `None`; the
matrix's Strong/Partial/None distribution changed accordingly (see D-034).

---

## D-031 — Authority judgment must never reward unsupported speculation (SA-08)
**Date:** 2026-09-11

**Decision.** SA-08 distinguishes **detectable contradiction** (the statements
differ), **resolvable contradiction** (supplied provenance/priority rules settle
it), and **unresolved contradiction** (nothing establishes authority). The
authored case must either provide candidate-visible provenance / priority rules
sufficient to resolve authority, and/or deliberately include conflicts that
cannot be resolved and reward an explicit statement that the conflict is
unresolved. Confident guessing is never rewarded.

**Rationale.** The earlier design rewarded "judgment about which source is
likely authoritative", which invites unsupported speculation when no
information establishes precedence.

**Alternatives considered.** Always supply an authority rule; always leave
authority open; remove the authority component.

**Consequences.** Only the count of detectable contradictions is mechanically
bounded; resolvability and authority are judge-evaluated against the visible
provenance rules or the honest "unresolved" answer.

---

## D-032 — Score audience adaptation against stated roles, not cultural stereotypes (BC-07)
**Date:** 2026-09-11

**Decision.** Remove scoring based on "Chinese hierarchy conventions". BC-07
compares two explicit audience roles — a business-unit / management decision
maker and an execution / project team. The higher-level version emphasizes,
where appropriate, the conclusion, business impact, material risk, and the
decision or resource ask. The execution version emphasizes, where appropriate,
operational context, dependencies, owners, next actions, and implementation
detail. Facts remain invariant. The same anti-stereotype rule applies across
the Chinese business domain: score observable business-communication outcomes,
not vague cultural style.

**Rationale.** "Hierarchy conventions" is not an observable requirement: two
reviewers cannot reliably mark it met or unmet, and it risks rewarding
stereotypes about how Chinese business writing is assumed to work.

**Alternatives considered.** Keep hierarchy-based scoring with a disclaimer;
score only on formatting; drop the two-audience case.

**Consequences.** `CASE_MATRIX_V1.md` domain 4 now carries an explicit
anti-stereotype rule, and BC-03's "hierarchy and politeness" criterion was
replaced with stated-register and question-precision criteria.

---

## D-033 — Retry planning must be side-effect aware (AW-04)
**Date:** 2026-09-11

**Decision.** AW-04 tests side-effect-aware retry planning. The case
distinguishes safe/idempotent read retries, operations whose completion state
is uncertain after a failure, and irreversible or high-impact side effects. The
plan must reason about bounded retries, idempotency, duplicate-side-effect
prevention, verification before retry, and fallback/escalation. No universal
"correct retry count" is assumed unless the prompt explicitly supplies such a
policy.

**Rationale.** Blanket retries are the failure mode the case exists to detect.
The hard judgment is not "how many retries" but whether retrying is safe for
that operation.

**Alternatives considered.** A fixed maximum-retry number as the scoring rule;
a pure error-taxonomy question; dropping the case.

**Consequences.** Deterministic checks may verify that retry budgets are bounded
and required fields exist; the risk judgment stays judge-evaluated. AW-04 moved
from Strong to Partial.

---

## D-034 — Deterministic checks must test the intended constraint, not a proxy
**Date:** 2026-09-11

**Decision.** Add a general rule: a deterministic check must test the intended
constraint, not a superficial proxy. Weak proxies include requiring the word
"risk", requiring a fixed phrase to prove correct prioritisation, and checking
that a number appears without checking the computation. Prefer structural,
exact, enum, count, invariant, or objectively derived checks. Where correctness
cannot be robustly checked mechanically, leave it to case-level criteria and
judges. Audit the planned Strong/Partial labels in `CASE_MATRIX_V1.md` and
downgrade any opportunity relying primarily on keyword presence.

**Rationale.** A weak check is worse than no check: it makes
`constraint_pass_rate` look like evidence while rewarding keyword gaming and
failing correct answers.

**Alternatives considered.** Keep proxy checks with a documented caveat; remove
all content checks; defer the audit to Phase 3B.

**Consequences.** Six planned opportunities changed on audit: IF-01, IF-09,
PR-05, AW-04, and AW-06 moved Strong → Partial, and IF-06 moved Partial → None.
The revised distribution is 14 Strong / 25 Partial / 11 None across the
unchanged 50 slots. No slot count, domain, difficulty, or language target
changed.

---

## D-035 — Quantitative cases must establish how correctness is checked
**Date:** 2026-09-11

**Decision.** Every quantitatively grounded case (SA-03, SA-10, PR-04, PR-05,
PR-06, PR-10) documents how correctness is established: objectively derivable
expected values, factual invariants, stated decision rules, and tolerances
where rounding applies. A number merely appearing is not evidence of
arithmetic correctness. If the deterministic framework cannot honestly verify a
planned numeric constraint, that component is marked for judge/reference
evaluation rather than presented as deterministic. No generic math engine is
built.

**Rationale.** Numeric answers are the easiest place to create a check that
looks rigorous and proves nothing. Closing the derivation over candidate-visible
data is what makes a numeric check meaningful.

**Alternatives considered.** Build a general arithmetic engine; rely on judges
for all numerics; rely on expected-number string matching.

**Consequences.** `CASE_MATRIX_V1.md` §7 records the per-case plan. A small
framework extension — a named-field numeric value check with an explicit
tolerance — is recorded as a Phase 3/4 candidate, not implemented now.

---

## D-036 — Incomplete runs suppress comparative metrics but keep diagnostics
**Date:** 2026-09-11

**Decision.** For an incomplete candidate run, keep diagnostic fields
(`actual_spend_cny`, `calls_completed`, `cases_completed`, partial token usage,
partial latency) and suppress cross-model comparative metrics that require
equal denominators: `cost_per_100_tasks_cny`, `quality_per_cny`, official Pareto
eligibility, and official rank are returned `null`. The report identifies them
as unavailable because the run is incomplete.

**Rationale.** This implements the equal-denominator decision (D-021, D-022)
for the remaining comparative metrics. Cost per 100 tasks and quality per CNY
computed from a reduced run are non-comparable, not approximately comparable.
Suppressing rank but publishing a comparative cost would be internally
inconsistent.

**Alternatives considered.** Publish comparative metrics with a footnote;
scale cost to the planned case count; hide incomplete models entirely.

**Consequences.** The summary carries a `metric_availability` block naming the
comparative metrics, the diagnostic metrics, and the affected models. The
leaderboard renders `n/a — run incomplete` for a suppressed cell. Covered by new
tests in `tests/test_ranking_invariant.py`.

---

## D-037 — Human calibration: base 50 responses plus a risk-based extension
**Date:** 2026-09-11

**Decision.** Replace the rigid "approximately 10%" calibration target with a
base stratified sample of **50 candidate responses** plus a **risk-based
extension of approximately 10–20** responses when warranted, for a practical
review of roughly 50–70. The base sample covers all candidate models, all five
domains, and easy/medium/hard. The extension prioritises hard cases, cases with
no deterministic checks, high Judge A / Judge B disagreement, Kimi / MiniMax /
Doubao responses, responses near close ranking boundaries, and anomalous
failures.

**Rationale.** A flat percentage scales with total response count rather than
with where judge error is likely, and at 10% of a 500-response run it under- or
over-samples the wrong cells. A fixed base guarantees coverage; the risk-based
extension concentrates review where it can change a conclusion.

**Alternatives considered.** Keep 10%; fixed 10% floor with no extension;
sample everything (infeasible).

**Consequences.** The sampling *policy* is frozen in `METHODOLOGY_V1.md` §2D;
executing the sample remains a Phase 3/4 task. No agreement result is
fabricated, and none is published before real human review exists.

---

## D-038 — Gate 3A.1 passed: the design standard and matrix are approved for Phase 3B
**Date:** 2026-09-11

**Decision.** The external Gate 3A.1 review of
`CASE_DESIGN_STANDARD_V1.md` and `CASE_MATRIX_V1.md` passed. Both documents are
approved as the authoritative basis for production case authoring and now carry
the status **APPROVED FOR PHASE 3B AUTHORING**. Phase 3B-1 (domain 1,
`instruction_constraint_following`) is authorized to begin.

**Rationale.** The Phase 3A.1 corrections resolved the review findings:
self-containment and `reference_facts` (D-027), no private chain-of-thought
(D-028), audience adaptation over verbatim copying (D-029), outcome-based
conflict resolution (D-030), authority judgment without guessing (D-031),
observable audience roles (D-032), side-effect-aware retry planning (D-033), the
deterministic-check quality rule and its Strong→Partial audit (D-034),
quantitative correctness planning (D-035), incomplete-run comparative-metric
suppression (D-036), and the base-50 plus risk-based calibration policy
(D-037).

**Alternatives considered.** Approve with follow-up corrections; hold Phase 3B
pending a second review round; approve the matrix but not the standard.

**Consequences.** The approval covers the **design documents only**. It does not
approve the production dataset, any individual case, or any benchmark result.
Authored cases are reviewed per domain before freezing; the 50-case dataset is
not approved until it is complete. Authoring progress and per-domain review
state are tracked in `docs/DATASET_QA_V1.md`. No live paid benchmark is
authorized.

---

## D-039 — Add three generic deterministic operators after production-case review
**Date:** 2026-09-11

**Decision.** Add exactly three generic deterministic operators — 
`section_max_chars`, `section_bullet_count`, and `exact_keys` — and raise the
recorded deterministic operator count from 18 to 21. All documents that stated
the old count now state 21. No other operator is added and no existing operator
changes behavior. No case-specific branch is introduced; the three operators
are generic and reusable.

**Rationale.** The Phase 3B-1 external review of Domain 1
(`instruction_constraint_following`) exposed concrete false-pass risks in three
authored cases:

- IF-03 enforced its per-section 120-character budget with a tolerance-based
  regex. A section padded with whitespace could run over budget and still pass,
  and the regex stopped early if a section body itself contained `【`. A
  section-isolating character count removes the tolerance.
- IF-09's only counting check was an aggregate bullet total. A wrong 4/3/2
  split still summed to 9 and passed. A section-scoped bullet count
  distinguishes the correct 3/4/2 split from a wrong split.
- IF-07 used required keys plus a forbidden-legacy-key list. That combination
  cannot reject arbitrary additional fields, so a response with extra keys
  could pass. An exact key-set check closes the gap.

The operators were introduced **only** in response to that production-case
review and the false-pass risks it exposed; they were not speculative additions.

**Alternatives considered.** Keep the tolerance-based regex and leave the
false-pass gaps in place — rejected, because a check that can pass while the
constraint is violated injects noise into `constraint_pass_rate`. Add
case-specific operators — rejected, because branches keyed to a case ID are not
reusable and violate the generic-check design.

**Consequences.** `src/deterministic.py` implements the three operators,
`METHODOLOGY_V1.md` §2A lists 21 types, and the counts in `README.md`,
`ARCHITECTURE.md`, and `HANDOFF.md` read 21. Six Domain-1 cases (IF-02, IF-03,
IF-06, IF-07, IF-09, IF-10) were replaced with externally authored canonical
definitions that use them. Domain 1 remains **EXTERNAL RE-REVIEW PENDING**; no
domain is approved. This decision records an implementation change only; it does
not approve any case or dataset.

---

## D-040 — Freeze Domain 1 after external final review; external control of remaining case authorship
**Date:** 2026-09-11

**Decision.** The external final review passed on all ten
`instruction_constraint_following` cases (IF-01 through IF-10) after the
Phase 3B-1.2 patches to IF-03 and IF-06. Domain 1 is **FROZEN / EXTERNALLY
APPROVED**. The frozen cases are recorded in `data/cases_v1.json` and the QA
ledger (`docs/DATASET_QA_V1.md`). Production case semantic authorship for the
remaining domains (SA, PR, BC, AW) is **externally controlled**: execution
agents may integrate externally authored canonical case definitions, validate
them, and run them, but must not independently author or redesign them.

**Rationale.** Two review rounds, plus the Phase 3B-1.1 operator additions and
the Phase 3B-1.2 patches, converged on a clean final review with no rejected
cases and no further semantic revision required. Separating semantic authorship
(external) from execution/integration (this project's agents) preserves the
methodology by keeping case design decisions out of the agent that also writes
the checks and runs them.

**Scope.** The approval covers **Domain 1 only**. It does not approve the
50-case dataset, any later domain, any model ID, any price, or any benchmark
result. `data/cases_v1.json` remains `production_status: "authoring"` because
only 10 of 50 cases exist. No live paid benchmark is authorized.

**Consequences.** Domain 1 is committed as the Domain 1 freeze checkpoint
(`feat: freeze instruction-following benchmark cases`). Phase 3B-2
(`structured_information_analysis`) waits for externally authored canonical
SA-01 … SA-10 definitions. DeepSeek agents must not independently author SA
production cases.

---

## D-041 — Freeze Structured Information Analysis after external final review
**Date:** 2026-09-11

**Decision.** The external final review passed on all ten
`structured_information_analysis` cases (SA-01 through SA-10) after the
Phase 3B-2.1 canonical patch round. Domain 2 is **FROZEN / EXTERNALLY
APPROVED**. The frozen cases are recorded in `data/cases_v1.json` and the QA
ledger (`docs/DATASET_QA_V1.md`). The earlier Gate 3B-2 PATCH history is
preserved in the ledger as QA provenance.

The Phase 3B-2.1 patches that closed the review were:

- **SA-05 — provenance rule clarified.** The prompt now requires each `Evidence`
  entry's `[M#]` and quoted text to come from the same message, with the quoted
  span taken as a contiguous verbatim source extract (no rewrites, merges, or
  cross-message stitching). Message IDs stay machine-checked; exact source
  attribution and verbatim contiguity remain judge-evaluated.
- **SA-08 — reporting order made deterministic.** A fixed reporting priority
  (P1事故数 > 已部署版本 > 灰度比例 > 支付转化率) was added solely to determine
  the *output order*. It does not change source authority: the resolution rules
  for version, rollout proportion, and P1 count are unchanged, and the payment
  conversion rate stays unresolved.
- **SA-09 — missing-data plus known-failure interaction.** Vendor D now has both
  a missing security result and a known failed accuracy gate, exercising the
  rule that a known failure yields REJECT even when another required field is
  missing. B and C remain UNDETERMINED and A remains APPROVE.
- **SA-10 — ROUND_HALF_UP plus a real tie-break.** The case now specifies
  decimal ROUND_HALF_UP at the final total and a genuine post-rounding tie
  (B and C both 84.5) broken by the higher quality score, producing the ranking
  C > B > D > A.

**Rationale.** The Gate 3B-2 review found six cases already correct and four
requiring sharper, objectively checkable rules. The Phase 3B-2.1 canonical
patches supplied those rules without expanding the deterministic framework: no
new operator was required and the operator count remains 21.

**Scope.** The approval covers **Domain 2 only**. It does not approve the
50-case dataset, any later domain, any model ID, any price, or any benchmark
result. `data/cases_v1.json` remains `production_status: "authoring"` because
only 20 of 50 cases exist. No live paid benchmark is authorized.

**Consequences.** Domain 2 is committed as the Domain 2 freeze checkpoint
(`feat: freeze structured-analysis benchmark cases`). Phase 3B-3
(`product_reasoning_decision`) proceeds only with externally authored canonical
PR-01 … PR-10 definitions, which execution agents integrate but do not author or
redesign. The same externally controlled semantic authorship applies to the
remaining domains.

---

## D-042 — Freeze Product Reasoning & Decision after external final review
**Date:** 2026-09-11

**Decision.** The final external semantic review passed on all ten
`product_reasoning_decision` cases (PR-01 through PR-10) after the Phase 3B-3.1
canonical patch round. Domain 3 is **FROZEN / EXTERNALLY APPROVED**. The frozen
cases are recorded in `data/cases_v1.json` and the QA ledger
(`docs/DATASET_QA_V1.md`). The earlier Gate 3B-3 PASS/PATCH history and the
Phase 3B-3.1 revision provenance are preserved in the ledger.

**Deterministic vs. judged split.** Objective arithmetic and explicit
constraints remain deterministically checked where appropriate (the
quantitative baselines in PR-04, PR-05, PR-06, and PR-10, plus the supplied
section presence/order checks). Open product recommendations remain
judge-evaluated: **no deterministic hidden winner is permitted for an open
product decision.** In particular, PR-10 does not deterministically require
`A+D` or `A+C+D`.

**Phase 3B-3.1 corrections recorded.** The Gate 3B-3 review found five cases
whose wording admitted unintended readings; the Phase 3B-3.1 canonical full
objects closed each one:

- **PR-01** — the exact-two-feature requirement is now explicit in the
  evaluation criteria, and the author note no longer suggests a preferred
  hidden feature pair.
- **PR-05** — the unit-economics formula now unambiguously subtracts the
  *combined* average monthly infra-and-support cost; the earlier ambiguous
  "average infra + support cost" phrasing was removed. The baseline is
  unchanged: Flat 25920, Usage 21840.
- **PR-06** — engineering effort vs. calendar time is disambiguated: self-build
  earliest usable version is explicitly stated as week 8 with no
  parallel-compression path; the year-1 arithmetic is unchanged.
- **PR-07** — the output structure was made strategy-neutral: the heading is
  now `【风险控制与退出条件】`, and the structure no longer presupposes a
  whitelist Beta as the mandatory strategy.
- **PR-10** — residual engineering capacity now has an explicit competing value
  as an A/D delivery buffer (unused weeks are the only buffer; scheduling C
  consumes it), creating a real buffer-vs-option-value trade-off between A+D
  and A+C+D. The portfolio choice remains judge-evaluated.

**Rationale.** The Gate 3B-3 review found five cases already correct and five
whose wording admitted an unintended reading. The Phase 3B-3.1 canonical
patches supplied authoritative full replacement objects without expanding the
deterministic framework: no new operator was required and the operator count
remains 21.

**Scope.** The approval covers **Domain 3 only**. It does not approve the
50-case dataset, any later domain, any model ID, any price, or any benchmark
result. `data/cases_v1.json` remains `production_status: "authoring"` because
only 30 of 50 cases exist. No live paid benchmark is authorized.

**Consequences.** Domain 3 is committed as the Domain 3 freeze checkpoint
(`feat: freeze product-reasoning benchmark cases`). Phase 3B-4
(`chinese_business_communication`) proceeds only with externally authored
canonical BC-01 … BC-10 definitions; the same externally controlled semantic
authorship applies to BC and AW. Execution agents integrate canonical
definitions but do not author or redesign them.

---

## D-043 — Reopen Domain 3 for Matrix compliance; CASE_MATRIX_V1 is upstream-authoritative
**Date:** 2026-09-11

**Decision.** `CASE_MATRIX_V1.md` (APPROVED) is the **upstream-authoritative**
definition of production slot identity: each slot fixes its capability, output
shape, language, difficulty, and deterministic-opportunity plan. A case that is
semantically well-written but does not occupy its approved slot is not a valid
production case. Following an external audit, Domain 3
(`product_reasoning_decision`) was **reopened** and its ten cases replaced with
externally authored Matrix-compliant canonical definitions (Phase 3B-3R).

**Rationale.** The Phase 3B-3/3B-3.1 PR set passed semantic quality review and
was frozen at commit `e859a6d`, but it had drifted materially from the approved
Domain-3 slot definitions — different slot capabilities, titles, output shapes,
and deterministic plan. **Semantic case quality alone is not sufficient if a
case drifts from its slot.** The matrix is the contract that makes the
50-slot coverage meaningful and comparable, so compliance is a precondition
for freezing, not a nice-to-have.

**History preserved.** Commit `e859a6d` remains an **auditable historical
checkpoint**; Git history was **not** reset, reverted, amended, squashed, or
rewritten. The PR domain was reopened in place, and the superseded definitions
remain recoverable from `e859a6d`. No duplicate or archive copy was added to
`data/cases_v1.json`.

**Matrix-compliant replacement.** The new externally authored PR-01 … PR-10
restore, per slot: working title (`CASE_MATRIX_V1.md` Domain-3 table),
capability, language (8 `zh` / 1 `en` / 1 `mixed`), difficulty (2 easy / 5
medium / 3 hard), output shape, and the deterministic plan (8 Partial / 2 None,
0 Strong). PR-06 and PR-08 declare no deterministic checks. Objective arithmetic
and constraints stay deterministic where appropriate; open product
recommendations, model selection, and model-chosen thresholds remain
judge-evaluated. No winner regex and no hidden canonical threshold was added.
No new deterministic operator was required (count remains 21) and no
methodology or Matrix text was changed.

**Scope.** Domain 3 is **REOPENED — MATRIX COMPLIANCE EXTERNAL REVIEW
PENDING**; PR-01 … PR-10 are **AUTHORED — EXTERNAL REVIEW PENDING**. Domains 1
and 2 remain frozen. The 50-case dataset is not approved and no live paid
benchmark is authorized.

**Consequences.** The replacement stays uncommitted until external semantic +
Matrix review passes, after which Domain 3 is frozen again. **Future domain
authoring must assert Matrix compliance (slot, title, language, difficulty,
shape, deterministic plan) before any semantic freeze.** Matrix compliance is
now covered by a regression test (`tests/test_pr_cases.py`).

---

## D-044 — Matrix Compliance Repair complete; Domain 3 re-frozen
**Date:** 2026-09-11

**Decision.** The Phase 3B-3R Matrix Compliance Repair completed successfully.
The repaired `product_reasoning_decision` set (PR-01 … PR-10) passed **both**
the Matrix Gate and the Semantic Gate, and Domain 3 is **RE-FROZEN /
EXTERNALLY APPROVED**. No further PR semantic change is authorized.

**Slot identity.** `CASE_MATRIX_V1.md` (APPROVED) remains
**upstream-authoritative** for production slot identity. Semantic quality and
Matrix compliance are **separate mandatory freeze gates**: a case that is
semantically well-written but does not occupy its approved slot cannot freeze.

**History.** Historical commit `e859a6d` (the earlier PR freeze) remains intact
and auditable as a superseded checkpoint; Git history was not reset, reverted,
amended, squashed, or rewritten. The repaired definitions are committed as
`fix: align product-reasoning cases with approved matrix`.

**PR-10 role separation.** PR-10 explicitly separates the new-model candidates
(Aster, Birch, Cedar) — which are subject to the new-model hard gates — from
Legacy, which is the current production baseline and feature-flag rollback
target only and is not a new-model candidate. Cedar cannot be a recommendation
or runner-up because it fails the p95 and cost hard gates. Recommended model and
model-chosen rollback thresholds remain judge-evaluated.

**Judge boundary.** Open or subjective judgment is **not** replaced with
keyword or winner proxies. Deterministic checks cover structure and concrete
trigger-field presence only; no winner regex and no hidden threshold was added.
PR-06 and PR-08 remain `deterministic_checks == []`; the operator count remains
21 and no runtime semantics changed.

**Forward requirement for remaining domains.** Every future domain freeze gate
(BC, AW) must verify, in order:

1. **Matrix compliance** — slot, working title, difficulty, language, output
   shape, and deterministic-opportunity plan match APPROVED `CASE_MATRIX_V1.md`.
2. **Semantic quality** — external semantic review passes.
3. **Deterministic / judge boundary** — objective constraints deterministic,
   open judgment judge-evaluated, no winner proxy or hidden canonical answer.
4. **Dataset-wide coverage invariants** — domain counts, difficulty/language
   distributions, and the 50-case target remain consistent.
5. **Runtime / schema validation** — all declarations validate; the offline
   validation commands pass.

**Scope.** This approval covers **Domain 3 only**. Domains 4–5 are not authored,
the 50-case dataset is not approved, and no live paid benchmark is authorized.
Production case semantics remain externally authored; execution agents
integrate canonical definitions and do not author or redesign them.

---

## D-045 — Integrate Domain 4 (Chinese business communication) from approved Matrix slots
**Date:** 2026-09-11

**Decision.** Phase 3B-4 integrated the externally authored canonical
BC-01 … BC-10 into `data/cases_v1.json` (40/50 cases). Authoring began from the
APPROVED `CASE_MATRIX_V1.md` Domain-4 slots, and **Matrix compliance was
asserted before any semantic freeze**, per D-043/D-044. BC is **AUTHORED —
MATRIX + SEMANTIC EXTERNAL REVIEW PENDING**; it is not approved or frozen.

**Communication scoring.** BC follows **explicit-role / observable-outcome**
communication scoring: audience adaptation is driven only by the work
responsibilities stated in the prompt. **No generalized Chinese
hierarchy/deference (or personality/power-distance/cultural) stereotype is
scored.** BC-07 encodes this explicitly (business-unit decision maker vs.
project execution team) and is covered by an anti-stereotype regression test.

**Deterministic / judge boundary.** The supplied deterministic plan is
3 Strong (BC-01, BC-02, BC-10) / 4 Partial (BC-04, BC-05, BC-07, BC-08) /
3 None (BC-03, BC-06, BC-09). **BC-03, BC-06, and BC-09 intentionally remain
judge-only** (`deterministic_checks == []`); no checks were added to them, and
no semantic proxy checks were introduced. The operator count remains 21 and no
runtime semantics changed.

**Consequences.** The BC definitions are uncommitted pending external Matrix +
Semantic Gate Review. IF/SA/PR remain frozen / externally approved. Domain 5
(AW) is not authored. The 50-case dataset is not approved and no live paid
benchmark is authorized. Production case semantics remain externally authored;
execution agents integrate canonical definitions and do not author or redesign
them.

---

## D-046 — Freeze Chinese Business Communication after Matrix, Semantic, and Deterministic-contract Gates
**Date:** 2026-09-11

**Decision.** Chinese Business Communication (BC-01 … BC-10) passed the final
Matrix Gate, Semantic Gate, and **Deterministic-contract Gate**, and Domain 4 is
**FROZEN / EXTERNALLY APPROVED**. No further BC production-case semantic change
is authorized. The Phase 3B-4 / 3B-4.1 provenance (initial Matrix-compliant set,
7 PASS / 3 PATCH, deterministic-contract repair) is preserved in the QA ledger.

**Deterministic-contract repairs recorded.** The Phase 3B-4.1 round replaced the
three PATCH cases:

- **BC-01** and **BC-10** key-figure checks are **surface-order independent**:
  each required number/date is a separate presence check, so a correct answer
  that reorders the numbers is not falsely failed.
- **BC-04**'s user-visible no-jargon instruction is now response-wide and
  matches its `forbidden_phrases` checker exactly, removing the earlier
  prompt/checker scope mismatch.

**Judge boundary.** Communication semantics — factual direction (rise/fall),
responsibility assignment, relationship preservation, and stakeholder framing —
remain **judge-evaluated** where a mechanical check would become proxy scoring.
No winner regex or hidden canonical wording was added; the deterministic plan
remains 3 Strong / 4 Partial / 3 None, with BC-03, BC-06, and BC-09 intentionally
`deterministic_checks == []`.

**BC-07.** Audience adaptation uses **explicit organizational responsibilities
only** (business-unit decision maker vs. project execution team). The benchmark
does **not** score generalized Chinese hierarchy, deference, personality,
power-distance, or cultural stereotypes, and this is enforced by an
anti-stereotype regression test.

**Forward requirement for Domain 5.** The AW freeze must pass, in order:

1. **Matrix compliance** — slot, working title, difficulty, language, output
   shape, and deterministic-opportunity plan match APPROVED `CASE_MATRIX_V1.md`.
2. **Semantic quality** — external semantic review passes.
3. **Deterministic / judge boundary** — objective constraints deterministic,
   open judgment judge-evaluated, no winner proxy or hidden canonical answer.
4. **Dataset-wide coverage invariants** — domain counts, difficulty/language
   distributions, and the 50-case target remain consistent.
5. **Runtime / schema validation** — all declarations validate; the offline
   validation commands pass.

**Scope.** This approval covers **Domain 4 only**. Domain 5 (AW) is not
authored, the 50-case dataset is not approved, and no live paid benchmark is
authorized. Production case semantics remain externally authored; execution
agents integrate canonical definitions and do not author or redesign them.

---

## D-047 — Integrate Domain 5 (Agent Workflow Planning) from approved Matrix slots
**Date:** 2026-09-11

**Decision.** Phase 3B-5 integrated the externally authored canonical
AW-01 … AW-10 into `data/cases_v1.json`, completing **all 50 of 50 authored
production slots**. Domain 5 was authored from the APPROVED
`CASE_MATRIX_V1.md` Domain-5 slots (2 easy / 5 medium / 3 hard; 7 zh / 1 en /
2 mixed; 2 Strong / 3 Partial / 5 None). AW is **AUTHORED — MATRIX + SEMANTIC
EXTERNAL REVIEW PENDING**; it is not approved or frozen.

**Planning only.** The AW domain is a planning benchmark: it evaluates
decomposition, tool selection, dependency ordering, retry safety, permission
boundaries, approval gates, parallelism, data contracts, stopping/budgets, and
missing-input escalation. It performs **no real tool execution, no code task, no
multi-agent implementation, and no network/model/API call**.

**Key semantic invariants.**

- **AW-04** retry handling is **side-effect-aware** (safe read vs. write with
  uncertain completion vs. customer-visible send) and does **not** assume a
  universal retry count; retry-count appropriateness remains judge-evaluated.
- **AW-05** separates technical tool availability from business **authority**;
  the boundary is judged by consequence and permission, not by a keyword
  classifier.
- **AW-08** tests explicit inter-tool **data contracts** (8 fields plus
  validation and mismatch handling).
- **AW-09** tests **termination and budget** discipline (call/time/cost budgets,
  information gain, conflict escalation).
- **AW-10** tests **stop-and-escalate** behaviour when a required input is
  missing, rather than guessing defaults.
- **AW-02, AW-05, AW-07, AW-09, AW-10** intentionally remain judge-only.

**Recorded divergence (not fixed here).** `CASE_MATRIX_V1.md` lists IF-06 as a
deterministic "None" slot, but the frozen IF-06 approved in Phase 3B-1.2 carries
four structural checks, so it realizes as a Partial. The dataset therefore has
**10** `[]` cases rather than the Matrix's planned 11. This is a pre-existing
IF-domain artifact; frozen IF semantics were not edited in this phase. The
discrepancy is recorded in `docs/DATASET_QA_V1.md`.

**Scope.** No domain is approved by this decision beyond what was already
approved (Domains 1–4). AW awaits external Matrix + Semantic review; the 50-case
dataset is not production-frozen and no live paid benchmark is authorized.
Production case semantics remain externally authored; execution agents
integrate canonical definitions and do not author or redesign them.

---

## D-048 — Correct D-047's detected defect: restore IF-06 to the approved None contract
**Date:** 2026-09-11

**Decision.** The Phase 3B-5 audit's **14 Strong / 26 Partial / 10 None** realized
distribution was a **detected defect, not a new approved benchmark design.**
`CASE_MATRIX_V1.md` remains **upstream-authoritative** for deterministic-plan
identity. IF-06 must be **None**, exactly as approved by the Phase 3A.1
deterministic-quality audit (which changed IF-06 Partial → None because correct
conflict resolution is judged from which instruction wins, whether the output
follows the winner, and whether the stated precedence basis is correct, rather
than from mechanical proxy evidence).

**Repair.** Phase 3B-5R replaced IF-06 with the externally authored canonical
object whose `deterministic_checks == []` (Matrix-approved judge-only None
case). IF-06's prompt, evaluation criteria, reference facts, difficulty,
language, and title are unchanged; the other 49 production cases were not
modified. This restores the approved **14 Strong / 25 Partial / 11 None**
distribution (IF 4/5/1, SA 5/5/0, PR 0/8/2, BC 3/4/3, AW 2/3/5). **No Matrix
amendment was made** — the data was repaired to match the Matrix.

**Frozen status is not absolute.** This repair establishes that a **frozen
status does not prevent reopening a case when a higher-level specification
violation is discovered.** Domain 1 was reopened solely for this IF-06
deterministic-plan repair and remains
**REOPENED — IF-06 MATRIX COMPLIANCE EXTERNAL RE-REVIEW PENDING**; IF-06 is
**REVISED — MATRIX COMPLIANCE EXTERNAL RE-REVIEW PENDING**. Domain 5 (AW) remains
**AUTHORED — MATRIX + SEMANTIC EXTERNAL REVIEW PENDING**.

**Forward requirement.** **All future final dataset gates must compare the
realized deterministic level of each case against `CASE_MATRIX_V1.md`, not only
validate that checker declarations are well-formed.** Declaration validation
alone cannot catch a case whose realized deterministic strength drifted from its
approved slot. `tests/test_aw_cases.py` now covers per-domain and global
deterministic distributions against the Matrix.

**Scope.** No benchmark design change, no Matrix change, and no live paid
benchmark authorization. Production case semantics remain externally authored;
execution agents integrate canonical definitions and do not author or redesign
them.

---

## D-049 — Final V1 production dataset freeze (50 cases)
**Date:** 2026-09-11

**Decision.** AIProductBench CN V1 production case authoring is **complete**.
All 50 Matrix slots are authored across the five domains (10 each); all five
domains passed Matrix + Semantic review, with the deterministic/judge boundary
audited separately. The full 50-case dataset passed the Matrix, Semantic,
Deterministic-contract, and global coverage/invariant Gates with
**50 PASS / 0 PATCH / 0 REJECT**, and is **FROZEN / EXTERNALLY APPROVED** for
production. `data/cases_v1.json` `production_status` is set to the
already-supported production-ready value `"complete"` (no schema change).

**Final distributions.** Deterministic level **14 Strong / 25 Partial / 11
None**; language **40 zh / 6 en / 4 mixed**; difficulty **10 easy / 25 medium /
15 hard**; 50 cases, 10 per domain; 21 deterministic operators (unchanged, no
runtime change). The eleven None cases are IF-06, BC-03, BC-06, BC-09, PR-06,
PR-08, AW-02, AW-05, AW-07, AW-09, AW-10 (each `deterministic_checks == []`).

**Repairs folded into the freeze.** The IF-06 historical deterministic-plan
drift was repaired to the upstream Matrix None contract (Phase 3B-5R), and the
AW-03 (unique-label execution plan; A/B/C one parallel batch; letters-only
critical path) and AW-04 (digits-only retry-budget cell; no universal retry
count) deterministic contracts were repaired before freeze (Phase 3B-5.1).

**Immutable baseline.** The 50-case semantic freeze manifest
(`docs/DATASET_FREEZE_V1.md`) is now the **immutable V1 case baseline**;
aggregate SHA-256 `6b450383e528a5a0a6b813112f96182a3625c04c948839fc551c8ded63da513c`.
`tests/test_dataset_freeze.py` permanently pins the manifest, per-case hashes,
Matrix slot identity, global distributions, and the deterministic/judge
boundary.

**Any future semantic case modification requires**, in order:

1. an **explicit versioned reopening** (a new dataset version);
2. **Matrix compliance review** against the upstream `CASE_MATRIX_V1.md`;
3. **semantic review**;
4. **deterministic / judge-boundary review**;
5. a **new freeze hash**.

**Known documentation-level divergence (recorded, not a blocker).** 43 of the 50
frozen case titles equal the `CASE_MATRIX_V1.md` working titles; seven frozen
IF/SA cases (IF-01, IF-02, IF-04, IF-09, IF-10, SA-01, SA-08) carry their own
externally approved display titles. Identifiers, domains, difficulty, language,
and deterministic level match the Matrix for all 50 cases. Frozen case titles
were **not** edited in this checkpoint.

**Scope.** This decision freezes the **production case set only**. It does not
verify model IDs, pricing, an FX snapshot, or credentials, and it does not
authorize a paid run. No live paid benchmark has been authorized. Model,
provider, pricing, and judge work may proceed without changing the frozen case
set; frozen production cases must not be modified by provider/runtime work.

---

## D-050 — Phase 4A readiness: extend the registry contract and audit live-readiness offline
**Date:** 2026-09-11

**Decision.** Phase 4A (Live Benchmark Readiness) began with a read-only audit of
the model registry, provider adapter, pricing/FX architecture, judge mapping,
incomplete-model handling, and run-manifest shape (`docs/PHASE4A_READINESS_AUDIT.md`).
No network/provider/model call was made, and the frozen 50-case dataset was not
touched (semantic manifest SHA-256 unchanged:
`6b450383e528a5a0a6b813112f96182a3625c04c948839fc551c8ded63da513c`).

**Registry contract extension (backward-compatible).** The registry could not yet
represent the full Phase 4A contract, so four optional/additive fields were added:
`enabled`, `thinking_config`, and `model_id_verified_as_of` per model, plus
`reasoning` and `cached_input` per pricing block. All default to `true`/`null`
and no existing consumer changes. `src/models.py` validates them when present
(and requires `model_id_verified_as_of` once a model is marked verified).
`config.FX_SNAPSHOT` / `SYNTHETIC_FX_SNAPSHOT` gained a `snapshot_id`. New offline
validators `pricing.validate_fx_snapshot` and `pricing.validate_pricing_snapshot`
pin the snapshot contracts. **No literal model ID and no price was filled in.**

**Verified compliant (no change needed).** Judge selection reproduces the frozen
cross-family mapping exactly (Qwen→DeepSeek+GLM; DeepSeek→Qwen+GLM;
Kimi/MiniMax/GLM/Doubao→Qwen+DeepSeek), with no same-family judge, exactly two
judges, and judge-unavailable when fewer than two eligible judges remain.
Incomplete-model accounting already suppresses normalized/comparative metrics and
official ranking while retaining raw spend, calls, cases, tokens, and latency
diagnostics.

**Identified gaps (not implemented in this phase).** The run document lacks
`dataset_manifest_hash`, `git_commit`, a registry-snapshot ID, `pricing_snapshot_id`,
`fx_snapshot_id`, an explicit `start_time`, and an environment/runtime-version
block; `thinking_config` is in the registry but not yet echoed into per-candidate
run records. These are documented design items for the next Phase 4 step, not a
broad redesign.

**Scope.** Still no verified model ID, no verified price, no FX snapshot, and no
provider credentials; no paid/live call is authorized. Model, provider, pricing,
and judge work may proceed without changing the frozen case set.

---

## D-051 — Phase 4B/C: lock official model IDs, pricing, FX, and execution config offline
**Date:** 2026-09-11

**Decision.** The ten logical V1 slots are locked to verified literal provider
model IDs (`as_of` 2026-09-11): `qwen3.8-max` / `qwen3.8-flash` (Qwen, China
Beijing), `deepseek-v4-pro` / `deepseek-v4-flash` (DeepSeek), `kimi-k3` /
`kimi-k2.6` (Kimi/Moonshot), `MiniMax-M3`, `glm-5.3` / `glm-5.3-flash` (Z.AI),
`doubao-seed-2-1-pro-260628` (Volcano Ark). **Kimi flagship is `kimi-k3`; Kimi
value is `kimi-k2.6`.** Endpoints: Qwen
`https://dashscope.aliyuncs.com/compatible-mode/v1` (Beijing — must stay paired
with Beijing pricing), DeepSeek `https://api.deepseek.com`, Kimi
`https://api.moonshot.ai/v1`, MiniMax `https://api.minimax.io/v1`, GLM
`https://api.z.ai/api/paas/v4`, Doubao
`https://ark.cn-beijing.volces.com/api/v3`. No eleventh model was added.

**No universal temperature override.** The global `temperature = 0.0` requirement
was removed from the registry schema, validator, and provider adapter. Sampling
is sent only when a model's `request_config` explicitly specifies it, so every
model keeps provider-default/recommended reasoning behavior: Qwen thinking via
`enable_thinking`; DeepSeek `reasoning_effort=high` with no temperature/top_p;
Kimi K3 `reasoning_effort=max`, Kimi K2.6 preserves provider defaults (temp 1.0 /
top_p 0.95); MiniMax adaptive with `reasoning_split=true`; GLM provider-default
sampling; Doubao provider defaults (no invented `reasoning_effort`). Effective
request config is inspectable and recorded per candidate in the run manifest.

**Immutable snapshots.** Pricing snapshot `v1-pricing-2026-09-11` (`as_of`
2026-09-11, content SHA-256
`3d03267601e2978f664408543dd97094f0c2bb3c1284958951915662af3ce1b6`), with native
prices (USD except Doubao CNY), DeepSeek peak/off-peak tiers selected from the
request timestamp (never averaged), MiniMax context tiers using the current
payable rate, GLM cached-input as limited-time free, and Doubao cache storage
recorded but uncounted unless a stored cache is created. Fixed FX snapshot
`ecb-2026-09-10-usd-cny` (ECB EUR/USD 1.1616, EUR/CNY 7.7900 → USD/CNY
`6.706267217630854`). Registry snapshot `v1-registry-2026-09-11` (content SHA-256
`5a0175a3e1879ec5f7cdfcd0fbc46a1ab7b838602ad536f7a552dd67f8c01970`, no
credentials).

**Run manifest gaps closed.** The run document now records
`dataset_manifest_hash`, `git_commit`, registry/pricing/FX snapshot ids + hashes,
`judge_config_snapshot_id`, `start_time`, and a runtime/environment block, plus
per-candidate logical/provider ids, thinking/request config, pricing record,
case counts, judge availability, input/output/reasoning/cached tokens, native
and CNY spend, and latency diagnostics. Usage normalization reads cached-input
tokens only when the provider exposes them and returns null otherwise.

**Historical archive.** The retired V0.1 entry previously labelled
`deepseek-v4-flash` was relabelled `deepseek-v4-flash-v0.1-review` (original id
preserved in its notes) so it cannot collide with the V1 model id
`deepseek-v4-flash`; its retired prices are unchanged and remain excluded from V1
cost.

**Scope.** No live/provider/model/network call was made. Model IDs are verified
and pricing is resolved, but provider credentials are still absent, official
source URLs still need confirmation, and no paid-run authorization has been
given. The next step is a controlled live smoke test; the full candidate+judge
benchmark run is **not** authorized. The frozen 50-case dataset is unchanged.

---

## D-052 — Phase 4D.1: MiniMax-M3 migration to MiniMax China (domestic) + DeepSeek output budget
**Date:** 2026-09-11

**Decision.** The MiniMax benchmark MODEL is unchanged and remains exactly
`MiniMax-M3`; this supersedes only the *execution route* locked in D-051. The
candidate moved from the MiniMax International route to the **MiniMax China
domestic official Open Platform**: provider `MiniMax China`, provider key
`minimax_china`, region `cn-domestic`, host `api.minimaxi.com`, text-generation
path `/v1/text/chatcompletion_v2` (no `/chat/completions` suffix appended). The
path is expressed as a new config-driven `chat_completions_path` field in the
model pool so the provider adapter still contains no provider-specific
branching. The international-only `reasoning_split` extension was dropped;
MiniMax-M3 now runs on provider-default reasoning behavior
(`thinking_mode = provider_default`).

**Pricing.** The active V1 MiniMax-M3 pricing record is replaced with the
current China domestic CNY pay-as-you-go rates (as_of 2026-09-11, per 1M tokens,
native CNY → normalization 1.0): input context ≤ 512K → input 2.1 / output 8.4 /
cached_input 0.42; input context > 512K and ≤ 1M → input 4.2 / output 16.8 /
cached_input 0.84. No separate reasoning-token price is recorded because the
provider does not expose one. The retired international USD pricing is **not
deleted**: it is preserved inside the MiniMax entry as `superseded_provider_route`
(`historical_inactive`) for provenance, and the V0.1-era `historical_pricing_archive`
is untouched.

**Snapshots.** Registry snapshot `v1-registry-2026-09-11.1` and pricing snapshot
`v1-pricing-2026-09-11.1` were recomputed. The registry snapshot now records
`chat_completions_path` so the domestic route is explicit. The dataset version,
dataset semantic manifest, case hashes, judge mapping, and every other
model/provider pricing record are unchanged.

**DeepSeek runtime output budget.** The AW-04 diagnostic showed both DeepSeek
models returning HTTP 200 with `finish_reason = length`, empty final content,
and the entire 2048-token budget consumed by reasoning (reasoning_content 3514 /
3477 chars, 2048/2048 reasoning tokens). This is case A (reasoning exhausted the
generation budget). Only the DeepSeek runtime output budget was raised to a
bounded 8192 (`max_output_tokens` and `request_config.max_output_tokens`); no
sampling parameter, model ID, price, or judge mapping changed. A single AW-04
rerun per DeepSeek model then returned final content (554 and 593 chars) with
reasoning + cached token fields captured.

**Scope.** Targeted blocker-clearance probes only, under a 20 CNY phase ceiling;
no full smoke rerun and no 50-case benchmark. The frozen 50-case dataset is
unchanged.

---

## D-053 — Phase 4D final: live runtime validated (Qwen judge route + checkpoint)
**Date:** 2026-09-11

**Decision.** Close Phase 4D as COMPLETE on live-runtime evidence. The Phase 4D
controlled live smoke is recorded as **PASS**: all six candidate providers have a
verified live candidate path and both frozen cross-family dual-judge routes have
produced 2/2 valid verdicts. The full 50-case paid benchmark remains
**READY but NOT executed and NOT authorized**.

**What was verified live in the final checkpoint.**

- *Qwen executor auth:* re-verified inside the execution process (HTTP 200 from
  the Beijing DashScope compatible endpoint). Credential values were never
  printed or written to any artifact.
- *Qwen candidates:* `qwen3.8-max` and `qwen3.8-flash` each ran frozen IF-07
  exactly once and returned `PROBE_PASS`: HTTP 200, literal model ID echoed back
  verbatim, `enable_thinking=true` accepted, final content returned, usage and
  reasoning-token counts captured, cached-input tokens captured (0), latency
  recorded, native USD cost resolved, CNY cost resolved through the fixed ECB FX
  snapshot, and 8/8 deterministic checks executing.
- *Judge route Qwen + DeepSeek:* PASS on the **stored** MiniMax-M3 China IF-07
  candidate response (no candidate regeneration). `qwen3.8-max` and
  `deepseek-v4-pro` each returned a valid structured verdict, 2/2, with the
  requested route matching the frozen route exactly.
- *Judge route DeepSeek + GLM:* PASS on the stored Qwen IF-07 candidate
  response, 2/2 valid verdicts, frozen route matched.

**Why the Qwen judge route was proved on a MiniMax candidate.** The first Phase
4D smoke reached the judge stage for Kimi and Doubao candidates but persisted
only response lengths, never response text, and no 4D.1 probe artifact exists for
those models. Reusing a stored MiniMax-M3 China IF-07 response was therefore used
instead: every non-Qwen, non-DeepSeek, non-GLM candidate family — Kimi, MiniMax,
GLM and Doubao alike — maps to the identical frozen judge route
`qwen_flagship > deepseek_flagship` (D-051). The route proved is the exact route
those candidates receive; the candidate source substitution was explicitly
authorized for this step, and no judge was substituted.

**Cost.** The final checkpoint made 2 paid calls for 0.05768222 CNY. The Phase
4D.1 + 4D probe ledger stands at 0.36870636 CNY in total, far below the 20 CNY
phase ceiling and below the 2 CNY checkpoint ceiling.

**Failure history preserved.** The first controlled live smoke did **not** pass:
Qwen was rejected with HTTP 401 (invalid API key), MiniMax and GLM were rejected
as unbilled, and DeepSeek returned empty content because reasoning exhausted the
2048-token budget. Those failures remain recorded in the Phase 4D / 4D.1 results
artifacts and are not to be rewritten. D-052 records the MiniMax China migration
and the DeepSeek bounded 8192 output-token budget that cleared them.

**Snapshots.** Active registry `v1-registry-2026-09-11.1`
(`c339688f35c653c079a50c0a5477287168e12e82bee710387d1b67ad4fb63899`) and active
pricing `v1-pricing-2026-09-11.1`
(`9f7af42243e5e0b78b1776934de5483f0e3e650765a19dd929e78af10aa15c42`) match the
recomputed canonical hashes exactly. The MiniMax China migration and the
DeepSeek output-budget change are both captured inside the `.1` snapshot
revision, so no further hash recomputation was required.

**Scope.** Targeted probes and offline regression only; no 50-case benchmark, no
leaderboard, no Pareto ranking. The frozen dataset is unchanged (manifest
`6b450383e528a5a0a6b813112f96182a3625c04c948839fc551c8ded63da513c`), the judge
mapping and rubric are unchanged, and no credentials or result artifacts are
committed.
