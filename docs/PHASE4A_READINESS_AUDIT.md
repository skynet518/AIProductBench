# Phase 4A — Live Benchmark Readiness Audit (offline)

**Scope.** Read-only audit of the model registry, provider adapter, pricing/FX
architecture, judge configuration, incomplete-model handling, and run-manifest
shape, ahead of any live benchmark work. **No network / provider / model call
was made while producing this audit.**

Basis: frozen 50-case dataset at commit `0725f77` (semantic manifest SHA-256
`6b450383e528a5a0a6b813112f96182a3625c04c948839fc551c8ded63da513c`). The
production cases are immutable in this phase.

---

## 1. Logical model registry audit

All ten logical slots are present in `data/models_v1.json`. Every literal
provider model ID is deliberately `null` and marked `unverified`; nothing is
guessed.

| Logical key | Provider (`provider_key`) | Market position | Configured `model_id` | ID status |
| --- | --- | --- | --- | --- |
| `qwen_flagship` | Alibaba Model Studio (`alibaba_model_studio`) | flagship | `null` | unverified |
| `qwen_value` | Alibaba Model Studio (`alibaba_model_studio`) | value | `null` | unverified |
| `deepseek_flagship` | DeepSeek (`deepseek`) | flagship | `null` | unverified |
| `deepseek_value` | DeepSeek (`deepseek`) | value | `null` | unverified |
| `kimi_flagship` | Moonshot AI (`moonshot`) | flagship | `null` | unverified |
| `kimi_value` | Moonshot AI (`moonshot`) | balanced | `null` | unverified |
| `minimax_flagship` | MiniMax (`minimax`) | flagship | `null` | unverified |
| `glm_flagship` | Zhipu BigModel (`zhipu_bigmodel`) | flagship | `null` | unverified |
| `glm_value` | Zhipu BigModel (`zhipu_bigmodel`) | value | `null` | unverified |
| `doubao_flagship` | Volcano Ark (`volcano_ark`) | flagship | `null` | unverified |

All ten are `candidate: true`. `judge_eligible: true` for `qwen_flagship`,
`deepseek_flagship`, and `glm_flagship` (the shared registry has no judge-only
duplicates).

## 2. Registry contract mapping

The registry now represents the full Phase 4A contract. Required contract field →
registry storage key:

| Contract field | Storage key | Notes |
| --- | --- | --- |
| `logical_model_id` | `key` | |
| `provider` | `provider` (+ `provider_key`) | |
| `provider_model_id` | `model_id` | `null` until verified |
| `display_name` | `display_name` | |
| `model_family` | `model_family` | |
| `tier` | `product_tier` | `flagship` / `balanced` / `value` |
| `enabled` | `enabled` | **added Phase 4A** (bool; all `true`) |
| `thinking_mode` | `thinking_mode` | `disabled` / `enabled` / `provider_default` |
| `thinking_config` | `thinking_config` | **added Phase 4A** (null or object) |
| `input_price_native` | `pricing.input` | |
| `output_price_native` | `pricing.output` | |
| `reasoning_price_native_or_null` | `pricing.reasoning` | **added Phase 4A** |
| (provider-specific) | `pricing.cached_input` | **added Phase 4A** (null = not used) |
| `currency` | `pricing.native_currency` | |
| `pricing_unit` | `pricing.unit` | `per_1m_tokens` |
| `pricing_as_of` | `pricing.snapshot_date` | |
| `pricing_source` | `pricing.source` | |
| `model_id_verified` | `model_id_status` | `verified` / `unverified` |
| `model_id_verified_as_of` | `model_id_verified_as_of` | **added Phase 4A** |

The four added fields are optional/additive only: `src/models.py` validates them
when present and no existing consumer is affected.

## 3. Provider adapter audit

There is **one generic native adapter** (`src/providers.py`), not per-provider
adapters. Provider differences are configuration. All six providers are
currently configured with `wire_api: "chat_completions"`.

