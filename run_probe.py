#!/usr/bin/env python3
"""Phase 4D.1 targeted blocker-clearance probes for AIProductBench CN V1.

This is deliberately NOT the benchmark runner and NOT the Phase 4D smoke run.
It issues the smallest possible number of paid calls to clear specific blockers
identified by the previous smoke:

* ``candidate``  — one or more models x one or more frozen cases, candidate
  calls only (no judges), with honest verification and cost plumbing.
* ``judge``      — reuses a candidate response already captured by a probe
  artifact and runs an explicitly requested judge pair, asserting the requested
  pair is the frozen cross-family route for that candidate.
* ``diagnostic`` — a single raw HTTP call per model that records response
  structure (field names, finish_reason, content/reasoning lengths, token
  counts) without ever storing reasoning text.

Safety properties:

* Paid calls require an explicit ``--confirm`` flag.
* A hard phase ceiling (20 CNY, native-normalized) is enforced across *every*
  probe invocation via a shared spend ledger, before each call.
* Credentials are read from environment variables only and are never written
  into any artifact, printed, or serialized.
* Chain-of-thought / reasoning text is never stored or printed; only lengths,
  token counts, and field names are recorded.

This module contains no benchmark methodology. It reuses the frozen evaluator,
judge selection, pricing, and provider plumbing unchanged.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import time
from pathlib import Path

import requests

import run_smoke
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

PHASE = "4D.1"
PHASE_CEILING_CNY = 20.0
LEDGER_FILE = config.RESULTS_DIR / "phase4d1_spend_ledger.json"
AUTHORITATIVE_DATASET_MANIFEST = (
    "6b450383e528a5a0a6b813112f96182a3625c04c948839fc551c8ded63da513c"
)


# --------------------------------------------------------------------------
# Cross-invocation spend ledger (hard phase ceiling)
# --------------------------------------------------------------------------


def _load_ledger() -> dict:
    if LEDGER_FILE.exists():
        with open(LEDGER_FILE, encoding="utf-8") as handle:
            return json.load(handle)
    return {"phase": PHASE, "ceiling_cny": PHASE_CEILING_CNY, "entries": []}


def _ledger_total(ledger: dict) -> float:
    present = [
        entry["normalized_cost_cny"]
        for entry in ledger.get("entries", [])
        if entry.get("normalized_cost_cny") is not None
    ]
    return round(sum(present), 8) if present else 0.0


class PhaseBudget:
    """Hard phase-wide CNY ceiling, persisted across probe invocations."""

    def __init__(self, ceiling_cny: float):
        self.ceiling_cny = ceiling_cny
        self.ledger = _load_ledger()
        self.ledger["ceiling_cny"] = ceiling_cny
        self.stopped = False
        self.stop_reason: str | None = None
        self.unpriced_calls = 0

    def spent_so_far(self) -> float:
        return _ledger_total(self.ledger)

    def remaining(self) -> float:
        return round(self.ceiling_cny - self.spent_so_far(), 8)

    def can_afford(self, estimate_cny, *, label: str) -> bool:
        if self.stopped:
            return False
        if estimate_cny is None:
            return True
        if self.spent_so_far() + float(estimate_cny) > self.ceiling_cny:
            self.stopped = True
            self.stop_reason = (
                f"phase ceiling would be exceeded before {label}: "
                f"{self.spent_so_far():.6f} + {float(estimate_cny):.6f} > "
                f"{self.ceiling_cny:.2f} CNY"
            )
            return False
        return True

    def record(
        self,
        *,
        label: str,
        normalized_cost_cny,
        native_cost=None,
        native_currency=None,
    ) -> None:
        if normalized_cost_cny is None:
            self.unpriced_calls += 1
        self.ledger.setdefault("entries", []).append(
            {
                "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "label": label,
                "native_cost": native_cost,
                "native_currency": native_currency,
                "normalized_cost_cny": normalized_cost_cny,
            }
        )
        runner.write_json(self.ledger, LEDGER_FILE)
        if self.spent_so_far() >= self.ceiling_cny:
            self.stopped = True
            self.stop_reason = (
                f"phase ceiling reached after {label}: "
                f"{self.spent_so_far():.6f} >= {self.ceiling_cny:.2f} CNY"
            )


def _estimate_call_cny(model: dict, messages: list[dict]) -> float | None:
    """Conservative pre-call estimate: full max_output_tokens budget."""
    input_estimate = sum(max(1, len(m["content"]) // 4) for m in messages) + 256
    output_estimate = int(model.get("max_output_tokens") or 2048)
    priced = pricing.price_call(
        model,
        input_estimate,
        output_estimate,
        at=dt.datetime.now(dt.timezone.utc),
        fx_snapshot=config.FX_SNAPSHOT,
    )
    return priced.get("normalized_cost_cny")


# --------------------------------------------------------------------------
# Shared loading
# --------------------------------------------------------------------------


def _load(keys: list[str], case_ids: list[str]):
    pool = runner.load_model_pool()
    by_key = {m["key"]: m for m in pool["models"]}
    missing = [k for k in keys if k not in by_key]
    if missing:
        raise SystemExit(f"Unknown model key(s): {missing}")
    selected_models = [by_key[k] for k in keys]

    case_document = cases_module.load_cases(config.PRODUCTION_CASES_FILE)
    index = {c["id"]: c for c in cases_module.all_cases(case_document)}
    missing_cases = [c for c in case_ids if c not in index]
    if missing_cases:
        raise SystemExit(f"Unknown case id(s): {missing_cases}")
    selected_cases = [index[c] for c in case_ids]

    manifest = cases_module.semantic_manifest_hash(cases_module.all_cases(case_document))
    if manifest != AUTHORITATIVE_DATASET_MANIFEST:
        raise SystemExit(
            f"Frozen dataset manifest mismatch: {manifest}"
        )
    return pool, selected_models, selected_cases


def _snapshot_ids(pool: dict) -> dict:
    registry = models.build_registry_snapshot(pool)
    pricing_doc = pricing.build_pricing_snapshot(pool["models"])
    return {
        "registry_snapshot_id": registry["snapshot_id"],
        "registry_snapshot_hash": registry["content_sha256"],
        "pricing_snapshot_id": pricing_doc["snapshot_id"],
        "pricing_snapshot_hash": pricing_doc["content_sha256"],
        "fx_snapshot_id": config.FX_SNAPSHOT.get("snapshot_id"),
        "fx_rate": config.FX_SNAPSHOT.get("fx_rate"),
    }


def _base_document(mode: str, pool: dict, *, output: Path) -> dict:
    started = dt.datetime.now(dt.timezone.utc)
    return {
        "artifact": f"AIProductBench CN V1 - Phase {PHASE} targeted probe ({mode})",
        "phase": PHASE,
        "mode": mode,
        "run_id": f"probe-4D1-{mode}-{started.strftime('%Y%m%dT%H%M%SZ')}",
        "synthetic": False,
        "generated_at": started.isoformat(timespec="seconds"),
        "provenance": {
            "git_commit_at_run": runner._git_commit(),
            "dataset_manifest_sha256": AUTHORITATIVE_DATASET_MANIFEST,
            **_snapshot_ids(pool),
        },
        "cost_control": {
            "phase_ceiling_cny": PHASE_CEILING_CNY,
            "ledger_file": str(LEDGER_FILE.relative_to(config.PROJECT_ROOT)),
            "enforced_before_every_call": True,
        },
        "credentials": {
            "values_read_into_artifact": False,
            "availability": run_smoke._credential_rows(pool),
        },
        "results": [],
        "totals": {},
    }


def _finalize_totals(document: dict, budget: PhaseBudget) -> None:
    calls = [c for r in document["results"] for c in r.get("calls", [])]
    present = [c["normalized_cost_cny"] for c in calls if c.get("normalized_cost_cny") is not None]
    native: dict[str, float] = {}
    for call in calls:
        if call.get("native_cost") is not None and call.get("native_currency"):
            cur = call["native_currency"]
            native[cur] = round(native.get(cur, 0.0) + call["native_cost"], 8)
    document["totals"] = {
        "calls": len(calls),
        "calls_billed": len(present),
        "cost_this_run_cny": round(sum(present), 8) if present else 0.0,
        "native_cost_by_currency": native or None,
        "phase_spent_cny": budget.spent_so_far(),
        "phase_remaining_cny": budget.remaining(),
        "phase_stopped": budget.stopped,
        "phase_stop_reason": budget.stop_reason,
        "unpriced_calls": budget.unpriced_calls,
    }
    runner.write_json(document, budget.output_path)


# --------------------------------------------------------------------------
# Candidate probes
# --------------------------------------------------------------------------


def run_candidate(
    *, keys: list[str], case_ids: list[str], output: Path, confirm: bool
) -> int:
    pool, selected_models, selected_cases = _load(keys, case_ids)
    document = _base_document("candidate", pool, output=output)
    budget = PhaseBudget(PHASE_CEILING_CNY)
    budget.output_path = output

    print(f"Probe run   : {document['run_id']}")
    print(f"Phase spend : {budget.spent_so_far():.6f} / {PHASE_CEILING_CNY:.2f} CNY (before)")
    print(f"Models      : {', '.join(keys)}")
    print(f"Cases       : {', '.join(case_ids)}")
    print("Credentials : " + ", ".join(
        f"{r['env_var']}={'yes' if r['present'] else 'no'}"
        for r in document["credentials"]["availability"]
    ))

    if not confirm:
        print("\nDry probe (no network calls). Re-run with --confirm to spend.")
        runner.write_json(document, output)
        return 2

    for model in selected_models:
        result = {
            "model_key": model["key"],
            "display_name": model["display_name"],
            "model_id": model.get("model_id"),
            "model_family": model["model_family"],
            "provider": model["provider"],
            "provider_key": model["provider_key"],
            "region": model.get("region"),
            "endpoint": providers._endpoint(model),
            "credential_env": model["api_key_env"],
            "credential_present": run_smoke._credential_present(model),
            "request_config": providers.effective_request_config(model),
            "thinking_config": model.get("thinking_config"),
            "status": None,
            "status_reason": None,
            "verification": {},
            "calls": [],
        }
        if not result["credential_present"]:
            result["status"] = "PROBE_BLOCKED_CREDENTIAL"
            result["status_reason"] = f"{model['api_key_env']} is not set."
            document["results"].append(result)
            _finalize_totals(document, budget)
            continue

        for case in selected_cases:
            messages = [{"role": "user", "content": case["prompt"]}]
            estimate = _estimate_call_cny(model, messages)
            if not budget.can_afford(estimate, label=f"candidate {model['key']}/{case['id']}"):
                result["status"] = "PROBE_STOPPED_CEILING"
                result["status_reason"] = budget.stop_reason
                break

            call = {
                "case_id": case["id"],
                "stage": "candidate",
                "accepted": False,
                "error": None,
                "error_classification": None,
                "attempts": None,
                "response_chars": None,
                "response_text": None,
                "latency_ms": None,
                "input_tokens": None,
                "output_tokens": None,
                "total_tokens": None,
                "reasoning_tokens": None,
                "cached_input_tokens": None,
                "native_cost": None,
                "native_currency": None,
                "normalized_cost_cny": None,
                "normalization_method": None,
                "cost_error": None,
                "deterministic": None,
            }
            try:
                response = providers.chat(model, messages, fx_snapshot=config.FX_SNAPSHOT)
            except providers.ProviderError as exc:
                message = str(exc)
                classification = run_smoke.classify_provider_error(message)
                call["error"] = message
                call["error_classification"] = classification
                call["attempts"] = run_smoke._attempts_for(message, classification)
                result["calls"].append(call)
                result["status"] = run_smoke.status_for_classification(classification)
                result["status_reason"] = f"{classification}: {message}"
                break

            call.update(
                {
                    "accepted": True,
                    "attempts": response.get("attempts"),
                    "response_chars": len(response.get("text") or ""),
                    "response_text": response.get("text"),
                    "latency_ms": response.get("latency_ms"),
                    "input_tokens": response.get("input_tokens"),
                    "output_tokens": response.get("output_tokens"),
                    "total_tokens": response.get("total_tokens"),
                    "reasoning_tokens": response.get("reasoning_tokens"),
                    "cached_input_tokens": response.get("cached_input_tokens"),
                    "native_cost": response.get("native_cost"),
                    "native_currency": response.get("native_currency"),
                    "normalized_cost_cny": response.get("normalized_cost_cny"),
                    "normalization_method": response.get("normalization_method"),
                    "cost_error": response.get("cost_error"),
                }
            )
            call["deterministic"] = deterministic.evaluate(case, response["text"])
            budget.record(
                label=f"candidate {model['key']}/{case['id']}",
                normalized_cost_cny=response.get("normalized_cost_cny"),
                native_cost=response.get("native_cost"),
                native_currency=response.get("native_currency"),
            )
            result["calls"].append(call)
            print(
                f"  {model['key']:<20} {case['id']} "
                f"HTTP-OK chars={call['response_chars']} "
                f"in={call['input_tokens']} out={call['output_tokens']} "
                f"reason={call['reasoning_tokens']} cached={call['cached_input_tokens']} "
                f"cny={call['normalized_cost_cny']} lat={call['latency_ms']}ms"
            )

        if result["status"] is None:
            result["status"] = "PROBE_PASS" if result["calls"] and all(
                c["accepted"] for c in result["calls"]
            ) else "PROBE_FAIL"
        result["verification"] = _candidate_verification(result)
        document["results"].append(result)
        _finalize_totals(document, budget)

    _finalize_totals(document, budget)
    print(f"\nPhase spend : {budget.spent_so_far():.6f} / {PHASE_CEILING_CNY:.2f} CNY")
    print(f"Artifact    : {output}")
    return 0 if all(r["status"] == "PROBE_PASS" for r in document["results"]) else 1


def _capture_state(values) -> str:
    if not values:
        return "no_calls"
    present = [v for v in values if v is not None]
    if len(present) == len(values):
        return "available"
    if not present:
        return "null"
    return "mixed"


def _candidate_verification(result: dict) -> dict:
    calls = result["calls"]
    accepted = [c for c in calls if c.get("accepted")]
    extra_body = (result.get("request_config") or {}).get("extra_body") or {}
    return {
        "A_request_accepted": bool(accepted),
        "B_provider_model_id_resolves": bool(accepted),
        "C_thinking_config_sent": sorted(extra_body.keys()),
        "D_response_text_returned": all(c.get("response_chars") for c in accepted),
        "E_input_tokens": _capture_state([c.get("input_tokens") for c in calls]),
        "F_output_tokens": _capture_state([c.get("output_tokens") for c in calls]),
        "G_reasoning_tokens": _capture_state([c.get("reasoning_tokens") for c in calls]),
        "H_cached_input_tokens": _capture_state([c.get("cached_input_tokens") for c in calls]),
        "I_latency_measured": bool(calls) and all(c.get("latency_ms") is not None for c in calls),
        "J_native_price_resolved": bool(calls) and all(c.get("native_cost") is not None for c in calls),
        "K_cny_normalization_resolved": bool(calls)
        and all(c.get("normalized_cost_cny") is not None for c in calls),
        "L_deterministic_checks_execute": any(
            (c.get("deterministic") or {}).get("checks") for c in calls
        ),
    }


# --------------------------------------------------------------------------
# Judge probes
# --------------------------------------------------------------------------


def run_judge(
    *,
    source: Path,
    candidate_key: str,
    case_id: str,
    judge_keys: list[str],
    output: Path,
    confirm: bool,
) -> int:
    with open(source, encoding="utf-8") as handle:
        source_doc = json.load(handle)

    candidate_result = next(
        (r for r in source_doc.get("results", []) if r["model_key"] == candidate_key), None
    )
    if candidate_result is None:
        raise SystemExit(f"{candidate_key} not found in {source}")
    call = next(
        (c for c in candidate_result["calls"] if c["case_id"] == case_id and c.get("accepted")),
        None,
    )
    if call is None or not call.get("response_text"):
        raise SystemExit(
            f"No stored response text for {candidate_key}/{case_id} in {source}. "
            "Store response_text with a candidate probe first."
        )
    response_text = call["response_text"]

    pool, selected_models, selected_cases = _load([candidate_key], [case_id])
    candidate = selected_models[0]
    case = selected_cases[0]
    by_key = {m["key"]: m for m in pool["models"]}
    missing = [k for k in judge_keys if k not in by_key]
    if missing:
        raise SystemExit(f"Unknown judge key(s): {missing}")
    judge_models = [by_key[k] for k in judge_keys]

    frozen = judge.select_judges(candidate, models.judges(pool), models.judge_priority(pool))
    frozen_keys = [j["key"] for j in frozen]
    route_matches = frozen_keys == [j["key"] for j in judge_models]

    document = _base_document("judge", pool, output=output)
    document["provenance"]["source_artifact"] = str(source)
    document["provenance"]["candidate_model_key"] = candidate_key
    document["provenance"]["case_id"] = case_id
    document["frozen_judge_route"] = frozen_keys
    document["requested_judge_route"] = [j["key"] for j in judge_models]
    document["route_matches_frozen"] = route_matches
    budget = PhaseBudget(PHASE_CEILING_CNY)
    budget.output_path = output

    print(f"Probe run   : {document['run_id']}")
    print(f"Candidate   : {candidate_key}/{case_id} ({len(response_text)} chars reused)")
    print(f"Judge route : requested={document['requested_judge_route']} frozen={frozen_keys} "
          f"match={route_matches}")
    print(f"Phase spend : {budget.spent_so_far():.6f} / {PHASE_CEILING_CNY:.2f} CNY (before)")

    if not confirm:
        print("\nDry probe (no network calls). Re-run with --confirm to spend.")
        runner.write_json(document, output)
        return 2

    for judge_model in judge_models:
        result = {
            "judge_key": judge_model["key"],
            "judge_model_id": judge_model.get("model_id"),
            "judge_family": judge_model["model_family"],
            "judge_provider": judge_model["provider"],
            "credential_env": judge_model["api_key_env"],
            "credential_present": run_smoke._credential_present(judge_model),
            "status": None,
            "status_reason": None,
            "calls": [],
        }
        if not result["credential_present"]:
            result["status"] = "PROBE_BLOCKED_CREDENTIAL"
            result["status_reason"] = f"{judge_model['api_key_env']} is not set."
            document["results"].append(result)
            _finalize_totals(document, budget)
            continue

        messages = judge.build_judge_messages(case, candidate, judge_model, response_text)
        estimate = _estimate_call_cny(judge_model, messages)
        if not budget.can_afford(estimate, label=f"judge {judge_model['key']}/{case_id}"):
            result["status"] = "PROBE_STOPPED_CEILING"
            result["status_reason"] = budget.stop_reason
            document["results"].append(result)
            _finalize_totals(document, budget)
            continue

        record = {
            "case_id": case_id,
            "stage": "judge",
            "accepted": False,
            "error": None,
            "error_classification": None,
            "attempts": None,
            "latency_ms": None,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "reasoning_tokens": None,
            "cached_input_tokens": None,
            "native_cost": None,
            "native_currency": None,
            "normalized_cost_cny": None,
            "scores": None,
            "mean_score": None,
            "normalized_score": None,
            "rationale": None,
        }
        try:
            response = providers.chat(judge_model, messages, fx_snapshot=config.FX_SNAPSHOT)
        except providers.ProviderError as exc:
            message = str(exc)
            classification = run_smoke.classify_provider_error(message)
            record["error"] = message
            record["error_classification"] = classification
            record["attempts"] = run_smoke._attempts_for(message, classification)
            result["calls"].append(record)
            result["status"] = run_smoke.status_for_classification(classification)
            result["status_reason"] = f"{classification}: {message}"
            document["results"].append(result)
            _finalize_totals(document, budget)
            continue

        record.update(
            {
                "accepted": True,
                "attempts": response.get("attempts"),
                "latency_ms": response.get("latency_ms"),
                "input_tokens": response.get("input_tokens"),
                "output_tokens": response.get("output_tokens"),
                "total_tokens": response.get("total_tokens"),
                "reasoning_tokens": response.get("reasoning_tokens"),
                "cached_input_tokens": response.get("cached_input_tokens"),
                "native_cost": response.get("native_cost"),
                "native_currency": response.get("native_currency"),
                "normalized_cost_cny": response.get("normalized_cost_cny"),
            }
        )
        try:
            verdict = judge.parse_judge_output(response["text"])
        except judge.JudgeOutputError as exc:
            record["error"] = f"invalid judge output: {exc}"
            record["error_classification"] = "INVALID_JUDGE_OUTPUT"
            result["status"] = "PROBE_FAIL"
            result["status_reason"] = record["error"]
        else:
            record["scores"] = verdict["scores"]
            record["rationale"] = verdict["rationale"]
            record["mean_score"] = verdict["mean_score"]
            record["normalized_score"] = verdict["normalized_score"]
            result["status"] = "PROBE_PASS"
        budget.record(
            label=f"judge {judge_model['key']}/{case_id}",
            normalized_cost_cny=response.get("normalized_cost_cny"),
            native_cost=response.get("native_cost"),
            native_currency=response.get("native_currency"),
        )
        result["calls"].append(record)
        document["results"].append(result)
        _finalize_totals(document, budget)
        print(
            f"  {judge_model['key']:<20} {result['status']} "
            f"scores={record['scores']} cny={record['normalized_cost_cny']} "
            f"lat={record['latency_ms']}ms"
        )

    valid = sum(1 for r in document["results"] if r["status"] == "PROBE_PASS")
    document["valid_verdicts"] = valid
    document["route_verified"] = bool(route_matches and valid == 2)
    _finalize_totals(document, budget)
    print(f"\nValid verdicts: {valid}/2  route_verified={document['route_verified']}")
    print(f"Phase spend   : {budget.spent_so_far():.6f} / {PHASE_CEILING_CNY:.2f} CNY")
    return 0 if document["route_verified"] else 1


# --------------------------------------------------------------------------
# Raw diagnostic probes (structure only; never reasoning text)
# --------------------------------------------------------------------------


def run_diagnostic(
    *, keys: list[str], case_id: str, output: Path, confirm: bool
) -> int:
    pool, selected_models, selected_cases = _load(keys, [case_id])
    case = selected_cases[0]
    document = _base_document("diagnostic", pool, output=output)
    budget = PhaseBudget(PHASE_CEILING_CNY)
    budget.output_path = output

    print(f"Probe run   : {document['run_id']}")
    print(f"Case        : {case_id}")
    print(f"Phase spend : {budget.spent_so_far():.6f} / {PHASE_CEILING_CNY:.2f} CNY (before)")

    if not confirm:
        print("\nDry probe (no network calls). Re-run with --confirm to spend.")
        runner.write_json(document, output)
        return 2

    for model in selected_models:
        result = {
            "model_key": model["key"],
            "model_id": model.get("model_id"),
            "provider": model["provider"],
            "endpoint": providers._endpoint(model),
            "credential_present": run_smoke._credential_present(model),
            "request_config": providers.effective_request_config(model),
            "status": None,
            "status_reason": None,
            "calls": [],
        }
        if not result["credential_present"]:
            result["status"] = "PROBE_BLOCKED_CREDENTIAL"
            result["status_reason"] = f"{model['api_key_env']} is not set."
            document["results"].append(result)
            _finalize_totals(document, budget)
            continue

        messages = [{"role": "user", "content": case["prompt"]}]
        estimate = _estimate_call_cny(model, messages)
        if not budget.can_afford(estimate, label=f"diagnostic {model['key']}/{case_id}"):
            result["status"] = "PROBE_STOPPED_CEILING"
            result["status_reason"] = budget.stop_reason
            document["results"].append(result)
            _finalize_totals(document, budget)
            continue

        call = _raw_call(model, messages)
        ready = call.get("http_status") == 200 and call.get("diagnostic", {}).get(
            "final_content_chars", 0
        )
        result["status"] = "PROBE_PASS" if ready else "PROBE_DIAGNOSED"
        result["calls"].append(call)
        budget.record(
            label=f"diagnostic {model['key']}/{case_id}",
            normalized_cost_cny=call.get("normalized_cost_cny"),
            native_cost=call.get("native_cost"),
            native_currency=call.get("native_currency"),
        )
        document["results"].append(result)
        _finalize_totals(document, budget)
        diag = call.get("diagnostic", {})
        print(
            f"  {model['key']:<18} status={call.get('http_status')} "
            f"finish_reason={diag.get('finish_reason')} "
            f"content_chars={diag.get('final_content_chars')} "
            f"reasoning_chars={diag.get('reasoning_content_chars')} "
            f"in={diag.get('input_tokens')} out={diag.get('output_tokens')} "
            f"reason={diag.get('reasoning_tokens')} "
            f"msg_fields={diag.get('message_field_names')}"
        )

    _finalize_totals(document, budget)
    print(f"\nPhase spend : {budget.spent_so_far():.6f} / {PHASE_CEILING_CNY:.2f} CNY")
    print(f"Artifact    : {output}")
    return 0


def _raw_call(model: dict, messages: list[dict]) -> dict:
    """One raw HTTP call that records response structure, never reasoning text."""
    api_key = providers.resolve_api_key(model)
    url = providers._endpoint(model)
    payload = providers._build_payload(model, messages)
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    called_at = dt.datetime.now(dt.timezone.utc)

    call = {
        "called_at": called_at.isoformat(timespec="seconds"),
        "http_status": None,
        "request_output_token_limit": payload.get("max_tokens")
        or payload.get("max_output_tokens"),
        "request_field_names": sorted(payload.keys()),
        "latency_ms": None,
        "diagnostic": {},
        "native_cost": None,
        "native_currency": None,
        "normalized_cost_cny": None,
        "cost_error": None,
    }
    try:
        started = time.perf_counter()
        response = requests.post(
            url, headers=headers, json=payload, timeout=config.REQUEST_TIMEOUT_SECONDS
        )
    except requests.RequestException as exc:
        call["diagnostic"]["transport_error"] = f"{type(exc).__name__}"
        return call
    call["latency_ms"] = round((time.perf_counter() - started) * 1000, 1)
    call["http_status"] = response.status_code

    diag = call["diagnostic"]
    try:
        data = response.json()
    except ValueError:
        diag["json_valid"] = False
        diag["raw_body_chars"] = len(response.text or "")
        return call
    diag["json_valid"] = True
    if not isinstance(data, dict):
        diag["response_type"] = type(data).__name__
        return call

    diag["response_field_names"] = sorted(data.keys())
    if "base_resp" in data and isinstance(data["base_resp"], dict):
        diag["base_resp_field_names"] = sorted(data["base_resp"].keys())
        diag["base_resp_status_code"] = data["base_resp"].get("status_code")

    choices = data.get("choices") or []
    if choices and isinstance(choices[0], dict):
        choice = choices[0]
        diag["choice_field_names"] = sorted(choice.keys())
        diag["finish_reason"] = choice.get("finish_reason")
        message = choice.get("message")
        if isinstance(message, dict):
            diag["message_field_names"] = sorted(message.keys())
            diag["final_content_chars"] = len(message.get("content") or "")
            reasoning = message.get("reasoning_content")
            diag["reasoning_content_chars"] = len(reasoning) if isinstance(reasoning, str) else None
            diag["reasoning_content_present"] = isinstance(reasoning, str) and bool(reasoning)
            # Never store the reasoning text itself.

    usage = data.get("usage") or {}
    if isinstance(usage, dict):
        diag["usage_field_names"] = sorted(usage.keys())
        diag["input_tokens"] = usage.get("prompt_tokens")
        diag["output_tokens"] = usage.get("completion_tokens")
        diag["total_tokens"] = usage.get("total_tokens")
        details = usage.get("completion_tokens_details") or {}
        prompt_details = usage.get("prompt_tokens_details") or {}
        diag["reasoning_tokens"] = details.get("reasoning_tokens")
        diag["cached_input_tokens"] = prompt_details.get("cached_tokens")

    priced = pricing.price_call(
        model,
        diag.get("input_tokens"),
        diag.get("output_tokens"),
        cached_input_tokens=diag.get("cached_input_tokens"),
        at=called_at,
        fx_snapshot=config.FX_SNAPSHOT,
    )
    call["native_cost"] = priced.get("native_cost")
    call["native_currency"] = priced.get("native_currency")
    call["normalized_cost_cny"] = priced.get("normalized_cost_cny")
    call["cost_error"] = priced.get("cost_error")
    return call


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run_probe.py",
        description=(
            "Phase 4D.1 targeted probes: minimum paid calls to clear specific "
            f"live-smoke blockers. Hard phase ceiling {PHASE_CEILING_CNY:.0f} CNY."
        ),
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--confirm", action="store_true", help="required to make paid calls")
    common.add_argument("--output", type=Path, default=None)

    candidate = sub.add_parser("candidate", parents=[common], help="candidate-only probe")
    candidate.add_argument("--models", required=True, help="comma-separated model keys")
    candidate.add_argument("--cases", required=True, help="comma-separated case ids")

    judge_p = sub.add_parser("judge", parents=[common], help="reuse a candidate response and run judges")
    judge_p.add_argument("--source", type=Path, required=True, help="probe artifact with stored response_text")
    judge_p.add_argument("--candidate-model", required=True, dest="candidate_model")
    judge_p.add_argument("--case", required=True, dest="case")
    judge_p.add_argument("--judges", required=True, help="comma-separated judge model keys")

    diag = sub.add_parser("diagnostic", parents=[common], help="raw single-call structure capture")
    diag.add_argument("--models", required=True, help="comma-separated model keys")
    diag.add_argument("--case", required=True, dest="case")

    return parser.parse_args(argv)


def _default_output(mode: str, label: str) -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in label)[:60]
    return config.RESULTS_DIR / f"probe_4D1_{mode}_{safe}_{stamp}.json"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.mode == "candidate":
        keys = [k.strip() for k in args.models.split(",") if k.strip()]
        case_ids = [c.strip() for c in args.cases.split(",") if c.strip()]
        output = args.output or _default_output("candidate", "-".join(keys) + "_" + "-".join(case_ids))
        return run_candidate(keys=keys, case_ids=case_ids, output=output, confirm=args.confirm)
    if args.mode == "judge":
        keys = [k.strip() for k in args.judges.split(",") if k.strip()]
        output = args.output or _default_output(
            "judge", f"{args.candidate_model}_{args.case}_" + "-".join(keys)
        )
        return run_judge(
            source=args.source,
            candidate_key=args.candidate_model,
            case_id=args.case,
            judge_keys=keys,
            output=output,
            confirm=args.confirm,
        )
    if args.mode == "diagnostic":
        keys = [k.strip() for k in args.models.split(",") if k.strip()]
        output = args.output or _default_output("diagnostic", "-".join(keys) + "_" + args.case)
        return run_diagnostic(keys=keys, case_id=args.case, output=output, confirm=args.confirm)
    raise SystemExit("unknown mode")


if __name__ == "__main__":
    raise SystemExit(main())
