"""Offline tests for the Phase 4D smoke harness (no network, no real cost).

These tests replace the provider transport with a deterministic fake so the
smoke orchestration logic — scope locking, budget ceiling, error
classification, credential blocking — can be exercised without any paid call.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
import datetime as dt
from pathlib import Path
from unittest import mock

import run_smoke
from src import providers, runner


def _fake_chat(model, messages, *, at=None, fx_snapshot=None):
    """Deterministic fake provider transport used only by these tests."""
    at = at or dt.datetime.now(dt.timezone.utc)
    is_judge = any("strict evaluator" in (m.get("content") or "") for m in messages)
    if is_judge:
        text = json.dumps(
            {
                "scores": {
                    "task_completion": 3,
                    "reasoning_quality": 3,
                    "instruction_following": 3,
                },
                "rationale": "Test-only placeholder rationale.",
            }
        )
    else:
        text = "Test-only placeholder candidate response."

    input_tokens = 100
    output_tokens = 50
    cost = providers.pricing.price_call(
        model,
        input_tokens,
        output_tokens,
        at=at,
        fx_snapshot=fx_snapshot,
    )
    return {
        "text": text,
        "latency_ms": 12.5,
        "model_key": model["key"],
        "model_id": model.get("model_id"),
        "called_at": "2026-09-11T00:00:00+00:00",
        "attempts": 1,
        "synthetic": False,
        "error": None,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "reasoning_tokens": None,
        "cached_input_tokens": None,
        **{key: cost[key] for key in cost},
    }


class TestSmokeHarness(unittest.TestCase):
    def _run(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        output = Path(tmp.name) / "smoke.json"
        with mock.patch("src.providers.chat", side_effect=_fake_chat):
            code = run_smoke.run_smoke(confirm=True, output=output)
        with open(output, encoding="utf-8") as handle:
            return code, json.load(handle)

    def test_full_smoke_pass_offline(self):
        code, document = self._run()
        self.assertEqual(code, 0)
        self.assertEqual(len(document["models"]), 10)
        self.assertTrue(all(m["status"] == "SMOKE_PASS" for m in document["models"]))
        # 3 candidate calls + 3 cases x 2 judges per model.
        self.assertEqual(document["totals"]["candidate_calls"], 30)
        self.assertEqual(document["totals"]["judge_calls"], 60)
        self.assertEqual(document["totals"]["total_api_calls"], 90)
        self.assertFalse(document["totals"]["budget_stopped"])
        self.assertLess(document["totals"]["total_cost_cny"], 100.0)

    def test_cost_ceiling_stops_new_calls(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        output = Path(tmp.name) / "smoke.json"
        with mock.patch.object(run_smoke, "SMOKE_COST_CEILING_CNY", 0.000001):
            with mock.patch("src.providers.chat", side_effect=_fake_chat):
                code = run_smoke.run_smoke(confirm=True, output=output)
        with open(output, encoding="utf-8") as handle:
            document = json.load(handle)
        self.assertEqual(code, 1)
        self.assertTrue(document["totals"]["budget_stopped"])
        self.assertLess(document["totals"]["total_api_calls"], 90)
        self.assertIsNotNone(document["totals"]["budget_stop_reason"])

    def test_credential_absent_blocks_only_that_model(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        output = Path(tmp.name) / "smoke.json"
        env = dict(os.environ)
        env.pop("DASHSCOPE_API_KEY", None)
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch("src.providers.chat", side_effect=_fake_chat):
                run_smoke.run_smoke(confirm=True, output=output)
        with open(output, encoding="utf-8") as handle:
            document = json.load(handle)
        qwen = [m for m in document["models"] if m["model_key"] == "qwen_flagship"][0]
        self.assertEqual(qwen["status"], "SMOKE_BLOCKED_CREDENTIAL")
        # Qwen is also the priority judge for every non-Qwen family, so those
        # candidates cannot be scored while that credential is absent.
        qwen_judged = [m for m in document["models"] if m["model_family"] != "Qwen"]
        self.assertTrue(
            all(m["status"] == "SMOKE_BLOCKED_CREDENTIAL" for m in qwen_judged)
        )
        kimi = [m for m in document["models"] if m["model_key"] == "kimi_flagship"][0]
        credential_judge_errors = [
            row
            for row in kimi["judge_calls"]
            if row.get("error_classification") == "CREDENTIAL"
        ]
        self.assertTrue(credential_judge_errors)

    def test_permanent_http_error_is_classified_and_not_retried(self):
        pool = runner.load_model_pool()
        model = [m for m in pool["models"] if m["key"] == "glm_flagship"][0]
        case = {
            "id": "IF-07",
            "prompt": "x",
        }

        def failing_chat(m, messages, *, at=None, fx_snapshot=None):
            if m["key"] == "glm_flagship":
                raise providers.ProviderError(
                    f"{m['display_name']} rejected the request (HTTP 404): model not found"
                )
            return _fake_chat(m, messages, at=at, fx_snapshot=fx_snapshot)

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        output = Path(tmp.name) / "smoke.json"
        with mock.patch("src.providers.chat", side_effect=failing_chat):
            run_smoke.run_smoke(confirm=True, output=output)
        with open(output, encoding="utf-8") as handle:
            document = json.load(handle)
        glm = [m for m in document["models"] if m["model_key"] == "glm_flagship"][0]
        self.assertEqual(glm["status"], "SMOKE_FAIL")
        self.assertEqual(len(glm["candidate_calls"]), 1)
        self.assertEqual(
            glm["candidate_calls"][0]["error_classification"],
            "MODEL_ACCESS_OR_ENDPOINT",
        )

    def test_classify_provider_error_variants(self):
        self.assertEqual(
            run_smoke.classify_provider_error("HTTP 404: nope"),
            "MODEL_ACCESS_OR_ENDPOINT",
        )
        self.assertEqual(run_smoke.classify_provider_error("HTTP 401: no"), "ACCOUNT_AUTH")
        self.assertEqual(
            run_smoke.classify_provider_error("HTTP 400: bad field"), "REQUEST_CONTRACT"
        )
        self.assertEqual(
            run_smoke.classify_provider_error("insufficient balance"), "BILLING_CREDIT"
        )
        # A billing body returned under a generic status code is still billing.
        self.assertEqual(
            run_smoke.classify_provider_error(
                'HTTP 429: {"error":{"code":"1113","message":'
                '"Insufficient balance or no resource package. Please recharge."}}'
            ),
            "BILLING_CREDIT",
        )
        self.assertEqual(
            run_smoke.classify_provider_error("Missing credentials for X"), "CREDENTIAL"
        )

    def test_permanent_error_attempts_is_one(self):
        self.assertEqual(
            run_smoke._attempts_for("HTTP 401: nope", "ACCOUNT_AUTH"), 1
        )
        self.assertEqual(
            run_smoke._attempts_for("failed after 3 attempt(s): HTTP 503", "PROVIDER_SERVER"),
            3,
        )

    def test_reaudit_reclassifies_billing_body(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "artifact.json"
        artifact = {
            "models": [
                {
                    "model_key": "glm_flagship",
                    "model_id": "glm-5.3",
                    "display_name": "GLM flagship tier",
                    "model_family": "GLM",
                    "provider": "Zhipu",
                    "provider_key": "zhipu_bigmodel",
                    "credential_env": "ZHIPU_API_KEY",
                    "request_config": {"extra_body": {}},
                    "cases_attempted": ["IF-07"],
                    "cases_completed": [],
                    "candidate_calls": [
                        {
                            "case_id": "IF-07",
                            "accepted": False,
                            "error": (
                                "GLM flagship tier failed after 3 attempt(s): HTTP 429: "
                                '{"error":{"code":"1113","message":"Insufficient balance '
                                'or no resource package. Please recharge."}}'
                            ),
                            "error_classification": "RATE_LIMIT",
                            "attempts": 3,
                            "input_tokens": None,
                            "output_tokens": None,
                            "reasoning_tokens": None,
                            "cached_input_tokens": None,
                            "latency_ms": None,
                            "native_cost": None,
                            "native_currency": None,
                            "normalized_cost_cny": None,
                            "cost_error": None,
                        }
                    ],
                    "judge_calls": [],
                    "judge_availability": {},
                    "judges_used": [],
                    "deterministic_checks_run": 0,
                    "deterministic_checks_passed": 0,
                    "deterministic_cases_all_passed": 0,
                    "native_cost_by_currency": None,
                    "candidate_cost_cny": None,
                    "judge_cost_cny": None,
                    "total_cost_cny": None,
                    "token_usage": {},
                    "latency_ms": {},
                    "provider_errors": [
                        {
                            "stage": "candidate",
                            "case_id": "IF-07",
                            "model_key": "glm_flagship",
                            "model_id": "glm-5.3",
                            "provider": "Zhipu",
                            "error": (
                                "HTTP 429: Insufficient balance or no resource package."
                            ),
                            "classification": "RATE_LIMIT",
                            "attempts": 3,
                            "request_config": {},
                        }
                    ],
                    "retry_diagnostics": [],
                    "status": "SMOKE_FAIL",
                    "status_reason": "RATE_LIMIT",
                    "verification": {},
                }
            ],
            "totals": {},
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(artifact, handle)
        document = run_smoke.reaudit_artifact(path)
        model = document["models"][0]
        self.assertEqual(model["status"], "SMOKE_BLOCKED_BILLING")
        self.assertEqual(
            model["candidate_calls"][0]["error_classification"], "BILLING_CREDIT"
        )
        self.assertEqual(
            model["provider_errors"][0]["classification"], "BILLING_CREDIT"
        )

    def test_budget_precall_guard(self):
        budget = run_smoke.Budget(10.0)
        self.assertTrue(budget.can_afford(1.0, label="a"))
        budget.add(9.5, label="a")
        self.assertFalse(budget.can_afford(1.0, label="b"))
        self.assertTrue(budget.stopped)


if __name__ == "__main__":
    unittest.main()
