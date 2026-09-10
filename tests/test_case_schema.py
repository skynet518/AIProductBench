"""Case schema validation and the frozen five-domain rule."""

import copy
import json
import unittest
from pathlib import Path

from src import cases as cases_module
from src import config

FIXTURE = Path(__file__).resolve().parent.parent / "data" / "fixtures" / "synthetic_v1_cases.json"


def load_fixture() -> dict:
    with open(FIXTURE, encoding="utf-8") as handle:
        return json.load(handle)


def first_case(document: dict) -> dict:
    return document["test_cases"][0]


def make_case(**overrides) -> dict:
    case = {
        "id": "T-01",
        "title": "test case",
        "domain": "instruction_constraint_following",
        "difficulty": "easy",
        "language": "zh",
        "test_intent": "verify something specific",
        "prompt": "do the thing",
        "evaluation_criteria": ["a concrete criterion"],
        "tags": ["test"],
        "deterministic_checks": [],
    }
    case.update(overrides)
    return case


def errors_for(case: dict) -> list[str]:
    return cases_module.validate_cases({"test_cases": [case]})["errors"]


class TestConfiguredDomains(unittest.TestCase):
    def test_exactly_five_domains_configured(self):
        self.assertEqual(len(config.DOMAINS), 5)
        self.assertEqual(len(set(config.DOMAINS)), 5)

    def test_domain_names_are_the_frozen_set(self):
        self.assertEqual(
            list(config.DOMAINS),
            [
                "instruction_constraint_following",
                "structured_information_analysis",
                "product_reasoning_decision",
                "chinese_business_communication",
                "agent_workflow_planning",
            ],
        )

    def test_each_domain_has_a_short_label(self):
        for domain in config.DOMAINS:
            self.assertIn(domain, config.DOMAIN_SHORT_LABELS)


class TestCaseSchema(unittest.TestCase):
    def test_fixture_is_valid(self):
        result = cases_module.validate_cases(load_fixture())
        self.assertEqual(result["errors"], [])

    def test_fixture_is_labelled_synthetic(self):
        document = load_fixture()
        self.assertTrue(document["synthetic"])
        warnings = cases_module.validate_cases(document)["warnings"]
        self.assertTrue(any("SYNTHETIC FIXTURE" in warning for warning in warnings))

    def test_fixture_covers_all_five_domains(self):
        distribution = cases_module.domain_distribution(
            cases_module.all_cases(load_fixture())
        )
        self.assertEqual(len(distribution), 5)
        self.assertTrue(all(count >= 1 for count in distribution.values()))

    def test_missing_required_field_is_an_error(self):
        document = load_fixture()
        del first_case(document)["difficulty"]
        result = cases_module.validate_cases(document)
        self.assertTrue(any("difficulty" in error for error in result["errors"]))

    def test_unknown_domain_is_an_error(self):
        document = load_fixture()
        first_case(document)["domain"] = "coding"
        result = cases_module.validate_cases(document)
        self.assertTrue(any("coding" in error for error in result["errors"]))

    def test_unknown_difficulty_is_an_error(self):
        document = load_fixture()
        first_case(document)["difficulty"] = "extreme"
        result = cases_module.validate_cases(document)
        self.assertTrue(any("extreme" in error for error in result["errors"]))

    def test_unknown_language_is_an_error(self):
        document = load_fixture()
        first_case(document)["language"] = "ja"
        result = cases_module.validate_cases(document)
        self.assertTrue(any("ja" in error for error in result["errors"]))

    def test_duplicate_case_id_is_an_error(self):
        document = load_fixture()
        duplicate = copy.deepcopy(first_case(document))
        document["test_cases"].append(duplicate)
        result = cases_module.validate_cases(document)
        self.assertTrue(any("Duplicate case id" in error for error in result["errors"]))

    def test_empty_evaluation_criteria_is_an_error(self):
        document = load_fixture()
        first_case(document)["evaluation_criteria"] = []
        result = cases_module.validate_cases(document)
        self.assertTrue(
            any("evaluation_criteria" in error for error in result["errors"])
        )

    def test_malformed_deterministic_check_is_an_error(self):
        document = load_fixture()
        first_case(document)["deterministic_checks"] = [{"name": "no type"}]
        result = cases_module.validate_cases(document)
        self.assertTrue(any("deterministic check" in error for error in result["errors"]))

    def test_missing_domain_is_a_warning_not_an_error(self):
        document = load_fixture()
        document["test_cases"] = [
            case
            for case in document["test_cases"]
            if case["domain"] != "agent_workflow_planning"
        ]
        result = cases_module.validate_cases(document)
        self.assertEqual(result["errors"], [])
        self.assertTrue(
            any("agent_workflow_planning" in warning for warning in result["warnings"])
        )

    def test_small_dataset_is_a_warning_not_an_error(self):
        result = cases_module.validate_cases(load_fixture())
        self.assertTrue(
            any("production target is 50" in warning for warning in result["warnings"])
        )

    def test_authoring_dataset_is_flagged_as_not_final(self):
        document = load_fixture()
        document["production_status"] = "authoring"
        result = cases_module.validate_cases(document)
        self.assertEqual(result["errors"], [])
        self.assertTrue(
            any(
                "partial authoring dataset" in warning
                and "not eligible as the final V1 benchmark dataset" in warning
                for warning in result["warnings"]
            )
        )

    def test_complete_dataset_is_not_flagged_as_partial(self):
        document = load_fixture()
        document["production_status"] = "complete"
        result = cases_module.validate_cases(document)
        self.assertFalse(
            any("partial authoring dataset" in warning for warning in result["warnings"])
        )

    def test_empty_case_list_is_rejected(self):
        result = cases_module.validate_cases({"test_cases": []})
        self.assertTrue(result["errors"])


