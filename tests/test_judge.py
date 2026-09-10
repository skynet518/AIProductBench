"""Judge selection: fixed priority, leave-one-family/provider-out, strict parsing."""

import json
import unittest

from src import config, judge

PRIORITY = ["qwen_flagship", "deepseek_flagship", "glm_flagship"]


def model(key, family, provider_key, *, candidate=True, judge_eligible=False, tier="flagship") -> dict:
    return {
        "key": key,
        "display_name": key,
        "model_family": family,
        "provider": provider_key,
        "provider_key": provider_key,
        "product_tier": tier,
        "candidate": candidate,
        "judge_eligible": judge_eligible,
    }


# One shared registry: the three judge-eligible models are also candidates.
JUDGE_POOL = [
    model("qwen_flagship", "Qwen", "alibaba_model_studio", judge_eligible=True),
    model("deepseek_flagship", "DeepSeek", "deepseek", judge_eligible=True),
    model("glm_flagship", "GLM", "zhipu_bigmodel", judge_eligible=True),
]


def candidate(key, family, provider_key) -> dict:
    return model(key, family, provider_key)


def selected_keys(candidate_model: dict, pool=None, priority=PRIORITY) -> list[str]:
    return [
        item["key"]
        for item in judge.select_judges(candidate_model, pool or JUDGE_POOL, priority)
    ]


def verdict(scores: dict, error=None) -> dict:
    return {"scores": scores, "error": error, "mean_score": sum(scores.values()) / len(scores)}


def good_scores(a=4, b=4, c=4) -> dict:
    return {"task_completion": a, "reasoning_quality": b, "instruction_following": c}


class TestFixedPriorityJudgeSelection(unittest.TestCase):
    """The exact judge pairs the V1 methodology requires."""

    def test_qwen_candidate_selects_deepseek_and_glm(self):
        self.assertEqual(
            selected_keys(candidate("qwen_flagship", "Qwen", "alibaba_model_studio")),
            ["deepseek_flagship", "glm_flagship"],
        )

    def test_deepseek_candidate_selects_qwen_and_glm(self):
        self.assertEqual(
            selected_keys(candidate("deepseek_flagship", "DeepSeek", "deepseek")),
            ["qwen_flagship", "glm_flagship"],
        )

    def test_glm_candidate_selects_qwen_and_deepseek(self):
        self.assertEqual(
            selected_keys(candidate("glm_flagship", "GLM", "zhipu_bigmodel")),
            ["qwen_flagship", "deepseek_flagship"],
        )

    def test_kimi_minimax_doubao_select_qwen_and_deepseek(self):
        for key, family, provider_key in [
            ("kimi_flagship", "Kimi", "moonshot"),
            ("minimax_flagship", "MiniMax", "minimax"),
            ("doubao_flagship", "Doubao", "volcano_ark"),
        ]:
            self.assertEqual(
                selected_keys(candidate(key, family, provider_key)),
                ["qwen_flagship", "deepseek_flagship"],
                msg=key,
            )

    def test_value_tier_candidates_follow_the_same_family_rule(self):
        self.assertEqual(
            selected_keys(candidate("qwen_value", "Qwen", "alibaba_model_studio")),
            ["deepseek_flagship", "glm_flagship"],
        )
        self.assertEqual(
            selected_keys(candidate("glm_value", "GLM", "zhipu_bigmodel")),
            ["qwen_flagship", "deepseek_flagship"],
        )


