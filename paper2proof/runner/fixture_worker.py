"""Standalone reviewed solver. No imports from the evaluator or application.

This file is snapshotted by the local runner. It is not a sandbox and must never
be replaced by generated or user-supplied code for local execution.
"""

import json
import math
import sys


def solve(payload: dict, *, wrong_update: bool = False) -> dict:
    matrix, rhs = payload["matrix"], payload["rhs"]
    norms = [math.fsum(a * a for a in row) for row in matrix]
    trials = []
    for trial in payload["trials"]:
        current = [0.0] * len(matrix[0])
        trace = [current.copy()]
        for index in trial["rows"]:
            row = matrix[index]
            residual = rhs[index] - math.fsum(a * x for a, x in zip(row, current, strict=True))
            coefficient = residual / norms[index]
            if wrong_update:
                coefficient *= 0.5  # Deliberately injected method error.
            current = [x + coefficient * a for x, a in zip(current, row, strict=True)]
            trace.append(current)
        trials.append({"seed": trial["seed"], "iterates": trace})
    return {"schema_version": "solver-output-v1", "trials": trials}


if __name__ == "__main__":
    variant = sys.argv[1]
    if variant not in {"reference", "wrong_update"}:
        raise SystemExit("Unsupported reviewed fixture variant")
    payload = json.load(sys.stdin)
    if variant == "wrong_update":
        print("INJECTED FAULT: claimed relative_error=0; claimed success=true", file=sys.stderr)
    else:
        print("Reviewed engineering fixture; no scientific verdict computed here.", file=sys.stderr)
    json.dump(solve(payload, wrong_update=variant == "wrong_update"), sys.stdout, allow_nan=False)
