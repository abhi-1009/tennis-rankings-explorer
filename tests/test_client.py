"""API client error handling: retries on rate limits, clear errors on bad keys, no endless loops."""
import pytest
import requests

from api import config, sportradar_client as client


class FakeResponse:
    def __init__(self, status, payload=None, text=""):
        self.status_code, self._payload, self.text = status, payload or {}, text

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def fast_and_keyed(monkeypatch):
    monkeypatch.setattr(config, "API_KEY", "test-key")
    monkeypatch.setattr(client.time, "sleep", lambda seconds: None)


def script(monkeypatch, outcomes):
    """Make requests.get return/raise the given outcomes in order; returns the list of recorded calls."""
    calls, queue = [], list(outcomes)

    def fake_get(url, headers=None, timeout=None):
        calls.append({"url": url, "headers": headers})
        outcome = queue.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
    monkeypatch.setattr(client.requests, "get", fake_get)
    return calls


def test_success_returns_json_and_sends_the_key_in_a_header(monkeypatch):
    calls = script(monkeypatch, [FakeResponse(200, {"ok": True})])
    assert client.fetch_json("competitions") == {"ok": True}
    assert calls[0]["headers"] == {"x-api-key": "test-key"}
    assert "api_key" not in calls[0]["url"]                 # the key must never be in the URL


def test_rate_limit_and_server_errors_are_retried(monkeypatch):
    calls = script(monkeypatch, [FakeResponse(429), FakeResponse(503), FakeResponse(200, {"ok": 1})])
    assert client.fetch_json("complexes") == {"ok": 1}
    assert len(calls) == 3


def test_bad_key_fails_immediately_with_a_clear_message(monkeypatch):
    calls = script(monkeypatch, [FakeResponse(403, text="forbidden")])
    with pytest.raises(client.SportRadarError, match="403"):
        client.fetch_json("competitions")
    assert len(calls) == 1                                   # no pointless retries


def test_network_errors_stop_after_the_retry_limit(monkeypatch):
    calls = script(monkeypatch, [requests.ConnectionError("down")] * config.MAX_RETRIES)
    with pytest.raises(client.SportRadarError, match="Gave up"):
        client.fetch_json("doubles_rankings")
    assert len(calls) == config.MAX_RETRIES


def test_missing_api_key_is_reported_before_any_request(monkeypatch):
    monkeypatch.setattr(config, "API_KEY", "")
    calls = script(monkeypatch, [])
    with pytest.raises(client.SportRadarError, match="API_KEY"):
        client.fetch_json("competitions")
    assert calls == []
