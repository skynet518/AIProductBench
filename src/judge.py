"""The single LLM-as-Judge.

One judge evaluates every candidate response against two inputs at once: the
shared three-dimension rubric and the case-level evaluation criteria. Output
must be strict, machine-readable JSON.

Invalid judge output is never repaired. If a score is out of range, missing,
misnamed, or not an integer, the judge call is reported as a failure so the
result is visibly incomplete rather than silently plausible.
"""

from __future__ import annotations

import json
import re

from src import config, providers


class JudgeOutputError(ValueError):
    """Raised when judge output cannot be parsed and validated strictly."""


RUBRIC_TEXT = """\
You are a strict evaluator of AI assistant responses for an AI product team.

Score the candidate response on exactly these three dimensions:

1. task_completion — Did the response fully do what the case asked for, using only
   the information given, without inventing facts?
2. instruction_following — Did the response obey every explicit constraint in the
   case, including format, length, structure, and negative constraints?
3. quality_usefulness — Would an experienced product manager find this response
   genuinely useful, specific, and decision-ready?

Scale for every dimension: an integer from 1 to 5.
5 = excellent, no meaningful flaw.
4 = good, minor flaw.
3 = acceptable, a clear flaw that a reviewer would need to fix.
2 = poor, a major flaw or a missed requirement.
1 = unusable or not responsive.

Judge against both the shared rubric above and the case-specific evaluation
criteria you are given. The case-specific criteria are authoritative when they
are more concrete than the general descriptions.

Be calibrated, not generous: reserve 5 for responses with no meaningful flaw.
Score on what the response actually contains, not on what it intended.

Return only a JSON object with exactly this shape and no other text:

{"scores": {"task_completion": <int 1-5>, "instruction_following": <int 1-5>, "quality_usefulness": <int 1-5>}, "rationale": "<one or two sentences citing the specific criteria that were met or missed>"}
"""


def build_judge_messages(case: dict, model_name: str, response_text: str) -> list[dict]:
    criteria = "\n".join(f"- {item}" for item in case["evaluation_criteria"])
    user_content = f"""\
## Test case

Case ID: {case['id']}
Domain: {case['domain']}
Title: {case['title']}

### Prompt given to the candidate model

{case['prompt']}

### Case-specific evaluation criteria

{criteria}

## Candidate response under evaluation

Candidate model: {model_name}

```
{response_text}
```

Score the candidate response on the three rubric dimensions and return the JSON object.
"""
    return [
        {"role": "system", "content": RUBRIC_TEXT},
        {"role": "user", "content": user_content},
    ]


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


def _synthetic_judge_output(case: dict, model_name: str) -> str:
    """Deterministic strict-JSON judge output for --dry-run only."""
    import hashlib

    digest = hashlib.sha256(f"{case['id']}|{model_name}".encode("utf-8")).hexdigest()
    number = int(digest[:8], 16)
    scores = {
        dimension: 2 + (number >> (index * 3)) % 4
        for index, dimension in enumerate(config.RUBRIC_DIMENSIONS)
    }
    payload = {
        "scores": scores,
        "rationale": (
            "Synthetic dry-run rationale. Deterministic placeholder for pipeline "
            f"validation of case {case['id']}; not a real evaluation."
        ),
    }
    return json.dumps(payload)


def evaluate(case: dict, model_name: str, response_text: str, *, dry_run: bool = False) -> dict:
    """Run the single judge on one response and return the validated verdict."""
    messages = build_judge_messages(case, model_name, response_text)

    if dry_run:
        call = providers.synthetic_call(config.JUDGE, messages, seed=f"judge|{case['id']}")
        call["text"] = _synthetic_judge_output(case, model_name)
    else:
        call = providers.chat(config.JUDGE, messages)

    verdict = parse_judge_output(call["text"])
    verdict.update(
        {
            "input_tokens": call["input_tokens"],
            "output_tokens": call["output_tokens"],
            "total_tokens": call["total_tokens"],
            "estimated_cost_usd": call["estimated_cost_usd"],
            "cost_basis": call.get("cost_basis"),
            "cost_error": call.get("cost_error"),
            "called_at": call.get("called_at"),
            "latency_ms": call["latency_ms"],
            "judge_model": config.JUDGE["model"],
            "judge_prompt_version": config.JUDGE_PROMPT_VERSION,
            "synthetic": call["synthetic"],
        }
    )
    return verdict
