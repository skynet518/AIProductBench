# AIProductBench CN V1 — Case Coverage Matrix

**Status: APPROVED FOR PHASE 3B AUTHORING (Gate 3A.1 passed). The production
dataset itself is not approved; no production prompt has been written yet.**

This document plans all 50 production case slots before authoring begins. It
contains no final user prompts, only the planned intent, shape, and coverage for
each slot. Phase 3B fills these slots; it does not invent new ones.

Authoring rules live in `CASE_DESIGN_STANDARD_V1.md`. Evaluation design lives in
`METHODOLOGY_V1.md`.

---

## 1. Matrix rules

| Rule | Value |
| --- | --- |
| Total slots | 50 |
| Domains | 5 |
| Cases per domain | Exactly 10 |
| Difficulty per domain | Exactly 2 easy / 5 medium / 3 hard |
| Languages | Approximately 40 `zh`, approximately 10 `en` / `mixed` |
| Production prompts | **Not written in this phase** |

ID prefixes: `IF` instruction_constraint_following, `SA`
structured_information_analysis, `PR` product_reasoning_decision, `BC`
chinese_business_communication, `AW` agent_workflow_planning.

Each slot records: planned ID, working title, domain, difficulty, language, test
intent, primary capability, secondary capability, expected answer shape,
deterministic check opportunity, key evaluation focus, and why it is meaningfully
different from the other nine cases in its domain.

---

## 2. Domain 1 — `instruction_constraint_following`

Required coverage: formatting constraints, inclusion/exclusion constraints,
multi-part instructions, resolvable conflicting instructions, clarification
instead of unjustified execution, fact preservation under format transformation,
output-length constraints, audience adaptation under fixed facts. Not all ten
cases are JSON or schema tests.

### Slots

| ID | Working title | Diff | Lang | Expected shape | Deterministic opportunity |
| --- | --- | --- | --- | --- | --- |
| IF-01 | 混乱需求改写为三条问题陈述 | easy | zh | Bullets | Partial — exact bullet count only; "no solution named" judged |
| IF-02 | Constrained release notes | easy | en | Prose + bullets | Strong — required prefix, bullet count, word cap, banned words |
| IF-03 | 一次事实，三种受众 | medium | zh | Labeled prose sections | Partial — section labels, per-section char caps |
| IF-04 | 澄清而不是直接开工 | medium | zh | Two numbered questions + one line | Partial — exact question count, banned words, no-work constraint |
| IF-05 | 会议纪要到行动项表 | medium | zh | Table | Strong — row count, column headers, no-invented-owner |
| IF-06 | 冲突指令的优先级判定 | medium | zh | Prose + applied instruction | None — outcome and precedence rationale judged |
| IF-07 | 输出格式契约 | medium | zh | JSON | Strong — JSON validity, exact keys, enum values, no fence |
| IF-08 | 长文压缩到固定预算 | hard | zh | Ordered prose sections | Strong — char cap, section ordering, all key figures present |
| IF-09 | 多部分指令与内部冲突 | hard | mixed | Prose + bullets | Partial — per-part counts; conflict resolution judged |
| IF-10 | 硬性否定约束下的重写 | hard | zh | Prose | Partial — banned word list, banned structure |

### Slot detail

**IF-01** — *Test intent:* verify exact-count and negative-constraint obedience on
a minimal transformation task. *Primary:* format constraint adherence.
*Secondary:* fact extraction from messy input. *Eval focus:* exactly three
bullets, nothing else, and no solution proposed. *Deterministic scope:* the
bullet count (plus a no-extra-content structural check) is mechanically tested.
Whether the model proposed a solution is judged, not matched against a keyword
list. *Distinct from the other nine:* the baseline case; only one formatting
rule plus one exclusion rule, with no reasoning load.

**IF-02** — *Test intent:* obey several simultaneous simple constraints in
English. *Primary:* multi-constraint obedience. *Secondary:* tone control. *Eval
focus:* required prefix, exactly three bullets, word ceiling, banned-word list,
second person. *Distinct:* the only English easy case, and the only one using a
required literal prefix plus a word ceiling together.

**IF-03** — *Test intent:* transform one fact set for three audiences without
altering any material fact. *Primary:* audience adaptation under fixed facts.
*Secondary:* length control. *Eval focus:* material factual claims stay
invariant across all three sections — numerical values, dates, named entities,
commitments, and statuses must not change — while wording, terminology,
sentence structure, and information density may change to suit each audience.
Section labels are exact and per-section ceilings hold. This is audience
adaptation without factual drift, not verbatim copying. *Distinct:* the only
case requiring three parallel renderings of the same input.

**IF-04** — *Test intent:* ask for clarification instead of executing an
under-specified request. *Primary:* refusing unjustified execution.
*Secondary:* question quality. *Eval focus:* exactly two questions, one
assumption line, no plan or draft produced. *Distinct:* the only case where
producing the requested artefact is a failure.

