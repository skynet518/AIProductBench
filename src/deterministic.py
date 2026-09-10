"""Deterministic constraint checking.

Checks run wherever a case constraint is objectively machine-verifiable. They
never judge subjective quality and they never override LLM judgment; the two
signals are reported side by side.

Note on length checks: `max_words` counts whitespace-separated tokens, which is
appropriate for English text but under-counts Chinese text, where words are not
whitespace-delimited. Case authors writing Chinese-first cases should express
length limits with `max_chars` instead.
"""

from __future__ import annotations

import json
import re


def _strip_fence(text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    return fenced.group(1).strip() if fenced else text.strip()


def extract_json(text: str):
    """Return (value, error). Extracts the first JSON object or array found."""
    cleaned = _strip_fence(text or "")
    for opener, closer in (("{", "}"), ("[", "]")):
        start, end = cleaned.find(opener), cleaned.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1]), None
            except json.JSONDecodeError as exc:
                return None, f"invalid JSON: {exc.msg}"
    return None, "no JSON object or array found"


def _words(text: str) -> list[str]:
    return text.split()


def _bullets(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip().startswith(("-", "*", "•"))]


def _run_check(check: dict, text: str) -> tuple[bool, str]:
    kind = check.get("type")

    if kind == "valid_json":
        value, error = extract_json(text)
        if error:
            return False, error
        expect = check.get("expect")
        if expect == "object" and not isinstance(value, dict):
            return False, f"expected a JSON object, got {type(value).__name__}"
        if expect == "array" and not isinstance(value, list):
            return False, f"expected a JSON array, got {type(value).__name__}"
        return True, "valid JSON"

    if kind in ("required_keys", "forbidden_keys"):
        value, error = extract_json(text)
        if error:
            return False, error
        if not isinstance(value, dict):
            return False, "expected a JSON object"
        keys = check.get("keys") or []
        present = [key for key in keys if key in value]
        if kind == "required_keys":
            missing = [key for key in keys if key not in value]
            return (not missing), (f"missing keys: {missing}" if missing else f"all {len(keys)} keys present")
        unexpected = present
        return (not unexpected), (f"forbidden keys present: {unexpected}" if unexpected else "no forbidden keys")

    if kind in ("exact_item_count", "max_items", "min_items"):
        value, error = extract_json(text)
        if error:
            return False, error
        if not isinstance(value, list):
            return False, "expected a JSON array"
        expected = check.get("count")
        actual = len(value)
        if kind == "exact_item_count":
            return actual == expected, f"{actual} item(s), expected {expected}"
        if kind == "max_items":
            return actual <= expected, f"{actual} item(s), maximum {expected}"
        return actual >= expected, f"{actual} item(s), minimum {expected}"

    if kind in ("max_words", "min_words"):
        expected = check.get("count")
        actual = len(_words(text))
        if kind == "max_words":
            return actual <= expected, f"{actual} word(s), maximum {expected}"
        return actual >= expected, f"{actual} word(s), minimum {expected}"

    if kind in ("max_chars", "min_chars"):
        expected = check.get("count")
        actual = len(text)
        if kind == "max_chars":
            return actual <= expected, f"{actual} character(s), maximum {expected}"
        return actual >= expected, f"{actual} character(s), minimum {expected}"

    if kind == "exact_bullet_count":
        expected = check.get("count")
        actual = len(_bullets(text))
        return actual == expected, f"{actual} bullet(s), expected {expected}"

    if kind in ("required_phrases", "forbidden_phrases"):
        phrases = check.get("phrases") or []
        haystack = text if check.get("case_sensitive") else text.lower()
        found, missing = [], []
        for phrase in phrases:
            needle = phrase if check.get("case_sensitive") else phrase.lower()
            (found if needle in haystack else missing).append(phrase)
        if kind == "required_phrases":
            return (not missing), (f"missing phrases: {missing}" if missing else f"all {len(phrases)} phrase(s) present")
        return (not found), (f"forbidden phrases present: {found}" if found else "no forbidden phrases")

    if kind == "ordering":
        phrases = check.get("phrases") or []
        position = -1
        for phrase in phrases:
            found_at = text.find(phrase, position + 1)
            if found_at == -1:
                return False, f"'{phrase}' not found after the previous item"
            position = found_at
        return True, f"{len(phrases)} phrase(s) in order"

    if kind == "forbidden_regex":
        pattern = check.get("pattern") or ""
        match = re.search(pattern, text)
        return (match is None), (f"matched forbidden pattern: {match.group(0)!r}" if match else "no match")

    if kind == "required_regex":
        pattern = check.get("pattern") or ""
        match = re.search(pattern, text)
        return (match is not None), (f"matched {match.group(0)!r}" if match else "pattern not found")

    if kind == "no_markdown_fence":
        present = "```" in text
        return (not present), ("markdown fence present" if present else "no markdown fence")

    if kind == "numeric_range":
        pattern = check.get("pattern") or r"(-?\d+(?:\.\d+)?)"
        match = re.search(pattern, text)
        if not match:
            return False, "no number found"
        try:
            value = float(match.group(1))
        except (IndexError, ValueError):
            return False, "capture group 1 is not numeric"
        low, high = check.get("min"), check.get("max")
        if low is not None and value < low:
            return False, f"{value} is below {low}"
        if high is not None and value > high:
            return False, f"{value} is above {high}"
        return True, f"{value} within range"

    return False, f"unsupported check type: {kind!r}"


def evaluate(case: dict, response_text: str) -> dict:
    """Run every deterministic check declared by a case.

    Returns a per-check record plus the case-level `constraint_pass_rate`. A
    case with no deterministic checks reports `None`, never a fabricated 1.0.
    """
    checks = case.get("deterministic_checks") or []
    text = response_text or ""
    results = []

    for check in checks:
        passed, detail = _run_check(check, text)
        results.append(
            {
                "name": check.get("name") or check.get("type"),
                "type": check.get("type"),
                "passed": passed,
                "detail": detail,
            }
        )

    total = len(results)
    passed_count = sum(1 for item in results if item["passed"])
    return {
        "checks": results,
        "checks_passed": passed_count,
        "checks_total": total,
        "constraint_pass_rate": round(passed_count / total, 4) if total else None,
        "all_passed": (passed_count == total) if total else None,
    }
