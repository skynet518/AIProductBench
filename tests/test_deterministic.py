"""Deterministic constraint checking."""

import unittest

from src import deterministic


def case_with(checks: list) -> dict:
    return {"id": "T-01", "deterministic_checks": checks}


def check_passed(check: dict, text: str) -> bool:
    return deterministic.evaluate(case_with([check]), text)["checks"][0]["passed"]


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


class TestSectionMaxChars(unittest.TestCase):
    """`section_max_chars` isolates one section body and applies len() <= count."""

    def passes(self, count: int, text: str, end="【销售团队】") -> bool:
        check = {
            "type": "section_max_chars",
            "start_marker": "【客服团队】",
            "end_marker": end,
            "count": count,
        }
        return check_passed(check, text)

    def test_119_characters_passes_for_count_120(self):
        self.assertTrue(self.passes(120, "【客服团队】" + "x" * 119 + "【销售团队】"))

    def test_exactly_120_characters_passes(self):
        self.assertTrue(self.passes(120, "【客服团队】" + "x" * 120 + "【销售团队】"))

    def test_121_characters_fails(self):
        self.assertFalse(self.passes(120, "【客服团队】" + "x" * 121 + "【销售团队】"))

    def test_last_section_with_null_end_marker(self):
        self.assertTrue(self.passes(120, "【客服团队】" + "x" * 120, end=None))
        self.assertFalse(self.passes(120, "【客服团队】" + "x" * 121, end=None))

    def test_missing_start_marker_fails(self):
        self.assertFalse(self.passes(120, "【销售团队】" + "x" * 10))

    def test_missing_end_marker_fails(self):
        self.assertFalse(self.passes(120, "【客服团队】" + "x" * 10))

    def test_duplicate_start_marker_fails(self):
        self.assertFalse(
            self.passes(120, "【客服团队】a【客服团队】b【销售团队】")
        )

    def test_duplicate_end_marker_fails(self):
        self.assertFalse(
            self.passes(120, "【客服团队】a【销售团队】b【销售团队】")
        )

    def test_end_marker_before_start_marker_fails(self):
        self.assertFalse(self.passes(120, "【销售团队】a【客服团队】b"))

    def test_surrounding_whitespace_is_stripped_before_counting(self):
        text = "\n\n【客服团队】\n\n" + "x" * 120 + "\n\n【销售团队】\n\n"
        self.assertTrue(self.passes(120, text))


class TestSectionBulletCount(unittest.TestCase):
    """`section_bullet_count` counts only `^\\s*-\\s+` lines in one section."""

    MIXED_SPLIT_DOC = (
        "## 变更摘要\n"
        "- a\n- b\n- c\n"
        "## Rollout checklist\n"
        "- d\n- e\n- f\n- g\n"
        "## 风险与回滚\n"
        "- h\n- i\n"
    )

    WRONG_SPLIT_DOC = (
        "## 变更摘要\n"
        "- a\n- b\n- c\n- c2\n"
        "## Rollout checklist\n"
        "- d\n- e\n- f\n"
        "## 风险与回滚\n"
        "- h\n- i\n"
    )

    def section(self, start, end, count, text) -> bool:
        check = {
            "type": "section_bullet_count",
            "start_marker": start,
            "end_marker": end,
            "count": count,
        }
        return check_passed(check, text)

    def test_correct_count_passes(self):
        text = "## S\n- a\n- b\n- c\n## E\n"
        self.assertTrue(self.section("## S", "## E", 3, text))

    def test_too_few_fails(self):
        text = "## S\n- a\n- b\n## E\n"
        self.assertFalse(self.section("## S", "## E", 3, text))

    def test_too_many_fails(self):
        text = "## S\n- a\n- b\n- c\n- d\n## E\n"
        self.assertFalse(self.section("## S", "## E", 3, text))

    def test_correct_three_four_two_split_passes(self):
        self.assertTrue(self.section("## 变更摘要", "## Rollout checklist", 3, self.MIXED_SPLIT_DOC))
        self.assertTrue(self.section("## Rollout checklist", "## 风险与回滚", 4, self.MIXED_SPLIT_DOC))
        self.assertTrue(self.section("## 风险与回滚", None, 2, self.MIXED_SPLIT_DOC))

    def test_wrong_four_three_two_split_fails_despite_global_total_nine(self):
        global_total = deterministic.evaluate(
            case_with([{"type": "exact_bullet_count", "count": 9}]), self.WRONG_SPLIT_DOC
        )
        self.assertTrue(global_total["checks"][0]["passed"], "global total is still 9")
        self.assertFalse(
            self.section("## 变更摘要", "## Rollout checklist", 3, self.WRONG_SPLIT_DOC)
        )
        self.assertFalse(
            self.section("## Rollout checklist", "## 风险与回滚", 4, self.WRONG_SPLIT_DOC)
        )

    def test_bullets_outside_the_section_are_ignored(self):
        text = "- preface 1\n- preface 2\n## S\n- a\n- b\n## E\n- after\n"
        self.assertTrue(self.section("## S", "## E", 2, text))

    def test_missing_start_marker_fails(self):
        text = "- a\n- b\n## E\n"
        self.assertFalse(self.section("## S", "## E", 2, text))

    def test_duplicate_start_marker_fails(self):
        text = "## S\n- a\n## S\n- b\n## E\n"
        self.assertFalse(self.section("## S", "## E", 2, text))

    def test_final_section_with_null_end_marker_works(self):
        text = "## S\n- a\n- b\n"
        self.assertTrue(self.section("## S", None, 2, text))
        self.assertFalse(self.section("## S", None, 3, text))


class TestExactKeys(unittest.TestCase):
    """`exact_keys` requires a JSON object whose key set equals the declared set."""

    FIVE_KEYS = ["case_ref", "priority", "state", "assignee", "channel"]

    EXACT = '{"case_ref": "SR-1", "priority": "medium", "state": "pending", "assignee": null, "channel": "phone"}'

    def check(self, text: str) -> bool:
        return check_passed({"type": "exact_keys", "keys": self.FIVE_KEYS}, text)

    def test_exact_five_keys_pass(self):
        self.assertTrue(self.check(self.EXACT))

    def test_key_order_change_passes(self):
        reordered = (
            '{"channel": "phone", "assignee": null, "state": "pending", '
            '"priority": "medium", "case_ref": "SR-1"}'
        )
        self.assertTrue(self.check(reordered))

    def test_missing_key_fails(self):
        text = '{"case_ref": "SR-1", "priority": "medium", "state": "pending", "assignee": null}'
        self.assertFalse(self.check(text))

    def test_arbitrary_extra_key_fails(self):
        text = self.EXACT[:-1] + ', "notes": "extra"}'
        self.assertFalse(self.check(text))

    def test_legacy_extra_key_fails(self):
        text = self.EXACT[:-1] + ', "legacy_status": "in_progress"}'
        self.assertFalse(self.check(text))

    def test_invalid_json_fails(self):
        self.assertFalse(self.check("not json at all"))

    def test_array_root_fails(self):
        self.assertFalse(self.check('["case_ref", "priority"]'))


if __name__ == "__main__":
    unittest.main()
