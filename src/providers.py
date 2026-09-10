"""Minimal OpenAI-compatible HTTP client.

Both configured providers are reached over an OpenAI-compatible HTTP API, so a
single small requests-based implementation covers them. Everything that differs
between providers — base URL, API key environment variable, and wire API shape —
is configuration in src/config.py rather than duplicated logic here.

This is deliberately not a provider framework. It is one function that posts a
chat request and normalises the response.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import os
import time

import requests

from src import config


class ProviderError(RuntimeError):
    """Raised when a model call fails after the configured retries."""


class MissingCredentials(ProviderError):
    """Raised when the API key environment variable for a provider is not set."""


def resolve_api_key(entry: dict) -> str:
    """Read a provider API key from the environment. Never from a file."""
    api_key = os.environ.get(entry["api_key_env"], "").strip()
    if not api_key:
        raise MissingCredentials(
            f"Missing credentials for {entry['display_name']}: set the "
            f"{entry['api_key_env']} environment variable."
        )
    return api_key


def _endpoint(entry: dict) -> str:
    base_url = entry["base_url"].rstrip("/")
    if entry["wire_api"] == "responses":
        return f"{base_url}/responses"
    return f"{base_url}/chat/completions"


def _build_payload(entry: dict, messages: list[dict]) -> dict:
    if entry["wire_api"] == "responses":
        return {
            "model": entry["model"],
            "input": [
                {"role": message["role"], "content": message["content"]}
                for message in messages
            ],
            "max_output_tokens": entry["max_output_tokens"],
            "temperature": entry["temperature"],
        }
    return {
        "model": entry["model"],
        "messages": messages,
        "max_tokens": entry["max_output_tokens"],
        "temperature": entry["temperature"],
    }


def _extract_text_and_usage(data: dict, wire_api: str) -> tuple[str, dict]:
    if wire_api == "responses":
        parts = []
        for item in data.get("output") or []:
            if item.get("type") != "message":
                continue
            for chunk in item.get("content") or []:
                if chunk.get("type") in ("output_text", "text"):
                    parts.append(chunk.get("text") or "")
        usage = data.get("usage") or {}
        return "".join(parts).strip(), {
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "total_tokens": usage.get("total_tokens"),
        }

    text = ""
    choices = data.get("choices") or []
    if choices:
        message = choices[0].get("message") or {}
        text = (message.get("content") or "").strip()
    usage = data.get("usage") or {}
    return text, {
        "input_tokens": usage.get("prompt_tokens"),
        "output_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
    }


# Status codes that will not succeed on retry.
_FATAL_STATUS = {400, 401, 403, 404, 422}

# Fixed timestamp used for offline dry runs so that synthetic cost figures are
# reproducible and never depend on when the dry run happened to be executed.
SYNTHETIC_CALL_TIMESTAMP = dt.datetime(2026, 9, 11, 2, 0, tzinfo=dt.timezone.utc)


def _price(model_id: str, input_tokens, output_tokens, called_at: dt.datetime) -> dict:
    """Price a call without ever substituting a guessed rate."""
    try:
        priced = config.price_call(model_id, input_tokens, output_tokens, at=called_at)
    except config.PricingError as exc:
        return {"estimated_cost_usd": None, "cost_basis": None, "cost_error": str(exc)}
    return {
        "estimated_cost_usd": priced["cost_usd"],
        "cost_basis": priced["basis"],
        "cost_error": None,
    }


def chat(entry: dict, messages: list[dict]) -> dict:
    """Call a model and return text, latency, token usage, and cost.

    Retries transient network errors and server-side failures. Fails loudly on
    missing credentials or a non-retryable error response.
    """
    api_key = resolve_api_key(entry)
    url = _endpoint(entry)
    payload = _build_payload(entry, messages)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    last_error = "unknown error"
    for attempt in range(config.MAX_RETRIES + 1):
        called_at = dt.datetime.now(dt.timezone.utc)
        started = time.perf_counter()
        try:
            response = requests.post(
                url, headers=headers, json=payload, timeout=config.REQUEST_TIMEOUT_SECONDS
            )
        except requests.RequestException as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        else:
            latency_ms = round((time.perf_counter() - started) * 1000, 1)
            if response.status_code in _FATAL_STATUS:
                raise ProviderError(
                    f"{entry['display_name']} rejected the request "
                    f"(HTTP {response.status_code}): {response.text[:300]}"
                )
            if response.status_code >= 400:
                last_error = f"HTTP {response.status_code}: {response.text[:300]}"
            else:
                try:
                    data = response.json()
                except ValueError as exc:
                    last_error = f"provider returned invalid JSON: {exc}"
                else:
                    text, usage = _extract_text_and_usage(data, entry["wire_api"])
                    if not text:
                        last_error = "provider returned an empty response"
                    else:
                        price = _price(
                            entry["model"],
                            usage["input_tokens"],
                            usage["output_tokens"],
                            called_at,
                        )
                        return {
                            "text": text,
                            "latency_ms": latency_ms,
                            "input_tokens": usage["input_tokens"],
                            "output_tokens": usage["output_tokens"],
                            "total_tokens": usage["total_tokens"],
                            "model_id": entry["model"],
                            "called_at": called_at.isoformat(timespec="seconds"),
                            "attempts": attempt + 1,
                            "synthetic": False,
                            "error": None,
                            **price,
                        }

        if attempt < config.MAX_RETRIES:
            time.sleep(config.RETRY_BACKOFF_SECONDS * (2**attempt))

    raise ProviderError(
        f"{entry['display_name']} failed after {config.MAX_RETRIES + 1} attempt(s): {last_error}"
    )


def synthetic_call(entry: dict, messages: list[dict], seed: str) -> dict:
    """Deterministic offline stand-in used by --dry-run.

    Every value returned here is fabricated by a hash function so that the
    dry run exercises the full pipeline without network access or cost. The
    `synthetic` flag is propagated into the results document, and dry-run
    artifacts are written outside the committed result files.
    """
    digest = hashlib.sha256(f"{entry['key']}|{seed}".encode("utf-8")).hexdigest()
    number = int(digest[:10], 16)

    prompt_characters = sum(len(message["content"]) for message in messages)
    input_tokens = max(1, prompt_characters // 4)
    output_tokens = 160 + (number % 180)

    text = (
        "[SYNTHETIC DRY-RUN RESPONSE — generated offline, not by a real model]\n"
        f"Model: {entry['display_name']} ({entry['model']})\n"
        f"Case seed: {seed}\n"
        "This placeholder exists only to exercise the benchmark pipeline end to end."
    )
    price = _price(entry["model"], input_tokens, output_tokens, SYNTHETIC_CALL_TIMESTAMP)
    return {
        "text": text,
        "latency_ms": round(120 + (number % 900) / 10, 1),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "model_id": entry["model"],
        "called_at": SYNTHETIC_CALL_TIMESTAMP.isoformat(timespec="seconds"),
        "attempts": 1,
        "synthetic": True,
        "error": None,
        **price,
    }
