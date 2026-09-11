#!/usr/bin/env python3
"""Phase 5 — official AIProductBench CN V1 full benchmark run.

This is the *official* 50-case paid run. It adds execution concerns (bounded
concurrency, restart-safe checkpointing, a hard CNY ceiling, and the official
artifact set) on top of the frozen evaluation stack. It contains **no benchmark
methodology of its own**: candidate records, judge selection, judge parsing,
deterministic evaluation, pricing/FX resolution, ranking, Pareto analysis, and
incomplete-model suppression are all delegated unchanged to ``src/``.

Design:

* Candidate calls and judge calls are separate phases with separate accounting.
* Every completed paid call is appended to a JSONL checkpoint immediately, so an
  interrupted run resumes without regenerating a single completed call.
* A hard ceiling (150 CNY native-normalized) is checked against accumulated
  spend *and* a projection over the remaining work before each new paid call.
* Credentials are read from environment variables only and are never printed,
  stored, or serialized.
* Hidden reasoning / chain-of-thought is never stored: only token counts and
  response structure are recorded.

Usage::

    python3 run_official.py --preflight            # offline checks only
    python3 run_official.py --self-test            # offline full-pipeline rehearsal
    python3 run_official.py --confirm              # the official paid run
    python3 run_official.py --confirm --resume     # resume an interrupted run
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import platform
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

import run_smoke
from src import (
    analytics,
    cases as cases_module,
    config,
    deterministic,
    judge,
    leaderboard as leaderboard_module,
    models,
    pricing,
    providers,
    runner,
)

PHASE = "5"
HARD_CEILING_CNY = 150.0
GLOBAL_CONCURRENCY = 6
PER_PROVIDER_CONCURRENCY = 2

# Provider account-level concurrency limits observed in the Phase 4D/5 live
# probes. Moonshot enforces an organisation-wide concurrency of 1 for the Kimi
# flagship slot, so dispatching two simultaneous Kimi calls produces HTTP 429
# without ever reaching the model. This is an execution limit, not a benchmark
# semantic: it changes how fast calls are issued, never what is asked or scored.
PER_PROVIDER_CONCURRENCY_OVERRIDES = {"moonshot": 1}
# After this many rate-limit failures in one phase, a provider is throttled back
# to a single in-flight call for the rest of that phase.
RATE_LIMIT_DEGRADE_THRESHOLD = 3

# Live observation (Phase 5, qwen_flagship/SA-07): 3315 output tokens were billed
# against a configured 2048-token cap, because thinking tokens are billed beyond
# `max_tokens`. The reserve-before-dispatch bound therefore cannot rely on the
# configured cap alone. D-053 sets the frozen envelope to 16384; the reservation
# bound takes twice that so a single call can never silently breach the ceiling.
OUTPUT_TOKEN_BOUND_MULTIPLIER = 2

# The frozen config sets a 120s client read timeout. Live Phase 5 evidence shows
# thinking-heavy production cases legitimately need longer: four successful
# calls exceeded 60s, the slowest succeeded at 114.6s, and three further calls
# failed on read timeout. The timeout is a client-side execution parameter — the
# same prompt, model, and parameters are sent either way — so it is raised at
# runtime rather than by editing the frozen configuration file. The override is
# recorded in the run manifest and never changes what is asked or scored.
OFFICIAL_READ_TIMEOUT_SECONDS = 600.0

# Transient failure classes get exactly one deferred re-queue pass after the
# main pass. Deterministic failures (auth, billing, model access, request
# contract) are never re-queued.
TRANSIENT_CLASSES = {"RATE_LIMIT", "PROVIDER_SERVER", "NETWORK", "UNKNOWN"}

EXPECTED_DATASET_MANIFEST = (
    "6b450383e528a5a0a6b813112f96182a3625c04c948839fc551c8ded63da513c"
)
# The run is pinned by frozen hashes (dataset manifest, registry, pricing, FX)
# rather than by a hard-coded commit id: once this harness is itself tracked, a
# literal commit constant can never match the commit that contains it. The
# commit actually used is recorded in the run manifest.
# Paths that must never change. These carry the frozen evaluation semantics:
# case content, the approved matrix, the semantic freeze manifest, the frozen
# methodology, and the pricing/FX snapshots.
FROZEN_SEMANTIC_PATHS = {
    "data/cases_v1.json",
    "docs/CASE_MATRIX_V1.md",
    "docs/DATASET_FREEZE_V1.md",
    "docs/METHODOLOGY_V1.md",
    "data/pricing_snapshot_v1.json",
    "data/fx_snapshot_v1.json",
}
# The D-053/D-054 runtime-envelope revision, the D-054 aggregation-recovery
# patch, and Phase 5 harness tooling. These may legitimately be modified or
# added while the runtime/config work is still uncommitted.
D053_REVISION_PATHS = {
    "data/models_v1.json",
    "data/model_registry_snapshot_v1.json",
    "src/config.py",
    "src/models.py",
    "src/providers.py",
    "src/judge.py",
    "src/runner.py",
    "docs/DECISIONS.md",
    "docs/HANDOFF.md",
    "tests/test_phase4bc_config.py",
    "run_official.py",
    "tests/test_official_harness.py",
    "tests/test_judge_failure_aggregation.py",
}
EXPECTED_REGISTRY_ID = "v1-registry-2026-09-11.3"
EXPECTED_REGISTRY_HASH = (
    "259b02adb05f73ab2d800c8f41d9b2608b8eddb17ae97e9d3f31ecff79409eab"
)
EXPECTED_PRICING_ID = "v1-pricing-2026-09-11.1"
EXPECTED_PRICING_HASH = (
    "9f7af42243e5e0b78b1776934de5483f0e3e650765a19dd929e78af10aa15c42"
)
CREDENTIAL_ENV_VARS = (
    "DASHSCOPE_API_KEY",
    "DEEPSEEK_API_KEY",
    "MOONSHOT_API_KEY",
    "MINIMAX_API_KEY",
    "ZHIPU_API_KEY",
    "ARK_API_KEY",
)

_WRITE_LOCK = threading.Lock()


def _iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _git_status() -> str:
    """Best-effort local git status (no network)."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(config.PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
        # Keep the leading status column of the first line intact.
        return result.stdout.rstrip("\n")
    except Exception:  # pragma: no cover - defensive
        return "<unavailable>"


