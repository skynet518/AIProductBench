"""Deterministic constraint checking."""

import unittest

from src import deterministic


def case_with(checks: list) -> dict:
    return {"id": "T-01", "deterministic_checks": checks}


class TestDeterministicChecks(unittest.TestCase):
    def test_no_checks_reports_none_not_perfect_score(self):
        result = deterministic.evaluate(case_with([]), "anything")
        self.assertIsNone(result["constraint_pass_rate"])
        self.assertIsNone(result["all_passed"])
        self.assertEqual(result["checks_total"], 0)

    def test_valid_json_object(self):
        result = deterministic.evaluate(
            case_with([{"type": "valid_json", "expect": "object"}]), '{"a": 1}'
        )
        self.assertTrue(result["checks"][0]["passed"])

    def test_valid_json_rejects_prose_and_wrong_shape(self):
        prose = deterministic.evaluate(case_with([{"type": "valid_json"}]), "not json")
        self.assertFalse(prose["checks"][0]["passed"])
        array = deterministic.evaluate(
            case_with([{"type": "valid_json", "expect": "object"}]), "[1, 2]"
        )
        self.assertFalse(array["checks"][0]["passed"])

    def test_json_found_inside_markdown_fence(self):
        result = deterministic.evaluate(
            case_with([{"type": "valid_json", "expect": "object"}]),
            '```json\n{"a": 1}\n```',
        )
        self.assertTrue(result["checks"][0]["passed"])

    def test_required_and_forbidden_keys(self):
        text = '{"product_area": "billing", "severity": "high"}'
        required = deterministic.evaluate(
            case_with([{"type": "required_keys", "keys": ["product_area", "severity"]}]), text
        )
        self.assertTrue(required["checks"][0]["passed"])
        missing = deterministic.evaluate(
            case_with([{"type": "required_keys", "keys": ["blocked_since"]}]), text
        )
        self.assertFalse(missing["checks"][0]["passed"])
        forbidden = deterministic.evaluate(
            case_with([{"type": "forbidden_keys", "keys": ["severity"]}]), text
        )
        self.assertFalse(forbidden["checks"][0]["passed"])

    def test_exact_item_count(self):
        passing = deterministic.evaluate(
            case_with([{"type": "exact_item_count", "count": 2}]), "[1, 2]"
        )
        self.assertTrue(passing["checks"][0]["passed"])
        failing = deterministic.evaluate(
            case_with([{"type": "exact_item_count", "count": 3}]), "[1, 2]"
        )
        self.assertFalse(failing["checks"][0]["passed"])

    def test_exact_bullet_count(self):
        text = "- one\n- two\n- three\n"
        result = deterministic.evaluate(
            case_with([{"type": "exact_bullet_count", "count": 3}]), text
        )
        self.assertTrue(result["checks"][0]["passed"])
        result = deterministic.evaluate(
            case_with([{"type": "exact_bullet_count", "count": 2}]), text
        )
        self.assertFalse(result["checks"][0]["passed"])

    def test_word_and_character_limits(self):
        text = "one two three"
        self.assertTrue(
            deterministic.evaluate(case_with([{"type": "max_words", "count": 3}]), text)[
                "checks"
            ][0]["passed"]
        )
        self.assertFalse(
            deterministic.evaluate(case_with([{"type": "max_words", "count": 2}]), text)[
                "checks"
            ][0]["passed"]
        )
        self.assertTrue(
            deterministic.evaluate(case_with([{"type": "max_chars", "count": 13}]), text)[
                "checks"
            ][0]["passed"]
        )
        self.assertFalse(
            deterministic.evaluate(case_with([{"type": "min_chars", "count": 50}]), text)[
                "checks"
            ][0]["passed"]
        )

    def test_required_and_forbidden_phrases(self):
        text = "我们建议按季度推进，不使用任何抓手。"
        required = deterministic.evaluate(
            case_with([{"type": "required_phrases", "phrases": ["季度"]}]), text
        )
        self.assertTrue(required["checks"][0]["passed"])
        forbidden = deterministic.evaluate(
            case_with([{"type": "forbidden_phrases", "phrases": ["抓手"]}]), text
        )
        self.assertFalse(forbidden["checks"][0]["passed"])

    def test_ordering(self):
        text = "先导出，再分类，然后摘要，最后写回。"
        passing = deterministic.evaluate(
            case_with([{"type": "ordering", "phrases": ["导出", "分类", "摘要", "写回"]}]), text
        )
        self.assertTrue(passing["checks"][0]["passed"])
        failing = deterministic.evaluate(
            case_with([{"type": "ordering", "phrases": ["导出", "摘要", "分类"]}]), text
        )
        self.assertFalse(failing["checks"][0]["passed"])

    def test_numeric_range(self):
        passing = deterministic.evaluate(
            case_with([{"type": "numeric_range", "min": 0, "max": 1}]), "confidence: 0.8"
        )
        self.assertTrue(passing["checks"][0]["passed"])
        failing = deterministic.evaluate(
            case_with([{"type": "numeric_range", "min": 0, "max": 1}]), "confidence: 1.8"
        )
        self.assertFalse(failing["checks"][0]["passed"])

    def test_forbidden_regex(self):
        result = deterministic.evaluate(
            case_with([{"type": "forbidden_regex", "pattern": r"```"}]),
            "```python\nprint(1)\n```",
        )
        self.assertFalse(result["checks"][0]["passed"])

    def test_unsupported_check_type_fails_loudly(self):
        result = deterministic.evaluate(case_with([{"type": "vibes"}]), "text")
        self.assertFalse(result["checks"][0]["passed"])
        self.assertIn("unsupported check type", result["checks"][0]["detail"])

    def test_pass_rate_aggregation(self):
        checks = [
            {"type": "max_words", "count": 5},
            {"type": "required_phrases", "phrases": ["缺失"]},
        ]
        result = deterministic.evaluate(case_with(checks), "one two")
        self.assertEqual(result["checks_total"], 2)
        self.assertEqual(result["checks_passed"], 1)
        self.assertEqual(result["constraint_pass_rate"], 0.5)
        self.assertFalse(result["all_passed"])


if __name__ == "__main__":
    unittest.main()
