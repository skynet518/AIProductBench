"""Product-reasoning-decision (PR) production-domain integrity — Matrix-compliant set.

The Phase 3B-3/3B-3.1 PR set passed semantic quality review but drifted from the
APPROVED CASE_MATRIX_V1.md slots, so Domain 3 was reopened and replaced with the
externally authored Matrix-compliant canonical definitions (Phase 3B-3R).

These tests pin the Matrix plan (slot/title, difficulty, language, deterministic
strength), guard the 20 frozen IF/SA objects, validate declarations, and verify
case-visible source facts. They deliberately do NOT encode a mandatory product
recommendation, a model winner, or any hidden threshold value.
"""

import hashlib
import json
import re
import unittest
from collections import Counter
from decimal import Decimal
from pathlib import Path

from src import deterministic

ROOT = Path(__file__).resolve().parent.parent
PRODUCTION_CASES = ROOT / "data" / "cases_v1.json"

PR_IDS = [f"PR-{i:02d}" for i in range(1, 11)]
FROZEN_IDS = [f"IF-{i:02d}" for i in range(1, 11)] + [f"SA-{i:02d}" for i in range(1, 11)]

# PR-01 … PR-09 passed the Phase 3B-3R external review and must not change when
# PR-10 is patched (Phase 3B-3R.1).
PR_PASS_IDS = [f"PR-{i:02d}" for i in range(1, 10)]
PR_PASS_HASHES = {
    "PR-01": "326c756e1997c22ec2a5c4fa8ddba58e90748c5204e34527f1fa37dfb526fc28",
    "PR-02": "50f6ffa58c3b985e6d38bb7e7524b0031c6c2a908cd524de4fe8670ab2648b52",
    "PR-03": "d13cbde921ecf69f982fb11247c2db2da35db14f3f7699b57a9d61f0f4ace8a7",
    "PR-04": "76a9a3eb460f3677e53e3ec5f100a74165985ef80bef3e7517a1fdaaa73fcc1d",
    "PR-05": "baa75c94343a96e75a46ec3a57e07f4bbbcf900b97bbb123b88739c52453d87d",
    "PR-06": "a345e0443c806d3038bc0e87c208126eebb7b09408e53ad4c3410853341a05dc",
    "PR-07": "2efac9943de42077c203e6fe1e6b083d84bf04df2e40dc728ab5ac7c24dd8e8f",
    "PR-08": "3585f357fdbec171e0a3af0d06a585415dd7825704b027b1ae5f3775feef1d9c",
    "PR-09": "008889e3a090c538221b32740bac61c52b2080e08b27804331fff30b4fd29f8b",
}

# Frozen Domain 1 / Domain 2 object hashes (sort_keys, compact separators).
FROZEN_HASHES = {
    "IF-01": "397de71403b07772180656167846d1cd32df02d8f6b7c0d887c3e2f65619ce01",
    "IF-02": "8e87960276d118cd4222d7094b19eccaf343efd5f051dd4142b2b0901167e547",
    "IF-03": "4ffdb8a5d38c69bd3ffe0084e4aecce8b341a8e6c3f9d590c4874d23cff0cda6",
    "IF-04": "7e0b437784f4b860af27305165127b7f68f1f17095dcbe7d35983c5b11d86093",
    "IF-05": "af25073bc306f2290823734358ec14d66adaa84775099bf4c2a9cf3ed967d8e1",
    "IF-06": "2af24750bc1e56ed1b620ba6f43ae6d906cc1e3dc37fd9c3115b5c3ceee60831",
    "IF-07": "a2c1a628aa486fdbd2462127fff2a320e3aebdbf28169163c5f2488cc0fae37f",
    "IF-08": "d71bcad2e3957e0512cf54b421fe64f7763a1c44cc0d3a3a74d9cc6275f0c784",
    "IF-09": "dcd60f3b9db0a45fba661573874bbb71167c17e7f2eeb305143f67e99d241764",
    "IF-10": "eca2fb4aef1e42c827f367fe98aa2294f35003c09e369860306bfad222f36e3c",
    "SA-01": "4bb16b8508964d9df9467eccf928c699ca493cd966dfdc90d4cb503d0738219b",
    "SA-02": "f6ed058cbae1b156d88566050fe01a512200aeb5845ebd6a6ba2784bc1122001",
    "SA-03": "d300a4f94574b0da311eb4ae8314b05e9c7db1b9621806d65fbb74444f7a65c5",
    "SA-04": "8e1e5492e22817603887a02eb60e5ce1163bd35595e19cb47ae0e36eb7db8a4e",
    "SA-05": "8c58d5d0035582e6b9413468ec88a2a6cd3bee548129327a301cada51d0ad206",
    "SA-06": "2071cbcdc5c456d0fcd64a21671657af4e9aea544dbaaf6634170d6742deede4",
    "SA-07": "aa2ef061e0dc06cf5d9315b5a1fc64c99a4c11eb28ed2e5e7db79e5247a5ba8d",
    "SA-08": "1095a804dda62c1c2c8f758c0832adad2fc2f10b280938f262925b6e53606d59",
    "SA-09": "2aa230ce084ba2ff597903b376888b4f34f5de1ea2964191799143aeda86a5fd",
    "SA-10": "91a33fea8b0d1c678c4a41a518758c3781887b435ea6af8f8161aa4910d50e91",
}