**IF-05** — *Test intent:* convert unstructured meeting notes into a fixed table
without inventing data. *Primary:* format transformation into a table.
*Secondary:* non-invention. *Eval focus:* exact column set, row count, owners
only where stated. *Distinct:* the only table-output case in this domain.

**IF-06** — *Test intent:* resolve two mutually conflicting instructions using a
priority rule stated in the prompt. *Primary:* conflict resolution with stated
precedence. *Secondary:* observable decision rationale. *Eval focus:* the
correct instruction wins according to the supplied precedence rule, the actual
output follows that winning instruction, and a concise rationale identifies the
applicable precedence. Evaluation is decided by which instruction the output
obeys and the stated basis, not by the presence of a literal phrase.
*Deterministic scope:* none — this is a judge-evaluated outcome (see §7).
*Distinct:* the only case with a genuine internal contradiction to resolve.

**IF-07** — *Test intent:* emit a strict serialization contract when the input is
already structured. *Primary:* schema obedience. *Secondary:* enum discipline.
*Eval focus:* valid JSON, exact keys, allowed enum values, no prose or fences.
*Distinct:* requires no analysis at all — it isolates format obedience, unlike
the extraction cases in the structured domain.

**IF-08** — *Test intent:* compress a long source to a hard length budget while
losing no key information. *Primary:* information-preserving compression.
*Secondary:* section ordering. *Eval focus:* every key figure retained, ceiling
respected, required order kept. *Distinct:* the only case where the binding
constraint is a budget rather than a format.

**IF-09** — *Test intent:* handle a multi-part deliverable whose parts carry
conflicting constraints. *Primary:* multi-part instruction tracking.
*Secondary:* conflict handling. *Eval focus:* every part present, conflict
acknowledged, stated precedence honoured. *Distinct:* the only mixed-language
case here, and the only one combining multi-part counting with a conflict.

**IF-10** — *Test intent:* rewrite under a dense load of negative constraints.
*Primary:* negative-constraint obedience. *Secondary:* meaning preservation.
*Eval focus:* no banned vocabulary, no banned rhetorical structure, meaning
unchanged. *Distinct:* the densest exclusion load in the domain, and the only
case banning a *structure* rather than a word.

---

## 3. Domain 2 — `structured_information_analysis`

Required coverage: extraction, classification, noisy cleanup, table
interpretation, quantitative comparison, schema conversion, evidence-backed
recommendation, contradiction detection, missing-data handling, aggregation and
synthesis. All data required to answer is provided in the prompt; there is no
live external data dependency.

### Slots

| ID | Working title | Diff | Lang | Expected shape | Deterministic opportunity |
| --- | --- | --- | --- | --- | --- |
| SA-01 | Messy ticket to fixed schema | easy | en | JSON | Strong — validity, required keys, enum, null handling |
| SA-02 | 工单分类到固定标签集 | easy | zh | Classification labels | Strong — label enum membership |
| SA-03 | 表格数据解读与量化对比 | medium | zh | Table + prose verdict | Partial — required numbers appear in output |
| SA-04 | Schema conversion between two shapes | medium | en | JSON | Strong — target keys, no legacy keys |
| SA-05 | 噪声清理：从群聊提取需求 | medium | zh | Bullets + evidence quotes | Partial — quote markers, item count |
| SA-06 | 证据支撑的建议 | medium | zh | JSON verdict + prose | Strong — required keys, verdict enum |
| SA-07 | 跨文档聚合与综合 | medium | zh | Structured sections | Partial — section labels, consensus items present |
| SA-08 | 矛盾检测 | hard | zh | Ranked contradiction list + judgment | Partial — detectable-contradiction count only |
| SA-09 | Missing-data discipline | hard | en | Gap report + bounded conclusion | Partial — explicit missing-field statement |
| SA-10 | 多源数据聚合到评分表 | hard | zh | Table + method note | Strong — table shape, rounding rule, method note |

### Slot detail

**SA-01** — *Test intent:* extract a fixed record from a messy free-text ticket.
*Primary:* single-record extraction. *Secondary:* null discipline. *Eval focus:*
all required keys, valid enums, `null` rather than a guessed value. *Distinct:*
the baseline extraction case, one record, no ambiguity between fields.

**SA-02** — *Test intent:* assign a fixed taxonomy label, including an escape
label for out-of-scope input. *Primary:* classification. *Secondary:* honest
`unknown` use. *Eval focus:* label from the allowed set, justified briefly.
*Distinct:* the only pure classification case; no field extraction.

**SA-03** — *Test intent:* interpret a small dataset and compare options
quantitatively. *Primary:* table interpretation and arithmetic. *Secondary:*
comparison under a stated rule. *Eval focus:* correct deltas, correct pick, no
arithmetic errors. *Deterministic scope:* the expected deltas and totals are
derived from the candidate-visible table, so checking the derived values is a
correctness check, not a "number appears" proxy; the comparison verdict is
judge-evaluated. See §7. *Distinct:* the only case where the model must compute
rather than read.

