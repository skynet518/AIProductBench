"""Native pricing, tiering, time-of-day windows, and CNY normalization."""

import datetime as dt
import unittest

from src import config, pricing

UTC = dt.timezone.utc
MONDAY_PEAK = dt.datetime(2026, 9, 14, 2, 0, tzinfo=UTC)
MONDAY_OFF_PEAK = dt.datetime(2026, 9, 14, 0, 0, tzinfo=UTC)
SATURDAY_PEAK_HOUR = dt.datetime(2026, 9, 19, 2, 0, tzinfo=UTC)


def model(pricing_block, key="m1", family="Test", provider="test") -> dict:
    return {
        "key": key,
        "display_name": key,
        "model_family": family,
        "provider": provider,
        "provider_key": provider,
        "model_id": "test-model-1",
        "pricing": pricing_block,
    }


def flat(input_rate=1.0, output_rate=2.0, currency="USD", status="verified", limit=None) -> dict:
    return {
        "status": status,
        "snapshot_date": "2026-09-11",
        "native_currency": currency,
        "unit": "per_1m_tokens",
        "source": "test source",
        "input": input_rate,
        "output": output_rate,
        "input_tier_limit_tokens": limit,
        "time_of_day": None,
        "notes": [],
    }


class TestNativePricing(unittest.TestCase):
    def test_flat_rate_cost(self):
        result = pricing.native_price_call(model(flat(1.0, 2.0)), 1_000_000, 1_000_000)
        self.assertAlmostEqual(result["native_cost"], 3.0, places=6)

    def test_missing_tokens_yields_no_cost(self):
        result = pricing.native_price_call(model(flat()), None, None)
        self.assertIsNone(result["native_cost"])

    def test_unverified_pricing_raises(self):
        block = flat(status="unverified")
        block["input"] = None
        block["output"] = None
        with self.assertRaises(pricing.PricingError):
            pricing.native_price_call(model(block), 100, 100)

    def test_input_tier_limit_is_enforced(self):
        block = flat(limit=32_000)
        with self.assertRaises(pricing.PricingError) as caught:
            pricing.native_price_call(model(block), 40_000, 100)
        self.assertIn("exceeds", str(caught.exception))

    def test_input_tier_boundary_is_inclusive(self):
        result = pricing.native_price_call(model(flat(limit=32_000)), 32_000, 100)
        self.assertIsNotNone(result["native_cost"])


class TestTimeOfDayPricing(unittest.TestCase):
    def deepseek_block(self) -> dict:
        block = flat(0.22, 0.66, limit=None)
        block["time_of_day"] = {
            "off_peak": {"input": 0.22, "output": 0.66},
            "peak": {"input": 0.44, "output": 1.32},
            "peak_windows_utc": [[1, 4], [6, 10]],
            "peak_weekdays_only": True,
        }
        return block

    def test_peak_and_off_peak_windows(self):
        block = self.deepseek_block()
        peak = pricing.native_price_call(model(block), 1_000_000, 0, at=MONDAY_PEAK)
        off_peak = pricing.native_price_call(model(block), 1_000_000, 0, at=MONDAY_OFF_PEAK)
        self.assertEqual(peak["window"], "peak")
        self.assertEqual(off_peak["window"], "off_peak")
        self.assertAlmostEqual(peak["native_cost"], 0.44, places=6)
        self.assertAlmostEqual(off_peak["native_cost"], 0.22, places=6)

    def test_weekend_is_always_off_peak(self):
        result = pricing.native_price_call(
            model(self.deepseek_block()), 1_000_000, 0, at=SATURDAY_PEAK_HOUR
        )
        self.assertEqual(result["window"], "off_peak")

    def test_window_boundaries_are_start_inclusive_end_exclusive(self):
        block = self.deepseek_block()
        for hour, expected in [(0, "off_peak"), (1, "peak"), (3, "peak"), (4, "off_peak"), (6, "peak"), (10, "off_peak")]:
            at = MONDAY_OFF_PEAK.replace(hour=hour)
            result = pricing.native_price_call(model(block), 1000, 0, at=at)
            self.assertEqual(result["window"], expected, msg=f"hour {hour}")

    def test_time_of_day_without_timestamp_raises(self):
        with self.assertRaises(pricing.PricingError):
            pricing.native_price_call(model(self.deepseek_block()), 100, 100)