class TestJudgeSelectionInvariants(unittest.TestCase):
    def test_exactly_two_judges_selected(self):
        for candidate_model in JUDGE_POOL + [
            candidate("kimi_flagship", "Kimi", "moonshot"),
            candidate("doubao_flagship", "Doubao", "volcano_ark"),
        ]:
            self.assertEqual(
                len(selected_keys(candidate_model)), config.JUDGES_PER_RESPONSE
            )

    def test_same_family_judging_is_impossible(self):
        for candidate_model in JUDGE_POOL + [
            candidate("kimi_flagship", "Kimi", "moonshot"),
            candidate("minimax_flagship", "MiniMax", "minimax"),
        ]:
            chosen = judge.select_judges(candidate_model, JUDGE_POOL, PRIORITY)
            for item in chosen:
                self.assertNotEqual(item["model_family"], candidate_model["model_family"])
                self.assertNotEqual(item["provider_key"], candidate_model["provider_key"])

    def test_same_provider_judging_is_impossible_across_families(self):
        # A candidate on Zhipu's channel must not be judged by the GLM judge.
        cross_family_same_provider = candidate(
            "gateway_model", "SomeOtherFamily", "zhipu_bigmodel"
        )
        self.assertNotIn(
            "glm_flagship", selected_keys(cross_family_same_provider)
        )

    def test_selected_pair_is_always_cross_family(self):
        for candidate_model in JUDGE_POOL + [
            candidate("kimi_flagship", "Kimi", "moonshot"),
            candidate("glm_value", "GLM", "zhipu_bigmodel"),
        ]:
            families = {
                item["model_family"]
                for item in judge.select_judges(candidate_model, JUDGE_POOL, PRIORITY)
            }
            self.assertEqual(len(families), config.JUDGES_PER_RESPONSE)

    def test_selection_is_deterministic(self):
        candidate_model = candidate("kimi_flagship", "Kimi", "moonshot")
        first = selected_keys(candidate_model)
        second = selected_keys(candidate_model)
        self.assertEqual(first, second)

    def test_selection_does_not_depend_on_the_candidate_key(self):
        """No hash rotation: unrelated candidates must not get different judge pairs."""
        pairs = {
            tuple(selected_keys(candidate(key, family, provider_key)))
            for key, family, provider_key in [
                ("kimi_flagship", "Kimi", "moonshot"),
                ("minimax_flagship", "MiniMax", "minimax"),
                ("doubao_flagship", "Doubao", "volcano_ark"),
                ("zzz_unrelated_key", "Kimi", "moonshot"),
            ]
        }
        self.assertEqual(len(pairs), 1)

    def test_selection_ignores_judge_pool_order(self):
        shuffled = [JUDGE_POOL[2], JUDGE_POOL[0], JUDGE_POOL[1]]
        self.assertEqual(
            selected_keys(candidate("kimi_flagship", "Kimi", "moonshot"), pool=shuffled),
            ["qwen_flagship", "deepseek_flagship"],
        )

    def test_unlisted_judges_fall_back_to_key_order(self):
        pool = JUDGE_POOL + [
            model("zzz_extra_judge", "Extra", "extra_provider", judge_eligible=True)
        ]
        self.assertEqual(
            selected_keys(candidate("kimi_flagship", "Kimi", "moonshot"), pool=pool),
            ["qwen_flagship", "deepseek_flagship"],
        )

    def test_insufficient_eligible_judges_returns_empty(self):
        candidate_model = candidate("kimi_flagship", "Kimi", "moonshot")
        self.assertEqual(
            judge.select_judges(candidate_model, JUDGE_POOL[:1], PRIORITY), []
        )

    def test_same_family_only_pool_returns_empty_instead_of_substituting(self):
        candidate_model = candidate("qwen_flagship", "Qwen", "alibaba_model_studio")
        qwen_heavy = [
            model("qwen_flagship", "Qwen", "alibaba_model_studio", judge_eligible=True),
            model("qwen_value", "Qwen", "alibaba_model_studio", judge_eligible=True, tier="value"),
        ]
        self.assertEqual(judge.select_judges(candidate_model, qwen_heavy, PRIORITY), [])

    def test_order_judges_respects_priority(self):
        ordered = judge.order_judges(JUDGE_POOL, PRIORITY)
        self.assertEqual([item["key"] for item in ordered], PRIORITY)


class TestJudgeRegistryAgainstConfiguration(unittest.TestCase):
    def setUp(self):
        from src import runner

        self.pool = runner.load_model_pool()

    def test_configured_priority_exists_and_is_judge_eligible(self):
        from src import models

        priority = models.judge_priority(self.pool)
        self.assertTrue(priority)
        eligible = {m["key"] for m in models.judges(self.pool)}
        for key in priority:
            self.assertIn(key, eligible)

    def test_no_duplicate_registry_entries(self):
        from src import models

        result = models.validate_model_pool(self.pool)
        self.assertEqual(result["errors"], [])

    def test_registry_has_no_judge_only_duplicates(self):
        from src import models

        judges = models.judges(self.pool)
        self.assertTrue(judges)
        for entry in judges:
            self.assertTrue(
                entry.get("candidate"),
                msg=f"{entry['key']} should be a shared entry, not a judge-only copy",
            )

    def test_each_candidate_family_gets_the_configured_pair(self):
        from src import models

        expected = {
            "Qwen": ["deepseek_flagship", "glm_flagship"],
            "DeepSeek": ["qwen_flagship", "glm_flagship"],
            "GLM": ["qwen_flagship", "deepseek_flagship"],
            "Kimi": ["qwen_flagship", "deepseek_flagship"],
            "MiniMax": ["qwen_flagship", "deepseek_flagship"],
            "Doubao": ["qwen_flagship", "deepseek_flagship"],
        }
        priority = models.judge_priority(self.pool)
        for entry in models.candidates(self.pool):
            chosen = [
                item["key"]
                for item in judge.select_judges(entry, models.judges(self.pool), priority)
            ]
            self.assertEqual(chosen, expected[entry["model_family"]], msg=entry["key"])