**SA-04** — *Test intent:* convert one machine-readable shape into another.
*Primary:* schema conversion. *Secondary:* dropping obsolete fields. *Eval
focus:* target keys present, legacy keys absent, values mapped correctly.
*Distinct:* input is already structured, so this isolates transformation rather
than extraction.

**SA-05** — *Test intent:* filter noisy multi-speaker input into real
requirements with provenance. *Primary:* noisy-information cleanup.
*Secondary:* evidence linkage. *Eval focus:* each requirement traceable to a
quoted line, noise excluded. *Distinct:* the only case whose difficulty comes
from input noise rather than task complexity.

**SA-06** — *Test intent:* make a recommendation that cites the evidence
supporting it. *Primary:* evidence-backed recommendation. *Secondary:* structured
output. *Eval focus:* verdict matches the stated rule, supporting rows cited, no
unsupported claim. *Distinct:* the only case requiring an explicit
claim-to-evidence mapping.

**SA-07** — *Test intent:* synthesize several short sources into one consolidated
view. *Primary:* aggregation across sources. *Secondary:* conflict flagging.
*Eval focus:* all sources represented, overlaps merged, disagreements flagged.
*Distinct:* the only multi-source synthesis case at medium difficulty.

**SA-08** — *Test intent:* detect contradictions between two reports that claim
to describe the same thing, and be honest about which conflicts can be
resolved. *Primary:* contradiction detection and classification. *Secondary:*
disciplined handling of unresolved conflicts. *Eval focus:* each contradiction
named with both values, and the case distinguishes **detectable contradiction**
(the two statements differ), **resolvable contradiction** (supplied provenance
or priority rules settle it), and **unresolved contradiction** (nothing in the
material establishes authority). The case must either (A) provide
candidate-visible source provenance / priority rules sufficient to resolve
authority, and/or (B) deliberately include conflicts whose authority cannot be
established — rewarding an explicit statement that the conflict is unresolved.
Confident guessing is never rewarded. *Deterministic scope:* only the count of
detectable contradictions is mechanically bounded; resolvability and authority
are judge-evaluated. *Distinct:* the only case where the primary task is
finding disagreement.

**SA-09** — *Test intent:* handle an incomplete dataset without silently
imputing. *Primary:* missing-data discipline. *Secondary:* bounded conclusions.
*Eval focus:* missing fields named, unsupported conclusions withheld, remaining
conclusion explicitly bounded. *Distinct:* the only case where the correct
behaviour is to refuse part of the task.

**SA-10** — *Test intent:* aggregate several partial tables into one scorecard
using a stated method. *Primary:* multi-source aggregation. *Secondary:*
numeric-rule adherence. *Eval focus:* correct weights, stated rounding,
reproducible method note. *Deterministic scope:* the scorecard shape is
structural, and the score values are recomputed from the visible inputs and the
stated weights and rounding rule, so they are objectively derivable ground
truth; the method note is judge-evaluated. See §7. *Distinct:* the only case
combining aggregation with a strict numeric rule.

---

## 4. Domain 3 — `product_reasoning_decision`

Required coverage: feature prioritisation, metric design, launch/no-launch,
MVP scope, trade-off reasoning, experiment design, user-problem diagnosis,
roadmap choice, model/product selection, risk and rollback planning. Cases must
reward explicit reasoning, not generic PM vocabulary.

### Slots

| ID | Working title | Diff | Lang | Expected shape | Deterministic opportunity |
| --- | --- | --- | --- | --- | --- |
| PR-01 | 本季度只做两件事 | easy | zh | Decision + rationale | Partial — required decision-rule statement |
| PR-02 | Metric definition for a simple feature | easy | en | Prose + short list | Partial — one primary metric present |
| PR-03 | MVP 范围裁剪 | medium | zh | Scoped list + exclusions | Partial — excluded items named |
| PR-04 | 上线 / 不上线决策 | medium | zh | Recommendation + conditions | Partial — explicit recommendation present |
| PR-05 | 指标设计含护栏与回滚阈值 | medium | zh | Metric table | Partial — table shape; threshold adequacy judged |
| PR-06 | 权衡推理：质量 / 成本 / 延迟 | medium | zh | Comparison + justified pick | None — subjective only |
| PR-07 | 实验设计 | medium | zh | Structured experiment plan | Partial — required plan fields |
| PR-08 | 用户问题诊断 | hard | zh | Hypothesis ranking + evidence plan | None — subjective only |
| PR-09 | 路线图选择 | hard | zh | Sequenced roadmap | Partial — sequence and capacity constraints |
| PR-10 | 模型选型与风险回滚 | hard | mixed | Recommendation + risk table + triggers | Partial — risk table shape, trigger values |

### Slot detail

