import json
import subprocess
import sys
import threading
import time
from pathlib import Path

from paper2proof.artifacts.evidence import digest
from paper2proof.runner.local_fixture import fixture_environment
from paper2proof.schemas.workflow import Paper

MAX_PDF_BYTES = 25 * 1024 * 1024


class PDFError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def parse_pdf(path: Path, paper_id: str, *, timeout: float = 30, canceled=None) -> Paper:
    if path.stat().st_size > MAX_PDF_BYTES:
        raise PDFError("pdf_size_limit", "PDF exceeds 25 MiB.")
    with path.open("rb") as stream:
        if stream.read(5) != b"%PDF-":
            raise PDFError("invalid_pdf_signature", "File must begin with a PDF signature.")
    process = subprocess.Popen(
        [sys.executable, "-I", str(Path(__file__).with_name("worker.py")), str(path.resolve())],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=fixture_environment(),
    )
    buffers = [bytearray(), bytearray()]
    exceeded = threading.Event()

    def capture(stream, buffer, limit):
        try:
            while chunk := stream.read(8192):
                if len(buffer) + len(chunk) > limit:
                    exceeded.set()
                    process.kill()
                    return
                buffer.extend(chunk)
        finally:
            stream.close()

    threads = [
        threading.Thread(target=capture, args=(process.stdout, buffers[0], 8 * 1024 * 1024)),
        threading.Thread(target=capture, args=(process.stderr, buffers[1], 64 * 1024)),
    ]
    for thread in threads:
        thread.start()
    timed_out = False
    was_canceled = False
    deadline = time.monotonic() + timeout
    try:
        while True:
            if canceled and canceled():
                was_canceled = True
                process.kill()
                process.wait()
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(process.args, timeout)
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
    if timed_out:
        raise PDFError("parser_timeout", "PDF parsing exceeded its time limit.")
    if was_canceled:
        raise PDFError("parser_canceled", "PDF parsing was canceled.")
    if exceeded.is_set():
        raise PDFError("parser_output_limit", "Parser output exceeded its size limit.")
    if process.returncode != 0:
        raise PDFError("parser_failure", "Parser exited unexpectedly or exhausted memory.")
    result = json.loads(buffers[0])
    if "error" in result:
        raise PDFError(result["error"], result["message"])
    return Paper(id=paper_id, sha256=digest(path.read_bytes()), **result)
