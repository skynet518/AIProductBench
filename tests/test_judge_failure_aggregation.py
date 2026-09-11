"""Offline aggregation tests for judge failure records.

Judge verdicts can legitimately be failure records: a provider error or an
unparseable judge output produces a record with an ``error`` and without the
success-only telemetry (tokens, latency). Aggregation must tolerate those
records, keep them as failures, and never fabricate scores or zero usage.

No network access and no paid call is made by any test here.
"""

from __future__ import annotations

import unittest

import run_official
from src import config, judge, runner


def _model(key: str, *, candidate: bool = True, judge_eligible: bool = False) -> dict:
    return {
        "key": key,
        "display_name": key.replace("_", " ").title(),
        "model_id": f"{key}-id",
        "model_family": key.split("_")[0].title(),
        "provider": "Test Provider",
        "provider_key": key.split("_")[0],
        "region": "test",
        "product_tier": "flagship",
        "inference_channel": "native",
        "thinking_mode": "enabled",
        "candidate": candidate,
        "judge_eligible": judge_eligible,
    }


def _valid_verdict(judge_key: str, score: int = 5) -> dict:
    return {
        "judge_key": judge_key,
        "judge_model_id": f"{judge_key}-id",
        "judge_family": judge_key.split("_")[0].title(),
        "judge_provider": "Test Provider",
        "scores": {
            "task_completion": score,
            "reasoning_quality": score,
            "instruction_following": score,
        },
        "rationale": "ok",
        "mean_score": float(score),
        "normalized_score": (score - 1) / 4 * 100,
        "error": None,
        "input_tokens": 100,
        "output_tokens": 200,
        "total_tokens": 300,
        "reasoning_tokens": 50,
        "cached_input_tokens": 0,
        "latency_ms": 1000.0,
        "native_cost": 0.01,
        "native_currency": "USD",
        "normalized_cost_cny": 0.05,
        "normalization_method": "fx",
        "cost_basis": "test",
        "cost_error": None,
    }


def _failed_verdict(judge_key: str, message: str = "invalid judge output: not JSON") -> dict:
    """Error-record shape produced by judge._evaluate_one on failure.

    Deliberately contains NO token/latency telemetry, exactly like the four
    invalid-format judge records in the canonical run.
    """
    return {
        "judge_key": judge_key,
        "judge_display_name": judge_key,
        "judge_family": judge_key.split("_")[0].title(),
        "judge_provider": "Test Provider",
        "judge_prompt_version": config.JUDGE_PROMPT_VERSION,
        "scores": None,
        "rationale": None,
        "mean_score": None,
        "normalized_score": None,
        "error": message,
    }


def _row(model_key: str, case_id: str, verdicts: list[dict], **overrides) -> dict:
    aggregate = judge.aggregate_verdicts(verdicts)
    judge_costs = [
        verdict["normalized_cost_cny"]
        for verdict in verdicts
        if verdict.get("normalized_cost_cny") is not None
    ]
    row = {
        "case_id": case_id,
        "domain": config.DOMAINS[0],
        "difficulty": "medium",
        "language": "zh",
        "model_key": model_key,
        "model_name": model_key,
        "model_id": f"{model_key}-id",
        "model_family": model_key.split("_")[0].title(),
        "provider": "Test Provider",
        "product_tier": "flagship",
        "inference_channel": "native",
        "thinking_mode": "enabled",
        "response_text": "answer",
        "latency_ms": 1200.0,
        "input_tokens": 300,
        "output_tokens": 400,
        "total_tokens": 700,
        "reasoning_tokens": 100,
        "cached_input_tokens": 0,
        "native_cost": 0.02,
        "native_currency": "USD",
        "normalized_cost_cny": 0.10,
        "normalization_method": "fx",
        "cost_basis": "test",
        "cost_error": None,
        "called_at": "2026-09-11T00:00:00+00:00",
        "synthetic": False,
        "error": None,
        "deterministic": {
            "checks": [{"name": "c", "passed": True, "detail": "ok"}],
            "checks_passed": 1,
            "checks_total": 1,
            "constraint_pass_rate": 1.0,
            "all_passed": True,
        },
        "judges_attempted": ["judge_a", "judge_b"],
        "judge_unavailable_reason": None,
        "judgements": verdicts,
        "aggregate": aggregate if aggregate.get("judges_valid", 0) >= 2 else None,
        "judge_agreement": judge.judge_agreement(verdicts),
        "judge_cost_cny": round(sum(judge_costs), 8) if judge_costs else None,
    }
    if row["aggregate"] is None and aggregate.get("judges_valid", 0) < 2:
        row["judge_unavailable_reason"] = (
            f"only {aggregate.get('judges_valid', 0)}/2 intended judge verdicts are valid"
        )
    row.update(overrides)
    return row


