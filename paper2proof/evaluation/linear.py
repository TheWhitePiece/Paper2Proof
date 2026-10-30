import json
import math

from pydantic import ValidationError

from paper2proof.planning.fixture import LinearProblem
from paper2proof.schemas.experiment import MAX_OUTPUT_BYTES, FixtureSpec, SolverOutput


class InvalidOutput(ValueError):
    """Untrusted output is malformed, oversized, or incompatible with the spec."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidOutput("Duplicate JSON key")
        result[key] = value
    return result


def parse_output(data: bytes, spec: FixtureSpec) -> SolverOutput:
    if len(data) > MAX_OUTPUT_BYTES:
        raise InvalidOutput("Output exceeds byte limit")
    try:
        # Reject ambiguous duplicate keys before Pydantic validates numeric shapes.
        json.loads(data, object_pairs_hook=_unique_object)
        output = SolverOutput.model_validate_json(data)
    except (ValueError, UnicodeError, RecursionError, ValidationError) as exc:
        raise InvalidOutput("Output must be bounded, finite, schema-valid numeric JSON") from exc
    seeds = [trial.seed for trial in output.trials]
    if seeds != list(spec.seeds):
        raise InvalidOutput("Missing, duplicate, reordered, or unexpected trial seeds")
    if any(len(trial.iterates) != spec.iterations + 1 for trial in output.trials):
        raise InvalidOutput("Every trial must contain the complete iteration trace")
    return output


def relative_norm(vector, reference) -> float:
    denominator = math.sqrt(math.fsum(value * value for value in reference))
    if denominator <= 0:
        raise ValueError("Relative metric requires a nonzero reference norm")
    return math.sqrt(math.fsum(value * value for value in vector)) / denominator


def evaluate(spec: FixtureSpec, problem: LinearProblem, data: bytes) -> dict:
    try:
        return _evaluate(spec, problem, data)
    except (ArithmeticError, ValueError) as exc:
        if isinstance(exc, InvalidOutput):
            raise
        raise InvalidOutput("Numeric output cannot be evaluated safely") from exc


def _evaluate(spec: FixtureSpec, problem: LinearProblem, data: bytes) -> dict:
    output = parse_output(data, spec)
    measurements = []
    fidelity_failures = []
    for trial, schedule in zip(output.trials, problem.schedules, strict=True):
        if any(value != 0.0 for value in trial.iterates[0]):
            fidelity_failures.append({"seed": trial.seed, "iteration": 0})
        # Independent update-rule verification against trusted rows, not solver logs.
        for iteration, row_index in enumerate(schedule, start=1):
            previous, observed = trial.iterates[iteration - 1 : iteration + 1]
            row = problem.matrix[row_index]
            dot = math.fsum(row[j] * previous[j] for j in range(spec.columns))
            norm_squared = math.fsum(a * a for a in row)
            step = (problem.rhs[row_index] - dot) / norm_squared
            expected = tuple(previous[j] + step * row[j] for j in range(spec.columns))
            if not all(
                math.isclose(actual, wanted, rel_tol=1e-10, abs_tol=1e-12)
                for actual, wanted in zip(observed, expected, strict=True)
            ):
                fidelity_failures.append({"seed": trial.seed, "iteration": iteration})
                break  # One diagnostic per failed trial bounds report size.
        final = trial.iterates[-1]
        error = [final[j] - problem.solution[j] for j in range(spec.columns)]
        residual = [
            math.fsum(a * x for a, x in zip(row, final, strict=True)) - b
            for row, b in zip(problem.matrix, problem.rhs, strict=True)
        ]
        relative_error = relative_norm(error, problem.solution)
        relative_residual = relative_norm(residual, problem.rhs)
        if not math.isfinite(relative_error) or not math.isfinite(relative_residual):
            raise InvalidOutput("Computed metric is non-finite")
        measurements.append(
            {
                "seed": trial.seed,
                "relative_solution_error": relative_error,
                "relative_residual": relative_residual,
                "unit": "dimensionless_ratio",
                "iterations": spec.iterations,
            }
        )
    if fidelity_failures:
        assessment, reason = "inconclusive", "method_fidelity_failed"
    elif spec.target_relative_error is None:
        assessment, reason = "inconclusive", "missing_target"
    elif all(m["relative_solution_error"] <= spec.target_relative_error for m in measurements):
        assessment, reason = "fixture_target_met", "all_declared_trials_met_target"
    else:
        assessment, reason = "fixture_target_not_met", "at_least_one_trial_outside_target"
    return {
        "assessment": assessment,
        "reason": reason,
        "scientific_verdict": None,
        "measurements": measurements,
        "method_fidelity_passed": not fidelity_failures,
        "fidelity_failures": fidelity_failures,
        "uncertainty": "descriptive_only; no population-level or paper-reproduction inference",
    }
