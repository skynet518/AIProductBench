"""Phase 4B/C — locked model registry, pricing/FX snapshots, execution config.

Offline only. No network or provider call is made by any test here.
"""

import datetime as dt
import hashlib
import json
import unittest

from src import config, models, pricing, providers, runner

UTC = dt.timezone.utc
MONDAY_PEAK = dt.datetime(2026, 9, 14, 2, 0, tzinfo=UTC)
MONDAY_OFF_PEAK = dt.datetime(2026, 9, 14, 0, 0, tzinfo=UTC)

EXPECTED_MODEL_IDS = {
    "qwen_flagship": "qwen3.8-max",
    "qwen_value": "qwen3.8-flash",
    "deepseek_flagship": "deepseek-v4-pro",
    "deepseek_value": "deepseek-v4-flash",
    "kimi_flagship": "kimi-k3",
    "kimi_value": "kimi-k2.6",
    "minimax_flagship": "MiniMax-M3",
    "glm_flagship": "glm-5.3",
    "glm_value": "glm-5.3-flash",
    "doubao_flagship": "doubao-seed-2-1-pro-260628",
}
EXPECTED_ENDPOINTS = {
    "qwen_flagship": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "qwen_value": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "deepseek_flagship": "https://api.deepseek.com",
    "deepseek_value": "https://api.deepseek.com",
    "kimi_flagship": "https://api.moonshot.ai/v1",
    "kimi_value": "https://api.moonshot.ai/v1",
    "minimax_flagship": "https://api.minimaxi.com",
    "glm_flagship": "https://api.z.ai/api/paas/v4",
    "glm_value": "https://api.z.ai/api/paas/v4",
    "doubao_flagship": "https://ark.cn-beijing.volces.com/api/v3",
}
MANIFEST_SHA256 = "6b450383e528a5a0a6b813112f96182a3625c04c948839fc551c8ded63da513c"


def _pool():
    return models.load_model_pool()


def _by_key(pool):
    return {m["key"]: m for m in pool["models"]}


class TestLockedRegistry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pool = _pool()
        cls.by_key = _by_key(cls.pool)

    def test_exactly_ten_slots(self):
        self.assertEqual(len(self.pool["models"]), 10)
        self.assertEqual(set(self.by_key), set(EXPECTED_MODEL_IDS))

    def test_exact_provider_model_ids(self):
        for key, expected in EXPECTED_MODEL_IDS.items():
            with self.subTest(model=key):
                self.assertEqual(self.by_key[key]["model_id"], expected)
                self.assertEqual(self.by_key[key]["model_id_status"], "verified")

    def test_kimi_flagship_is_k3_not_k26(self):
        self.assertEqual(self.by_key["kimi_flagship"]["model_id"], "kimi-k3")
        self.assertNotEqual(self.by_key["kimi_flagship"]["model_id"], "kimi-k2.6")

    def test_kimi_value_is_k26(self):
        self.assertEqual(self.by_key["kimi_value"]["model_id"], "kimi-k2.6")

    def test_endpoints(self):
        for key, expected in EXPECTED_ENDPOINTS.items():
            with self.subTest(model=key):
                self.assertEqual(self.by_key[key]["base_url"], expected)

    def test_pool_validates(self):
        self.assertEqual(models.validate_model_pool(self.pool)["errors"], [])

    def test_minimax_international_pricing_preserved_as_provenance(self):
        # Phase 4D.1 replaced the active international USD pricing with the China
        # domestic CNY pricing, but the retired international route must remain
        # recorded as historical provenance rather than being silently dropped.
        retired = self.by_key["minimax_flagship"]["superseded_provider_route"]
        self.assertEqual(retired["status"], "historical_inactive")
        self.assertEqual(retired["provider_key"], "minimax")
        self.assertEqual(retired["region"], "global")
        self.assertEqual(retired["native_currency"], "USD")
        self.assertEqual(retired["input_tiers"][0]["input"], 0.3)
        # The V0.1-era historical archive is untouched by this migration.
        archive = models.historical_pricing(self.pool)
        self.assertEqual(len(archive["entries"]), 3)


