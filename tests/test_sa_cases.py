"""Structured-information-analysis (SA) production-domain integrity.

SA-01 … SA-10 were authored externally and integrated as canonical definitions.
These tests pin the domain's shape and the frozen Domain 1 cases, validate every
deterministic declaration, and run representative canonical correct answers
through the declared deterministic checks.
"""

import hashlib
import json
import re
import unittest
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from src import deterministic

ROOT = Path(__file__).resolve().parent.parent
PRODUCTION_CASES = ROOT / "data" / "cases_v1.json"

SA_IDS = [f"SA-{i:02d}" for i in range(1, 11)]
IF_IDS = [f"IF-{i:02d}" for i in range(1, 11)]

RECOGNIZED_CASE_KEYS = {
    "id",
    "title",
    "domain",
    "difficulty",
    "language",
    "tags",
    "test_intent",
    "prompt",
    "evaluation_criteria",
    "deterministic_checks",
    "reference_facts",
    "expected_structure",
    "ambiguity_notes",
    "author_notes",
}

# Frozen Domain 1 object hashes (sort_keys, compact separators). These pin
# IF-01 … IF-10 so integrating later domains cannot silently alter them.
IF_HASHES = {
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
}


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


def run_named_check(case: dict, name: str, text: str) -> bool:
    check = check_named(case, name)
    return deterministic.evaluate({"deterministic_checks": [check]}, text)["checks"][0][
        "passed"
    ]


# Representative canonical correct answers (asserted to pass every declared check).
CANONICAL_ANSWERS = {
    "SA-01": (
        '{"ticket_id": "T-8841", "product": "Orbit", "priority": "medium", '
        '"issue_type": "access", "customer_tier": "enterprise", "account_owner": null}'
    ),
    "SA-02": "1: BUG\n2: BILLING\n3: FEATURE_REQUEST\n4: ACCESS\n5: OTHER",
    "SA-03": (
        "| 方案 | 预计月成本 | 准确率门槛 | 延迟门槛 | 是否合格 |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| A | 36000 | 满足 | 满足 | 合格 |\n"
        "| B | 28000 | 满足 | 不满足 | 不合格 |\n"
        "| C | 35000 | 满足 | 满足 | 合格 |\n"
        "结论：选择 C，较次优合格方案 A 每月节省 1000 元"
    ),
    "SA-04": (
        '{"customer_id": "C-2048", "name": "Northstar Labs", "plan_code": "ENT", '
        '"state": "suspended", "primary_email": "ops@northstar.example"}'
    ),
    "SA-05": (
        '- Requirement: 同时支持 CSV 与 XLSX 导出 | Evidence: [M2] "本次版本导出必须同时支持 CSV 和 XLSX"\n'
        '- Requirement: 用户可选择最长 90 天的导出日期范围 | Evidence: [M5] "用户必须可以选择导出日期范围，最长 90 天"\n'
        '- Requirement: 文件名必须包含 workspace 名称和导出日期 | Evidence: [M8] "文件名必须包含 workspace 名称和导出日期"\n'
        '- Requirement: 超过 50MB 的文件异步生成并发送站内通知 | Evidence: [M11] "超过 50MB 的文件异步生成，完成后发送站内通知"'
    ),
    "SA-06": (
        '{"verdict":"C","eligible":["A","C"]}\n'
        "理由：C 的审计覆盖率 99% 高于 A 的 95%，且两者均满足全部硬门槛。"
    ),
    "SA-07": (
        "【共同结论】\n"
        "- 批量导出在销售与客服两侧都有明确需求信号，工程预计 10 月 30 日开发完成。\n"
        "- SSO 同样存在需求，但工程表示约需 6 周。\n"
        "【需要决策】\n"
        "- SSO 无法赶上 11 月 15 日，且批量导出与 SSO 可以独立发布，需要决定上线范围与顺序。\n"
        "【来源差异】\n"
        "- Android 崩溃率：销售 2.1%、客服 2.8%、工程 2.3%，材料未给出来源优先级。"
    ),
    "SA-08": (
        "- 矛盾字段：P1事故数；A值：3；B值：2；状态：可解决；依据：Incident Tracker 导出优先于人工事故汇总。\n"
        "- 矛盾字段：已部署版本；A值：2.4.1；B值：2.4.0；状态：可解决；依据：Deployment Console 导出优先于人工周报。\n"
        "- 矛盾字段：灰度比例；A值：50%；B值：30%；状态：可解决；依据：Deployment Console 导出优先于人工周报。\n"
        "- 矛盾字段：支付转化率；A值：4.8%；B值：5.2%；状态：未解决；依据：缺少统一统计口径，也未声明来源优先级。\n"
        "总体判断：支付转化率冲突仍需要补充统一口径的来源信息。"
    ),
    "SA-09": (
        "A — APPROVE — all four gates are known and satisfied\n"
        "B — UNDETERMINED — security review is missing and no known gate fails\n"
        "C — UNDETERMINED — monthly cost is missing and no known gate fails\n"
        "D — REJECT — known accuracy 91.5% is below the 92.0% gate despite missing security\n"
        "Bounded conclusion: Only A can be approved today."
    ),
    "SA-10": (
        "| 排名 | 候选 | 质量 | 成本效率 | 延迟表现 | 支持能力 | 总分 |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        "| 1 | C | 95 | 60 | 90 | 90 | 84.5 |\n"
        "| 2 | B | 87.5 | 90 | 75 | 80 | 84.5 |\n"
        "| 3 | D | 90 | 80 | 85 | 70 | 83.5 |\n"
        "| 4 | A | 92 | 70 | 80 | 85 | 83.1 |\n"
        "方法说明：按候选ID连接四张来源表，使用给定权重，只在最终一步按ROUND_HALF_UP保留1位小数，并在同分时使用质量分作为tie-break。"
    ),
}


