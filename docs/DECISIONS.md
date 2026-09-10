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
