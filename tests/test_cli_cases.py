"""CLI case-source wiring: production dataset path vs synthetic fixture."""

import unittest
from pathlib import Path

import run_benchmark
from src import config


class TestCaseSourceWiring(unittest.TestCase):
    def test_default_case_source_is_the_synthetic_fixture(self):
        args = run_benchmark.parse_args(["--validate-only"])
        self.assertEqual(args.cases, config.DEFAULT_CASES_FILE)

    def test_production_flag_uses_the_production_dataset_path(self):
        args = run_benchmark.parse_args(["--validate-only", "--production-cases"])
        self.assertEqual(args.cases, config.PRODUCTION_CASES_FILE)

    def test_production_dataset_path_is_not_the_fixture(self):
        self.assertNotEqual(config.PRODUCTION_CASES_FILE, config.DEFAULT_CASES_FILE)
        self.assertEqual(Path(config.PRODUCTION_CASES_FILE).name, "cases_v1.json")

    def test_explicit_cases_path_still_wins_without_the_flag(self):
        args = run_benchmark.parse_args(["--validate-only", "--cases", "data/custom.json"])
        self.assertEqual(args.cases, Path("data/custom.json"))


if __name__ == "__main__":
    unittest.main()