class JudgeFailureAggregationTests(unittest.TestCase):
    def _pool(self):
        return {
            "models": [
                _model("complete_model", candidate=True),
                _model("incomplete_model", candidate=True),
                _model("judge_a", candidate=False, judge_eligible=True),
                _model("judge_b", candidate=False, judge_eligible=True),
            ]
        }

    def test_a_valid_verdicts_keep_real_telemetry(self):
        rows = [
            _row("complete_model", "C-1", [_valid_verdict("judge_a"), _valid_verdict("judge_b")]),
            _row("complete_model", "C-2", [_valid_verdict("judge_a"), _valid_verdict("judge_b")]),
        ]
        summary = runner.summarize(rows, self._pool(), required_cases=2)
        overhead = summary["judge_overhead"]
        self.assertEqual(overhead["judge_calls"], 4)
        self.assertEqual(overhead["judge_total_tokens"]["input"], 400)
        self.assertEqual(overhead["judge_total_tokens"]["output"], 800)
        self.assertEqual(overhead["judge_total_tokens"]["total"], 1200)
        self.assertEqual(overhead["judge_avg_latency_ms"], 1000.0)
        self.assertEqual(overhead["judge_failure_records"], 0)

    def test_b_error_verdict_without_telemetry_does_not_crash(self):
        rows = [
            _row("incomplete_model", "C-1", [_valid_verdict("judge_a"), _failed_verdict("judge_b")]),
            _row("incomplete_model", "C-2", [_failed_verdict("judge_a"), _failed_verdict("judge_b")]),
        ]
        summary = runner.summarize(rows, self._pool(), required_cases=2)
        overhead = summary["judge_overhead"]
        self.assertEqual(overhead["judge_calls"], 4)
        # Only the one valid verdict contributes; unknowns stay unknown.
        self.assertEqual(overhead["judge_total_tokens"]["input"], 100)
        self.assertEqual(overhead["judge_avg_latency_ms"], 1000.0)
        self.assertEqual(overhead["judge_failure_records"], 3)

    def test_c_mixed_success_and_failure_records_summarize_together(self):
        rows = [
            _row("complete_model", "C-1", [_valid_verdict("judge_a"), _valid_verdict("judge_b")]),
            _row("complete_model", "C-2", [_valid_verdict("judge_a"), _valid_verdict("judge_b")]),
            _row("incomplete_model", "C-1", [_valid_verdict("judge_a"), _failed_verdict("judge_b")]),
            _row("incomplete_model", "C-2", [_failed_verdict("judge_a"), _failed_verdict("judge_b")]),
        ]
        summary = runner.summarize(rows, self._pool(), required_cases=2)
        self.assertEqual(summary["judge_overhead"]["judge_calls"], 8)
        self.assertEqual(summary["judge_overhead"]["judge_failure_records"], 3)
        self.assertEqual(summary["judge_overhead"]["judge_total_tokens"]["input"], 500)

    def test_d_incomplete_model_stays_incomplete_and_unranked(self):
        rows = [
            _row("complete_model", "C-1", [_valid_verdict("judge_a"), _valid_verdict("judge_b")]),
            _row("complete_model", "C-2", [_valid_verdict("judge_a"), _valid_verdict("judge_b")]),
            _row("incomplete_model", "C-1", [_valid_verdict("judge_a"), _failed_verdict("judge_b")]),
            _row("incomplete_model", "C-2", [_failed_verdict("judge_a"), _failed_verdict("judge_b")]),
        ]
        summary = runner.summarize(rows, self._pool(), required_cases=2)
        by_key = {row["model_key"]: row for row in summary["models"]}
        incomplete = by_key["incomplete_model"]
        self.assertFalse(incomplete["rank_eligible"])
        self.assertIsNone(incomplete["rank"])
        self.assertIsNone(incomplete["quality_per_cny"])
        self.assertFalse(incomplete["pareto_quality_cost"])
        self.assertIn("incomplete_model", summary["official_ranking"]["incomplete_models"][0]["model_key"])

    def test_e_complete_model_remains_rank_eligible(self):
        rows = [
            _row("complete_model", "C-1", [_valid_verdict("judge_a"), _valid_verdict("judge_b")]),
            _row("complete_model", "C-2", [_valid_verdict("judge_a"), _valid_verdict("judge_b")]),
            _row("incomplete_model", "C-1", [_valid_verdict("judge_a"), _failed_verdict("judge_b")]),
            _row("incomplete_model", "C-2", [_failed_verdict("judge_a"), _failed_verdict("judge_b")]),
        ]
        summary = runner.summarize(rows, self._pool(), required_cases=2)
        by_key = {row["model_key"]: row for row in summary["models"]}
        complete = by_key["complete_model"]
        self.assertTrue(complete["rank_eligible"])
        self.assertEqual(complete["rank"], 1)
        self.assertEqual(complete["cases_scored"], 2)
        self.assertIsNotNone(complete["quality_per_cny"])

    def test_f_failed_judge_records_contribute_no_quality_score(self):
        only_failures = [
            _failed_verdict("judge_a", "provider: boom"),
            _failed_verdict("judge_b", "invalid judge output: not JSON"),
        ]
        row = _row("incomplete_model", "C-1", only_failures)
        self.assertIsNone(row["aggregate"])
        self.assertIsNone(row["judge_agreement"])
        summary = runner.summarize([row] * 2, self._pool(), required_cases=2)
        by_key = {item["model_key"]: item for item in summary["models"]}
        model = by_key["incomplete_model"]
        self.assertIsNone(model["overall_score"])
        self.assertIsNone(model["dimension_scores"]["task_completion"])
        self.assertEqual(model["cases_scored"], 0)
        self.assertFalse(model["rank_eligible"])


