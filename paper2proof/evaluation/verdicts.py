"""Deterministic equivalence policy; not authority to declare fixture reproduction."""

import math


def equivalence_outcome(
    *,
    completed: bool,
    comparable: bool,
    fidelity: bool,
    sufficient_trials: bool,
    mode: str,
    interval: tuple[float, float] | None,
    acceptance_band: tuple[float, float],
) -> dict:
    if mode not in {"direct", "adapted"}:
        raise ValueError("Unknown experiment mode")
    if (
        not all(math.isfinite(value) for value in acceptance_band)
        or acceptance_band[0] > acceptance_band[1]
    ):
        raise ValueError("Invalid frozen acceptance band")
    if not completed:
        return {
            "scientific_verdict": None,
            "adapted_target": None,
            "reason": "execution_incomplete",
        }
    if not comparable or not fidelity or not sufficient_trials or interval is None:
        return {
            "scientific_verdict": "inconclusive",
            "adapted_target": None,
            "reason": "evidence_gates_failed",
        }
    lower, upper = interval
    if not all(math.isfinite(value) for value in interval) or lower > upper:
        raise ValueError("Invalid uncertainty interval")
    left, right = acceptance_band
    outcome = (
        "inside"
        if left <= lower <= upper <= right
        else "outside"
        if upper < left or lower > right
        else "overlap"
    )
    if mode == "adapted":
        return {
            "scientific_verdict": "inconclusive",
            "adapted_target": outcome,
            "reason": "adapted_conditions",
        }
    return {
        "scientific_verdict": {
            "inside": "reproduced_within_tolerance",
            "outside": "not_reproduced_in_this_run",
            "overlap": "inconclusive",
        }[outcome],
        "adapted_target": None,
        "reason": outcome,
    }
