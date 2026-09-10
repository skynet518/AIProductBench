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

import difflib
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


BULLET_LINE_RE = re.compile(r"^\s*-\s+")


def _isolate_section(check: dict, text: str) -> tuple[str | None, str | None]:
    """Return (body, error) for a section-marker check.

    Shared semantics for `section_max_chars` and `section_bullet_count`:

    - `start_marker` is required and must occur exactly once.
    - `end_marker` is optional (`null`); a non-null end marker must occur
      exactly once and after the start marker.
    - the body is the text after the start marker and before the end marker,
      or to end-of-response when `end_marker` is null.
    - only surrounding whitespace is stripped; nothing else is normalized.

    Malformed, missing, duplicate, or out-of-order markers return an error
    rather than raising, so a bad declaration or an unexpected response fails
    the check safely instead of crashing the evaluator.
    """
    start_marker = check.get("start_marker")
    if not isinstance(start_marker, str) or start_marker == "":
        return None, "start_marker is missing or not a non-empty string"
    if text.count(start_marker) != 1:
        return None, f"start_marker {start_marker!r} must occur exactly once"
    start = text.index(start_marker) + len(start_marker)

    end_marker = check.get("end_marker")
    if end_marker is None:
        return text[start:].strip(), None
    if not isinstance(end_marker, str) or end_marker == "":
        return None, "end_marker must be null or a non-empty string"
    if text.count(end_marker) != 1:
        return None, f"end_marker {end_marker!r} must occur exactly once"
    end = text.index(end_marker)
    if end < start:
        return None, "end_marker occurs before start_marker"
    return text[start:end].strip(), None


# --------------------------------------------------------------------------
# Declaration validation
#
# Every operator's parameter contract is derived from `_run_check` below and
# declared once, centrally, in `_DECLARATIONS`. Dataset validation calls
# `validate_check_declaration`, so a malformed declaration fails before any
# run rather than surfacing as a silent runtime failure. This does not change
# any operator's runtime semantics.
# --------------------------------------------------------------------------

SUPPORTED_CHECK_TYPES = frozenset(
    {
        "valid_json",
        "required_keys",
        "forbidden_keys",
        "exact_keys",
        "exact_item_count",
        "max_items",
        "min_items",
        "max_words",
        "min_words",
        "max_chars",
        "min_chars",
        "exact_bullet_count",
        "section_max_chars",
        "section_bullet_count",
        "required_phrases",
        "forbidden_phrases",
        "ordering",
        "forbidden_regex",
        "required_regex",
        "no_markdown_fence",
        "numeric_range",
    }
)


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _count_error(value, *, positive: bool) -> str | None:
    if not _is_int(value):
        return f"must be an integer, got {type(value).__name__}"
    if positive and value <= 0:
        return "must be a positive integer (> 0)"
    if not positive and value < 0:
        return "must be a non-negative integer (>= 0)"
    return None


def _nonempty_string_error(value) -> str | None:
    if not isinstance(value, str):
        return f"must be a string, got {type(value).__name__}"
    if value == "":
        return "must be a non-empty string"
    return None


def _end_marker_error(value) -> str | None:
    if value is None:
        return None
    return _nonempty_string_error(value)


def _regex_error(value) -> str | None:
    error = _nonempty_string_error(value)
    if error:
        return error
    try:
        re.compile(value)
    except re.error as exc:
        return f"is not a valid regex: {exc}"
    return None


def _capture_regex_error(value) -> str | None:
    """`numeric_range.pattern` is read through `match.group(1)` at runtime."""
    error = _regex_error(value)
    if error:
        return error
    if re.compile(value).groups < 1:
        return "must contain at least one capture group (group 1 is read at runtime)"
    return None


def _string_list_error(value) -> str | None:
    if not isinstance(value, list):
        return f"must be a list of strings, got {type(value).__name__}"
    if not value:
        return "must be a non-empty list"
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            return f"must contain only strings, found {type(item).__name__}"
        if item == "":
            return "must not contain empty strings"
        if item in seen:
            return f"must not contain duplicate entries ({item!r})"
        seen.add(item)
    return None


def _bool_error(value) -> str | None:
    if not isinstance(value, bool):
        return f"must be a boolean, got {type(value).__name__}"
    return None


def _number_error(value) -> str | None:
    if not _is_number(value):
        return f"must be a number, got {type(value).__name__}"
    return None


def _expect_error(value) -> str | None:
    if value not in ("object", "array"):
        return "must be 'object' or 'array'"
    return None


def _section_cross_errors(check: dict) -> list[str]:
    start, end = check.get("start_marker"), check.get("end_marker")
    if isinstance(start, str) and isinstance(end, str) and start == end:
        return ["'end_marker' must differ from 'start_marker'"]
    return []


def _numeric_range_cross_errors(check: dict) -> list[str]:
    low, high = check.get("min"), check.get("max")
    if _is_number(low) and _is_number(high) and low > high:
        return ["'min' must be less than or equal to 'max'"]
    return []


_NON_NEGATIVE_COUNT = {"count": lambda value: _count_error(value, positive=False)}
_POSITIVE_COUNT = {"count": lambda value: _count_error(value, positive=True)}