class RankingPrecisionTests(unittest.TestCase):
    """The published score is rounded; the ordering must use full precision."""

    def _pool(self):
        return {
            "models": [
                _model("lower_exact", candidate=True),
                _model("higher_exact", candidate=True),
                _model("judge_a", candidate=False, judge_eligible=True),
                _model("judge_b", candidate=False, judge_eligible=True),
            ]
        }

    def _rows(self):
        # 3-decimal means collide at 96.333 but full precision differs:
        # lower_exact = 96.3326, higher_exact = 96.3334
        rows = []
        for score in (96.3333, 96.3319):
            rows.append(
                _row(
                    "lower_exact",
                    f"C-{len(rows)}",
                    [_valid_verdict("judge_a"), _valid_verdict("judge_b")],
                    aggregate={"overall_score": score, "judges_valid": 2,
                               "judges_total": 2, "quality_score": score / 100 * 4 + 1,
                               "dimension_scores": {d: score for d in config.RUBRIC_DIMENSIONS}},
                )
            )
        for score in (96.3335, 96.3333):
            rows.append(
                _row(
                    "higher_exact",
                    f"C-{len(rows)}",
                    [_valid_verdict("judge_a"), _valid_verdict("judge_b")],
                    aggregate={"overall_score": score, "judges_valid": 2,
                               "judges_total": 2, "quality_score": score / 100 * 4 + 1,
                               "dimension_scores": {d: score for d in config.RUBRIC_DIMENSIONS}},
                )
            )
        return rows

    def test_displayed_scores_are_rounded_and_equal(self):
        summary = runner.summarize(self._rows(), self._pool(), required_cases=2)
        rows = {row["model_key"]: row for row in summary["models"]}
        self.assertEqual(rows["lower_exact"]["overall_score"], 96.333)
        self.assertEqual(rows["higher_exact"]["overall_score"], 96.333)

    def test_ranking_uses_full_precision_not_list_order(self):
        summary = runner.summarize(self._rows(), self._pool(), required_cases=2)
        rows = {row["model_key"]: row for row in summary["models"]}
        self.assertLess(
            rows["lower_exact"]["overall_score_exact"],
            rows["higher_exact"]["overall_score_exact"],
        )
        self.assertEqual(rows["higher_exact"]["rank"], 1)
        self.assertEqual(rows["lower_exact"]["rank"], 2)
        self.assertIn(
            "full-precision", summary["official_ranking"]["ordering_rule"]
        )


