"""Provider retry-policy tests for deterministic configuration errors.

These tests replace the HTTP transport with a fake so no network call is made.
They verify that deterministic billing/configuration failures are never
retried, while transient failures still use the bounded retry loop.
"""

from __future__ import annotations

import unittest
from unittest import mock

from src import providers


def _model():
    return {
        "key": "test_model",
        "display_name": "Test model",
        "api_key_env": "TEST_PROVIDER_API_KEY",
        "base_url": "https://example.invalid/v1",
        "wire_api": "chat_completions",
        "model_id": "test-model-id",
        "request_config": {},
        "max_output_tokens": 64,
    }


class TestProviderErrorPolicy(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.dict(
            "os.environ", {"TEST_PROVIDER_API_KEY": "test-key-value"}
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _call(self, status_code, text, *, side_effect=None):
        response = mock.Mock()
        response.status_code = status_code
        response.text = text
        response.json.return_value = {}
        with mock.patch(
            "src.providers.requests.post",
            side_effect=side_effect or (lambda *a, **k: response),
        ) as post:
            with mock.patch.object(providers.config, "RETRY_BACKOFF_SECONDS", 0):
                with self.assertRaises(providers.ProviderError):
                    providers.chat(_model(), [{"role": "user", "content": "hi"}])
        return post.call_count

    def test_payment_required_is_not_retried(self):
        calls = self._call(402, '{"error":"insufficient balance"}')
        self.assertEqual(calls, 1)

    def test_billing_body_under_429_is_not_retried(self):
        calls = self._call(
            429,
            '{"error":{"code":"1113","message":"Insufficient balance or no '
            'resource package. Please recharge."}}',
        )
        self.assertEqual(calls, 1)

    def test_transient_rate_limit_is_retried(self):
        calls = self._call(429, '{"error":"rate limit exceeded"}')
        self.assertEqual(calls, providers.config.MAX_RETRIES + 1)

    def test_bad_request_is_not_retried(self):
        calls = self._call(400, '{"error":"unsupported field"}')
        self.assertEqual(calls, 1)


if __name__ == "__main__":
    unittest.main()
