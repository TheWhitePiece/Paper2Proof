"""Versioned synthetic generator with fixed row schedules and known solution."""

import math
import random
from dataclasses import dataclass

from paper2proof.schemas.experiment import FixtureSpec


@dataclass(frozen=True)
class LinearProblem:
    matrix: tuple[tuple[float, ...], ...]
    rhs: tuple[float, ...]
    solution: tuple[float, ...]
    schedules: tuple[tuple[int, ...], ...]

    def solver_input(self, spec: FixtureSpec) -> dict:
        # The reference solution is held by the evaluator, not sent to the worker.
        return {
            "matrix": self.matrix,
            "rhs": self.rhs,
            "trials": [
                {"seed": seed, "rows": schedule}
                for seed, schedule in zip(spec.seeds, self.schedules, strict=True)
            ],
        }


def make_problem(spec: FixtureSpec) -> LinearProblem:
    generator = random.Random(spec.generator_seed)
    matrix = tuple(
        tuple(generator.uniform(-1, 1) for _ in range(spec.columns)) for _ in range(spec.rows)
    )
    solution = tuple(generator.uniform(-1, 1) for _ in range(spec.columns))
    rhs = tuple(math.fsum(a * x for a, x in zip(row, solution, strict=True)) for row in matrix)
    weights = [math.fsum(value * value for value in row) for row in matrix]
    schedules = tuple(
        tuple(random.Random(seed).choices(range(spec.rows), weights=weights, k=spec.iterations))
        for seed in spec.seeds
    )
    return LinearProblem(matrix, rhs, solution, schedules)
