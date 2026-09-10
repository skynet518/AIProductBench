"""One shared model registry, and the V1 pricing reset."""

import copy
import unittest

from src import models, pricing, runner


def minimal_pool() -> dict:
    """A tiny valid-shaped pool used for targeted validation tests."""
    return {
        "pool_version": "test",
        "judge_priority": ["j_qwen", "j_deepseek"],
        "models": [
            {
                "key": "j_qwen",
                "display_name": "Qwen judge",
                "model_family": "Qwen",
                "provider": "Alibaba Model Studio",
                "provider_key": "alibaba_model_studio",
                "product_tier": "flagship",
                "inference_channel": "native",
                "thinking_mode": "provider_default",
                "model_id": "qwen-test",
                "model_id_status": "verified",
                "base_url": "https://example.invalid/v1",
                "api_key_env": "DASHSCOPE_API_KEY",
                "wire_api": "chat_completions",
                "temperature": 0.0,
                "candidate": True,
                "judge_eligible": True,
                "pricing": {
                    "status": "unverified",
                    "native_currency": None,
                    "input": None,
                    "output": None,
                },
            },
            {
                "key": "j_deepseek",
                "display_name": "DeepSeek judge",
                "model_family": "DeepSeek",
                "provider": "DeepSeek",
                "provider_key": "deepseek",
                "product_tier": "flagship",
                "inference_channel": "native",
                "thinking_mode": "provider_default",
                "model_id": "deepseek-test",
                "model_id_status": "verified",
                "base_url": "https://example.invalid/v1",
                "api_key_env": "DEEPSEEK_API_KEY",
                "wire_api": "chat_completions",
                "temperature": 0.0,
                "candidate": True,
                "judge_eligible": True,
                "pricing": {
                    "status": "unverified",
                    "native_currency": None,
                    "input": None,
                    "output": None,
                },
            },
        ],
    }


class TestConfiguredRegistry(unittest.TestCase):
    def setUp(self):
        self.pool = runner.load_model_pool()

    def test_pool_is_valid(self):
        self.assertEqual(models.validate_model_pool(self.pool)["errors"], [])

    def test_ten_candidates_across_six_families_and_providers(self):
        facts = models.pool_facts(self.pool)
        self.assertEqual(facts["candidate_count"], 10)
        self.assertEqual(len(facts["families"]), 6)
        self.assertEqual(len(facts["providers"]), 6)

    def test_three_judges_sharing_the_same_registry(self):
        facts = models.pool_facts(self.pool)
        self.assertEqual(facts["judge_count"], 3)
        self.assertEqual(facts["registry_size"], 10)
        self.assertEqual(len(facts["judge_families"]), 3)

    def test_judge_entries_are_not_judge_only_duplicates(self):
        for entry in models.judges(self.pool):
            self.assertTrue(entry["candidate"], msg=entry["key"])

    def test_no_two_entries_share_family_and_tier(self):
        slots = [
            (entry["model_family"], entry["product_tier"]) for entry in self.pool["models"]
        ]
        self.assertEqual(len(slots), len(set(slots)))

    def test_duplicate_family_and_tier_is_rejected(self):
        pool = minimal_pool()
        clone = copy.deepcopy(pool["models"][0])
        clone["key"] = "j_qwen_duplicate"
        clone["judge_eligible"] = False
        pool["models"].append(clone)
        errors = models.validate_model_pool(pool)["errors"]
        self.assertTrue(any("Duplicate registry entries" in error for error in errors))

    def test_judge_priority_is_validated(self):
        pool = minimal_pool()
        pool["judge_priority"] = ["j_qwen", "not_a_real_model"]
        errors = models.validate_model_pool(pool)["errors"]
        self.assertTrue(any("not_a_real_model" in error for error in errors))

    def test_missing_judge_priority_is_rejected(self):
        pool = minimal_pool()
        pool.pop("judge_priority")
        errors = models.validate_model_pool(pool)["errors"]
        self.assertTrue(any("judge_priority" in error for error in errors))


