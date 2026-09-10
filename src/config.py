"""Central configuration for AIProductBench V0.1.

Model identifiers, provider endpoints, credentials, and pricing live here so
that no benchmark logic hard-codes a provider or a model ID.

Credentials are read from environment variables only. This project never reads
API keys, tokens, or provider settings from Codex configuration files or any
other file on disk. To change a model or endpoint without editing code, set the
corresponding AIPB_* environment variable documented below.
"""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path
from urllib.parse import urlparse

# --------------------------------------------------------------------------
# Paths and versions
# --------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
TEST_CASES_FILE = DATA_DIR / "test_cases.json"
RESULTS_DIR = PROJECT_ROOT / "results"
SAMPLE_RESULTS_FILE = PROJECT_ROOT / "sample_results.json"
LEADERBOARD_FILE = PROJECT_ROOT / "leaderboard.html"

BENCHMARK_VERSION = "0.1.0"
JUDGE_PROMPT_VERSION = "0.1"

# --------------------------------------------------------------------------
# Capability domains and rubric
# --------------------------------------------------------------------------

DOMAINS = (
    "instruction_following",
    "product_reasoning",
    "structured_analysis",
)

RUBRIC_DIMENSIONS = (
    "task_completion",
    "instruction_following",
    "quality_usefulness",
)

SCORE_MIN = 1
SCORE_MAX = 5

# --------------------------------------------------------------------------
# Request behaviour
# --------------------------------------------------------------------------

REQUEST_TIMEOUT_SECONDS = 120
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 2.0

# --------------------------------------------------------------------------
# Providers and models
# --------------------------------------------------------------------------
#
# Exactly two candidate models are evaluated, plus exactly one judge. The judge
# belongs to the Qwen family, which is a documented V0.1 bias limitation.
#
# The two Qwen models use pinned, dated snapshots so that a run can be
# reproduced against the same weights. The DeepSeek API model ID is not a dated
# snapshot, so DeepSeek must not be described as date-pinned; its documented
# underlying model version is recorded separately in REPRODUCIBILITY below.

DEFAULT_QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"


def _env(name: str, default: str) -> str:
    value = os.environ.get(name, "").strip()
    return value or default


MODELS = (
    {
        "key": "qwen_flash",
        "display_name": "Qwen 3.7 Flash",
        "provider": "qwen",
        "base_url": _env("AIPB_BASE_URL_QWEN", DEFAULT_QWEN_BASE_URL),
        "api_key_env": "DASHSCOPE_API_KEY",
        "model": _env("AIPB_MODEL_QWEN", "qwen3.7-flash-2026-07-15"),
        "wire_api": _env("AIPB_WIRE_API_QWEN", "chat_completions"),
        "temperature": 0.0,
        "max_output_tokens": 1024,
    },
    {
        "key": "deepseek_flash",
        "display_name": "DeepSeek V4 Flash",
        "provider": "deepseek",
        "base_url": _env("AIPB_BASE_URL_DEEPSEEK", DEFAULT_DEEPSEEK_BASE_URL),
        "api_key_env": "DEEPSEEK_API_KEY",
        "model": _env("AIPB_MODEL_DEEPSEEK", "deepseek-v4-flash"),
        "wire_api": _env("AIPB_WIRE_API_DEEPSEEK", "chat_completions"),
        "temperature": 0.0,
        "max_output_tokens": 1024,
    },
)

JUDGE = {
    "key": "judge_qwen_max",
    "display_name": "Qwen 3.7 Max",
    "provider": "qwen",
    "base_url": _env("AIPB_BASE_URL_QWEN", DEFAULT_QWEN_BASE_URL),
    "api_key_env": "DASHSCOPE_API_KEY",
    "model": _env("AIPB_JUDGE_MODEL", "qwen3.7-max-2026-05-20"),
    "wire_api": _env("AIPB_WIRE_API_QWEN", "chat_completions"),
    "temperature": 0.0,
    "max_output_tokens": 700,
}

# --------------------------------------------------------------------------
# Reproducibility metadata
# --------------------------------------------------------------------------

REPRODUCIBILITY = {
    "qwen_candidate_snapshot": "2026-07-15",
    "qwen_judge_snapshot": "2026-05-20",
    "deepseek_api_model_id": "deepseek-v4-flash",
    "deepseek_documented_model_version": "DeepSeek-V4-Flash-0731",
    "deepseek_is_date_pinned": False,
    "note": (
        "The two Qwen models are pinned to dated snapshots. The DeepSeek public "
        "API model ID is not a dated snapshot, so DeepSeek is not represented as "
        "date-pinned; only its documented underlying model version is recorded."
    ),
}