class DisagreementAuditTests(unittest.TestCase):
    def _rows(self):
        rows = []
        # three cases with both judges valid, gaps 0.0, 0.4 and 2.0
        rows.append(_row("m", "C-1", [_valid_verdict("judge_a"), _valid_verdict("judge_b")]))
        rows.append(
            _row(
                "m",
                "C-2",
                [
                    {**_valid_verdict("judge_a"), "mean_score": 5.0},
                    {**_valid_verdict("judge_b"), "mean_score": 4.6},
                ],
            )
        )
        rows.append(
            _row(
                "m",
                "C-3",
                [
                    {**_valid_verdict("judge_a"), "mean_score": 5.0},
                    {**_valid_verdict("judge_b"), "mean_score": 3.0},
                ],
            )
        )
        # one case with only a single valid judge must be excluded
        rows.append(
            _row("m", "C-4", [_valid_verdict("judge_a"), _failed_verdict("judge_b")])
        )
        return rows

    def test_population_and_histogram_are_consistent(self):
        analysis = run_official.judge_disagreement_analysis(self._rows())
        self.assertEqual(analysis["population"], 3)
        self.assertEqual(analysis["histogram_counts_sum"], analysis["population"])
        counts = {item["bin"]: item["count"] for item in analysis["histogram"]}
        self.assertEqual(counts["exactly_zero"], 1)
        self.assertEqual(counts["gt0_le0.5"], 1)   # gap 0.4
        self.assertEqual(counts["gt1.5_le2.0"], 1)  # gap 2.0
        self.assertEqual(analysis["mean_gap"], round((0.0 + 0.4 + 2.0) / 3, 4))
        self.assertEqual(
            analysis["highest_disagreement_cases"][0]["case_id"], "C-3"
        )
        self.assertEqual(
            analysis["highest_disagreement_cases"][0]["gap"], 2.0
        )

    def test_bins_are_mutually_exclusive_over_a_dense_range(self):
        definitions = [item[1] for item in run_official.DISAGREEMENT_BINS]
        self.assertEqual(len(definitions), len(set(definitions)))
        for gap in (0.0, 0.001, 0.5, 0.501, 1.0, 1.001, 1.5, 2.0, 2.001, 5.0):
            matched = 0
            for name, _definition, lower, upper in run_official.DISAGREEMENT_BINS:
                if name == "exactly_zero":
                    matched += 1 if gap == 0.0 else 0
                elif upper is None:
                    matched += 1 if gap > lower else 0
                else:
                    matched += 1 if lower < gap <= upper else 0
            self.assertEqual(matched, 1, msg=f"gap {gap} matched {matched} bins")


if __name__ == "__main__":
    unittest.main()