| Aspect | Status |
| --- | --- |
| Adapter exists (all six) | yes — single generic adapter |
| Protocol style | `chat_completions` (OpenAI-compatible shape); `responses` branch implemented but unused by current config |
| Endpoint mechanism | `base_url` from the registry + `/chat/completions` (or `/responses`) |
| API-key env var | per entry: `DASHSCOPE_API_KEY`, `DEEPSEEK_API_KEY`, `MOONSHOT_API_KEY`, `MINIMAX_API_KEY`, `ZHIPU_API_KEY`, `ARK_API_KEY` |
| Request model field | `"model"` (from `model_id`) |
| System/user messages | yes — `messages` array passed through |
| Temperature | `0.0` (validator enforces) |
| Thinking / reasoning controls | **NOT implemented** — no payload field; per-provider control names are UNKNOWN / REQUIRE OFFICIAL VERIFICATION |
| Usage input tokens | `prompt_tokens` (chat) / `input_tokens` (responses) |
| Usage output tokens | `completion_tokens` (chat) / `output_tokens` (responses) |
| Reasoning tokens | `completion_tokens_details.reasoning_tokens` (chat) / `output_tokens_details.reasoning_tokens` (responses); provider exposure is UNKNOWN / REQUIRES OFFICIAL VERIFICATION |
| Latency location | `time.perf_counter()` around the HTTP POST in `providers.chat` (wall-clock, per call; only the successful attempt's latency is returned) |
| Retry behavior | `MAX_RETRIES = 2`, backoff `2**attempt` s; fatal statuses `{400,401,403,404,422}` are not retried |
| Timeout behavior | `REQUEST_TIMEOUT_SECONDS = 120` |
| Error normalization | `ProviderError` / `MissingCredentials`; per-call `error` recorded in results |

Base URLs are documentation-based and must be confirmed for the chosen region at
run time. No undocumented provider behavior is asserted here.

## 4. Pricing snapshot architecture

Native price is preserved per model in the `pricing` block: `status`,
`snapshot_date` (as-of), `native_currency`, `unit`, `source`,
`applies_to_model_id`, `input`, `output`, `reasoning` (new, nullable),
`cached_input` (new, nullable), `input_tier_limit_tokens`, `time_of_day`, and
`notes`. `pricing.price_call` produces `native_cost` plus the CNY-normalized
value; `pricing.pricing_snapshot()` persists the metadata with the run.

- **Statuses:** `unverified` (all ten today), `synthetic` (dry-run only),
  `verified` (requires a verified model ID + numeric rates + currency + source +
  as-of date).
- **No historical leakage:** the retired V0.1 archive is separate and
  `used_for_v1_cost: false`; the validator rejects a V1 entry that references an
  archived pricing ID.
- **Time-of-day pricing** and **input-tier limits** are representable and
  enforced.
- **Gap:** the pricing snapshot has no `snapshot_id`/content hash; a run
  references the embedded snapshot, not an immutable ID. Design item for Phase 4.

## 5. FX / CNY normalization

`config.FX_SNAPSHOT` (unverified: null rate, date, source) and
`config.SYNTHETIC_FX_SNAPSHOT` (dry-run only: synthetic 7.20) both carry
`fx_pair`, `fx_rate`, `fx_snapshot_date`, `source`, and now `snapshot_id`.
`normalize_to_cny` converts only on an exact `USD/CNY` pair with a positive rate;
otherwise the CNY value stays `null` with an explanatory note. No live FX lookup
exists. `pricing.validate_fx_snapshot` validates the contract.

## 6. Judge configuration compliance

Fixed `judge_priority = [qwen_flagship, deepseek_flagship, glm_flagship]`;
judge-eligible = those three. Verified selection (no same-family judge, exactly
two cross-family judges):

| Candidate family | Selected judges |
| --- | --- |
| Qwen | DeepSeek + GLM |
| DeepSeek | Qwen + GLM |
| Kimi | Qwen + DeepSeek |
| MiniMax | Qwen + DeepSeek |
| GLM | Qwen + DeepSeek |
| Doubao | Qwen + DeepSeek |

No silent substitution: `select_judges` returns `[]` when fewer than two eligible
cross-family judges remain, and the case is recorded as judge-unavailable.
**Compliant.**

## 7. Incomplete-model accounting

`runner.summarize` sets `rank_eligible = (cases_scored == required_cases and
required_cases > 0)`. An incomplete model keeps raw spend (`actual_spend_cny`),
`calls_completed`, `cases_completed`, tokens, latency diagnostics, per-case
records, and `judge_unavailable_cases`, and suppresses
`cost_per_100_tasks_cny`, `quality_per_cny`, `official_rank`, and official Pareto
eligibility, with `incomplete_reason` recorded. **Compliant** with the frozen
methodology.

## 8. Run-manifest status

`runner.build_document` already records: `snapshot_id` (run id),
`benchmark_version`, `generated_at`, `dataset` (version + distributions),
`model_pool` (pool version + facts + candidate/judge entries + judge priority),
`rubric` (incl. judge prompt version and selection rule), `pricing_snapshot`,
`historical_pricing`, `results`, `failures`, `summary`.

Per-candidate capture already includes provider model ID, case counts, judge
availability, token usage, native cost, and latency. **Not yet present** (design
items, not implemented in this phase): `dataset_manifest_hash`, `git_commit`,
a `model_registry_snapshot` ID/hash, a `pricing_snapshot_id`, an `fx_snapshot_id`,
an explicit `start_time`, and an environment/runtime-version block. `thinking_config`
is now in the registry but not yet echoed into per-candidate run records.

## 9. Items that require official web/provider verification

1. Literal provider model IDs for all ten logical slots (flagship + value/balanced per family).
2. Provider-native base URLs / regions for each chosen model.
3. Thinking/reasoning control field names and allowed values per provider.
4. Whether each provider exposes reasoning/cached token counts, and the exact field names.
5. Provider-native pricing for input, output, reasoning, and (where offered) cached input, with native currency and as-of date.
6. Any tier/context-length price thresholds and time-of-day pricing rules.
7. A dated USD/CNY FX snapshot with a named source.
8. Rate limits / concurrency limits and any required request headers per provider.
9. Provider credentials for Moonshot, MiniMax, Zhipu, and Volcano Ark (and Qwen/DeepSeek).
10. Confirmation that the three judge flagships are reachable with the same request shape.

## 10. Blockers before the first live smoke test

- All ten `model_id` values are `null`/unverified → `resolve_model_id` refuses to run.
- No active V1 pricing is verified → cost accounting cannot produce real numbers.
- No FX snapshot → USD-priced models have no CNY-normalized value.
- Provider credentials are not configured.
- No explicit authorization for a paid run (`--confirm` gate) has been given.

---

# Phase 4B/C — Official registry + pricing lock (implemented)

The Phase 4A gaps above are now closed **offline**. No live API/model/provider/
network call was made.

## 11. Verified model registry

All ten logical slots have a verified literal provider model ID (`as_of`
2026-09-11):

| Logical key | Provider model ID | Region |
| --- | --- | --- |
| `qwen_flagship` | `qwen3.8-max` | cn-beijing |
| `qwen_value` | `qwen3.8-flash` | cn-beijing |
| `deepseek_flagship` | `deepseek-v4-pro` | global |
| `deepseek_value` | `deepseek-v4-flash` | global |
| `kimi_flagship` | `kimi-k3` | international |
| `kimi_value` | `kimi-k2.6` | international |
| `minimax_flagship` | `MiniMax-M3` | global |
| `glm_flagship` | `glm-5.3` | global |
| `glm_value` | `glm-5.3-flash` | global |
| `doubao_flagship` | `doubao-seed-2-1-pro-260628` | cn-beijing |

**Kimi flagship is `kimi-k3`; Kimi value is `kimi-k2.6`.** Endpoints: Qwen
`https://dashscope.aliyuncs.com/compatible-mode/v1` (China Beijing — must stay
paired with Beijing pricing), DeepSeek `https://api.deepseek.com`, Kimi
`https://api.moonshot.ai/v1`, MiniMax `https://api.minimax.io/v1`, GLM
`https://api.z.ai/api/paas/v4`, Doubao
`https://ark.cn-beijing.volces.com/api/v3`.

**Registry snapshot:** `v1-registry-2026-09-11`, content SHA-256
`5a0175a3e1879ec5f7cdfcd0fbc46a1ab7b838602ad536f7a552dd67f8c01970`
(`data/model_registry_snapshot_v1.json`; excludes credentials).

## 12. Provider-default thinking / request configuration

The universal `temperature = 0.0` override was **removed**. Sampling is sent
only when a model's `request_config` explicitly specifies it, so every model
keeps provider-default/recommended reasoning behavior:

| Model | Effective thinking / request config |
| --- | --- |
| Qwen3.8 Max / Flash | thinking adaptive; `enable_thinking=true` (Qwen extension); no temperature override |
| DeepSeek V4 Pro / Flash | thinking enabled; `reasoning_effort=high`; no temperature/top_p |
| Kimi K3 | always thinking; `reasoning_effort=max`; no temperature override |
| Kimi K2.6 | thinking enabled; provider defaults temperature 1.0 / top_p 0.95 preserved (not overridden) |
| MiniMax-M3 | thinking adaptive; `reasoning_split=true`; no temperature override |
| GLM-5.3 / Flash | thinking enabled; provider default sampling preserved; no temperature override |
| Doubao Seed 2.1 Pro | provider-default reasoning/sampling; no undocumented `reasoning_effort` |

Effective request config is inspectable (`providers.effective_request_config`)
and recorded in the run manifest per candidate.

## 13. Pricing snapshot

Immutable snapshot `v1-pricing-2026-09-11`, `as_of` 2026-09-11, content SHA-256
`3d03267601e2978f664408543dd97094f0c2bb3c1284958951915662af3ce1b6`
(`data/pricing_snapshot_v1.json`). Native prices are stored (USD except Doubao
CNY); CNY normalization uses the fixed FX snapshot. No separate reasoning price
is invented where reasoning is billed as output tokens.

- **DeepSeek** uses peak/off-peak pricing (Monday–Friday, 01:00–04:00 and
  06:00–10:00 UTC peak), selected from the request timestamp; peak/off-peak are
  never averaged.
- **MiniMax-M3** uses context tiers (≤512K and >512K–1M); the current payable
  "Permanent 50% off" rate is used, with list prices recorded in notes.
- **GLM** cached-input storage is recorded as limited-time free; no numeric
  storage rate is fabricated.
- **Doubao** records cache storage 0.017 CNY / 1M tokens / hour, counted only if
  a billable stored cache is actually created.

## 14. Fixed FX snapshot

`ecb-2026-09-10-usd-cny` (`data/fx_snapshot_v1.json`): ECB reference rates
EUR/USD 1.1616 and EUR/CNY 7.7900 → **USD/CNY = 7.7900 / 1.1616 =
6.706267217630854**, `as_of` 2026-09-10. Native CNY converts at 1.0. No live
floating rate is used.

## 15. Run manifest — gaps closed

`run_manifest` now records `run_id`, `dataset_version`, `dataset_manifest_hash`,
`git_commit`, `model_registry_snapshot_id`/`_hash`, `pricing_snapshot_id`/`_hash`,
`fx_snapshot_id`, `judge_config_snapshot_id`, `start_time`, and a
`runtime` block (python_version, platform, benchmark_version). Per candidate it
records logical model id, provider model id, provider, `thinking_config`,
`request_config`, `pricing_record`, case counts, judge availability,
input/output/reasoning/cached tokens, native + CNY spend, and latency
diagnostics. Usage normalization now reads cached-input tokens when exposed and
returns null otherwise (nothing is estimated).

## 16. Historical archive note

The retired V0.1 entry previously labelled `deepseek-v4-flash` was relabelled to
`deepseek-v4-flash-v0.1-review` so it cannot collide with the V1 model id
`deepseek-v4-flash`. The original V0.1 id string is preserved in the entry notes;
the retired prices are unchanged and remain excluded from V1 cost.

## 17. Still requires official verification / live smoke

Source **URLs** for model IDs and prices are stored as labels only
(`source_url: null`, `source_url_status: requires_official_verification`); exact
official documentation URLs still need confirmation. Provider thinking/reasoning
field names and reasoning/cached-token exposure should be confirmed against
provider-native docs and a controlled live smoke test. Credentials are still
required. **No full paid run is authorized.**
