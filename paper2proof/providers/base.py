from typing import Generic, Protocol, TypeVar

from pydantic import BaseModel, ConfigDict, Field

Output = TypeVar("Output", bound=BaseModel)


class ProviderCapabilities(BaseModel):
    model_config = ConfigDict(frozen=True)
    json_schema: bool = False
    tool_calling: bool = False
    reasoning_options: bool = False
    max_output_tokens: int = Field(default=1024, gt=0)


class UsageRecord(BaseModel):
    provider: str
    model: str
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    request_id: str | None = None
    is_fixture: bool = False


class GenerationResult(BaseModel, Generic[Output]):
    output: Output
    usage: UsageRecord


class StructuredProvider(Protocol):
    capabilities: ProviderCapabilities

    async def generate(
        self, *, prompt: str, output_schema: type[Output], max_output_tokens: int
    ) -> GenerationResult[Output]: ...


class ProviderUnavailableError(RuntimeError):
    """Requested integration is not implemented; never silently fall back."""