**PR-01** — *Test intent:* prioritise a small backlog and state the rule before
applying it. *Primary:* prioritisation. *Secondary:* explicit rule statement.
*Eval focus:* rule stated first, exactly two picks, deferral justified.
*Distinct:* the baseline decision case; small, bounded, one rule.

**PR-02** — *Test intent:* define measurement for a feature with one primary and
one guardrail metric. *Primary:* metric design. *Secondary:* computability from
stated events. *Eval focus:* exactly one primary, guardrail computable, no vague
goals. *Distinct:* the only case that is purely about metric definition.

**PR-03** — *Test intent:* cut a feature list down to a shippable MVP under a
fixed budget. *Primary:* scope reduction. *Secondary:* explicit exclusions.
*Eval focus:* fits the budget, everything removed is named, rationale tied to the
constraint. *Distinct:* the only case whose core act is deliberate subtraction.

**PR-04** — *Test intent:* make a launch decision from evaluation, cost, and
latency evidence. *Primary:* go/no-go judgment. *Secondary:* conditional
reasoning. *Eval focus:* clear recommendation, reasons traceable to given
numbers, no invented data. *Deterministic scope:* the recommendation enum and
the presence of the required condition/evidence fields are structural. Whether
the decision is correct against the visible numbers is judge-evaluated against
the stated decision rule, not inferred from the presence of a number. See §7.
*Distinct:* the only binary ship decision with multiple failing signals to
weigh.

**PR-05** — *Test intent:* produce a measurement plan with guardrails and
explicit rollback thresholds. *Primary:* measurement design. *Secondary:*
rollback planning. *Eval focus:* one primary, at most three guardrails, each with
a computation and a numeric trigger. The deterministic check verifies table
shape, guardrail count, and that a numeric trigger field exists; whether the
chosen thresholds are *appropriate* is judge-evaluated, because the case does
not supply a single objectively correct value unless it states one.
*Distinct:* extends metric design into operational thresholds, unlike PR-02.

**PR-06** — *Test intent:* choose between options that trade quality against cost
and latency. *Primary:* trade-off reasoning. *Secondary:* decision-rule usage.
*Eval focus:* explicit trade-off articulation, choice follows the stated rule,
runner-up named. *Deterministic scope:* none — every quantity the answer needs
is visible, but the trade-off verdict is a judgment, so it is scored against
criteria and judged rather than faked with a keyword check. See §7. *Distinct:*
the only case centred on multi-objective trade-offs rather than a single
criterion.

**PR-07** — *Test intent:* design an experiment with a falsifiable success
condition. *Primary:* experiment design. *Secondary:* stopping rules. *Eval
focus:* hypothesis, unit, duration, metric, and stop rule all present and
coherent. *Distinct:* the only case requiring an experimental design.

**PR-08** — *Test intent:* diagnose a user problem from mixed signals and rank
competing explanations. *Primary:* problem diagnosis. *Secondary:* evidence
planning. *Eval focus:* hypotheses ranked, each with the evidence that would
confirm or falsify it, no premature conclusion. *Distinct:* the only case whose
output is diagnosis rather than a decision or a plan.

**PR-09** — *Test intent:* choose and sequence roadmap items across quarters
under capacity limits and dependencies. *Primary:* roadmap sequencing.
*Secondary:* dependency reasoning. *Eval focus:* respects capacity, honours
dependencies, justifies deferrals. *Distinct:* the only case spanning multiple
planning horizons.

**PR-10** — *Test intent:* select a model or approach and specify how to contain
the risk. *Primary:* selection under constraints. *Secondary:* risk and rollback
planning. *Eval focus:* recommendation justified by numbers, risk table with
concrete triggers, rollback path stated. *Deterministic scope:* the risk table
shape and the presence of trigger fields are structural; the adequacy of each
trigger and the selection rationale are judge-evaluated. See §7. *Distinct:* the
only case pairing a selection decision with an explicit rollback plan, and the
only mixed-language case here.

---

## 5. Domain 4 — `chinese_business_communication`

All ten cases are Chinese-first. This domain tests genuinely Chinese
professional contexts — register, information density, and relationship
handling — not generic writing quality.

**Anti-stereotype rule.** Scoring is against observable communication
outcomes: who the reader is, what they need to decide or do, which facts they
need, and the appropriate information density. No case rewards or penalises a
generalized notion of "Chinese hierarchy", deference, or cultural style, and no
case requires private chain-of-thought. This principle applies across the whole
Chinese-language domain.

### Slots

