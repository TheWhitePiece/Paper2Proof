"""Offline fixture workflow. No generated code or provider calls are accepted."""

import json
import platform
import sys
from pathlib import Path
from uuid import uuid4

from paper2proof.artifacts.evidence import (
    canonical_json,
    digest,
    verify_bundle,
    write_manifest,
    write_once,
)
from paper2proof.evaluation.linear import InvalidOutput, evaluate
from paper2proof.planning.fixture import make_problem
from paper2proof.runner.local_fixture import WORKER_SOURCE, execute_reviewed_fixture
from paper2proof.schemas.experiment import FixtureSpec

PACKAGE_ROOT = Path(__file__).resolve().parent
SNAPSHOTS = {
    "solver.py": WORKER_SOURCE,
    "evaluator.py": PACKAGE_ROOT / "evaluation" / "linear.py",
    "generator.py": PACKAGE_ROOT / "planning" / "fixture.py",
    "contracts.py": PACKAGE_ROOT / "schemas" / "experiment.py",
    "requirements-dev.lock": PACKAGE_ROOT.parent / "requirements-dev.lock",
}
LIMITATIONS = [
    "Engineering fixture, not a sourced paper experiment or scientific verdict.",
    "Local reviewed code only: no network, filesystem, memory, or process isolation.",
    "Fidelity checks validate the supplied trace, not proof of arbitrary code semantics.",
    "Descriptive fixed-seed metrics, not statistical evidence for a population claim.",
    "Hashes detect byte changes against this manifest; they are not signed attestations.",
]


def run_fixture(
    output_root: Path,
    *,
    spec: FixtureSpec | None = None,
    variant: str = "reference",
    parent_attempt_id: str | None = None,
    timeout_seconds: float | None = None,
    canceled=None,
) -> Path:
    if variant not in {"reference", "wrong_update", "missing_setting"}:
        raise ValueError("Unknown fixture variant")
    spec = spec or FixtureSpec()
    if variant == "missing_setting":
        spec = spec.model_copy(update={"target_relative_error": None})
    if timeout_seconds is not None:
        spec = spec.model_copy(update={"invocation_timeout_seconds": timeout_seconds})
    # Revalidate even if an internal caller used model_copy/model_construct.
    spec = FixtureSpec.model_validate_json(spec.model_dump_json())
    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    attempt_id = uuid4().hex
    directory = output_root / attempt_id
    directory.mkdir(exist_ok=False)
    spec_bytes = canonical_json(spec.model_dump(mode="json"))
    problem = make_problem(spec)
    input_bytes = canonical_json(problem.solver_input(spec))
    write_once(directory / "spec.json", spec_bytes)
    write_once(directory / "input.json", input_bytes)
    for name, source in SNAPSHOTS.items():
        write_once(directory / name, source.read_bytes())
    if spec.target_relative_error is None:
        execution = {
            "state": "not_started",
            "exit_reason": "missing_configuration",
            "exit_code": None,
            "runner": "local_reviewed_fixture_only",
            "sandbox_job_id": None,
            "network_isolated": False,
            "resource_isolated": False,
        }
        write_once(directory / "stdout.json", b"")
        write_once(directory / "stderr.log", b"Not started: required target is unspecified.\n")
        evaluation = {
            "assessment": "inconclusive",
            "reason": "missing_target",
            "scientific_verdict": None,
            "measurements": [],
        }
    else:
        try:
            execution = execute_reviewed_fixture(
                directory,
                input_bytes,
                variant,
                timeout_seconds=spec.invocation_timeout_seconds,
                canceled=canceled,
            )
        except OSError:
            execution = {
                "state": "failed",
                "exit_reason": "launch_error",
                "exit_code": None,
                "runner": "local_reviewed_fixture_only",
                "sandbox_job_id": None,
                "network_isolated": False,
                "resource_isolated": False,
            }
            for name in ("stdout.json", "stderr.log"):
                if not (directory / name).exists():
                    write_once(directory / name, b"")
        evaluation = {"assessment": None, "scientific_verdict": None, "measurements": []}
        if execution["state"] == "completed":
            try:
                evaluation = evaluate(spec, problem, (directory / "stdout.json").read_bytes())
            except (InvalidOutput, ArithmeticError) as exc:
                execution["state"] = "failed"
                execution["exit_reason"] = "invalid_output"
                evaluation["reason"] = type(exc).__name__
        else:
            evaluation["reason"] = execution["exit_reason"]
    execution["python_version"] = sys.version
    execution["platform"] = platform.platform()
    write_once(directory / "execution.json", canonical_json(execution))
    report = {
        "schema_version": "fixture-report-v1",
        "attempt_id": attempt_id,
        "parent_attempt_id": parent_attempt_id,
        "experiment_mode": "engineering_fixture",
        "fixture_variant": variant,
        "injected_fault": variant != "reference",
        "execution_state": execution["state"],
        "exit_reason": execution["exit_reason"],
        "spec_sha256": digest(spec_bytes),
        "input_sha256": digest(input_bytes),
        "code_sha256": digest((directory / "solver.py").read_bytes()),
        "evaluator_sha256": digest((directory / "evaluator.py").read_bytes()),
        "output_sha256": digest((directory / "stdout.json").read_bytes()),
        "evaluator_version": spec.evaluator_version,
        "target_relative_error": spec.target_relative_error,
        "aggregation": spec.aggregation,
        **evaluation,
        "limitations": LIMITATIONS,
    }
    write_once(directory / "report.json", canonical_json(report))
    write_once(
        directory / "README.md",
        (
            b"# Engineering fixture evidence\n\n"
            b"Not a paper reproduction. Read report.json for measurements and limitations.\n"
            b"stdout.json is bounded numeric solver output; stderr.log is untrusted solver text.\n"
            b"execution.json is supervisor telemetry. spec.json freezes the declared target.\n"
            b"input.json contains matrix, RHS, and row schedules, not the reference solution.\n\n"
            b"From the matching Paper2Proof checkout with locked dependencies installed:\n\n"
            b"    python -m paper2proof.cli verify PATH_TO_THIS_DIRECTORY\n"
            b"    python -m paper2proof.cli rerun PATH_TO_THIS_DIRECTORY\n\n"
            b"Rerun creates a new attempt and uses only the installed reviewed solver.\n"
            b"Source/dependency snapshots must match; bundled Python is never imported.\n"
            b"Same Python/platform is recommended; cross-platform floating point is unverified.\n"
            b"Manifest integrity is not proof of authentic measurements. No PDF is included.\n"
        ),
    )
    write_manifest(directory)
    return directory


def rerun_fixture(directory: Path, output_root: Path) -> Path:
    verify_bundle(directory)
    for name, source in SNAPSHOTS.items():
        if (directory / name).read_bytes() != source.read_bytes():
            raise ValueError(f"Rerun requires matching reviewed source/environment: {name}")
    spec = FixtureSpec.model_validate_json((directory / "spec.json").read_bytes())
    expected_input = canonical_json(make_problem(spec).solver_input(spec))
    if (directory / "input.json").read_bytes() != expected_input:
        raise ValueError("Saved input does not match the frozen fixture generator/spec")
    report = json.loads((directory / "report.json").read_bytes())
    return run_fixture(
        output_root,
        spec=spec,
        variant=report["fixture_variant"],
        parent_attempt_id=report["attempt_id"],
    )
