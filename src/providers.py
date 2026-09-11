"""Provider-native HTTP access.

Every V1 candidate is reached through its own native provider endpoint. All
provider differences — base URL, credential environment variable, wire API
shape, model ID — are configuration read from the model pool, so this module
contains no provider-specific branching and no model names.

This is deliberately one function, not an adapter framework. A provider needing
a genuinely different protocol gets one more branch in `_build_payload`, not a
new layer.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import os
import time

import requests

from src import config, pricing


class ProviderError(RuntimeError):
    """Raised when a model call fails after the configured retries."""


class MissingCredentials(ProviderError):
    """Raised when the API key environment variable for a provider is not set."""


def resolve_api_key(model: dict) -> str:
    """Read a provider API key from the environment. Never from a file."""
    api_key = os.environ.get(model["api_key_env"], "").strip()
    if not api_key:
        raise MissingCredentials(
            f"Missing credentials for {model['display_name']}: set the "
            f"{model['api_key_env']} environment variable."
        )
    return api_key


def resolve_model_id(model: dict) -> str:
    model_id = model.get("model_id")
    if not model_id:
        raise ProviderError(
            f"Model '{model['key']}' has no verified model ID. Verify it against "
            "provider-native documentation before running a paid benchmark."
        )
    return model_id


def _endpoint(model: dict) -> str:
    base_url = model["base_url"].rstrip("/")
    if model["wire_api"] == "responses":
        return f"{base_url}/responses"
    # Some providers expose a non-OpenAI chat path (for example MiniMax China's
    # /v1/text/chatcompletion_v2). The path is configuration read from the model
    # pool, so no provider-specific branching lives here.
    path = model.get("chat_completions_path")
    if path:
        return f"{base_url}{path}" if path.startswith("/") else f"{base_url}/{path}"
    return f"{base_url}/chat/completions"


def effective_request_config(model: dict) -> dict:
    """The effective request configuration recorded in run artifacts.

    There is no universal temperature override: sampling parameters are sent
    only when a model's `request_config` explicitly specifies them, so every
    model keeps its provider-default/recommended reasoning behavior.
    """
    config_block = model.get("request_config") or {}
    return {
        "temperature": config_block.get("temperature"),
        "top_p": config_block.get("top_p"),
        "max_output_tokens": config_block.get("max_output_tokens")
        or model.get("max_output_tokens", 2048),
        "extra_body": dict(config_block.get("extra_body") or {}),
    }


def _build_payload(model: dict, messages: list[dict]) -> dict:
    config_block = effective_request_config(model)
    if model["wire_api"] == "responses":
        payload = {
            "model": resolve_model_id(model),
            "input": [
                {"role": message["role"], "content": message["content"]}
                for message in messages
            ],
            "max_output_tokens": config_block["max_output_tokens"],
        }
    else:
        payload = {
            "model": resolve_model_id(model),
            "messages": messages,
            "max_tokens": config_block["max_output_tokens"],
        }
    if config_block["temperature"] is not None:
        payload["temperature"] = config_block["temperature"]
    if config_block["top_p"] is not None:
        payload["top_p"] = config_block["top_p"]
    for key, value in config_block["extra_body"].items():
        payload[key] = value
    return payload


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
        details = usage.get("output_tokens_details") or {}
        input_details = usage.get("input_tokens_details") or {}
        return "".join(parts).strip(), {
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "reasoning_tokens": details.get("reasoning_tokens"),
            "cached_input_tokens": input_details.get("cached_tokens"),
        }

    text = ""
    choices = data.get("choices") or []
    if choices:
        message = choices[0].get("message") or {}
        text = (message.get("content") or "").strip()
    usage = data.get("usage") or {}
    details = usage.get("completion_tokens_details") or {}
    prompt_details = usage.get("prompt_tokens_details") or {}
    return text, {
        "input_tokens": usage.get("prompt_tokens"),
        "output_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "reasoning_tokens": details.get("reasoning_tokens"),
        "cached_input_tokens": prompt_details.get("cached_tokens"),
    }


# Status codes that will not succeed on retry. 402 Payment Required is a
# deterministic billing failure, so it is never retried.
_FATAL_STATUS = {400, 401, 402, 403, 404, 422}

# Some providers report billing/credit failures under a generic status code
# (for example HTTP 429 carrying an "insufficient balance" body). Those are
# deterministic too, so the body is checked before deciding to retry.
_BILLING_BODY_MARKERS = (
    "insufficient balance",
    "insufficient_quota",
    "insufficient_balance_error",
    "no resource package",
    "recharge",
    "arrears",
    "余额",
    "欠费",
    "充值",
)


def _is_billing_body(text: str) -> bool:
    lowered = (text or "").lower()
    return any(marker in lowered for marker in _BILLING_BODY_MARKERS)

# Fixed timestamp used for offline dry runs so synthetic cost figures are
# reproducible and do not depend on when the dry run was executed.
SYNTHETIC_CALL_TIMESTAMP = dt.datetime(2026, 9, 11, 2, 0, tzinfo=dt.timezone.utc)


def chat(
    model: dict,
    messages: list[dict],
    *,
    at: dt.datetime | None = None,
    fx_snapshot: dict | None = None,
) -> dict:
    """Call a model once and return text, latency, usage, and cost."""
    api_key = resolve_api_key(model)
    url = _endpoint(model)
    payload = _build_payload(model, messages)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    last_error = "unknown error"
    for attempt in range(config.MAX_RETRIES + 1):
        called_at = at or dt.datetime.now(dt.timezone.utc)
        started = time.perf_counter()
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=config.REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        else:
            latency_ms = round((time.perf_counter() - started) * 1000, 1)
            if response.status_code in _FATAL_STATUS or (
                response.status_code >= 400 and _is_billing_body(response.text)
            ):
                raise ProviderError(
                    f"{model['display_name']} rejected the request "
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
                    text, usage = _extract_text_and_usage(data, model["wire_api"])
                    if not text:
                        last_error = "provider returned an empty response"
                    else:
                        cost = pricing.price_call(
                            model,
                            usage["input_tokens"],
                            usage["output_tokens"],
                            cached_input_tokens=usage.get("cached_input_tokens"),
                            at=called_at,
                            fx_snapshot=fx_snapshot,
                        )
                        return {
                            "text": text,
                            "latency_ms": latency_ms,
                            "model_key": model["key"],
                            "model_id": resolve_model_id(model),
                            "called_at": called_at.isoformat(timespec="seconds"),
                            "attempts": attempt + 1,
                            "synthetic": False,
                            "error": None,
                            **usage,
                            **{key: cost[key] for key in cost},
                        }

        if attempt < config.MAX_RETRIES:
            time.sleep(config.RETRY_BACKOFF_SECONDS * (2**attempt))

    raise ProviderError(
        f"{model['display_name']} failed after {config.MAX_RETRIES + 1} attempt(s): {last_error}"
    )


def synthetic_call(
    model: dict,
    messages: list[dict],
    seed: str,
    *,
    fx_snapshot: dict | None = None,
) -> dict:
    """Deterministic offline stand-in used by --dry-run.

    Every value is fabricated by a hash function so the dry run exercises the
    full pipeline without network access or cost. The `synthetic` flag is
    propagated into the results document.
    """
    digest = hashlib.sha256(f"{model['key']}|{seed}".encode("utf-8")).hexdigest()
    number = int(digest[:10], 16)

    prompt_characters = sum(len(message["content"]) for message in messages)
    input_tokens = max(1, prompt_characters // 4)
    output_tokens = 160 + (number % 180)
    reasoning_tokens = (number % 40) if number % 3 == 0 else None

    text = (
        "[SYNTHETIC DRY-RUN RESPONSE — generated offline, not by a real model]\n"
        f"Model: {model['display_name']}\n"
        f"Case seed: {seed}\n"
        "This placeholder exists only to exercise the benchmark pipeline end to end."
    )

    cost = pricing.price_call(
        model,
        input_tokens,
        output_tokens,
        at=SYNTHETIC_CALL_TIMESTAMP,
        fx_snapshot=fx_snapshot,
        synthetic=True,
    )
    return {
        "text": text,
        "latency_ms": round(120 + (number % 900) / 10, 1),
        "model_key": model["key"],
        "model_id": model.get("model_id"),
        "called_at": SYNTHETIC_CALL_TIMESTAMP.isoformat(timespec="seconds"),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "reasoning_tokens": reasoning_tokens,
        "cached_input_tokens": None,
        "attempts": 1,
        "synthetic": True,
        "error": None,
        **{key: cost[key] for key in cost},
    }