def _write_json(path: Path, payload) -> Path:
    """Atomically write a JSON artifact."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(temporary, path)
    return path


def _append_jsonl(path: Path, record: dict) -> None:
    """Append one completed unit to a checkpoint file and flush it to disk."""
    with _WRITE_LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())


def _load_jsonl(path: Path) -> list[dict]:
    if not Path(path).exists():
        return []
    records = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                # A partially written trailing line can only come from a hard
                # interruption mid-append; the unit is simply retried.
                continue
    return records


# --------------------------------------------------------------------------
# Preflight
# --------------------------------------------------------------------------


def preflight(pool: dict, case_document: dict, *, require_clean_git: bool = True) -> dict:
    """Offline readiness checks. Makes zero network calls."""
    case_list = cases_module.all_cases(case_document)
    checks: list[dict] = []

    def add(name, ok, detail):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    status = _git_status()
    # git --porcelain emits a fixed "XY path" layout; keep the leading status
    # column so the path slice is correct.
    status_lines = [line for line in status.splitlines() if line.strip()]
    touched = []
    for line in status_lines:
        path = line.rstrip()[3:].strip() if len(line) > 3 else ""
        if " -> " in path:  # renames report "old -> new"
            path = path.split(" -> ")[-1].strip()
        touched.append(path)
    frozen_touched = sorted(path for path in touched if path in FROZEN_SEMANTIC_PATHS)
    unexpected = sorted(
        path
        for path in touched
        if path not in FROZEN_SEMANTIC_PATHS and path not in D053_REVISION_PATHS
    )
    add(
        "frozen_semantics_unmodified",
        (not frozen_touched and not unexpected) if require_clean_git else True,
        (
            "case/matrix/freeze/methodology/pricing/FX inputs untouched"
            if not frozen_touched and not unexpected
            else f"frozen inputs touched: {frozen_touched}; unexpected: {unexpected}"
        ),
    )

    commit = runner._git_commit()
    add("git_commit", bool(commit), commit or "unknown")
    add("head_is_recorded", bool(commit), commit or "unknown")

    manifest = cases_module.semantic_manifest_hash(case_list)
    add("dataset_manifest", manifest == EXPECTED_DATASET_MANIFEST, manifest)

    case_ids = [case["id"] for case in case_list]
    add("case_count", len(case_list) == 50, f"{len(case_list)} cases")
    add("case_ids_unique", len(set(case_ids)) == len(case_ids), f"{len(set(case_ids))} unique")
    add("production_status", case_document.get("production_status") == "complete",
        str(case_document.get("production_status")))

    registry = models.build_registry_snapshot(pool)
    add("registry_snapshot", registry["snapshot_id"] == EXPECTED_REGISTRY_ID,
        registry["snapshot_id"])
    add("registry_hash", registry["content_sha256"] == EXPECTED_REGISTRY_HASH,
        registry["content_sha256"])

    pricing_doc = pricing.build_pricing_snapshot(pool["models"])
    add("pricing_snapshot", pricing_doc["snapshot_id"] == EXPECTED_PRICING_ID,
        pricing_doc["snapshot_id"])
    add("pricing_hash", pricing_doc["content_sha256"] == EXPECTED_PRICING_HASH,
        pricing_doc["content_sha256"])

    fx_id = config.FX_SNAPSHOT.get("snapshot_id")
    add("fx_snapshot", fx_id == "ecb-2026-09-10-usd-cny", str(fx_id))

    missing = [name for name in CREDENTIAL_ENV_VARS if not os.environ.get(name, "").strip()]
    add("credentials_present", not missing,
        "all six environment variables present" if not missing else f"missing: {missing}")

    validation = runner.validate_all(case_document, pool)
    add("schema_validation", not validation["errors"],
        f"{len(validation['errors'])} error(s)")

    candidates = models.candidates(pool)
    add("candidate_count", len(candidates) == 10, f"{len(candidates)} candidates")

    judge_plan = {}
    for model in candidates:
        selected = judge.select_judges(model, models.judges(pool), models.judge_priority(pool))
        judge_plan[model["key"]] = [item["key"] for item in selected]
        add(f"judges::{model['key']}", len(selected) == 2,
            ",".join(item["key"] for item in selected) or "none")

    return {
        "checked_at": _iso(),
        "git_commit": commit,
        "git_status_porcelain": status_lines,
        "dataset_manifest_sha256": manifest,
        "registry_snapshot_id": registry["snapshot_id"],
        "registry_snapshot_hash": registry["content_sha256"],
        "pricing_snapshot_id": pricing_doc["snapshot_id"],
        "pricing_snapshot_hash": pricing_doc["content_sha256"],
        "fx_snapshot_id": fx_id,
        "fx_rate": config.FX_SNAPSHOT.get("fx_rate"),
        "credential_availability": [
            {"env_var": name, "present": bool(os.environ.get(name, "").strip())}
            for name in CREDENTIAL_ENV_VARS
        ],
        "judge_plan": judge_plan,
        "checks": checks,
        "ok": all(check["ok"] for check in checks),
    }


# --------------------------------------------------------------------------
# Budget
# --------------------------------------------------------------------------


class Budget:
    """Thread-safe hard ceiling on native-normalized CNY spend."""

    def __init__(self, ceiling_cny: float):
        self.ceiling_cny = float(ceiling_cny)
        self.spent_cny = 0.0
        self.reserved_cny = 0.0
        self.paid_calls = 0
        self.stopped = False
        self.stop_reason: str | None = None
        self.last_refusal: str | None = None
        self.bound_broken = False
        self._lock = threading.Lock()

    def add(self, cost_cny) -> None:
        with self._lock:
            self.paid_calls += 1
            if cost_cny is not None:
                self.spent_cny = round(self.spent_cny + float(cost_cny), 8)
            if self.spent_cny >= self.ceiling_cny:
                self.stopped = True
                self.stop_reason = (
                    f"hard ceiling reached: spent {self.spent_cny:.4f} >= "
                    f"{self.ceiling_cny:.2f} CNY"
                )

    def remaining(self) -> float:
        return round(self.ceiling_cny - self.spent_cny, 8)

    def seed(self, spent_cny) -> None:
        """Carry accumulated spend from an earlier (interrupted) session."""
        with self._lock:
            if spent_cny:
                self.spent_cny = round(self.spent_cny + float(spent_cny), 8)

    def reserve(self, estimate_cny, *, label: str) -> bool:
        """Reserve the upper-bound cost of a call before it is dispatched.

        Every in-flight call holds a reservation, so ``spent + reserved`` is a
        genuine upper bound on the final spend. The ceiling is therefore a hard
        limit rather than a post-hoc observation.
        """
        estimate = float(estimate_cny or 0.0)
        with self._lock:
            if self.stopped:
                return False
            if self.spent_cny + self.reserved_cny + estimate > self.ceiling_cny:
                # Refuse this call without latching a global stop: a single
                # expensive unit must not starve cheaper work that still fits.
                # The ceiling remains hard because no call is ever dispatched
                # without a reservation that fits.
                self.last_refusal = (
                    f"ceiling would be exceeded before {label}: spent "
                    f"{self.spent_cny:.6f} + reserved {self.reserved_cny:.6f} + "
                    f"estimate {estimate:.6f} > {self.ceiling_cny:.2f} CNY"
                )
                return False
            self.reserved_cny = round(self.reserved_cny + estimate, 8)
            return True

    def release(self, estimate_cny, actual_cny) -> None:
        """Release a reservation and record the observed cost."""
        estimate = float(estimate_cny or 0.0)
        with self._lock:
            self.reserved_cny = round(max(0.0, self.reserved_cny - estimate), 8)
            self.paid_calls += 1
            if actual_cny is not None:
                self.spent_cny = round(self.spent_cny + float(actual_cny), 8)
                if estimate and float(actual_cny) > estimate + 1e-9:
                    # The upper bound was broken; stop rather than drift past
                    # the ceiling on a bound we can no longer trust.
                    self.bound_broken = True
                    self.stopped = True
                    self.stop_reason = (
                        f"observed cost {float(actual_cny):.6f} exceeded the "
                        f"per-call upper bound {estimate:.6f}"
                    )
            if self.spent_cny >= self.ceiling_cny:
                self.stopped = True
                self.stop_reason = (
                    f"hard ceiling reached: spent {self.spent_cny:.4f} >= "
                    f"{self.ceiling_cny:.2f} CNY"
                )

    def can_afford(self, estimate_cny, *, label: str) -> bool:
        with self._lock:
            if self.stopped:
                return False
            if estimate_cny is None:
                return True
            if self.spent_cny + self.reserved_cny + float(estimate_cny) > self.ceiling_cny:
                self.last_refusal = (
                    f"ceiling would be exceeded before {label}: "
                    f"{self.spent_cny:.6f} + {self.reserved_cny:.6f} + "
                    f"{float(estimate_cny):.6f} > {self.ceiling_cny:.2f} CNY"
                )
                return False
            return True

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "ceiling_cny": self.ceiling_cny,
                "spent_cny": self.spent_cny,
                "reserved_cny": self.reserved_cny,
                "remaining_cny": self.remaining(),
                "paid_calls": self.paid_calls,
                "stopped": self.stopped,
                "stop_reason": self.stop_reason,
                "last_refusal": self.last_refusal,
                "bound_broken": self.bound_broken,
            }


def _upper_bound_call_cny(
    model: dict, input_chars: int, *, synthetic: bool, role: str = "candidate"
):
    """Upper-bound cost of one call, used to reserve budget before dispatch.

    Input tokens are upper-bounded by the character count (one token per
    character is at or above the true ratio for Chinese and comfortably above it
    for English). Output tokens are bounded by a multiple of the registry
    envelope rather than the cap itself, because providers bill
    reasoning/thinking tokens beyond ``max_tokens``. The result is never
    recorded as observed usage.
    """
    input_tokens = max(1, int(input_chars))
    configured = int(
        (providers.effective_request_config(model, role=role).get("max_output_tokens"))
        or 2048
    )
    output_tokens = OUTPUT_TOKEN_BOUND_MULTIPLIER * max(configured, 1)
    try:
        priced = pricing.price_call(
            model,
            input_tokens,
            output_tokens,
            at=dt.datetime.now(dt.timezone.utc),
            fx_snapshot=config.SYNTHETIC_FX_SNAPSHOT if synthetic else config.FX_SNAPSHOT,
            synthetic=synthetic,
        )
    except Exception:
        return None
    return priced.get("normalized_cost_cny")


# --------------------------------------------------------------------------
# Unit execution
# --------------------------------------------------------------------------


def _candidate_record(
    case: dict, model: dict, response: dict, pool: dict, *, synthetic: bool
) -> dict:
    """Candidate record in exactly the frozen runner shape (minus judgements)."""
    record = runner._base_record(case, model, synthetic)
    record.update(
        {
            "model_id": response.get("model_id"),
            "response_text": response["text"],
            "latency_ms": response["latency_ms"],
            "input_tokens": response["input_tokens"],
            "output_tokens": response["output_tokens"],
            "total_tokens": response["total_tokens"],
            "reasoning_tokens": response.get("reasoning_tokens"),
            "cached_input_tokens": response.get("cached_input_tokens"),
            "native_cost": response["native_cost"],
            "native_currency": response["native_currency"],
            "normalized_cost_cny": response["normalized_cost_cny"],
            "normalization_method": response["normalization_method"],
            "cost_basis": response["basis"],
            "cost_error": response["cost_error"],
            "called_at": response["called_at"],
            "synthetic": response["synthetic"],
            "attempts": response.get("attempts"),
            "finish_reason": response.get("finish_reason"),
            "deterministic": deterministic.evaluate(case, response["text"]),
        }
    )
    selected = judge.select_judges(
        model, models.judges(pool), models.judge_priority(pool)
    )
    record["judges_attempted"] = [item["key"] for item in selected]
    if not selected:
        record["judge_unavailable_reason"] = (
            "fewer than two cross-family judges are eligible for this candidate"
        )
    return record


def run_candidate_unit(*, case, model, pool, synthetic: bool) -> tuple[dict, dict]:
    """One candidate call. Returns (record_or_none, outcome)."""
    messages = [{"role": "user", "content": case["prompt"]}]
    started = time.perf_counter()
    try:
        if synthetic:
            response = providers.synthetic_call(
                model, messages, seed=f"{case['id']}|{model['key']}",
                fx_snapshot=config.SYNTHETIC_FX_SNAPSHOT,
            )
        else:
            response = providers.chat(model, messages, fx_snapshot=config.FX_SNAPSHOT)
    except providers.ProviderError as exc:
        message = str(exc)
        classification = run_smoke.classify_provider_error(message)
        record = runner._base_record(case, model, synthetic)
        record["error"] = message
        record["error_classification"] = classification
        record["attempts"] = run_smoke._attempts_for(message, classification)
        return record, {
            "ok": False,
            "classification": classification,
            "cost_cny": None,
            "error": message,
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
        }

    record = _candidate_record(case, model, response, pool, synthetic=synthetic)
    return record, {
        "ok": True,
        "classification": None,
        "cost_cny": response.get("normalized_cost_cny"),
        "error": None,
        "elapsed_ms": response.get("latency_ms"),
        "attempts": response.get("attempts"),
    }


def run_judge_unit(*, case, candidate_model, judge_model, response_text, synthetic: bool):
    """One judge call, delegated to the frozen judge implementation."""
    verdict = judge._evaluate_one(
        case,
        candidate_model,
        judge_model,
        response_text,
        dry_run=synthetic,
        fx_snapshot=config.SYNTHETIC_FX_SNAPSHOT if synthetic else config.FX_SNAPSHOT,
    )
    ok = verdict.get("error") is None and verdict.get("scores") is not None
    classification = None
    if not ok:
        classification = (
            run_smoke.classify_provider_error(verdict["error"])
            if verdict.get("error", "").startswith(("provider:", "Missing credentials"))
            else "INVALID_JUDGE_OUTPUT"
            if verdict.get("error")
            else "UNKNOWN"
        )
    return verdict, {
        "ok": ok,
        "classification": classification,
        "cost_cny": verdict.get("normalized_cost_cny"),
        "error": verdict.get("error"),
        "elapsed_ms": verdict.get("latency_ms"),
    }


# --------------------------------------------------------------------------
# Concurrency driver
# --------------------------------------------------------------------------


def execute_units(
    units: list[dict],
    *,
    worker,
    budget: Budget,
    checkpoint_path: Path,
    label: str,
    synthetic: bool,
    max_workers: int = GLOBAL_CONCURRENCY,
    per_provider: int = PER_PROVIDER_CONCURRENCY,
    progress_every: int = 25,
) -> dict:
    """Run paid units with bounded concurrency, checkpointing, and a hard ceiling.

    Each unit is a dict with at least: key, model_key, provider_key, estimate_cny.
    The worker is called with the unit and must return (payload, outcome).
    """
    previous = _load_jsonl(checkpoint_path)
    results: dict[str, dict] = {}
    completed_keys: set[str] = set()
    for record in previous:
        key = record.get("key")
        if not key:
            continue
        outcome = record.get("outcome") or {}
        results[key] = record.get("payload")
        if outcome.get("ok") or outcome.get("classification") not in TRANSIENT_CLASSES:
            completed_keys.add(key)
        else:
            # Transient failures (rate limit, provider 5xx, network) are retried
            # on resume; deterministic failures are never retried.
            completed_keys.discard(key)
            results.pop(key, None)
    pending = [unit for unit in units if unit["key"] not in completed_keys]
    already = len(units) - len(pending)

    stats = {
        "stage": label,
        "units_total": len(units),
        "units_already_checkpointed": already,
        "units_completed": 0,
        "units_failed": 0,
        "units_skipped_ceiling": 0,
        "paid_calls": 0,
        "attempts_total": 0,
        "retries": 0,
        "cost_cny": 0.0,
        "spent_before": budget.spent_cny,
        "by_classification": {},
    }

    provider_in_flight: dict[str, int] = {}
    provider_limit = {
        unit["provider_key"]: PER_PROVIDER_CONCURRENCY_OVERRIDES.get(
            unit["provider_key"], per_provider
        )
        for unit in units
    }
    rate_limit_hits: dict[str, int] = {}
    lock = threading.Lock()
    next_progress = progress_every
    transient_keys: list[str] = []

    def handle(unit, payload, outcome):
        _append_jsonl(
            checkpoint_path,
            {
                "key": unit["key"],
                "stage": label,
                "model_key": unit["model_key"],
                "provider_key": unit["provider_key"],
                "case_id": unit["case_id"],
                "judge_key": unit.get("judge_key"),
                "recorded_at": _iso(),
                "payload": payload,
                "outcome": outcome,
            },
        )
        with lock:
            results[unit["key"]] = payload
            stats["paid_calls"] += 1
            stats["attempts_total"] += int(outcome.get("attempts") or 1)
            if outcome.get("ok"):
                stats["units_completed"] += 1
            else:
                stats["units_failed"] += 1
                classification = outcome.get("classification") or "UNKNOWN"
                stats["by_classification"][classification] = (
                    stats["by_classification"].get(classification, 0) + 1
                )
                if classification in TRANSIENT_CLASSES:
                    transient_keys.append(unit["key"])
                if classification == "RATE_LIMIT":
                    provider = unit["provider_key"]
                    rate_limit_hits[provider] = rate_limit_hits.get(provider, 0) + 1
                    if (
                        rate_limit_hits[provider] >= RATE_LIMIT_DEGRADE_THRESHOLD
                        and provider_limit.get(provider, per_provider) > 1
                    ):
                        provider_limit[provider] = 1
                        print(
                            f"  [{label}] provider '{provider}' throttled to 1 "
                            f"in-flight call after {rate_limit_hits[provider]} "
                            "rate-limit responses",
                            flush=True,
                        )
            if outcome.get("cost_cny") is not None:
                stats["cost_cny"] = round(
                    stats["cost_cny"] + float(outcome["cost_cny"]), 8
                )
        budget.release(unit.get("estimate_cny"), outcome.get("cost_cny"))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        in_flight = {}
        while pending or in_flight:
            # Greedy dispatch, respecting the global and per-provider caps.
            index = 0
            while index < len(pending) and len(in_flight) < max_workers:
                unit = pending[index]
                provider = unit["provider_key"]
                if provider_in_flight.get(provider, 0) >= provider_limit.get(
                    provider, per_provider
                ):
                    index += 1
                    continue
                if budget.stopped:
                    break
                if not budget.reserve(unit.get("estimate_cny"), label=unit["key"]):
                    # One unit that cannot fit under the ceiling must not block
                    # cheaper units queued behind it. Skip it and keep scanning;
                    # any unit that is skipped this way stays pending and is
                    # reported as ceiling-skipped when nothing can be dispatched.
                    index += 1
                    continue
                pending.pop(index)
                provider_in_flight[provider] = provider_in_flight.get(provider, 0) + 1
                in_flight[executor.submit(worker, unit)] = unit

            if not in_flight:
                if pending:
                    stats["units_skipped_ceiling"] += len(pending)
                    for unit in pending:
                        results[unit["key"]] = None
                    pending = []
                    if not budget.stopped:
                        budget.stopped = True
                        budget.stop_reason = (
                            budget.last_refusal
                            or "no remaining unit fits under the hard ceiling"
                        )
                break

            done, _ = wait(list(in_flight), return_when=FIRST_COMPLETED)
            for future in done:
                unit = in_flight.pop(future)
                provider_in_flight[unit["provider_key"]] -= 1
                try:
                    payload, outcome = future.result()
                except Exception as exc:  # defensive: a worker crash must not lose the run
                    payload, outcome = None, {
                        "ok": False,
                        "classification": "WORKER_ERROR",
                        "cost_cny": None,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                handle(unit, payload, outcome)
                if stats["paid_calls"] >= next_progress:
                    next_progress += progress_every
                    print(
                        f"  [{label}] {stats['paid_calls']} calls | "
                        f"ok={stats['units_completed']} fail={stats['units_failed']} "
                        f"spent={budget.spent_cny:.4f}/{budget.ceiling_cny:.2f} CNY",
                        flush=True,
                    )

    stats["results"] = results
    stats["transient_keys"] = transient_keys
    stats["spent_after"] = budget.spent_cny
    stats["budget"] = budget.snapshot()
    stats["retries"] = max(0, stats["attempts_total"] - stats["paid_calls"])
    return stats


# --------------------------------------------------------------------------
# Phase planning
# --------------------------------------------------------------------------


def build_candidate_units(pool: dict, case_list: list[dict], *, synthetic: bool) -> list[dict]:
    units = []
    for model in models.candidates(pool):
        for case in case_list:
            units.append(
                {
                    "key": f"candidate|{model['key']}|{case['id']}",
                    "stage": "candidate",
                    "model_key": model["key"],
                    "provider_key": model["provider_key"],
                    "case_id": case["id"],
                    "judge_key": None,
                    "model": model,
                    "case": case,
                    "estimate_cny": _upper_bound_call_cny(
                        model, len(case["prompt"]), synthetic=synthetic
                    ),
                }
            )
    return units


def build_judge_units(
    pool: dict, case_index: dict, candidate_records: list[dict], *, synthetic: bool
) -> list[dict]:
    by_key = {model["key"]: model for model in pool["models"]}
    units = []
    for record in candidate_records:
        if not record or record.get("error") or not record.get("response_text"):
            continue
        case = case_index[record["case_id"]]
        for judge_key in record.get("judges_attempted") or []:
            judge_model = by_key[judge_key]
            units.append(
                {
                    "key": f"judge|{record['model_key']}|{record['case_id']}|{judge_key}",
                    "stage": "judge",
                    "model_key": record["model_key"],
                    "provider_key": judge_model["provider_key"],
                    "case_id": record["case_id"],
                    "judge_key": judge_key,
                    "case": case,
                    "candidate_model": by_key[record["model_key"]],
                    "judge_model": judge_model,
                    "response_text": record["response_text"],
                    "estimate_cny": _upper_bound_call_cny(
                        judge_model,
                        len(case["prompt"]) + len(record["response_text"]) + 3000,
                        synthetic=synthetic,
                        role="judge",
                    ),
                }
            )
    return units


def attach_verdicts(records: list[dict], judge_payloads: dict, *, required: int = 2) -> dict:
    """Attach judge verdicts to candidate records, enforcing the frozen rule.

    A candidate case counts as *scored* only when it has a valid verdict from
    every intended cross-family judge (docs/METHODOLOGY_V1.md §3, Phase 5 §11).
    A case with fewer valid verdicts keeps its diagnostics but is not scored, so
    it can never be averaged into a reduced denominator.
    """
    stats = {"cases_with_two_valid_judges": 0, "cases_with_partial_judges": 0,
             "cases_with_no_valid_judges": 0, "judge_unavailable_cases": 0}

    by_candidate: dict[str, list[dict]] = {}
    for key, payload in judge_payloads.items():
        parts = key.split("|")
        if len(parts) != 4 or parts[0] != "judge":
            continue
        by_candidate.setdefault(f"{parts[1]}|{parts[2]}", []).append(payload)

    for record in records:
        if record is None:
            continue
        if record.get("error") or not record.get("response_text"):
            record.setdefault("judgements", [])
            continue
        verdicts = [
            payload
            for payload in by_candidate.get(f"{record['model_key']}|{record['case_id']}", [])
            if payload
        ]
        record["judgements"] = verdicts
        record["judge_agreement"] = judge.judge_agreement(verdicts)
        costs = [
            verdict.get("normalized_cost_cny")
            for verdict in verdicts
            if verdict.get("normalized_cost_cny") is not None
        ]
        record["judge_cost_cny"] = round(sum(costs), 8) if costs else None

        valid = judge.aggregate_verdicts(verdicts)
        if valid.get("judges_valid", 0) >= required:
            record["aggregate"] = valid
            stats["cases_with_two_valid_judges"] += 1
        else:
            record["aggregate"] = None
            record["judge_unavailable_reason"] = (
                f"only {valid.get('judges_valid', 0)}/{required} intended judge "
                "verdicts are valid; the case is not scored"
            )
            stats["judge_unavailable_cases"] += 1
            if valid.get("judges_valid", 0) == 0:
                stats["cases_with_no_valid_judges"] += 1
            else:
                stats["cases_with_partial_judges"] += 1
    return stats


# --------------------------------------------------------------------------
# Analytics helpers for the official artifacts
# --------------------------------------------------------------------------


def domain_scores(results: list[dict], model_key: str) -> dict:
    scored = [
        row
        for row in results
        if row
        and row.get("model_key") == model_key
        and row.get("aggregate")
        and row.get("error") is None
    ]
    out = {}
    for domain in config.DOMAINS:
        values = [
            row["aggregate"]["overall_score"]
            for row in scored
            if row["domain"] == domain and row["aggregate"]["overall_score"] is not None
        ]
        out[domain] = round(sum(values) / len(values), 2) if values else None
    return out


DISAGREEMENT_BINS = (
    ("exactly_zero", "gap == 0", 0.0, 0.0),
    ("gt0_le0.5", "0 < gap <= 0.5", 0.0, 0.5),
    ("gt0.5_le1.0", "0.5 < gap <= 1.0", 0.5, 1.0),
    ("gt1.0_le1.5", "1.0 < gap <= 1.5", 1.0, 1.5),
    ("gt1.5_le2.0", "1.5 < gap <= 2.0", 1.5, 2.0),
    ("gt2.0", "gap > 2.0", 2.0, None),
)


def judge_disagreement_analysis(results: list[dict], *, top_n: int = 10) -> dict:
    """Dual-judge disagreement over the cases that actually have two judges.

    Derived from the persisted judge verdicts (never from a pre-computed
    summary). The population is every candidate case whose two intended
    cross-family judges both produced a valid verdict; cases with a missing or
    invalid verdict are excluded here and reported separately as
    judge-unavailable. Bins are explicit, mutually exclusive half-open
    intervals, and their counts sum exactly to the population.
    """
    population = []
    for record in results:
        if not record:
            continue
        verdicts = [
            verdict
            for verdict in (record.get("judgements") or [])
            if verdict.get("scores") and not verdict.get("error")
        ]
        if len(verdicts) < 2:
            continue
        means = [float(verdict["mean_score"]) for verdict in verdicts]
        gap = round(max(means) - min(means), 3)
        population.append(
            {
                "model_key": record["model_key"],
                "case_id": record["case_id"],
                "domain": record.get("domain"),
                "judges": [verdict.get("judge_key") for verdict in verdicts],
                "judge_mean_scores": means,
                "gap": gap,
                "dimension_gaps": {
                    dimension: round(
                        max(v["scores"][dimension] for v in verdicts)
                        - min(v["scores"][dimension] for v in verdicts),
                        3,
                    )
                    for dimension in config.RUBRIC_DIMENSIONS
                },
            }
        )

    histogram = []
    for name, definition, lower, upper in DISAGREEMENT_BINS:
        if name == "exactly_zero":
            count = sum(1 for item in population if item["gap"] == 0.0)
        elif upper is None:
            count = sum(1 for item in population if item["gap"] > lower)
        else:
            count = sum(1 for item in population if lower < item["gap"] <= upper)
        histogram.append(
            {"bin": name, "definition": definition, "count": count}
        )

    gaps = [item["gap"] for item in population]
    highest = sorted(
        population, key=lambda item: (-item["gap"], item["model_key"], item["case_id"])
    )[:top_n]
    return {
        "population_definition": (
            "candidate cases whose two intended cross-family judges both returned a "
            "valid structured verdict"
        ),
        "population": len(population),
        "excluded_judge_unavailable_cases": sum(
            1
            for record in results
            if record and record.get("judge_unavailable_reason")
        ),
        "histogram": histogram,
        "histogram_counts_sum": sum(item["count"] for item in histogram),
        "mean_gap": round(sum(gaps) / len(gaps), 4) if gaps else None,
        "max_gap": max(gaps) if gaps else None,
        "exact_agreement_cases": sum(1 for gap in gaps if gap == 0.0),
        "highest_disagreement_cases": highest,
    }


def leaderboard_rows(document: dict, results: list[dict]) -> list[dict]:
    summary = document["summary"]
    rows = []
    for row in summary["models"]:
        rows.append(
            {
                "official_rank": row["rank"],
                "model_key": row["model_key"],
                "model_name": row["model_name"],
                "provider_model_id": row.get("model_id"),
                "model_family": row.get("model_family"),
                "provider": row.get("provider"),
                "provider_key": row.get("provider_key"),
                "region": row.get("region"),
                "product_tier": row.get("product_tier"),
                "completion_status": "COMPLETE" if row["rank_eligible"] else "INCOMPLETE",
                "official_ranking_eligible": row["rank_eligible"],
                "incomplete_reason": row["incomplete_reason"],
                "overall_quality": row["overall_score"],
                "overall_quality_exact": row.get("overall_score_exact"),
                "rubric_dimension_scores": row["dimension_scores"],
                "domain_scores": domain_scores(results, row["model_key"]),
                "deterministic_constraint_pass_rate": row["constraint_pass_rate"],
                "deterministic_checks": row["deterministic_checks"],
                "cases_scored": row["cases_scored"],
                "cases_required": row["cases_required"],
                "cases_failed": row["cases_failed"],
                "judge_unavailable_cases": row["judge_unavailable_cases"],
                "judge_usage": {
                    "judge_agreement_mean_abs_difference": row[
                        "judge_agreement_mean_abs_difference"
                    ],
                    "judge_agreement_samples": row["judge_agreement_samples"],
                },
                "candidate_cost_cny": row["candidate_cost_cny"],
                "candidate_cost_native": row["candidate_cost_native"],
                "judge_cost_cny": row["judge_cost_cny"],
                "actual_spend_cny": row["actual_spend_cny"],
                "cost_per_100_tasks_cny": row["cost_per_100_tasks_cny"],
                "quality_per_cny": row["quality_per_cny"],
                "comparative_metrics_available": row["comparative_metrics_available"],
                "suppressed_metrics": row["unavailable_metrics"],
                "latency": row["latency"],
                "tokens": row["tokens"],
                "pareto_quality_cost": row["pareto_quality_cost"],
                "pareto_quality_cost_latency": row["pareto_quality_cost_latency"],
                "dominated_by": row["dominated_by"],
            }
        )
    return rows


CSV_COLUMNS = [
    "official_rank",
    "model_key",
    "model_name",
    "provider",
    "product_tier",
    "provider_model_id",
    "completion_status",
    "overall_quality",
    "overall_quality_exact",
    "deterministic_constraint_pass_rate",
    "candidate_cost_cny",
    "quality_per_cny",
    "cost_per_100_tasks_cny",
    "mean_latency_ms",
    "p50_latency_ms",
    "p95_latency_ms",
    "pareto_quality_cost",
    "pareto_quality_cost_latency",
    "cases_scored",
    "cases_required",
]


def write_leaderboard_csv(rows: list[dict], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "official_rank": row["official_rank"],
                    "model_key": row["model_key"],
                    "model_name": row["model_name"],
                    "provider": row["provider"],
                    "product_tier": row["product_tier"],
                    "provider_model_id": row["provider_model_id"],
                    "completion_status": row["completion_status"],
                    "overall_quality": row["overall_quality"],
                    "overall_quality_exact": row["overall_quality_exact"],
                    "deterministic_constraint_pass_rate": row[
                        "deterministic_constraint_pass_rate"
                    ],
                    "candidate_cost_cny": row["candidate_cost_cny"],
                    "quality_per_cny": row["quality_per_cny"],
                    "cost_per_100_tasks_cny": row["cost_per_100_tasks_cny"],
                    "mean_latency_ms": row["latency"]["avg_latency_ms"],
                    "p50_latency_ms": row["latency"]["p50_latency_ms"],
                    "p95_latency_ms": row["latency"]["p95_latency_ms"],
                    "pareto_quality_cost": row["pareto_quality_cost"],
                    "pareto_quality_cost_latency": row["pareto_quality_cost_latency"],
                    "cases_scored": row["cases_scored"],
                    "cases_required": row["cases_required"],
                }
            )
    return path


def _risk_score(record: dict, case: dict) -> float:
    """Deterministic risk heuristic used for the risk-focused calibration slice."""
    score = 0.0
    agreement = record.get("judge_agreement") or {}
    score += 3.0 * float(agreement.get("overall_mean_abs_difference") or 0.0)
    overall = (record.get("aggregate") or {}).get("overall_score")
    if overall is not None:
        score += max(0.0, (100.0 - float(overall)) / 25.0)
    det = record.get("deterministic") or {}
    if det and det.get("all_passed") is False:
        score += 3.0
    rate = det.get("constraint_pass_rate")
    if rate is not None and rate < 1.0:
        score += 2.0 * (1.0 - float(rate))
    if not case.get("deterministic_checks"):
        score += 2.0
    if case.get("difficulty") == "hard":
        score += 1.5
    elif case.get("difficulty") == "medium":
        score += 0.5
    judges = [v for v in record.get("judgements") or [] if v.get("scores")]
    if judges and det.get("all_passed") is False:
        judge_mean = sum(v["mean_score"] for v in judges) / len(judges)
        if judge_mean >= 4.0:
            score += 2.0  # deterministic-vs-judge divergence
    return round(score, 4)


def select_calibration(
    results: list[dict],
    case_list: list[dict],
    *,
    base_target: int = 50,
    risk_target: int = 10,
) -> dict:
    """Select the frozen 50 base + 10 risk-focused human calibration sample."""
    candidates = [row for row in results if row and not row.get("error") and row.get("response_text")]
    by_model_case = {(row["model_key"], row["case_id"]): row for row in candidates}
    model_keys = sorted({row["model_key"] for row in candidates})
    case_index = {case["id"]: case for case in case_list}

    domain_cases = {
        domain: sorted(
            [case["id"] for case in case_list if case["domain"] == domain]
        )
        for domain in config.DOMAINS
    }

    base: list[dict] = []
    for model_position, model_key in enumerate(model_keys):
        for domain_position, domain in enumerate(config.DOMAINS):
            ids = domain_cases[domain]
            chosen = None
            for offset in range(len(ids)):
                case_id = ids[(model_position + 2 * domain_position + offset) % len(ids)]
                record = by_model_case.get((model_key, case_id))
                if record and record.get("aggregate"):
                    chosen = (case_id, record, offset)
                    break
            if chosen is None:
                continue
            case_id, record, offset = chosen
            case = case_index[case_id]
            base.append(
                {
                    "sample_id": f"CAL-BASE-{len(base) + 1:03d}",
                    "slice": "base",
                    "selection_reason": "stratified: one case per domain per model",
                    "fallback_offset": offset or None,
                    "model_key": model_key,
                    "case_id": case_id,
                    "domain": case["domain"],
                    "difficulty": case.get("difficulty"),
                    "language": case.get("language"),
                }
            )
            if len(base) >= base_target:
                break
        if len(base) >= base_target:
            break

    used = {(item["model_key"], item["case_id"]) for item in base}
    scored = [
        row
        for row in candidates
        if (row["model_key"], row["case_id"]) not in used and row.get("aggregate")
    ]
    ranked = sorted(
        scored,
        key=lambda row: (
            -_risk_score(row, case_index[row["case_id"]]),
            row["model_key"],
            row["case_id"],
        ),
    )
    risk: list[dict] = []
    per_model: dict[str, int] = {}
    for row in ranked:
        if per_model.get(row["model_key"], 0) >= 2:
            continue
        case = case_index[row["case_id"]]
        risk.append(
            {
                "sample_id": f"CAL-RISK-{len(risk) + 1:03d}",
                "slice": "risk",
                "selection_reason": "risk-focused: disagreement/deterministic/judge divergence",
                "risk_score": _risk_score(row, case),
                "model_key": row["model_key"],
                "case_id": row["case_id"],
                "domain": case["domain"],
                "difficulty": case.get("difficulty"),
                "language": case.get("language"),
            }
        )
        per_model[row["model_key"]] = per_model.get(row["model_key"], 0) + 1
        if len(risk) >= risk_target:
            break

    def render(selection: dict) -> dict:
        record = by_model_case[(selection["model_key"], selection["case_id"])]
        case = case_index[selection["case_id"]]
        return {
            **selection,
            "case_title": case.get("title"),
            "case_prompt": case["prompt"],
            "evaluation_criteria": case.get("evaluation_criteria"),
            "candidate_model_id": record.get("model_id"),
            "candidate_response": record.get("response_text"),
            "deterministic": record.get("deterministic"),
            "judge_scores": [
                {
                    "judge_key": verdict.get("judge_key"),
                    "judge_model_id": verdict.get("judge_model_id"),
                    "scores": verdict.get("scores"),
                    "mean_score": verdict.get("mean_score"),
                    "normalized_score": verdict.get("normalized_score"),
                    "error": verdict.get("error"),
                }
                for verdict in record.get("judgements") or []
            ],
            "aggregate_quality": (record.get("aggregate") or {}).get("overall_score"),
            "human_labels": None,
            "human_label_status": "pending_external_review",
        }

    samples = [render(item) for item in base] + [render(item) for item in risk]
    difficulty = {}
    language = {}
    domain = {}
    for item in samples:
        difficulty[item["difficulty"]] = difficulty.get(item["difficulty"], 0) + 1
        language[item["language"]] = language.get(item["language"], 0) + 1
        domain[item["domain"]] = domain.get(item["domain"], 0) + 1
    return {
        "samples": samples,
        "distribution": {
            "total": len(samples),
            "base": len(base),
            "risk": len(risk),
            "by_model": {
                key: sum(1 for item in samples if item["model_key"] == key)
                for key in model_keys
            },
            "by_domain": domain,
            "by_difficulty": difficulty,
            "by_language": language,
        },
    }


def build_sample_results(document: dict, results: list[dict], case_index: dict) -> dict:
    """Compact, release-ready sample of real official-run results."""
    scored = [row for row in results if row and row.get("aggregate") and row.get("error") is None]
    picks: list[dict] = []
    seen: set[tuple[str, str]] = set()

    by_model: dict[str, list[dict]] = {}
    for row in scored:
        by_model.setdefault(row["model_key"], []).append(row)
    for model_key, rows in sorted(by_model.items()):
        ordered = sorted(rows, key=lambda row: row["aggregate"]["overall_score"])
        median = ordered[len(ordered) // 2]
        key = (median["model_key"], median["case_id"])
        if key not in seen:
            seen.add(key)
            picks.append(median)

    if scored:
        best = max(scored, key=lambda row: row["aggregate"]["overall_score"])
        worst = min(scored, key=lambda row: row["aggregate"]["overall_score"])
        for row in (best, worst):
            key = (row["model_key"], row["case_id"])
            if key not in seen:
                seen.add(key)
                picks.append(row)

    samples = []
    for row in picks:
        case = case_index[row["case_id"]]
        samples.append(
            {
                "case_id": row["case_id"],
                "case_title": case.get("title"),
                "domain": row["domain"],
                "difficulty": row.get("difficulty"),
                "language": row.get("language"),
                "model_key": row["model_key"],
                "model_name": row.get("model_name"),
                "provider_model_id": row.get("model_id"),
                "response_text": row.get("response_text"),
                "deterministic": {
                    "checks_passed": (row.get("deterministic") or {}).get("checks_passed"),
                    "checks_total": (row.get("deterministic") or {}).get("checks_total"),
                    "constraint_pass_rate": (row.get("deterministic") or {}).get(
                        "constraint_pass_rate"
                    ),
                    "all_passed": (row.get("deterministic") or {}).get("all_passed"),
                },
                "judge_scores": [
                    {
                        "judge_key": verdict.get("judge_key"),
                        "judge_provider_model_id": verdict.get("judge_model_id"),
                        "scores": verdict.get("scores"),
                        "mean_score": verdict.get("mean_score"),
                        "normalized_score": verdict.get("normalized_score"),
                        "error": verdict.get("error"),
                    }
                    for verdict in row.get("judgements") or []
                ],
                "aggregate_quality": row["aggregate"]["overall_score"],
                "input_tokens": row.get("input_tokens"),
                "output_tokens": row.get("output_tokens"),
                "reasoning_tokens": row.get("reasoning_tokens"),
                "cached_input_tokens": row.get("cached_input_tokens"),
                "native_cost": row.get("native_cost"),
                "native_currency": row.get("native_currency"),
                "normalized_cost_cny": row.get("normalized_cost_cny"),
                "latency_ms": row.get("latency_ms"),
            }
        )

    return {
        "artifact": "AIProductBench CN V1 — official run sample results",
        "run_id": document.get("run_id"),
        "git_commit": document["run_manifest"].get("git_commit"),
        "dataset_manifest_sha256": document["dataset"]["semantic_manifest_sha256"],
        "model_registry_snapshot_id": document["run_manifest"].get(
            "model_registry_snapshot_id"
        ),
        "pricing_snapshot_id": document["run_manifest"].get("pricing_snapshot_id"),
        "fx_snapshot_id": document["run_manifest"].get("fx_snapshot_id"),
        "note": (
            "A compact sample of real official-run results for readers. Values are "
            "observed provider usage; no synthetic data is included."
        ),
        "samples": samples,
    }


def write_official_artifacts(
    *,
    run_dir: Path,
    pool: dict,
    document: dict,
    results: list[dict],
    case_list: list[dict],
    pre: dict,
    phases: dict,
    budget: Budget,
    started_at: dt.datetime,
    finished_at: dt.datetime,
    synthetic: bool,
) -> dict:
    """Write the full official artifact set. Returns a path map."""
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    case_index = {case["id"]: case for case in case_list}
    paths: dict[str, str] = {}

    judge_payloads = [
        {
            "candidate_model_key": record["model_key"],
            "candidate_provider_model_id": record.get("model_id"),
            "case_id": record["case_id"],
            "domain": record["domain"],
            **verdict,
        }
        for record in results
        if record
        for verdict in (record.get("judgements") or [])
    ]

    failures = []
    for record in results:
        if not record:
            continue
        if record.get("error"):
            failures.append(
                {
                    "stage": "candidate",
                    "model_key": record["model_key"],
                    "provider": record.get("provider"),
                    "case_id": record["case_id"],
                    "classification": record.get("error_classification"),
                    "attempts": record.get("attempts"),
                    "error": record["error"],
                }
            )
        if record.get("judge_unavailable_reason"):
            failures.append(
                {
                    "stage": "judge",
                    "model_key": record["model_key"],
                    "case_id": record["case_id"],
                    "classification": "JUDGE_INCOMPLETE",
                    "error": record["judge_unavailable_reason"],
                    "verdict_errors": [
                        verdict.get("error")
                        for verdict in record.get("judgements") or []
                        if verdict.get("error")
                    ],
                }
            )
    for verdict in judge_payloads:
        if verdict.get("error"):
            failures.append(
                {
                    "stage": "judge_call",
                    "model_key": verdict["candidate_model_key"],
                    "case_id": verdict["case_id"],
                    "judge_key": verdict.get("judge_key"),
                    "classification": "JUDGE_CALL_ERROR",
                    "error": verdict["error"],
                }
            )

    summary = document["summary"]
    rows = leaderboard_rows(document, results)
    calibration = select_calibration(results, case_list)
    history = _phase_history(run_dir)

    # ---- audit/reporting blocks (additive; frozen metrics untouched) -------
    disagreement = judge_disagreement_analysis(results)
    summary["judge_disagreement_analysis"] = disagreement
    candidate_planned = len(models.candidates(pool)) * len(case_list)
    candidate_attempted = sum(1 for record in results if record)
    judge_planned = sum(
        len(record.get("judges_attempted") or [])
        for record in results
        if record and not record.get("error") and record.get("response_text")
    )
    judge_attempted = len(judge_payloads)
    all_models_complete = summary["official_ranking"]["complete_run"]
    execution_complete = (
        candidate_attempted >= candidate_planned and judge_attempted >= judge_planned
    )
    summary["execution_semantics"] = {
        "execution_complete": execution_complete,
        "execution_complete_meaning": (
            "Every planned paid unit was attempted and persisted: candidates "
            f"{candidate_attempted}/{candidate_planned}, judges "
            f"{judge_attempted}/{judge_planned}."
        ),
        "all_models_complete": all_models_complete,
        "all_models_complete_meaning": (
            "A model is complete only when all 50 production cases have a valid "
            "candidate result and both intended cross-family judges returned a valid "
            "verdict. Fewer than ten complete models is a benchmark result, not an "
            "unfinished execution."
        ),
        "run_complete_legacy_field": {
            "value": all_models_complete,
            "meaning": (
                "Compatibility alias of all_models_complete. It does NOT describe "
                "whether the paid execution finished."
            ),
        },
        "candidate_units_planned": candidate_planned,
        "candidate_units_attempted": candidate_attempted,
        "judge_units_planned": judge_planned,
        "judge_units_attempted": judge_attempted,
    }

    head = runner._git_commit()
    worktree_clean = _git_status().strip() == ""
    execution_commit = (document.get("recovery") or {}).get(
        "execution_provenance", {}
    ).get("git_execution_commit") or document["run_manifest"].get("git_commit")
    runtime_baseline = (document.get("recovery") or {}).get(
        "execution_provenance", {}
    ).get("configuration_baseline_commit") or "e10ceb0aa89483050ec0b09eb96e7d16c37e4e09"
    finalization_commit = (
        head if (worktree_clean and head and head != execution_commit) else None
    )

    manifest = {
        "artifact": "AIProductBench CN V1 — official full-run manifest",
        "phase": PHASE,
        "run_id": document.get("run_id"),
        "run_kind": "official_full_run",
        "canonical_official_run": not synthetic,
        "canonical_spend": document.get("canonical_spend"),
        "recovery": document.get("recovery"),
        "execution_git_commit": execution_commit,
        "runtime_baseline_commit": runtime_baseline,
        "finalization_commit": finalization_commit,
        "git_commit": execution_commit,
        "git_commit_semantics": (
            "Compatibility alias of execution_git_commit: the commit the paid execution "
            "ran from. runtime_baseline_commit is the D-054 configuration baseline (its "
            "parent) and finalization_commit is null until the recovery/reporting fix is "
            "committed. Frozen inputs are identical across all three and are verified by "
            "hash in this manifest."
        ),
        "execution_semantics": summary.get("execution_semantics"),
        "final_execution_envelope": {
            "candidate_generation_ceiling_tokens": max(
                model.get("max_output_tokens") or 0 for model in models.candidates(pool)
            ),
            "judge_generation_ceiling_tokens": max(
                [
                    model.get("judge_max_output_tokens") or 0
                    for model in models.judges(pool)
                ]
                or [0]
            ),
            "client_read_timeout_seconds": config.REQUEST_TIMEOUT_SECONDS,
            "global_concurrent_paid_calls": GLOBAL_CONCURRENCY,
            "default_provider_concurrent_calls": PER_PROVIDER_CONCURRENCY,
            "kimi_max_in_flight": PER_PROVIDER_CONCURRENCY_OVERRIDES.get("moonshot"),
            "hard_cost_ceiling_cny": budget.ceiling_cny,
            "note": (
                "FINAL V1 values. The runtime-envelope design is closed: no adaptive "
                "per-case budget, no escalation beyond the candidate ceiling, and no "
                "post-hoc change to prompts, judge mapping, or thinking configuration."
            ),
        },
        "synthetic": synthetic,
        "started_at": started_at.isoformat(timespec="seconds"),
        "finished_at": finished_at.isoformat(timespec="seconds"),
        "elapsed_seconds": round((finished_at - started_at).total_seconds(), 1),
        "git_commit": document["run_manifest"].get("git_commit"),
        "dataset_name": document["dataset"].get("name"),
        "dataset_version": document["dataset"].get("version"),
        "dataset_manifest_sha256": document["dataset"]["semantic_manifest_sha256"],
        "model_registry_snapshot_id": document["run_manifest"].get(
            "model_registry_snapshot_id"
        ),
        "model_registry_snapshot_hash": document["run_manifest"].get(
            "model_registry_snapshot_hash"
        ),
        "pricing_snapshot_id": document["run_manifest"].get("pricing_snapshot_id"),
        "pricing_snapshot_hash": document["run_manifest"].get("pricing_snapshot_hash"),
        "fx_snapshot_id": document["run_manifest"].get("fx_snapshot_id"),
        "fx_rate": config.FX_SNAPSHOT.get("fx_rate"),
        "judge_config_snapshot_id": document["run_manifest"].get(
            "judge_config_snapshot_id"
        ),
        "runtime": document["run_manifest"].get("runtime"),
        "candidate_models": [model["key"] for model in models.candidates(pool)],
        "judge_plan": pre["judge_plan"],
        "concurrency": {
            "global_paid_calls": GLOBAL_CONCURRENCY,
            "per_provider_paid_calls": PER_PROVIDER_CONCURRENCY,
            "per_provider_overrides": PER_PROVIDER_CONCURRENCY_OVERRIDES,
            "rate_limit_degrade_threshold": RATE_LIMIT_DEGRADE_THRESHOLD,
            "note": (
                "Provider account concurrency limits are an execution constraint, not a "
                "benchmark semantic. Moonshot enforces an organisation-wide concurrency of "
                "1 for Kimi, so Kimi calls are issued one at a time."
            ),
        },
        "retry_policy": {
            "max_retries": config.MAX_RETRIES,
            "backoff_seconds": config.RETRY_BACKOFF_SECONDS,
            "never_retried": list(run_smoke.PERMANENT_STATUS) + [402],
            "deferred_requeue_passes": 1,
            "deferred_requeue_classes": sorted(TRANSIENT_CLASSES),
        },
        "runtime_overrides": {
            "client_read_timeout_seconds": (
                OFFICIAL_READ_TIMEOUT_SECONDS if not synthetic else None
            ),
            "configured_read_timeout_seconds": config.REQUEST_TIMEOUT_SECONDS,
            "reason": (
                "D-053 sets the client read timeout to 600s. The first official attempt "
                "recorded a legitimate successful response needing 297.6s, so the previous "
                "allowance was not sufficiently separated from observed valid latency. The "
                "timeout is only the maximum network/runtime allowance and never changes "
                "benchmark latency measurement."
            ),
        },
        "runtime_envelope": {
            "candidate_max_output_tokens": sorted(
                {model.get("max_output_tokens") for model in models.candidates(pool)}
            ),
            "judge_max_output_tokens": sorted(
                {
                    model.get("judge_max_output_tokens")
                    for model in models.judges(pool)
                    if model.get("judge_max_output_tokens")
                }
            ),
            "role_separation": (
                "Candidate execution and judge execution are separate roles with "
                "separate generation envelopes, recorded separately here."
            ),
            "adaptive_per_case_budget": False,
            "automatic_escalation": False,
            "kimi_max_in_flight": PER_PROVIDER_CONCURRENCY_OVERRIDES.get("moonshot"),
            "note": (
                "D-054: 32768 is the FINAL V1 candidate generation ceiling and 16384 is the "
                "judge ceiling. A candidate that reaches 32768 with finish_reason=length and "
                "empty final content is a genuine candidate failure; the envelope is never "
                "widened again."
            ),
        },
        "cost_control": {
            "hard_ceiling_cny": budget.ceiling_cny,
            "spent_cny": budget.spent_cny,
            "reserved_in_flight_cny": budget.reserved_cny,
            "remaining_cny": budget.remaining(),
            "ceiling_reached": budget.stopped,
            "stop_reason": budget.stop_reason,
            "upper_bound_broken": budget.bound_broken,
            "policy": (
                "Every paid call reserves a per-call upper-bound cost before it is "
                "dispatched, so accumulated spend can never exceed the ceiling. The "
                "bound uses one token per input character and the model's configured "
                "output cap."
            ),
        },
        "phases": {name: {k: v for k, v in stats.items() if k != "results"}
                   for name, stats in phases.items()},
        "completion": {
            "run_complete": summary["official_ranking"]["complete_run"],
            "ranking_eligible_models": summary["official_ranking"]["ranked_models"],
            "incomplete_models": [
                {"model_key": item["model_key"], "reason": item["reason"]}
                for item in summary["official_ranking"]["incomplete_models"]
            ],
            "note": (
                "A model is INCOMPLETE unless every one of the 50 production cases has a "
                "valid candidate result and two valid intended cross-family judge "
                "verdicts. INCOMPLETE models keep their diagnostics but are never ranked."
            ),
        },
        "session_history": history,
        "session_count": len({entry.get("session_id") for entry in history}) or 1,
        "run_history_note": (
            "This run was executed across multiple sessions. Interrupted sessions "
            "preserve every completed paid call; only unfinished work is retried, so "
            "no paid call is duplicated. All sessions are recorded here."
        ),
        "credentials": {
            "values_recorded": False,
            "availability": pre["credential_availability"],
        },
        "preflight": pre,
    }
    _write_json(run_dir / "run_manifest.json", manifest)
    paths["run_manifest"] = str(run_dir / "run_manifest.json")

    candidate_records = [record for record in results if record]
    _write_json(run_dir / "candidate_results.json", candidate_records)
    paths["candidate_results_json"] = str(run_dir / "candidate_results.json")
    with open(run_dir / "candidate_results.jsonl", "w", encoding="utf-8") as handle:
        for record in candidate_records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    paths["candidate_results_jsonl"] = str(run_dir / "candidate_results.jsonl")

    _write_json(run_dir / "judge_results.json", judge_payloads)
    paths["judge_results_json"] = str(run_dir / "judge_results.json")
    with open(run_dir / "judge_results.jsonl", "w", encoding="utf-8") as handle:
        for verdict in judge_payloads:
            handle.write(json.dumps(verdict, ensure_ascii=False) + "\n")
    paths["judge_results_jsonl"] = str(run_dir / "judge_results.jsonl")

    _write_json(run_dir / "failures.json", failures)
    paths["failures"] = str(run_dir / "failures.json")

    _write_json(run_dir / "summary.json", summary)
    paths["summary"] = str(run_dir / "summary.json")

    _write_json(
        run_dir / "judge_disagreement.json",
        {
            "run_id": document.get("run_id"),
            "note": (
                "Dual-judge disagreement computed directly from the persisted judge "
                "verdicts in this run's checkpoint. Bins are explicit, mutually "
                "exclusive half-open intervals; histogram_counts_sum must equal "
                "population."
            ),
            **disagreement,
        },
    )
    paths["judge_disagreement"] = str(run_dir / "judge_disagreement.json")

    _write_json(run_dir / "leaderboard.json", rows)
    paths["leaderboard_json"] = str(run_dir / "leaderboard.json")
    write_leaderboard_csv(rows, run_dir / "leaderboard.csv")
    paths["leaderboard_csv"] = str(run_dir / "leaderboard.csv")

    _write_json(
        run_dir / "pareto.json",
        {
            "run_id": document.get("run_id"),
            "rule": (
                "Pareto frontier over rank-eligible (complete) models only. An incomplete "
                "model is never placed on the official frontier."
            ),
            "objectives": summary["pareto"]["quality_cost"]["objectives"],
            "quality_cost": summary["pareto"]["quality_cost"],
            "quality_cost_latency": summary["pareto"]["quality_cost_latency"],
            "rank_eligible_models": [
                row["model_key"] for row in rows if row["official_ranking_eligible"]
            ],
            "excluded_incomplete_models": [
                {
                    "model_key": row["model_key"],
                    "reason": row["incomplete_reason"],
                }
                for row in rows
                if not row["official_ranking_eligible"]
            ],
        },
    )
    paths["pareto"] = str(run_dir / "pareto.json")

    _write_json(
        run_dir / "cost_summary.json",
        {
            "run_id": document.get("run_id"),
            "currency": config.DISPLAY_CURRENCY,
            "fx_snapshot_id": config.FX_SNAPSHOT.get("snapshot_id"),
            "fx_rate": config.FX_SNAPSHOT.get("fx_rate"),
            "pricing_snapshot_id": document["run_manifest"].get("pricing_snapshot_id"),
            "candidate_spend_cny": summary["totals"]["candidate_cost_cny"],
            "judge_spend_cny": summary["totals"]["judge_cost_cny"],
            "total_spend_cny": (
                round(
                    (summary["totals"]["candidate_cost_cny"] or 0.0)
                    + (summary["totals"]["judge_cost_cny"] or 0.0),
                    8,
                )
            ),
            "hard_ceiling_cny": budget.ceiling_cny,
            "ceiling_remaining_cny": budget.remaining(),
            "candidate_calls": summary["totals"]["candidate_calls"],
            "judge_calls": summary["totals"]["judge_calls"],
            "per_model": [
                {
                    "model_key": row["model_key"],
                    "completion_status": row["completion_status"],
                    "candidate_cost_cny": row["candidate_cost_cny"],
                    "judge_cost_cny": row["judge_cost_cny"],
                    "actual_spend_cny": row["actual_spend_cny"],
                    "cost_per_100_tasks_cny": row["cost_per_100_tasks_cny"],
                    "quality_per_cny": row["quality_per_cny"],
                }
                for row in rows
            ],
        },
    )
    paths["cost_summary"] = str(run_dir / "cost_summary.json")

    _write_json(
        run_dir / "latency_summary.json",
        {
            "run_id": document.get("run_id"),
            "role_separation": (
                "Candidate latency and judge latency are reported separately and never mixed."
            ),
            "candidate_latency_ms": {
                row["model_key"]: row["latency"] for row in rows
            },
            "judge_latency_ms": {
                "avg_latency_ms": summary["judge_overhead"]["judge_avg_latency_ms"],
                "p95_latency_ms": summary["judge_overhead"]["judge_p95_latency_ms"],
                "samples": summary["judge_overhead"]["judge_calls"],
            },
        },
    )
    paths["latency_summary"] = str(run_dir / "latency_summary.json")

    _write_json(run_dir / "official_results.json", document)
    paths["official_results"] = str(run_dir / "official_results.json")

    sample = build_sample_results(document, results, case_index)
    _write_json(run_dir / "sample_results.json", sample)
    paths["sample_results"] = str(run_dir / "sample_results.json")

    calibration_doc = {
        "artifact": "AIProductBench CN V1 — human calibration sample v1",
        "run_id": document.get("run_id"),
        "public_status": (
            "human calibration sample prepared / human review pending"
        ),
        "human_calibrated": False,
        "public_wording_note": (
            "This artifact selects outputs for external human review. No human labels "
            "exist yet and none are fabricated; V1 must not be described as "
            "human-calibrated until real labels are supplied."
        ),
        "git_commit": document["run_manifest"].get("git_commit"),
        "dataset_manifest_sha256": document["dataset"]["semantic_manifest_sha256"],
        "model_registry_snapshot_id": document["run_manifest"].get(
            "model_registry_snapshot_id"
        ),
        "pricing_snapshot_id": document["run_manifest"].get("pricing_snapshot_id"),
        "fx_snapshot_id": document["run_manifest"].get("fx_snapshot_id"),
        "design": {
            "base_samples": 50,
            "risk_samples": 10,
            "base_rule": "one case per domain per model (50 base samples)",
            "risk_rule": (
                "highest risk score across judge disagreement, low scores, "
                "deterministic failures, deterministic-check-free cases, hard "
                "difficulty and deterministic-vs-judge divergence"
            ),
            "no_model_calls_made": True,
            "human_labels": "pending external review — never fabricated",
        },
        "distribution": calibration["distribution"],
        "samples": calibration["samples"],
    }
    _write_json(run_dir / "calibration_sample_v1.json", calibration_doc)
    paths["calibration_sample"] = str(run_dir / "calibration_sample_v1.json")

    leaderboard_module.write(
        document,
        run_dir / "leaderboard.html",
        banner=(
            "Official AIProductBench CN V1 run — values are observed provider "
            "usage and real scoring. INCOMPLETE models are not ranked. Ranked models "
            "are ordered by full-precision mean overall quality; the displayed score "
            "is rounded to 3 decimals and exact values are in leaderboard.json/csv. "
            "Human calibration sample prepared — human review pending."
        )
        if not synthetic
        else "SELF-TEST OUTPUT — synthetic, not a real benchmark result.",
    )
    paths["leaderboard_html"] = str(run_dir / "leaderboard.html")

    return paths


# --------------------------------------------------------------------------
# Run directory handling
# --------------------------------------------------------------------------


def _envelope_call(model: dict, case: dict, *, fx_snapshot: dict) -> dict:
    """One candidate call that captures the full D-053 runtime envelope.

    Records structure and accounting only — never hidden reasoning text. The
    retry policy mirrors ``src.providers.chat`` exactly (bounded retries,
    deterministic failures never retried) so the validation reflects the
    production execution path.
    """
    import requests

    messages = [{"role": "user", "content": case["prompt"]}]
    api_key = providers.resolve_api_key(model)
    url = providers._endpoint(model)
    payload = providers._build_payload(model, messages)
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    called_at = dt.datetime.now(dt.timezone.utc)

    record = {
        "case_id": case["id"],
        "case_title": case.get("title"),
        "domain": case.get("domain"),
        "difficulty": case.get("difficulty"),
        "model_key": model["key"],
        "model_id": model.get("model_id"),
        "provider": model.get("provider"),
        "endpoint": url,
        "request_max_tokens": payload.get("max_tokens") or payload.get("max_output_tokens"),
        "http_status": None,
        "finish_reason": None,
        "content_chars": 0,
        "content_text": None,
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
        "reasoning_tokens": None,
        "cached_input_tokens": None,
        "latency_ms": None,
        "attempts": 0,
        "error": None,
        "error_classification": None,
        "native_cost": None,
        "native_currency": None,
        "normalized_cost_cny": None,
        "cost_error": None,
        "deterministic": None,
    }

    attempt = 0
    while attempt <= config.MAX_RETRIES:
        attempt += 1
        record["attempts"] = attempt
        started = time.perf_counter()
        try:
            response = requests.post(
                url, headers=headers, json=payload,
                timeout=config.REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            record["latency_ms"] = round((time.perf_counter() - started) * 1000, 1)
            record["error"] = f"{type(exc).__name__}: {exc}"
            record["error_classification"] = "NETWORK"
        else:
            record["latency_ms"] = round((time.perf_counter() - started) * 1000, 1)
            record["http_status"] = response.status_code
            if response.status_code in providers._FATAL_STATUS or (
                response.status_code >= 400 and providers._is_billing_body(response.text)
            ):
                record["error"] = (
                    f"HTTP {response.status_code}: {response.text[:300]}"
                )
                record["error_classification"] = run_smoke.classify_provider_error(
                    record["error"]
                )
                return record  # deterministic failure: never retried
            if response.status_code >= 400:
                record["error"] = f"HTTP {response.status_code}: {response.text[:300]}"
                record["error_classification"] = run_smoke.classify_provider_error(
                    record["error"]
                )
            else:
                try:
                    data = response.json()
                except ValueError:
                    record["error"] = "provider returned invalid JSON"
                    record["error_classification"] = "UNKNOWN"
                else:
                    text, usage = providers._extract_text_and_usage(
                        data, model["wire_api"]
                    )
                    record.update(
                        {
                            "finish_reason": providers._extract_finish_reason(
                                data, model["wire_api"]
                            ),
                            "content_chars": len(text or ""),
                            "content_text": text or None,
                            "input_tokens": usage.get("input_tokens"),
                            "output_tokens": usage.get("output_tokens"),
                            "total_tokens": usage.get("total_tokens"),
                            "reasoning_tokens": usage.get("reasoning_tokens"),
                            "cached_input_tokens": usage.get("cached_input_tokens"),
                        }
                    )
                    priced = pricing.price_call(
                        model,
                        usage.get("input_tokens"),
                        usage.get("output_tokens"),
                        cached_input_tokens=usage.get("cached_input_tokens"),
                        at=called_at,
                        fx_snapshot=fx_snapshot,
                    )
                    record.update(
                        {
                            "native_cost": priced.get("native_cost"),
                            "native_currency": priced.get("native_currency"),
                            "normalized_cost_cny": priced.get("normalized_cost_cny"),
                            "cost_error": priced.get("cost_error"),
                        }
                    )
                    if text:
                        record["error"] = None
                        record["error_classification"] = None
                        break
                    record["error"] = "empty final content (generation envelope exhausted)"
                    record["error_classification"] = "EMPTY_FINAL_CONTENT"
        if attempt <= config.MAX_RETRIES:
            time.sleep(config.RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1)))

    if record["content_text"]:
        record["deterministic"] = deterministic.evaluate(case, record["content_text"])
    return record


def envelope_units_from_checkpoint(
    source_run: Path, pool: dict, case_index: dict
) -> list[dict]:
    """The previously failed candidate units recorded in an aborted run.

    Successful units are never selected, so a D-053 validation re-runs exactly
    the failures and nothing else.
    """
    source_checkpoint = Path(source_run) / "checkpoint" / "candidate_calls.jsonl"
    if not source_checkpoint.exists():
        raise SystemExit(f"No candidate checkpoint found at {source_checkpoint}")

    by_key = {model["key"]: model for model in pool["models"]}

    latest: dict[str, dict] = {}
    for record in _load_jsonl(source_checkpoint):
        latest[record["key"]] = record
    failed = [record for record in latest.values() if not record["outcome"]["ok"]]

    units = []
    for record in sorted(failed, key=lambda item: (item["model_key"], item["case_id"])):
        model = by_key[record["model_key"]]
        case = case_index[record["case_id"]]
        error = record["outcome"].get("error") or ""
        units.append(
            {
                "key": record["key"],
                "provider_key": model["provider_key"],
                "model_key": model["key"],
                "case_id": case["id"],
                "judge_key": None,
                "model": model,
                "case": case,
                "previous_error": error,
                "previous_kind": (
                    "empty_response" if "empty response" in error else "transport_or_other"
                ),
                "estimate_cny": _upper_bound_call_cny(
                    model, len(case["prompt"]), synthetic=False
                ),
            }
        )
    return units


def run_envelope_check(
    *, source_run: Path, output_dir: Path, confirm: bool, ceiling_cny: float
) -> int:
    """Re-run exactly the previously failed candidate units under D-053."""
    pool = runner.load_model_pool()
    case_document = runner.load_test_cases(config.PRODUCTION_CASES_FILE)
    case_list = cases_module.all_cases(case_document)
    case_index = {case["id"]: case for case in case_list}
    units = envelope_units_from_checkpoint(Path(source_run), pool, case_index)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = output_dir / "units.jsonl"
    budget = Budget(ceiling_cny)

    print(f"Envelope validation: {len(units)} previously failed candidate units")
    print(f"Envelope   : {sorted({m['max_output_tokens'] for m in pool['models']})} tokens")
    print(f"Timeout    : {config.REQUEST_TIMEOUT_SECONDS:.0f}s")
    print(f"Ceiling    : {ceiling_cny:.2f} CNY")
    if not confirm:
        print("Re-run with --confirm to spend.")
        return 2

    def worker(unit):
        record = _envelope_call(
            unit["model"], unit["case"], fx_snapshot=config.FX_SNAPSHOT
        )
        outcome = {
            "ok": bool(record.get("content_text")),
            "classification": record.get("error_classification"),
            "cost_cny": record.get("normalized_cost_cny"),
            "error": record.get("error"),
            "elapsed_ms": record.get("latency_ms"),
            "attempts": record.get("attempts"),
        }
        return record, outcome

    stats = execute_units(
        units,
        worker=worker,
        budget=budget,
        checkpoint_path=checkpoint,
        label="envelope_check",
        synthetic=False,
        progress_every=5,
    )

    records = [
        stats["results"].get(unit["key"]) for unit in units
    ]
    records = [record for record in records if record]

    previous_empty = [unit for unit in units if unit["previous_kind"] == "empty_response"]
    previous_other = [unit for unit in units if unit["previous_kind"] != "empty_response"]
    empty_ok = [
        record for record in records
        if any(u["key"] == f"candidate|{record['model_key']}|{record['case_id']}" for u in previous_empty)
        and record.get("content_chars")
    ]
    other_records = [
        record for record in records
        if any(u["key"] == f"candidate|{record['model_key']}|{record['case_id']}" for u in previous_other)
    ]
    other_ok = [
        record for record in other_records
        if record.get("content_chars")
        or record.get("error_classification") in ("NETWORK", "RATE_LIMIT", "PROVIDER_SERVER")
    ]
    still_empty = [
        record for record in records
        if not record.get("content_chars")
        and record.get("finish_reason") == "length"
        and record.get("error_classification") == "EMPTY_FINAL_CONTENT"
    ]

    def classify(record: dict) -> str:
        if record.get("content_chars"):
            return "PASS"
        if (
            record.get("finish_reason") == "length"
            and record.get("error_classification") == "EMPTY_FINAL_CONTENT"
        ):
            return "REAL_MODEL_FAILURE"
        if record.get("error_classification") in ("NETWORK", "RATE_LIMIT", "PROVIDER_SERVER"):
            return "TRANSIENT_RUNTIME_FAILURE"
        return "OTHER_FAILURE"

    for record in records:
        record["classification"] = classify(record)

    counts = {
        "PASS": sum(1 for record in records if record["classification"] == "PASS"),
        "REAL_MODEL_FAILURE": sum(
            1 for record in records if record["classification"] == "REAL_MODEL_FAILURE"
        ),
        "TRANSIENT_RUNTIME_FAILURE": sum(
            1 for record in records if record["classification"] == "TRANSIENT_RUNTIME_FAILURE"
        ),
        "OTHER_FAILURE": sum(
            1 for record in records if record["classification"] == "OTHER_FAILURE"
        ),
    }
    attempted = len(records)
    units_requested = len(units)
    all_attempted = attempted == units_requested
    truncation_by_family: dict[str, int] = {}
    for record in still_empty:
        family = next(
            (
                model["model_family"]
                for model in pool["models"]
                if model["key"] == record["model_key"]
            ),
            "unknown",
        )
        truncation_by_family[family] = truncation_by_family.get(family, 0) + 1
    # D-054 §10: the envelope is validated when every unit was attempted under
    # the final configuration and any remaining truncation is isolated model behaviour
    # rather than a systemic infrastructure defect. An isolated 32768
    # empty-final failure is a REAL_MODEL_FAILURE and never triggers another
    # envelope revision.
    validated = all_attempted and counts["OTHER_FAILURE"] == 0

    summary = {
        "validation": "D-053 runtime-envelope validation",
        "source_aborted_run": str(source_run),
        "aborted_run_status": "ABORTED_RUNTIME_ENVELOPE",
        "units_requested": len(units),
        "units_rerun": attempted,
        "previous_generation_budget_failures": len(previous_empty),
        "previous_generation_budget_failures_now_non_empty": len(empty_ok),
        "previous_transport_failures": len(previous_other),
        "previous_transport_failures_now_acceptable": len(other_ok),
        "still_finish_reason_length_with_empty_content": len(still_empty),
        "classification_counts": counts,
        "truncation_by_family": truncation_by_family,
        "all_units_attempted": all_attempted,
        "units_not_attempted": units_requested - attempted,
        "validated": validated,
        "envelope_final": True,
        "further_escalation_permitted": False,
        "spend_cny": budget.spent_cny,
        "ceiling_cny": budget.ceiling_cny,
        "candidate_max_output_tokens_envelope": sorted(
            {m["max_output_tokens"] for m in pool["models"]}
        ),
        "judge_max_output_tokens_envelope": sorted(
            {
                m["judge_max_output_tokens"]
                for m in pool["models"]
                if m.get("judge_max_output_tokens")
            }
        ),
        "timeout_seconds": config.REQUEST_TIMEOUT_SECONDS,
        "registry_snapshot_id": models.build_registry_snapshot(pool)["snapshot_id"],
        "registry_snapshot_hash": models.build_registry_snapshot(pool)["content_sha256"],
        "observed": {
            "max_output_tokens": max(
                (r.get("output_tokens") or 0) for r in records
            ) if records else None,
            "max_reasoning_tokens": max(
                (r.get("reasoning_tokens") or 0) for r in records
            ) if records else None,
            "max_latency_ms": max(
                (r.get("latency_ms") or 0) for r in records
            ) if records else None,
        },
    }
    _write_json(output_dir / "summary.json", summary)
    _write_json(output_dir / "units.json", records)
    _write_json(
        output_dir / "registration.json",
        {
            "registry_snapshot_id": summary["registry_snapshot_id"],
            "registry_snapshot_hash": summary["registry_snapshot_hash"],
            "pricing_snapshot_id": pricing.build_pricing_snapshot(pool["models"])["snapshot_id"],
            "pricing_snapshot_hash": pricing.build_pricing_snapshot(pool["models"])["content_sha256"],
            "fx_snapshot_id": config.FX_SNAPSHOT.get("snapshot_id"),
            "timeout_seconds": config.REQUEST_TIMEOUT_SECONDS,
            "candidate_max_output_tokens": summary["candidate_max_output_tokens_envelope"],
            "judge_max_output_tokens": summary["judge_max_output_tokens_envelope"],
            "kimi_max_in_flight": PER_PROVIDER_CONCURRENCY_OVERRIDES.get("moonshot"),
        },
    )

    print("\n== Envelope validation result ==")
    for record in records:
        print(
            f"  {record['model_key']:<20} {record['case_id']:<7} "
            f"http={record.get('http_status')} finish={record.get('finish_reason')} "
            f"chars={record.get('content_chars')} in={record.get('input_tokens')} "
            f"out={record.get('output_tokens')} reason={record.get('reasoning_tokens')} "
            f"lat={(record.get('latency_ms') or 0)/1000:.1f}s "
            f"cny={record.get('normalized_cost_cny')} "
            f"det={(record.get('deterministic') or {}).get('all_passed')}"
        )
    print(f"\n  generation-budget failures now non-empty: "
          f"{len(empty_ok)}/{len(previous_empty)}")
    print(f"  transport unit acceptable                 : "
          f"{len(other_ok)}/{len(previous_other)}")
    print(f"  still length+empty                        : {len(still_empty)}")
    print(f"  spend                                     : {budget.spent_cny:.6f} / "
          f"{budget.ceiling_cny:.2f} CNY")
    print(f"  classification                            : {counts}")
    print(f"  units attempted                           : {attempted}/{units_requested}")
    print(f"  truncation by family                      : {truncation_by_family}")
    print(f"  VALIDATED={validated} (32768 is final; isolated REAL_MODEL_FAILURE "
          "does not trigger another revision)")
    return 0 if validated else 1


def resolve_run_dir(explicit: Path | None, *, synthetic: bool, force_new: bool = False) -> Path:
    if explicit:
        return Path(explicit)
    prefix = "official_selftest_" if synthetic else "official_run_v1_"
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    if not force_new:
        existing = sorted(
            [path for path in config.RESULTS_DIR.glob(f"{prefix}*") if path.is_dir()],
            key=lambda path: path.name,
        )
        if existing:
            return existing[-1]
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return config.RESULTS_DIR / f"{prefix}{stamp}"


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run_official.py",
        description=(
            "Phase 5 official AIProductBench CN V1 full run: 50 frozen cases x 10 "
            "locked candidates with the frozen cross-family dual-judge mapping."
        ),
    )
    parser.add_argument("--confirm", action="store_true",
                        help="required to make paid calls")
    parser.add_argument("--preflight", action="store_true",
                        help="run offline preflight checks only")
    parser.add_argument("--self-test", action="store_true", dest="self_test",
                        help="offline full-pipeline rehearsal with synthetic calls")
    parser.add_argument("--run-dir", type=Path, default=None,
                        help="explicit run directory (default: resume the newest)")
    parser.add_argument("--new-run", action="store_true",
                        help="always create a fresh run directory")
    parser.add_argument("--report-only", action="store_true", dest="report_only",
                        help="no calls: rebuild artifacts from the existing checkpoint")
    parser.add_argument("--envelope-check", action="store_true", dest="envelope_check",
                        help="D-053: re-run only previously failed BUDGET units")
    parser.add_argument("--source-run", type=Path, default=None, dest="source_run",
                        help="aborted run directory used by --envelope-check")
    parser.add_argument("--validation-ceiling-cny", type=float, default=20.0,
                        dest="validation_ceiling_cny",
                        help="hard ceiling for the D-053 envelope validation")
    parser.add_argument("--validation-dir", type=Path, default=None,
                        dest="validation_dir",
                        help="reuse an existing validation directory (resumes it)")
    parser.add_argument("--ceiling-cny", type=float, default=HARD_CEILING_CNY,
                        help=f"hard spend ceiling in CNY (default {HARD_CEILING_CNY:.0f})")
    return parser.parse_args(argv)


def _merge_payloads(base: dict, extra: dict) -> dict:
    merged = dict(base)
    for key, payload in extra.items():
        current = merged.get(key)
        if payload is None:
            continue
        if current is None or payload.get("error") is None:
            merged[key] = payload
    return merged


def _seed_budget_from_checkpoints(budget: Budget, run_dir: Path) -> float:
    spent = 0.0
    checkpoint_dir = run_dir / "checkpoint"
    if checkpoint_dir.exists():
        for path in sorted(checkpoint_dir.glob("*.jsonl")):
            for record in _load_jsonl(path):
                cost = (record.get("outcome") or {}).get("cost_cny")
                if cost:
                    spent += float(cost)
    budget.seed(spent)
    return round(spent, 8)


def _record_phase_history(run_dir: Path, record: dict) -> Path:
    """Append one phase/session record so multi-session provenance survives."""
    path = run_dir / "checkpoint" / "phase_history.jsonl"
    _append_jsonl(path, record)
    return path


def _phase_history(run_dir: Path) -> list[dict]:
    return _load_jsonl(run_dir / "checkpoint" / "phase_history.jsonl")


def _slim_phase_stats(stats: dict) -> dict:
    slim = {key: value for key, value in stats.items() if key != "results"}
    transient = slim.get("transient_keys")
    if transient is not None:
        slim["transient_key_count"] = len(transient)
        slim["transient_keys"] = transient[:50]
    return slim


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    synthetic = bool(args.self_test)

    pool = runner.load_model_pool()
    case_document = runner.load_test_cases(config.PRODUCTION_CASES_FILE)
    case_list = cases_module.all_cases(case_document)
    case_index = {case["id"]: case for case in case_list}

    pre = preflight(pool, case_document, require_clean_git=not synthetic)
    print("== Phase 5 preflight ==")
    for check in pre["checks"]:
        print(f"  [{'ok' if check['ok'] else 'FAIL'}] {check['check']}: {check['detail']}")
    print(f"  dataset manifest : {pre['dataset_manifest_sha256']}")
    print(f"  registry         : {pre['registry_snapshot_id']} {pre['registry_snapshot_hash']}")
    print(f"  pricing          : {pre['pricing_snapshot_id']} {pre['pricing_snapshot_hash']}")
    print(f"  fx               : {pre['fx_snapshot_id']} {pre['fx_rate']}")
    print("  credentials      : " + ", ".join(
        f"{row['env_var']}={'present' if row['present'] else 'MISSING'}"
        for row in pre["credential_availability"]
    ))
    if not pre["ok"]:
        print("\nPREFLIGHT FAILED — frozen state does not match. Stopping.")
        return 1
    if args.preflight:
        print("\nPreflight passed. No paid calls made.")
        return 0
    if args.envelope_check:
        source = args.source_run or (
            config.RESULTS_DIR / "official_run_v1_20260911T075351Z"
        )
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_dir = (
            Path(args.validation_dir)
            if args.validation_dir
            else config.RESULTS_DIR / f"d054_envelope_validation_{stamp}"
        )
        return run_envelope_check(
            source_run=Path(source),
            output_dir=output_dir,
            confirm=args.confirm,
            ceiling_cny=args.validation_ceiling_cny,
        )
    if args.report_only:
        run_dir = resolve_run_dir(args.run_dir, synthetic=synthetic)
        checkpoint_dir = run_dir / "checkpoint"
        if not checkpoint_dir.exists():
            print(f"\nNo checkpoint found under {run_dir}. Nothing to report.")
            return 1
        budget = Budget(args.ceiling_cny)
        _seed_budget_from_checkpoints(budget, run_dir)
        candidate_units = build_candidate_units(pool, case_list, synthetic=synthetic)
        judge_units = build_judge_units(pool, case_index, [], synthetic=synthetic)
        candidate_payloads = {
            record["key"]: record.get("payload")
            for record in _load_jsonl(checkpoint_dir / "candidate_calls.jsonl")
            if record.get("key")
        }
        for extra in ("candidate_calls_requeue.jsonl",):
            path = checkpoint_dir / extra
            if path.exists():
                candidate_payloads = _merge_payloads(
                    candidate_payloads,
                    {
                        record["key"]: record.get("payload")
                        for record in _load_jsonl(path)
                        if record.get("key")
                    },
                )
        records = [candidate_payloads.get(unit["key"]) for unit in candidate_units]
        records = [record for record in records if record]
        judge_payloads = {}
        for name in ("judge_calls.jsonl", "judge_calls_requeue.jsonl"):
            path = checkpoint_dir / name
            if path.exists():
                for record in _load_jsonl(path):
                    if record.get("key") and record.get("payload"):
                        judge_payloads[record["key"]] = record["payload"]
        merge_stats = attach_verdicts(records, judge_payloads)

        failures = [
            {
                "stage": "candidate",
                "case_id": record["case_id"],
                "model_key": record["model_key"],
                "classification": record.get("error_classification"),
                "error": record["error"],
            }
            for record in records
            if record.get("error")
        ]
        started_at = dt.datetime.now(dt.timezone.utc)
        document = runner.build_document(
            case_document, pool, records, failures,
            dry_run=False, fx_snapshot=config.FX_SNAPSHOT,
        )
        # Preserve the canonical run identity when rebuilding in place. The run
        # directory carries the authoritative run id of the paid execution.
        directory_name = run_dir.name
        match = re.match(r"^official_run_v1_final_(\d{8}T\d{6}Z)$", directory_name)
        run_id = (
            f"official-v1-{match.group(1)}"
            if match
            else f"report-only-{started_at.strftime('%Y%m%dT%H%M%SZ')}"
        )
        document["run_id"] = run_id
        document["run_directory"] = str(run_dir)
        document["run_manifest"]["run_id"] = run_id
        document["run_manifest"]["run_directory"] = str(run_dir)

        def _phase_spend(*names):
            total = 0.0
            printed = 0
            for name in names:
                for record in _load_jsonl(checkpoint_dir / name):
                    cost = (record.get("outcome") or {}).get("cost_cny")
                    if cost:
                        total += float(cost)
                    printed += 1
            return round(total, 8), printed

        candidate_spend, candidate_records_used = _phase_spend(
            "candidate_calls.jsonl", "candidate_calls_requeue.jsonl"
        )
        judge_spend, judge_records_used = _phase_spend(
            "judge_calls.jsonl", "judge_calls_requeue.jsonl"
        )
        document["canonical_spend"] = {
            "candidate_spend_cny": candidate_spend,
            "judge_spend_cny": judge_spend,
            "total_spend_cny": round(candidate_spend + judge_spend, 8),
            "candidate_checkpoint_records": candidate_records_used,
            "judge_checkpoint_records": judge_records_used,
            "note": (
                "Spend of the canonical paid execution, recovered from the immutable "
                "checkpoint. Excludes aborted-run, smoke, probe, D-053 and D-054 "
                "validation spend."
            ),
        }
        document["recovery"] = {
            "mode": "offline_rebuild_from_canonical_checkpoint",
            "no_network": True,
            "no_new_paid_calls": True,
            "raw_checkpoint_mutated": False,
            "rebuilt_at": started_at.isoformat(timespec="seconds"),
            "aggregation_fix": (
                "src/runner.py summarize(): judge verdict token/latency telemetry is "
                "read optionally, because valid judge failure records (provider error "
                "or unparseable judge output) carry no success-only fields."
            ),
            "execution_provenance": {
                "git_execution_commit": pre.get("git_commit"),
                "configuration_baseline_commit": "e10ceb0aa89483050ec0b09eb96e7d16c37e4e09",
                "note": (
                    "The paid execution ran from a harness-only commit whose parent is the "
                    "D-054 configuration baseline; dataset, registry, pricing and FX are "
                    "identical to that baseline and are verified by hash in this manifest."
                ),
            },
        }
        paths = write_official_artifacts(
            run_dir=run_dir, pool=pool, document=document, results=records,
            case_list=case_list, pre=pre,
            phases={"candidate": {"report_only": True, "merge": merge_stats}},
            budget=budget, started_at=started_at, finished_at=started_at,
            synthetic=synthetic,
        )
        print(f"\nReport-only rebuild: {len(records)} candidate records, "
              f"{len(judge_payloads)} judge verdicts.")
        for name, path in paths.items():
            print(f"  {name:<22} {path}")
        return 0

    if not (args.confirm or synthetic):
        print("\nPaid calls require --confirm. Use --preflight for checks only.")
        return 2

    run_dir = resolve_run_dir(
        args.run_dir, synthetic=synthetic, force_new=bool(args.new_run)
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir = run_dir / "checkpoint"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    started_at = dt.datetime.now(dt.timezone.utc)
    run_id = f"{'selftest' if synthetic else 'official'}-v1-{started_at.strftime('%Y%m%dT%H%M%SZ')}"
    budget = Budget(args.ceiling_cny)
    seeded = _seed_budget_from_checkpoints(budget, run_dir)

    print(f"\nRun directory : {run_dir}")
    print(f"Run ID        : {run_id}")
    print(f"Ceiling       : {budget.ceiling_cny:.2f} CNY (already recorded: {seeded:.6f} CNY)")
    print(f"Concurrency   : {GLOBAL_CONCURRENCY} global / {PER_PROVIDER_CONCURRENCY} per provider")
    print(f"Synthetic     : {synthetic}")
    if not synthetic:
        config.REQUEST_TIMEOUT_SECONDS = OFFICIAL_READ_TIMEOUT_SECONDS
        print(
            f"Read timeout  : {OFFICIAL_READ_TIMEOUT_SECONDS:.0f}s "
            "(runtime override of the frozen 120s client default)"
        )

    # ---- candidate phase -------------------------------------------------
    candidate_units = build_candidate_units(pool, case_list, synthetic=synthetic)
    print(f"\n== Candidate phase: {len(candidate_units)} units ==")
    candidate_stats = execute_units(
        candidate_units,
        worker=lambda unit: run_candidate_unit(
            case=unit["case"], model=unit["model"], pool=pool, synthetic=synthetic
        ),
        budget=budget,
        checkpoint_path=checkpoint_dir / "candidate_calls.jsonl",
        label="candidate",
        synthetic=synthetic,
    )
    _record_phase_history(run_dir, {
        "session_id": run_id, "recorded_at": _iso(), "phase": "candidate_main",
        "stats": _slim_phase_stats(candidate_stats),
    })
    candidate_payloads = dict(candidate_stats["results"])
    transient = [u for u in candidate_units if u["key"] in set(candidate_stats["transient_keys"])]
    if transient and not budget.stopped:
        print(f"\n== Candidate deferred retry pass: {len(transient)} units ==")
        retry_stats = execute_units(
            transient,
            worker=lambda unit: run_candidate_unit(
                case=unit["case"], model=unit["model"], pool=pool, synthetic=synthetic
            ),
            budget=budget,
            checkpoint_path=checkpoint_dir / "candidate_calls_requeue.jsonl",
            label="candidate_requeue",
            synthetic=synthetic,
        )
        candidate_payloads = _merge_payloads(candidate_payloads, retry_stats["results"])
        _record_phase_history(run_dir, {
            "session_id": run_id, "recorded_at": _iso(), "phase": "candidate_requeue",
            "stats": _slim_phase_stats(retry_stats),
        })
        candidate_stats["retry_pass"] = {
            key: value for key, value in retry_stats.items() if key != "results"
        }

    candidate_records = [candidate_payloads.get(unit["key"]) for unit in candidate_units]

    # ---- judge phase -----------------------------------------------------
    judge_units = build_judge_units(
        pool, case_index, [r for r in candidate_records if r], synthetic=synthetic
    )
    print(f"\n== Judge phase: {len(judge_units)} units ==")
    judge_stats = execute_units(
        judge_units,
        worker=lambda unit: run_judge_unit(
            case=unit["case"],
            candidate_model=unit["candidate_model"],
            judge_model=unit["judge_model"],
            response_text=unit["response_text"],
            synthetic=synthetic,
        ),
        budget=budget,
        checkpoint_path=checkpoint_dir / "judge_calls.jsonl",
        label="judge",
        synthetic=synthetic,
    )
    _record_phase_history(run_dir, {
        "session_id": run_id, "recorded_at": _iso(), "phase": "judge_main",
        "stats": _slim_phase_stats(judge_stats),
    })
    judge_payloads = dict(judge_stats["results"])
    transient_j = [u for u in judge_units if u["key"] in set(judge_stats["transient_keys"])]
    if transient_j and not budget.stopped:
        print(f"\n== Judge deferred retry pass: {len(transient_j)} units ==")
        retry_stats = execute_units(
            transient_j,
            worker=lambda unit: run_judge_unit(
                case=unit["case"],
                candidate_model=unit["candidate_model"],
                judge_model=unit["judge_model"],
                response_text=unit["response_text"],
                synthetic=synthetic,
            ),
            budget=budget,
            checkpoint_path=checkpoint_dir / "judge_calls_requeue.jsonl",
            label="judge_requeue",
            synthetic=synthetic,
        )
        judge_payloads = _merge_payloads(judge_payloads, retry_stats["results"])
        _record_phase_history(run_dir, {
            "session_id": run_id, "recorded_at": _iso(), "phase": "judge_requeue",
            "stats": _slim_phase_stats(retry_stats),
        })
        judge_stats["retry_pass"] = {
            key: value for key, value in retry_stats.items() if key != "results"
        }

    # ---- aggregation -----------------------------------------------------
    records = [record for record in candidate_records if record]
    judge_stats["merge"] = attach_verdicts(records, judge_payloads)

    failures = []
    for record in records:
        if record.get("error"):
            failures.append(
                {
                    "stage": "candidate",
                    "case_id": record["case_id"],
                    "model_key": record["model_key"],
                    "model_name": record.get("model_name"),
                    "classification": record.get("error_classification"),
                    "error": record["error"],
                }
            )

    document = runner.build_document(
        case_document,
        pool,
        records,
        failures,
        dry_run=False,
        fx_snapshot=config.FX_SNAPSHOT,
    )
    document["run_id"] = run_id
    document["run_directory"] = str(run_dir)
    document["synthetic"] = synthetic
    document["run_manifest"]["run_id"] = run_id
    document["run_manifest"]["run_directory"] = str(run_dir)
    document["run_manifest"]["phase"] = PHASE

    finished_at = dt.datetime.now(dt.timezone.utc)
    paths = write_official_artifacts(
        run_dir=run_dir,
        pool=pool,
        document=document,
        results=records,
        case_list=case_list,
        pre=pre,
        phases={"candidate": candidate_stats, "judge": judge_stats},
        budget=budget,
        started_at=started_at,
        finished_at=finished_at,
        synthetic=synthetic,
    )

    summary = document["summary"]
    print("\n== Official run summary ==")
    print(f"  elapsed            : {round((finished_at - started_at).total_seconds(), 1)}s")
    print(f"  candidate calls    : {summary['totals']['candidate_calls']} attempted")
    print(f"  judge calls        : {summary['totals']['judge_calls']} attempted")
    print(f"  candidate spend    : {summary['totals']['candidate_cost_cny']} CNY")
    print(f"  judge spend        : {summary['totals']['judge_cost_cny']} CNY")
    print(f"  total spend        : {budget.spent_cny:.6f} CNY of {budget.ceiling_cny:.2f}")
    print(f"  ceiling remaining  : {budget.remaining():.6f} CNY")
    for row in summary["models"]:
        status = "COMPLETE" if row["rank_eligible"] else "INCOMPLETE"
        score = row["overall_score"]
        print(f"  {row['model_key']:<20} {status:<11} "
              f"score={score if score is not None else 'n/a'} "
              f"cases={row['cases_scored']}/{row['cases_required']} "
              f"rank={row['rank']}")
    print("\n  artifacts:")
    for name, path in paths.items():
        print(f"    {name:<22} {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
