"""Equal-denominator rule: only a fully scored model may hold an official rank."""

import copy
import unittest

from src import config, leaderboard, runner


def _dry_run_document() -> tuple[dict, dict, dict]:
    pool = runner.load_model_pool()
    cases_document = runner.load_test_cases()
    document = runner.run_benchmark(
        cases_document,
        pool,
        dry_run=True,
        fx_snapshot=config.SYNTHETIC_FX_SNAPSHOT,
    )
    return document, pool, cases_document


def _fail_one_case(results: list[dict], model_key: str, case_id: str) -> None:
    """Simulate a permanent failure for one (model, case) pair."""
    for row in results:
        if row["model_key"] == model_key and row["case_id"] == case_id:
            row["aggregate"] = None
            row["error"] = "simulated permanent failure"
            return
    raise AssertionError(f"no result row for {model_key}/{case_id}")


class TestEqualDenominatorRanking(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document, cls.pool, cls.cases_document = _dry_run_document()
        cls.required = cls.document["dataset"]["case_count"]

    def test_fully_scored_run_is_rank_eligible(self):
        official = self.document["summary"]["official_ranking"]
        self.assertTrue(official["complete_run"])
        self.assertEqual(official["incomplete_models"], [])
        self.assertEqual(len(official["ranked_models"]), 10)
        for row in self.document["summary"]["models"]:
            self.assertTrue(row["rank_eligible"], msg=row["model_key"])
            self.assertIsNotNone(row["rank"])
            self.assertEqual(row["cases_scored"], self.required)
            self.assertIsNone(row["incomplete_reason"])

    def test_ranks_are_contiguous_when_every_model_qualifies(self):
        ranks = sorted(row["rank"] for row in self.document["summary"]["models"])
        self.assertEqual(ranks, list(range(1, len(ranks) + 1)))

    def test_required_cases_matches_the_dataset(self):
        self.assertEqual(
            self.document["summary"]["official_ranking"]["required_cases"],
            len(self.cases_document["test_cases"]),
        )

    def test_incomplete_model_loses_rank_eligibility(self):
        results = copy.deepcopy(self.document["results"])
        victim = results[0]["model_key"]
        _fail_one_case(results, victim, self.cases_document["test_cases"][0]["id"])

        summary = runner.summarize(results, self.pool, required_cases=self.required)
        victim_row = next(row for row in summary["models"] if row["model_key"] == victim)

        self.assertFalse(victim_row["rank_eligible"])
        self.assertIsNone(victim_row["rank"])
        self.assertEqual(victim_row["cases_scored"], self.required - 1)
        self.assertIsNotNone(victim_row["incomplete_reason"])

    def test_incomplete_model_is_listed_but_not_ranked(self):
        results = copy.deepcopy(self.document["results"])
        victim = results[0]["model_key"]
        _fail_one_case(results, victim, self.cases_document["test_cases"][0]["id"])

        official = runner.summarize(
            results, self.pool, required_cases=self.required
        )["official_ranking"]

        self.assertFalse(official["complete_run"])
        self.assertNotIn(victim, official["ranked_models"])
        self.assertIn(victim, [item["model_key"] for item in official["incomplete_models"]])
        entry = next(
            item for item in official["incomplete_models"] if item["model_key"] == victim
        )
        self.assertEqual(entry["cases_scored"], self.required - 1)
        self.assertEqual(entry["cases_required"], self.required)
        self.assertIn("valid score", entry["reason"])

    def test_remaining_models_keep_contiguous_ranks(self):
        results = copy.deepcopy(self.document["results"])
        victim = results[0]["model_key"]
        _fail_one_case(results, victim, self.cases_document["test_cases"][0]["id"])

        summary = runner.summarize(results, self.pool, required_cases=self.required)
        others = [row for row in summary["models"] if row["model_key"] != victim]
        self.assertTrue(all(row["rank_eligible"] for row in others))
        self.assertEqual(
            sorted(row["rank"] for row in others), list(range(1, len(others) + 1))
        )

    def test_incomplete_model_is_excluded_from_the_pareto_frontier(self):
        results = copy.deepcopy(self.document["results"])
        victim = results[0]["model_key"]
        _fail_one_case(results, victim, self.cases_document["test_cases"][0]["id"])

        pareto = runner.summarize(
            results, self.pool, required_cases=self.required
        )["pareto"]["quality_cost"]

        self.assertNotIn(victim, pareto["frontier"])
        self.assertNotIn(victim, pareto["not_evaluated"])
        self.assertNotIn(victim, pareto["dominated"])

    def test_partial_metrics_remain_visible_as_diagnostics(self):
        results = copy.deepcopy(self.document["results"])
        victim = results[0]["model_key"]
        _fail_one_case(results, victim, self.cases_document["test_cases"][0]["id"])

        summary = runner.summarize(results, self.pool, required_cases=self.required)
        victim_row = next(row for row in summary["models"] if row["model_key"] == victim)

        # A diagnostic score still exists; it simply does not carry an official rank.
        self.assertIsNotNone(victim_row["overall_score"])
        self.assertEqual(victim_row["cases_total"], self.required)
        self.assertEqual(victim_row["cases_scored"], self.required - 1)

    def test_incomplete_model_suppresses_comparative_cost_metrics(self):
        results = copy.deepcopy(self.document["results"])
        victim = results[0]["model_key"]
        _fail_one_case(results, victim, self.cases_document["test_cases"][0]["id"])

        summary = runner.summarize(results, self.pool, required_cases=self.required)
        victim_row = next(row for row in summary["models"] if row["model_key"] == victim)

        # Comparative metrics require equal denominators and are suppressed.
        self.assertIsNone(victim_row["cost_per_100_tasks_cny"])
        self.assertIsNone(victim_row["quality_per_cny"])
        self.assertFalse(victim_row["comparative_metrics_available"])
        for name in ("cost_per_100_tasks_cny", "quality_per_cny", "official_rank"):
            self.assertIn(name, victim_row["unavailable_metrics"])

        # Fully scored models keep their comparative metrics.
        for row in summary["models"]:
            if row["model_key"] == victim:
                continue
            self.assertIsNotNone(row["cost_per_100_tasks_cny"])
            self.assertIsNotNone(row["quality_per_cny"])
            self.assertTrue(row["comparative_metrics_available"])
            self.assertEqual(row["unavailable_metrics"], [])

    def test_incomplete_model_keeps_diagnostic_fields(self):
        results = copy.deepcopy(self.document["results"])
        victim = results[0]["model_key"]
        _fail_one_case(results, victim, self.cases_document["test_cases"][0]["id"])

        summary = runner.summarize(results, self.pool, required_cases=self.required)
        victim_row = next(row for row in summary["models"] if row["model_key"] == victim)

        # Actual spend, completed calls/cases, and partial usage stay visible.
        self.assertIsNotNone(victim_row["actual_spend_cny"])
        self.assertEqual(victim_row["actual_spend_cny"], victim_row["candidate_cost_cny"])
        self.assertEqual(victim_row["cases_completed"], self.required - 1)
        self.assertEqual(victim_row["calls_completed"], self.required - 1)
        self.assertIsNotNone(victim_row["tokens"]["total"])
        self.assertIsNotNone(victim_row["latency"]["samples"])

    def test_metric_availability_block_flags_an_incomplete_run(self):
        results = copy.deepcopy(self.document["results"])
        victim = results[0]["model_key"]
        _fail_one_case(results, victim, self.cases_document["test_cases"][0]["id"])

        availability = runner.summarize(
            results, self.pool, required_cases=self.required
        )["metric_availability"]

        self.assertFalse(availability["run_complete"])
        self.assertIn(victim, availability["suppressed_for_incomplete_models"])
        self.assertIn("cost_per_100_tasks_cny", availability["comparative_metrics"])
        self.assertIn("actual_spend_cny", availability["diagnostic_metrics"])

    def test_complete_run_keeps_every_comparative_metric(self):
        availability = self.document["summary"]["metric_availability"]
        self.assertTrue(availability["run_complete"])
        self.assertEqual(availability["suppressed_for_incomplete_models"], [])
        for row in self.document["summary"]["models"]:
            self.assertTrue(row["comparative_metrics_available"])
            self.assertEqual(row["unavailable_metrics"], [])
            self.assertIsNotNone(row["cost_per_100_tasks_cny"])

    def test_leaderboard_marks_suppressed_metrics_as_unavailable(self):
        results = copy.deepcopy(self.document["results"])
        victim = results[0]["model_key"]
        _fail_one_case(results, victim, self.cases_document["test_cases"][0]["id"])

        document = copy.deepcopy(self.document)
        document["summary"] = runner.summarize(
            results, self.pool, required_cases=self.required
        )
        html = leaderboard.render(document)

        self.assertIn("n/a — run incomplete", html)
        self.assertIn("OFFICIAL RANKING INCOMPLETE", html)

    def test_judge_unavailable_case_makes_a_model_incomplete(self):
        results = copy.deepcopy(self.document["results"])
        victim = results[0]["model_key"]
        for row in results:
            if row["model_key"] == victim and row["case_id"] == self.cases_document["test_cases"][1]["id"]:
                row["judgements"] = []
                row["aggregate"] = None
                row["judge_available_reason"] = None
                row["judge_unavailable_reason"] = "fewer than two cross-family judges"

        summary = runner.summarize(results, self.pool, required_cases=self.required)
        victim_row = next(row for row in summary["models"] if row["model_key"] == victim)
        self.assertFalse(victim_row["rank_eligible"])
        self.assertEqual(victim_row["judge_unavailable_cases"], 1)
        self.assertIn("judge-unavailable", victim_row["incomplete_reason"])

    def test_required_cases_defaults_to_the_observed_case_count(self):
        summary = runner.summarize(self.document["results"], self.pool)
        self.assertEqual(
            summary["official_ranking"]["required_cases"], self.required
        )
        self.assertTrue(summary["official_ranking"]["complete_run"])


if __name__ == "__main__":
    unittest.main()