# --------------------------------------------------------------------------
# Pricing snapshot
# --------------------------------------------------------------------------
#
# Official provider list pricing only. Promotional or discounted rates are
# deliberately excluded. All rates are USD per 1,000,000 tokens.
#
# Qwen rates are region-specific. The region is resolved from the configured
# DashScope base URL rather than assumed, and an unrecognised base URL is a hard
# error instead of a silent guess.

PRICING_SNAPSHOT_DATE = "2026-09-11"

PRICING_SOURCES = (
    "Alibaba Cloud Model Studio — qwen3.7-flash Model Info",
    "Alibaba Cloud Model Studio — qwen3.7-max Model Info",
    "DeepSeek API Docs — Models & Pricing",
)

DASHSCOPE_REGIONS = {
    "cn-beijing": {
        "label": "China (Beijing)",
        "host": "dashscope.aliyuncs.com",
        "models": {
            "qwen3.7-flash-2026-07-15": {
                "input": 0.028,
                "output": 0.11,
                "input_tier_limit_tokens": 32_000,
                "tier_note": "valid for request inputs at or below 32K tokens",
            },
            "qwen3.7-max-2026-05-20": {
                "input": 1.65,
                "output": 4.951,
                "input_tier_limit_tokens": None,
                "tier_note": None,
            },
        },
    },
    "sg-singapore": {
        "label": "Singapore (International)",
        "host": "dashscope-intl.aliyuncs.com",
        "models": {
            "qwen3.7-flash-2026-07-15": {
                "input": 0.03,
                "output": 0.13,
                "input_tier_limit_tokens": 32_000,
                "tier_note": "valid for request inputs at or below 32K tokens",
            },
            "qwen3.7-max-2026-05-20": {
                "input": 2.50,
                "output": 7.50,
                "input_tier_limit_tokens": None,
                "tier_note": None,
            },
        },
    },
}

DEEPSEEK_PRICING = {
    "peak": {"input": 0.44, "output": 1.32},
    "off_peak": {"input": 0.22, "output": 0.66},
    # Peak windows in UTC, Monday through Friday. Boundaries are treated as
    # [start, end): 01:00-04:00 and 06:00-10:00.
    "peak_windows_utc": ((1, 4), (6, 10)),
    "peak_weekdays_only": True,
    "cache_note": (
        "DeepSeek cache-hit token accounting is not used in V0.1, so input cost "
        "is calculated conservatively with cache-miss pricing."
    ),
}

# Fixed reference timestamps so that validation and projections are reproducible
# and never depend on when they happen to be executed.
_REFERENCE_TIMESTAMP = dt.datetime(2026, 9, 11, 0, 0, tzinfo=dt.timezone.utc)


def weekday_window_times() -> tuple[dt.datetime, dt.datetime]:
    """Return (peak sample, off-peak sample) inside DeepSeek's published windows."""
    day = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)
    while day.weekday() != 0:  # Monday
        day += dt.timedelta(days=1)
    return day.replace(hour=2), day.replace(hour=0)


class PricingError(ValueError):
    """Raised when a cost cannot be derived without guessing."""


def dashscope_region(base_url: str) -> str | None:
    """Resolve the DashScope region key from a base URL, or None if unknown."""
    host = (urlparse(base_url).hostname or "").lower()
    for key, region in DASHSCOPE_REGIONS.items():
        if host == region["host"] or host.endswith("." + region["host"]):
            return key
    return None


def model_entry(model_id: str) -> dict | None:
    for entry in list(MODELS) + [JUDGE]:
        if entry["model"] == model_id:
            return entry
    return None


def is_deepseek_peak(at: dt.datetime) -> bool:
    """True during DeepSeek peak hours: Mon-Fri 01:00-04:00 and 06:00-10:00 UTC."""
    at = at.astimezone(dt.timezone.utc)
    if DEEPSEEK_PRICING["peak_weekdays_only"] and at.weekday() >= 5:
        return False
    return any(start <= at.hour < end for start, end in DEEPSEEK_PRICING["peak_windows_utc"])


