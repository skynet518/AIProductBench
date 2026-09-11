"""Pricing and currency normalization.

Design rules (frozen, see docs/METHODOLOGY_V1.md and docs/DECISIONS.md D-011):

* Native provider price and currency are always preserved.
* A normalized CNY value is produced for display, and it is produced only when
  it can be produced honestly: natively-CNY prices convert directly, and other
  currencies require an explicit dated FX snapshot with a named source.
* Nothing here ever invents a rate, and no permanent conversion rate is
  hard-coded.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

from src import config


class PricingError(ValueError):
    """Raised when a cost cannot be derived without guessing."""


PRICING_SNAPSHOT_ID = "v1-pricing-2026-09-11"
PRICING_SNAPSHOT_AS_OF = "2026-09-11"
PRICING_SNAPSHOT_FILE = config.DATA_DIR / "pricing_snapshot_v1.json"


def canonical_hash(obj) -> str:
    """Order-insensitive SHA-256 over canonical JSON (UTF-8, keys sorted)."""
    blob = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def is_peak_window(pricing_block: dict, at: dt.datetime) -> bool:
    """True during a provider-declared peak window.

    Boundaries are treated as [start, end) in UTC.
    """
    schedule = pricing_block.get("time_of_day") or {}
    at = at.astimezone(dt.timezone.utc)
    if schedule.get("peak_weekdays_only", True) and at.weekday() >= 5:
        return False
    windows = schedule.get("peak_windows_utc") or []
    return any(start <= at.hour < end for start, end in windows)


def synthetic_pricing(model: dict) -> dict:
    """Deterministic placeholder pricing used only by --dry-run.

    Every value is derived from a hash of the model key, so a dry run is
    reproducible and no synthetic figure can be mistaken for a published price.
    Roughly half the models are priced natively in CNY and half in USD so that
    both the direct and the FX-conversion paths are exercised offline.
    """
    digest = hashlib.sha256(f"pricing|{model['key']}".encode("utf-8")).hexdigest()
    number = int(digest[:8], 16)
    native_currency = "CNY" if number % 2 == 0 else "USD"
    return {
        "status": "synthetic",
        "synthetic": True,
        "snapshot_date": "2026-09-11",
        "native_currency": native_currency,
        "unit": "per_1m_tokens",
        "source": "synthetic dry-run fixture — not a published price",
        "applies_to_model_id": model.get("model_id"),
        "input": round(0.5 + (number % 30) / 10, 4),
        "output": round(1.5 + (number % 60) / 10, 4),
        "input_tier_limit_tokens": None,
        "time_of_day": None,
        "notes": ["Synthetic dry-run pricing. Never used for a real run."],
    }


def effective_pricing(model: dict, *, synthetic: bool = False) -> dict:
    if synthetic:
        return synthetic_pricing(model)
    pricing = model.get("pricing")
    if not isinstance(pricing, dict):
        raise PricingError(f"Model '{model['key']}' has no pricing block.")
    if pricing.get("status") == "historical_inactive":
        raise PricingError(
            f"Model '{model['key']}' carries retired V0.1-era pricing. Historical pricing "
            "must never be used for V1 cost estimation."
        )
    return pricing


def native_price_call(
    model: dict,
    input_tokens,
    output_tokens,
    *,
    cached_input_tokens=None,
    at: dt.datetime | None = None,
    synthetic: bool = False,
) -> dict:
    """Compute the native-currency cost of one call.

    Raises PricingError when the price is unknown, when a time-of-day price is
    requested without a timestamp, or when the request exceeds the priced tier.

    `cached_input_tokens` is billed at the cached-input rate when the provider
    returns it and the snapshot exposes a rate; otherwise all input tokens are
    billed at the input (cache-miss) rate. Nothing is inferred.
    """
    pricing = effective_pricing(model, synthetic=synthetic)
    status = pricing.get("status")

    if status not in ("verified", "synthetic"):
        raise PricingError(
            f"Pricing for '{model['key']}' is '{status}' and cannot be used for cost estimation."
        )

    input_rate, output_rate, cached_rate, window, tier_label = _resolve_rates(
        model, pricing, input_tokens, at
    )
    if input_rate is None or output_rate is None:
        raise PricingError(f"Pricing for '{model['key']}' has no numeric rates.")

    if input_tokens is None or output_tokens is None:
        return {
            "native_cost": None,
            "native_currency": pricing.get("native_currency"),
            "basis": "unavailable: provider reported no token usage",
            "window": None,
            "tier": tier_label,
            "input_rate": input_rate,
            "cached_input_rate": cached_rate,
            "output_rate": output_rate,
        }

    billed_cached = cached_input_tokens or 0
    if billed_cached and cached_rate is None:
        billed_cached = 0
    miss_tokens = input_tokens - billed_cached
    cost = (
        miss_tokens * input_rate
        + billed_cached * (cached_rate or 0)
        + output_tokens * output_rate
    ) / 1_000_000
    return {
        "native_cost": round(cost, 8),
        "native_currency": pricing.get("native_currency"),
        "basis": f"native list price, {window.replace('_', '-')}",
        "window": window,
        "tier": tier_label,
        "input_rate": input_rate,
        "cached_input_rate": cached_rate,
        "output_rate": output_rate,
    }


def _resolve_rates(model: dict, pricing: dict, input_tokens, at):
    """Resolve (input, output, cached_input) rates for one call.

    Precedence: time-of-day schedule, then context tiers, then flat rates.
    """
    schedule = pricing.get("time_of_day")
    if schedule:
        if at is None:
            raise PricingError(
                f"Model '{model['key']}' is priced by time of day, so a call timestamp "
                "is required to resolve the rate."
            )
        window = "peak" if is_peak_window(pricing, at) else "off_peak"
        rates = schedule[window]
        return rates.get("input"), rates.get("output"), rates.get("cached_input"), window, None

    tiers = pricing.get("input_tiers")
    if isinstance(tiers, list) and tiers:
        if input_tokens is None:
            raise PricingError(
                f"Model '{model['key']}' is priced by context tier, so input token "
                "usage is required to resolve the rate."
            )
        for tier in tiers:
            limit = tier.get("max_input_tokens")
            if limit is None or input_tokens <= limit:
                return (
                    tier.get("input"),
                    tier.get("output"),
                    tier.get("cached_input"),
                    "flat",
                    tier.get("label") or f"<= {limit}",
                )
        raise PricingError(
            f"Input of {input_tokens:,} tokens for '{model['key']}' exceeds the largest "
            "context tier of the pricing snapshot. Cost is not estimated because applying "
            "a lower tier rate would be wrong."
        )

    limit = pricing.get("input_tier_limit_tokens")
    if limit is not None and input_tokens is not None and input_tokens > limit:
        raise PricingError(
            f"Input of {input_tokens:,} tokens for '{model['key']}' exceeds the "
            f"{limit:,}-token limit of the pricing snapshot. Cost is not estimated "
            "because applying this rate would be wrong."
        )
    return pricing.get("input"), pricing.get("output"), pricing.get("cached_input"), "flat", None


def normalize_to_cny(
    native_cost, native_currency: str | None, fx_snapshot: dict | None
) -> dict:
    """Convert a native cost to CNY, or explain honestly why it cannot."""
    result = {
        "normalized_cost_cny": None,
        "display_currency": config.DISPLAY_CURRENCY,
        "normalization_method": "unavailable",
        "fx_pair": None,
        "fx_rate": None,
        "fx_snapshot_date": None,
        "normalization_note": None,
    }

    if native_cost is None:
        result["normalization_note"] = "no native cost available"
        return result

    if not native_currency:
        result["normalization_note"] = "native currency is unknown"
        return result

    if native_currency.upper() == config.DISPLAY_CURRENCY:
        result["normalized_cost_cny"] = round(native_cost, 8)
        result["normalization_method"] = "native"
        return result

    snapshot = fx_snapshot or {}
    rate = snapshot.get("fx_rate")
    pair = snapshot.get("fx_pair")
    expected_pair = f"{native_currency.upper()}/{config.DISPLAY_CURRENCY}"

    if not rate or rate <= 0 or not pair:
        result["normalization_note"] = (
            f"no FX snapshot configured for {expected_pair}; "
            "native price preserved and CNY value left null"
        )
        return result

    if pair.upper() != expected_pair:
        result["normalization_note"] = (
            f"FX snapshot pair '{pair}' does not match the required '{expected_pair}'"
        )
        return result

    result["normalized_cost_cny"] = round(native_cost * rate, 8)
    result["normalization_method"] = "fx"
    result["fx_pair"] = pair
    result["fx_rate"] = rate
    result["fx_snapshot_date"] = snapshot.get("fx_snapshot_date")
    return result


def price_call(
    model: dict,
    input_tokens,
    output_tokens,
    *,
    cached_input_tokens=None,
    at: dt.datetime | None = None,
    fx_snapshot: dict | None = None,
    synthetic: bool = False,
) -> dict:
    """Price one call and normalize it for display.

    Never raises for missing data: an unusable price is returned as a null cost
    with `cost_error` explaining why, so the pipeline records an honest gap
    instead of a fabricated number.
    """
    try:
        native = native_price_call(
            model,
            input_tokens,
            output_tokens,
            cached_input_tokens=cached_input_tokens,
            at=at,
            synthetic=synthetic,
        )
        native_error = None
    except PricingError as exc:
        native = {
            "native_cost": None,
            "native_currency": effective_pricing(model, synthetic=synthetic).get(
                "native_currency"
            ),
            "basis": None,
            "window": None,
            "tier": None,
            "input_rate": None,
            "cached_input_rate": None,
            "output_rate": None,
        }
        native_error = str(exc)

    normalized = normalize_to_cny(
        native["native_cost"], native["native_currency"], fx_snapshot
    )

    return {
        "native_cost": native["native_cost"],
        "native_currency": native["native_currency"],
        "normalized_cost_cny": normalized["normalized_cost_cny"],
        "display_currency": normalized["display_currency"],
        "normalization_method": normalized["normalization_method"],
        "normalization_note": native_error or normalized["normalization_note"],
        "fx_pair": normalized["fx_pair"],
        "fx_rate": normalized["fx_rate"],
        "fx_snapshot_date": normalized["fx_snapshot_date"],
        "basis": native["basis"],
        "window": native["window"],
        "tier": native.get("tier"),
        "input_rate": native["input_rate"],
        "cached_input_rate": native.get("cached_input_rate"),
        "output_rate": native["output_rate"],
        "pricing_status": effective_pricing(model, synthetic=synthetic).get("status"),
        "cost_error": native_error,
    }


def pricing_snapshot(models_list: list[dict], fx_snapshot: dict | None, *, synthetic: bool) -> dict:
    """Snapshot metadata for the results document."""
    entries = []
    for model in models_list:
        pricing = effective_pricing(model, synthetic=synthetic)
        entries.append(
            {
                "model_key": model["key"],
                "display_name": model["display_name"],
                "status": pricing.get("status"),
                "snapshot_date": pricing.get("snapshot_date"),
                "native_currency": pricing.get("native_currency"),
                "source": pricing.get("source"),
                "source_url": pricing.get("source_url"),
                "applies_to_model_id": pricing.get("applies_to_model_id"),
                "region": pricing.get("region"),
                "input": pricing.get("input"),
                "output": pricing.get("output"),
                "cached_input": pricing.get("cached_input"),
                "reasoning": pricing.get("reasoning"),
                "input_tier_limit_tokens": pricing.get("input_tier_limit_tokens"),
                "input_tiers": pricing.get("input_tiers"),
                "time_of_day": pricing.get("time_of_day"),
                "cache_storage": pricing.get("cache_storage"),
                "notes": pricing.get("notes") or [],
            }
        )

    return {
        "display_currency": config.DISPLAY_CURRENCY,
        "synthetic": synthetic,
        "fx_snapshot": fx_snapshot,
        "models": entries,
    }


# --------------------------------------------------------------------------
# Snapshot schema validation (offline; used by Phase 4 readiness checks)
# --------------------------------------------------------------------------

FX_STATUSES = ("unverified", "synthetic", "verified")
PRICING_STATUSES = ("unverified", "synthetic", "verified")


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _record_has_rates(entry: dict) -> bool:
    """True when a snapshot record exposes usable input/output rates."""
    if entry.get("input") is not None and entry.get("output") is not None:
        return True
    schedule = entry.get("time_of_day")
    if isinstance(schedule, dict) and all(
        isinstance(schedule.get(window), dict)
        and schedule[window].get("input") is not None
        and schedule[window].get("output") is not None
        for window in ("peak", "off_peak")
    ):
        return True
    tiers = entry.get("input_tiers")
    if isinstance(tiers, list) and tiers and all(
        isinstance(tier, dict)
        and tier.get("input") is not None
        and tier.get("output") is not None
        for tier in tiers
    ):
        return True
    return False


def validate_fx_snapshot(snapshot) -> list[str]:
    """Validate the FX snapshot contract used for CNY normalization.

    A verified snapshot must carry a positive rate, a pair, an as-of date, a
    named source, and a snapshot id. Unverified/synthetic snapshots may carry
    null values but never an invalid one.
    """
    if not isinstance(snapshot, dict):
        return ["FX snapshot must be an object."]

    errors: list[str] = []
    for field in ("status", "fx_pair", "fx_rate", "fx_snapshot_date", "source", "snapshot_id"):
        if field not in snapshot:
            errors.append(f"FX snapshot is missing '{field}'.")

    status = snapshot.get("status")
    if status is not None and status not in FX_STATUSES:
        errors.append(f"FX snapshot status '{status}' must be one of {list(FX_STATUSES)}.")

    pair = snapshot.get("fx_pair")
    if pair is not None and (not isinstance(pair, str) or "/" not in pair):
        errors.append("FX snapshot 'fx_pair' must look like 'USD/CNY'.")

    rate = snapshot.get("fx_rate")
    if rate is not None and (not _is_number(rate) or rate <= 0):
        errors.append("FX snapshot 'fx_rate' must be null or a positive number.")

    if status == "verified":
        if rate is None:
            errors.append("A verified FX snapshot must carry a positive 'fx_rate'.")
        if not snapshot.get("fx_snapshot_date"):
            errors.append("A verified FX snapshot must carry 'fx_snapshot_date'.")
        if not snapshot.get("source"):
            errors.append("A verified FX snapshot must carry a named 'source'.")
        if not snapshot.get("snapshot_id"):
            errors.append("A verified FX snapshot must carry a 'snapshot_id'.")
    return errors


def validate_pricing_snapshot(snapshot) -> list[str]:
    """Validate the pricing snapshot contract persisted with a run."""
    if not isinstance(snapshot, dict):
        return ["Pricing snapshot must be an object."]

    errors: list[str] = []
    if snapshot.get("display_currency") != config.DISPLAY_CURRENCY:
        errors.append(
            f"Pricing snapshot 'display_currency' must be {config.DISPLAY_CURRENCY!r}."
        )
    if not isinstance(snapshot.get("synthetic"), bool):
        errors.append("Pricing snapshot 'synthetic' must be a boolean.")
    if snapshot.get("fx_snapshot") is not None:
        errors.extend(
            f"FX snapshot: {error}" for error in validate_fx_snapshot(snapshot["fx_snapshot"])
        )

    entries = snapshot.get("models")
    if not isinstance(entries, list) or not entries:
        errors.append("Pricing snapshot must contain a non-empty 'models' list.")
        return errors

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"Pricing snapshot model {index} must be an object.")
            continue
        label = entry.get("model_key") or f"index {index}"
        status = entry.get("status")
        if status not in PRICING_STATUSES:
            errors.append(
                f"Pricing snapshot model {label} status '{status}' must be one of "
                f"{list(PRICING_STATUSES)}."
            )
            continue
        if status == "unverified":
            continue
        if not _record_has_rates(entry):
            errors.append(
                f"Pricing snapshot model {label} has no usable input/output rates "
                "for a priced entry."
            )
        for field in ("native_currency", "snapshot_date", "source"):
            if not entry.get(field):
                errors.append(
                    f"Pricing snapshot model {label} must carry '{field}' for a priced entry."
                )
    return errors


# --------------------------------------------------------------------------
# Immutable production pricing snapshot (Phase 4B/C)
# --------------------------------------------------------------------------


def build_pricing_snapshot(models_list: list[dict]) -> dict:
    """Build the immutable V1 pricing snapshot from the registry pricing blocks.

    The content hash is computed over the snapshot content excluding the hash
    field itself, so it is a stable content address: future provider price
    changes cannot alter a historical snapshot.
    """
    records = []
    for model in models_list:
        block = model.get("pricing") or {}
        records.append(
            {
                "model_key": model["key"],
                "provider": model.get("provider"),
                "provider_key": model.get("provider_key"),
                "model_id": model.get("model_id"),
                "region": model.get("region"),
                "native_currency": block.get("native_currency"),
                "unit": block.get("unit"),
                "source": block.get("source"),
                "source_url": block.get("source_url"),
                "input": block.get("input"),
                "output": block.get("output"),
                "cached_input": block.get("cached_input"),
                "reasoning": block.get("reasoning"),
                "input_tiers": block.get("input_tiers"),
                "time_of_day": block.get("time_of_day"),
                "cache_storage": block.get("cache_storage"),
                "notes": block.get("notes") or [],
            }
        )
    content = {
        "snapshot_id": PRICING_SNAPSHOT_ID,
        "as_of": PRICING_SNAPSHOT_AS_OF,
        "records": records,
    }
    content["content_sha256"] = canonical_hash(content)
    return content


def pricing_snapshot_hash(snapshot: dict) -> str | None:
    return snapshot.get("content_sha256")


def load_pricing_snapshot(path: Path | None = None) -> dict:
    path = path or PRICING_SNAPSHOT_FILE
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def validate_pricing_content(snapshot) -> list[str]:
    """Validate the immutable pricing snapshot document."""
    if not isinstance(snapshot, dict):
        return ["Pricing snapshot document must be an object."]
    errors: list[str] = []
    for field in ("snapshot_id", "as_of", "content_sha256", "records"):
        if not snapshot.get(field):
            errors.append(f"Pricing snapshot document is missing '{field}'.")
    if snapshot.get("content_sha256"):
        without_hash = {k: v for k, v in snapshot.items() if k != "content_sha256"}
        if canonical_hash(without_hash) != snapshot["content_sha256"]:
            errors.append("Pricing snapshot 'content_sha256' does not match its content.")
    records = snapshot.get("records")
    if not isinstance(records, list) or not records:
        errors.append("Pricing snapshot document must contain a non-empty 'records' list.")
        return errors
    seen = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"Pricing record {index} must be an object.")
            continue
        label = record.get("model_key") or f"index {index}"
        if label in seen:
            errors.append(f"Duplicate pricing record for {label}.")
        seen.add(label)
        for field in ("provider", "model_id", "native_currency", "unit", "source"):
            if not record.get(field):
                errors.append(f"Pricing record {label} must carry '{field}'.")
        if not (
            (record.get("input") is not None and record.get("output") is not None)
            or record.get("input_tiers")
            or record.get("time_of_day")
        ):
            errors.append(f"Pricing record {label} has no usable input/output rates.")
    return errors
