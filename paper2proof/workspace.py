"""Local workflow service. Never executes provider-generated code."""

import asyncio
import json
import shutil
import threading
import time
import zipfile
from pathlib import Path
from uuid import uuid4

from paper2proof.agents.generation import generate_code, offline_code_provider
from paper2proof.artifacts.evidence import canonical_json, digest, verify_bundle, write_once
from paper2proof.experiments import run_fixture
from paper2proof.pdf.parser import MAX_PDF_BYTES, PDFError, parse_pdf
from paper2proof.review import make_claim, make_spec, verify_spec
from paper2proof.schemas.experiment import FixtureSpec
from paper2proof.schemas.workflow import Claim, ClaimDraft, Paper, ReviewDraft, SpecVersion
from paper2proof.store import Conflict, Store


class Workspace:
    def __init__(self, root: Path):
        self.store = Store(root)
        self.root = self.store.root

    def paper_path(self, identifier: str) -> Path:
        # Look up the record before constructing a server-generated path.
        paper = self.store.get(identifier, "paper")
        path = self.root / "papers" / paper["id"] / "original.pdf"
        if digest(path.read_bytes()) != paper["sha256"]:
            raise ValueError("Stored PDF integrity check failed")
        return path

    def add_pdf(self, payload: bytes) -> dict:
        identifier = uuid4().hex
        directory = self.root / "papers" / identifier
        directory.mkdir(parents=True, exist_ok=False)
        path = directory / "original.pdf"
        write_once(path, payload)
        try:
            paper = parse_pdf(path, identifier)
        except Exception:
            path.unlink()
            directory.rmdir()
            raise
        return self.store.put("paper", paper.model_dump(mode="json"))

    def queue_pdf(self, payload: bytes) -> dict:
        if len(payload) > MAX_PDF_BYTES:
            raise PDFError("pdf_size_limit", "PDF exceeds 25 MiB.")
        if not payload.startswith(b"%PDF-"):
            raise PDFError("invalid_pdf_signature", "A PDF signature is required.")
        identifier = uuid4().hex
        directory = self.root / "papers" / identifier
        directory.mkdir(parents=True, exist_ok=False)
        write_once(directory / "original.pdf", payload)
        paper = {
            "id": identifier,
            "state": "queued",
            "sha256": digest(payload),
            "pages": None,
            "spans": [],
            "warnings": [],
            "parser_version": "pending",
        }
        self.store.put("paper", paper)
        try:
            job = self.store.enqueue_extraction(identifier)
        except Conflict:
            self.store.finish_paper(
                identifier,
                {**paper, "state": "rejected", "error": "Queue full; upload again later."},
            )
            raise
        return {"id": identifier, "state": "queued", "extraction_job_id": job["id"]}

    def add_claim(self, paper_id: str, draft: ClaimDraft, previous_id=None) -> dict:
        paper = Paper.model_validate(self.store.get(paper_id, "paper"))
        previous = (
            Claim.model_validate(self.store.get(previous_id, "claim")) if previous_id else None
        )
        if previous and previous.paper_id != paper_id:
            raise ValueError("Claim versions must belong to the same paper")
        claim = make_claim(paper, draft, previous)
        return self.store.put("claim", claim.model_dump(mode="json"), paper_id)

    def add_spec(self, claim_id: str, draft: ReviewDraft, previous_id=None) -> dict:
        claim = Claim.model_validate(self.store.get(claim_id, "claim"))
        paper = Paper.model_validate(self.store.get(claim.paper_id, "paper"))
        previous = (
            SpecVersion.model_validate(self.store.get(previous_id, "spec")) if previous_id else None
        )
        if previous and previous.claim_id != claim_id:
            raise ValueError("Spec versions must belong to the same claim")
        spec = make_spec(paper, claim, draft, previous)
        return self.store.put("spec", spec.model_dump(mode="json"), claim_id)

    def process_one(self) -> bool:
        self.cleanup_deleted()
        job = self.store.claim_job()
        if not job:
            return False
        identifier = job["id"]
        directory = self.root / "jobs" / identifier
        directory.mkdir(parents=True, exist_ok=False)
        stop_heartbeat = threading.Event()

        def heartbeat():
            while not stop_heartbeat.wait(5):
                if not self.store.renew_lease(identifier):
                    return

        lease_thread = threading.Thread(target=heartbeat, daemon=True)
        lease_thread.start()
        try:
            if job["kind"] == "extract_pdf":
                paper = parse_pdf(
                    self.root / "papers" / job["spec_id"] / "original.pdf",
                    job["spec_id"],
                    canceled=lambda: bool(
                        self.store.job(identifier, include_deleted=True)["canceled"]
                    ),
                )
                self.store.finish_paper(paper.id, paper.model_dump(mode="json"))
                write_once(
                    directory / "extraction.json", canonical_json(paper.model_dump(mode="json"))
                )
                self.store.finish(
                    identifier,
                    "completed",
                    result=self.seal(
                        directory,
                        {"paper_id": paper.id, "pages": paper.pages, "scientific_verdict": None},
                    ),
                )
                return True
            spec = SpecVersion.model_validate(
                self.store.get(job["spec_id"], "spec", include_deleted=True)
            )
            verify_spec(spec)
            claim = Claim.model_validate(
                self.store.get(spec.claim_id, "claim", include_deleted=True)
            )
            paper = Paper.model_validate(
                self.store.get(spec.paper_id, "paper", include_deleted=True)
            )
            write_once(directory / "spec.json", canonical_json(spec.model_dump(mode="json")))
            write_once(directory / "claim.json", canonical_json(claim.model_dump(mode="json")))
            write_once(
                directory / "provenance.json",
                canonical_json(
                    {
                        "paper_sha256": paper.sha256,
                        "source_spans": [
                            span.model_dump(mode="json")
                            for span in paper.spans
                            if span.id == claim.span_id
                        ],
                    }
                ),
            )
            if self.store.job(identifier, include_deleted=True)["canceled"]:
                self.store.finish(identifier, "canceled")
                return True
            if job["kind"] == "generation_preview":
                result = asyncio.run(
                    generate_code(
                        offline_code_provider(spec, claim),
                        paper,
                        claim,
                        spec,
                        directory / "generation",
                        event=lambda stage, text: self.store.event(identifier, stage, text),
                        canceled=lambda: bool(
                            self.store.job(identifier, include_deleted=True)["canceled"]
                        ),
                    )
                )
                self.store.finish(
                    identifier, "awaiting_sandbox", result=self.seal(directory, result)
                )
            else:
                self.store.event(
                    identifier,
                    "executing",
                    "Running reviewed engineering fixture. Not a paper reproduction.",
                )
                evidence = run_fixture(
                    directory / "evidence",
                    spec=FixtureSpec(target_relative_error=spec.target_relative_error),
                    canceled=lambda: bool(
                        self.store.job(identifier, include_deleted=True)["canceled"]
                    ),
                )
                verify_bundle(evidence)
                result = json.loads((evidence / "report.json").read_bytes())
                result["review_spec_hash"] = spec.spec_hash
                result["evidence_subdirectory"] = evidence.relative_to(directory).as_posix()
                self.store.finish(
                    identifier,
                    "completed" if result["execution_state"] == "completed" else "failed",
                    result=self.seal(directory, result),
                )
        except Exception as exc:
            if job["kind"] == "extract_pdf":
                pending = self.store.get(job["spec_id"], "paper", include_deleted=True)
                if pending.get("state") == "queued":
                    self.store.finish_paper(
                        job["spec_id"], {**pending, "state": "rejected", "error": str(exc)[:500]}
                    )
            self.store.finish(
                identifier,
                "failed",
                result=self.seal(directory, {"partial": True}),
                error=f"{type(exc).__name__}: {str(exc)[:500]}",
            )
        finally:
            stop_heartbeat.set()
            lease_thread.join(timeout=1)
        return True

    @staticmethod
    def seal(directory: Path, result: dict) -> dict:
        files = {}
        for path in directory.rglob("*"):
            if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()):
                raise ValueError("Evidence cannot contain symlinks")
            if path.is_file():
                files[path.relative_to(directory).as_posix()] = digest(path.read_bytes())
        return {**result, "artifact_hashes": files}

    def export(self, identifier: str) -> Path:
        job = self.store.job(identifier)
        if job["kind"] == "extract_pdf":
            raise ValueError("Export an experiment job; full paper text is excluded from exports")
        if job["state"] not in {"completed", "awaiting_sandbox", "failed", "canceled"}:
            raise ValueError("Wait for the job to stop before exporting")
        directory = self.root / "jobs" / identifier
        if not directory.is_dir():
            raise ValueError("This job has no artifacts to export")
        # No PDFs, database, environment files, or caller-supplied paths in exports.
        files, total = {}, 0
        for path in sorted(directory.rglob("*")):
            if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()):
                raise ValueError("Symlinks cannot be exported")
            if not path.is_file():
                continue
            if path.suffix not in {".json", ".py", ".md", ".log", ".lock", ".diff"}:
                raise ValueError("Unexpected export file type")
            total += path.stat().st_size
            if total > 100 * 1024 * 1024:
                raise ValueError("Export exceeds 100 MiB")
            files[path.relative_to(directory).as_posix()] = path.read_bytes()
        expected = (job["result"] or {}).get("artifact_hashes", {})
        if set(files) != set(expected) or any(
            digest(data) != expected[name] for name, data in files.items()
        ):
            raise ValueError("Job evidence changed after completion; export refused")
        files["job.json"] = canonical_json(job)
        files["events.json"] = canonical_json(self.store.events(identifier))
        manifest = {
            "files": {
                name: {"sha256": digest(data), "size_bytes": len(data)}
                for name, data in files.items()
            },
            "exclusions": [
                "Original PDF (redistribution rights not assumed)",
                "Credentials",
                "Workspace database",
            ],
            "label": "Local offline evidence; not a paper reproduction or Meta inference",
        }
        output = self.root / "exports" / f"{uuid4().hex}.zip"
        output.parent.mkdir(exist_ok=True)
        with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in files.items():
                archive.writestr(name, data)
            archive.writestr("export-manifest.json", canonical_json(manifest))
        with self.store.connect() as db:
            db.execute("INSERT INTO exports VALUES (?,?)", (output.name, identifier))
        return output

    def cleanup_deleted(self):
        with self.store.connect() as db:
            pending = db.execute(
                "SELECT paper_id FROM deletions WHERE completed IS NULL"
            ).fetchall()
        for row in pending:
            paper_id = row[0]
            records, jobs = self.store.descendants(paper_id)
            if any(job["state"] == "running" for job in jobs):
                continue
            targets = [self.root / "papers" / paper_id]
            with self.store.connect() as db:
                for job in jobs:
                    targets.append(self.root / "jobs" / job["id"])
                    targets.extend(
                        self.root / "exports" / item[0]
                        for item in db.execute(
                            "SELECT filename FROM exports WHERE job_id=?", (job["id"],)
                        )
                    )
            try:
                for target in targets:
                    resolved = target.resolve()
                    if resolved == self.root or not resolved.is_relative_to(self.root):
                        raise ValueError("Deletion target escaped the workspace")
                    if target.is_symlink() or target.is_file():
                        target.unlink()
                    elif target.is_dir():
                        shutil.rmtree(target)
            except OSError:
                # A download or antivirus scan may briefly hold a Windows file open.
                # Access stays revoked; retain metadata so the next pass can retry.
                continue
            with self.store.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                for job in jobs:
                    db.execute("DELETE FROM exports WHERE job_id=?", (job["id"],))
                    db.execute("DELETE FROM events WHERE job_id=?", (job["id"],))
                    db.execute("DELETE FROM jobs WHERE id=?", (job["id"],))
                for identifier in records:
                    db.execute("DELETE FROM approvals WHERE spec_id=?", (identifier,))
                for identifier in records:
                    db.execute("DELETE FROM records WHERE id=?", (identifier,))
                db.execute(
                    "UPDATE deletions SET completed=? WHERE paper_id=?", (time.time(), paper_id)
                )
