"""End-to-end dry-run behaviour: network isolation, cost separation, dual judging."""

import socket
import unittest

import requests

from src import config, providers, runner


def _blocked(*args, **kwargs):
    raise AssertionError("outbound network access attempted during an offline run")


class TestDryRunIsolation(unittest.TestCase):
    """A dry run must make zero external calls and incur zero real cost."""

    def setUp(self):
        self._original_connect = socket.socket.connect
        self._original_create = socket.create_connection
        self._original_post = requests.post
        socket.socket.connect = _blocked
        socket.create_connection = _blocked
        requests.post = _blocked

    def tearDown(self):
        socket.socket.connect = self._original_connect
        socket.create_connection = self._original_create
        requests.post = self._original_post

    def _run(self) -> dict:
        pool = runner.load_model_pool()
        case_document = runner.load_test_cases()
        return runner.run_benchmark(
            case_document,
            pool,
            dry_run=True,
            fx_snapshot=config.SYNTHETIC_FX_SNAPSHOT,
        )

    def test_dry_run_completes_without_network(self):
        document = self._run()
        self.assertTrue(document["synthetic"])
        self.assertEqual(document["failures"], [])

    def test_every_result_is_flagged_synthetic(self):
        document = self._run()
        self.assertTrue(document["results"])
        for record in document["results"]:
            self.assertTrue(record["synthetic"])
            for verdict in record["judgements"]:
                self.assertTrue(verdict["synthetic"])

    def test_pricing_snapshot_is_marked_synthetic(self):
        document = self._run()
        self.assertTrue(document["pricing_snapshot"]["synthetic"])
        self.assertTrue(document["pricing_snapshot"]["fx_snapshot"]["synthetic"])


