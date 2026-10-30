"""Bounded subprocess for a fixed reviewed fixture. NOT an isolation boundary."""

import os
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from paper2proof.schemas.experiment import MAX_OUTPUT_BYTES

MAX_STDERR_BYTES = 64 * 1024
WORKER_SOURCE = Path(__file__).with_name("fixture_worker.py")


def fixture_environment() -> dict[str, str]:
    # No inherited API keys, DB URLs, PYTHONPATH, or home directory variables.
    # This reduces accidental exposure; host filesystem/network are NOT isolated.
    return {
        key: os.environ[key] for key in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP") if key in os.environ
    }


def execute_reviewed_fixture(
    directory: Path,
    payload: bytes,
    variant: Literal["reference", "wrong_update"],
    *,
    timeout_seconds: float = 30,
    canceled=None,
) -> dict:
    if variant not in {"reference", "wrong_update"}:
        raise ValueError("Only reviewed fixture variants can run locally")
    if not 0 < timeout_seconds <= 180:
        raise ValueError("Timeout must be between zero and 180 seconds")
    solver = directory / "solver.py"
    if solver.is_symlink() or solver.read_bytes() != WORKER_SOURCE.read_bytes():
        raise ValueError("Local execution is restricted to the current reviewed solver")
    started_at = datetime.now(UTC).isoformat()
    start = time.monotonic()
    exceeded = threading.Event()
    input_failed = threading.Event()
    capture_errors = []
    with (
        (directory / "stdout.json").open("xb") as stdout_file,
        (directory / "stderr.log").open("xb") as stderr_file,
    ):
        process = subprocess.Popen(
            [sys.executable, "-I", str(solver.resolve()), variant],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=directory,
            env=fixture_environment(),
            shell=False,
        )

        def capture(stream, destination, limit):
            written = 0
            try:
                while chunk := stream.read(8192):
                    room = limit - written
                    destination.write(chunk[:room])
                    written += min(len(chunk), room)
                    if len(chunk) > room:
                        exceeded.set()
                        process.kill()
                        break
            except OSError as exc:
                capture_errors.append(type(exc).__name__)
                process.kill()
            finally:
                stream.close()

        def feed_input():
            try:
                with process.stdin:
                    process.stdin.write(payload)
            except OSError:
                input_failed.set()

        threads = [
            threading.Thread(target=capture, args=(process.stdout, stdout_file, MAX_OUTPUT_BYTES)),
            threading.Thread(target=capture, args=(process.stderr, stderr_file, MAX_STDERR_BYTES)),
            threading.Thread(target=feed_input),
        ]
        for thread in threads:
            thread.start()
        timed_out = False
        was_canceled = False
        try:
            while True:
                if canceled and canceled():
                    was_canceled = True
                    process.kill()
                    process.wait()
                    break
                remaining = timeout_seconds - (time.monotonic() - start)
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(process.args, timeout_seconds)
                try:
                    process.wait(timeout=min(0.1, remaining))
                    break
                except subprocess.TimeoutExpired:
                    continue
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            process.wait()
        finally:
            for thread in threads:
                thread.join()
        reason = (
            "canceled"
            if was_canceled
            else "output_limit"
            if exceeded.is_set()
            else "timeout"
            if timed_out
            else "capture_error"
            if capture_errors
            else "input_error"
            if input_failed.is_set()
            else "process_error"
            if process.returncode != 0
            else "completed"
        )
    return {
        "state": "completed" if reason == "completed" else "failed",
        "exit_reason": reason,
        "exit_code": process.returncode,
        "started_at": started_at,
        "finished_at": datetime.now(UTC).isoformat(),
        "wall_seconds": time.monotonic() - start,
        "timeout_seconds": timeout_seconds,
        "runner": "local_reviewed_fixture_only",
        "sandbox_job_id": None,
        "network_isolated": False,
        "resource_isolated": False,
        "stdout_limit_bytes": MAX_OUTPUT_BYTES,
        "stderr_limit_bytes": MAX_STDERR_BYTES,
    }
