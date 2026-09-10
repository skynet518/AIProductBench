"""Deterministic-check declaration validation.

Every supported operator has a centrally declared parameter contract in
`src/deterministic.py`. These tests pin that contract: one valid declaration
per operator must pass, and malformed declarations must fail so dataset
validation stops a broken check before any run.
"""

import json
import unittest
from pathlib import Path

from src import cases as cases_module
from src import deterministic

ROOT = Path(__file__).resolve().parent.parent
PRODUCTION_CASES = ROOT / "data" / "cases_v1.json"
FIXTURE = ROOT / "data" / "fixtures" / "synthetic_v1_cases.json"
ARCHIVE = ROOT / "data" / "archive" / "test_cases_v0_1.json"


def load(path: Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def errors_for(check) -> list[str]:
    return deterministic.validate_check_declaration(check)


# One well-formed declaration per supported operator, derived from the runtime
# contract in `_run_check`.
VALID_DECLARATIONS = {
    "valid_json": {"type": "valid_json", "expect": "object"},
    "required_keys": {"type": "required_keys", "keys": ["product_area", "severity"]},
    "forbidden_keys": {"type": "forbidden_keys", "keys": ["legacy_status"]},
    "exact_keys": {"type": "exact_keys", "keys": ["case_ref", "priority", "state"]},
    "exact_item_count": {"type": "exact_item_count", "count": 3},
    "max_items": {"type": "max_items", "count": 3},
    "min_items": {"type": "min_items", "count": 1},
    "max_words": {"type": "max_words", "count": 80},
    "min_words": {"type": "min_words", "count": 10},
    "max_chars": {"type": "max_chars", "count": 120},
    "min_chars": {"type": "min_chars", "count": 10},
    "exact_bullet_count": {"type": "exact_bullet_count", "count": 3},
    "section_max_chars": {
        "type": "section_max_chars",
        "start_marker": "【客服团队】",
        "end_marker": "【销售团队】",
        "count": 120,
    },
    "section_bullet_count": {
        "type": "section_bullet_count",
        "start_marker": "## 变更摘要",
        "end_marker": None,
        "count": 3,
    },
    "required_phrases": {"type": "required_phrases", "phrases": ["甲", "乙"]},
    "forbidden_phrases": {
        "type": "forbidden_phrases",
        "phrases": ["抓手"],
        "case_sensitive": True,
    },
    "ordering": {"type": "ordering", "phrases": ["甲", "乙"]},
    "forbidden_regex": {"type": "forbidden_regex", "pattern": "[!！]"},
    "required_regex": {"type": "required_regex", "pattern": "\\d+"},
    "no_markdown_fence": {"type": "no_markdown_fence"},
    "numeric_range": {
        "type": "numeric_range",
        "pattern": "(\\d+)",
        "min": 0,
        "max": 10,
    },
}


class TestOperatorDeclarationSchema(unittest.TestCase):
    def test_exactly_twenty_one_supported_operators(self):
        self.assertEqual(len(deterministic.SUPPORTED_CHECK_TYPES), 21)

    def test_valid_declarations_cover_every_supported_operator(self):
        self.assertEqual(
            set(VALID_DECLARATIONS), set(deterministic.SUPPORTED_CHECK_TYPES)
        )

    def test_every_valid_declaration_passes(self):
        for kind, declaration in VALID_DECLARATIONS.items():
            with self.subTest(operator=kind):
                self.assertEqual(errors_for(declaration), [])

    def test_declarations_with_a_name_pass(self):
        for kind, declaration in VALID_DECLARATIONS.items():
            with self.subTest(operator=kind):
                named = dict(declaration, name=f"{kind} check")
                self.assertEqual(errors_for(named), [])

    def test_empty_name_fails(self):
        declaration = dict(VALID_DECLARATIONS["max_chars"], name="")
        self.assertTrue(errors_for(declaration))


class TestTypeAndMembership(unittest.TestCase):
    def test_unknown_operator_fails(self):
        errors = errors_for({"type": "vibes"})
        self.assertTrue(errors)
        self.assertIn("unsupported check type", errors[0])

    def test_unknown_operator_suggests_a_close_match(self):
        self.assertIn("max_chars", errors_for({"type": "max_char"})[0])

    def test_missing_type_fails(self):
        self.assertIn("missing a 'type'", errors_for({"name": "no type"})[0])

    def test_non_string_type_fails(self):
        self.assertIn("must be a string", errors_for({"type": 7})[0])

    def test_non_object_declaration_fails(self):
        self.assertIn("must be an object", errors_for("max_chars")[0])

    def test_unexpected_field_fails(self):
        declaration = dict(VALID_DECLARATIONS["max_chars"], cout=120)
        errors = errors_for(declaration)
        self.assertTrue(any("unexpected field 'cout'" in error for error in errors))


class TestCountParameters(unittest.TestCase):
    def test_missing_required_count_fails(self):
        self.assertIn(
            "missing required field 'count'", errors_for({"type": "max_chars"})[0]
        )

    def test_non_integer_count_fails(self):
        self.assertTrue(errors_for({"type": "max_words", "count": "80"}))

    def test_bool_does_not_pass_as_integer_count(self):
        self.assertTrue(errors_for({"type": "max_chars", "count": True}))

    def test_negative_count_fails(self):
        self.assertTrue(errors_for({"type": "min_chars", "count": -1}))

    def test_zero_count_is_allowed_where_meaningful(self):
        self.assertEqual(errors_for({"type": "max_words", "count": 0}), [])
        self.assertEqual(errors_for({"type": "min_items", "count": 0}), [])
        self.assertEqual(
            errors_for(
                {
                    "type": "section_bullet_count",
                    "start_marker": "## S",
                    "end_marker": None,
                    "count": 0,
                }
            ),
            [],
        )

    def test_section_max_chars_requires_a_positive_count(self):
        declaration = {
            "type": "section_max_chars",
            "start_marker": "## S",
            "end_marker": None,
            "count": 0,
        }
        errors = errors_for(declaration)
        self.assertTrue(any("positive integer" in error for error in errors))


class TestStringAndRegexParameters(unittest.TestCase):
    def test_missing_required_string_fails(self):
        self.assertTrue(errors_for({"type": "required_regex"})[0].startswith("is missing"))

    def test_empty_required_string_fails(self):
        self.assertTrue(errors_for({"type": "required_regex", "pattern": ""}))

    def test_non_string_pattern_fails(self):
        self.assertTrue(errors_for({"type": "forbidden_regex", "pattern": 7}))

    def test_invalid_regex_fails(self):
        errors = errors_for({"type": "required_regex", "pattern": "("})
        self.assertTrue(any("not a valid regex" in error for error in errors))

    def test_valid_regex_compiles(self):
        self.assertEqual(
            errors_for({"type": "required_regex", "pattern": "2026-10-20\\s*01:00"}), []
        )


class TestListParameters(unittest.TestCase):
    def test_missing_required_list_fails(self):
        self.assertIn(
            "missing required field 'keys'", errors_for({"type": "exact_keys"})[0]
        )

    def test_empty_list_fails(self):
        self.assertTrue(errors_for({"type": "required_keys", "keys": []}))

    def test_wrong_container_type_fails(self):
        self.assertTrue(errors_for({"type": "required_keys", "keys": "a,b"}))

    def test_non_string_member_fails(self):
        self.assertTrue(errors_for({"type": "forbidden_keys", "keys": ["a", 7]}))

    def test_empty_string_member_fails(self):
        self.assertTrue(errors_for({"type": "ordering", "phrases": ["a", ""]}))

    def test_duplicate_members_fail(self):
        self.assertTrue(errors_for({"type": "required_phrases", "phrases": ["a", "a"]}))

    def test_duplicate_exact_keys_fail(self):
        errors = errors_for({"type": "exact_keys", "keys": ["a", "b", "a"]})
        self.assertTrue(any("duplicate" in error for error in errors))

    def test_non_boolean_case_sensitive_fails(self):
        self.assertTrue(
            errors_for(
                {
                    "type": "required_phrases",
                    "phrases": ["a"],
                    "case_sensitive": "yes",
                }
            )
        )


class TestSectionDeclarations(unittest.TestCase):
    def base(self, **overrides) -> dict:
        declaration = {
            "type": "section_max_chars",
            "start_marker": "## S",
            "end_marker": "## E",
            "count": 120,
        }
        declaration.update(overrides)
        return declaration

    def test_valid_section_declaration_passes(self):
        self.assertEqual(errors_for(self.base()), [])
        self.assertEqual(errors_for(self.base(end_marker=None)), [])

    def test_missing_start_marker_fails(self):
        declaration = self.base()
        del declaration["start_marker"]
        self.assertTrue(errors_for(declaration))

    def test_non_string_start_marker_fails(self):
        self.assertTrue(errors_for(self.base(start_marker=7)))

    def test_empty_start_marker_fails(self):
        self.assertTrue(errors_for(self.base(start_marker="")))

    def test_non_string_non_null_end_marker_fails(self):
        self.assertTrue(errors_for(self.base(end_marker=7)))

    def test_empty_end_marker_fails(self):
        self.assertTrue(errors_for(self.base(end_marker="")))

    def test_missing_end_marker_field_fails(self):
        declaration = self.base()
        del declaration["end_marker"]
        self.assertTrue(errors_for(declaration))

    def test_identical_start_and_end_markers_fail(self):
        errors = errors_for(self.base(end_marker="## S"))
        self.assertTrue(any("must differ" in error for error in errors))

    def test_section_bullet_count_identical_markers_fail(self):
        declaration = {
            "type": "section_bullet_count",
            "start_marker": "## S",
            "end_marker": "## S",
            "count": 2,
        }
        self.assertTrue(any("must differ" in error for error in errors_for(declaration)))


class TestValidJsonAndNumericRange(unittest.TestCase):
    def test_valid_json_accepts_object_and_array(self):
        self.assertEqual(errors_for({"type": "valid_json", "expect": "object"}), [])
        self.assertEqual(errors_for({"type": "valid_json", "expect": "array"}), [])
        self.assertEqual(errors_for({"type": "valid_json"}), [])

    def test_valid_json_rejects_unknown_expect(self):
        self.assertTrue(errors_for({"type": "valid_json", "expect": "tuple"}))

    def test_numeric_range_valid_declaration_passes(self):
        self.assertEqual(
            errors_for({"type": "numeric_range", "pattern": "(\\d+)", "min": 0, "max": 10}),
            [],
        )
        self.assertEqual(errors_for({"type": "numeric_range"}), [])

    def test_numeric_range_requires_a_capture_group(self):
        errors = errors_for({"type": "numeric_range", "pattern": "\\d+"})
        self.assertTrue(any("capture group" in error for error in errors))

    def test_numeric_range_rejects_invalid_pattern(self):
        self.assertTrue(errors_for({"type": "numeric_range", "pattern": "("}))

    def test_numeric_range_rejects_non_numeric_bounds(self):
        self.assertTrue(errors_for({"type": "numeric_range", "min": "0"}))
        self.assertTrue(errors_for({"type": "numeric_range", "max": True}))

    def test_numeric_range_rejects_inverted_bounds(self):
        errors = errors_for({"type": "numeric_range", "min": 10, "max": 1})
        self.assertTrue(any("less than or equal" in error for error in errors))


class TestDatasetIntegration(unittest.TestCase):
    def test_validator_surfaces_declaration_errors(self):
        case = {
            "id": "T-01",
            "title": "t",
            "domain": "instruction_constraint_following",
            "difficulty": "easy",
            "language": "zh",
            "test_intent": "i",
            "prompt": "p",
            "evaluation_criteria": ["c"],
            "tags": ["t"],
            "deterministic_checks": [{"type": "max_chars", "count": "120"}],
        }
        errors = cases_module.validate_cases({"test_cases": [case]})["errors"]
        self.assertTrue(any("deterministic check 0" in error for error in errors))

    def test_synthetic_fixture_passes_declaration_validation(self):
        document = load(FIXTURE)
        for case in document["test_cases"]:
            for check in case.get("deterministic_checks") or []:
                with self.subTest(case=case["id"]):
                    self.assertEqual(deterministic.validate_check_declaration(check), [])

    @unittest.skipUnless(PRODUCTION_CASES.exists(), "production dataset not present")
    def test_production_if_cases_pass_declaration_validation(self):
        document = load(PRODUCTION_CASES)
        for case in document["test_cases"]:
            for index, check in enumerate(case.get("deterministic_checks") or []):
                with self.subTest(case=case["id"], check=index):
                    self.assertEqual(deterministic.validate_check_declaration(check), [])

    def test_archived_v0_1_dataset_has_no_check_declarations(self):
        """The archived V0.1 dataset predates the V1 check schema.

        It declares no deterministic checks at all, so it cannot redefine V1
        operator semantics. It is historical and not part of active validation.
        """
        document = load(ARCHIVE)
        self.assertTrue(document["test_cases"])
        for case in document["test_cases"]:
            self.assertFalse(case.get("deterministic_checks"))


if __name__ == "__main__":
    unittest.main()
