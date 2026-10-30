import json
import math

import pytest
from pydantic import ValidationError

from paper2proof.artifacts.evidence import canonical_json, digest, verify_bundle, write_once
from paper2proof.evaluation.linear import InvalidOutput, evaluate, parse_output
from paper2proof.experiments import rerun_fixture, run_fixture
from paper2proof.planning.fixture import LinearProblem, make_problem
from paper2proof.runner import local_fixture
from paper2proof.schemas.experiment import MAX_OUTPUT_BYTES, FixtureSpec


def read_report(directory):
    return json.loads((directory / "report.json").read_bytes())


def orthogonal_case(iterations=32):
    spec = FixtureSpec(seeds=(7,), iterations=iterations)
    matrix = tuple(tuple(float(i % 32 == j) for j in range(32)) for i in range(128))
    problem = LinearProblem(matrix, (1.0,) * 128, (1.0,) * 32, (tuple(range(iterations)),))
    trace = [[float(j < iteration) for j in range(32)] for iteration in range(iterations + 1)]
    output = {"schema_version": "solver-output-v1", "trials": [{"seed": 7, "iterates": trace}]}
    return spec, problem, output


def test_generator_is_deterministic_and_consistent():
    spec = FixtureSpec()
    problem = make_problem(spec)
    assert problem == make_problem(spec)
    assert len(problem.matrix) == 128
    assert len(problem.matrix[0]) == 32
    for row, rhs in zip(problem.matrix, problem.rhs, strict=True):
        assert math.fsum(a * x for a, x in zip(row, problem.solution, strict=True)) == rhs
    assert "solution" not in problem.solver_input(spec)


def test_frozen_spec_and_missing_target():
    with pytest.raises(ValidationError):
        FixtureSpec(seeds=(1, 1))
    with pytest.raises(ValidationError):
        FixtureSpec(iterations=100000)
    spec = FixtureSpec()
    with pytest.raises(ValidationError):
        spec.target_relative_error = 0.5
    assert FixtureSpec(target_relative_error=None).target_relative_error is None


def test_independent_known_metric_fixtures():
    spec, problem, output = orthogonal_case()
    result = evaluate(spec, problem, canonical_json(output))
    assert result["assessment"] == "fixture_target_met"
    assert result["measurements"][0]["relative_solution_error"] == 0
    assert result["measurements"][0]["relative_residual"] == 0
    assert result["scientific_verdict"] is None
    spec, problem, output = orthogonal_case(iterations=1)
    result = evaluate(spec, problem, canonical_json(output))
    assert result["assessment"] == "fixture_target_not_met"
    assert result["measurements"][0]["relative_solution_error"] == pytest.approx(math.sqrt(31 / 32))
    assert result["measurements"][0]["unit"] == "dimensionless_ratio"


def test_perfect_final_answer_with_wrong_method_cannot_pass():
    spec, problem, output = orthogonal_case()
    output["trials"][0]["iterates"] = [[1.0] * 32 for _ in range(33)]
    result = evaluate(spec, problem, canonical_json(output))
    assert result["measurements"][0]["relative_solution_error"] == 0
    assert result["assessment"] == "inconclusive"
    assert result["method_fidelity_passed"] is False


@pytest.mark.parametrize("fault", ["nan", "infinity", "bool", "shape", "missing", "seed", "extra"])
def test_malformed_outputs_are_rejected(fault):
    spec, _, output = orthogonal_case(iterations=1)
    if fault in {"nan", "infinity", "bool"}:
        output["trials"][0]["iterates"][1][0] = {
            "nan": float("nan"),
            "infinity": float("inf"),
            "bool": True,
        }[fault]
    elif fault == "shape":
        output["trials"][0]["iterates"][1].pop()
    elif fault == "missing":
        output["trials"] = []
    elif fault == "seed":
        output["trials"][0]["seed"] = 99
    else:
        output["claimed_success"] = True
    with pytest.raises(InvalidOutput):
        parse_output(json.dumps(output).encode(), spec)


def test_duplicate_keys_oversized_outputs_and_incomplete_traces_fail():
    spec, _, output = orthogonal_case(iterations=1)
    encoded = canonical_json(output)
    with pytest.raises(InvalidOutput):
        parse_output(encoded.replace(b'"seed":7', b'"seed":7,"seed":7'), spec)
    with pytest.raises(InvalidOutput):
        parse_output(b" " * (MAX_OUTPUT_BYTES + 1), spec)
    with pytest.raises(InvalidOutput):
        parse_output(encoded, FixtureSpec(seeds=(7,), iterations=2))


def test_finite_but_overflowing_numeric_output_fails_safely():
    spec, problem, output = orthogonal_case(iterations=1)
    output["trials"][0]["iterates"][1] = [1e308] * 32
    with pytest.raises(InvalidOutput):
        evaluate(spec, problem, canonical_json(output))


