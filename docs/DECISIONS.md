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