class TestProductionSchemaFields(unittest.TestCase):
    def test_full_production_case_is_valid(self):
        self.assertEqual(errors_for(make_case()), [])

    def test_missing_test_intent_is_an_error(self):
        case = make_case()
        del case["test_intent"]
        self.assertTrue(any("test_intent" in error for error in errors_for(case)))

    def test_missing_tags_is_an_error(self):
        case = make_case()
        del case["tags"]
        self.assertTrue(any("tags" in error for error in errors_for(case)))

    def test_empty_tags_is_an_error(self):
        self.assertTrue(any("tags" in error for error in errors_for(make_case(tags=[]))))

    def test_missing_title_is_an_error(self):
        case = make_case()
        del case["title"]
        self.assertTrue(any("title" in error for error in errors_for(case)))

    def test_fixture_cases_satisfy_the_production_schema(self):
        for case in cases_module.all_cases(load_fixture()):
            self.assertTrue(case.get("test_intent"), msg=case["id"])
            self.assertTrue(case.get("tags"), msg=case["id"])


class TestWordCountLanguageRule(unittest.TestCase):
    """Whitespace word counts are a valid length measure for English only."""

    def test_chinese_case_rejects_max_words(self):
        case = make_case(
            language="zh", deterministic_checks=[{"type": "max_words", "count": 80}]
        )
        errors = errors_for(case)
        self.assertTrue(any("max_words" in error for error in errors), msg=errors)
        self.assertTrue(any("max_chars" in error for error in errors), msg=errors)

    def test_chinese_case_rejects_min_words(self):
        case = make_case(
            language="zh", deterministic_checks=[{"type": "min_words", "count": 30}]
        )
        self.assertTrue(any("min_words" in error for error in errors_for(case)))

    def test_chinese_case_allows_character_limits(self):
        case = make_case(
            language="zh",
            deterministic_checks=[{"type": "max_chars", "count": 120}],
        )
        self.assertEqual(errors_for(case), [])

    def test_english_case_allows_word_count_checks(self):
        case = make_case(
            language="en",
            deterministic_checks=[
                {"type": "max_words", "count": 120},
                {"type": "min_words", "count": 30},
            ],
        )
        self.assertEqual(errors_for(case), [])

    def test_mixed_case_rejects_word_count_without_justification(self):
        case = make_case(
            language="mixed",
            deterministic_checks=[{"type": "max_words", "count": 120}],
        )
        errors = errors_for(case)
        self.assertTrue(any("word_count_justification" in error for error in errors))

    def test_mixed_case_allows_word_count_with_justification(self):
        case = make_case(
            language="mixed",
            deterministic_checks=[{"type": "max_words", "count": 120}],
            word_count_justification=(
                "The expected answer is English prose; the Chinese source appears only in "
                "the quoted input, so a whitespace word count is a valid length measure."
            ),
        )
        self.assertEqual(errors_for(case), [])

    def test_blank_justification_is_not_accepted(self):
        case = make_case(
            language="mixed",
            deterministic_checks=[{"type": "max_words", "count": 120}],
            word_count_justification="   ",
        )
        self.assertTrue(errors_for(case))

    def test_non_length_checks_are_unaffected_by_language(self):
        case = make_case(
            language="zh",
            deterministic_checks=[
                {"type": "exact_bullet_count", "count": 3},
                {"type": "forbidden_phrases", "phrases": ["赋能"]},
            ],
        )
        self.assertEqual(errors_for(case), [])


if __name__ == "__main__":
    unittest.main()
