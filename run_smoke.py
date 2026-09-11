#!/usr/bin/env python3
"""Phase 4D controlled live smoke test for AIProductBench CN V1.

This is deliberately NOT the benchmark runner. It runs exactly three frozen
production cases (`IF-07`, `SA-03`, `AW-04`) across the ten locked candidate
models, with the frozen cross-family judge mapping, so that real provider
behavior (model-ID resolution, request-config acceptance, usage/latency/cost
plumbing, judge execution) can be verified before any full 50-case run.

Safety properties:

* Paid calls require an explicit ``--confirm`` flag.
* A hard smoke-level cost ceiling (100 CNY, native-normalized) is enforced
  before every call; when accumulated spend reaches it, new calls stop and the
  completed diagnostics are preserved.
* Deterministic configuration errors (400/401/403/404/422) are never retried;
  the affected model path is stopped and classified.
* Credentials are read from environment variables only and are never written
  into the artifact, logged, or reported.

This module contains no benchmark methodology. It reuses the frozen evaluator,
judge selection, pricing, and provider plumbing unchanged.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

from src import (
    cases as cases_module,
    config,
    deterministic,
    judge,
    models,
    pricing,
    providers,
    runner,
)

# --------------------------------------------------------------------------
# Frozen smoke scope (Phase 4D)
# --------------------------------------------------------------------------

SMOKE_CASES = ("IF-07", "SA-03", "AW-04")

# Exactly the ten locked V1 candidate slots. Asserted against the registry so a
# registry drift is caught rather than silently changing the smoke scope.
SMOKE_MODEL_KEYS = (
    "qwen_flagship",
    "qwen_value",
    "deepseek_flagship",
    "deepseek_value",
    "kimi_flagship",
    "kimi_value",
    "minimax_flagship",
    "glm_flagship",
    "glm_value",
    "doubao_flagship",
)

SMOKE_COST_CEILING_CNY = 100.0

AUTHORITATIVE_GIT_COMMIT = "2cfe55cf0936e7bb2dae3ea0d9ec363840fdda18"
AUTHORITATIVE_DATASET_MANIFEST = (
    "6b450383e528a5a0a6b813112f96182a3625c04c948839fc551c8ded63da513c"
)

# Status codes that indicate a deterministic configuration problem, not a
# transient failure (mirrors src/providers._FATAL_STATUS).
PERMANENT_STATUS = (400, 401, 403, 404, 422)

PERMANENT_CLASSIFICATIONS = (
    "CREDENTIAL",
    "ACCOUNT_AUTH",
    "BILLING_CREDIT",
    "MODEL_ACCESS_OR_ENDPOINT",
    "REQUEST_CONTRACT",
)

# Billing/credit errors are sometimes returned under a generic status code
# (for example HTTP 429 with an "insufficient balance" body), so the body is
# checked before the status code is mapped.
BILLING_MARKERS = (
    "insufficient balance",
    "insufficient_quota",
    "quota exceeded",
    "insufficient_balance_error",
    "no resource package",
    "recharge",
    "billing",
    "arrears",
    "payment required",
    "余额",
    "欠费",
    "充值",
)


# --------------------------------------------------------------------------
# Budget control
# --------------------------------------------------------------------------


class Budget:
    """Native-normalized CNY smoke budget. Never fabricates a missing cost."""

    def __init__(self, ceiling_cny: float):
        self.ceiling_cny = ceiling_cny
        self.spent_cny = 0.0
        self.stopped = False
        self.stop_reason: str | None = None
        self.unpriced_calls = 0

    def add(self, normalized_cost_cny, *, label: str) -> None:
        if normalized_cost_cny is None:
            self.unpriced_calls += 1
            return
        self.spent_cny = round(self.spent_cny + float(normalized_cost_cny), 8)
        if self.spent_cny >= self.ceiling_cny:
            self.stopped = True
            self.stop_reason = (
                f"cost ceiling reached after {label}: "
                f"{self.spent_cny:.6f} CNY >= {self.ceiling_cny:.2f} CNY"
            )

    def remaining(self) -> float:
        return round(self.ceiling_cny - self.spent_cny, 8)

    def can_afford(self, estimate_cny, *, label: str) -> bool:
        if self.stopped:
            return False
        if estimate_cny is None:
            return True  # unknown estimate; rely on post-call accumulation
        if self.spent_cny + float(estimate_cny) > self.ceiling_cny:
            self.stopped = True
            self.stop_reason = (
                f"projected cost ceiling reached before {label}: "
                f"{self.spent_cny:.6f} + {float(estimate_cny):.6f} > "
                f"{self.ceiling_cny:.2f} CNY"
            )
            return False
        return True


def _estimate_call_cny(model: dict, messages: list[dict], fx_snapshot) -> float | None:
    """Conservative pre-call estimate: full max_output_tokens budget."""
    input_estimate = sum(max(1, len(m["content"]) // 4) for m in messages) + 256
    output_estimate = int(model.get("max_output_tokens") or 2048)
    priced = pricing.price_call(
        model,
        input_estimate,
        output_estimate,
        at=dt.datetime.now(dt.timezone.utc),
        fx_snapshot=fx_snapshot,
    )
    return priced.get("normalized_cost_cny")


# --------------------------------------------------------------------------
# Provider error classification
# --------------------------------------------------------------------------


def classify_provider_error(message: str) -> str:
    text = message or ""
    lowered = text.lower()
    if any(marker in lowered for marker in BILLING_MARKERS):
        return "BILLING_CREDIT"
    match = re.search(r"HTTP (\d{3})", text)
    if match:
        status = int(match.group(1))
        if status in (401, 403):
            return "ACCOUNT_AUTH"
        if status == 404:
            return "MODEL_ACCESS_OR_ENDPOINT"
        if status in (400, 422):
            return "REQUEST_CONTRACT"
        if status == 429:
            return "RATE_LIMIT"
        if 500 <= status < 600:
            return "PROVIDER_SERVER"
    if "Missing credentials" in text:
        return "CREDENTIAL"
    if "Timeout" in text or "Timed out" in text or "ConnectionError" in text:
        return "NETWORK"
    return "UNKNOWN"


def status_for_classification(classification: str) -> str:
    if classification == "CREDENTIAL":
        return "SMOKE_BLOCKED_CREDENTIAL"
    if classification == "BILLING_CREDIT":
        return "SMOKE_BLOCKED_BILLING"
    if classification == "ACCOUNT_AUTH":
        return "SMOKE_BLOCKED_ACCOUNT"
    return "SMOKE_FAIL"


def _attempts_from_error(message: str) -> int | None:
    match = re.search(r"after (\d+) attempt", message or "")
    return int(match.group(1)) if match else None


def _attempts_for(message: str, classification: str) -> int | None:
    """Attempt count recorded for an error.

    Permanent configuration errors are raised immediately, without a retry
    loop, so the attempt count is exactly one.
    """
    attempts = _attempts_from_error(message)
    if attempts is None and classification in PERMANENT_CLASSIFICATIONS:
        return 1
    return attempts


# --------------------------------------------------------------------------
# Aggregate helpers
# --------------------------------------------------------------------------


def _sum_present(values):
    present = [v for v in values if v is not None]
    return round(sum(present), 8) if present else None


def _capture_state(values) -> str:
    """Honest availability summary for an optional usage field."""
    if not values:
        return "no_calls"
    present = [v for v in values if v is not None]
    if len(present) == len(values):
        return "available"
    if not present:
        return "null"
    return "mixed"


# --------------------------------------------------------------------------
# Frozen scope + provenance
# --------------------------------------------------------------------------


def _frozen_scope(pool: dict):
    key_set = {m["key"] for m in models.candidates(pool)}
    if key_set != set(SMOKE_MODEL_KEYS):
        raise SystemExit(
            "Registry drift: candidate slots do not match the locked Phase 4D set. "
            f"expected={sorted(SMOKE_MODEL_KEYS)} got={sorted(key_set)}"
        )
    candidates = [models.by_key(pool, key) for key in SMOKE_MODEL_KEYS]

    case_document = cases_module.load_cases(config.PRODUCTION_CASES_FILE)
    case_index = {c["id"]: c for c in cases_module.all_cases(case_document)}
    missing = [cid for cid in SMOKE_CASES if cid not in case_index]
    if missing:
        raise SystemExit(f"Frozen smoke cases missing from the production dataset: {missing}")
    selected_cases = [case_index[cid] for cid in SMOKE_CASES]

    manifest = cases_module.semantic_manifest_hash(cases_module.all_cases(case_document))
    if manifest != AUTHORITATIVE_DATASET_MANIFEST:
        raise SystemExit(
            "Frozen dataset manifest mismatch: "
            f"expected {AUTHORITATIVE_DATASET_MANIFEST} got {manifest}"
        )
    return candidates, selected_cases, case_document


def _snapshot_ids(pool: dict) -> dict:
    registry = models.build_registry_snapshot(pool)
    pricing_doc = pricing.build_pricing_snapshot(pool["models"])
    fx = config.FX_SNAPSHOT
    return {
        "registry_snapshot_id": registry["snapshot_id"],
        "registry_snapshot_hash": registry["content_sha256"],
        "pricing_snapshot_id": pricing_doc["snapshot_id"],
        "pricing_snapshot_hash": pricing_doc["content_sha256"],
        "fx_snapshot_id": fx.get("snapshot_id"),
        "fx_rate": fx.get("fx_rate"),
        "fx_pair": fx.get("fx_pair"),
        "fx_snapshot_date": fx.get("fx_snapshot_date"),
        "fx_source": fx.get("source"),
    }


def _credential_rows(pool: dict) -> list[dict]:
    rows = []
    seen: set[str] = set()
    for model in pool["models"]:
        env = model["api_key_env"]
        if env in seen:
            continue
        seen.add(env)
        rows.append({"env_var": env, "present": bool(os.environ.get(env, "").strip())})
    return rows


def _credential_present(model: dict) -> bool:
    return bool(os.environ.get(model["api_key_env"], "").strip())


# --------------------------------------------------------------------------
# Smoke execution
# --------------------------------------------------------------------------


def run_smoke(*, confirm: bool, output: Path) -> int:
    pool = runner.load_model_pool()
    candidates, selected_cases, _case_document = _frozen_scope(pool)
    snapshots = _snapshot_ids(pool)
    credential_rows = _credential_rows(pool)

    run_started = dt.datetime.now(dt.timezone.utc)
    run_id = f"smoke-4D-{run_started.strftime('%Y%m%dT%H%M%SZ')}"

    document: dict = {
        "artifact": "AIProductBench CN V1 - Phase 4D controlled live smoke test",
        "run_id": run_id,
        "phase": "4D",
        "synthetic": False,
        "generated_at": run_started.isoformat(timespec="seconds"),
        "scope": {
            "cases": list(SMOKE_CASES),
            "models": list(SMOKE_MODEL_KEYS),
            "max_cases_per_model": 3,
            "note": (
                "Smoke test only. No leaderboard, no Pareto ranking, no full 50-case run."
            ),
        },
        "provenance": {
            "git_commit": AUTHORITATIVE_GIT_COMMIT,
            "git_commit_at_run": runner._git_commit(),
            "dataset_manifest_sha256": AUTHORITATIVE_DATASET_MANIFEST,
            **snapshots,
        },
        "cost_control": {
            "ceiling_cny": SMOKE_COST_CEILING_CNY,
            "basis": "native-normalized CNY (candidate + judge)",
            "enforced_before_every_call": True,
            "retries": {
                "max_retries": config.MAX_RETRIES,
                "backoff_seconds": config.RETRY_BACKOFF_SECONDS,
                "never_retried_status": list(PERMANENT_STATUS),
            },
        },
        "credentials": {
            "values_read_into_artifact": False,
            "availability": credential_rows,
        },
        "models": [],
        "totals": {},
        "compatibility_issues": [],
        "blockers": [],
    }

    print(f"Smoke run ID : {run_id}")
    print(f"Dataset      : {AUTHORITATIVE_DATASET_MANIFEST}")
    print(f"Cases        : {', '.join(SMOKE_CASES)}")
    print(f"Ceiling      : {SMOKE_COST_CEILING_CNY:.2f} CNY (native-normalized)")
    print(
        "Credentials  : "
        + ", ".join(
            f"{r['env_var']}={'yes' if r['present'] else 'no'}" for r in credential_rows
        )
    )
    print()

    if not confirm:
        print("Dry smoke check only (no network calls). Re-run with --confirm to spend.")
        output.parent.mkdir(parents=True, exist_ok=True)
        runner.write_json(document, output)
        print(f"Preflight artifact written to {output}")
        return 2

    budget = Budget(SMOKE_COST_CEILING_CNY)

    for model in candidates:
        entry = _run_model(model, selected_cases, pool, budget)
        document["models"].append(entry)
        _finalize_totals(document, budget)
        output.parent.mkdir(parents=True, exist_ok=True)
        runner.write_json(document, output)
        print(
            f"  {model['display_name']:<26} {entry['status']:<26} "
            f"cases {len(entry['cases_completed'])}/{len(SMOKE_CASES)} "
            f"spend {budget.spent_cny:.4f} CNY"
        )

    _finalize_totals(document, budget)
    runner.write_json(document, output)

    print()
    print(f"Total API calls : {document['totals']['total_api_calls']}")
    print(f"Total spend CNY : {document['totals']['total_cost_cny']}")
    for currency, amount in (document["totals"]["native_cost_by_currency"] or {}).items():
        print(f"Native spend    : {amount:.6f} {currency}")
    if budget.stop_reason:
        print(f"Stopped         : {budget.stop_reason}")
    print(f"Artifact        : {output}")

    failed = [m["model_key"] for m in document["models"] if m["status"] == "SMOKE_FAIL"]
    return 1 if failed else 0


def _run_model(model: dict, cases: list[dict], pool: dict, budget: Budget) -> dict:
    entry: dict = {
        "model_key": model["key"],
        "display_name": model["display_name"],
        "model_id": model.get("model_id"),
        "model_family": model["model_family"],
        "provider": model["provider"],
        "provider_key": model["provider_key"],
        "credential_env": model["api_key_env"],
        "credential_present": _credential_present(model),
        "request_config": providers.effective_request_config(model),
        "thinking_config": model.get("thinking_config"),
        "status": None,
        "status_reason": None,
        "cases_attempted": [],
        "cases_completed": [],
        "candidate_calls": [],
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
        "provider_errors": [],
        "retry_diagnostics": [],
        "verification": {},
    }

    if not entry["credential_present"]:
        entry["status"] = "SMOKE_BLOCKED_CREDENTIAL"
        entry["status_reason"] = f"{model['api_key_env']} is not set in the environment."
        _finalize_model(entry)
        entry["verification"] = _verification(entry)
        return entry

    for case in cases:
        if budget.stopped:
            entry["status_reason"] = budget.stop_reason
            break
        entry["cases_attempted"].append(case["id"])
        messages = [{"role": "user", "content": case["prompt"]}]
        estimate = _estimate_call_cny(model, messages, config.FX_SNAPSHOT)
        if not budget.can_afford(estimate, label=f"candidate {model['key']}/{case['id']}"):
            entry["status_reason"] = budget.stop_reason
            break

        call_record = {
            "case_id": case["id"],
            "stage": "candidate",
            "request_config": providers.effective_request_config(model),
            "accepted": False,
            "error": None,
            "error_classification": None,
            "attempts": None,
            "response_chars": None,
            "latency_ms": None,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "reasoning_tokens": None,
            "cached_input_tokens": None,
            "native_cost": None,
            "native_currency": None,
            "normalized_cost_cny": None,
            "cost_error": None,
            "deterministic": None,
        }

        try:
            response = providers.chat(model, messages, fx_snapshot=config.FX_SNAPSHOT)
        except providers.ProviderError as exc:
            message = str(exc)
            classification = classify_provider_error(message)
            call_record["error"] = message
            call_record["error_classification"] = classification
            call_record["attempts"] = _attempts_for(message, classification)
            entry["candidate_calls"].append(call_record)
            _record_provider_error(entry, model, case["id"], message, classification, "candidate")
            entry["status"] = status_for_classification(classification)
            if classification not in PERMANENT_CLASSIFICATIONS:
                entry["status"] = "SMOKE_FAIL"
            entry["status_reason"] = f"{classification}: {message}"
            break

        call_record.update(
            {
                "accepted": True,
                "attempts": response.get("attempts"),
                "response_chars": len(response.get("text") or ""),
                "latency_ms": response.get("latency_ms"),
                "input_tokens": response.get("input_tokens"),
                "output_tokens": response.get("output_tokens"),
                "total_tokens": response.get("total_tokens"),
                "reasoning_tokens": response.get("reasoning_tokens"),
                "cached_input_tokens": response.get("cached_input_tokens"),
                "native_cost": response.get("native_cost"),
                "native_currency": response.get("native_currency"),
                "normalized_cost_cny": response.get("normalized_cost_cny"),
                "cost_error": response.get("cost_error"),
            }
        )
        budget.add(
            response.get("normalized_cost_cny"),
            label=f"candidate {model['key']}/{case['id']}",
        )

        det = deterministic.evaluate(case, response["text"])
        call_record["deterministic"] = det
        entry["deterministic_checks_run"] += len(det.get("checks") or [])
        entry["deterministic_checks_passed"] += sum(
            1 for check in det.get("checks") or [] if check.get("passed")
        )
        if det.get("all_passed"):
            entry["deterministic_cases_all_passed"] += 1
        entry["cases_completed"].append(case["id"])
        entry["candidate_calls"].append(call_record)

        _run_judges(entry, model, case, response["text"], pool, budget)

    if entry["status"] is None:
        blocked = _judge_blocker_status(entry)
        if blocked is not None:
            entry["status"], entry["status_reason"] = blocked

    if entry["status"] is None:
        entry["status"] = "SMOKE_PASS" if _is_pass(entry) else "SMOKE_FAIL"
        if entry["status"] == "SMOKE_FAIL":
            entry["status_reason"] = "one or more required smoke checks did not complete"

    entry["judges_used"] = sorted(
        {row["judge_key"] for row in entry["judge_calls"] if row.get("scores")}
    )
    _finalize_model(entry)
    entry["verification"] = _verification(entry)
    return entry


def _judge_blocker_status(entry: dict):
    """Map a blocking judge-side condition to a smoke status.

    A candidate whose own calls succeed but whose intended judges are
    credential/account/billing-blocked cannot produce a score; that is a
    blocked run, not an implementation failure.
    """
    for row in entry["judge_calls"]:
        classification = row.get("error_classification")
        if classification == "CREDENTIAL":
            return (
                "SMOKE_BLOCKED_CREDENTIAL",
                f"judge {row.get('judge_key')} credential unavailable: {row.get('error')}",
            )
        if classification == "ACCOUNT_AUTH":
            return (
                "SMOKE_BLOCKED_ACCOUNT",
                f"judge {row.get('judge_key')} account/auth failure: {row.get('error')}",
            )
        if classification == "BILLING_CREDIT":
            return (
                "SMOKE_BLOCKED_BILLING",
                f"judge {row.get('judge_key')} billing/credit failure: {row.get('error')}",
            )
    return None


def _record_provider_error(entry, model, case_id, message, classification, stage):
    attempts = _attempts_for(message, classification)
    entry["provider_errors"].append(
        {
            "stage": stage,
            "case_id": case_id,
            "model_key": model["key"],
            "model_id": model.get("model_id"),
            "provider": model["provider"],
            "error": message,
            "classification": classification,
            "attempts": attempts,
            "request_config": providers.effective_request_config(model),
        }
    )
    entry["retry_diagnostics"].append(
        {
            "stage": stage,
            "case_id": case_id,
            "attempts": attempts,
            "classification": classification,
        }
    )


def _run_judges(entry, model, case, response_text, pool, budget):
    selected = judge.select_judges(
        model, models.judges(pool), models.judge_priority(pool)
    )
    entry["judge_availability"][case["id"]] = [j["key"] for j in selected]
    if not selected:
        entry["judge_calls"].append(
            {
                "case_id": case["id"],
                "judge_key": None,
                "error": "fewer than two cross-family judges are eligible",
                "error_classification": "JUDGE_UNAVAILABLE",
                "scores": None,
            }
        )
        return

    for judge_model in selected:
        base = {
            "case_id": case["id"],
            "judge_key": judge_model["key"],
            "judge_model_id": judge_model.get("model_id"),
            "judge_family": judge_model["model_family"],
            "judge_provider": judge_model["provider"],
            "scores": None,
            "rationale": None,
            "error": None,
            "error_classification": None,
            "attempts": None,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "reasoning_tokens": None,
            "cached_input_tokens": None,
            "native_cost": None,
            "native_currency": None,
            "normalized_cost_cny": None,
            "latency_ms": None,
        }
        if not _credential_present(judge_model):
            base["error"] = f"{judge_model['api_key_env']} is not set in the environment."
            base["error_classification"] = "CREDENTIAL"
            entry["judge_calls"].append(base)
            continue
        if budget.stopped:
            base["error"] = budget.stop_reason
            base["error_classification"] = "COST_CEILING"
            entry["judge_calls"].append(base)
            continue

        messages = judge.build_judge_messages(case, model, judge_model, response_text)
        estimate = _estimate_call_cny(judge_model, messages, config.FX_SNAPSHOT)
        if not budget.can_afford(estimate, label=f"judge {judge_model['key']}/{case['id']}"):
            base["error"] = budget.stop_reason
            base["error_classification"] = "COST_CEILING"
            entry["judge_calls"].append(base)
            continue

        try:
            call = providers.chat(judge_model, messages, fx_snapshot=config.FX_SNAPSHOT)
        except providers.ProviderError as exc:
            message = str(exc)
            classification = classify_provider_error(message)
            base["error"] = message
            base["error_classification"] = classification
            base["attempts"] = _attempts_for(message, classification)
            entry["judge_calls"].append(base)
            _record_provider_error(
                entry, judge_model, case["id"], message, classification, "judge"
            )
            continue

        base.update(
            {
                "attempts": call.get("attempts"),
                "input_tokens": call.get("input_tokens"),
                "output_tokens": call.get("output_tokens"),
                "total_tokens": call.get("total_tokens"),
                "reasoning_tokens": call.get("reasoning_tokens"),
                "cached_input_tokens": call.get("cached_input_tokens"),
                "native_cost": call.get("native_cost"),
                "native_currency": call.get("native_currency"),
                "normalized_cost_cny": call.get("normalized_cost_cny"),
                "latency_ms": call.get("latency_ms"),
            }
        )
        try:
            verdict = judge.parse_judge_output(call["text"])
        except judge.JudgeOutputError as exc:
            base["error"] = f"invalid judge output: {exc}"
            base["error_classification"] = "INVALID_JUDGE_OUTPUT"
        else:
            base.update(
                {
                    "scores": verdict["scores"],
                    "rationale": verdict["rationale"],
                    "mean_score": verdict["mean_score"],
                    "normalized_score": verdict["normalized_score"],
                }
            )
        budget.add(
            call.get("normalized_cost_cny"),
            label=f"judge {judge_model['key']}/{case['id']}",
        )
        entry["judge_calls"].append(base)


def _is_pass(entry: dict) -> bool:
    if len(entry["cases_completed"]) != len(SMOKE_CASES):
        return False
    if entry["deterministic_checks_run"] <= 0:
        return False
    if any(
        call.get("normalized_cost_cny") is None or call.get("cost_error")
        for call in entry["candidate_calls"]
    ):
        return False
    for case_id in entry["cases_completed"]:
        intended = entry["judge_availability"].get(case_id) or []
        valid = {
            row["judge_key"]
            for row in entry["judge_calls"]
            if row["case_id"] == case_id and row.get("scores")
        }
        if len(intended) != 2 or len(valid) != 2:
            return False
    return True


def _derive_status(entry: dict):
    """Recompute a model status from its recorded calls (used by re-audit)."""
    for row in entry["candidate_calls"]:
        classification = row.get("error_classification")
        if classification:
            return (
                status_for_classification(classification),
                f"{classification}: {row.get('error')}",
            )
    blocked = _judge_blocker_status(entry)
    if blocked is not None:
        return blocked
    for row in entry["judge_calls"]:
        if (
            row.get("error")
            and not row.get("scores")
            and row.get("error_classification") not in ("COST_CEILING", "JUDGE_UNAVAILABLE")
        ):
            return (
                "SMOKE_FAIL",
                f"{row.get('error_classification')}: {row.get('error')}",
            )
    if _is_pass(entry):
        return "SMOKE_PASS", None
    return "SMOKE_FAIL", "one or more required smoke checks did not complete"


def _finalize_model(entry: dict) -> None:
    native: dict[str, float] = {}
    for call in entry["candidate_calls"] + entry["judge_calls"]:
        if call.get("native_cost") is not None and call.get("native_currency"):
            currency = call["native_currency"]
            native[currency] = round(native.get(currency, 0.0) + call["native_cost"], 8)
    entry["native_cost_by_currency"] = native or None
    entry["candidate_cost_cny"] = _sum_present(
        [call.get("normalized_cost_cny") for call in entry["candidate_calls"]]
    )
    entry["judge_cost_cny"] = _sum_present(
        [call.get("normalized_cost_cny") for call in entry["judge_calls"]]
    )
    entry["total_cost_cny"] = _sum_present(
        [entry["candidate_cost_cny"], entry["judge_cost_cny"]]
    )
    entry["token_usage"] = {
        "candidate_input": _sum_present(
            [c.get("input_tokens") for c in entry["candidate_calls"]]
        ),
        "candidate_output": _sum_present(
            [c.get("output_tokens") for c in entry["candidate_calls"]]
        ),
        "candidate_reasoning": _sum_present(
            [c.get("reasoning_tokens") for c in entry["candidate_calls"]]
        ),
        "candidate_cached_input": _sum_present(
            [c.get("cached_input_tokens") for c in entry["candidate_calls"]]
        ),
        "judge_input": _sum_present(
            [c.get("input_tokens") for c in entry["judge_calls"]]
        ),
        "judge_output": _sum_present(
            [c.get("output_tokens") for c in entry["judge_calls"]]
        ),
        "judge_reasoning": _sum_present(
            [c.get("reasoning_tokens") for c in entry["judge_calls"]]
        ),
        "judge_cached_input": _sum_present(
            [c.get("cached_input_tokens") for c in entry["judge_calls"]]
        ),
    }
    latencies = [
        c.get("latency_ms")
        for c in entry["candidate_calls"]
        if c.get("latency_ms") is not None
    ]
    entry["latency_ms"] = {
        "samples": len(latencies),
        "min": min(latencies) if latencies else None,
        "max": max(latencies) if latencies else None,
        "mean": round(sum(latencies) / len(latencies), 1) if latencies else None,
    }


def _verification(entry: dict) -> dict:
    calls = entry["candidate_calls"]
    accepted = [c for c in calls if c.get("accepted")]
    all_completed = len(entry["cases_completed"]) == len(SMOKE_CASES)
    intended_judges = {
        judge_key
        for keys in entry["judge_availability"].values()
        for judge_key in (keys or [])
    }
    valid_judge_keys = {
        row["judge_key"] for row in entry["judge_calls"] if row.get("scores")
    }
    thinking_fields = providers.effective_request_config(
        {"key": entry["model_key"], "request_config": entry.get("request_config")}
    ).get("extra_body")
    return {
        "A_request_accepted": bool(accepted) and all_completed,
        "B_provider_model_id_resolves": bool(accepted),
        "C_reasoning_thinking_config_accepted": (
            "verified_accepted"
            if accepted and thinking_fields
            else ("no_explicit_field_sent" if accepted else "not_verified")
        ),
        "D_response_text_returned": bool(accepted),
        "E_input_tokens": _capture_state([c.get("input_tokens") for c in calls]),
        "F_output_tokens": _capture_state([c.get("output_tokens") for c in calls]),
        "G_reasoning_tokens": _capture_state([c.get("reasoning_tokens") for c in calls]),
        "H_cached_input_tokens": _capture_state(
            [c.get("cached_input_tokens") for c in calls]
        ),
        "I_latency_measured": (
            all(c.get("latency_ms") is not None for c in calls) if calls else False
        ),
        "J_native_price_resolved": (
            bool(calls) and all(c.get("native_cost") is not None for c in calls)
        ),
        "K_cny_normalization_resolved": (
            bool(calls) and all(c.get("normalized_cost_cny") is not None for c in calls)
        ),
        "L_deterministic_checks_execute": entry["deterministic_checks_run"] > 0,
        "M_judge_requests_execute": len(entry["judge_calls"]) > 0,
        "N_both_intended_judges_available": (
            len(intended_judges) == 2 and intended_judges <= valid_judge_keys
        ),
        "O_final_case_score_producible": (
            all_completed
            and len(valid_judge_keys) >= 2
            and entry.get("status") == "SMOKE_PASS"
        ),
    }


def _finalize_totals(document: dict, budget: Budget | None = None) -> None:
    candidate_calls = sum(len(m["candidate_calls"]) for m in document["models"])
    judge_calls = sum(len(m["judge_calls"]) for m in document["models"])
    native: dict[str, float] = {}
    for model in document["models"]:
        for currency, amount in (model["native_cost_by_currency"] or {}).items():
            native[currency] = round(native.get(currency, 0.0) + amount, 8)
    candidate_cny = _sum_present([m["candidate_cost_cny"] for m in document["models"]])
    judge_cny = _sum_present([m["judge_cost_cny"] for m in document["models"]])
    previous = document.get("totals") or {}
    document["totals"] = {
        "candidate_calls": candidate_calls,
        "judge_calls": judge_calls,
        "total_api_calls": candidate_calls + judge_calls,
        "candidate_cost_cny": candidate_cny,
        "judge_cost_cny": judge_cny,
        "total_cost_cny": _sum_present([candidate_cny, judge_cny]),
        "native_cost_by_currency": native or None,
        "budget_spent_cny": budget.spent_cny if budget else previous.get("budget_spent_cny"),
        "budget_remaining_cny": (
            budget.remaining() if budget else previous.get("budget_remaining_cny")
        ),
        "budget_stopped": budget.stopped if budget else previous.get("budget_stopped"),
        "budget_stop_reason": (
            budget.stop_reason if budget else previous.get("budget_stop_reason")
        ),
        "unpriced_calls": (
            budget.unpriced_calls if budget else previous.get("unpriced_calls")
        ),
    }
    document["compatibility_issues"] = [
        {
            "model_key": model["model_key"],
            "model_id": model["model_id"],
            "provider": model["provider"],
            "stage": error["stage"],
            "classification": error["classification"],
            "error": error["error"],
        }
        for model in document["models"]
        for error in model["provider_errors"]
    ]
    document["blockers"] = [
        {
            "model_key": model["model_key"],
            "model_id": model["model_id"],
            "status": model["status"],
            "reason": model["status_reason"],
        }
        for model in document["models"]
        if model["status"] not in (None, "SMOKE_PASS")
    ]


def reaudit_artifact(path: Path) -> dict:
    """Re-derive error classification and model status from a saved artifact.

    Provider/account/billing failures are sometimes returned under a generic
    HTTP status (for example HTTP 429 carrying "insufficient balance"). No paid
    call is repeated: only the recorded error strings are re-classified, and
    the classifier bug is corrected transparently.
    """
    path = Path(path)
    with open(path, encoding="utf-8") as handle:
        document = json.load(handle)

    for model in document["models"]:
        for row in model["candidate_calls"]:
            if row.get("error"):
                classification = classify_provider_error(row["error"])
                row["error_classification"] = classification
                row["attempts"] = _attempts_for(row["error"], classification)
        for row in model["judge_calls"]:
            if row.get("error") and row.get("error_classification") not in (
                "COST_CEILING",
                "JUDGE_UNAVAILABLE",
            ):
                classification = classify_provider_error(row["error"])
                row["error_classification"] = classification
                row["attempts"] = _attempts_for(row["error"], classification)
        for error in model["provider_errors"]:
            classification = classify_provider_error(error["error"])
            error["classification"] = classification
            error["attempts"] = _attempts_for(error["error"], classification)
        model["retry_diagnostics"] = [
            {
                "stage": error["stage"],
                "case_id": error["case_id"],
                "judge_key": error.get("judge_key"),
                "attempts": error["attempts"],
                "classification": error["classification"],
            }
            for error in model["provider_errors"]
        ]
        model["status"], model["status_reason"] = _derive_status(model)
        model["judges_used"] = sorted(
            {row["judge_key"] for row in model["judge_calls"] if row.get("scores")}
        )
        model["verification"] = _verification(model)

    _finalize_totals(document)
    document["reaudit"] = {
        "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "note": (
            "Error classifications and model statuses re-derived from recorded "
            "provider error strings; no paid call was repeated. Billing bodies "
            "returned under a generic HTTP status are classified as billing issues."
        ),
    }
    runner.write_json(document, path)
    return document


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run_smoke.py",
        description=(
            "Phase 4D controlled live smoke test: 3 frozen cases, 10 locked models, "
            f"{SMOKE_COST_CEILING_CNY:.0f} CNY hard ceiling."
        ),
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="required to make real paid provider calls",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="artifact path (default: results/smoke_4D_<timestamp>.json)",
    )
    parser.add_argument(
        "--reaudit",
        type=Path,
        default=None,
        help=(
            "re-classify an existing smoke artifact from its recorded provider "
            "errors and rewrite it (no network calls)"
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.reaudit:
        document = reaudit_artifact(args.reaudit)
        print(f"Re-audited {args.reaudit}")
        for model in document["models"]:
            print(
                f"  {model['model_key']:<20} {model['status']:<26} "
                f"{model['status_reason'] or ''}"
            )
        return 0
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = args.output or (config.RESULTS_DIR / f"smoke_4D_{stamp}.json")
    return run_smoke(confirm=args.confirm, output=output)


if __name__ == "__main__":
    sys.exit(main())
