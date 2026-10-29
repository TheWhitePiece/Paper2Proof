"""Explicit test responses, never fabricated model or scientific results."""

from paper2proof.config import Settings
from paper2proof.providers.base import (
    GenerationResult,
    Output,
    ProviderCapabilities,
    ProviderUnavailableError,
    StructuredProvider,
    UsageRecord,
)


class OfflineProvider:
    capabilities = ProviderCapabilities(json_schema=True)

    def __init__(self, fixture_json: str):
        if len(fixture_json.encode("utf-8")) > 64 * 1024:
            raise ValueError("Offline fixture exceeds 64 KiB")
        self._fixture_json = fixture_json

    async def generate(
        self, *, prompt: str, output_schema: type[Output], max_output_tokens: int
    ) -> GenerationResult[Output]:
        if not 1 <= max_output_tokens <= self.capabilities.max_output_tokens:
            raise ValueError("Requested output token limit exceeds provider capability")
        return GenerationResult(
            output=output_schema.model_validate_json(self._fixture_json),
            usage=UsageRecord(provider="offline", model="fixture-v1", is_fixture=True),
        )


def create_provider(settings: Settings, *, fixture_json: str) -> StructuredProvider:
    if settings.provider != "offline":
        raise ProviderUnavailableError(
            "Live provider adapters are deferred. Credentials alone do not enable inference."
        )
    return OfflineProvider(fixture_json)
