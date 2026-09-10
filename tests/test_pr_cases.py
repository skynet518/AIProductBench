"""Product-reasoning-decision (PR) production-domain integrity.

PR-01 … PR-10 were authored externally and integrated as canonical definitions.
These tests pin the domain shape, validate every deterministic declaration,
guard the 20 frozen IF/SA objects, and independently recompute the quantitative
baselines with decimal-safe arithmetic. They deliberately do NOT encode a
mandatory product recommendation.
"""

import hashlib
import json
import unittest
from collections import Counter
from decimal import Decimal
from pathlib import Path

from src import deterministic

ROOT = Path(__file__).resolve().parent.parent
PRODUCTION_CASES = ROOT / "data" / "cases_v1.json"

PR_IDS = [f"PR-{i:02d}" for i in range(1, 11)]
FROZEN_IDS = [f"IF-{i:02d}" for i in range(1, 11)] + [f"SA-{i:02d}" for i in range(1, 11)]

# Frozen IF-01 … IF-10 and SA-01 … SA-10 object hashes (sort_keys, compact
# separators). Integration of later domains must not alter them.
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

# The deterministic regex checks these quantitative cases are allowed to
# declare, in order. A winner/decision regex would appear here as an extra
# entry, so pinning the exact list proves no such check was added. The PR-05
# `Decision:` / `Trade-off:` / `Guardrail:` entries are label-presence checks,
# not winner matching.
QUANT_REGEX_PATTERNS = {
    "PR-04": ["(?m)^量化基线：\\s*A=600；B=600；C=300；A\\+C=900\\s*$"],
    "PR-05": [
        "(?m)^Quant baseline:\\s*Flat=25920;\\s*Usage=21840\\s*$",
        "(?m)^Decision:",
        "(?m)^Trade-off:",
        "(?m)^Guardrail:",
    ],
    "PR-06": ["(?m)^成本基线：\\s*自研=196000元；供应商=231000元；差额=35000元\\s*$"],
    "PR-10": ["(?m)^量化基线：\\s*A=108万；B=108万；C=0万；D=88万\\s*$"],
}

QUANT_TYPE_SETS = {
    "PR-04": {"required_regex", "required_phrases", "ordering"},
    "PR-05": {"required_regex"},
    "PR-06": {"required_regex", "required_phrases", "ordering"},
    "PR-10": {"required_regex", "required_phrases", "ordering"},
}

# Structure-only cases: these must not gain any regex check (and in particular
# no winner regex).
STRUCTURE_ONLY_IDS = ["PR-01", "PR-02", "PR-03", "PR-07", "PR-08", "PR-09"]

