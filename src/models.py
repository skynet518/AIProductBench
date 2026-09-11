"""Configurable model pool for AIProductBench CN V1.

The candidate and judge pools are data, not code. Nothing in the benchmark
pipeline may branch on a specific model name; it reads these entries instead.

An entry distinguishes MODEL FAMILY (who trained the model) from INFERENCE
PROVIDER / CHANNEL (who serves it), because the same family reached through a
different channel has different latency, price, and reliability.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src import config

REGISTRY_SNAPSHOT_ID = "v1-registry-2026-09-11"
REGISTRY_SNAPSHOT_AS_OF = "2026-09-11"
REGISTRY_SNAPSHOT_FILE = config.DATA_DIR / "model_registry_snapshot_v1.json"


def canonical_hash(obj) -> str:
    """Order-insensitive SHA-256 over canonical JSON (UTF-8, keys sorted)."""
    blob = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()

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
)

PRODUCT_TIERS = ("flagship", "balanced", "value")
THINKING_MODES = ("disabled", "enabled", "provider_default")
WIRE_APIS = ("chat_completions", "responses")


def pricing_has_rates(pricing: dict) -> bool:
    """True when a pricing block carries usable input/output rates.

    Supports flat pricing, time-of-day (peak/off-peak) pricing, and
    context-tiered pricing (`input_tiers`).
    """
    if pricing.get("input") is not None and pricing.get("output") is not None:
        return True
    schedule = pricing.get("time_of_day")
    if isinstance(schedule, dict) and schedule:
        if all(
            isinstance(schedule.get(window), dict)
            and schedule[window].get("input") is not None
            and schedule[window].get("output") is not None
            for window in ("peak", "off_peak")
        ):
            return True
    tiers = pricing.get("input_tiers")
    if isinstance(tiers, list) and tiers:
        if all(
            isinstance(tier, dict)
            and tier.get("input") is not None
            and tier.get("output") is not None
            for tier in tiers
        ):
            return True
    return False


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
        if "enabled" in model and not isinstance(model["enabled"], bool):
            errors.append(f"Model {label} 'enabled' must be a boolean.")
        if "region" in model and (
            not isinstance(model["region"], str) or not model["region"].strip()
        ):
            errors.append(f"Model {label} 'region' must be a non-empty string.")
        thinking_config = model.get("thinking_config")
        if "thinking_config" in model and thinking_config is not None and not isinstance(
            thinking_config, dict
        ):
            errors.append(f"Model {label} 'thinking_config' must be null or an object.")
        request_config = model.get("request_config")
        if request_config is not None:
            if not isinstance(request_config, dict):
                errors.append(f"Model {label} 'request_config' must be null or an object.")
            else:
                for field in ("temperature", "top_p"):
                    value = request_config.get(field)
                    if value is not None and (
                        isinstance(value, bool) or not isinstance(value, (int, float))
                    ):
                        errors.append(
                            f"Model {label} request_config '{field}' must be null or a number."
                        )
                extra_body = request_config.get("extra_body")
                if extra_body is not None and not isinstance(extra_body, dict):
                    errors.append(
                        f"Model {label} request_config 'extra_body' must be null or an object."
                    )
        verified_as_of = model.get("model_id_verified_as_of")
        if verified_as_of is not None and (
            not isinstance(verified_as_of, str) or not verified_as_of.strip()
        ):
            errors.append(
                f"Model {label} 'model_id_verified_as_of' must be null or a non-empty string."
            )
        if model.get("model_id_status") == "verified" and not verified_as_of:
            errors.append(
                f"Model {label} is marked verified but has no 'model_id_verified_as_of' date."
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

        pricing = model.get("pricing")
        if not isinstance(pricing, dict):
            errors.append(f"Model {label} is missing a pricing block.")
        else:
            for field in ("status", "input", "output"):
                if field not in pricing:
                    errors.append(f"Model {label} pricing block is missing '{field}'.")
            for field in ("reasoning", "cached_input"):
                value = pricing.get(field)
                if value is not None and (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or value < 0
                ):
                    errors.append(
                        f"Model {label} pricing '{field}' must be null or a non-negative number."
                    )
            if pricing.get("status") == "historical_inactive":
                errors.append(
                    f"Model {label} uses inactive historical pricing. Historical V0.1-era "
                    "prices must never be attached to an active V1 model entry."
                )
            if pricing.get("status") == "verified":
                if not pricing_has_rates(pricing):
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
        and pricing_has_rates(model["pricing"])
    ]


# --------------------------------------------------------------------------
# Deterministic registry snapshot (Phase 4B/C)
# --------------------------------------------------------------------------


def build_registry_snapshot(pool: dict) -> dict:
    """Deterministic snapshot of the registry fields a run must lock.

    Secrets (API-key environment variable names) are deliberately excluded.
    """
    records = []
    for model in pool["models"]:
        records.append(
            {
                "logical_model_id": model["key"],
                "provider": model.get("provider"),
                "provider_key": model.get("provider_key"),
                "provider_model_id": model.get("model_id"),
                "model_family": model.get("model_family"),
                "tier": model.get("product_tier"),
                "region": model.get("region"),
                "base_url": model.get("base_url"),
                "wire_api": model.get("wire_api"),
                "thinking_mode": model.get("thinking_mode"),
                "thinking_config": model.get("thinking_config"),
                "request_config": model.get("request_config"),
                "model_id_status": model.get("model_id_status"),
                "model_id_verified_as_of": model.get("model_id_verified_as_of"),
            }
        )
    content = {
        "snapshot_id": REGISTRY_SNAPSHOT_ID,
        "as_of": REGISTRY_SNAPSHOT_AS_OF,
        "models": records,
    }
    content["content_sha256"] = canonical_hash(content)
    return content


def load_registry_snapshot(path: Path | None = None) -> dict:
    path = path or REGISTRY_SNAPSHOT_FILE
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def validate_registry_snapshot(snapshot) -> list[str]:
    if not isinstance(snapshot, dict):
        return ["Registry snapshot must be an object."]
    errors: list[str] = []
    for field in ("snapshot_id", "as_of", "content_sha256", "models"):
        if not snapshot.get(field):
            errors.append(f"Registry snapshot is missing '{field}'.")
    if snapshot.get("content_sha256"):
        without_hash = {k: v for k, v in snapshot.items() if k != "content_sha256"}
        if canonical_hash(without_hash) != snapshot["content_sha256"]:
            errors.append("Registry snapshot 'content_sha256' does not match its content.")
    models_list = snapshot.get("models")
    if not isinstance(models_list, list) or len(models_list) != 10:
        errors.append("Registry snapshot must contain exactly ten model records.")
        return errors
    for index, record in enumerate(models_list):
        if not isinstance(record, dict):
            errors.append(f"Registry record {index} must be an object.")
            continue
        label = record.get("logical_model_id") or f"index {index}"
        for field in ("provider", "provider_model_id", "model_family", "tier", "region"):
            if not record.get(field):
                errors.append(f"Registry record {label} must carry '{field}'.")
        if "api_key_env" in record:
            errors.append(f"Registry record {label} must not include credential fields.")
    return errors