| ID | Working title | Diff | Lang | Expected shape | Deterministic opportunity |
| --- | --- | --- | --- | --- | --- |
| BC-01 | 内部进展改写给管理层 | easy | zh | Prose | Strong — char cap, banned jargon, key figures present |
| BC-02 | 会议纪要转行动项 | easy | zh | Table / bullets | Strong — row count, owner only when stated |
| BC-03 | 需求澄清邮件 | medium | zh | Email prose | None — subjective only |
| BC-04 | 向技术团队转译业务需求 | medium | zh | Structured prose + requirements list | Partial — requirement count, banned internal jargon |
| BC-05 | 项目风险升级 | medium | zh | Structured escalation note | Partial — required escalation fields |
| BC-06 | 客户延期说明与补救方案 | medium | zh | Customer-facing prose | None — subjective only |
| BC-07 | 同一事实面向两类受众改写 | medium | zh | Two labeled sections | Partial — section labels, differing density |
| BC-08 | 避免空话套话的危机沟通 | hard | zh | Prose | Partial — banned word list |
| BC-09 | 拒绝不合理请求 | hard | zh | Prose message | None — subjective only |
| BC-10 | 三页材料压缩成一页汇报稿 | hard | zh | Structured one-pager | Strong — char cap, fixed sections, all figures retained |

### Slot detail

**BC-01** — *Test intent:* rewrite internal progress for management with facts
intact and no filler. *Primary:* executive register. *Secondary:* fact
preservation. *Eval focus:* conclusion first, all figures unchanged, no empty
jargon. *Distinct:* the baseline Chinese executive-communication case.

**BC-02** — *Test intent:* turn meeting notes into action items with owners and
dates only where stated. *Primary:* meeting-to-action conversion. *Secondary:*
non-invention. *Eval focus:* each action has a clear verb and owner only if
present in the notes. *Distinct:* the only note-taking case; output is a
structured task list, not prose.

**BC-03** — *Test intent:* write a professional clarification email for an
under-specified request. *Primary:* Chinese business register in writing.
*Secondary:* question precision. *Eval focus:* specific, answerable questions;
register appropriate to the stated internal counterpart; no assumption baked
into the draft. *Distinct:* clarification appears here as *communication*,
whereas IF-04 tests it as *refusal to execute*.

**BC-04** — *Test intent:* translate a business ask into requirements an
engineering team can act on. *Primary:* cross-functional translation.
*Secondary:* preserving business intent. *Eval focus:* requirements actionable
and testable, original intent intact, no unexplained internal shorthand.
*Distinct:* the only case targeting business-to-engineering translation.

**BC-05** — *Test intent:* escalate a slipping project to leadership. *Primary:*
risk escalation. *Secondary:* structure under pressure. *Eval focus:* facts,
impact, options, and a specific ask all present and separated. *Distinct:* the
only escalation case; the required ask is the scoring hinge.

**BC-06** — *Test intent:* tell a customer about a delay without blame or
over-promising. *Primary:* external relationship communication. *Secondary:*
commitment discipline. *Eval focus:* no blame assignment, concrete remedy, no
promise the facts do not support. *Distinct:* the only customer-facing
(external) communication case.

**BC-07** — *Test intent:* render one fact set at two levels of information
density for two audiences. *Primary:* audience-level adaptation. *Secondary:*
density control. *Eval focus:* same facts, genuinely different density and
framing for two **explicitly stated audience roles**: a business-unit /
management decision maker and an execution / project team. The higher-level
version emphasizes, where appropriate, the conclusion, business impact,
material risk, and the decision or resource ask. The execution version
emphasizes, where appropriate, operational context, dependencies, owners, next
actions, and implementation detail. Facts remain invariant across both
versions; only density, framing, and emphasis change. *Distinct:* distinct from
IF-03 (three audiences, language-focused adaptation) in that this is a
two-audience density and framing test judged against stated communication
needs, not a notion of hierarchy or deference.

**BC-08** — *Test intent:* write internal incident communication that avoids
euphemism and buzzwords. *Primary:* plain, direct Chinese business writing.
*Secondary:* incident framing. *Eval focus:* impact and next steps stated
plainly, banned filler absent, no responsibility-dodging language. *Distinct:*
the only crisis-communication case.

**BC-09** — *Test intent:* decline a stakeholder request without damaging the
relationship. *Primary:* relationship-preserving refusal. *Secondary:*
alternative offering. *Eval focus:* clear refusal, reason without blame, a
workable alternative proposed. *Distinct:* the only case centred on
relationship management rather than information transfer.

**BC-10** — *Test intent:* compress long material into a one-page executive
brief without losing the decision ask. *Primary:* information density under a
hard budget. *Secondary:* structure. *Eval focus:* all key figures retained, the
ask unmistakable, ceiling respected. *Distinct:* the only case combining density
pressure with a decision ask at hard difficulty.

---

## 6. Domain 5 — `agent_workflow_planning`

Planning only. No real tool execution, no code, no multi-agent implementation.
Required coverage: tool selection, decomposition, dependency ordering, error and
retry handling, permissions and safety boundaries, human approval gates,
parallel versus sequential execution, data handoff between steps, stopping
criteria, and escalation when information is missing.

### Slots

