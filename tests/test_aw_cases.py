"""Agent-workflow-planning (AW) production-domain integrity.

AW-01 … AW-10 were authored externally against the APPROVED
`CASE_MATRIX_V1.md` Domain-5 slots and integrated in Phase 3B-5, completing all
50 authored slots. These tests pin the Matrix plan (slot/title, difficulty,
language, deterministic strength, output shape), guard the 40 frozen IF/SA/PR/BC
objects, validate declarations, and assert case-visible planning facts. They do
NOT encode a graded plan, a universal retry count, a canonic* boundary answer, or
any real tool execution.
"""

import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path

from src import deterministic

ROOT = Path(__file__).resolve().parent.parent
PRODUCTION_CASES = ROOT / "data" / "cases_v1.json"

AW_IDS = [f"AW-{i:02d}" for i in range(1, 11)]
FROZEN_IDS = (
    [f"IF-{i:02d}" for i in range(1, 11)]
    + [f"SA-{i:02d}" for i in range(1, 11)]
    + [f"PR-{i:02d}" for i in range(1, 11)]
    + [f"BC-{i:02d}" for i in range(1, 11)]
)

# Frozen Domain 1-4 object hashes (sort_keys, compact separators).
FROZEN_HASHES = {
    "IF-01": "397de71403b07772180656167846d1cd32df02d8f6b7c0d887c3e2f65619ce01",
    "IF-02": "8e87960276d118cd4222d7094b19eccaf343efd5f051dd4142b2b0901167e547",
    "IF-03": "4ffdb8a5d38c69bd3ffe0084e4aecce8b341a8e6c3f9d590c4874d23cff0cda6",
    "IF-04": "7e0b437784f4b860af27305165127b7f68f1f17095dcbe7d35983c5b11d86093",
    "IF-05": "af25073bc306f2290823734358ec14d66adaa84775099bf4c2a9cf3ed967d8e1",
    "IF-06": "8f352b868579b7fb07b7ec0224c11d6bbfa72a967312d00a80eb3cbb9c528a03",
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
    "BC-01": "2843e5026057fe3bb45276c1a5a91748526e63c58298c56fa0943b271c193bb8",
    "BC-02": "3f53489613f9d3f07120bdd42393eea28a371b3bb8021a40b7668e61056f51a4",
    "BC-03": "559e63032587702dc708573a8adf9e0907079f3b575451ebe44d00fb78e795d0",
    "BC-04": "b67342f3629e268d2e19d0c176e6e06933f48989c6cbe2ba3c5449878e7aeb70",
    "BC-05": "af3cc685811f2cc29775e89bf099f07953f617ec588764ee7bb2f56050fdbf83",
    "BC-06": "be7f12b37c5138668341fd3d14af18e737034e2287d9f01439a49f2569004e42",
    "BC-07": "a1c0aac7c2faca651b0d76ebcef999e80c75804865f5952433129cb6278b6ff6",
    "BC-08": "3ab2abc60d9a88285f209d4e6bd61d8cf2159ea85946cc8dfecb24cb0db4c588",
    "BC-09": "6445c219fc6235b54149437e1df1caaf9ff04c4973a172d4f13bad936c485fbc",
    "BC-10": "07a1c7d287a311e41bf5448af8dac238e30af13a81ccafef8db1e011b6d5fc38",
}

AW_TITLES = {
    "AW-01": "客服工单自动分类工作流",
    "AW-02": "Tool selection for a simple goal",
    "AW-03": "依赖排序（含数据依赖）",
    "AW-04": "错误与重试处理",
    "AW-05": "权限与安全边界",
    "AW-06": "人工审批门设计",
    "AW-07": "串行 vs 并行判断",
    "AW-08": "工具间数据交接契约",
    "AW-09": "停止条件与预算约束",
    "AW-10": "信息缺失时的升级路径",
}
AW_DIFFICULTY = {
    "AW-01": "easy", "AW-02": "easy", "AW-03": "medium", "AW-04": "medium",
    "AW-05": "medium", "AW-06": "medium", "AW-07": "medium", "AW-08": "hard",
    "AW-09": "hard", "AW-10": "hard",
}
AW_LANGUAGE = {
    "AW-01": "zh", "AW-02": "en", "AW-03": "zh", "AW-04": "zh", "AW-05": "mixed",
    "AW-06": "zh", "AW-07": "zh", "AW-08": "zh", "AW-09": "zh", "AW-10": "mixed",
}
AW_STRONG_IDS = ["AW-01", "AW-08"]
AW_PARTIAL_IDS = ["AW-03", "AW-04", "AW-06"]
AW_NONE_IDS = ["AW-02", "AW-05", "AW-07", "AW-09", "AW-10"]

