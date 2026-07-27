import importlib

import pytest


def test_cache_ttl_is_configurable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CACHE_TTL_SECONDS", "120")
    import app.config as config

    importlib.reload(config)
    assert config.CACHE_TTL_SECONDS == 120

    monkeypatch.setenv("CACHE_TTL_SECONDS", "300")
    importlib.reload(config)
    assert config.CACHE_TTL_SECONDS == 300


def test_rate_limit_settings_are_configurable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "5")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "10")
    import app.config as config

    importlib.reload(config)
    assert config.RATE_LIMIT_REQUESTS == 5
    assert config.RATE_LIMIT_WINDOW_SECONDS == 10

    monkeypatch.delenv("RATE_LIMIT_REQUESTS", raising=False)
    monkeypatch.delenv("RATE_LIMIT_WINDOW_SECONDS", raising=False)
    importlib.reload(config)
