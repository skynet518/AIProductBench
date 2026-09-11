"""Phase 4A live-benchmark readiness — offline-only invariants.

Pins the frozen dataset, the model-registry contract, pricing/FX snapshot
schemas, the cross-family judge mapping, and incomplete-model accounting.
No test in this module makes a network or provider call.
"""

import copy
import hashlib
import json
import unittest
from pathlib import Path

from src import config, judge, models, pricing, runner

ROOT = Path(__file__).resolve().parent.parent
FREEZE_MANIFEST = ROOT / "docs" / "DATASET_FREEZE_V1.md"
MANIFEST_SHA256 = "6b450383e528a5a0a6b813112f96182a3625c04c948839fc551c8ded63da513c"

REGISTRY_CONTRACT_FIELDS = (
    "key",  # logical_model_id
    "provider",
    "provider_key",
    "model_id",  # provider_model_id
    "display_name",
    "model_family",
    "product_tier",  # tier
    "enabled",
    "thinking_mode",
    "thinking_config",
    "model_id_status",  # model_id_verified
    "model_id_verified_as_of",
)
PRICING_CONTRACT_FIELDS = (
    "input",
    "output",
    "reasoning",
    "cached_input",
    "native_currency",
    "unit",
    "snapshot_date",
    "source",
)

EXPECTED_JUDGE_FAMILIES = {
    "Qwen": ["DeepSeek", "GLM"],
    "DeepSeek": ["Qwen", "GLM"],
    "Kimi": ["Qwen", "DeepSeek"],
    "MiniMax": ["Qwen", "DeepSeek"],
    "GLM": ["Qwen", "DeepSeek"],
    "Doubao": ["Qwen", "DeepSeek"],
}


def object_hash(obj) -> str:
    blob = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def load_production_document() -> dict:
    with open(config.PRODUCTION_CASES_FILE, encoding="utf-8") as handle:
        return json.load(handle)


def parse_manifest_doc() -> dict:
    text = FREEZE_MANIFEST.read_text(encoding="utf-8")
    import re

    block = re.search(r"```text\n(.*?)```", text, re.DOTALL).group(1)
    return dict(line.split() for line in block.splitlines() if line.strip())


class TestFrozenDatasetIntact(unittest.TestCase):
    def test_semantic_manifest_hash_unchanged(self):
        case_list = load_production_document()["test_cases"]
        manifest = "\n".join(
            f"{c['id']} {object_hash(c)}" for c in sorted(case_list, key=lambda c: c["id"])
        ) + "\n"
        self.assertEqual(hashlib.sha256(manifest.encode("utf-8")).hexdigest(), MANIFEST_SHA256)

    def test_every_production_case_matches_the_freeze_manifest(self):
        recorded = parse_manifest_doc()
        cases = load_production_document()["test_cases"]
        self.assertEqual(len(cases), 50)
        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertEqual(recorded[case["id"]], object_hash(case))

    def test_production_status_is_complete(self):
        self.assertEqual(load_production_document()["production_status"], "complete")


class TestRegistryContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pool = models.load_model_pool()

    def test_pool_validates_with_no_errors(self):
        self.assertEqual(models.validate_model_pool(self.pool)["errors"], [])

    def test_ten_logical_slots_have_verified_literal_ids(self):
        entries = self.pool["models"]
        self.assertEqual(len(entries), 10)
        for model in entries:
            with self.subTest(model=model["key"]):
                self.assertTrue(model["model_id"])
                self.assertEqual(model["model_id_status"], "verified")
                self.assertEqual(model["model_id_verified_as_of"], "2026-09-11")

    def test_registry_represents_the_full_contract(self):
        for model in self.pool["models"]:
            with self.subTest(model=model["key"]):
                for field in REGISTRY_CONTRACT_FIELDS:
                    self.assertIn(field, model)
                for field in PRICING_CONTRACT_FIELDS:
                    self.assertIn(field, model["pricing"])
                self.assertIsInstance(model["enabled"], bool)
                self.assertIsInstance(model["thinking_config"], (dict, type(None)))

    def test_operator_count_still_21(self):
        from src import deterministic

        self.assertEqual(len(deterministic.SUPPORTED_CHECK_TYPES), 21)


class TestPricingAndFxContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pool = models.load_model_pool()

    def test_production_fx_snapshot_validates(self):
        self.assertEqual(pricing.validate_fx_snapshot(config.FX_SNAPSHOT), [])

    def test_synthetic_fx_snapshot_validates(self):
        self.assertEqual(pricing.validate_fx_snapshot(config.SYNTHETIC_FX_SNAPSHOT), [])

    def test_verified_fx_snapshot_converts_usd(self):
        result = pricing.normalize_to_cny(1.0, "USD", config.FX_SNAPSHOT)
        self.assertEqual(result["normalization_method"], "fx")
        self.assertAlmostEqual(result["normalized_cost_cny"], 7.7900 / 1.1616, places=6)

    def test_missing_fx_snapshot_leaves_cny_null(self):
        result = pricing.normalize_to_cny(1.0, "USD", None)
        self.assertIsNone(result["normalized_cost_cny"])
        self.assertEqual(result["normalization_method"], "unavailable")

    def test_production_pricing_snapshot_validates(self):
        snapshot = pricing.pricing_snapshot(
            self.pool["models"], config.FX_SNAPSHOT, synthetic=False
        )
        self.assertEqual(pricing.validate_pricing_snapshot(snapshot), [])

    def test_synthetic_pricing_snapshot_validates(self):
        snapshot = pricing.pricing_snapshot(
            self.pool["models"], config.SYNTHETIC_FX_SNAPSHOT, synthetic=True
        )
        self.assertEqual(pricing.validate_pricing_snapshot(snapshot), [])

    def test_verified_pricing_requires_a_verified_model_id(self):
        pool = copy.deepcopy(self.pool)
        model = pool["models"][0]
        model["pricing"]["status"] = "verified"
        model["pricing"]["input"] = 1.0
        model["pricing"]["output"] = 2.0
        model["pricing"]["native_currency"] = "USD"
        model["model_id_status"] = "unverified"
        model["model_id"] = None
        model["model_id_verified_as_of"] = None
        errors = models.validate_model_pool(pool)["errors"]
        self.assertTrue(any("unverified model ID" in error for error in errors))


class TestJudgeMapping(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pool = models.load_model_pool()
        cls.pool_judges = models.judges(cls.pool)
        cls.priority = models.judge_priority(cls.pool)

    def test_expected_cross_family_mapping(self):
        by_family = {}
        for candidate in models.candidates(self.pool):
            selected = judge.select_judges(candidate, self.pool_judges, self.priority)
            by_family.setdefault(
                candidate["model_family"], [j["model_family"] for j in selected]
            )
        self.assertEqual(by_family, EXPECTED_JUDGE_FAMILIES)

    def test_no_same_family_judge_and_exactly_two_judges(self):
        for candidate in models.candidates(self.pool):
            selected = judge.select_judges(candidate, self.pool_judges, self.priority)
            with self.subTest(candidate=candidate["key"]):
                self.assertEqual(len(selected), 2)
                families = [j["model_family"] for j in selected]
                self.assertNotIn(candidate["model_family"], families)
                self.assertEqual(len(set(families)), 2)

    def test_insufficient_cross_family_judges_are_unavailable(self):
        candidate = {"model_family": "Kimi", "provider_key": "moonshot"}
        only_one = [j for j in self.pool_judges if j["model_family"] == "Qwen"]
        self.assertEqual(judge.select_judges(candidate, only_one, self.priority), [])


class TestIncompleteModelRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pool = models.load_model_pool()
        cls.cases_document = load_production_document()
        cls.document = runner.run_benchmark(
            copy.deepcopy(cls.cases_document),
            cls.pool,
            dry_run=True,
            fx_snapshot=config.SYNTHETIC_FX_SNAPSHOT,
        )
        cls.required = cls.document["dataset"]["case_count"]

    def _incomplete_summary(self) -> dict:
        results = copy.deepcopy(self.document["results"])
        victim = results[0]["model_key"]
        target = self.cases_document["test_cases"][0]["id"]
        for row in results:
            if row["model_key"] == victim and row["case_id"] == target:
                row["aggregate"] = None
                row["error"] = "simulated permanent failure"
                break
        else:
            raise AssertionError("no matching result row")
        return runner.summarize(results, self.pool, required_cases=self.required)

    def test_incomplete_model_suppresses_official_metrics(self):
        summary = self._incomplete_summary()
        row = next(r for r in summary["models"] if not r["rank_eligible"])
        self.assertIsNone(row["rank"])
        self.assertIsNone(row["cost_per_100_tasks_cny"])
        self.assertIsNone(row["quality_per_cny"])
        self.assertFalse(row["comparative_metrics_available"])
        self.assertIn("official_rank", row["unavailable_metrics"])
        self.assertIsNotNone(row["incomplete_reason"])
        self.assertFalse(summary["official_ranking"]["complete_run"])

    def test_incomplete_model_retains_diagnostics(self):
        summary = self._incomplete_summary()
        row = next(r for r in summary["models"] if not r["rank_eligible"])
        self.assertIsNotNone(row["actual_spend_cny"])
        self.assertIsNotNone(row["calls_completed"])
        self.assertIsNotNone(row["cases_completed"])
        self.assertIsNotNone(row["tokens"])


if __name__ == "__main__":
    unittest.main()