# `required` fields must be present and valid; `optional` fields are checked
# only when present. `name` and `type` are always permitted on every operator.
_DECLARATIONS: dict[str, dict] = {
    "valid_json": {"optional": {"expect": _expect_error}},
    "required_keys": {"required": {"keys": _string_list_error}},
    "forbidden_keys": {"required": {"keys": _string_list_error}},
    "exact_keys": {"required": {"keys": _string_list_error}},
    "exact_item_count": {"required": dict(_NON_NEGATIVE_COUNT)},
    "max_items": {"required": dict(_NON_NEGATIVE_COUNT)},
    "min_items": {"required": dict(_NON_NEGATIVE_COUNT)},
    "max_words": {"required": dict(_NON_NEGATIVE_COUNT)},
    "min_words": {"required": dict(_NON_NEGATIVE_COUNT)},
    "max_chars": {"required": dict(_NON_NEGATIVE_COUNT)},
    "min_chars": {"required": dict(_NON_NEGATIVE_COUNT)},
    "exact_bullet_count": {"required": dict(_NON_NEGATIVE_COUNT)},
    "section_max_chars": {
        "required": {
            "start_marker": _nonempty_string_error,
            "end_marker": _end_marker_error,
            **dict(_POSITIVE_COUNT),
        },
        "cross": _section_cross_errors,
    },
    "section_bullet_count": {
        "required": {
            "start_marker": _nonempty_string_error,
            "end_marker": _end_marker_error,
            **dict(_NON_NEGATIVE_COUNT),
        },
        "cross": _section_cross_errors,
    },
    "required_phrases": {
        "required": {"phrases": _string_list_error},
        "optional": {"case_sensitive": _bool_error},
    },
    "forbidden_phrases": {
        "required": {"phrases": _string_list_error},
        "optional": {"case_sensitive": _bool_error},
    },
    "ordering": {"required": {"phrases": _string_list_error}},
    "forbidden_regex": {"required": {"pattern": _regex_error}},
    "required_regex": {"required": {"pattern": _regex_error}},
    "no_markdown_fence": {},
    "numeric_range": {
        "optional": {
            "pattern": _capture_regex_error,
            "min": _number_error,
            "max": _number_error,
        },
        "cross": _numeric_range_cross_errors,
    },
}


def validate_check_declaration(check) -> list[str]:
    """Return declaration errors for one `deterministic_checks` entry.

    Messages are fragments meant to follow a caller-supplied "Case <id>
    deterministic check <i>" prefix. An empty list means the declaration is
    well-formed for its operator.
    """
    if not isinstance(check, dict):
        return ["must be an object with a 'type'"]

    kind = check.get("type")
    if kind is None:
        return ["is missing a 'type'"]
    if not isinstance(kind, str):
        return [f"'type' must be a string, got {type(kind).__name__}"]
    if kind not in SUPPORTED_CHECK_TYPES:
        message = f"uses unsupported check type {kind!r}"
        suggestion = difflib.get_close_matches(kind, sorted(SUPPORTED_CHECK_TYPES), n=1)
        if suggestion:
            message += f"; did you mean {suggestion[0]!r}?"
        return [message]

    spec = _DECLARATIONS[kind]
    required = spec.get("required", {})
    optional = spec.get("optional", {})
    allowed = set(required) | set(optional) | {"type", "name"}
    errors: list[str] = []

    if "name" in check:
        error = _nonempty_string_error(check["name"])
        if error:
            errors.append(f"'name' {error}")

    for field, validate in required.items():
        if field not in check:
            errors.append(f"is missing required field {field!r}")
            continue
        error = validate(check[field])
        if error:
            errors.append(f"{field!r} {error}")

    for field, validate in optional.items():
        if field not in check:
            continue
        error = validate(check[field])
        if error:
            errors.append(f"{field!r} {error}")

    for field in check:
        if field in allowed:
            continue
        message = f"has an unexpected field {field!r}"
        suggestion = difflib.get_close_matches(field, sorted(allowed), n=1)
        if suggestion:
            message += f"; did you mean {suggestion[0]!r}?"
        errors.append(message)

    cross = spec.get("cross")
    if cross:
        errors.extend(cross(check))
    return errors


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

    if kind == "exact_keys":
        value, error = extract_json(text)
        if error:
            return False, error
        if not isinstance(value, dict):
            return False, "expected a JSON object"
        declared = set(check.get("keys") or [])
        actual = set(value.keys())
        if actual == declared:
            return True, f"exactly {len(declared)} key(s) present"
        missing = sorted(declared - actual)
        extra = sorted(actual - declared)
        parts = []
        if missing:
            parts.append(f"missing keys: {missing}")
        if extra:
            parts.append(f"extra keys: {extra}")
        return False, "; ".join(parts)

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

    if kind == "section_max_chars":
        body, error = _isolate_section(check, text)
        if error:
            return False, error
        expected = check.get("count")
        if not isinstance(expected, int):
            return False, "count is missing or not an integer"
        actual = len(body)
        return actual <= expected, f"{actual} character(s) in section, maximum {expected}"

    if kind == "section_bullet_count":
        body, error = _isolate_section(check, text)
        if error:
            return False, error
        expected = check.get("count")
        if not isinstance(expected, int):
            return False, "count is missing or not an integer"
        actual = sum(1 for line in body.splitlines() if BULLET_LINE_RE.match(line))
        return actual == expected, f"{actual} bullet(s) in section, expected {expected}"

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
