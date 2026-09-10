"""Cross-family dual-judge evaluation.

Design (frozen, see docs/METHODOLOGY_V1.md §2C and docs/DECISIONS.md D-008/D-009):

* One shared model registry. A model may be both a candidate and a judge; there
  are no judge-only duplicates of an existing model.
* Leave-one-provider-out: a candidate response is never scored by a judge that
  shares the candidate's model family or inference provider, when an alternative
  exists.
* Judge selection follows a fixed priority list declared in configuration, not a
  per-candidate hash. Every candidate family therefore sees the same judge
  ordering, which avoids an avoidable evaluation confound.
* Exactly two eligible cross-family judges score each candidate response.
* Invalid judge output is rejected, never repaired or clamped.

Candidate execution and judge execution are distinct roles over the same
registry. Candidate inference cost and judge evaluation cost are never mixed,
and candidate latency and judge latency are never mixed.
"""

from __future__ import annotations

import hashlib
import json
import re

from src import config, pricing, providers


class JudgeOutputError(ValueError):
    """Raised when judge output cannot be parsed and validated strictly."""


RUBRIC_TEXT = """\
You are a strict evaluator of AI assistant responses for a Chinese AI product team.

Score the candidate response on exactly these three dimensions:

1. task_completion — Did the response fully do what the case asked for, using only
   the information given, without inventing facts?
2. reasoning_quality — Is the reasoning correct, specific, and decision-ready for an
   experienced product manager?
3. instruction_following — Did the response obey every explicit constraint in the
   case, including format, length, structure, and negative constraints?

Scale for every dimension: an integer from 1 to 5.
5 = excellent, no meaningful flaw.
4 = good, minor flaw.
3 = acceptable, a clear flaw a reviewer would need to fix.
2 = poor, a major flaw or a missed requirement.
1 = unusable or not responsive.

Judge against both the shared rubric above and the case-specific evaluation
criteria you are given. The case-specific criteria are authoritative when they
are more concrete than the general descriptions.

Be calibrated, not generous: reserve 5 for responses with no meaningful flaw.
Score what the response actually contains, not what it intended. If the response
is in Chinese, judge it as a native Chinese business reader would.

Return only a JSON object with exactly this shape and no other text:

{"scores": {"task_completion": <int 1-5>, "reasoning_quality": <int 1-5>, "instruction_following": <int 1-5>}, "rationale": "<one or two sentences citing the specific criteria that were met or missed>"}
"""


def build_judge_messages(
    case: dict, candidate: dict, judge_model: dict, response_text: str
) -> list[dict]:
    criteria = "\n".join(f"- {item}" for item in case["evaluation_criteria"])
    user_content = f"""\
## Test case

Case ID: {case['id']}
Domain: {case['domain']}
Difficulty: {case.get('difficulty')}
Language: {case.get('language')}
Title: {case.get('title', '')}

### Prompt given to the candidate model

{case['prompt']}

### Case-specific evaluation criteria

{criteria}

## Candidate response under evaluation

Candidate model: {candidate['display_name']}
Evaluating judge: {judge_model['display_name']}

```
{response_text}
```

Score the candidate response on the three rubric dimensions and return the JSON object.
"""
    return [
        {"role": "system", "content": RUBRIC_TEXT},
        {"role": "user", "content": user_content},
    ]


# --------------------------------------------------------------------------
# Judge selection
# --------------------------------------------------------------------------


def eligible_judges(candidate: dict, judge_pool: list[dict]) -> list[dict]:
    """Judges that do not share the candidate's model family or provider."""
    return [
        judge
        for judge in judge_pool
        if judge["model_family"] != candidate["model_family"]
        and judge["provider_key"] != candidate["provider_key"]
    ]


def order_judges(judge_pool: list[dict], priority: list[str] | tuple[str, ...]) -> list[dict]:
    """Order the judge pool by the configured fixed priority list.

    Judges named in `priority` come first in that exact order. Any judge not
    listed follows, ordered by key, so the result is always total and stable.
    """
    index = {key: position for position, key in enumerate(priority)}
    fallback = len(index)
    return sorted(
        judge_pool,
        key=lambda model: (index.get(model["key"], fallback), model["key"]),
    )


