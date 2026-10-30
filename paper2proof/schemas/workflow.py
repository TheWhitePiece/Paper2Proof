"""Provenance, human review and generation contracts for the local workflow."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceSpan(Contract):
    id: str
    page: int = Field(ge=1, le=50)
    bbox: tuple[FiniteFloat, FiniteFloat, FiniteFloat, FiniteFloat]
    text: str = Field(min_length=1, max_length=20000)


class Paper(Contract):
    state: Literal["ready"] = "ready"
    id: str
    sha256: str
    pages: int = Field(ge=1, le=50)
    spans: tuple[SourceSpan, ...] = Field(max_length=20000)
    warnings: tuple[str, ...]
    parser_version: str


class ClaimDraft(Contract):
    statement: str = Field(min_length=5, max_length=2000)
    span_id: str = Field(max_length=100)
    quote: str = Field(min_length=5, max_length=2000)
    metric: Literal["relative_l2_solution_error", "unsupported"]
    unit: str = Field(default="dimensionless_ratio", max_length=100)
    direction: Literal["smaller_is_better", "larger_is_better", "unknown"] = "smaller_is_better"
    reported_value: FiniteFloat | None = None
    unknown_reason: str = Field(default="Not specified in selected passage", max_length=1000)
    method: Literal["randomized_kaczmarz", "unknown"] = "unknown"

    @model_validator(mode="after")
    def unknown_is_explained(self):
        if self.reported_value is None and not self.unknown_reason.strip():
            raise ValueError("Unknown reported value requires a reason")
        return self


class Claim(ClaimDraft):
    id: str
    paper_id: str
    origin: Literal["user_provided"] = "user_provided"
    version: int = 1
    previous_version_id: str | None = None


class Setting(Contract):
    value: str | int | float | None
    origin: Literal["paper_sourced", "user_provided", "assumed"]
    rationale: str = Field(min_length=1, max_length=1000)
    source_span_id: str | None = None
    source_quote: str | None = Field(default=None, max_length=2000)


class ReviewDraft(Contract):
    mode: Literal["adapted", "direct"] = "adapted"
    target_relative_error: FiniteFloat | None = Field(default=None, gt=0, le=1)
    target_rationale: str = Field(default="", max_length=2000)
    settings: dict[str, Setting]
    assumptions: tuple[str, ...] = Field(default=(), max_length=30)


class SpecVersion(ReviewDraft):
    id: str
    claim_id: str
    paper_id: str
    version: int
    previous_version_id: str | None
    spec_hash: str
    blockers: tuple[str, ...]
    evaluator_version: Literal["linear-evaluator-v1"] = "linear-evaluator-v1"


class CodeFile(Contract):
    path: str = Field(max_length=100)
    content: str = Field(min_length=1, max_length=64000)


class CodeProposal(Contract):
    schema_version: Literal["code-proposal-v1"] = "code-proposal-v1"
    spec_hash: str
    source_span_ids: tuple[str, ...] = Field(min_length=1, max_length=20)
    explanation: str = Field(min_length=1, max_length=4000)
    files: tuple[CodeFile, ...] = Field(min_length=1, max_length=3)


class StartRequest(Contract):
    kind: Literal["generation_preview", "engineering_fixture"]
    spec_hash: str
