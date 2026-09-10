"""Configurable model pool for AIProductBench CN V1.

The candidate and judge pools are data, not code. Nothing in the benchmark
pipeline may branch on a specific model name; it reads these entries instead.

An entry distinguishes MODEL FAMILY (who trained the model) from INFERENCE
PROVIDER / CHANNEL (who serves it), because the same family reached through a
different channel has different latency, price, and reliability.
"""

from __future__ import annotations

import json
from pathlib import Path

from src import config

REQUIRED_FIELDS = (
    "key",
    "display_name",
    "model_family",
    "provider",
    "provider_key",
    "product_tier",
    "inference_channel",
    "thinking_mode",
    "model_id_status",
    "base_url",
    "api_key_env",
    "wire_api",
    "temperature",
)

PRODUCT_TIERS = ("flagship", "balanced", "value")
THINKING_MODES = ("disabled", "enabled", "provider_default")
WIRE_APIS = ("chat_completions", "responses")


def load_model_pool(path: Path | None = None) -> dict:
    path = path or config.MODEL_POOL_FILE
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def candidates(pool: dict) -> list[dict]:
    return [model for model in pool["models"] if model.get("candidate")]


def judges(pool: dict) -> list[dict]:
    return [model for model in pool["models"] if model.get("judge_eligible")]


def judge_priority(pool: dict) -> list[str]:
    """Fixed judge priority order, declared in the pool configuration.

    Selection follows this list; it is never derived from a candidate hash.
    """
    return list(pool.get("judge_priority") or [])


def historical_pricing(pool: dict) -> dict:
    """Retired V0.1-era pricing. Historical reference only; never used for V1 cost."""
    archive = pool.get("historical_pricing_archive") or {}
    return archive if isinstance(archive, dict) else {}


def archived_pricing_model_ids(pool: dict) -> set[str]:
    """Model IDs that only ever had historical (V0.1-era) pricing attached."""
    return {
        entry.get("applies_to_model_id")
        for entry in (historical_pricing(pool).get("entries") or [])
        if entry.get("applies_to_model_id")
    }


def by_key(pool: dict, key: str) -> dict:
    for model in pool["models"]:
        if model["key"] == key:
            return model
    raise KeyError(f"Unknown model key: {key}")


