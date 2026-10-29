import asyncio

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError

from paper2proof.config import Settings
from paper2proof.providers.base import ProviderUnavailableError
from paper2proof.providers.offline import OfflineProvider, create_provider
from services.api.main import create_app


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    import os

    for key in os.environ:
        if key.startswith("P2P_") or key in {
            "MODEL_API_KEY",
            "MODAL_TOKEN_ID",
            "MODAL_TOKEN_SECRET",
        }:
            monkeypatch.delenv(key)


def test_offline_startup_without_credentials():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        assert client.get("/api/v1/health").json()["status"] == "ok"
        response = client.get("/api/v1/status")
        assert response.json()["provider"] == "offline"
        assert response.json()["live_inference_available"] is False
        assert response.json()["sandbox_execution_available"] is False
        assert response.headers["x-request-id"]


def test_secrets_do_not_appear_in_status_or_settings_repr():
    settings = Settings(_env_file=None, MODEL_API_KEY="private-test-value")
    with TestClient(create_app(settings)) as client:
        assert "private-test-value" not in client.get("/api/v1/status").text
    assert "private-test-value" not in repr(settings)


@pytest.mark.parametrize(
    "overrides",
    [
        {"provider": "meta"},
        {"runner": "modal"},
        {"max_repairs": 4},
        {"max_model_calls": 21},
        {"model_budget_usd": float("nan")},
        {"invocation_timeout_seconds": 180, "run_timeout_seconds": 60},
    ],
)
def test_invalid_configuration_is_rejected(overrides):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **overrides)


def test_live_provider_never_silently_falls_back():
    settings = Settings(
        _env_file=None,
        provider="meta",
        model="test-model",
        base_url="https://example.invalid",
        MODEL_API_KEY="test-key",
    )
    with pytest.raises(ProviderUnavailableError):
        create_provider(settings, fixture_json="{}")


class ExampleOutput(BaseModel):
    count: int


def test_offline_provider_validates_schema_and_labels_usage():
    result = asyncio.run(
        OfflineProvider('{"count": 2}').generate(
            prompt="test only",
            output_schema=ExampleOutput,
            max_output_tokens=100,
        )
    )
    assert result.output.count == 2
    assert result.usage.is_fixture
    assert result.usage.estimated_cost_usd is None
    with pytest.raises(ValidationError):
        asyncio.run(
            OfflineProvider('{"count": "invalid"}').generate(
                prompt="test only",
                output_schema=ExampleOutput,
                max_output_tokens=100,
            )
        )


def test_unknown_route_returns_structured_error():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.get("/api/v1/missing")
        assert response.status_code == 404
        assert response.json()["request_id"] == response.headers["x-request-id"]
        assert response.json()["retryable"] is False


def test_environment_overrides_dotenv_without_requiring_secrets(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("P2P_MAX_MODEL_CALLS=10\nP2P_PROVIDER=offline\n", encoding="utf-8")
    monkeypatch.setenv("P2P_MAX_MODEL_CALLS", "5")
    settings = Settings(_env_file=env_file)
    assert settings.max_model_calls == 5
    assert settings.provider == "offline"
