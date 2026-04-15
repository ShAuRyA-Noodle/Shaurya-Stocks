"""Sanity checks on Settings — fail fast if someone breaks the contract."""

from __future__ import annotations

from quant.config import get_settings


def test_settings_loads() -> None:
    s = get_settings()
    assert s.app_name == "quant-platform"
    assert s.app_env in {"development", "staging", "production"}


def test_required_tier1_providers_present() -> None:
    s = get_settings()
    assert s.polygon_api_key.get_secret_value(), "Polygon key missing"
    assert s.alpaca_api_key_id.get_secret_value(), "Alpaca key ID missing"
    assert s.alpaca_api_secret_key.get_secret_value(), "Alpaca secret missing"
    assert s.fred_api_key.get_secret_value(), "FRED key missing"


def test_provider_summary_shape() -> None:
    summary = get_settings().provider_summary()
    assert set(summary.keys()) >= {"polygon", "alpaca", "fred", "groq"}
    assert all(isinstance(v, bool) for v in summary.values())


def test_cors_origins_parsed() -> None:
    origins = get_settings().cors_origins_list
    assert "http://localhost:3000" in origins
