"""Frozen contracts for the engineering fixture, not a paper-derived claim."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

MAX_OUTPUT_BYTES = 8 * 1024 * 1024
Vector = Annotated[tuple[FiniteFloat, ...], Field(min_length=32, max_length=32)]


class FixtureSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: Literal["linear-fixture-v1"] = "linear-fixture-v1"
    experiment_mode: Literal["engineering_fixture"] = "engineering_fixture"
    method: Literal["row_norm_weighted_kaczmarz"] = "row_norm_weighted_kaczmarz"
    initialization: Literal["zero_vector"] = "zero_vector"
    baseline: Literal["zero_vector_relative_error_1"] = "zero_vector_relative_error_1"
    metric: Literal["relative_l2_solution_error"] = "relative_l2_solution_error"
    stopping_rule: Literal["fixed_iterations"] = "fixed_iterations"
    settings_origin: Literal["engineering_fixture_not_paper"] = "engineering_fixture_not_paper"
    rows: Literal[128] = 128
    columns: Literal[32] = 32
    generator_seed: int = Field(default=2026, ge=0, le=2**32 - 1)
    seeds: tuple[int, ...] = Field(default=(7, 23, 41), min_length=1, max_length=5)
    iterations: int = Field(default=512, ge=1, le=1024)
    invocation_timeout_seconds: FiniteFloat = Field(default=30.0, gt=0, le=180)
    target_relative_error: FiniteFloat | None = Field(default=0.01, gt=0, le=1)
    aggregation: Literal["all_trials"] = "all_trials"
    uncertainty: Literal["descriptive_only"] = "descriptive_only"
    tolerance_origin: Literal["engineering_policy_not_paper"] = "engineering_policy_not_paper"
    evaluator_version: Literal["linear-evaluator-v1"] = "linear-evaluator-v1"

    @model_validator(mode="after")
    def unique_seeds(self) -> "FixtureSpec":
        if len(set(self.seeds)) != len(self.seeds):
            raise ValueError("Seeds must be unique")
        if any(seed < 0 or seed >= 2**32 for seed in self.seeds):
            raise ValueError("Seeds must be unsigned 32-bit integers")
        return self


class TrialOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    seed: int
    iterates: tuple[Vector, ...] = Field(min_length=2, max_length=1025)


class SolverOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    schema_version: Literal["solver-output-v1"]
    trials: tuple[TrialOutput, ...] = Field(min_length=1, max_length=5)
