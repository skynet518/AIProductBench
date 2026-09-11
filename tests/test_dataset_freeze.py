"""Permanent AIProductBench CN V1 dataset-freeze invariants.

This module is the final anti-drift guard for the frozen 50-case production
dataset. It pins the semantic manifest, per-case hashes, Matrix slot identity,
global distributions, and the deterministic/judge boundary. It does NOT depend
on any candidate wording.
"""

import hashlib
import json
import re
import unittest
from collections import Counter
from pathlib import Path

from src import deterministic

ROOT = Path(__file__).resolve().parent.parent
PRODUCTION_CASES = ROOT / "data" / "cases_v1.json"
FREEZE_MANIFEST = ROOT / "docs" / "DATASET_FREEZE_V1.md"
MATRIX = ROOT / "docs" / "CASE_MATRIX_V1.md"

MANIFEST_SHA256 = "6b450383e528a5a0a6b813112f96182a3625c04c948839fc551c8ded63da513c"

NONE_IDS = [
    "IF-06", "BC-03", "BC-06", "BC-09", "PR-06", "PR-08",
    "AW-02", "AW-05", "AW-07", "AW-09", "AW-10",
]
STRONG_IDS = [
    "IF-02", "IF-05", "IF-07", "IF-08",
    "SA-01", "SA-02", "SA-04", "SA-06", "SA-10",
    "BC-01", "BC-02", "BC-10",
    "AW-01", "AW-08",
]

# Per-domain language / difficulty plans from APPROVED CASE_MATRIX_V1.md.
DOMAIN_LANGUAGE = {
    "IF": {"zh": 8, "en": 1, "mixed": 1},
    "SA": {"zh": 7, "en": 3, "mixed": 0},
    "PR": {"zh": 8, "en": 1, "mixed": 1},
    "BC": {"zh": 10, "en": 0, "mixed": 0},
    "AW": {"zh": 7, "en": 1, "mixed": 2},
}
DOMAIN_DIFFICULTY = {"easy": 2, "medium": 5, "hard": 3}

# The seven frozen IF/SA cases whose approved display title differs in wording
# from the Matrix *working* title. Identifiers, domains, difficulty, language,
# and deterministic level still match the Matrix exactly.
CASE_TITLE_OVERRIDES = {
    "IF-01": "用户反馈整理为三条问题陈述",
    "IF-02": "Constrained internal release note",
    "IF-04": "需求不清时先澄清",
    "IF-09": "中英双语交接说明",
    "IF-10": "在否定约束下重写",
    "SA-01": "Messy support ticket to fixed schema",
    "SA-08": "矛盾检测与可解决性判断",
}


def object_hash(obj) -> str:
    blob = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def load_document() -> dict:
    with open(PRODUCTION_CASES, encoding="utf-8") as handle:
        return json.load(handle)


def load_cases() -> dict:
    return {c["id"]: c for c in load_document()["test_cases"]}


def build_manifest(cases: dict) -> str:
    return "\n".join(f"{cid} {object_hash(cases[cid])}" for cid in sorted(cases)) + "\n"


def parse_manifest_doc() -> str:
    text = FREEZE_MANIFEST.read_text(encoding="utf-8")
    block = re.search(r"```text\n(.*?)```", text, re.DOTALL).group(1)
    return "\n".join(line for line in block.split("\n") if line.strip()) + "\n"


def parse_matrix_slots() -> dict:
    slots = {}
    for line in MATRIX.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*((?:IF|SA|PR|BC|AW)-\d{2})\s*\|", line)
        if m:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            slots.setdefault(
                cells[0], {"title": cells[1], "difficulty": cells[2], "language": cells[3]}
            )
    return slots


class TestFrozenDatasetCounts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = load_document()
        cls.cases = load_cases()

    def test_production_status_is_complete(self):
        self.assertEqual(self.doc["production_status"], "complete")

    def test_exactly_fifty_cases(self):
        self.assertEqual(len(self.doc["test_cases"]), 50)
        self.assertEqual(len(self.cases), 50)

    def test_ten_cases_per_domain(self):
        counts = Counter(c["domain"] for c in self.cases.values())
        self.assertEqual(
            counts,
            {
                "instruction_constraint_following": 10,
                "structured_information_analysis": 10,
                "product_reasoning_decision": 10,
                "chinese_business_communication": 10,
                "agent_workflow_planning": 10,
            },
        )

    def test_difficulty_distribution(self):
        self.assertEqual(
            Counter(c["difficulty"] for c in self.cases.values()),
            {"easy": 10, "medium": 25, "hard": 15},
        )

    def test_language_distribution(self):
        self.assertEqual(
            Counter(c["language"] for c in self.cases.values()),
            {"zh": 40, "en": 6, "mixed": 4},
        )

    def test_deterministic_distribution(self):
        none_ids = sorted(cid for cid, c in self.cases.items() if c["deterministic_checks"] == [])
        self.assertEqual(none_ids, sorted(NONE_IDS))
        self.assertEqual(len(STRONG_IDS), 14)
        self.assertEqual(len(NONE_IDS), 11)
        self.assertEqual(50 - len(STRONG_IDS) - len(NONE_IDS), 25)  # Partial
        for cid in STRONG_IDS:
            self.assertTrue(self.cases[cid]["deterministic_checks"], msg=cid)

    def test_operator_count_is_21(self):
        self.assertEqual(len(deterministic.SUPPORTED_CHECK_TYPES), 21)