def select_judges(
    candidate: dict,
    judge_pool: list[dict],
    priority: list[str] | tuple[str, ...] = (),
    count: int = config.JUDGES_PER_RESPONSE,
) -> list[dict]:
    """Select exactly `count` cross-family judges for one candidate.

    Selection is deterministic and configuration-driven:

    1. order the judge pool by the fixed priority list,
    2. drop judges sharing the candidate's model family or provider key,
    3. take the first two remaining judges, skipping any whose family is already
       represented so the pair is always cross-family.

    There is no per-candidate hashing or rotation: unrelated candidates are not
    evaluated by different judge pairs. Returns an empty list when fewer than
    `count` eligible cross-family judges remain. A same-family judge is never
    substituted merely to obtain a second score; the caller records that response
    as judge-unavailable instead.
    """
    ordered = order_judges(judge_pool, priority)
    eligible = [
        judge
        for judge in ordered
        if judge["model_family"] != candidate["model_family"]
        and judge["provider_key"] != candidate["provider_key"]
    ]
    if len(eligible) < count:
        return []

    selected: list[dict] = []
    used_families: set[str] = set()
    for judge in eligible:
        if len(selected) == count:
            break
        if judge["model_family"] in used_families:
            continue
        selected.append(judge)
        used_families.add(judge["model_family"])

    return selected if len(selected) == count else []


# --------------------------------------------------------------------------
# Strict parsing
# --------------------------------------------------------------------------


def parse_judge_output(raw_text: str) -> dict:
    """Strictly parse and validate judge output. Never repairs invalid scores."""
    cleaned = (raw_text or "").strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if fenced:
        cleaned = fenced.group(1).strip()

    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise JudgeOutputError(
            f"Judge output contained no JSON object. Raw output: {raw_text[:300]!r}"
        )

    try:
        payload = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise JudgeOutputError(
            f"Judge output is not valid JSON: {exc}. Raw output: {raw_text[:300]!r}"
        ) from exc

    if not isinstance(payload, dict):
        raise JudgeOutputError(f"Judge output must be a JSON object, got {type(payload).__name__}.")

    scores = payload.get("scores")
    if not isinstance(scores, dict):
        raise JudgeOutputError("Judge output is missing a 'scores' object.")

    missing = [dim for dim in config.RUBRIC_DIMENSIONS if dim not in scores]
    if missing:
        raise JudgeOutputError(f"Judge output is missing rubric dimensions: {missing}.")

    unexpected = [key for key in scores if key not in config.RUBRIC_DIMENSIONS]
    if unexpected:
        raise JudgeOutputError(f"Judge output contains unexpected dimensions: {unexpected}.")

    for dimension in config.RUBRIC_DIMENSIONS:
        value = scores[dimension]
        if isinstance(value, bool) or not isinstance(value, int):
            raise JudgeOutputError(
                f"Score for '{dimension}' must be an integer, got {value!r} "
                f"({type(value).__name__})."
            )
        if not config.SCORE_MIN <= value <= config.SCORE_MAX:
            raise JudgeOutputError(
                f"Score for '{dimension}' must be between {config.SCORE_MIN} and "
                f"{config.SCORE_MAX}, got {value}."
            )

    rationale = payload.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        raise JudgeOutputError("Judge output must include a non-empty 'rationale' string.")

    mean_score = sum(scores[dim] for dim in config.RUBRIC_DIMENSIONS) / len(config.RUBRIC_DIMENSIONS)
    normalized = (mean_score - config.SCORE_MIN) / (config.SCORE_MAX - config.SCORE_MIN) * 100

    return {
        "scores": {dim: scores[dim] for dim in config.RUBRIC_DIMENSIONS},
        "rationale": rationale.strip(),
        "mean_score": round(mean_score, 3),
        "normalized_score": round(normalized, 2),
    }


def _synthetic_judge_output(case: dict, candidate: dict, judge_model: dict) -> str:
    """Deterministic strict-JSON judge output for --dry-run only."""
    digest = hashlib.sha256(
        f"{case['id']}|{candidate['key']}|{judge_model['key']}".encode("utf-8")
    ).hexdigest()
    number = int(digest[:8], 16)
    scores = {
        dimension: 2 + (number >> (index * 3)) % 4
        for index, dimension in enumerate(config.RUBRIC_DIMENSIONS)
    }
    return json.dumps(
        {
            "scores": scores,
            "rationale": (
                "Synthetic dry-run rationale. Deterministic placeholder for pipeline "
                f"validation of case {case['id']}; not a real evaluation."
            ),
        }
    )


# --------------------------------------------------------------------------
# Evaluation
# --------------------------------------------------------------------------