| ID | Working title | Diff | Lang | Expected shape | Deterministic opportunity |
| --- | --- | --- | --- | --- | --- |
| AW-01 | 客服工单自动分类工作流 | easy | zh | Numbered plan | Strong — step ordering, approval gate present |
| AW-02 | Tool selection for a simple goal | easy | en | Selection + rationale | None — subjective only |
| AW-03 | 依赖排序（含数据依赖） | medium | zh | Ordered plan + dependency notes | Partial — required ordering |
| AW-04 | 错误与重试处理 | medium | zh | Failure table | Partial — table shape, bounded-retry fields; risk judged |
| AW-05 | 权限与安全边界 | medium | mixed | Boundary plan | None — subjective only |
| AW-06 | 人工审批门设计 | medium | zh | Gate list | Partial — countable gates; criteria quality judged |
| AW-07 | 串行 vs 并行判断 | medium | zh | Plan + parallelism rationale | None — subjective only |
| AW-08 | 工具间数据交接契约 | hard | zh | Contract + plan | Strong — required contract fields |
| AW-09 | 停止条件与预算约束 | hard | zh | Policy + plan | None — subjective only |
| AW-10 | 信息缺失时的升级路径 | hard | mixed | Escalation plan | None — subjective only |

### Slot detail

**AW-01** — *Test intent:* decompose a routine pipeline into ordered steps with
inputs, outputs, and one approval gate. *Primary:* workflow decomposition.
*Secondary:* ordering. *Eval focus:* correct order, each step's input and output
stated, gate placed sensibly. *Distinct:* the baseline planning case; smallest
step count and one gate.

**AW-02** — *Test intent:* choose the right tools for a goal from a supplied
list, and say what is not needed. *Primary:* tool selection. *Secondary:*
minimalism. *Eval focus:* choices justified against the goal, unnecessary tools
explicitly excluded. *Distinct:* the only case focused on selection rather than
sequencing, and the only English easy case in this domain.

**AW-03** — *Test intent:* order steps where data produced by one step is
required by another. *Primary:* dependency ordering. *Secondary:* identifying
the critical path. *Eval focus:* no step scheduled before its input exists.
*Distinct:* the only case whose difficulty is purely dependency-driven.

**AW-04** — *Test intent:* define side-effect-aware failure and retry handling
for a given pipeline.
*Primary:* side-effect-aware retry planning. *Secondary:* fallback design.
*Eval focus:* failure modes enumerated and classified by side-effect risk —
safe/idempotent reads, operations whose completion state is uncertain after a
failure, and irreversible or high-impact side effects. A good plan reasons
about bounded retries, idempotency, duplicate-side-effect prevention,
verification before retry, and fallback/escalation. The case must not assume a
universal "correct retry count" unless the prompt explicitly supplies such a
policy. *Deterministic scope:* the framework may verify that retry budgets are
bounded and that required fields exist; the risk judgment itself is
judge-evaluated (see §7). *Distinct:* the only case whose output is a failure
matrix.

**AW-05** — *Test intent:* decide which steps may run unattended and which
require permission. *Primary:* permission and safety boundaries. *Secondary:*
risk classification. *Eval focus:* boundaries justified by consequence, no
unattended high-impact action. *Distinct:* the only case centred on authority
rather than correctness.

**AW-06** — *Test intent:* place human approval gates with explicit criteria.
*Primary:* approval-gate design. *Secondary:* criteria precision. *Eval focus:*
each gate names what is approved, by whom, and against what condition.
*Distinct:* expands the single gate of AW-01 into a designed set with criteria.

**AW-07** — *Test intent:* decide which steps can run in parallel under a shared
resource constraint. *Primary:* parallel versus sequential judgment.
*Secondary:* resource reasoning. *Eval focus:* parallel set is safe and
justified, shared resource respected. *Distinct:* the only case about execution
topology rather than step content.

**AW-08** — *Test intent:* specify the data contract passed between steps.
*Primary:* data handoff design. *Secondary:* validation. *Eval focus:* fields,
formats, validation rules, and mismatch behaviour all defined. *Distinct:* the
only case where the deliverable is an interface, not a sequence.

**AW-09** — *Test intent:* define when a long-running workflow must stop or
escalate. *Primary:* stopping criteria. *Secondary:* budget discipline. *Eval
focus:* stop conditions, escalation path, and cost/latency budget rules stated.
*Distinct:* the only case about termination rather than execution.

**AW-10** — *Test intent:* define the escalation path when required information
is unavailable. *Primary:* escalation on missing input. *Secondary:* refusal to
guess. *Eval focus:* exactly what is missing, from whom, and what happens while
waiting. *Distinct:* the only case where the correct behaviour is to stop and
escalate rather than proceed, and the second mixed-language case here.

---

## 7. Coverage Audit

Self-review performed against the rules in §1 and the checks required by the
Phase 3A brief.

### Counts