def validate_model_pool(pool: dict) -> dict:
    """Return {"errors": [...], "warnings": [...]}. Canonical V1 sources: docs/ARCHITECTURE.md §4."""
    errors: list[str] = []
    warnings: list[str] = []

    models = pool.get("models")
    if not isinstance(models, list) or not models:
        return {"errors": ["The model pool must contain a non-empty 'models' list."], "warnings": []}

    seen_keys: set[str] = set()
    for index, model in enumerate(models):
        label = model.get("key") or f"index {index}"
        for field in REQUIRED_FIELDS:
            if model.get(field) in (None, ""):
                errors.append(f"Model {label} is missing '{field}'.")

        key = model.get("key")
        if key in seen_keys:
            errors.append(f"Duplicate model key: {key}.")
        seen_keys.add(key)

        if model.get("product_tier") not in PRODUCT_TIERS:
            errors.append(
                f"Model {label} has product_tier '{model.get('product_tier')}'; "
                f"expected one of {list(PRODUCT_TIERS)}."
            )
        if model.get("thinking_mode") not in THINKING_MODES:
            errors.append(
                f"Model {label} has thinking_mode '{model.get('thinking_mode')}'; "
                f"expected one of {list(THINKING_MODES)}."
            )
        if model.get("wire_api") not in WIRE_APIS:
            errors.append(f"Model {label} has unsupported wire_api '{model.get('wire_api')}'.")
        if model.get("model_id_status") not in ("verified", "unverified"):
            errors.append(
                f"Model {label} has model_id_status '{model.get('model_id_status')}'; "
                "expected 'verified' or 'unverified'."
            )
        if model.get("model_id_status") == "verified" and not model.get("model_id"):
            errors.append(f"Model {label} is marked verified but has no model_id.")

        base_url = model.get("base_url") or ""
        if not base_url.startswith("https://"):
            errors.append(f"Model {label} base_url must use https.")
        api_key_env = model.get("api_key_env") or ""
        if api_key_env != api_key_env.upper():
            errors.append(f"Model {label} api_key_env must be an upper-case environment variable name.")
        if model.get("temperature") != 0.0:
            errors.append(f"Model {label} must run at temperature 0.0 for reproducibility.")

        pricing = model.get("pricing")
        if not isinstance(pricing, dict):
            errors.append(f"Model {label} is missing a pricing block.")
        else:
            for field in ("status", "input", "output"):
                if field not in pricing:
                    errors.append(f"Model {label} pricing block is missing '{field}'.")
            if pricing.get("status") == "historical_inactive":
                errors.append(
                    f"Model {label} uses inactive historical pricing. Historical V0.1-era "
                    "prices must never be attached to an active V1 model entry."
                )
            if pricing.get("status") == "verified":
                if pricing.get("input") is None or pricing.get("output") is None:
                    errors.append(f"Model {label} pricing is marked verified but rates are null.")
                if not pricing.get("native_currency"):
                    errors.append(f"Model {label} pricing is marked verified but native_currency is null.")
                if model.get("model_id_status") != "verified":
                    errors.append(
                        f"Model {label} has verified pricing but an unverified model ID. "
                        "A price cannot be verified before the model it applies to is."
                    )
                applies_to = pricing.get("applies_to_model_id")
                if applies_to in archived_pricing_model_ids(pool):
                    errors.append(
                        f"Model {label} pricing references '{applies_to}', which is a retired "
                        "V0.1-era pricing entry. Archived pricing must not leak into V1 cost "
                        "estimation."
                    )
                if applies_to and model.get("model_id") and applies_to != model["model_id"]:
                    warnings.append(
                        f"Model {label} pricing applies to '{applies_to}' but the configured "
                        f"model_id is '{model['model_id']}'."
                    )
            elif pricing.get("status") == "unverified":
                if pricing.get("input") is not None or pricing.get("output") is not None:
                    warnings.append(
                        f"Model {label} pricing is marked unverified but carries numeric rates."
                    )
            else:
                errors.append(f"Model {label} has unsupported pricing status '{pricing.get('status')}'.")

    candidate_models = candidates(pool)
    judge_models = judges(pool)

    if not candidate_models:
        errors.append("The pool must contain at least one candidate model.")
    if len(candidate_models) != config.TARGET_CANDIDATE_MODELS:
        warnings.append(
            f"Candidate model count is {len(candidate_models)}; the V1 planning target is "
            f"{config.TARGET_CANDIDATE_MODELS}."
        )

    judge_families = {model["model_family"] for model in judge_models}
    if len(judge_models) < config.JUDGES_PER_RESPONSE:
        errors.append(
            f"The judge pool needs at least {config.JUDGES_PER_RESPONSE} judge-eligible models, "
            f"found {len(judge_models)}."
        )
    if len(judge_families) < config.JUDGES_PER_RESPONSE:
        errors.append(
            "The judge pool must span at least "
            f"{config.JUDGES_PER_RESPONSE} model families so cross-family dual judging is possible; "
            f"found {sorted(judge_families)}."
        )

    # One shared registry: no judge-only duplicate of an existing candidate model.
    registry_slots: dict[tuple[str, str], str] = {}
    for model in models:
        slot = (model.get("model_family"), model.get("product_tier"))
        if slot in registry_slots:
            errors.append(
                f"Duplicate registry entries for {slot[0]} / {slot[1]}: "
                f"'{registry_slots[slot]}' and '{model.get('key')}'. Use one shared model "
                "entry and mark it judge_eligible instead of adding a judge-only copy."
            )
        else:
            registry_slots[slot] = model.get("key")

    priority = judge_priority(pool)
    if not priority:
        errors.append(
            "The pool must declare a 'judge_priority' list so judge selection is "
            "reproducible from configuration."
        )
    for index, key in enumerate(priority):
        if key not in {model["key"] for model in models}:
            errors.append(f"judge_priority entry {index} ('{key}') is not in the registry.")
        elif key not in {model["key"] for model in judge_models}:
            errors.append(f"judge_priority entry '{key}' is not judge_eligible.")
    if len(set(priority)) != len(priority):
        errors.append("judge_priority must not contain duplicate entries.")

    unverified = [
        model["key"]
        for model in models
        if model.get("model_id_status") != "verified"
    ]
    if unverified:
        warnings.append(
            f"{len(unverified)} model(s) have unverified model IDs and cannot be used for a paid run: "
            f"{', '.join(unverified)}."
        )

    return {"errors": errors, "warnings": warnings}


def unverified_models(pool: dict) -> list[dict]:
    return [model for model in pool["models"] if model.get("model_id_status") != "verified"]


def pool_facts(pool: dict) -> dict:
    """Small factual summary used by validation output and the leaderboard."""
    candidate_models = candidates(pool)
    judge_models = judges(pool)
    return {
        "pool_version": pool.get("pool_version"),
        "candidate_count": len(candidate_models),
        "judge_count": len(judge_models),
        "families": sorted({model["model_family"] for model in candidate_models}),
        "providers": sorted({model["provider"] for model in candidate_models}),
        "judge_families": sorted({model["model_family"] for model in judge_models}),
        "judge_keys": [model["key"] for model in judge_models],
        "judge_priority": judge_priority(pool),
        "registry_size": len(pool["models"]),
        "historical_pricing_entries": len(
            historical_pricing(pool).get("entries") or []
        ),
        "inference_channels": sorted(
            {model["inference_channel"] for model in candidate_models}
        ),
    }


def priced_models(pool: dict) -> list[dict]:
    """Models whose pricing block is verified and numeric."""
    return [
        model
        for model in pool["models"]
        if model["pricing"].get("status") == "verified"
        and model["pricing"].get("input") is not None
    ]
