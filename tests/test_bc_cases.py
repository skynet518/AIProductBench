"""Chinese-business-communication (BC) production-domain integrity.

BC-01 … BC-10 were authored externally against the APPROVED
`CASE_MATRIX_V1.md` Domain-4 slots and integrated in Phase 3B-4. These tests pin
the Matrix plan (slot/title, difficulty, language, deterministic strength,
output shape), guard the 30 frozen IF/SA/PR objects, validate declarations, and
assert case-visible source facts. They deliberately do NOT encode graded business
wording, a preferred decision, or canned refusal/response text.
"""

import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path

from src import deterministic

ROOT = Path(__file__).resolve().parent.parent
PRODUCTION_CASES = ROOT / "data" / "cases_v1.json"

BC_IDS = [f"BC-{i:02d}" for i in range(1, 11)]
FROZEN_IDS = (
    [f"IF-{i:02d}" for i in range(1, 11)]
    + [f"SA-{i:02d}" for i in range(1, 11)]
    + [f"PR-{i:02d}" for i in range(1, 11)]
)

# Frozen Domain 1/2/3 object hashes (sort_keys, compact separators). BC
# integration must not alter any of them.
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
    "PR-01": "326c756e1997c22ec2a5c4fa8ddba58e90748c5204e34527f1fa37dfb526fc28",
    "PR-02": "50f6ffa58c3b985e6d38bb7e7524b0031c6c2a908cd524de4fe8670ab2648b52",
    "PR-03": "d13cbde921ecf69f982fb11247c2db2da35db14f3f7699b57a9d61f0f4ace8a7",
    "PR-04": "76a9a3eb460f3677e53e3ec5f100a74165985ef80bef3e7517a1fdaaa73fcc1d",
    "PR-05": "baa75c94343a96e75a46ec3a57e07f4bbbcf900b97bbb123b88739c52453d87d",
    "PR-06": "a345e0443c806d3038bc0e87c208126eebb7b09408e53ad4c3410853341a05dc",
    "PR-07": "2efac9943de42077c203e6fe1e6b083d84bf04df2e40dc728ab5ac7c24dd8e8f",
    "PR-08": "3585f357fdbec171e0a3af0d06a585415dd7825704b027b1ae5f3775feef1d9c",
    "PR-09": "008889e3a090c538221b32740bac61c52b2080e08b27804331fff30b4fd29f8b",
    "PR-10": "24a56be7f26bbd3ccbf07031e8f5deb05297846c03f339e86bcc28e5f9a1c3d4",
}

# APPROVED CASE_MATRIX_V1.md Domain-4 slot tables.
BC_TITLES = {
    "BC-01": "内部进展改写给管理层",
    "BC-02": "会议纪要转行动项",
    "BC-03": "需求澄清邮件",
    "BC-04": "向技术团队转译业务需求",
    "BC-05": "项目风险升级",
    "BC-06": "客户延期说明与补救方案",
    "BC-07": "同一事实面向两类受众改写",
    "BC-08": "避免空话套话的危机沟通",
    "BC-09": "拒绝不合理请求",
    "BC-10": "三页材料压缩成一页汇报稿",
}
BC_DIFFICULTY = {
    "BC-01": "easy", "BC-02": "easy", "BC-03": "medium", "BC-04": "medium",
    "BC-05": "medium", "BC-06": "medium", "BC-07": "medium", "BC-08": "hard",
    "BC-09": "hard", "BC-10": "hard",
}
BC_STRONG_IDS = ["BC-01", "BC-02", "BC-10"]
BC_PARTIAL_IDS = ["BC-04", "BC-05", "BC-07", "BC-08"]
BC_NONE_IDS = ["BC-03", "BC-06", "BC-09"]


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


def check_types(case: dict) -> set:
    return {c["type"] for c in case["deterministic_checks"]}