# APPROVED CASE_MATRIX_V1.md Domain-3 slot tables (working title / diff / lang).
MATRIX_TITLES = {
    "PR-01": "本季度只做两件事",
    "PR-02": "Metric definition for a simple feature",
    "PR-03": "MVP 范围裁剪",
    "PR-04": "上线 / 不上线决策",
    "PR-05": "指标设计含护栏与回滚阈值",
    "PR-06": "权衡推理：质量 / 成本 / 延迟",
    "PR-07": "实验设计",
    "PR-08": "用户问题诊断",
    "PR-09": "路线图选择",
    "PR-10": "模型选型与风险回滚",
}
MATRIX_LANGUAGE = {
    "PR-01": "zh", "PR-02": "en", "PR-03": "zh", "PR-04": "zh", "PR-05": "zh",
    "PR-06": "zh", "PR-07": "zh", "PR-08": "zh", "PR-09": "zh", "PR-10": "mixed",
}
MATRIX_DIFFICULTY = {
    "PR-01": "easy", "PR-02": "easy", "PR-03": "medium", "PR-04": "medium",
    "PR-05": "medium", "PR-06": "medium", "PR-07": "medium", "PR-08": "hard",
    "PR-09": "hard", "PR-10": "hard",
}

# Matrix deterministic plan: 8 Partial (non-empty structural checks), 2 None ([]).
PARTIAL_IDS = ["PR-01", "PR-02", "PR-03", "PR-04", "PR-05", "PR-07", "PR-09", "PR-10"]
NONE_IDS = ["PR-06", "PR-08"]
# Only structural/Partial-style operators are allowed; no Strong objective
# operators (exact_keys, numeric_range, valid_json, ...) may appear.
ALLOWED_PR_CHECK_TYPES = {"ordering", "required_phrases", "required_regex", "exact_bullet_count"}


def object_hash(obj) -> str:
    blob = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def load_document() -> dict:
    with open(PRODUCTION_CASES, encoding="utf-8") as handle:
        return json.load(handle)


def load_by_id() -> dict:
    return {case["id"]: case for case in load_document()["test_cases"]}


def check_named(case: dict, name: str) -> dict:
    return next(c for c in case["deterministic_checks"] if c["name"] == name)


def patterns_of(case: dict) -> list:
    return [c["pattern"] for c in case["deterministic_checks"] if c["type"] == "required_regex"]


