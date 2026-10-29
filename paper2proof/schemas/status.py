from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RunState(StrEnum):
    QUEUED = "queued"
    PLANNING = "planning"
    GENERATING = "generating"
    TESTING = "testing"
    EXECUTING = "executing"
    EVALUATING = "evaluating"
    REPAIRING = "repairing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    BUDGET_EXCEEDED = "budget_exceeded"


class ScientificOutcome(StrEnum):
    REPRODUCED = "reproduced_within_tolerance"
    NOT_REPRODUCED = "not_reproduced_in_this_run"
    INCONCLUSIVE = "inconclusive"


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    version: str


class DevelopmentStatus(BaseModel):
    stage: Literal["foundation"] = "foundation"
    provider: str
    runner: str
    live_inference_available: Literal[False] = False
    sandbox_execution_available: Literal[False] = False
    persistence_available: Literal[False] = False
    message: str


class APIError(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    message: str
    details: list[dict[str, str]] = Field(default_factory=list)
    request_id: str
    retryable: bool = False