def rates_for(model_id: str, at: dt.datetime | None = None) -> dict:
    """Resolve the rates that apply to one model call.

    Raises PricingError when the region cannot be identified, when a call falls
    outside the priced input tier, or when the model has no snapshot entry. A
    missing rate is never replaced with a guess.
    """
    entry = model_entry(model_id)
    if entry is None:
        raise PricingError(f"No configured model matches model ID '{model_id}'.")

    if entry["provider"] == "qwen":
        region_key = dashscope_region(entry["base_url"])
        if region_key is None:
            raise PricingError(
                f"Cannot identify the DashScope region from the configured base URL "
                f"'{entry['base_url']}', so {model_id} pricing is unresolved."
            )
        region = DASHSCOPE_REGIONS[region_key]
        model_rates = region["models"].get(model_id)
        if model_rates is None:
            raise PricingError(f"No {region['label']} price entry for model '{model_id}'.")
        return {
            "input": model_rates["input"],
            "output": model_rates["output"],
            "basis": f"list price, {region['label']}",
            "region": region_key,
            "region_label": region["label"],
            "input_tier_limit_tokens": model_rates["input_tier_limit_tokens"],
            "window": "flat",
        }

    if at is None:
        raise PricingError(
            f"Model '{model_id}' is priced by time of day, so a call timestamp is "
            "required to resolve the rate."
        )
    window = "peak" if is_deepseek_peak(at) else "off_peak"
    model_rates = DEEPSEEK_PRICING[window]
    return {
        "input": model_rates["input"],
        "output": model_rates["output"],
        "basis": f"list price, {'peak' if window == 'peak' else 'off-peak'} "
        f"(cache-miss input, published peak windows in UTC)",
        "region": None,
        "region_label": None,
        "input_tier_limit_tokens": None,
        "window": window,
    }


def price_call(
    model_id: str, input_tokens, output_tokens, at: dt.datetime | None = None
) -> dict:
    """Price one model call.

    Returns the cost plus the rates and basis used. Raises PricingError rather
    than applying a rate that does not match the call. Returns None cost when the
    provider did not report token usage.
    """
    if input_tokens is None or output_tokens is None:
        return {"cost_usd": None, "basis": "unavailable: provider reported no token usage",
                "input_rate": None, "output_rate": None, "window": None,
                "region_label": None}

    rates = rates_for(model_id, at=at)
    limit = rates["input_tier_limit_tokens"]
    if limit is not None and input_tokens > limit:
        raise PricingError(
            f"Input of {input_tokens:,} tokens for '{model_id}' exceeds the "
            f"{limit:,}-token limit of the V0.1 price snapshot. Cost is not "
            "estimated because applying this rate would be wrong."
        )

    cost = (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000
    return {
        "cost_usd": round(cost, 6),
        "basis": rates["basis"],
        "input_rate": rates["input"],
        "output_rate": rates["output"],
        "window": rates["window"],
        "region_label": rates["region_label"],
    }


def pricing_snapshot() -> dict:
    """Snapshot metadata enriched with the resolved region and rates in use."""
    summary = []
    for entry in list(MODELS) + [JUDGE]:
        model_id = entry["model"]
        record = {
            "display_name": entry["display_name"],
            "model_id": model_id,
            "pricing_model": "time_of_day" if entry["provider"] == "deepseek" else "flat",
            "input": None,
            "output": None,
            "windows": None,
            "basis": None,
            "input_tier_limit_tokens": None,
        }
        try:
            if record["pricing_model"] == "time_of_day":
                peak_at, off_peak_at = weekday_window_times()
                peak = rates_for(model_id, at=peak_at)
                off_peak = rates_for(model_id, at=off_peak_at)
                record["windows"] = {
                    "peak": {"input": peak["input"], "output": peak["output"]},
                    "off_peak": {
                        "input": off_peak["input"],
                        "output": off_peak["output"],
                    },
                }
                record["basis"] = (
                    "list price by published UTC peak windows; input assumes cache-miss pricing"
                )
            else:
                rates = rates_for(model_id, at=_REFERENCE_TIMESTAMP)
                record["input"] = rates["input"]
                record["output"] = rates["output"]
                record["basis"] = rates["basis"]
                record["input_tier_limit_tokens"] = rates["input_tier_limit_tokens"]
        except PricingError as exc:
            record["basis"] = f"unresolved: {exc}"
        summary.append(record)

    return {
        "date": PRICING_SNAPSHOT_DATE,
        "currency": "USD",
        "unit": "USD per 1,000,000 tokens",
        "verified": True,
        "official_list_pricing_only": True,
        "sources": list(PRICING_SOURCES),
        "dashscope_region": {
            key: region["label"] for key, region in DASHSCOPE_REGIONS.items()
        }.get(dashscope_region(MODELS[0]["base_url"]) or "", "unidentified"),
        "resolved_rates": summary,
        "deepseek_peak_windows_utc": [
            f"{start:02d}:00-{end:02d}:00" for start, end in DEEPSEEK_PRICING["peak_windows_utc"]
        ],
        "notes": [
            "Official provider list pricing only; promotional discounts excluded.",
            DEEPSEEK_PRICING["cache_note"],
            "qwen3.7-flash rates apply only to requests with input at or below 32K tokens.",
            "DeepSeek peak hours are 01:00-04:00 and 06:00-10:00 UTC, Monday to Friday.",
        ],
    }


def get_model(key: str) -> dict:
    for entry in MODELS:
        if entry["key"] == key:
            return entry
    raise KeyError(f"Unknown model key: {key}")