class TestPrDomainShape(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = load_document()
        cls.cases = {c["id"]: c for c in cls.doc["test_cases"]}

    def test_exactly_pr_01_through_pr_10_once(self):
        ids = [c["id"] for c in self.doc["test_cases"]]
        self.assertEqual(ids, FROZEN_IDS + PR_IDS)
        self.assertEqual(len(ids), len(set(ids)))

    def test_thirty_production_cases(self):
        self.assertEqual(len(self.doc["test_cases"]), 30)

    def test_no_bc_or_aw_production_cases(self):
        ids = [c["id"] for c in self.doc["test_cases"]]
        self.assertFalse([i for i in ids if i.startswith(("BC-", "AW-"))], msg=ids)

    def test_production_status_is_still_authoring(self):
        self.assertEqual(self.doc["production_status"], "authoring")


class TestMatrixCompliance(unittest.TestCase):
    """Regression guard so the PR domain cannot silently drift from its Matrix slots."""

    @classmethod
    def setUpClass(cls):
        cls.cases = load_by_id()

    def test_titles_match_approved_matrix_working_titles(self):
        titles = {cid: self.cases[cid]["title"] for cid in PR_IDS}
        self.assertEqual(titles, MATRIX_TITLES)

    def test_difficulty_matches_matrix(self):
        got = {cid: self.cases[cid]["difficulty"] for cid in PR_IDS}
        self.assertEqual(got, MATRIX_DIFFICULTY)
        self.assertEqual(Counter(got.values()), {"easy": 2, "medium": 5, "hard": 3})

    def test_language_matches_matrix(self):
        got = {cid: self.cases[cid]["language"] for cid in PR_IDS}
        self.assertEqual(got, MATRIX_LANGUAGE)
        self.assertEqual(Counter(got.values()), {"zh": 8, "en": 1, "mixed": 1})

    def test_all_pr_cases_are_product_reasoning_decision(self):
        for cid in PR_IDS:
            with self.subTest(case=cid):
                self.assertEqual(self.cases[cid]["domain"], "product_reasoning_decision")

    def test_deterministic_plan_is_8_partial_2_none(self):
        for cid in PARTIAL_IDS:
            with self.subTest(case=cid):
                self.assertTrue(self.cases[cid]["deterministic_checks"], msg=cid)
        for cid in NONE_IDS:
            with self.subTest(case=cid):
                self.assertEqual(self.cases[cid]["deterministic_checks"], [])

    def test_no_pr_case_uses_strong_objective_operators(self):
        for cid in PR_IDS:
            with self.subTest(case=cid):
                types = {c["type"] for c in self.cases[cid]["deterministic_checks"]}
                self.assertTrue(types <= ALLOWED_PR_CHECK_TYPES, msg=f"{cid}: {types}")


class TestFrozenIfSaUnchanged(unittest.TestCase):
    def test_twenty_frozen_objects_match_hashes(self):
        cases = load_by_id()
        for cid in FROZEN_IDS:
            with self.subTest(case=cid):
                self.assertEqual(object_hash(cases[cid]), FROZEN_HASHES[cid])

    def test_pr_01_through_pr_09_unchanged(self):
        cases = load_by_id()
        for cid in PR_PASS_IDS:
            with self.subTest(case=cid):
                self.assertEqual(object_hash(cases[cid]), PR_PASS_HASHES[cid])


class TestPrDeclarationValidation(unittest.TestCase):
    def test_every_pr_declaration_validates(self):
        cases = load_by_id()
        for cid in PR_IDS:
            for index, check in enumerate(cases[cid]["deterministic_checks"]):
                with self.subTest(case=cid, check=index):
                    self.assertEqual(deterministic.validate_check_declaration(check), [])


class TestNoWinnerRegexOrHiddenThreshold(unittest.TestCase):
    def test_pr04_decision_regex_is_an_enumeration_not_a_winner(self):
        pattern = patterns_of(load_by_id()["PR-04"])[0]
        # Both outcomes are allowed by the structure check; neither is pinned.
        self.assertIn("上线", pattern)
        self.assertIn("暂缓", pattern)
        self.assertIn("(上线|暂缓)", pattern)

    def test_pr05_trigger_patterns_check_numeric_presence_only(self):
        patterns = patterns_of(load_by_id()["PR-05"])
        row_patterns = [p for p in patterns if p.endswith(r"\d")]
        self.assertEqual(len(row_patterns), 4)  # PRIMARY + 3 GUARDRAIL rows
        for baseline in ("18", "6.0", "4.5", "0.7"):
            self.assertFalse(
                any(baseline in p for p in patterns),
                msg=f"hidden baseline threshold literal {baseline} in a pattern",
            )

    def test_pr10_trigger_patterns_check_numeric_presence_only(self):
        case = load_by_id()["PR-10"]
        patterns = patterns_of(case)
        row_patterns = [p for p in patterns if p.endswith(r"\d")]
        self.assertEqual(len(row_patterns), 3)  # Quality drift / Latency / Cost
        for model in ("Aster", "Birch", "Cedar", "Legacy"):
            self.assertFalse(
                any(model in p for p in patterns),
                msg=f"model winner {model} encoded in a deterministic pattern",
            )

    def test_none_cases_have_no_checks_at_all(self):
        cases = load_by_id()
        self.assertEqual(cases["PR-06"]["deterministic_checks"], [])
        self.assertEqual(cases["PR-08"]["deterministic_checks"], [])


class TestPr01Prioritisation(unittest.TestCase):
    def test_basics(self):
        case = load_by_id()["PR-01"]
        order = check_named(case, "决策规则在选择之前")
        self.assertEqual(order["phrases"], ["决策规则：", "选择：", "理由："])
        self.assertEqual(order["type"], "ordering")
        selection = check_named(case, "选择行包含两个项目槽位")["pattern"]
        # Exactly two slots, drawn from the A-E candidate set (no pinned pair).
        self.assertIn("[A-E]", selection)
        self.assertNotIn("A+B", selection)
        self.assertNotIn("A、C", selection)


class TestPr02MetricDefinition(unittest.TestCase):
    def test_output_contract_and_event_limitation(self):
        case = load_by_id()["PR-02"]
        phrases = check_named(case, "Required metric labels present")["phrases"]
        self.assertEqual(phrases, ["Primary metric:", "Guardrail metric:", "Why:"])
        self.assertIn(
            "No survey data, revenue data, or page-view event is available", case["prompt"]
        )
        for event in (
            "search_run",
            "filter_saved",
            "saved_filter_opened",
            "search_result_clicked",
            "search_error",
        ):
            self.assertIn(event, case["prompt"])


class TestPr03ScopeReduction(unittest.TestCase):
    def test_six_items_and_sections(self):
        case = load_by_id()["PR-03"]
        prompt = case["prompt"]
        for item in ("A.", "B.", "C.", "D.", "E.", "F."):
            self.assertIn(item, prompt)
        self.assertEqual(check_named(case, "六个候选功能对应六条列表项")["count"], 6)
        phrases = check_named(case, "三个部分齐全")["phrases"]
        self.assertEqual(phrases, ["【保留】", "【明确排除】", "【范围原则】"])


class TestPr04LaunchDecision(unittest.TestCase):
    def test_visible_hard_gates_and_current_values(self):
        prompt = load_by_id()["PR-04"]["prompt"]
        self.assertIn("win rate ≥ 55%", prompt)
        self.assertIn("严重错误率 ≤ 1.0%", prompt)
        self.assertIn("p95 延迟 ≤ 1.8 秒", prompt)
        self.assertIn("成本 ≤ 40000 元", prompt)
        self.assertIn("严重错误率：1.4%", prompt)
        self.assertIn("预计每月新增成本：44000 元", prompt)

    def test_regex_is_enumeration_not_winner(self):
        pattern = patterns_of(load_by_id()["PR-04"])[0]
        self.assertIn("(上线|暂缓)", pattern)


class TestPr05MetricGuardrailRollback(unittest.TestCase):
    def test_row_labels_and_numeric_trigger_fields(self):
        case = load_by_id()["PR-05"]
        phrases = check_named(case, "四种行类型存在")["phrases"]
        self.assertEqual(phrases, ["PRIMARY", "GUARDRAIL-1", "GUARDRAIL-2", "GUARDRAIL-3"])
        row_patterns = [p for p in patterns_of(case) if p.endswith(r"\d")]
        self.assertEqual(len(row_patterns), 4)
        # The tests do not prescribe any threshold value.
        for p in patterns_of(case):
            self.assertNotIn("18", p)
            self.assertNotIn("0.7", p)


class TestPr06Tradeoff(unittest.TestCase):
    def test_options_gates_and_math(self):
        case = load_by_id()["PR-06"]
        self.assertEqual(case["deterministic_checks"], [])
        prompt = case["prompt"]
        # All three options clear the hard gates (quality >= 91.5, latency <= 2.0, cost <= 50000).
        for quality in ("94.0", "92.7", "91.8"):
            self.assertIn(quality, prompt)
        self.assertTrue(all(q >= Decimal("91.5") for q in map(Decimal, ("94.0", "92.7", "91.8"))))
        # A vs B: cost +50%, quality +1.3.
        cost_increase = (Decimal("48000") - Decimal("32000")) / Decimal("32000")
        self.assertEqual(cost_increase, Decimal("0.5"))
        self.assertEqual(Decimal("94.0") - Decimal("92.7"), Decimal("1.3"))


class TestPr07ExperimentDesign(unittest.TestCase):
    def test_seven_fields_and_visible_design_facts(self):
        case = load_by_id()["PR-07"]
        expected = [
            "【假设】", "【随机化单位】", "【实验时长】", "【主指标】",
            "【护栏指标】", "【成功条件】", "【提前停止条件】",
        ]
        self.assertEqual(check_named(case, "实验计划字段齐全")["phrases"], expected)
        self.assertEqual(check_named(case, "实验计划字段顺序正确")["phrases"], expected)
        prompt = case["prompt"]
        self.assertIn("同一团队成员会互相影响", prompt)
        self.assertIn("激活定义已经固定", prompt)


class TestPr08Diagnosis(unittest.TestCase):
    def test_no_checks_and_visible_signals(self):
        case = load_by_id()["PR-08"]
        self.assertEqual(case["deterministic_checks"], [])
        prompt = case["prompt"]
        for signal in (
            "移动端导入完成率基本不变",
            "桌面端导入完成率",
            "后端 CSV 上传成功率保持在 98% 左右",
            "mapping_confirmed",
            "相关客服工单中，18张提到",
            "约20%的客户上传的是已经符合系统字段模板的CSV",
        ):
            self.assertIn(signal, prompt)


class TestPr09RoadmapSequencing(unittest.TestCase):
    def test_capacity_dependencies_and_renewal_risk(self):
        case = load_by_id()["PR-09"]
        prompt = case["prompt"]
        self.assertIn("各有 8 个工程周容量", prompt)
        self.assertIn("A. 审计日志完善：3周。是B的前置依赖。", prompt)
        self.assertIn("E. AI实验基础设施：2周。是F的前置依赖", prompt)
        self.assertIn("如果Q1仍频繁导出失败，会影响续约讨论", prompt)
        # No deterministic check encodes a mandatory roadmap winner.
        types = {c["type"] for c in case["deterministic_checks"]}
        self.assertTrue(types <= {"required_phrases", "ordering"})


class TestPr10ModelSelectionRollback(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = load_by_id()["PR-10"]

    def test_new_candidate_and_baseline_roles_are_separated(self):
        prompt = self.case["prompt"]
        # Aster/Birch/Cedar are the new-model candidates; Legacy is baseline +
        # rollback target only and is excluded from new-model gate selection.
        self.assertIn("Aster、Birch、Cedar 是本轮新模型候选", prompt)
        self.assertIn("Legacy 是当前 production model", prompt)
        self.assertIn("只作为现状基线和 rollback target", prompt)
        self.assertIn("不参与本轮新模型候选的 hard-constraint 准入判断", prompt)
        facts = " ".join(self.case["reference_facts"])
        self.assertIn(
            "Legacy不是本轮新模型候选，而是当前production baseline和feature-flag rollback target",
            facts,
        )

    def test_prompt_asks_recommendation_from_new_candidates_only(self):
        prompt = self.case["prompt"]
        self.assertIn("请从 Aster、Birch、Cedar 中推荐一个用于 20% traffic pilot 的新模型", prompt)
        self.assertIn("被硬门槛淘汰的模型不能作为 runner-up", prompt)

    def test_aster_and_birch_eligible_cedar_fails(self):
        facts = " ".join(self.case["reference_facts"])
        floor_quality, ceiling_latency, ceiling_cost = (
            Decimal("92.0"), Decimal("2.0"), Decimal("50000"),
        )
        # Aster: 94.2 / 1.9 / 48000 -> eligible.
        self.assertGreaterEqual(Decimal("94.2"), floor_quality)
        self.assertLessEqual(Decimal("1.9"), ceiling_latency)
        self.assertLessEqual(Decimal("48000"), ceiling_cost)
        # Birch: 92.8 / 1.2 / 33000 -> eligible.
        self.assertGreaterEqual(Decimal("92.8"), floor_quality)
        self.assertLessEqual(Decimal("1.2"), ceiling_latency)
        self.assertLessEqual(Decimal("33000"), ceiling_cost)
        self.assertIn("Aster与Birch满足全部新模型hard constraints", facts)
        # Cedar fails p95 and cost -> cannot be recommendation or runner-up.
        self.assertGreater(Decimal("2.6"), ceiling_latency)
        self.assertGreater(Decimal("55000"), ceiling_cost)
        self.assertIn(
            "Cedar违反p95延迟和成本hard constraints，因此不能被推荐或作为runner-up", facts
        )

    def test_risk_rows_and_structural_triggers(self):
        for row in ("Quality drift", "Latency", "Cost"):
            with self.subTest(row=row):
                self.assertTrue(
                    any(p.endswith(r"\d") and row in p for p in patterns_of(self.case))
                )

    def test_rollback_uses_feature_flag_to_legacy(self):
        prompt = self.case["prompt"]
        self.assertIn("Legacy remains available behind a feature flag for immediate rollback", prompt)
        self.assertIn("如何通过 feature flag 回滚到 Legacy", prompt)

    def test_no_winner_regex_names_a_new_model(self):
        patterns = patterns_of(self.case)
        for model in ("Aster", "Birch", "Cedar", "Legacy"):
            self.assertFalse(any(model in p for p in patterns))

    def test_no_hidden_trigger_thresholds(self):
        patterns = patterns_of(self.case)
        for literal in ("2.6", "55000", "1.9", "1.2", "0.9"):
            self.assertFalse(any(literal in p for p in patterns))


if __name__ == "__main__":
    unittest.main()