class TestSaDomainShape(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = load_document()
        cls.cases = {c["id"]: c for c in cls.doc["test_cases"]}

    def test_sa_block_is_exactly_ten_cases(self):
        ids = [c["id"] for c in self.doc["test_cases"]]
        self.assertEqual([i for i in ids if i.startswith("SA-")], SA_IDS)

    def test_exactly_sa_01_through_sa_10_once(self):
        ids = [c["id"] for c in self.doc["test_cases"]]
        self.assertEqual(ids[:10], IF_IDS)
        self.assertEqual(ids[10:20], SA_IDS)
        self.assertEqual(len(ids), len(set(ids)))

    def test_all_five_domains_are_authored(self):
        ids = [c["id"] for c in self.doc["test_cases"]]
        for prefix in ("IF", "SA", "PR", "BC", "AW"):
            with self.subTest(prefix=prefix):
                self.assertEqual(
                    len([i for i in ids if i.startswith(prefix + "-")]), 10
                )

    def test_sa_cases_are_all_structured_information_analysis(self):
        for cid in SA_IDS:
            with self.subTest(case=cid):
                self.assertEqual(
                    self.cases[cid]["domain"], "structured_information_analysis"
                )

    def test_sa_difficulty_distribution(self):
        got = [self.cases[cid]["difficulty"] for cid in SA_IDS]
        self.assertEqual(got.count("easy"), 2)
        self.assertEqual(got.count("medium"), 5)
        self.assertEqual(got.count("hard"), 3)

    def test_sa_language_distribution(self):
        got = [self.cases[cid]["language"] for cid in SA_IDS]
        self.assertEqual(got.count("zh"), 7)
        self.assertEqual(got.count("en"), 3)
        self.assertEqual(got.count("mixed"), 0)

    def test_production_status_is_complete(self):
        self.assertEqual(self.doc["production_status"], "complete")

    def test_sa_cases_introduce_no_extra_case_metadata(self):
        for cid in SA_IDS:
            with self.subTest(case=cid):
                self.assertEqual(set(self.cases[cid]), RECOGNIZED_CASE_KEYS)

    def test_no_current_web_dependency_metadata(self):
        banned = ("web", "internet", "online", "search", "current")
        for cid in SA_IDS:
            case = self.cases[cid]
            for key in case:
                self.assertFalse(
                    any(token in key.lower() for token in banned), msg=f"{cid} key {key}"
                )
            for tag in case.get("tags", []):
                self.assertFalse(
                    any(token in tag.lower() for token in banned),
                    msg=f"{cid} tag {tag}",
                )


class TestFrozenDomain1Unchanged(unittest.TestCase):
    def test_if_objects_match_frozen_hashes(self):
        cases = load_by_id()
        for cid in IF_IDS:
            with self.subTest(case=cid):
                self.assertEqual(object_hash(cases[cid]), IF_HASHES[cid])


class TestSaDeclarationValidation(unittest.TestCase):
    def test_every_sa_declaration_validates(self):
        cases = load_by_id()
        for cid in SA_IDS:
            for index, check in enumerate(cases[cid]["deterministic_checks"]):
                with self.subTest(case=cid, check=index):
                    self.assertEqual(
                        deterministic.validate_check_declaration(check), []
                    )


class TestSaCanonicalAnswers(unittest.TestCase):
    def test_canonical_answers_pass_every_declared_check(self):
        cases = load_by_id()
        for cid in SA_IDS:
            with self.subTest(case=cid):
                result = deterministic.evaluate(cases[cid], CANONICAL_ANSWERS[cid])
                self.assertTrue(
                    result["all_passed"],
                    msg=f"{cid} failed: "
                    + "; ".join(
                        f"{c['name']}: {c['detail']}"
                        for c in result["checks"]
                        if not c["passed"]
                    ),
                )


class TestSaKeyAssertions(unittest.TestCase):
    """Pin the specific values the external author specified per case."""

    @classmethod
    def setUpClass(cls):
        cls.cases = load_by_id()

    def test_sa01_exact_keys_and_null_owner(self):
        check = check_named(self.cases["SA-01"], "Exact output fields")
        self.assertEqual(
            set(check["keys"]),
            {
                "ticket_id",
                "product",
                "priority",
                "issue_type",
                "customer_tier",
                "account_owner",
            },
        )
        self.assertTrue(
            run_named_check(
                self.cases["SA-01"], "Missing owner remains null", CANONICAL_ANSWERS["SA-01"]
            )
        )
        guessed = CANONICAL_ANSWERS["SA-01"].replace('"account_owner": null', '"account_owner": "ops"')
        self.assertFalse(
            run_named_check(
                self.cases["SA-01"], "Missing owner remains null", guessed
            )
        )

    def test_sa02_five_taxonomy_labels(self):
        expected = {
            "工单1分类正确": "1: BUG",
            "工单2分类正确": "2: BILLING",
            "工单3分类正确": "3: FEATURE_REQUEST",
            "工单4分类正确": "4: ACCESS",
            "工单5分类正确": "5: OTHER",
        }
        for name, line in expected.items():
            with self.subTest(check=name):
                self.assertTrue(run_named_check(self.cases["SA-02"], name, line))

    def test_sa03_arithmetic_and_verdict(self):
        facts = " ".join(self.cases["SA-03"]["reference_facts"])
        for token in ("36000", "28000", "35000"):
            self.assertIn(token, facts)
        self.assertIn("选择C", facts.replace(" ", ""))
        answer = CANONICAL_ANSWERS["SA-03"]
        self.assertTrue(run_named_check(self.cases["SA-03"], "A成本为36000", answer))
        self.assertTrue(run_named_check(self.cases["SA-03"], "B成本为28000", answer))
        self.assertTrue(run_named_check(self.cases["SA-03"], "C成本为35000", answer))
        self.assertTrue(run_named_check(self.cases["SA-03"], "最终选择正确", answer))
        wrong = answer.replace("选择 C，较次优合格方案 A 每月节省 1000 元", "选择 B，较次优合格方案 A 每月节省 8000 元")
        self.assertFalse(run_named_check(self.cases["SA-03"], "最终选择正确", wrong))

    def test_sa04_exact_keys_and_primary_contact(self):
        check = check_named(self.cases["SA-04"], "Exact target keys")
        self.assertEqual(
            set(check["keys"]),
            {"customer_id", "name", "plan_code", "state", "primary_email"},
        )
        self.assertTrue(
            run_named_check(
                self.cases["SA-04"], "primary contact selected", CANONICAL_ANSWERS["SA-04"]
            )
        )
        billing = CANONICAL_ANSWERS["SA-04"].replace(
            "ops@northstar.example", "billing@northstar.example"
        )
        self.assertFalse(
            run_named_check(self.cases["SA-04"], "primary contact selected", billing)
        )

    def test_sa05_four_requirements_and_evidence_ids(self):
        case = self.cases["SA-05"]
        check = check_named(case, "恰好四条需求")
        self.assertEqual(check["count"], 4)
        answer = CANONICAL_ANSWERS["SA-05"]
        for evidence in ("M2", "M5", "M8", "M11"):
            with self.subTest(evidence=evidence):
                self.assertTrue(
                    run_named_check(case, f"包含{evidence}证据", answer)
                )
        too_few = answer.replace(
            '- Requirement: 用户可选择最长 90 天的导出日期范围 | Evidence: [M5] "用户必须可以选择导出日期范围，最长 90 天"\n',
            "",
        )
        self.assertFalse(run_named_check(case, "恰好四条需求", too_few))

    def test_sa05_evidence_spans_are_contiguous_verbatim_source(self):
        case = self.cases["SA-05"]
        messages = {
            f"M{m.group(1)}": m.group(2)
            for m in re.finditer(r"^\[M(\d+)\]\s*(.+)$", case["prompt"], re.M)
        }
        answer = CANONICAL_ANSWERS["SA-05"]
        found = re.findall(r'Evidence:\s*\[M(\d+)\]\s*"([^"]*)"', answer)
        self.assertEqual([f"M{n}" for n, _ in found], ["M2", "M5", "M8", "M11"])
        for number, span in found:
            message_id = f"M{number}"
            with self.subTest(message=message_id):
                self.assertTrue(span, msg="evidence span must not be empty")
                # The quoted span must be a contiguous verbatim substring of that message.
                self.assertIn(span, messages[message_id])
        # A paraphrase of the M2 message is not an acceptable contiguous source span.
        self.assertNotIn("本次版本需要支持 CSV 与 XLSX", messages["M2"])

    def test_sa06_verdict_c_and_eligible_ac(self):
        answer = CANONICAL_ANSWERS["SA-06"]
        self.assertTrue(
            run_named_check(self.cases["SA-06"], "第一行结论结构正确", answer)
        )
        wrong = answer.replace(
            '{"verdict":"C","eligible":["A","C"]}', '{"verdict":"D","eligible":["A","C","D"]}'
        )
        self.assertFalse(
            run_named_check(self.cases["SA-06"], "第一行结论结构正确", wrong)
        )

    def test_sa08_four_contradictions_and_reporting_order(self):
        case = self.cases["SA-08"]
        self.assertEqual(check_named(case, "恰好四条矛盾")["count"], 4)
        order_check = check_named(case, "四个字段按规定顺序出现")
        self.assertEqual(
            order_check["phrases"],
            ["P1事故数", "已部署版本", "灰度比例", "支付转化率"],
        )
        answer = CANONICAL_ANSWERS["SA-08"]
        self.assertTrue(deterministic.evaluate(case, answer)["all_passed"])
        self.assertTrue(run_named_check(case, "四个字段按规定顺序出现", answer))
        five = answer.replace("总体判断：", "- 第五项：无关；状态：可解决；依据：无。\n总体判断：")
        self.assertFalse(run_named_check(case, "恰好四条矛盾", five))
        wrong_order = (
            "- 矛盾字段：已部署版本；A值：2.4.1；B值：2.4.0；状态：可解决；依据：Deployment Console。\n"
            "- 矛盾字段：P1事故数；A值：3；B值：2；状态：可解决；依据：Incident Tracker。\n"
            "- 矛盾字段：灰度比例；A值：50%；B值：30%；状态：可解决；依据：Deployment Console。\n"
            "- 矛盾字段：支付转化率；A值：4.8%；B值：5.2%；状态：未解决；依据：缺少统一口径。\n"
            "总体判断：支付转化率仍需补充信息。"
        )
        self.assertFalse(run_named_check(case, "四个字段按规定顺序出现", wrong_order))

    def test_sa08_resolution_values(self):
        facts = " ".join(self.cases["SA-08"]["reference_facts"])
        self.assertIn("因此2.4.1可作为解决值", facts)
        self.assertIn("因此50%可作为解决值", facts)
        self.assertIn("因此2可作为解决值", facts)
        self.assertIn("因此未解决", facts)
        # The conversion-rate conflict must not be resolved to either truth value.
        self.assertNotIn("4.8可作为解决值", facts)
        self.assertNotIn("5.2可作为解决值", facts)

    def test_sa09_statuses_and_missing_plus_failure(self):
        case = self.cases["SA-09"]
        answer = CANONICAL_ANSWERS["SA-09"]
        for name in (
            "A status correct",
            "B status correct",
            "C status correct",
            "D status correct",
        ):
            with self.subTest(check=name):
                self.assertTrue(run_named_check(case, name, answer))
        self.assertTrue(
            run_named_check(case, "Bounded conclusion present", answer)
        )
        # D carries BOTH a missing security result and a known failed accuracy gate.
        d_row = next(line for line in case["prompt"].splitlines() if line.startswith("| D "))
        self.assertIn("missing", d_row)
        self.assertIn("91.5%", d_row)
        facts = " ".join(case["reference_facts"])
        self.assertIn("D is missing security", facts)
        self.assertIn("91.5%", facts)
        self.assertIn("D is REJECT", facts)
        # Regression: treating D as UNDETERMINED must fail its deterministic status check.
        self.assertFalse(
            run_named_check(case, "D status correct", answer.replace("D — REJECT", "D — UNDETERMINED"))
        )
        # B remains unresolved; mis-approving it fails the B status check.
        self.assertFalse(
            run_named_check(case, "B status correct", answer.replace("B — UNDETERMINED", "B — APPROVE"))
        )

    def test_sa10_decimal_ground_truth_and_tiebreak(self):
        weights = {
            "quality": Decimal("0.40"),
            "cost": Decimal("0.25"),
            "latency": Decimal("0.20"),
            "support": Decimal("0.15"),
        }
        scores = {
            "A": (Decimal("92"), Decimal("70"), Decimal("80"), Decimal("85")),
            "B": (Decimal("87.5"), Decimal("90"), Decimal("75"), Decimal("80")),
            "C": (Decimal("95"), Decimal("60"), Decimal("90"), Decimal("90")),
            "D": (Decimal("90"), Decimal("80"), Decimal("85"), Decimal("70")),
        }
        raw, rounded = {}, {}
        for candidate, (quality, cost, latency, support) in scores.items():
            total = (
                quality * weights["quality"]
                + cost * weights["cost"]
                + latency * weights["latency"]
                + support * weights["support"]
            )
            raw[candidate] = total
            rounded[candidate] = total.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        self.assertEqual(raw["A"], Decimal("83.05"))
        self.assertEqual(
            rounded,
            {
                "A": Decimal("83.1"),
                "B": Decimal("84.5"),
                "C": Decimal("84.5"),
                "D": Decimal("83.5"),
            },
        )
        ranking = sorted(rounded, key=lambda c: (rounded[c], scores[c][0]), reverse=True)
        self.assertEqual(ranking, ["C", "B", "D", "A"])
        # B and C tie on the rounded total; C wins on the higher quality score.
        self.assertEqual(rounded["B"], rounded["C"])
        self.assertGreater(scores["C"][0], scores["B"][0])

        # The canonical answer matches the independently recomputed ground truth.
        answer = CANONICAL_ANSWERS["SA-10"]
        for name in (
            "C第一且84.5",
            "B第二且84.5",
            "D第三且83.5",
            "A第四且83.1",
        ):
            with self.subTest(check=name):
                self.assertTrue(run_named_check(self.cases["SA-10"], name, answer))
        # 83.05 must round HALF_UP to 83.1, not 83.0 (truncation/banker's rounding).
        wrong_rounding = answer.replace(
            "| 4 | A | 92 | 70 | 80 | 85 | 83.1 |", "| 4 | A | 92 | 70 | 80 | 85 | 83.0 |"
        )
        self.assertFalse(
            run_named_check(self.cases["SA-10"], "A第四且83.1", wrong_rounding)
        )
        # Swapping the tie-break (B ahead of C) must fail the ranking checks.
        b_first = answer.replace(
            "| 1 | C | 95 | 60 | 90 | 90 | 84.5 |", "| 1 | B | 87.5 | 90 | 75 | 80 | 84.5 |"
        ).replace(
            "| 2 | B | 87.5 | 90 | 75 | 80 | 84.5 |", "| 2 | C | 95 | 60 | 90 | 90 | 84.5 |"
        )
        self.assertFalse(run_named_check(self.cases["SA-10"], "C第一且84.5", b_first))


if __name__ == "__main__":
    unittest.main()