# Canonical answers used only to prove the declared baseline/structure checks are
# satisfiable. They intentionally do NOT encode a graded product recommendation.
DECLARATION_ANSWERS = {
    "PR-04": (
        "量化基线：A=600；B=600；C=300；A+C=900\n"
        "【推荐方案】\n- 组合选择说明。\n"
        "【关键取舍】\n- 取舍说明。\n"
        "【下一步证据】\n- 证据说明。"
    ),
    "PR-05": (
        "Quant baseline: Flat=25920; Usage=21840\n"
        "Decision: choose a package.\n"
        "Trade-off: state the trade-off.\n"
        "Guardrail: state an observable guardrail."
    ),
    "PR-06": (
        "成本基线：自研=196000元；供应商=231000元；差额=35000元\n"
        "【当前建议】\n- 建议说明。\n"
        "【为什么不是只看一年成本】\n- 说明。\n"
        "【三个月后的转向条件】\n- 条件说明。"
    ),
    "PR-10": (
        "量化基线：A=108万；B=108万；C=0万；D=88万\n"
        "【季度组合】\n- 组合说明。\n"
        "【组合总成本与直接风险调整价值】\n- 成本与价值说明。\n"
        "【为什么不选另一个最有诱惑力的组合】\n- 说明。\n"
        "【下季度重新排序的触发条件】\n- 条件说明。"
    ),
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

    def test_pr_difficulty_distribution(self):
        counts = Counter(self.cases[cid]["difficulty"] for cid in PR_IDS)
        self.assertEqual(counts, {"easy": 2, "medium": 5, "hard": 3})

    def test_pr_language_distribution(self):
        counts = Counter(self.cases[cid]["language"] for cid in PR_IDS)
        self.assertEqual(counts, {"zh": 8, "en": 1, "mixed": 1})

    def test_all_pr_cases_are_product_reasoning_decision(self):
        for cid in PR_IDS:
            with self.subTest(case=cid):
                self.assertEqual(self.cases[cid]["domain"], "product_reasoning_decision")

    def test_production_status_is_still_authoring(self):
        self.assertEqual(self.doc["production_status"], "authoring")


class TestFrozenIfSaUnchanged(unittest.TestCase):
    def test_twenty_frozen_objects_match_hashes(self):
        cases = load_by_id()
        for cid in FROZEN_IDS:
            with self.subTest(case=cid):
                self.assertEqual(object_hash(cases[cid]), FROZEN_HASHES[cid])


class TestPrDeclarationValidation(unittest.TestCase):
    def test_every_pr_declaration_validates(self):
        cases = load_by_id()
        for cid in PR_IDS:
            for index, check in enumerate(cases[cid]["deterministic_checks"]):
                with self.subTest(case=cid, check=index):
                    self.assertEqual(
                        deterministic.validate_check_declaration(check), []
                    )


class TestNoWinnerChecks(unittest.TestCase):
    def test_quantitative_cases_only_check_baseline_and_structure(self):
        cases = load_by_id()
        for cid in QUANT_REGEX_PATTERNS:
            with self.subTest(case=cid):
                checks = cases[cid]["deterministic_checks"]
                types = [c["type"] for c in checks]
                self.assertEqual(
                    set(types), QUANT_TYPE_SETS[cid]
                )
                patterns = [c["pattern"] for c in checks if c["type"] == "required_regex"]
                self.assertEqual(patterns, QUANT_REGEX_PATTERNS[cid])

    def test_structure_only_cases_have_no_regex_checks(self):
        cases = load_by_id()
        for cid in STRUCTURE_ONLY_IDS:
            with self.subTest(case=cid):
                types = {c["type"] for c in cases[cid]["deterministic_checks"]}
                self.assertEqual(types, {"required_phrases", "ordering"})

    def test_declaration_answers_pass_structure_and_baseline_checks(self):
        cases = load_by_id()
        for cid, answer in DECLARATION_ANSWERS.items():
            with self.subTest(case=cid):
                result = deterministic.evaluate(cases[cid], answer)
                self.assertTrue(
                    result["all_passed"],
                    msg=f"{cid}: "
                    + "; ".join(
                        f"{c['name']}: {c['detail']}"
                        for c in result["checks"]
                        if not c["passed"]
                    ),
                )


class TestPr04Arithmetic(unittest.TestCase):
    def test_baseline(self):
        a = Decimal("40000") * Decimal("0.015")
        b = Decimal("15000") * Decimal("0.04")
        c = Decimal("25000") * Decimal("0.012")
        self.assertEqual(a, Decimal("600"))
        self.assertEqual(b, Decimal("600"))
        self.assertEqual(c, Decimal("300"))
        self.assertEqual(a + c, Decimal("900"))
        # A(3 weeks) + C(2 weeks) fits the 5-week capacity.
        self.assertEqual(Decimal("3") + Decimal("2"), Decimal("5"))


class TestPr05Arithmetic(unittest.TestCase):
    def test_baseline_and_finance_floor(self):
        flat = Decimal("180") * (Decimal("199") - Decimal("55"))
        usage = Decimal("260") * (Decimal("169") - Decimal("85"))
        self.assertEqual(flat, Decimal("25920"))
        self.assertEqual(usage, Decimal("21840"))
        floor = Decimal("20000")
        self.assertGreater(flat, floor)
        self.assertGreater(usage, floor)


class TestPr06Arithmetic(unittest.TestCase):
    def test_build_vs_buy_baseline(self):
        opportunity = Decimal("8") * Decimal("5") * Decimal("2500")
        in_house = opportunity + Decimal("12") * Decimal("8000")
        vendor = Decimal("15000") + Decimal("12") * Decimal("18000")
        self.assertEqual(opportunity, Decimal("100000"))
        self.assertEqual(in_house, Decimal("196000"))
        self.assertEqual(vendor, Decimal("231000"))
        self.assertEqual(vendor - in_house, Decimal("35000"))


class TestPr10ArithmeticAndDependency(unittest.TestCase):
    def test_risk_adjusted_values(self):
        a = Decimal("120") * Decimal("0.90")
        b = Decimal("240") * Decimal("0.45")
        c = Decimal("0") * Decimal("1.00")
        d = Decimal("110") * Decimal("0.80")
        self.assertEqual(a, Decimal("108"))
        self.assertEqual(b, Decimal("108"))
        self.assertEqual(c, Decimal("0"))
        self.assertEqual(d, Decimal("88"))

    def test_combinations_and_dependency(self):
        # Effort: A=3, B=5, C=2, D=4 weeks; capacity = 9 weeks.
        effort = {"A": Decimal("3"), "B": Decimal("5"), "C": Decimal("2"), "D": Decimal("4")}
        value = {"A": Decimal("108"), "B": Decimal("108"), "C": Decimal("0"), "D": Decimal("88")}
        capacity = Decimal("9")

        self.assertEqual(effort["A"] + effort["D"], Decimal("7"))
        self.assertEqual(value["A"] + value["D"], Decimal("196"))
        self.assertEqual(capacity - (effort["A"] + effort["D"]), Decimal("2"))
        self.assertEqual(effort["A"] + effort["C"] + effort["D"], capacity)
        self.assertEqual(value["A"] + value["C"] + value["D"], Decimal("196"))
        self.assertEqual(
            capacity - (effort["A"] + effort["C"] + effort["D"]), Decimal("0")
        )

        abc_effort = effort["A"] + effort["B"] + effort["C"]
        self.assertEqual(abc_effort, Decimal("10"))
        self.assertGreater(abc_effort, capacity)

        # B depends on C being selected in the same quarter.
        prompt = load_by_id()["PR-10"]["prompt"]
        self.assertIn("B只有在同一季度同时选择C时才是有效组合", prompt)


class TestPhase3b31Patches(unittest.TestCase):
    """Regression guards for the externally reviewed Phase 3B-3.1 patch."""

    @classmethod
    def setUpClass(cls):
        cls.cases = load_by_id()

    def test_pr01_requires_exactly_two_features_and_no_hidden_pair(self):
        case = self.cases["PR-01"]
        self.assertIn("恰好两个功能", case["prompt"])
        self.assertTrue(case["evaluation_criteria"][0].startswith("恰好选择两个功能"))
        notes = case["author_notes"]
        self.assertIn("do not exact-match a hidden feature pair", notes)
        self.assertNotIn("A+B", notes)
        # No deterministic check encodes a preferred feature pair.
        blob = json.dumps(case["deterministic_checks"], ensure_ascii=False)
        self.assertNotIn("A+B", blob)
        self.assertNotIn("A+C", blob)

    def test_pr05_formula_is_unambiguous(self):
        prompt = self.cases["PR-05"]["prompt"]
        self.assertIn(
            "combined average monthly infra-and-support cost per team", prompt
        )
        # The earlier ambiguous "(average revenue per team - average infra + support cost per team)"
        # wording must be gone.
        self.assertNotIn("average infra + support cost per team)", prompt)

    def test_pr06_states_earliest_usable_version_is_week_8(self):
        case = self.cases["PR-06"]
        self.assertIn("最早第 8 周", case["prompt"])
        self.assertTrue(any("最早第8周" in c for c in case["evaluation_criteria"]))
        self.assertTrue(any("最早第8周" in f for f in case["reference_facts"]))
        # The determinism does not infer elapsed time from "8 engineering weeks".
        blob = json.dumps(case["deterministic_checks"], ensure_ascii=False)
        self.assertNotIn("8工程周", blob)

    def test_pr07_strategy_neutral_heading(self):
        case = self.cases["PR-07"]
        new_heading = "【风险控制与退出条件】"
        old_heading = "【Beta边界与退出条件】"
        self.assertIn(new_heading, case["prompt"])
        self.assertNotIn(old_heading, case["prompt"])
        blob = json.dumps(case["deterministic_checks"], ensure_ascii=False)
        self.assertIn(new_heading, blob)
        self.assertNotIn(old_heading, blob)
        # Only the four fixed headings are required; Beta is never mandated.
        expected_phrases = ["【产品决策】", "【各方取舍】", new_heading, "【后续路线图条件】"]
        for name in ("四个部分齐全", "四个部分顺序正确"):
            phrases = check_named(case, name)["phrases"]
            self.assertEqual(phrases, expected_phrases)
            self.assertFalse(any("Beta" in phrase for phrase in phrases))

    def test_pr10_buffer_vs_option_value_is_judge_evaluated(self):
        case = self.cases["PR-10"]
        prompt = case["prompt"]
        self.assertIn("未分配的工程周可以作为 A/D 的交付缓冲", prompt)
        self.assertIn("一旦工程周排给 C，就不能同时作为缓冲", prompt)
        # No deterministic check requires a specific portfolio winner.
        patterns = [c["pattern"] for c in case["deterministic_checks"] if c["type"] == "required_regex"]
        self.assertEqual(
            patterns,
            ["(?m)^量化基线：\\s*A=108万；B=108万；C=0万；D=88万\\s*$"],
        )
        self.assertFalse(any(("A+D" in p or "A+C+D" in p) for p in patterns))
        blob = json.dumps(case["deterministic_checks"], ensure_ascii=False)
        self.assertNotIn("A+C+D", blob)


if __name__ == "__main__":
    unittest.main()
