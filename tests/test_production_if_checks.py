"""Canonical-answer coverage for the Phase 3B-1.1 IF operator additions.

Runs the production Domain-1 cases' own declared checks against a hand-written
canonical expected-success answer, then injects a targeted failure for each of
the three new deterministic operators (`section_max_chars`,
`section_bullet_count`, `exact_keys`).

These tests read `data/cases_v1.json`. They are skipped when that Phase 3B
deliverable is not present, so the framework suite remains runnable without it.
"""

import json
import unittest
from pathlib import Path

from src import deterministic

PRODUCTION_CASES = Path(__file__).resolve().parent.parent / "data" / "cases_v1.json"

# Canonical expected-success answers for the six cases revised in Phase 3B-1.1.
CANONICAL_ANSWERS = {
    "IF-02": (
        "Release note:\n"
        "- CSV export now lives on the Reports page.\n"
        "- Saved filters no longer disappear after logout.\n"
        "- The dashboard loads up to 5,000 rows without timing out."
    ),
    "IF-03": (
        "【客服团队】\n"
        "2026-10-18 22:00 至 10-19 02:00 迁移，停机约 4 小时；期间客户档案查询、"
        "工单创建不可用，报表导出可用但最多延迟 2 小时，请提前告知用户。\n"
        "【销售团队】\n"
        "迁移约 4 小时，批量导入超过 5,000 条会被拒绝，报表导出可用但最多延迟 2 小时；"
        "如失败将在 2026-10-19 06:00 前回滚并发布状态页通知。\n"
        "【实施顾问】\n"
        "迁移由运维团队负责，联系人李文。客户档案查询与工单创建不可用，"
        "批量导入超 5,000 条被拒；失败将在 2026-10-19 06:00 前回滚。"
    ),
    "IF-06": (
        "规则判断：采用规则 B，因为专项活动要求优先于通用规范。\n"
        "通知正文：2026-10-20 01:00 至 05:00 系统维护，报销单提交和审批暂停，"
        "其他功能正常，请提前安排。"
    ),
    "IF-07": (
        '{"case_ref": "SR-20261014-7781", "priority": "medium", "state": "pending", '
        '"assignee": null, "channel": "phone"}'
    ),
    "IF-09": (
        "## 变更摘要\n"
        "- 订单服务升级到 v2.4.1，包含支付回调重试逻辑。\n"
        "- 以业务排期（文档 B）为准，必须在 20:00 前完成。\n"
        "- 风险是支付回调可能重复通知，需要幂等校验。\n"
        "## Rollout checklist\n"
        "- Freeze the payments dashboard.\n"
        "- Notify the CS on-call.\n"
        "- Run the payment smoke test.\n"
        "- Monitor the error rate for 30 minutes.\n"
        "## 风险与回滚\n"
        "- 回滚切回 v2.4.0，预计 5 分钟，由值班同学执行。\n"
        "- 部署前确认 20:00 前完成，避免影响当晚大促。"
    ),
    "IF-10": (
        "致各位用户：9 月 28 日 14:02 到 14:45，支付页面无法加载约 43 分钟，"
        "约 6% 的下单请求失败，我们深表歉意，这是我们的责任。原因是数据库连接池"
        "配置变更，已定位并回滚，目前服务已恢复，我们正在持续监控。我们将在 48 "
        "小时内发布复盘说明。"
    ),
}


def load_cases() -> dict:
    with open(PRODUCTION_CASES, encoding="utf-8") as handle:
        return {case["id"]: case for case in json.load(handle)["test_cases"]}


def run_named_check(case: dict, name: str, text: str) -> bool:
    check = next(
        check for check in case["deterministic_checks"] if check["name"] == name
    )
    result = deterministic.evaluate({"deterministic_checks": [check]}, text)
    return result["checks"][0]["passed"]


@unittest.skipUnless(PRODUCTION_CASES.exists(), "production dataset not present")
class TestCanonicalIfAnswers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = load_cases()

    def test_canonical_answers_pass_every_declared_check(self):
        for case_id, answer in CANONICAL_ANSWERS.items():
            with self.subTest(case=case_id):
                result = deterministic.evaluate(self.cases[case_id], answer)
                if result["checks_total"] == 0:
                    # Matrix-approved judge-only None case (IF-06): no checks to pass.
                    self.assertIsNone(result["all_passed"])
                    continue
                self.assertTrue(
                    result["all_passed"],
                    msg=f"{case_id} failed: "
                    + "; ".join(
                        f"{check['name']}: {check['detail']}"
                        for check in result["checks"]
                        if not check["passed"]
                    ),
                )

    def test_revised_cases_declare_the_new_operators(self):
        expected = {
            "IF-03": "section_max_chars",
            "IF-07": "exact_keys",
            "IF-09": "section_bullet_count",
        }
        for case_id, operator in expected.items():
            with self.subTest(case=case_id):
                types = {
                    check["type"]
                    for check in self.cases[case_id].get("deterministic_checks", [])
                }
                self.assertIn(operator, types)

    def test_if06_is_the_matrix_approved_none_case(self):
        # Phase 3B-5R: IF-06 is a Matrix-approved judge-only None case.
        self.assertEqual(self.cases["IF-06"]["deterministic_checks"], [])
        self.assertEqual(self.cases["IF-06"]["difficulty"], "medium")
        self.assertEqual(self.cases["IF-06"]["language"], "zh")
        self.assertEqual(self.cases["IF-06"]["title"], "冲突指令的优先级判定")


@unittest.skipUnless(PRODUCTION_CASES.exists(), "production dataset not present")
class TestTargetedOperatorFailures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = load_cases()

    def test_section_max_chars_detects_over_budget_body(self):
        case = self.cases["IF-03"]
        over_budget = "【客服团队】\n" + "字" * 121 + "\n【销售团队】\n正文。\n【实施顾问】\n正文。"
        self.assertFalse(
            run_named_check(case, "客服团队正文不超过120字符", over_budget)
        )

    def test_section_bullet_count_detects_wrong_split(self):
        case = self.cases["IF-09"]
        wrong_split = CANONICAL_ANSWERS["IF-09"].replace(
            "- 风险是支付回调可能重复通知，需要幂等校验。\n", ""
        )
        self.assertFalse(
            run_named_check(case, "变更摘要恰好3条", wrong_split)
        )

    def test_exact_keys_detects_legacy_extra_key(self):
        case = self.cases["IF-07"]
        with_legacy = CANONICAL_ANSWERS["IF-07"][:-1] + ', "legacy_status": "in_progress"}'
        self.assertFalse(
            run_named_check(case, "字段集合完全一致", with_legacy)
        )


if __name__ == "__main__":
    unittest.main()