| Check | Result |
| --- | --- |
| Total slots | 50 ✅ |
| Cases per domain | 10 / 10 / 10 / 10 / 10 ✅ |
| Domains | Exactly 5 ✅ |
| Duplicate case IDs | None ✅ |
| Production prompts written | None — intent only ✅ |

### Difficulty by domain

| Domain | Easy | Medium | Hard | Total |
| --- | --- | --- | --- | --- |
| instruction_constraint_following | 2 | 5 | 3 | 10 |
| structured_information_analysis | 2 | 5 | 3 | 10 |
| product_reasoning_decision | 2 | 5 | 3 | 10 |
| chinese_business_communication | 2 | 5 | 3 | 10 |
| agent_workflow_planning | 2 | 5 | 3 | 10 |
| **Total** | **10** | **25** | **15** | **50** |

### Language

| Language | IF | SA | PR | BC | AW | Total |
| --- | --- | --- | --- | --- | --- | --- |
| `zh` | 8 | 7 | 8 | 10 | 7 | **40** |
| `en` | 1 | 3 | 1 | 0 | 1 | **6** |
| `mixed` | 1 | 0 | 1 | 0 | 2 | **4** |
| **Total** | 10 | 10 | 10 | 10 | 10 | **50** |

40 Chinese-first and 10 English/mixed, matching the methodology target.

### Expected output shape

| Shape | Count | Case IDs |
| --- | --- | --- |
| Prose / narrative | 13 | IF-03, IF-08, IF-10, PR-01, PR-04, PR-06, BC-01, BC-03, BC-06, BC-07, BC-08, BC-09, AW-02 |
| Bullets / list | 6 | IF-01, SA-05, PR-03, PR-08, BC-02, AW-06 |
| Table / matrix | 6 | IF-05, SA-03, SA-10, PR-05, PR-10, AW-04 |
| JSON / structured data | 4 | IF-07, SA-01, SA-04, SA-06 |
| Classification / labels | 1 | SA-02 |
| Mixed prose + structure | 10 | IF-02, IF-06, IF-09, SA-07, SA-09, PR-02, PR-07, BC-04, BC-05, BC-10 |
| Ranked / prioritised recommendation | 3 | PR-09, SA-08, AW-03 |
| Plan / sequence | 6 | AW-01, AW-05, AW-07, AW-08, AW-09, AW-10 |
| Q&A / clarification | 1 | IF-04 |

No domain is dominated by a single shape. The structured domain carries three
JSON-adjacent cases out of ten; that is deliberate, since serialization
discipline is a core part of what that domain measures, and the other seven use
tables, labels, bullets, and prose.

### Deterministic check opportunity

| Level | Count | Meaning |
| --- | --- | --- |
| Strong | 14 | Structural, countable, enum, ordering, or **objectively derived** constraints a checker can decide |
| Partial | 25 | A structural or length check covers part of the case; the semantic half stays with judges |
| None | 11 | Fully subjective or judged by outcome; judges only, `deterministic_checks: []` |

The eleven `None` slots are IF-06, BC-03, BC-06, BC-09, PR-06, PR-08, AW-02,
AW-05, AW-07, AW-09, AW-10. These are the cases where a correct answer can
legitimately take many forms, or where the intended constraint is a semantic
outcome that a keyword check cannot honestly test. Adding a mechanical check
would create false failures or keyword gaming rather than signal. They are
recorded as an accepted limitation of the automation rate, not a gap to be
closed by inventing checks.

#### Deterministic-check quality audit (Phase 3A.1)

Per the rule in `CASE_DESIGN_STANDARD_V1.md` §6 — a deterministic check must
test the intended constraint, not a superficial proxy — the Phase 3A planned
labels were re-audited. Six opportunities changed because their deterministic
half leaned on keyword, phrase, or number-presence evidence that does not
establish the capability:

| Slot | Was | Now | Why |
| --- | --- | --- | --- |
| IF-01 | Strong | **Partial** | Bullet count is a real structural check; "no solution named" is semantic, so it moved to judges |
| IF-06 | Partial | **None** | The planned evidence was a required priority phrase. Correct resolution is judged from which instruction the output obeys, not from a phrase |
| IF-09 | Strong | **Partial** | Per-part counts are real; the conflict-resolution note was presence-only, so that half is judged |
| PR-05 | Strong | **Partial** | Table shape is real; "threshold values present" is not evidence the thresholds are appropriate, so adequacy is judged |
| AW-04 | Strong | **Partial** | Bounded-retry structure is real; the retry-risk judgment and count suitability are judged, since no universal correct count exists |
| AW-06 | Strong | **Partial** | Gate count is countable; "approval criteria present" was presence-only, so criteria quality is judged |

Distribution after the audit:

| Domain | Strong | Partial | None |
| --- | --- | --- | --- |
| instruction_constraint_following | 4 | 5 | 1 |
| structured_information_analysis | 5 | 5 | 0 |
| product_reasoning_decision | 0 | 8 | 2 |
| chinese_business_communication | 3 | 4 | 3 |
| agent_workflow_planning | 2 | 3 | 5 |
| **Total** | **14** | **25** | **11** |

