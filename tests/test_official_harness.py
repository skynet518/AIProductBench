"""Offline tests for the Phase 5 official run harness (no network, no real cost).

These tests cover the execution-layer guarantees of ``run_official.py``: the
frozen incomplete-model rule, restart-safe checkpointing, the retry policy for
transient versus deterministic failures, the hard CNY ceiling, and calibration
sample selection. No provider call is made.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import run_official
from src import cases as cases_module, config


def _candidate_record(model_key: str, case_id: str, domain: str, **overrides):
    record = {
        "model_key": model_key,
        "case_id": case_id,
        "domain": domain,
        "response_text": "answer",
        "error": None,
        "judgements": [],
        "aggregate": None,
    }
    record.update(overrides)
    return record


def _verdict(judge_key: str, *, valid: bool = True, mean: float = 4.7):
    if not valid:
        return {
            "judge_key": judge_key,
            "judge_model_id": "m",
            "scores": None,
            "mean_score": None,
            "normalized_score": None,
            "error": "provider: boom",
            "normalized_cost_cny": None,
        }
    return {
        "judge_key": judge_key,
        "judge_model_id": "m",
        "scores": {
            "task_completion": 5,
            "reasoning_quality": 5,
            "instruction_following": 4,
        },
        "mean_score": mean,
        "normalized_score": 91.67,
        "error": None,
        "normalized_cost_cny": 0.01,
    }


class IncompleteModelRuleTests(unittest.TestCase):
    def test_case_with_two_valid_judges_is_scored(self):
        record = _candidate_record(
            "qwen_value", "IF-01", "instruction_constraint_following"
        )
        payloads = {
            "judge|qwen_value|IF-01|deepseek_flagship": _verdict("deepseek_flagship"),
            "judge|qwen_value|IF-01|glm_flagship": _verdict("glm_flagship"),
        }
        stats = run_official.attach_verdicts([record], payloads)
        self.assertIsNotNone(record["aggregate"])
        self.assertEqual(record["aggregate"]["judges_valid"], 2)
        self.assertEqual(stats["cases_with_two_valid_judges"], 1)
        self.assertIsNone(record.get("judge_unavailable_reason"))

    def test_case_with_one_valid_judge_is_not_scored(self):
        record = _candidate_record(
            "qwen_value", "IF-02", "instruction_constraint_following"
        )
        payloads = {
            "judge|qwen_value|IF-02|deepseek_flagship": _verdict("deepseek_flagship"),
            "judge|qwen_value|IF-02|glm_flagship": _verdict("glm_flagship", valid=False),
        }
        stats = run_official.attach_verdicts([record], payloads)
        self.assertIsNone(record["aggregate"])
        self.assertIn("only 1/2", record["judge_unavailable_reason"])
        self.assertEqual(stats["cases_with_partial_judges"], 1)
        self.assertEqual(len(record["judgements"]), 2)

    def test_candidate_failure_keeps_diagnostics_and_stays_unscored(self):
        record = _candidate_record(
            "qwen_value",
            "IF-03",
            "instruction_constraint_following",
            error="HTTP 401",
            response_text=None,
        )
        run_official.attach_verdicts([record], {})
        self.assertIsNone(record["aggregate"])


class CheckpointResumeTests(unittest.TestCase):
    def _units(self, keys):
        return [
            {
                "key": key,
                "provider_key": "moonshot",
                "model_key": "kimi_value",
                "case_id": "IF-01",
                "estimate_cny": None,
            }
            for key in keys
        ]

    def test_success_and_permanent_failure_are_final_but_transient_retries(self):
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint = Path(tmp) / "calls.jsonl"
            run_official._append_jsonl(checkpoint, {
                "key": "k1",
                "payload": {"error": None},
                "outcome": {"ok": True, "classification": None, "cost_cny": 0.01},
            })
            run_official._append_jsonl(checkpoint, {
                "key": "k2",
                "payload": {"error": "401"},
                "outcome": {"ok": False, "classification": "ACCOUNT_AUTH", "cost_cny": None},
            })
            run_official._append_jsonl(checkpoint, {
                "key": "k3",
                "payload": {"error": "429"},
                "outcome": {"ok": False, "classification": "RATE_LIMIT", "cost_cny": None},
            })

            called: list[str] = []

            def worker(unit):
                called.append(unit["key"])
                return {"error": None}, {
                    "ok": True,
                    "classification": None,
                    "cost_cny": 0.0,
                }

            stats = run_official.execute_units(
                self._units(["k1", "k2", "k3"]),
                worker=worker,
                budget=run_official.Budget(5.0),
                checkpoint_path=checkpoint,
                label="test",
                synthetic=False,
                progress_every=100,
            )
        self.assertEqual(called, ["k3"])
        self.assertEqual(stats["units_already_checkpointed"], 2)

    def test_moonshot_concurrency_override_is_single_flight(self):
        self.assertEqual(
            run_official.PER_PROVIDER_CONCURRENCY_OVERRIDES.get("moonshot"), 1
        )


class BudgetCeilingTests(unittest.TestCase):
    def test_ceiling_blocks_further_calls(self):
        budget = run_official.Budget(1.0)
        budget.add(0.6)
        self.assertTrue(budget.can_afford(0.3, label="ok"))
        self.assertFalse(budget.can_afford(0.5, label="too much"))
        # A refusal is per-call: a unit that does not fit must not latch a global
        # stop, or it would starve cheaper work that still fits.
        self.assertFalse(budget.stopped)
        self.assertIn("ceiling would be exceeded", budget.last_refusal)
        self.assertEqual(budget.remaining(), 0.4)

    def test_unaffordable_unit_does_not_starve_cheaper_units(self):
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint = Path(tmp) / "calls.jsonl"
            called: list[str] = []

            def worker(unit):
                called.append(unit["key"])
                return {}, {"ok": True, "classification": None, "cost_cny": 0.1}

            stats = run_official.execute_units(
                [
                    {
                        "key": "expensive",
                        "provider_key": "moonshot",
                        "model_key": "kimi_flagship",
                        "case_id": "IF-01",
                        "estimate_cny": 9.0,
                    },
                    {
                        "key": "cheap-a",
                        "provider_key": "deepseek",
                        "model_key": "deepseek_value",
                        "case_id": "IF-01",
                        "estimate_cny": 0.2,
                    },
                    {
                        "key": "cheap-b",
                        "provider_key": "minimax_china",
                        "model_key": "minimax_flagship",
                        "case_id": "IF-01",
                        "estimate_cny": 0.2,
                    },
                ],
                worker=worker,
                budget=run_official.Budget(1.0),
                checkpoint_path=checkpoint,
                label="test",
                synthetic=False,
                progress_every=100,
            )
        self.assertNotIn("expensive", called)
        self.assertIn("cheap-a", called)
        self.assertIn("cheap-b", called)
        self.assertEqual(stats["units_skipped_ceiling"], 1)

    def test_units_after_ceiling_are_skipped_not_spent(self):
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint = Path(tmp) / "calls.jsonl"
            called: list[str] = []

            def worker(unit):
                called.append(unit["key"])
                # Observed cost never exceeds the reserved upper bound.
                return {}, {"ok": True, "classification": None, "cost_cny": 0.5}

            stats = run_official.execute_units(
                [
                    {
                        "key": f"u{index}",
                        "provider_key": "deepseek",
                        "model_key": "deepseek_value",
                        "case_id": "IF-01",
                        "estimate_cny": 0.5,
                    }
                    for index in range(4)
                ],
                worker=worker,
                budget=run_official.Budget(1.0),
                checkpoint_path=checkpoint,
                label="test",
                synthetic=False,
                progress_every=100,
            )
        self.assertEqual(len(called), 2)
        self.assertGreater(stats["units_skipped_ceiling"], 0)
        self.assertLessEqual(stats["spent_after"], 1.0 + 1e-9)
        self.assertFalse(stats["budget"]["bound_broken"])

    def test_upper_bound_estimate_covers_output_cap(self):
        pool = run_official.runner.load_model_pool()
        model = next(m for m in pool["models"] if m["key"] == "deepseek_value")
        estimate = run_official._upper_bound_call_cny(model, 2000, synthetic=False)
        self.assertIsNotNone(estimate)
        # The reservation must exceed the D-053 envelope itself, because
        # providers bill reasoning tokens beyond max_tokens.
        envelope = run_official.providers.effective_request_config(model)[
            "max_output_tokens"
        ]
        self.assertEqual(envelope, 32768)
        # The reservation must scale with the doubled D-053 envelope rather than
        # the old 8192 cap (which would reserve well under 0.1 CNY here).
        self.assertEqual(run_official.OUTPUT_TOKEN_BOUND_MULTIPLIER, 2)
        self.assertGreater(estimate, 0.1)
        self.assertLess(estimate, 2.0)


class D053EnvelopeTests(unittest.TestCase):
    def test_registry_revision_and_hash_match_the_harness_expectations(self):
        pool = run_official.runner.load_model_pool()
        snapshot = run_official.models.build_registry_snapshot(pool)
        self.assertEqual(snapshot["snapshot_id"], run_official.EXPECTED_REGISTRY_ID)
        self.assertEqual(snapshot["content_sha256"], run_official.EXPECTED_REGISTRY_HASH)
        self.assertEqual(snapshot["snapshot_id"], "v1-registry-2026-09-11.3")

    def test_candidate_and_judge_ceilings_are_recorded_separately(self):
        pool = run_official.runner.load_model_pool()
        snapshot = run_official.models.build_registry_snapshot(pool)
        self.assertEqual(
            {record["max_output_tokens"] for record in snapshot["models"]}, {32768}
        )
        self.assertEqual(
            {
                record["judge_max_output_tokens"]
                for record in snapshot["models"]
                if record["judge_max_output_tokens"]
            },
            {16384},
        )
        # Judge-role estimates must reserve from the judge envelope, not 32768.
        judge_model = next(m for m in pool["models"] if m["key"] == "qwen_flagship")
        candidate_estimate = run_official._upper_bound_call_cny(
            judge_model, 2000, synthetic=False, role="candidate"
        )
        judge_estimate = run_official._upper_bound_call_cny(
            judge_model, 2000, synthetic=False, role="judge"
        )
        self.assertGreater(candidate_estimate, judge_estimate)

    def test_pricing_snapshot_is_unchanged_by_the_envelope_revision(self):
        pool = run_official.runner.load_model_pool()
        priced = run_official.pricing.build_pricing_snapshot(pool["models"])
        self.assertEqual(priced["snapshot_id"], "v1-pricing-2026-09-11.1")
        self.assertEqual(
            priced["content_sha256"],
            "9f7af42243e5e0b78b1776934de5483f0e3e650765a19dd929e78af10aa15c42",
        )

    def test_d053_timeout_and_kimi_concurrency(self):
        self.assertEqual(config.REQUEST_TIMEOUT_SECONDS, 600)
        self.assertEqual(run_official.OFFICIAL_READ_TIMEOUT_SECONDS, 600)
        self.assertEqual(
            run_official.PER_PROVIDER_CONCURRENCY_OVERRIDES.get("moonshot"), 1
        )
        self.assertLessEqual(run_official.GLOBAL_CONCURRENCY, 6)
        self.assertLessEqual(run_official.PER_PROVIDER_CONCURRENCY, 2)

    def test_envelope_validation_selects_only_previous_failures(self):
        aborted = Path("results/official_run_v1_20260911T075351Z")
        if not (aborted / "checkpoint" / "candidate_calls.jsonl").exists():
            self.skipTest("aborted-run checkpoint not present in this workspace")
        pool = run_official.runner.load_model_pool()
        document = cases_module.load_cases(config.PRODUCTION_CASES_FILE)
        case_index = {
            case["id"]: case for case in cases_module.all_cases(document)
        }
        units = run_official.envelope_units_from_checkpoint(
            aborted, pool, case_index
        )
        self.assertEqual(len(units), 16)
        kinds = [unit["previous_kind"] for unit in units]
        self.assertEqual(kinds.count("empty_response"), 15)
        self.assertEqual(kinds.count("transport_or_other"), 1)
        for unit in units:
            self.assertEqual(unit["model"]["max_output_tokens"], 32768)
            self.assertTrue(unit["key"].startswith("candidate|"))

    def test_finish_reason_is_extracted_and_never_reasoning_text(self):
        payload = {
            "choices": [
                {
                    "finish_reason": "length",
                    "message": {"content": "", "reasoning_content": "hidden"},
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 16384},
        }
        self.assertEqual(
            run_official.providers._extract_finish_reason(payload, "chat_completions"),
            "length",
        )
        text, usage = run_official.providers._extract_text_and_usage(
            payload, "chat_completions"
        )
        self.assertEqual(text, "")
        self.assertEqual(usage["output_tokens"], 16384)
        self.assertNotIn("reasoning_content", usage)


class CalibrationSelectionTests(unittest.TestCase):
    def _synthetic_results(self):
        document = cases_module.load_cases(config.PRODUCTION_CASES_FILE)
        case_list = cases_module.all_cases(document)
        pool = run_official.runner.load_model_pool()
        model_keys = [model["key"] for model in run_official.models.candidates(pool)]
        records = []
        for index, case in enumerate(case_list):
            for model_key in model_keys:
                records.append(
                    _candidate_record(
                        model_key,
                        case["id"],
                        case["domain"],
                        deterministic={
                            "checks": [{"name": "x", "passed": index % 3 != 0}],
                            "checks_passed": 1 if index % 3 != 0 else 0,
                            "checks_total": 1,
                            "constraint_pass_rate": 1.0 if index % 3 != 0 else 0.0,
                            "all_passed": index % 3 != 0,
                        },
                        aggregate={"overall_score": 100.0 - index},
                        judgements=[
                            _verdict("deepseek_flagship", mean=5.0),
                            _verdict("glm_flagship", mean=4.0 if index % 2 else 5.0),
                        ],
                    )
                )
        return records, case_list

    def test_calibration_covers_models_domains_and_slices(self):
        records, case_list = self._synthetic_results()
        selection = run_official.select_calibration(records, case_list)
        distribution = selection["distribution"]
        self.assertEqual(distribution["base"], 50)
        self.assertEqual(distribution["risk"], 10)
        self.assertEqual(distribution["total"], 60)
        self.assertEqual(len(distribution["by_model"]), 10)
        self.assertEqual(set(distribution["by_domain"]), set(config.DOMAINS))
        for sample in selection["samples"]:
            self.assertIsNone(sample["human_labels"])
            self.assertEqual(sample["human_label_status"], "pending_external_review")
            self.assertNotIn("reasoning_content", sample)


class PreflightTests(unittest.TestCase):
    def test_preflight_reports_frozen_provenance(self):
        pool = run_official.runner.load_model_pool()
        document = cases_module.load_cases(config.PRODUCTION_CASES_FILE)
        result = run_official.preflight(pool, document, require_clean_git=False)
        names = {check["check"] for check in result["checks"]}
        self.assertIn("dataset_manifest", names)
        self.assertIn("registry_hash", names)
        self.assertIn("pricing_hash", names)
        self.assertIn("head_matches_baseline", names)
        self.assertEqual(
            result["dataset_manifest_sha256"], run_official.EXPECTED_DATASET_MANIFEST
        )
        self.assertTrue(result["ok"])


if __name__ == "__main__":
    unittest.main()
