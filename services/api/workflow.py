import asyncio
import json
import time
from typing import Literal

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from paper2proof.artifacts.evidence import digest
from paper2proof.pdf.parser import MAX_PDF_BYTES, PDFError
from paper2proof.review import default_review
from paper2proof.schemas.workflow import ClaimDraft, ReviewDraft, StartRequest
from paper2proof.store import Conflict
from paper2proof.workspace import Workspace


class Approval(BaseModel):
    spec_hash: str = Field(min_length=64, max_length=64)
    accepted: Literal[True]


def router(workspace: Workspace) -> APIRouter:
    api = APIRouter(prefix="/api/v1")
    store = workspace.store

    @api.post("/demo-paper", status_code=202)
    def demo():
        from paper2proof.pdf.demo import demo_pdf

        return workspace.queue_pdf(demo_pdf())

    @api.get("/workspace")
    def overview():
        return {
            "papers": [
                {key: value for key, value in paper.items() if key != "spans"}
                for paper in store.list("paper")
            ],
            "jobs": store.jobs(),
            "mode": "single_user_offline",
            "storage": "sqlite_development",
        }

    @api.post("/papers", status_code=202)
    async def upload(request: Request):
        if request.headers.get("content-type", "").split(";")[0] != "application/pdf":
            raise PDFError(
                "unsupported_media", "Send raw PDF bytes with Content-Type: application/pdf."
            )
        payload = bytearray()
        async for chunk in request.stream():
            if len(payload) + len(chunk) > MAX_PDF_BYTES:
                raise PDFError("pdf_size_limit", "PDF exceeds 25 MiB.")
            payload.extend(chunk)
        return await asyncio.to_thread(workspace.queue_pdf, bytes(payload))

    @api.get("/papers/{identifier}")
    def paper(identifier: str):
        return store.get(identifier, "paper")

    @api.delete("/papers/{identifier}", status_code=202)
    def delete_paper(identifier: str):
        store.request_delete(identifier)
        return {"access_revoked": True, "cleanup": "queued_for_worker"}

    @api.get("/papers/{identifier}/pdf")
    def original(identifier: str):
        return FileResponse(
            workspace.paper_path(identifier),
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'inline; filename="source.pdf"',
                "X-Content-Type-Options": "nosniff",
            },
        )

    @api.get("/papers/{identifier}/claims")
    def claims(identifier: str):
        store.get(identifier, "paper")
        return store.list("claim", identifier)

    @api.post("/papers/{identifier}/claims", status_code=201)
    def add_claim(identifier: str, body: ClaimDraft):
        return workspace.add_claim(identifier, body)

    @api.post("/claims/{identifier}/versions", status_code=201)
    def correct_claim(identifier: str, body: ClaimDraft):
        previous = store.get(identifier, "claim")
        return workspace.add_claim(previous["paper_id"], body, identifier)

    @api.get("/review-defaults")
    def defaults():
        return default_review()

    @api.get("/claims/{identifier}/specs")
    def specs(identifier: str):
        store.get(identifier, "claim")
        return store.list("spec", identifier)

    @api.post("/claims/{identifier}/specs", status_code=201)
    def add_spec(identifier: str, body: ReviewDraft):
        return workspace.add_spec(identifier, body)

    @api.post("/specs/{identifier}/versions", status_code=201)
    def revise_spec(identifier: str, body: ReviewDraft, if_match: str = Header()):
        previous = store.get(identifier, "spec")
        if if_match != previous["spec_hash"]:
            raise Conflict("If-Match must identify the previous frozen specification")
        return workspace.add_spec(previous["claim_id"], body, identifier)

    @api.post("/specs/{identifier}/approve")
    def approve(identifier: str, body: Approval):
        store.approve(identifier, body.spec_hash)
        return {"approved": True, "spec_id": identifier, "spec_hash": body.spec_hash}

    @api.post("/specs/{identifier}/jobs", status_code=202)
    def start(
        identifier: str,
        body: StartRequest,
        idempotency_key: str = Header(min_length=8, max_length=128),
    ):
        store.get(identifier, "spec")
        return store.enqueue(identifier, body.spec_hash, body.kind, idempotency_key)

    @api.get("/jobs/{identifier}")
    def job(identifier: str):
        return store.job(identifier)

    @api.get("/jobs/{identifier}/events")
    def events(identifier: str, after: int = Query(default=0, ge=0)):
        return store.events(identifier, after)

    @api.get("/jobs/{identifier}/events/stream")
    async def stream(identifier: str, request: Request, last_event_id: str = Header(default="0")):
        cursor = int(last_event_id)
        if cursor < 0:
            raise ValueError("Last-Event-ID must be nonnegative")
        store.job(identifier)

        async def frames():
            nonlocal cursor
            until = time.monotonic() + 30
            while time.monotonic() < until and not await request.is_disconnected():
                for item in store.events(identifier, cursor):
                    cursor = item["sequence"]
                    yield f"id: {cursor}\ndata: {json.dumps(item)}\n\n"
                yield ": heartbeat\n\n"
                await asyncio.sleep(1)

        return StreamingResponse(
            frames(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"}
        )

    @api.post("/jobs/{identifier}/cancel")
    def cancel(identifier: str):
        store.cancel(identifier)
        return store.job(identifier)

    @api.get("/jobs/{identifier}/code", response_class=PlainTextResponse)
    def code(identifier: str):
        job = store.job(identifier)
        if job["kind"] != "generation_preview" or not job["result"]:
            raise ValueError("No staged code is available")
        attempt = job["result"]["attempt"]
        if not isinstance(attempt, int) or not 1 <= attempt <= 4:
            raise ValueError("Invalid attempt")
        path = (
            workspace.root
            / "jobs"
            / identifier
            / "generation"
            / f"attempt-{attempt}"
            / "src"
            / "solver.py"
        )
        content = path.read_bytes()
        if digest(content) != job["result"]["code_sha256"]:
            raise ValueError("Staged code integrity check failed")
        return content.decode("utf-8")

    @api.post("/jobs/{identifier}/export")
    def export(identifier: str):
        return FileResponse(
            workspace.export(identifier),
            filename=f"paper2proof-{identifier}.zip",
            media_type="application/zip",
        )

    return api