# APPROVED CASE_MATRIX_V1.md global deterministic-opportunity plan.
GLOBAL_STRONG_IDS = (
    ["IF-02", "IF-05", "IF-07", "IF-08"]
    + ["SA-01", "SA-02", "SA-04", "SA-06", "SA-10"]
    + []  # PR has no Strong slots
    + ["BC-01", "BC-02", "BC-10"]
    + ["AW-01", "AW-08"]
)
GLOBAL_NONE_IDS = [
    "IF-06", "BC-03", "BC-06", "BC-09", "PR-06", "PR-08",
    "AW-02", "AW-05", "AW-07", "AW-09", "AW-10",
]


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


class TestAwDomainShape(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = load_document()
        cls.cases = {c["id"]: c for c in cls.doc["test_cases"]}

    def test_exactly_aw_01_through_aw_10_once(self):
        ids = [c["id"] for c in self.doc["test_cases"]]
        self.assertEqual(ids, FROZEN_IDS + AW_IDS)
        self.assertEqual(len(ids), len(set(ids)))

    def test_fifty_production_cases(self):
        self.assertEqual(len(self.doc["test_cases"]), 50)

    def test_production_status_is_complete(self):
        self.assertEqual(self.doc["production_status"], "complete")

    def test_all_aw_cases_are_agent_workflow_planning(self):
        for cid in AW_IDS:
            with self.subTest(case=cid):
                self.assertEqual(self.cases[cid]["domain"], "agent_workflow_planning")


class TestAwMatrixCompliance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = load_by_id()

    def test_titles_match_approved_matrix_working_titles(self):
        self.assertEqual({cid: self.cases[cid]["title"] for cid in AW_IDS}, AW_TITLES)

    def test_difficulty_and_language_mappings(self):
        self.assertEqual(
            {cid: self.cases[cid]["difficulty"] for cid in AW_IDS}, AW_DIFFICULTY
        )
        self.assertEqual(
            {cid: self.cases[cid]["language"] for cid in AW_IDS}, AW_LANGUAGE
        )
        self.assertEqual(Counter(AW_DIFFICULTY.values()), {"easy": 2, "medium": 5, "hard": 3})
        self.assertEqual(Counter(AW_LANGUAGE.values()), {"zh": 7, "en": 1, "mixed": 2})

    def test_deterministic_plan_is_2_strong_3_partial_5_none(self):
        for cid in AW_STRONG_IDS:
            with self.subTest(case=cid):
                self.assertGreaterEqual(len(self.cases[cid]["deterministic_checks"]), 2)
        for cid in AW_PARTIAL_IDS:
            with self.subTest(case=cid):
                self.assertTrue(self.cases[cid]["deterministic_checks"])
        for cid in AW_NONE_IDS:
            with self.subTest(case=cid):
                self.assertEqual(self.cases[cid]["deterministic_checks"], [])

    def test_output_shape_identities(self):
        self.assertIn("forbidden_regex", {c["type"] for c in self.cases["AW-01"]["deterministic_checks"]})
        self.assertEqual(self.cases["AW-02"]["deterministic_checks"], [])
        self.assertEqual(
            {c["type"] for c in self.cases["AW-03"]["deterministic_checks"]}, {"ordering"}
        )
        self.assertIn("required_regex", {c["type"] for c in self.cases["AW-04"]["deterministic_checks"]})
        self.assertEqual(self.cases["AW-05"]["deterministic_checks"], [])
        self.assertIn("exact_bullet_count", {c["type"] for c in self.cases["AW-06"]["deterministic_checks"]})
        self.assertEqual(self.cases["AW-07"]["deterministic_checks"], [])
        self.assertIn("section_bullet_count", {c["type"] for c in self.cases["AW-08"]["deterministic_checks"]})
        self.assertEqual(self.cases["AW-09"]["deterministic_checks"], [])
        self.assertEqual(self.cases["AW-10"]["deterministic_checks"], [])


class TestFrozenDomainsUnchanged(unittest.TestCase):
    def test_forty_frozen_objects_match_hashes(self):
        cases = load_by_id()
        for cid in FROZEN_IDS:
            with self.subTest(case=cid):
                self.assertEqual(object_hash(cases[cid]), FROZEN_HASHES[cid])


class TestAwDeclarationValidation(unittest.TestCase):
    def test_every_aw_declaration_validates(self):
        cases = load_by_id()
        for cid in AW_IDS:
            for index, check in enumerate(cases[cid]["deterministic_checks"]):
                with self.subTest(case=cid, check=index):
                    self.assertEqual(deterministic.validate_check_declaration(check), [])

    def test_operator_count_is_21(self):
        self.assertEqual(len(deterministic.SUPPORTED_CHECK_TYPES), 21)


class TestGlobalDatasetMatrix(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = load_by_id()

    def test_ten_cases_per_domain(self):
        ids = list(self.cases)
        self.assertEqual(len(ids), 50)
        for prefix in ("IF", "SA", "PR", "BC", "AW"):
            with self.subTest(prefix=prefix):
                self.assertEqual(len([i for i in ids if i.startswith(prefix + "-")]), 10)

    def test_global_difficulty_distribution(self):
        counts = Counter(c["difficulty"] for c in self.cases.values())
        self.assertEqual(counts, {"easy": 10, "medium": 25, "hard": 15})

    def test_per_domain_difficulty_is_two_five_three(self):
        for prefix in ("IF", "SA", "PR", "BC", "AW"):
            counts = Counter(
                self.cases[f"{prefix}-{i:02d}"]["difficulty"] for i in range(1, 11)
            )
            with self.subTest(prefix=prefix):
                self.assertEqual(counts, {"easy": 2, "medium": 5, "hard": 3})

    def test_global_language_distribution(self):
        counts = Counter(c["language"] for c in self.cases.values())
        self.assertEqual(counts, {"zh": 40, "en": 6, "mixed": 4})

    def test_global_deterministic_opportunity_distribution(self):
        none_ids = sorted(cid for cid, c in self.cases.items() if c["deterministic_checks"] == [])
        # APPROVED CASE_MATRIX_V1.md: 14 Strong / 25 Partial / 11 None.
        self.assertEqual(none_ids, sorted(GLOBAL_NONE_IDS))
        self.assertEqual(len(GLOBAL_STRONG_IDS), 14)
        self.assertEqual(len(GLOBAL_NONE_IDS), 11)
        for cid in GLOBAL_STRONG_IDS:
            self.assertTrue(self.cases[cid]["deterministic_checks"], msg=cid)
        # IF-06 is the Matrix-approved judge-only None case (Phase 3B-5R repair).
        self.assertEqual(self.cases["IF-06"]["deterministic_checks"], [])

    def test_per_domain_deterministic_distribution(self):
        strong = {
            "IF": ["IF-02", "IF-05", "IF-07", "IF-08"],
            "SA": ["SA-01", "SA-02", "SA-04", "SA-06", "SA-10"],
            "PR": [],
            "BC": ["BC-01", "BC-02", "BC-10"],
            "AW": ["AW-01", "AW-08"],
        }
        expected = {"IF": (4, 5, 1), "SA": (5, 5, 0), "PR": (0, 8, 2), "BC": (3, 4, 3), "AW": (2, 3, 5)}
        for prefix, (s, p, n) in expected.items():
            ids = [f"{prefix}-{i:02d}" for i in range(1, 11)]
            none = [i for i in ids if self.cases[i]["deterministic_checks"] == []]
            partial = [
                i for i in ids
                if self.cases[i]["deterministic_checks"] and i not in strong[prefix]
            ]
            with self.subTest(prefix=prefix):
                self.assertEqual(
                    (len(strong[prefix]), len(partial), len(none)), (s, p, n)
                )


class TestAw01Decomposition(unittest.TestCase):
    def test_five_ordered_stages_and_approval_gate(self):
        case = load_by_id()["AW-01"]
        stages = ["读取工单", "生成分类候选", "人工审批门", "写入目标队列", "记录处理结果"]
        for i, stage in enumerate(stages, start=1):
            with self.subTest(stage=stage):
                pattern = check_named(case, f"步骤{i}为{stage}")["pattern"]
                # Each numbered step contract requires an input and an output slot.
                self.assertIn("输入：", pattern)
                self.assertIn("输出：", pattern)
        self.assertEqual(check_named(case, "审批门保留0.85阈值")["pattern"], "0\\.85")
        self.assertIn("0.85", case["prompt"])
        self.assertEqual(check_named(case, "不存在第6步")["type"], "forbidden_regex")


class TestAw02ToolSelection(unittest.TestCase):
    def test_no_checks_unnecessary_tools_and_no_publish(self):
        case = load_by_id()["AW-02"]
        self.assertEqual(case["deterministic_checks"], [])
        prompt = case["prompt"]
        for tool in ("csv_reader", "calculator", "text_clusterer"):
            self.assertIn(tool, prompt)
        for unnecessary in ("web_search", "slack_sender", "image_generator", "crm_writer"):
            self.assertIn(unnecessary, prompt)
        self.assertIn("must not send or publish anything", prompt)


class TestAw03DependencyOrdering(unittest.TestCase):
    def test_upstreams_before_merge_and_chain(self):
        case = load_by_id()["AW-03"]
        for name in ("A先于D再到E和F", "B先于D再到E和F", "C先于D再到E和F"):
            phrases = check_named(case, name)["phrases"]
            self.assertEqual(phrases[-2:], ["E. 计算续约风险", "F. 生成优先跟进清单"])
            self.assertEqual(phrases[1], "D. 合并客户主表")

    def test_prompt_requires_unique_labels_and_batch_semantics(self):
        prompt = load_by_id()["AW-03"]["prompt"]
        self.assertIn("每个任务的完整标签只能出现一次", prompt)
        self.assertIn("A、B、C属于同一个并行批次", prompt)
        self.assertIn("三行的相对顺序任意", prompt)
        self.assertIn("【关键路径】", prompt)
        self.assertIn("只使用任务字母表示关键路径", prompt)
        self.assertIn("不要再次写任务的完整名称", prompt)

    def test_no_fixed_relative_order_among_abc(self):
        case = load_by_id()["AW-03"]
        labels = ["A. CRM账户导出", "B. Billing账单导出", "C. Support事件导出"]
        # Each ordering check contributes exactly one A/B/C label, so no check
        # imposes a relative order among A, B, and C.
        for name in ("A先于D再到E和F", "B先于D再到E和F", "C先于D再到E和F"):
            phrases = check_named(case, name)["phrases"]
            self.assertEqual(len([p for p in phrases if p in labels]), 1)


class TestAw04RetrySafety(unittest.TestCase):
    def test_table_shape_and_bounded_retry_fields(self):
        case = load_by_id()["AW-04"]
        header = check_named(case, "失败策略表头正确")["pattern"]
        self.assertIn("最大自动重试次数", header)
        for row in ("A", "B", "C"):
            pattern = check_named(case, f"{row}行给出有限数字重试预算")["pattern"]
            self.assertIn("\\d+", pattern)

    def test_digits_only_cell_contract_is_candidate_visible(self):
        prompt = load_by_id()["AW-04"]["prompt"]
        self.assertIn("只写阿拉伯数字的非负整数", prompt)
        self.assertIn("不要加「次」", prompt)

    def test_no_universal_retry_count(self):
        case = load_by_id()["AW-04"]
        # The retry budget is a wildcard digit field, never a fixed number.
        for row in ("A", "B", "C"):
            pattern = check_named(case, f"{row}行给出有限数字重试预算")["pattern"]
            self.assertTrue(pattern.endswith("\\d+\\s*\\|"), msg=pattern)
        # The three row patterns differ only by the step letter; none prescribes
        # a literal canonical retry count.
        normalized = {
            check_named(case, f"{row}行给出有限数字重试预算")["pattern"].replace(
                f"\\|\\s*{row}\\s*\\|", "\\|\\s*X\\s*\\|"
            )
            for row in ("A", "B", "C")
        }
        self.assertEqual(len(normalized), 1)
        # The prompt never states a single canonical count.
        self.assertIn("题目没有统一的正确次数", case["prompt"])

    def test_side_effect_classes_and_verification_fields(self):
        case = load_by_id()["AW-04"]
        prompt = case["prompt"]
        self.assertIn("只读GET请求，没有外部副作用", prompt)  # A safe read
        self.assertIn("idempotency_key", prompt)  # B write with uncertain completion
        self.assertIn("external_ref", prompt)
        self.assertIn("message_id", prompt)  # C customer-visible send
        self.assertIn("重复发送可能造成客户收到两封邮件", prompt)


class TestAw05AuthorityBoundary(unittest.TestCase):
    def test_no_checks_and_access_is_not_authority(self):
        case = load_by_id()["AW-05"]
        self.assertEqual(case["deterministic_checks"], [])
        prompt = case["prompt"]
        self.assertIn("technically has access", prompt)
        self.assertIn("不要因为某个tool technically available就默认agent有业务权限", prompt)
        for side_effect in ("apply_service_credit", "change_contract_end_date", "delete_customer_data"):
            self.assertIn(side_effect, prompt)


class TestAw06ApprovalGates(unittest.TestCase):
    def test_three_gates_with_required_fields(self):
        case = load_by_id()["AW-06"]
        self.assertEqual(check_named(case, "恰好三个审批门")["count"], 3)
        for n in (1, 2, 3):
            pattern = check_named(case, f"Gate{n}字段完整")["pattern"]
            for field in ("批准对象：", "审批人：", "放行条件：", "未通过："):
                self.assertIn(field, pattern)

    def test_placement_is_not_prescribed(self):
        case = load_by_id()["AW-06"]
        blob = json.dumps(case["deterministic_checks"], ensure_ascii=False)
        for step in ("production执行数据库迁移", "扩大到100%流量", "向受影响客户发送完成通知"):
            self.assertNotIn(step, blob)


class TestAw07Parallelism(unittest.TestCase):
    def test_no_checks_and_single_staging_constraint(self):
        case = load_by_id()["AW-07"]
        self.assertEqual(case["deterministic_checks"], [])
        self.assertIn("团队只有一个staging环境", case["prompt"])
        self.assertIn("C、D、E任意两个都不能同时运行", case["prompt"])


class TestAw08DataContract(unittest.TestCase):
    FIELDS = [
        "event_id", "customer_id", "event_time", "change_type",
        "before_value", "after_value", "source_record_id", "schema_version",
    ]

    def test_eight_fields_and_four_handoff_bullets(self):
        case = load_by_id()["AW-08"]
        self.assertEqual(check_named(case, "Contract恰好8条")["count"], 8)
        self.assertEqual(check_named(case, "Handoff plan恰好4条")["count"], 4)
        for field in self.FIELDS:
            with self.subTest(field=field):
                self.assertEqual(
                    check_named(case, f"{field}字段存在")["pattern"],
                    f"(?m)^-\\s*{field}\\s*｜",
                )

    def test_validation_and_mismatch_boundary(self):
        case = load_by_id()["AW-08"]
        self.assertEqual(
            check_named(case, "三个部分齐全")["phrases"],
            ["【Contract fields】", "【Mismatch handling】", "【Handoff plan】"],
        )
        prompt = case["prompt"]
        self.assertIn("ISO 8601 UTC", prompt)
        self.assertIn("plan_change、owner_change、billing_change", prompt)
        self.assertIn('"1.0"', prompt)
        self.assertIn("继续送进风险评估器", prompt)


class TestAw09StopAndBudget(unittest.TestCase):
    def test_no_checks_and_visible_budgets(self):
        case = load_by_id()["AW-09"]
        self.assertEqual(case["deterministic_checks"], [])
        prompt = case["prompt"]
        self.assertIn("最多40次检索调用", prompt)
        self.assertIn("180秒", prompt)
        self.assertIn("2元", prompt)
        self.assertIn("至少2份相互独立的内部文档", prompt)
        self.assertIn("证据相互矛盾", prompt)
        # No hidden per-item search limit is asserted anywhere.
        self.assertNotIn("单条事实最多", prompt)


class TestAw10Escalation(unittest.TestCase):
    def test_no_checks_missing_inputs_and_deadlines(self):
        case = load_by_id()["AW-10"]
        self.assertEqual(case["deterministic_checks"], [])
        prompt = case["prompt"]
        self.assertIn("CSV没有currency列", prompt)
        self.assertIn("v3.2和v3.3", prompt)
        self.assertIn("没有approval_ticket_id", prompt)
        self.assertIn("3笔requested_amount超过5000", prompt)
        self.assertIn("tomorrow 09:00", prompt)
        self.assertIn("10:00–12:00", prompt)
        self.assertIn("不得猜currency、猜policy version或执行任何退款", prompt)


if __name__ == "__main__":
    unittest.main()