class TestPricingReset(unittest.TestCase):
    def setUp(self):
        self.pool = runner.load_model_pool()

    def test_no_active_v1_pricing_is_verified(self):
        for entry in self.pool["models"]:
            self.assertEqual(entry["pricing"]["status"], "unverified", msg=entry["key"])

    def test_no_active_v1_model_carries_numeric_rates(self):
        for entry in self.pool["models"]:
            self.assertIsNone(entry["pricing"]["input"], msg=entry["key"])
            self.assertIsNone(entry["pricing"]["output"], msg=entry["key"])
            self.assertIsNone(entry["pricing"]["native_currency"], msg=entry["key"])

    def test_historical_archive_exists_and_is_inactive(self):
        archive = models.historical_pricing(self.pool)
        self.assertEqual(archive["status"], "historical_inactive")
        self.assertEqual(len(archive["entries"]), 3)
        self.assertIn("NOT V1 pricing", archive["note"])

    def test_archived_entries_reference_v0_1_model_ids_only(self):
        archived_ids = models.archived_pricing_model_ids(self.pool)
        self.assertEqual(
            archived_ids,
            {"qwen3.7-flash-2026-07-15", "qwen3.7-max-2026-05-20", "deepseek-v4-flash"},
        )
        active_ids = {entry.get("model_id") for entry in self.pool["models"]}
        self.assertEqual(archived_ids & active_ids, set())

    def test_archived_pricing_block_cannot_be_priced(self):
        archived = models.historical_pricing(self.pool)["entries"][0]
        entry = {
            "key": "leaked",
            "display_name": "leaked",
            "model_family": "Qwen",
            "provider": "Alibaba Model Studio",
            "provider_key": "alibaba_model_studio",
            "model_id": archived["applies_to_model_id"],
            "pricing": {**archived, "status": "historical_inactive"},
        }
        with self.assertRaises(pricing.PricingError):
            pricing.effective_pricing(entry)
        with self.assertRaises(pricing.PricingError):
            pricing.native_price_call(entry, 1000, 1000)

    def test_archived_pricing_referenced_by_an_active_model_is_rejected(self):
        pool = minimal_pool()
        model = pool["models"][0]
        model["model_id"] = "qwen3.7-flash-2026-07-15"
        model["pricing"] = {
            "status": "verified",
            "snapshot_date": "2026-09-11",
            "native_currency": "USD",
            "input": 0.028,
            "output": 0.11,
            "applies_to_model_id": "qwen3.7-flash-2026-07-15",
            "time_of_day": None,
            "input_tier_limit_tokens": None,
            "notes": [],
        }
        pool["historical_pricing_archive"] = models.historical_pricing(self.pool)
        errors = models.validate_model_pool(pool)["errors"]
        self.assertTrue(any("must not leak into V1" in error for error in errors), msg=errors)

    def test_verified_pricing_with_unverified_model_id_is_rejected(self):
        pool = minimal_pool()
        model = pool["models"][0]
        model["model_id_status"] = "unverified"
        model["model_id"] = None
        model["pricing"] = {
            "status": "verified",
            "snapshot_date": "2026-09-11",
            "native_currency": "CNY",
            "input": 1.0,
            "output": 2.0,
            "applies_to_model_id": None,
            "time_of_day": None,
            "input_tier_limit_tokens": None,
            "notes": [],
        }
        errors = models.validate_model_pool(pool)["errors"]
        self.assertTrue(any("unverified model ID" in error for error in errors), msg=errors)

    def test_unresolved_pricing_blocks_a_paid_run(self):
        blockers = runner.check_ready_for_paid_run(self.pool)
        self.assertTrue(any("Unresolved active V1 pricing" in item for item in blockers))

    def test_no_model_is_priced_in_the_configured_pool(self):
        self.assertEqual(models.priced_models(self.pool), [])

    def test_cost_estimation_reports_unpriced_not_zero(self):
        result = pricing.price_call(self.pool["models"][0], 1000, 500, fx_snapshot=None)
        self.assertIsNone(result["native_cost"])
        self.assertIsNone(result["normalized_cost_cny"])
        self.assertIsNotNone(result["cost_error"])

    def test_documentation_snapshot_records_archived_pricing_as_unused(self):
        document = runner.run_benchmark(
            runner.load_test_cases(),
            self.pool,
            dry_run=True,
            fx_snapshot=None,
        )
        self.assertFalse(document["historical_pricing"]["used_for_v1_cost"])
        self.assertEqual(document["historical_pricing"]["status"], "historical_inactive")
        self.assertEqual(document["historical_pricing"]["entry_count"], 3)


if __name__ == "__main__":
    unittest.main()
