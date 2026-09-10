"""Case loading and V1 schema validation.

Canonical references: docs/METHODOLOGY_V1.md §1 and
docs/CASE_DESIGN_STANDARD_V1.md.

The production 50-case dataset is a Phase 3B deliverable. Until then the
validator runs against synthetic fixtures; it does not require the production
size to be present, but it enforces the full production schema so fixtures and
production cases cannot drift apart.
"""

from __future__ import annotations

import json
from pathlib import Path

from src import config

REQUIRED_FIELDS = (
    "id",
    "title",
    "domain",
    "difficulty",
    "language",
    "test_intent",
    "prompt",
    "evaluation_criteria",
    "tags",
)

# Word counting splits on whitespace, which is meaningless for Chinese text.
WORD_COUNT_CHECKS = ("max_words", "min_words")

# Languages for which a whitespace word count is a valid length measure.
WORD_COUNT_LANGUAGES = ("en",)


def load_cases(path: Path | None = None) -> dict:
    path = path or config.DEFAULT_CASES_FILE
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def all_cases(document: dict) -> list[dict]:
    return document.get("test_cases") or []


def validate_cases(document: dict) -> dict:
    """Return {"errors": [...], "warnings": [...]}."""
    errors: list[str] = []
    warnings: list[str] = []

    cases = document.get("test_cases")
    if not isinstance(cases, list) or not cases:
        return {"errors": ["A case file must contain a non-empty 'test_cases' list."], "warnings": []}

    seen_ids: set[str] = set()
    for index, case in enumerate(cases):
        label = case.get("id") or f"index {index}"

        for field in REQUIRED_FIELDS:
            if case.get(field) in (None, "", []):
                errors.append(f"Case {label} is missing a non-empty '{field}'.")

        case_id = case.get("id")
        if case_id in seen_ids:
            errors.append(f"Duplicate case id: {case_id}.")
        seen_ids.add(case_id)

        domain = case.get("domain")
        if domain and domain not in config.DOMAINS:
            errors.append(
                f"Case {label} has domain '{domain}'; expected one of {list(config.DOMAINS)}."
            )

        difficulty = case.get("difficulty")
        if difficulty and difficulty not in config.DIFFICULTIES:
            errors.append(
                f"Case {label} has difficulty '{difficulty}'; "
                f"expected one of {list(config.DIFFICULTIES)}."
            )

        language = case.get("language")
        if language and language not in config.LANGUAGES:
            errors.append(
                f"Case {label} has language '{language}'; expected one of {list(config.LANGUAGES)}."
            )

        criteria = case.get("evaluation_criteria")
        if criteria is not None and (not isinstance(criteria, list) or not criteria):
            errors.append(f"Case {label} must have a non-empty 'evaluation_criteria' list.")

        tags = case.get("tags")
        if tags is not None and (not isinstance(tags, list) or not tags):
            errors.append(f"Case {label} must have a non-empty 'tags' list.")

        checks = case.get("deterministic_checks")
        if checks is not None:
            if not isinstance(checks, list):
                errors.append(f"Case {label} 'deterministic_checks' must be a list.")
            else:
                for check_index, check in enumerate(checks):
                    if not isinstance(check, dict) or not check.get("type"):
                        errors.append(
                            f"Case {label} deterministic check {check_index} must be an object "
                            "with a 'type'."
                        )
                errors.extend(_validate_length_checks(case, checks, label))

    present_domains = {case.get("domain") for case in cases if case.get("domain")}
    missing_domains = [domain for domain in config.DOMAINS if domain not in present_domains]
    if missing_domains:
        warnings.append(
            f"No case covers these configured domains yet: {missing_domains}. "
            "The production dataset must cover all five."
        )

    if len(cases) != config.TARGET_CASES:
        warnings.append(
            f"Case count is {len(cases)}; the V1 production target is {config.TARGET_CASES}. "
            "This is expected until the Phase 3 dataset exists."
        )

    if document.get("synthetic"):
        warnings.append(str(document.get("synthetic_notice", "This case file is synthetic.")))

    return {"errors": errors, "warnings": warnings}


def _validate_length_checks(case: dict, checks: list, label: str) -> list[str]:
    """Enforce the language rule for whitespace word-count constraints.

    `max_words` / `min_words` count whitespace-separated tokens. That is a valid
    length measure for English and a meaningless one for Chinese, where words
    are not whitespace-delimited. Chinese cases must use `max_chars` /
    `min_chars`. Mixed-language cases may use word counts only with an explicit
    author justification recorded on the case.
    """
    language = case.get("language")
    word_checks = [
        check.get("type") for check in checks if check.get("type") in WORD_COUNT_CHECKS
    ]
    if not word_checks:
        return []

    if language in WORD_COUNT_LANGUAGES:
        return []

    if language == "zh":
        return [
            f"Case {label} is Chinese (language 'zh') but declares word-count checks "
            f"{sorted(set(word_checks))}. Whitespace word counts are meaningless for Chinese; "
            "use 'max_chars' / 'min_chars' instead."
        ]

    if language == "mixed":
        justification = case.get("word_count_justification")
        if not isinstance(justification, str) or not justification.strip():
            return [
                f"Case {label} is mixed-language and declares word-count checks "
                f"{sorted(set(word_checks))}. Mixed cases require an explicit "
                "'word_count_justification' explaining why a whitespace word count is "
                "valid for the expected answer."
            ]
    return []


def distribution(cases: list[dict], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for case in cases:
        value = case.get(field)
        if value:
            counts[value] = counts.get(value, 0) + 1
    return counts


def domain_distribution(cases: list[dict]) -> dict[str, int]:
    counts = {domain: 0 for domain in config.DOMAINS}
    for case in cases:
        domain = case.get("domain")
        if domain in counts:
            counts[domain] += 1
    return counts


def case_index(cases: list[dict]) -> dict[str, dict]:
    return {case["id"]: case for case in cases}