class TestJudgeParsing(unittest.TestCase):
    def test_valid_output_accepted(self):
        parsed = judge.parse_judge_output(
            json.dumps({"scores": good_scores(5, 4, 3), "rationale": "ok"})
        )
        self.assertEqual(parsed["scores"]["task_completion"], 5)
        self.assertEqual(parsed["mean_score"], 4.0)
        self.assertEqual(parsed["normalized_score"], 75.0)

    def test_fenced_output_accepted(self):
        raw = "```json\n" + json.dumps({"scores": good_scores(), "rationale": "ok"}) + "\n```"
        self.assertIsNotNone(judge.parse_judge_output(raw))

    def test_out_of_range_score_rejected(self):
        raw = json.dumps({"scores": good_scores(6, 4, 4), "rationale": "ok"})
        with self.assertRaises(judge.JudgeOutputError):
            judge.parse_judge_output(raw)

    def test_zero_score_rejected(self):
        raw = json.dumps({"scores": good_scores(0, 4, 4), "rationale": "ok"})
        with self.assertRaises(judge.JudgeOutputError):
            judge.parse_judge_output(raw)

    def test_float_score_rejected(self):
        raw = json.dumps({"scores": good_scores(4.0, 4, 4), "rationale": "ok"})
        with self.assertRaises(judge.JudgeOutputError):
            judge.parse_judge_output(raw)

    def test_boolean_score_rejected(self):
        raw = '{"scores": {"task_completion": true, "reasoning_quality": 4, "instruction_following": 4}, "rationale": "ok"}'
        with self.assertRaises(judge.JudgeOutputError):
            judge.parse_judge_output(raw)

    def test_missing_dimension_rejected(self):
        raw = '{"scores": {"task_completion": 4, "reasoning_quality": 4}, "rationale": "ok"}'
        with self.assertRaises(judge.JudgeOutputError):
            judge.parse_judge_output(raw)

    def test_extra_dimension_rejected(self):
        scores = good_scores()
        scores["bonus"] = 3
        with self.assertRaises(judge.JudgeOutputError):
            judge.parse_judge_output(json.dumps({"scores": scores, "rationale": "ok"}))

    def test_empty_rationale_rejected(self):
        with self.assertRaises(judge.JudgeOutputError):
            judge.parse_judge_output(json.dumps({"scores": good_scores(), "rationale": "  "}))

    def test_non_json_rejected(self):
        with self.assertRaises(judge.JudgeOutputError):
            judge.parse_judge_output("The response is quite good overall.")

    def test_json_array_rejected(self):
        with self.assertRaises(judge.JudgeOutputError):
            judge.parse_judge_output("[1, 2, 3]")


class TestJudgeAggregation(unittest.TestCase):
    def test_two_verdicts_are_averaged(self):
        aggregate = judge.aggregate_verdicts(
            [verdict(good_scores(5, 5, 5)), verdict(good_scores(3, 3, 3))]
        )
        self.assertEqual(aggregate["judges_valid"], 2)
        self.assertEqual(aggregate["quality_score"], 4.0)
        self.assertEqual(aggregate["overall_score"], 75.0)
        self.assertEqual(aggregate["dimension_scores"]["task_completion"], 4.0)

    def test_failed_verdict_is_excluded(self):
        aggregate = judge.aggregate_verdicts(
            [verdict(good_scores(5, 5, 5)), verdict(good_scores(1, 1, 1), error="boom")]
        )
        self.assertEqual(aggregate["judges_valid"], 1)
        self.assertEqual(aggregate["quality_score"], 5.0)
        self.assertEqual(aggregate["judges_total"], 2)

    def test_no_valid_verdict_reports_none(self):
        aggregate = judge.aggregate_verdicts([verdict(good_scores(), error="boom")])
        self.assertIsNone(aggregate["quality_score"])
        self.assertIsNone(aggregate["overall_score"])
        self.assertEqual(aggregate["judges_valid"], 0)

    def test_agreement_between_two_judges(self):
        agreement = judge.judge_agreement(
            [verdict(good_scores(5, 4, 3)), verdict(good_scores(3, 4, 5))]
        )
        self.assertEqual(agreement["judges"], 2)
        self.assertEqual(agreement["overall_mean_abs_difference"], 0.0)
        self.assertTrue(agreement["per_dimension"]["reasoning_quality"]["exact_match"])
        self.assertFalse(agreement["per_dimension"]["task_completion"]["exact_match"])
        self.assertEqual(
            agreement["per_dimension"]["task_completion"]["mean_abs_difference"], 2.0
        )

    def test_agreement_is_none_with_one_judge(self):
        self.assertIsNone(judge.judge_agreement([verdict(good_scores())]))

    def test_rubric_dimensions_match_frozen_set(self):
        self.assertEqual(
            list(config.RUBRIC_DIMENSIONS),
            ["task_completion", "reasoning_quality", "instruction_following"],
        )


if __name__ == "__main__":
    unittest.main()
