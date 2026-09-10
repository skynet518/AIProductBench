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

from src import config


class PricingError(ValueError):
    """Raised when a cost cannot be derived without guessing."""


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
    at: dt.datetime | None = None,
    synthetic: bool = False,
) -> dict:
    """Compute the native-currency cost of one call.

    Raises PricingError when the price is unknown, when a time-of-day price is
    requested without a timestamp, or when the request exceeds the priced tier.
    """
    pricing = effective_pricing(model, synthetic=synthetic)
    status = pricing.get("status")

    if status not in ("verified", "synthetic"):
        raise PricingError(
            f"Pricing for '{model['key']}' is '{status}' and cannot be used for cost estimation."
        )

    input_rate = pricing.get("input")
    output_rate = pricing.get("output")
    if input_rate is None or output_rate is None:
        raise PricingError(f"Pricing for '{model['key']}' has no numeric rates.")

    if input_tokens is None or output_tokens is None:
        return {
            "native_cost": None,
            "native_currency": pricing.get("native_currency"),
            "basis": "unavailable: provider reported no token usage",
            "window": None,
            "input_rate": input_rate,
            "output_rate": output_rate,
        }

    limit = pricing.get("input_tier_limit_tokens")
    if limit is not None and input_tokens > limit:
        raise PricingError(
            f"Input of {input_tokens:,} tokens for '{model['key']}' exceeds the "
            f"{limit:,}-token limit of the pricing snapshot. Cost is not estimated "
            "because applying this rate would be wrong."
        )

    schedule = pricing.get("time_of_day")
    window = "flat"
    if schedule:
        if at is None:
            raise PricingError(
                f"Model '{model['key']}' is priced by time of day, so a call timestamp "
                "is required to resolve the rate."
            )
        peak = is_peak_window(pricing, at)
        window = "peak" if peak else "off_peak"
        input_rate = schedule[window]["input"]
        output_rate = schedule[window]["output"]

    cost = (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000
    return {
        "native_cost": round(cost, 8),
        "native_currency": pricing.get("native_currency"),
        "basis": f"native list price, {window.replace('_', '-')}",
        "window": window,
        "input_rate": input_rate,
        "output_rate": output_rate,
    }


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
            model, input_tokens, output_tokens, at=at, synthetic=synthetic
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
            "input_rate": None,
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
        "input_rate": native["input_rate"],
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
                "applies_to_model_id": pricing.get("applies_to_model_id"),
                "input": pricing.get("input"),
                "output": pricing.get("output"),
                "input_tier_limit_tokens": pricing.get("input_tier_limit_tokens"),
                "time_of_day": pricing.get("time_of_day"),
                "notes": pricing.get("notes") or [],
            }
        )

    return {
        "display_currency": config.DISPLAY_CURRENCY,
        "synthetic": synthetic,
        "fx_snapshot": fx_snapshot,
        "models": entries,
    }