Language rule compliance: every `zh` slot uses `max_chars` / `min_chars` or no
length check at all. No `zh` slot declares `max_words` / `min_words`. The four
`mixed` slots (IF-09, PR-10, AW-05, AW-10) do not rely on word counts.

### Quantitative correctness plan

Six slots are quantitatively grounded: SA-03, SA-10, PR-04, PR-05, PR-06, and
PR-10. None of them is judged "correct because a number appears". Each states in
advance how correctness is established, following
`CASE_DESIGN_STANDARD_V1.md` §6:

| Slot | Expected values | How correctness is established | Deterministic vs judge |
| --- | --- | --- | --- |
| SA-03 | Deltas and totals over a small visible dataset | Derived by recomputation from the candidate-visible table; the comparison rule is stated in the prompt | Deterministic exact/derived values within a stated tolerance; the pick is judge-evaluated |
| SA-10 | Weighted scorecard values | Recomputed from visible partial tables plus the stated weights and rounding rule | Deterministic on shape and derived values; the method note is judge-evaluated |
| PR-04 | None fixed — a go/no-go against stated signals | Recommendation enum is structural; correctness is checked against the supplied decision rule and the visible numbers | Structural fields deterministic; the decision itself judge/reference-evaluated |
| PR-05 | Model-chosen guardrail thresholds | No single objectively correct threshold unless the prompt supplies one; only structure and numeric presence are mechanical | Structure deterministic; threshold adequacy judge-evaluated |
| PR-06 | Trade-off quantities visible in the prompt | Requires the model to compare, not compute a fixed hidden answer; the stated rule makes the correct choice derivable | No deterministic check (`[]`); judges verify the arithmetic and the verdict |
| PR-10 | Model-chosen risk triggers | Trigger fields are structural; adequacy and selection rationale are judgment | Structure deterministic; risk judgment judge-evaluated |

**Framework note.** The existing check set can express an exactly derived value
only indirectly (a `numeric_range` with `min == max` on the first matching
number), and it cannot bind a value to a named field or express a tolerance.
That is enough for the planned cases provided the prompt makes the required
value unambiguous, so no framework change is built now. The small extension that
would materially improve robustness — a named-field value check with an
explicit tolerance — is recorded as a Phase 3/4 candidate rather than
implemented speculatively. Where the framework cannot honestly verify a
constraint, that component is marked above as judge/reference-based.

### Scope checks

| Check | Result |
| --- | --- |
| Coding tasks | None ✅ |
| Current-web-information dependency | None — all data supplied in-prompt ✅ |
| RAG tasks | None ✅ |
| Real tool execution | None — planning only ✅ |
| Multi-agent implementation | None — planning only ✅ |
| Vision / multimodal | None ✅ |
| Adversarial prompt injection | None ✅ |
| Pure creative-writing contests | None ✅ |
| Duplicate test intents within a domain | None found; each slot carries a distinctiveness statement ✅ |
| Subjective cases with concrete evaluation focus | All eleven `None`-check slots carry explicit eval focus statements ✅ |

### Known trade-offs

1. **Prose is the largest single shape (13/50).** Business reasoning and
   communication genuinely produce prose, so a prose-heavy distribution is
   honest. Machine-checkable signal is weaker for prose, which is why the
   shadow-weight of judge scoring is highest there.
2. **Classification appears once.** One dedicated classification case (SA-02) is
   thin relative to extraction and schema work (SA-01, SA-04). Classification
   also appears as a sub-step in several analysis cases, but only SA-02 isolates
   it. If Phase 3B finds SA-02 too easy, promoting a second classification case
   would require displacing another slot.
3. **Eleven cases carry no deterministic checks at all.** This is a deliberate
   choice over inventing mechanical checks for subjective work (and, since the
   Phase 3A.1 keyword audit, over testing semantic outcomes with phrase
   matching); it means the `constraint_pass_rate` metric is silent for 22% of
   the dataset.
4. **Two domains are 100% Chinese (BC) or nearly so (IF, PR at 8/10).** That
   matches the 40/10 language target but means cross-lingual robustness is only
   lightly sampled, with 10 English/mixed cases in total.
5. **Four hard cases (PR-08, BC-09, AW-09, AW-10) have no deterministic checks
   and high subjectivity.** They will lean hardest on judge agreement, which is
   exactly where the correlated-judge limitation for tail families bites.

### Status

Matrix complete and internally consistent after the Phase 3A.1 semantic audit.
Gate 3A.1 external review passed, so this document and
`CASE_DESIGN_STANDARD_V1.md` are **APPROVED FOR PHASE 3B AUTHORING**. The
approval covers the design documents, not the production dataset: each authored
case is reviewed separately and the dataset is not approved until it is
complete.
