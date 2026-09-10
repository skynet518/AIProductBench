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

    def test_empty_case_list_is_rejected(self):
        result = cases_module.validate_cases({"test_cases": []})
        self.assertTrue(result["errors"])


if __name__ == "__main__":
    unittest.main()