class TestPipelineShape(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pool = runner.load_model_pool()
        cls.case_document = runner.load_test_cases()
        cls.document = runner.run_benchmark(
            cls.case_document,
            cls.pool,
            dry_run=True,
            fx_snapshot=config.SYNTHETIC_FX_SNAPSHOT,
        )

    def test_call_counts_match_configuration(self):
        case_count = self.document["dataset"]["case_count"]
        candidate_count = self.document["model_pool"]["candidate_count"]
        expected_candidate_calls = case_count * candidate_count
        expected_judge_calls = expected_candidate_calls * config.JUDGES_PER_RESPONSE
        self.assertEqual(
            self.document["summary"]["totals"]["candidate_calls"], expected_candidate_calls
        )
        self.assertEqual(
            self.document["summary"]["totals"]["judge_calls"], expected_judge_calls
        )

    def test_every_response_has_exactly_two_judgements(self):
        for record in self.document["results"]:
            self.assertEqual(
                len(record["judgements"]), config.JUDGES_PER_RESPONSE, msg=record["case_id"]
            )

    def test_no_judge_shares_the_candidate_provider(self):
        for record in self.document["results"]:
            for verdict in record["judgements"]:
                self.assertNotEqual(verdict["judge_provider"], record["provider"])
                self.assertNotEqual(verdict["judge_family"], record["model_family"])

    def test_two_judges_are_cross_family(self):
        for record in self.document["results"]:
            families = {verdict["judge_family"] for verdict in record["judgements"]}
            self.assertEqual(len(families), config.JUDGES_PER_RESPONSE)

    def test_each_candidate_uses_the_configured_fixed_judge_pair(self):
        expected = {
            "Qwen": ["deepseek_flagship", "glm_flagship"],
            "DeepSeek": ["qwen_flagship", "glm_flagship"],
            "GLM": ["qwen_flagship", "deepseek_flagship"],
            "Kimi": ["qwen_flagship", "deepseek_flagship"],
            "MiniMax": ["qwen_flagship", "deepseek_flagship"],
            "Doubao": ["qwen_flagship", "deepseek_flagship"],
        }
        for record in self.document["results"]:
            actual = [verdict["judge_key"] for verdict in record["judgements"]]
            self.assertEqual(
                actual, expected[record["model_family"]], msg=record["case_id"]
            )

    def test_judge_pair_does_not_vary_between_cases_for_the_same_candidate(self):
        seen: dict[str, list[str]] = {}
        for record in self.document["results"]:
            pair = [verdict["judge_key"] for verdict in record["judgements"]]
            if record["model_key"] in seen:
                self.assertEqual(seen[record["model_key"]], pair, msg=record["model_key"])
            seen[record["model_key"]] = pair

    def test_candidate_and_judge_costs_are_separate_fields(self):
        totals = self.document["summary"]["totals"]
        self.assertIn("candidate_cost_cny", totals)
        self.assertIn("judge_cost_cny", totals)
        for row in self.document["summary"]["models"]:
            self.assertIn("candidate_cost_cny", row)
            self.assertIn("judge_cost_cny", row)

    def test_judge_cost_is_not_folded_into_candidate_cost(self):
        for row in self.document["summary"]["models"]:
            if row["candidate_cost_cny"] is None or row["judge_cost_cny"] is None:
                continue
            records = [
                record
                for record in self.document["results"]
                if record["model_key"] == row["model_key"]
            ]
            candidate_only = sum(
                record["normalized_cost_cny"]
                for record in records
                if record["normalized_cost_cny"] is not None
            )
            self.assertAlmostEqual(row["candidate_cost_cny"], candidate_only, places=6)

    def test_summary_includes_latency_percentiles(self):
        for row in self.document["summary"]["models"]:
            self.assertIn("p50_latency_ms", row["latency"])
            self.assertIn("p95_latency_ms", row["latency"])
            self.assertIsNotNone(row["latency"]["p50_latency_ms"])
            self.assertIsNotNone(row["latency"]["p95_latency_ms"])

    def test_deterministic_checks_were_evaluated(self):
        checked = [
            record
            for record in self.document["results"]
            if record["deterministic"] and record["deterministic"]["checks_total"] > 0
        ]
        self.assertTrue(checked)
        for record in checked:
            self.assertIsNotNone(record["deterministic"]["constraint_pass_rate"])

    def test_judge_agreement_is_reported_for_scored_responses(self):
        agreements = [
            record["judge_agreement"]
            for record in self.document["results"]
            if record["judge_agreement"]
        ]
        self.assertTrue(agreements)
        for agreement in agreements:
            self.assertEqual(agreement["judges"], config.JUDGES_PER_RESPONSE)

    def test_pareto_frontier_is_present(self):
        pareto = self.document["summary"]["pareto"]
        self.assertIn("quality_cost", pareto)
        self.assertTrue(pareto["quality_cost"]["frontier"])
        self.assertEqual(len(pareto["quality_cost"]["objectives"]), 2)

    def test_snapshot_metadata_is_versioned(self):
        self.assertTrue(self.document["snapshot_id"])
        self.assertIn("synthetic", self.document["snapshot_id"])
        self.assertEqual(self.document["benchmark_version"], config.BENCHMARK_VERSION)


class TestPaidRunGate(unittest.TestCase):
    def test_unverified_ids_block_a_paid_run(self):
        pool = runner.load_model_pool()
        blockers = runner.check_ready_for_paid_run(pool)
        self.assertTrue(blockers)
        self.assertIn("Unverified model IDs", blockers[0])

    def test_real_call_refuses_an_unverified_model(self):
        pool = runner.load_model_pool()
        entry = pool["models"][0]
        self.assertIsNone(entry["model_id"])
        with self.assertRaises(providers.ProviderError):
            providers.resolve_model_id(entry)

    def test_credentials_come_from_environment_only(self):
        pool = runner.load_model_pool()
        for model in pool["models"]:
            self.assertTrue(model["api_key_env"].isupper())
            self.assertNotIn("/", model["api_key_env"])


if __name__ == "__main__":
    unittest.main()