class TestFrozenSemanticManifest(unittest.TestCase):
    def test_manifest_doc_aggregate_matches_expected(self):
        aggregate = hashlib.sha256(parse_manifest_doc().encode("utf-8")).hexdigest()
        self.assertEqual(aggregate, MANIFEST_SHA256)

    def test_recomputed_manifest_matches_expected_and_doc(self):
        manifest = build_manifest(load_cases())
        self.assertEqual(
            hashlib.sha256(manifest.encode("utf-8")).hexdigest(), MANIFEST_SHA256
        )
        self.assertEqual(manifest, parse_manifest_doc())

    def test_manifest_doc_agrees_with_every_case_hash(self):
        recorded = dict(line.split() for line in parse_manifest_doc().splitlines())
        cases = load_cases()
        self.assertEqual(len(recorded), 50)
        for cid in sorted(cases):
            with self.subTest(case=cid):
                self.assertEqual(recorded[cid], object_hash(cases[cid]))


class TestMatrixSlotIdentity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.slots = parse_matrix_slots()
        cls.cases = load_cases()

    def test_case_id_set_equals_matrix_slots(self):
        self.assertEqual(set(self.cases), set(self.slots))
        self.assertEqual(len(self.slots), 50)

    def test_difficulty_and_language_match_matrix_per_case(self):
        for cid, slot in self.slots.items():
            with self.subTest(case=cid):
                self.assertEqual(self.cases[cid]["difficulty"], slot["difficulty"])
                self.assertEqual(self.cases[cid]["language"], slot["language"])

    def test_per_domain_distributions(self):
        for prefix, langs in DOMAIN_LANGUAGE.items():
            ids = [f"{prefix}-{i:02d}" for i in range(1, 11)]
            with self.subTest(prefix=prefix):
                self.assertEqual(
                    Counter(self.cases[i]["difficulty"] for i in ids), DOMAIN_DIFFICULTY
                )
                self.assertEqual(
                    Counter(self.cases[i]["language"] for i in ids),
                    Counter({k: v for k, v in langs.items() if v}),
                )

    def test_titles_match_matrix_or_documented_override(self):
        mismatches = set()
        for cid, slot in self.slots.items():
            expected = CASE_TITLE_OVERRIDES.get(cid, slot["title"])
            self.assertEqual(self.cases[cid]["title"], expected, msg=cid)
            if self.cases[cid]["title"] != slot["title"]:
                mismatches.add(cid)
        # Exactly the seven documented working-title divergences exist.
        self.assertEqual(mismatches, set(CASE_TITLE_OVERRIDES))


class TestDeterministicBoundaryInvariants(unittest.TestCase):
    def test_if06_is_the_matrix_none_case(self):
        if06 = load_cases()["IF-06"]
        self.assertEqual(if06["deterministic_checks"], [])
        self.assertEqual(if06["difficulty"], "medium")
        self.assertEqual(if06["language"], "zh")

    def test_aw03_is_the_unique_label_parallel_batch_version(self):
        prompt = load_cases()["AW-03"]["prompt"]
        self.assertIn("每个任务的完整标签只能出现一次", prompt)
        self.assertIn("A、B、C属于同一个并行批次", prompt)
        self.assertIn("只使用任务字母表示关键路径", prompt)

    def test_aw04_is_the_digits_only_no_universal_count_version(self):
        case = load_cases()["AW-04"]
        self.assertIn("只写阿拉伯数字的非负整数", case["prompt"])
        for row in ("A", "B", "C"):
            pattern = next(
                c["pattern"] for c in case["deterministic_checks"]
                if c["name"] == f"{row}行给出有限数字重试预算"
            )
            self.assertTrue(pattern.endswith("\\d+\\s*\\|"), msg=pattern)


if __name__ == "__main__":
    unittest.main()