class TestThinkingAndRequestConfig(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.by_key = _by_key(_pool())

    def test_no_global_temperature_override(self):
        for key, model in self.by_key.items():
            with self.subTest(model=key):
                self.assertNotIn("temperature", model)
                self.assertIsNone(providers.effective_request_config(model)["temperature"])
                payload = providers._build_payload(model, [{"role": "user", "content": "hi"}])
                self.assertNotIn("temperature", payload)
                self.assertNotIn("top_p", payload)

    def test_qwen_uses_thinking_extension(self):
        payload = providers._build_payload(
            self.by_key["qwen_flagship"], [{"role": "user", "content": "hi"}]
        )
        self.assertTrue(payload.get("enable_thinking"))
        self.assertEqual(self.by_key["qwen_flagship"]["thinking_config"]["mode"], "adaptive")

    def test_deepseek_sends_reasoning_effort_and_no_sampling(self):
        for key in ("deepseek_flagship", "deepseek_value"):
            with self.subTest(model=key):
                payload = providers._build_payload(
                    self.by_key[key], [{"role": "user", "content": "hi"}]
                )
                self.assertEqual(payload.get("reasoning_effort"), "high")
                self.assertNotIn("temperature", payload)
                self.assertNotIn("top_p", payload)

    def test_runtime_envelope_is_uniform_across_all_slots(self):
        # D-054: the first official attempt showed reasoning-consuming models
        # returning finish_reason=length with empty final content at 2048,
        # DeepSeek exhausting 8192, and (D-053) DeepSeek/GLM still exhausting
        # 16384. The FINAL candidate ceiling is 32768; judges keep a separate
        # 16384 ceiling because the live judge routes already return verdicts.
        self.assertEqual(len(self.by_key), 10)
        for key, model in self.by_key.items():
            with self.subTest(model=key):
                self.assertEqual(model["max_output_tokens"], 32768)
                self.assertEqual(model["request_config"]["max_output_tokens"], 32768)
                payload = providers._build_payload(
                    model, [{"role": "user", "content": "hi"}]
                )
                self.assertEqual(payload["max_tokens"], 32768)
                if model.get("judge_eligible"):
                    self.assertEqual(model["judge_max_output_tokens"], 16384)

    def test_candidate_and_judge_envelopes_are_separate_roles(self):
        for key in ("qwen_flagship", "deepseek_flagship", "glm_flagship"):
            with self.subTest(model=key):
                model = self.by_key[key]
                candidate = providers._build_payload(
                    model, [{"role": "user", "content": "hi"}], role="candidate"
                )
                judge = providers._build_payload(
                    model, [{"role": "user", "content": "hi"}], role="judge"
                )
                self.assertEqual(candidate["max_tokens"], 32768)
                self.assertEqual(judge["max_tokens"], 16384)

    def test_registry_snapshot_records_the_runtime_envelope(self):
        snapshot = models.build_registry_snapshot(_pool())
        self.assertEqual(snapshot["snapshot_id"], "v1-registry-2026-09-11.3")
        self.assertEqual(
            {record["max_output_tokens"] for record in snapshot["models"]}, {32768}
        )
        self.assertEqual(
            {
                record["judge_max_output_tokens"]
                for record in snapshot["models"]
                if record["judge_max_output_tokens"]
            },
            {16384},
        )

    def test_client_read_timeout_is_d053_envelope(self):
        # The timeout is a maximum network/runtime allowance, never a latency
        # measurement: a legitimate response already required 297.6 seconds.
        self.assertEqual(config.REQUEST_TIMEOUT_SECONDS, 600)

    def test_kimi_contracts(self):
        k3 = providers._build_payload(self.by_key["kimi_flagship"], [])
        self.assertEqual(k3.get("reasoning_effort"), "max")
        self.assertNotIn("temperature", k3)
        k26 = providers._build_payload(self.by_key["kimi_value"], [])
        self.assertNotIn("temperature", k26)
        self.assertNotIn("top_p", k26)
        self.assertEqual(self.by_key["kimi_value"]["thinking_config"]["provider_default_temperature"], 1.0)
        self.assertEqual(self.by_key["kimi_value"]["thinking_config"]["provider_default_top_p"], 0.95)

    def test_minimax_china_uses_provider_default_reasoning(self):
        # Phase 4D.1: MiniMax-M3 runs on the China domestic route and sends no
        # international-only reasoning extension; provider-default behavior is used.
        model = self.by_key["minimax_flagship"]
        self.assertEqual(model["region"], "cn-domestic")
        self.assertEqual(model["provider"], "MiniMax China")
        self.assertEqual(model["thinking_mode"], "provider_default")
        self.assertEqual(model["thinking_config"]["mode"], "provider_default")
        payload = providers._build_payload(model, [])
        self.assertNotIn("reasoning_split", payload)
        self.assertNotIn("temperature", payload)
        self.assertNotIn("top_p", payload)

    def test_minimax_china_domestic_endpoint(self):
        model = self.by_key["minimax_flagship"]
        self.assertEqual(model["base_url"], "https://api.minimaxi.com")
        self.assertEqual(model["chat_completions_path"], "/v1/text/chatcompletion_v2")
        self.assertEqual(
            providers._endpoint(model),
            "https://api.minimaxi.com/v1/text/chatcompletion_v2",
        )

    def test_glm_and_doubao_preserve_provider_defaults(self):
        for key in ("glm_flagship", "glm_value", "doubao_flagship"):
            with self.subTest(model=key):
                payload = providers._build_payload(self.by_key[key], [])
                self.assertNotIn("temperature", payload)
                self.assertNotIn("top_p", payload)


class TestPricingSnapshot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pool = _pool()
        cls.by_key = _by_key(cls.pool)
        cls.snapshot = pricing.build_pricing_snapshot(cls.pool["models"])

    def test_snapshot_validates(self):
        self.assertEqual(pricing.validate_pricing_content(self.snapshot), [])

    def test_snapshot_hash_is_reproducible_and_matches_file(self):
        again = pricing.build_pricing_snapshot(self.pool["models"])
        self.assertEqual(self.snapshot["content_sha256"], again["content_sha256"])
        on_disk = pricing.load_pricing_snapshot()
        self.assertEqual(on_disk["content_sha256"], self.snapshot["content_sha256"])
        self.assertEqual(on_disk["snapshot_id"], pricing.PRICING_SNAPSHOT_ID)
        self.assertEqual(on_disk["as_of"], "2026-09-11")

    def test_native_prices_loaded(self):
        records = {r["model_key"]: r for r in self.snapshot["records"]}
        self.assertEqual((records["qwen_flagship"]["input"], records["qwen_flagship"]["output"]), (1.65, 4.951))
        self.assertEqual(records["qwen_flagship"]["cached_input"], 0.206)
        self.assertEqual((records["kimi_flagship"]["input"], records["kimi_flagship"]["output"]), (3.00, 15.00))
        self.assertEqual(records["doubao_flagship"]["native_currency"], "CNY")
        self.assertEqual(records["doubao_flagship"]["cache_storage"]["rate"], 0.017)

    def test_deepseek_peak_and_off_peak_selection(self):
        model = self.by_key["deepseek_flagship"]
        peak = pricing.native_price_call(model, 1_000_000, 0, at=MONDAY_PEAK)
        off = pricing.native_price_call(model, 1_000_000, 0, at=MONDAY_OFF_PEAK)
        self.assertEqual(peak["window"], "peak")
        self.assertEqual(off["window"], "off_peak")
        self.assertAlmostEqual(peak["native_cost"], 1.32, places=6)
        self.assertAlmostEqual(off["native_cost"], 0.66, places=6)

    def test_minimax_context_tier_selection(self):
        model = self.by_key["minimax_flagship"]
        small = pricing.native_price_call(model, 100_000, 0)
        large = pricing.native_price_call(model, 600_000, 0)
        # Phase 4D.1: MiniMax China domestic CNY pay-as-you-go rates.
        self.assertEqual(small["input_rate"], 2.1)
        self.assertEqual(large["input_rate"], 4.2)
        self.assertEqual(small["native_currency"], "CNY")

    def test_minimax_domestic_pricing_is_native_cny(self):
        records = {r["model_key"]: r for r in self.snapshot["records"]}
        minimax = records["minimax_flagship"]
        self.assertEqual(minimax["native_currency"], "CNY")
        self.assertEqual(minimax["region"], "cn-domestic")
        tiers = minimax["input_tiers"]
        self.assertEqual(
            (tiers[0]["input"], tiers[0]["output"], tiers[0]["cached_input"]),
            (2.1, 8.4, 0.42),
        )
        self.assertEqual(
            (tiers[1]["input"], tiers[1]["output"], tiers[1]["cached_input"]),
            (4.2, 16.8, 0.84),
        )
        self.assertIsNone(minimax["reasoning"])

    def test_cached_input_billing(self):
        model = self.by_key["qwen_flagship"]
        result = pricing.native_price_call(model, 1_000_000, 0, cached_input_tokens=1_000_000)
        self.assertAlmostEqual(result["native_cost"], 0.206, places=6)


class TestFxSnapshot(unittest.TestCase):
    def test_derived_usd_cny_value(self):
        self.assertAlmostEqual(config.FX_SNAPSHOT["fx_rate"], 7.7900 / 1.1616, places=12)
        self.assertEqual(config.FX_SNAPSHOT["snapshot_id"], "ecb-2026-09-10-usd-cny")
        self.assertEqual(config.FX_SNAPSHOT["as_of"], "2026-09-10")
        self.assertEqual(config.FX_SNAPSHOT["source"], "European Central Bank — Euro foreign exchange reference rates")

    def test_fx_snapshot_file_matches_config(self):
        on_disk = json.loads(config.FX_SNAPSHOT_FILE.read_text(encoding="utf-8"))
        self.assertEqual(on_disk["snapshot_id"], config.FX_SNAPSHOT["snapshot_id"])
        self.assertAlmostEqual(on_disk["fx_rate"], config.FX_SNAPSHOT["fx_rate"], places=12)
        self.assertEqual(on_disk["derivation"]["eur_usd"], 1.1616)
        self.assertEqual(on_disk["derivation"]["eur_cny"], 7.7900)

    def test_fx_snapshot_validates(self):
        self.assertEqual(pricing.validate_fx_snapshot(config.FX_SNAPSHOT), [])


class TestRegistrySnapshot(unittest.TestCase):
    def test_registry_snapshot_is_reproducible_and_matches_file(self):
        built = models.build_registry_snapshot(_pool())
        on_disk = models.load_registry_snapshot()
        self.assertEqual(built["content_sha256"], on_disk["content_sha256"])
        self.assertEqual(models.validate_registry_snapshot(on_disk), [])
        self.assertEqual(on_disk["snapshot_id"], models.REGISTRY_SNAPSHOT_ID)
        for record in on_disk["models"]:
            self.assertNotIn("api_key_env", record)


class TestRunManifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = runner.run_benchmark(
            runner.load_test_cases(),
            _pool(),
            dry_run=True,
            fx_snapshot=config.SYNTHETIC_FX_SNAPSHOT,
        )

    def test_run_manifest_has_all_phase4a_gap_fields(self):
        manifest = self.document["run_manifest"]
        for field in (
            "run_id", "dataset_version", "dataset_manifest_hash", "git_commit",
            "model_registry_snapshot_id", "model_registry_snapshot_hash",
            "pricing_snapshot_id", "pricing_snapshot_hash", "fx_snapshot_id",
            "judge_config_snapshot_id", "start_time", "runtime",
        ):
            with self.subTest(field=field):
                self.assertIn(field, manifest)
        for field in ("python_version", "platform", "benchmark_version"):
            self.assertIn(field, manifest["runtime"])

    def test_per_candidate_execution_fields(self):
        candidate = self.document["model_pool"]["candidates"][0]
        for field in (
            "logical_model_id", "provider_model_id", "provider",
            "thinking_config", "request_config", "pricing_record",
        ):
            with self.subTest(field=field):
                self.assertIn(field, candidate)
        row = self.document["summary"]["models"][0]
        for field in (
            "cases_attempted", "cases_completed", "judge_unavailable_cases",
            "tokens", "actual_spend_cny", "latency",
        ):
            with self.subTest(field=field):
                self.assertIn(field, row)
        for field in ("input", "output", "reasoning", "cached_input", "total"):
            self.assertIn(field, row["tokens"])


class TestUsageNullDiscipline(unittest.TestCase):
    def test_missing_usage_details_are_null_not_estimated(self):
        payload = {
            "choices": [{"message": {"content": "hello"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        text, usage = providers._extract_text_and_usage(payload, "chat_completions")
        self.assertEqual(text, "hello")
        self.assertIsNone(usage["reasoning_tokens"])
        self.assertIsNone(usage["cached_input_tokens"])

    def test_cached_and_reasoning_tokens_are_read_when_present(self):
        payload = {
            "choices": [{"message": {"content": "hello"}}],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
                "prompt_tokens_details": {"cached_tokens": 4},
                "completion_tokens_details": {"reasoning_tokens": 3},
            },
        }
        _, usage = providers._extract_text_and_usage(payload, "chat_completions")
        self.assertEqual(usage["cached_input_tokens"], 4)
        self.assertEqual(usage["reasoning_tokens"], 3)

    def test_synthetic_call_reports_null_cached_tokens(self):
        entry = _pool()["models"][0]
        call = providers.synthetic_call(entry, [{"role": "user", "content": "hi"}], "seed")
        self.assertIsNone(call["cached_input_tokens"])


class TestFrozenDatasetUnchanged(unittest.TestCase):
    def test_semantic_manifest_hash(self):
        cases = config.PRODUCTION_CASES_FILE
        doc = json.loads(cases.read_text(encoding="utf-8"))
        from src import cases as cases_module

        self.assertEqual(
            cases_module.semantic_manifest_hash(doc["test_cases"]), MANIFEST_SHA256
        )


if __name__ == "__main__":
    unittest.main()