def _evaluate_one(
    case: dict,
    candidate: dict,
    judge_model: dict,
    response_text: str,
    *,
    dry_run: bool,
    fx_snapshot: dict | None,
) -> dict:
    messages = build_judge_messages(case, candidate, judge_model, response_text)
    record = {
        "judge_key": judge_model["key"],
        "judge_display_name": judge_model["display_name"],
        "judge_family": judge_model["model_family"],
        "judge_provider": judge_model["provider"],
        "judge_prompt_version": config.JUDGE_PROMPT_VERSION,
        "scores": None,
        "rationale": None,
        "mean_score": None,
        "normalized_score": None,
        "error": None,
    }

    try:
        if dry_run:
            call = providers.synthetic_call(
                judge_model,
                messages,
                seed=f"judge|{case['id']}|{judge_model['key']}",
                fx_snapshot=fx_snapshot,
            )
            call["text"] = _synthetic_judge_output(case, candidate, judge_model)
        else:
            call = providers.chat(judge_model, messages, fx_snapshot=fx_snapshot)
    except providers.ProviderError as exc:
        record["error"] = f"provider: {exc}"
        return record

    try:
        verdict = parse_judge_output(call["text"])
    except JudgeOutputError as exc:
        record["error"] = f"invalid judge output: {exc}"
        return record

    record.update(verdict)
    record.update(
        {
            "input_tokens": call["input_tokens"],
            "output_tokens": call["output_tokens"],
            "total_tokens": call["total_tokens"],
            "reasoning_tokens": call.get("reasoning_tokens"),
            "latency_ms": call["latency_ms"],
            "native_cost": call["native_cost"],
            "native_currency": call["native_currency"],
            "normalized_cost_cny": call["normalized_cost_cny"],
            "normalization_method": call["normalization_method"],
            "cost_basis": call["basis"],
            "cost_error": call["cost_error"],
            "called_at": call["called_at"],
            "synthetic": call["synthetic"],
        }
    )
    return record


def evaluate(
    case: dict,
    candidate: dict,
    response_text: str,
    judge_models: list[dict],
    *,
    dry_run: bool,
    fx_snapshot: dict | None,
) -> list[dict]:
    """Run every selected judge on one candidate response."""
    return [
        _evaluate_one(
            case,
            candidate,
            judge_model,
            response_text,
            dry_run=dry_run,
            fx_snapshot=fx_snapshot,
        )
        for judge_model in judge_models
    ]


# --------------------------------------------------------------------------
# Aggregation
# --------------------------------------------------------------------------


def aggregate_verdicts(verdicts: list[dict]) -> dict:
    """Combine judge verdicts into one score for a candidate response."""
    valid = [
        verdict
        for verdict in verdicts
        if verdict.get("scores") and verdict.get("error") is None
    ]
    if not valid:
        return {
            "judges_valid": 0,
            "judges_total": len(verdicts),
            "dimension_scores": {dim: None for dim in config.RUBRIC_DIMENSIONS},
            "quality_score": None,
            "overall_score": None,
        }

    dimension_scores = {
        dimension: round(
            sum(verdict["scores"][dimension] for verdict in valid) / len(valid), 3
        )
        for dimension in config.RUBRIC_DIMENSIONS
    }
    quality_score = round(
        sum(dimension_scores.values()) / len(config.RUBRIC_DIMENSIONS), 3
    )
    overall = (quality_score - config.SCORE_MIN) / (config.SCORE_MAX - config.SCORE_MIN) * 100

    return {
        "judges_valid": len(valid),
        "judges_total": len(verdicts),
        "dimension_scores": dimension_scores,
        "quality_score": quality_score,
        "overall_score": round(overall, 2),
    }


def judge_agreement(verdicts: list[dict]) -> dict | None:
    """Agreement between two or more judges on the same response.

    Returns None when fewer than two judges produced a valid verdict, rather
    than reporting a fabricated agreement figure.
    """
    valid = [
        verdict
        for verdict in verdicts
        if verdict.get("scores") and verdict.get("error") is None
    ]
    if len(valid) < 2:
        return None

    per_dimension = {}
    for dimension in config.RUBRIC_DIMENSIONS:
        values = [verdict["scores"][dimension] for verdict in valid]
        per_dimension[dimension] = {
            "mean_abs_difference": round(
                (max(values) - min(values)), 3
            ),
            "exact_match": len(set(values)) == 1,
        }

    mean_scores = [verdict["mean_score"] for verdict in valid]
    return {
        "judges": len(valid),
        "overall_mean_abs_difference": round(max(mean_scores) - min(mean_scores), 3),
        "per_dimension": per_dimension,
    }