class TestBcDomainShape(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = load_document()
        cls.cases = {c["id"]: c for c in cls.doc["test_cases"]}

    def test_exactly_bc_01_through_bc_10_once(self):
        ids = [c["id"] for c in self.doc["test_cases"]]
        self.assertEqual(ids, FROZEN_IDS + BC_IDS)
        self.assertEqual(len(ids), len(set(ids)))

    def test_forty_production_cases(self):
        self.assertEqual(len(self.doc["test_cases"]), 40)

    def test_only_aw_domain_unauthored(self):
        ids = [c["id"] for c in self.doc["test_cases"]]
        self.assertFalse([i for i in ids if i.startswith("AW-")], msg=ids)
        c = Counter("".join(ch for ch in i if ch.isalpha()) for i in ids)
        self.assertEqual(c, {"IF": 10, "SA": 10, "PR": 10, "BC": 10})

    def test_production_status_is_still_authoring(self):
        self.assertEqual(self.doc["production_status"], "authoring")

    def test_all_bc_cases_are_chinese_business_communication(self):
        for cid in BC_IDS:
            with self.subTest(case=cid):
                self.assertEqual(self.cases[cid]["domain"], "chinese_business_communication")


class TestBcMatrixCompliance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = load_by_id()

    def test_titles_match_approved_matrix_working_titles(self):
        self.assertEqual({cid: self.cases[cid]["title"] for cid in BC_IDS}, BC_TITLES)

    def test_difficulty_matches_matrix(self):
        got = {cid: self.cases[cid]["difficulty"] for cid in BC_IDS}
        self.assertEqual(got, BC_DIFFICULTY)
        self.assertEqual(Counter(got.values()), {"easy": 2, "medium": 5, "hard": 3})

    def test_all_bc_cases_are_zh(self):
        langs = {cid: self.cases[cid]["language"] for cid in BC_IDS}
        self.assertEqual(set(langs.values()), {"zh"})
        self.assertEqual(len(langs), 10)

    def test_bc_deterministic_plan_is_3_strong_4_partial_3_none(self):
        for cid in BC_STRONG_IDS:
            with self.subTest(case=cid):
                self.assertGreaterEqual(len(self.cases[cid]["deterministic_checks"]), 2)
        for cid in BC_PARTIAL_IDS:
            with self.subTest(case=cid):
                self.assertTrue(self.cases[cid]["deterministic_checks"])
        for cid in BC_NONE_IDS:
            with self.subTest(case=cid):
                self.assertEqual(self.cases[cid]["deterministic_checks"], [])

    def test_output_shape_identities(self):
        # prose: no section/label checks
        self.assertEqual(check_types(self.cases["BC-01"]),
                         {"max_chars", "forbidden_phrases", "required_regex"})
        # bullets/list
        self.assertIn("exact_bullet_count", check_types(self.cases["BC-02"]))
        # email prose
        self.assertEqual(self.cases["BC-03"]["deterministic_checks"], [])
        self.assertIn("邮件", self.cases["BC-03"]["prompt"])
        # mixed prose + requirements list
        self.assertIn("section_bullet_count", check_types(self.cases["BC-04"]))
        # structured escalation note
        self.assertEqual(
            check_named(self.cases["BC-05"], "四个升级字段齐全")["phrases"],
            ["【事实】", "【影响】", "【可选方案】", "【需要决策】"],
        )
        # customer prose
        self.assertEqual(self.cases["BC-06"]["deterministic_checks"], [])
        # two labeled prose sections
        self.assertEqual(
            check_named(self.cases["BC-07"], "两个受众部分齐全")["phrases"],
            ["【事业部负责人】", "【项目执行团队】"],
        )
        self.assertIn("section_max_chars", check_types(self.cases["BC-07"]))
        # prose (blacklist only)
        self.assertEqual(check_types(self.cases["BC-08"]), {"forbidden_phrases"})
        # prose refusal message
        self.assertEqual(self.cases["BC-09"]["deterministic_checks"], [])
        # structured one-pager
        self.assertIn("max_chars", check_types(self.cases["BC-10"]))
        self.assertIn("ordering", check_types(self.cases["BC-10"]))


class TestFrozenDomainsUnchanged(unittest.TestCase):
    def test_thirty_frozen_objects_match_hashes(self):
        cases = load_by_id()
        for cid in FROZEN_IDS:
            with self.subTest(case=cid):
                self.assertEqual(object_hash(cases[cid]), FROZEN_HASHES[cid])


class TestBcDeclarationValidation(unittest.TestCase):
    def test_every_bc_declaration_validates(self):
        cases = load_by_id()
        for cid in BC_IDS:
            for index, check in enumerate(cases[cid]["deterministic_checks"]):
                with self.subTest(case=cid, check=index):
                    self.assertEqual(deterministic.validate_check_declaration(check), [])


class TestBc07AntiStereotype(unittest.TestCase):
    def test_explicit_role_definitions(self):
        prompt = load_by_id()["BC-07"]["prompt"]
        self.assertIn(
            "受众A：事业部负责人。她需要决定是否继续把推荐功能保持在当前灰度比例，"
            "并批准额外1个QA工程日。她关注业务结果、主要风险和需要她做的决定。",
            prompt,
        )
        self.assertIn(
            "受众B：推荐项目执行团队。他们需要安排问题修复、验证和下一轮扩量，"
            "关注具体状态、负责人、前置条件和下一步动作。",
            prompt,
        )

    def test_adaptation_is_role_based_not_stereotype_based(self):
        prompt = load_by_id()["BC-07"]["prompt"]
        self.assertIn(
            "不要根据职位猜测个人性格、权力距离或所谓沟通偏好；只根据题目明确给出的工作职责调整信息。",
            prompt,
        )

    def test_no_stereotype_heuristic_in_declarations(self):
        case = load_by_id()["BC-07"]
        blob = json.dumps(case["deterministic_checks"], ensure_ascii=False)
        for banned in ("性格", "权力距离", "层级", "文化"):
            self.assertNotIn(banned, blob)


class TestBc01ExecutiveSummary(unittest.TestCase):
    def test_cap_jargon_and_visible_figures(self):
        case = load_by_id()["BC-01"]
        cap = check_named(case, "管理层摘要不超过180字符")
        self.assertEqual((cap["type"], cap["count"]), ("max_chars", 180))
        banned = set(check_named(case, "禁用空泛术语和内部黑话")["phrases"])
        self.assertEqual(banned, {"抓手", "赋能", "拉通", "闭环", "回填脚本", "双写链路"})
        prompt = case["prompt"]
        for figure in (
            "80%", "2.8%", "1.1%", "10 月 18 日", "10 月 22 日", "4 天",
            "2 个后端工程日", "2 家",
        ):
            self.assertIn(figure, prompt)
        # No hidden management conclusion: the checks only cover cap/jargon/figures.
        self.assertTrue(check_types(case) <= {"max_chars", "forbidden_phrases", "required_regex"})

    def test_trend_values_are_independent_order_insensitive_presence_checks(self):
        case = load_by_id()["BC-01"]
        patterns = patterns_of(case)
        # The 7-day value is deterministically required.
        self.assertTrue(any(p == "7\\s*天" for p in patterns))
        self.assertIn("保留过去7天", {c["name"] for c in case["deterministic_checks"]})
        # 2.8% and 1.1% are separate presence checks, not one ordered pair.
        self.assertIn("保留2.8%", {c["name"] for c in case["deterministic_checks"]})
        self.assertIn("保留1.1%", {c["name"] for c in case["deterministic_checks"]})
        assert_28 = check_named(case, "保留2.8%")["pattern"]
        assert_11 = check_named(case, "保留1.1%")["pattern"]
        self.assertEqual(assert_28, "2\\.8\\s*[%％]")
        self.assertEqual(assert_11, "1\\.1\\s*[%％]")
        # Oct-18 and Oct-22 are separate presence checks, not one ordered pair.
        self.assertEqual(check_named(case, "保留原计划10月18日")["pattern"], "10\\s*月\\s*18\\s*日")
        self.assertEqual(check_named(case, "保留预计10月22日")["pattern"], "10\\s*月\\s*22\\s*日")
        # No pattern couples old-then-new values (order-independent).
        for p in patterns:
            self.assertFalse("2\\.8" in p and "1\\.1" in p, msg=p)
            self.assertFalse("10\\s*月\\s*18" in p and "10\\s*月\\s*22" in p, msg=p)


class TestBc02MeetingActions(unittest.TestCase):
    def test_bullet_count_owners_and_placeholder(self):
        case = load_by_id()["BC-02"]
        self.assertEqual(check_named(case, "恰好四条行动项")["count"], 4)
        self.assertEqual(check_named(case, "王珂行动项负责人和日期正确")["type"], "required_regex")
        self.assertIn("未指定", check_named(case, "报价模板负责人未指定")["pattern"])
        self.assertIn("未指定", check_named(case, "异常联系人负责人未指定")["pattern"])
        self.assertEqual(
            check_named(case, "不把线下物料作为行动项")["phrases"], ["制作线下宣传物料"]
        )
        self.assertIn("只输出恰好 4 条行动项", case["prompt"])


class TestBc03ClarificationEmail(unittest.TestCase):
    def test_no_checks_four_gaps_and_no_premature_analysis(self):
        case = load_by_id()["BC-03"]
        self.assertEqual(case["deterministic_checks"], [])
        prompt = case["prompt"]
        for gap in ("流失", "分析范围", "数据源", "管理会", "决定"):
            self.assertIn(gap, prompt)
        self.assertIn("不要现在就分析Q3流失原因", prompt)


class TestBc04RequirementTranslation(unittest.TestCase):
    def test_four_requirements_or_logic_and_boundaries(self):
        case = load_by_id()["BC-04"]
        section = check_named(case, "工程需求恰好四条")
        self.assertEqual((section["type"], section["count"]), ("section_bullet_count", 4))
        prompt = case["prompt"]
        self.assertIn("近30天出现过P1，或当前健康分 < 60", prompt)
        self.assertIn("自动邮件不在本期范围", prompt)
        self.assertEqual(
            set(check_named(case, "移除销售口语")["phrases"]),
            {"红灯客户", "来回翻", "续费季到了"},
        )

    def test_no_jargon_instruction_matches_response_wide_checker(self):
        case = load_by_id()["BC-04"]
        # The candidate-visible instruction is explicitly response-wide.
        self.assertIn("最终输出中不要继续使用销售口语", case["prompt"])
        check = check_named(case, "移除销售口语")
        self.assertEqual(check["type"], "forbidden_phrases")
        self.assertEqual(set(check["phrases"]), {"红灯客户", "来回翻", "续费季到了"})


class TestBc05RiskEscalation(unittest.TestCase):
    def test_sections_deadline_and_both_options(self):
        case = load_by_id()["BC-05"]
        self.assertEqual(
            check_named(case, "四个升级字段齐全")["phrases"],
            ["【事实】", "【影响】", "【可选方案】", "【需要决策】"],
        )
        self.assertIn("16:00", case["prompt"])
        self.assertIn("A. 正式切换延期3天", case["prompt"])
        self.assertIn("B. 保持10月25日切换", case["prompt"])
        # No preferred option is imposed deterministically.
        blob = json.dumps(case["deterministic_checks"], ensure_ascii=False)
        self.assertNotIn("方案A", blob)
        self.assertNotIn("方案B", blob)


class TestBc06DelayCommunication(unittest.TestCase):
    def test_no_checks_estimate_vs_date_and_workaround(self):
        case = load_by_id()["BC-06"]
        self.assertEqual(case["deterministic_checks"], [])
        prompt = case["prompt"]
        self.assertIn("还没有足够证据给出一个确定的新交付日期", prompt)
        self.assertIn("每天18:00", prompt)
        self.assertIn("10月14日的配置和使用培训仍然可以正常进行", prompt)


class TestBc07AudienceAdaptation(unittest.TestCase):
    def test_labels_section_cap_and_single_fact_source(self):
        case = load_by_id()["BC-07"]
        self.assertEqual(
            check_named(case, "两个受众部分齐全")["phrases"],
            ["【事业部负责人】", "【项目执行团队】"],
        )
        cap = check_named(case, "事业部负责人版本不超过180字符")
        self.assertEqual((cap["type"], cap["count"]), ("section_max_chars", 180))
        for fact in ("30%流量", "4.2%升到4.8%", "5.1%降到4.6%", "陈泽", "9月14日", "50%", "5.0%", "1个QA工程日"):
            self.assertIn(fact, case["prompt"])


class TestBc08CrisisCommunication(unittest.TestCase):
    def test_blacklist_only_facts_judged(self):
        case = load_by_id()["BC-08"]
        self.assertEqual(len(case["deterministic_checks"]), 1)
        check = case["deterministic_checks"][0]
        self.assertEqual(check["type"], "forbidden_phrases")
        self.assertEqual(
            set(check["phrases"]),
            {"高度重视", "第一时间", "全力以赴", "积极推进", "赋能", "闭环", "总体可控", "部分用户体验受到影响"},
        )
        # No proxy regexes for responsibility/framing.
        self.assertEqual(patterns_of(case), [])
        self.assertIn("约23%的订单创建请求失败", case["prompt"])


class TestBc09Refusal(unittest.TestCase):
    def test_no_checks_unsupported_guarantee_and_alternative(self):
        case = load_by_id()["BC-09"]
        self.assertEqual(case["deterministic_checks"], [])
        prompt = case["prompt"]
        self.assertIn("团队目前无法承诺11月1日上线", prompt)
        self.assertIn("联合计划会", prompt)
        self.assertIn("12月初", prompt)


class TestBc10ExecutiveOnePager(unittest.TestCase):
    def test_cap_sections_and_canonical_figures(self):
        case = load_by_id()["BC-10"]
        cap = check_named(case, "汇报稿不超过420字符")
        self.assertEqual((cap["type"], cap["count"]), ("max_chars", 420))
        self.assertEqual(
            check_named(case, "四部分顺序正确")["phrases"],
            ["【结论】", "【结果】", "【风险】", "【决策请求】"],
        )
        prompt = case["prompt"]
        for figure in (
            "8月20日", "35%", "41.0%", "47.2%", "28.4%", "29.1%", "0.8%",
            "1.2%", "1.6%", "1.0%", "28000元", "2周", "2个后端工程周",
            "1个QA工程周", "连续3天", "60%",
        ):
            self.assertIn(figure, prompt)
        # Deterministic checks verify structure/fact preservation only.
        self.assertTrue(check_types(case) <= {"max_chars", "ordering", "required_regex"})

    def test_key_figures_are_independent_presence_checks(self):
        case = load_by_id()["BC-10"]
        patterns = patterns_of(case)
        # 16 independent key-figure presence checks, no paired/ordered regexes.
        self.assertEqual(len(patterns), 16)
        for p in patterns:
            self.assertFalse("41\\.0" in p and "47\\.2" in p, msg=p)
            self.assertFalse("28\\.4" in p and "29\\.1" in p, msg=p)
            self.assertFalse("0\\.8" in p and "1\\.2" in p, msg=p)
        # Semantic direction remains in the evaluation criteria, not the regexes.
        self.assertTrue(any("方向不发生改变" in c for c in case["evaluation_criteria"]))
        self.assertIn("调整数字出现顺序", case["ambiguity_notes"])


class TestDatasetWideCoverage(unittest.TestCase):
    def test_per_domain_difficulty_matches_matrix(self):
        cases = load_by_id()
        for prefix in ("IF", "SA", "PR", "BC"):
            counts = Counter(
                cases[f"{prefix}-{i:02d}"]["difficulty"] for i in range(1, 11)
            )
            with self.subTest(prefix=prefix):
                self.assertEqual(counts, {"easy": 2, "medium": 5, "hard": 3})

    def test_total_difficulty_for_first_four_domains(self):
        cases = load_by_id()
        counts = Counter(cases[cid]["difficulty"] for cid in FROZEN_IDS + BC_IDS)
        self.assertEqual(counts, {"easy": 8, "medium": 20, "hard": 12})

    def test_bc_contributes_ten_zh(self):
        cases = load_by_id()
        self.assertEqual(sum(1 for cid in BC_IDS if cases[cid]["language"] == "zh"), 10)


if __name__ == "__main__":
    unittest.main()