class TestCnyNormalization(unittest.TestCase):
    FX = {
        "status": "verified",
        "fx_pair": "USD/CNY",
        "fx_rate": 7.2,
        "fx_snapshot_date": "2026-09-11",
        "source": "test FX source",
    }

    def test_native_cny_needs_no_conversion(self):
        result = pricing.normalize_to_cny(10.0, "CNY", config.FX_SNAPSHOT)
        self.assertEqual(result["normalization_method"], "native")
        self.assertEqual(result["normalized_cost_cny"], 10.0)

    def test_usd_without_fx_snapshot_stays_null(self):
        result = pricing.normalize_to_cny(1.0, "USD", config.FX_SNAPSHOT)
        self.assertEqual(result["normalization_method"], "unavailable")
        self.assertIsNone(result["normalized_cost_cny"])
        self.assertIn("no FX snapshot configured", result["normalization_note"])

    def test_usd_with_fx_snapshot_converts(self):
        result = pricing.normalize_to_cny(1.0, "USD", self.FX)
        self.assertEqual(result["normalization_method"], "fx")
        self.assertEqual(result["normalized_cost_cny"], 7.2)
        self.assertEqual(result["fx_rate"], 7.2)
        self.assertEqual(result["fx_snapshot_date"], "2026-09-11")

    def test_wrong_fx_pair_is_rejected(self):
        wrong = dict(self.FX, fx_pair="EUR/CNY")
        result = pricing.normalize_to_cny(1.0, "USD", wrong)
        self.assertIsNone(result["normalized_cost_cny"])
        self.assertIn("does not match", result["normalization_note"])

    def test_zero_or_missing_rate_is_not_used(self):
        for rate in (None, 0, -1):
            result = pricing.normalize_to_cny(1.0, "USD", dict(self.FX, fx_rate=rate))
            self.assertIsNone(result["normalized_cost_cny"])

    def test_no_native_cost_yields_no_cny(self):
        result = pricing.normalize_to_cny(None, "USD", self.FX)
        self.assertIsNone(result["normalized_cost_cny"])

    def test_production_fx_snapshot_is_not_configured(self):
        self.assertIsNone(config.FX_SNAPSHOT["fx_rate"])
        self.assertEqual(config.FX_SNAPSHOT["status"], "unverified")

    def test_synthetic_fx_fixture_is_labelled(self):
        self.assertTrue(config.SYNTHETIC_FX_SNAPSHOT["synthetic"])
        self.assertIn("not a real", config.SYNTHETIC_FX_SNAPSHOT["source"])


class TestPriceCall(unittest.TestCase):
    def test_unpriced_model_reports_reason_instead_of_raising(self):
        block = flat(status="unverified")
        block["input"] = None
        block["output"] = None
        result = pricing.price_call(model(block), 100, 100, fx_snapshot=None)
        self.assertIsNone(result["native_cost"])
        self.assertIsNone(result["normalized_cost_cny"])
        self.assertIsNotNone(result["cost_error"])

    def test_cost_error_does_not_mask_missing_usage(self):
        result = pricing.price_call(model(flat()), None, None, fx_snapshot=None)
        self.assertIsNone(result["native_cost"])
        self.assertIsNone(result["cost_error"])

    def test_synthetic_pricing_is_deterministic_and_labelled(self):
        entry = model(flat(status="unverified"), key="synthetic-check")
        first = pricing.synthetic_pricing(entry)
        second = pricing.synthetic_pricing(entry)
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "synthetic")
        self.assertIn("not a published price", first["source"])

    def test_synthetic_pricing_covers_both_currency_paths(self):
        currencies = {
            pricing.synthetic_pricing(model(flat(), key=f"model-{index}"))["native_currency"]
            for index in range(12)
        }
        self.assertEqual(currencies, {"CNY", "USD"})


if __name__ == "__main__":
    unittest.main()