def test_reference_run_report_hashes_and_clean_rerun(tmp_path):
    first = run_fixture(tmp_path / "first")
    report = read_report(first)
    assert report["execution_state"] == "completed"
    assert report["assessment"] == "fixture_target_met"
    assert report["scientific_verdict"] is None
    verify_bundle(first)
    spec = FixtureSpec.model_validate_json((first / "spec.json").read_bytes())
    independent = evaluate(spec, make_problem(spec), (first / "stdout.json").read_bytes())
    assert report["measurements"] == independent["measurements"]
    assert report["spec_sha256"] == digest((first / "spec.json").read_bytes())
    second = rerun_fixture(first, tmp_path / "fresh")
    rerun = read_report(second)
    assert rerun["parent_attempt_id"] == report["attempt_id"]
    assert rerun["attempt_id"] != report["attempt_id"]
    assert rerun["measurements"] == report["measurements"]
    assert (second / "stdout.json").read_bytes() == (first / "stdout.json").read_bytes()
    assert (second / "input.json").read_bytes() == (first / "input.json").read_bytes()
    with pytest.raises(FileExistsError):
        write_once(first / "spec.json", b"changed")


def test_wrong_update_with_forged_success_log_is_inconclusive(tmp_path):
    directory = run_fixture(tmp_path, variant="wrong_update")
    report = read_report(directory)
    assert report["execution_state"] == "completed"
    assert report["assessment"] == "inconclusive"
    assert report["reason"] == "method_fidelity_failed"
    assert report["injected_fault"] is True
    assert "claimed success=true" in (directory / "stderr.log").read_text()
    verify_bundle(directory)


def test_missing_setting_blocks_process_start(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Missing target must block execution")

    monkeypatch.setattr("paper2proof.experiments.execute_reviewed_fixture", forbidden)
    directory = run_fixture(tmp_path, variant="missing_setting")
    report = read_report(directory)
    assert report["execution_state"] == "not_started"
    assert report["assessment"] == "inconclusive"
    assert report["measurements"] == []
    verify_bundle(directory)


@pytest.mark.parametrize("failure", ["timeout", "output_limit"])
def test_supervisor_bounds_reviewed_process(tmp_path, monkeypatch, failure):
    timeout = 0.000001 if failure == "timeout" else 30
    if failure == "output_limit":
        monkeypatch.setattr(local_fixture, "MAX_OUTPUT_BYTES", 128)
    directory = run_fixture(tmp_path, timeout_seconds=timeout)
    report = read_report(directory)
    assert report["execution_state"] == "failed"
    assert report["exit_reason"] == failure
    assert report["scientific_verdict"] is None
    assert report["assessment"] is None
    verify_bundle(directory)


def test_secret_environment_is_not_forwarded(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "private-test-key")
    monkeypatch.setenv("P2P_DATABASE_URL", "private-test-db")
    monkeypatch.setenv("PYTHONPATH", "untrusted-module-path")
    assert "MODEL_API_KEY" not in local_fixture.fixture_environment()
    assert "P2P_DATABASE_URL" not in local_fixture.fixture_environment()
    assert "PYTHONPATH" not in local_fixture.fixture_environment()


def test_evidence_tamper_and_traversal_rejected(tmp_path):
    directory = run_fixture(tmp_path, variant="missing_setting")
    manifest_path = directory / "manifest.json"
    original = manifest_path.read_bytes()
    manifest = json.loads(original)
    manifest["files"]["../outside"] = manifest["files"].pop("stderr.log")
    manifest_path.write_bytes(canonical_json(manifest))
    with pytest.raises(ValueError, match="allowlisted"):
        verify_bundle(directory)
    manifest_path.write_bytes(original)
    (directory / "report.json").write_bytes(b"{}")
    with pytest.raises(ValueError, match="integrity"):
        verify_bundle(directory)


def test_local_runner_rejects_replaced_solver(tmp_path):
    (tmp_path / "solver.py").write_text("raise SystemExit('do not execute')")
    with pytest.raises(ValueError, match="reviewed solver"):
        local_fixture.execute_reviewed_fixture(tmp_path, b"{}", "reference")


def test_rehashed_bundle_cannot_authorize_unreviewed_code(tmp_path):
    directory = run_fixture(tmp_path, variant="missing_setting")
    replacement = b"raise SystemExit('bundled code must never run')\n"
    (directory / "solver.py").write_bytes(replacement)
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["files"]["solver.py"] = {
        "sha256": digest(replacement),
        "size_bytes": len(replacement),
    }
    manifest_path.write_bytes(canonical_json(manifest))
    verify_bundle(directory)  # Consistent hashes are not authority to execute code.
    with pytest.raises(ValueError, match="matching reviewed source"):
        rerun_fixture(directory, tmp_path / "rerun")


def test_launch_failure_retains_evidence(tmp_path, monkeypatch):
    def failed_launch(*args, **kwargs):
        raise OSError("Cannot launch reviewed worker")

    monkeypatch.setattr("paper2proof.experiments.execute_reviewed_fixture", failed_launch)
    directory = run_fixture(tmp_path)
    assert read_report(directory)["exit_reason"] == "launch_error"
    assert read_report(directory)["scientific_verdict"] is None
    verify_bundle(directory)


def test_cancel_terminates_reviewed_process_without_verdict(tmp_path):
    directory = run_fixture(tmp_path, canceled=lambda: True)
    report = read_report(directory)
    assert report["exit_reason"] == "canceled"
    assert report["scientific_verdict"] is None
    assert report["assessment"] is None
