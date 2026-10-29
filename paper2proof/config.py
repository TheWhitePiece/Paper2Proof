"""Server-only configuration. Loading settings never contacts a provider."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="P2P_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    provider: Literal["offline", "meta", "baseten", "fireworks"] = "offline"
    runner: Literal["disabled", "modal"] = "disabled"
    model: str = ""
    base_url: str = ""
    model_api_key: SecretStr = Field(default=SecretStr(""), validation_alias="MODEL_API_KEY")
    modal_token_id: SecretStr = Field(default=SecretStr(""), validation_alias="MODAL_TOKEN_ID")
    modal_token_secret: SecretStr = Field(
        default=SecretStr(""), validation_alias="MODAL_TOKEN_SECRET"
    )
    database_url: SecretStr = SecretStr("")
    redis_url: SecretStr = SecretStr("")
    max_model_calls: int = Field(default=20, ge=1, le=20)
    max_repairs: int = Field(default=3, ge=0, le=3)
    invocation_timeout_seconds: int = Field(default=180, ge=1, le=180)
    run_timeout_seconds: int = Field(default=900, ge=1, le=900)
    model_budget_usd: float = Field(default=2, gt=0, le=2, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_configuration(self) -> "Settings":
        if self.provider != "offline":
            if not self.model.strip() or not self.model_api_key.get_secret_value().strip():
                raise ValueError("A live provider requires P2P_MODEL and MODEL_API_KEY")
            if not self.base_url.startswith("https://"):
                raise ValueError("A live provider requires an HTTPS P2P_BASE_URL")
        if self.runner == "modal" and not (
            self.modal_token_id.get_secret_value().strip()
            and self.modal_token_secret.get_secret_value().strip()
        ):
            raise ValueError("Modal configuration requires MODAL_TOKEN_ID and MODAL_TOKEN_SECRET")
        if self.invocation_timeout_seconds > self.run_timeout_seconds:
            raise ValueError("Invocation timeout cannot exceed the total run timeout")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
