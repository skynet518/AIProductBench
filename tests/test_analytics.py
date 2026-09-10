"""Latency percentiles, cost metrics, and Pareto frontier computation."""

import unittest

from src import analytics


def row(key, score, cost, p95=None) -> dict:
    return {
        "model_key": key,
        "overall_score": score,
        "cost_per_100_tasks_cny": cost,
        "p95_latency_ms": p95,
    }


class TestLatency(unittest.TestCase):
    def test_percentile_interpolates(self):
        self.assertEqual(analytics.percentile([10, 20, 30, 40], 0.5), 25.0)
        self.assertEqual(analytics.percentile([10, 20, 30, 40], 0.0), 10.0)
        self.assertEqual(analytics.percentile([10, 20, 30, 40], 1.0), 40.0)

    def test_percentile_ignores_missing_values(self):
        self.assertEqual(analytics.percentile([10, None, 30], 0.0), 10.0)
        self.assertIsNone(analytics.percentile([], 0.5))
        self.assertIsNone(analytics.percentile([None, None], 0.5))

    def test_latency_stats(self):
        stats = analytics.latency_stats([100, 200, 300, 400])
        self.assertEqual(stats["samples"], 4)
        self.assertEqual(stats["avg_latency_ms"], 250.0)
        self.assertEqual(stats["p50_latency_ms"], 250.0)
        self.assertEqual(stats["p95_latency_ms"], 385.0)
        self.assertEqual(stats["max_latency_ms"], 400)

    def test_latency_stats_without_data(self):
        stats = analytics.latency_stats([])
        self.assertEqual(stats["samples"], 0)
        self.assertIsNone(stats["avg_latency_ms"])
        self.assertIsNone(stats["p95_latency_ms"])


class TestCostMetrics(unittest.TestCase):
    def test_cost_per_100_tasks(self):
        self.assertEqual(analytics.cost_per_100_tasks(1.0, 10), 10.0)
        self.assertEqual(analytics.cost_per_100_tasks(0.5, 50), 1.0)

    def test_cost_per_100_tasks_handles_missing_inputs(self):
        self.assertIsNone(analytics.cost_per_100_tasks(None, 10))
        self.assertIsNone(analytics.cost_per_100_tasks(1.0, 0))

    def test_quality_per_cny(self):
        self.assertEqual(analytics.quality_per_cny(80.0, 2.0), 40.0)
        self.assertEqual(analytics.quality_per_cny(80.0, 0.5), 160.0)

    def test_quality_per_cny_handles_missing_inputs(self):
        self.assertIsNone(analytics.quality_per_cny(None, 1.0))
        self.assertIsNone(analytics.quality_per_cny(80.0, None))
        self.assertIsNone(analytics.quality_per_cny(80.0, 0.0))


class TestDominance(unittest.TestCase):
    OBJECTIVES = [("overall_score", "max"), ("cost_per_100_tasks_cny", "min")]

    def test_strictly_better_on_both_dominates(self):
        self.assertTrue(
            analytics.dominates(row("a", 90, 1.0), row("b", 80, 2.0), self.OBJECTIVES)
        )

    def test_equal_on_one_better_on_other_dominates(self):
        self.assertTrue(
            analytics.dominates(row("a", 90, 2.0), row("b", 90, 3.0), self.OBJECTIVES)
        )

    def test_tradeoff_does_not_dominate(self):
        self.assertFalse(
            analytics.dominates(row("a", 95, 5.0), row("b", 80, 1.0), self.OBJECTIVES)
        )
        self.assertFalse(
            analytics.dominates(row("a", 80, 1.0), row("b", 95, 5.0), self.OBJECTIVES)
        )

    def test_identical_rows_do_not_dominate(self):
        self.assertFalse(
            analytics.dominates(row("a", 80, 1.0), row("b", 80, 1.0), self.OBJECTIVES)
        )

    def test_missing_value_cannot_dominate(self):
        self.assertFalse(
            analytics.dominates(row("a", None, 1.0), row("b", 80, 2.0), self.OBJECTIVES)
        )


class TestParetoFrontier(unittest.TestCase):
    OBJECTIVES = [("overall_score", "max"), ("cost_per_100_tasks_cny", "min")]

    def test_frontier_keeps_tradeoff_models(self):
        rows = [
            row("premium", 90, 10.0),
            row("balanced", 85, 5.0),
            row("cheap", 70, 1.0),
        ]
        result = analytics.pareto_frontier(rows, self.OBJECTIVES)
        self.assertEqual(sorted(result["frontier"]), ["balanced", "cheap", "premium"])
        self.assertEqual(result["dominated"], {})

    def test_dominated_model_names_its_dominator(self):
        rows = [
            row("winner", 90, 5.0),
            row("loser", 80, 6.0),
        ]
        result = analytics.pareto_frontier(rows, self.OBJECTIVES)
        self.assertEqual(result["frontier"], ["winner"])
        self.assertEqual(result["dominated"], {"loser": "winner"})

    def test_tie_is_not_dominated(self):
        rows = [row("a", 80, 5.0), row("b", 80, 5.0)]
        result = analytics.pareto_frontier(rows, self.OBJECTIVES)
        self.assertEqual(sorted(result["frontier"]), ["a", "b"])

    def test_rows_missing_objectives_are_not_evaluated(self):
        rows = [row("priced", 80, 5.0), row("unpriced", 90, None)]
        result = analytics.pareto_frontier(rows, self.OBJECTIVES)
        self.assertEqual(result["frontier"], ["priced"])
        self.assertEqual(result["not_evaluated"], ["unpriced"])

    def test_three_axis_frontier(self):
        objectives = [
            ("overall_score", "max"),
            ("cost_per_100_tasks_cny", "min"),
            ("p95_latency_ms", "min"),
        ]
        rows = [
            row("fast_cheap", 80, 1.0, 100),
            row("slow_dear", 80, 2.0, 900),
            row("best_quality", 95, 5.0, 500),
        ]
        result = analytics.pareto_frontier(rows, objectives)
        self.assertEqual(sorted(result["frontier"]), ["best_quality", "fast_cheap"])
        # fast_cheap matches slow_dear on quality while being cheaper and faster.
        self.assertEqual(result["dominated"], {"slow_dear": "fast_cheap"})


if __name__ == "__main__":
    unittest.main()
