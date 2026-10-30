import asyncio
import io
import json
import time
import zipfile

import pymupdf
import pytest
from fastapi.testclient import TestClient

from paper2proof.agents.generation import Budget, generate_code, offline_code_provider
from paper2proof.agents.paper import propose_claims, propose_spec
from paper2proof.artifacts.evidence import digest
from paper2proof.config import Settings
from paper2proof.evaluation.verdicts import equivalence_outcome
from paper2proof.pdf.demo import demo_pdf
from paper2proof.pdf.parser import MAX_PDF_BYTES, PDFError, parse_pdf
from paper2proof.providers.offline import OfflineProvider
from paper2proof.review import default_review, make_claim, make_spec
from paper2proof.schemas.workflow import Claim, ClaimDraft, Paper, ReviewDraft, SpecVersion
from paper2proof.store import Conflict, Store
from paper2proof.workspace import Workspace
from services.api.main import create_app


@pytest.fixture(scope="module")
def paper(tmp_path_factory):
    path = tmp_path_factory.mktemp("pdf") / "fixture.pdf"
    path.write_bytes(demo_pdf())
    return parse_pdf(path, "paper-fixture")


def claim_draft(paper):
    span = next(span for span in paper.spans if "Randomized Kaczmarz" in span.text)
    return ClaimDraft(
        statement="Engineering test error target",
        span_id=span.id,
        quote=span.text,
        metric="relative_l2_solution_error",
        method="randomized_kaczmarz",
    )


def ready_spec(paper):
    claim = make_claim(paper, claim_draft(paper))
    draft = default_review().model_copy(
        update={
            "target_relative_error": 0.01,
            "target_rationale": "Explicit engineering target, not a paper finding.",
        }
    )
    return claim, make_spec(paper, claim, draft)


def seed_store(root, paper):
    workspace = Workspace(root)
    workspace.store.put("paper", paper.model_dump(mode="json"))
    claim, spec = ready_spec(paper)
    workspace.store.put("claim", claim.model_dump(mode="json"), paper.id)
    workspace.store.put("spec", spec.model_dump(mode="json"), claim.id)
    workspace.store.approve(spec.id, spec.spec_hash)
    return workspace, spec


def test_pdf_provenance(paper):
    assert paper.pages == 1
    assert len(paper.sha256) == 64
    assert paper.spans[0].page == 1
    assert paper.spans[0].bbox[2] > paper.spans[0].bbox[0]
    assert paper.parser_version.startswith("pymupdf-")


@pytest.mark.parametrize(
    "case,expected",
    [
        ("signature", "invalid_pdf_signature"),
        ("corrupt", "corrupt_pdf"),
        ("encrypted", "encrypted_pdf"),
        ("scanned", "scanned_pdf"),
        ("pages", "page_limit"),
        ("oversized", "pdf_size_limit"),
        ("timeout", "parser_timeout"),
    ],
)
def test_bad_pdfs_rejected(tmp_path, case, expected):
    path = tmp_path / "test.pdf"
    if case == "signature":
        path.write_bytes(b"not a pdf")
    elif case == "corrupt":
        path.write_bytes(b"%PDF-1.7\ncorrupt")
    elif case == "oversized":
        with path.open("wb") as stream:
            stream.write(b"%PDF-")
            stream.seek(MAX_PDF_BYTES)
            stream.write(b"x")
    elif case in {"encrypted", "scanned", "pages"}:
        with pymupdf.open() as document:
            for _ in range(51 if case == "pages" else 1):
                document.new_page()
            if case == "encrypted":
                document.save(
                    path, encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="user"
                )
            else:
                document.save(path)
    else:
        path.write_bytes(demo_pdf())
    with pytest.raises(PDFError) as exc:
        parse_pdf(path, "test", timeout=0.000001 if case == "timeout" else 30)
    assert exc.value.code == expected


def test_citations_and_missing_information(paper):
    invalid = claim_draft(paper).model_copy(update={"quote": "This quotation does not exist"})
    with pytest.raises(ValueError, match="exact passage"):
        make_claim(paper, invalid)
    claim = make_claim(paper, claim_draft(paper))
    missing = make_spec(paper, claim, default_review())
    assert any("target" in blocker for blocker in missing.blockers)
    _, spec = ready_spec(paper)
    direct = ReviewDraft.model_validate(spec.model_dump(include=set(ReviewDraft.model_fields)))
    assert make_spec(paper, claim, direct.model_copy(update={"mode": "direct"})).blockers
    settings = dict(direct.settings)
    settings["dataset"] = settings["dataset"].model_copy(update={"value": None})
    assert make_spec(paper, claim, direct.model_copy(update={"settings": settings})).blockers


def test_spec_versions_preserve_old_approval_and_hash(tmp_path, paper):
    workspace, first = seed_store(tmp_path, paper)
    draft = ReviewDraft.model_validate(first.model_dump(include=set(ReviewDraft.model_fields)))
    second = workspace.add_spec(
        first.claim_id, draft.model_copy(update={"target_relative_error": 0.02}), first.id
    )
    assert second["version"] == 2
    assert second["spec_hash"] != first.spec_hash
    assert workspace.store.get(first.id, "spec")["target_relative_error"] == 0.01
    with pytest.raises(Conflict, match="Approve"):
        workspace.store.enqueue(
            second["id"], second["spec_hash"], "engineering_fixture", "new-version-key"
        )


def test_queue_persistence_idempotency_and_terminal_events(tmp_path, paper):
    workspace, spec = seed_store(tmp_path, paper)
    first = workspace.store.enqueue(spec.id, spec.spec_hash, "engineering_fixture", "same-request")
    restarted = Store(tmp_path)
    assert (
        restarted.enqueue(spec.id, spec.spec_hash, "engineering_fixture", "same-request")["id"]
        == first["id"]
    )
    with pytest.raises(Conflict):
        restarted.enqueue(spec.id, spec.spec_hash, "generation_preview", "same-request")
    assert restarted.claim_job()["id"] == first["id"]
    assert workspace.store.claim_job() is None
    restarted.finish(first["id"], "completed", result={"fixture": True})
    with pytest.raises(Conflict):
        restarted.finish(first["id"], "failed")
    events = restarted.events(first["id"])
    assert [event["sequence"] for event in events] == [1, 2, 3]
    assert restarted.events(first["id"], after=2) == events[2:]


def test_expired_worker_is_failed_without_duplicate_launch(tmp_path, paper):
    workspace, spec = seed_store(tmp_path, paper)
    job = workspace.store.enqueue(spec.id, spec.spec_hash, "engineering_fixture", "interrupted")
    workspace.store.claim_job()
    with workspace.store.connect() as db:
        db.execute("UPDATE jobs SET lease_until=? WHERE id=?", (time.time() - 1, job["id"]))
    assert Store(tmp_path).claim_job() is None
    assert workspace.store.job(job["id"])["error"] == "worker_interrupted"


def test_queue_cancel_and_capacity(tmp_path, paper):
    workspace, spec = seed_store(tmp_path, paper)
    jobs = [
        workspace.store.enqueue(spec.id, spec.spec_hash, "engineering_fixture", f"request-{i}")
        for i in range(5)
    ]
    with pytest.raises(Conflict, match="full"):
        workspace.store.enqueue(spec.id, spec.spec_hash, "engineering_fixture", "request-extra")
    for job in jobs:
        workspace.store.cancel(job["id"])
    assert workspace.store.claim_job() is None


def test_queued_pdf_survives_restart_and_can_be_canceled(tmp_path):
    workspace = Workspace(tmp_path)
    pending = workspace.queue_pdf(demo_pdf())
    assert workspace.store.get(pending["id"], "paper")["state"] == "queued"
    restarted = Workspace(tmp_path)
    restarted.store.cancel(pending["extraction_job_id"])
    assert restarted.store.get(pending["id"], "paper")["state"] == "rejected"
    assert not restarted.process_one()


def test_generation_stops_after_one_schema_retry(tmp_path, paper):
    claim, spec = ready_spec(paper)
    with pytest.raises(ValueError, match="one schema retry"):
        asyncio.run(generate_code(OfflineProvider("{}"), paper, claim, spec, tmp_path / "bad"))
    assert len(list((tmp_path / "bad").glob("attempt-*"))) == 2


def test_generation_preview_never_executes_code_and_exports(tmp_path, paper, monkeypatch):
    workspace, spec = seed_store(tmp_path, paper)
    job = workspace.store.enqueue(spec.id, spec.spec_hash, "generation_preview", "preview-job")

    def forbidden(*args, **kwargs):
        pytest.fail("Generated code must never enter the local runner")

    monkeypatch.setattr("paper2proof.workspace.run_fixture", forbidden)
    assert workspace.process_one()
    saved = Store(tmp_path).job(job["id"])
    assert saved["state"] == "awaiting_sandbox"
    assert saved["result"]["is_fixture"] is True
    assert saved["result"]["execution_performed"] is False
    archive_path = workspace.export(job["id"])
    with zipfile.ZipFile(archive_path) as archive:
        manifest = json.loads(archive.read("export-manifest.json"))
        assert not any(name.endswith(".pdf") or ".env" in name for name in archive.namelist())
        for name, metadata in manifest["files"].items():
            assert digest(archive.read(name)) == metadata["sha256"]
    (tmp_path / "jobs" / job["id"] / "spec.json").write_text("{}")
    with pytest.raises(ValueError, match="changed"):
        workspace.export(job["id"])


def test_worker_runs_reviewed_fixture_and_reconciles_report(tmp_path, paper):
    workspace, spec = seed_store(tmp_path, paper)
    job = workspace.store.enqueue(spec.id, spec.spec_hash, "engineering_fixture", "fixture-job")
    assert workspace.process_one()
    saved = workspace.store.job(job["id"])
    assert saved["state"] == "completed"
    assert saved["result"]["assessment"] == "fixture_target_met"
    assert saved["result"]["scientific_verdict"] is None
    assert saved["result"]["review_spec_hash"] == spec.spec_hash
    assert workspace.export(job["id"]).is_file()


@pytest.mark.parametrize("mutation", ["path", "spec", "citation", "imports"])
def test_bounded_repair_preserves_failed_attempts(tmp_path, paper, mutation):
    claim, spec = ready_spec(paper)
    valid = json.loads(offline_code_provider(spec, claim)._fixture_json)
    bad = json.loads(json.dumps(valid))
    if mutation == "path":
        bad["files"][0]["path"] = "../evaluation/linear.py"
    elif mutation == "spec":
        bad["spec_hash"] = "changed"
    elif mutation == "citation":
        bad["source_span_ids"] = ["invented"]
    else:
        bad["files"][0]["content"] = "import subprocess\ndef solve(payload): return {}"

    class Scripted:
        calls = 0

        async def generate(self, **kwargs):
            self.calls += 1
            return await OfflineProvider(json.dumps(bad if self.calls == 1 else valid)).generate(
                **kwargs
            )

    provider = Scripted()
    result = asyncio.run(generate_code(provider, paper, claim, spec, tmp_path / "attempts"))
    assert provider.calls == 2
    assert result["attempt"] == 2
    assert (tmp_path / "attempts" / "attempt-1" / "failure.json").exists()
    assert result["spec_hash"] == spec.spec_hash


def test_generation_budget_and_frozen_object_tampering(tmp_path, paper):
    claim, spec = ready_spec(paper)
    invalid = OfflineProvider('{"schema_version":"invalid"}')
    with pytest.raises(ValueError, match="budget"):
        asyncio.run(
            generate_code(
                invalid, paper, claim, spec, tmp_path / "limited", budget=Budget(max_calls=1)
            )
        )
    with pytest.raises(ValueError, match="Frozen"):
        asyncio.run(
            generate_code(
                offline_code_provider(spec, claim),
                paper,
                claim,
                spec.model_copy(update={"target_relative_error": 0.9}),
                tmp_path / "tampered",
            )
        )


def test_extraction_and_planning_contracts_do_not_invent_citations(paper):
    candidate = claim_draft(paper)
    provider = OfflineProvider(json.dumps({"claims": [candidate.model_dump(mode="json")]}))
    assert asyncio.run(propose_claims(provider, paper)).claims[0].quote == candidate.quote
    provider = OfflineProvider(
        json.dumps(
            {
                "claims": [
                    candidate.model_copy(update={"span_id": "invented"}).model_dump(mode="json")
                ]
            }
        )
    )
    with pytest.raises(ValueError, match="Citation"):
        asyncio.run(propose_claims(provider, paper))
    planned = asyncio.run(
        propose_spec(
            OfflineProvider(default_review().model_dump_json()), paper, make_claim(paper, candidate)
        )
    )
    assert planned.blockers


@pytest.mark.parametrize(
    "interval,outcome",
    [
        ((0.2, 0.8), "reproduced_within_tolerance"),
        ((1.1, 1.4), "not_reproduced_in_this_run"),
        ((0.9, 1.1), "inconclusive"),
    ],
)
def test_uncertainty_rules(interval, outcome):
    args = dict(
        completed=True,
        comparable=True,
        fidelity=True,
        sufficient_trials=True,
        mode="direct",
        interval=interval,
        acceptance_band=(0, 1),
    )
    assert equivalence_outcome(**args)["scientific_verdict"] == outcome
    assert equivalence_outcome(**{**args, "completed": False})["scientific_verdict"] is None
    assert (
        equivalence_outcome(**{**args, "mode": "adapted"})["scientific_verdict"] == "inconclusive"
    )


def test_http_workflow_and_untrusted_text_escaping(tmp_path):
    app = create_app(Settings(_env_file=None, data_dir=tmp_path))
    with TestClient(app) as client:
        assert client.get("/api/v1/workspace").status_code == 401
        access_code = (tmp_path / "access-code.txt").read_text()
        assert client.post("/api/v1/session", json={"access_code": access_code}).status_code == 200
        assert (
            client.post(
                "/api/v1/demo-paper", headers={"Origin": "https://evil.example"}
            ).status_code
            == 403
        )
        response = client.post(
            "/api/v1/papers", content=demo_pdf(), headers={"Content-Type": "application/pdf"}
        )
        assert response.status_code == 202, response.text
        paper_id = response.json()["id"]
        assert app.state.workspace.process_one()
        paper = Paper.model_validate(client.get(f"/api/v1/papers/{paper_id}").json())
        assert client.get(f"/api/v1/papers/{paper.id}/pdf").content.startswith(b"%PDF-")
        candidate = claim_draft(paper)
        response = client.post(
            f"/api/v1/papers/{paper.id}/claims", json=candidate.model_dump(mode="json")
        )
        claim = Claim.model_validate(response.json())
        draft = default_review().model_copy(
            update={"target_relative_error": 0.01, "target_rationale": "Engineering policy"}
        )
        response = client.post(
            f"/api/v1/claims/{claim.id}/specs", json=draft.model_dump(mode="json")
        )
        spec = SpecVersion.model_validate(response.json())
        body = {"kind": "generation_preview", "spec_hash": spec.spec_hash}
        assert (
            client.post(
                f"/api/v1/specs/{spec.id}/jobs",
                json=body,
                headers={"Idempotency-Key": "http-workflow"},
            ).status_code
            == 409
        )
        assert (
            client.post(
                f"/api/v1/specs/{spec.id}/approve",
                json={"spec_hash": spec.spec_hash, "accepted": True},
            ).status_code
            == 200
        )
        response = client.post(
            f"/api/v1/specs/{spec.id}/jobs", json=body, headers={"Idempotency-Key": "http-workflow"}
        )
        assert response.status_code == 202
        job_id = response.json()["id"]
        assert app.state.workspace.process_one()
        assert client.get(f"/api/v1/jobs/{job_id}").json()["state"] == "awaiting_sandbox"
        assert "def solve" in client.get(f"/api/v1/jobs/{job_id}/code").text
        export = client.post(f"/api/v1/jobs/{job_id}/export")
        assert export.status_code == 200
        with zipfile.ZipFile(io.BytesIO(export.content)) as archive:
            assert "export-manifest.json" in archive.namelist()


def test_local_sessions_protect_artifacts_and_expire(tmp_path):
    app = create_app(Settings(_env_file=None, data_dir=tmp_path))
    with TestClient(app) as client:
        assert client.get("/api/v1/workspace").status_code == 401
        assert client.get("/api/v1/jobs/unknown/code").status_code == 401
        assert client.post("/api/v1/session", json={"access_code": "incorrect"}).status_code == 401
        response = client.post(
            "/api/v1/session", json={"access_code": (tmp_path / "access-code.txt").read_text()}
        )
        assert response.status_code == 200
        assert "HttpOnly" in response.headers["set-cookie"]
        assert "SameSite=strict" in response.headers["set-cookie"]
        assert client.get("/api/v1/workspace").status_code == 200
        with app.state.workspace.store.connect() as db:
            db.execute("UPDATE sessions SET expires=0")
        assert client.get("/api/v1/workspace").status_code == 401


def test_deletion_revokes_access_then_cleans_files_and_exports(tmp_path):
    workspace = Workspace(tmp_path)
    paper = Paper.model_validate(workspace.add_pdf(demo_pdf()))
    claim, spec = ready_spec(paper)
    workspace.store.put("claim", claim.model_dump(mode="json"), paper.id)
    workspace.store.put("spec", spec.model_dump(mode="json"), claim.id)
    workspace.store.approve(spec.id, spec.spec_hash)
    job = workspace.store.enqueue(spec.id, spec.spec_hash, "generation_preview", "delete-evidence")
    workspace.process_one()
    archive = workspace.export(job["id"])
    workspace.store.request_delete(paper.id)
    with pytest.raises(KeyError):
        workspace.store.get(claim.id, "claim")
    with pytest.raises(KeyError):
        workspace.store.job(job["id"])
    assert workspace.store.list("paper") == []
    with pytest.raises(Conflict):
        workspace.store.enqueue(spec.id, spec.spec_hash, "engineering_fixture", "after-deletion")
    workspace.cleanup_deleted()
    assert not archive.exists()
    assert not (tmp_path / "papers" / paper.id).exists()
    assert not (tmp_path / "jobs" / job["id"]).exists()
    with workspace.store.connect() as db:
        assert db.execute(
            "SELECT completed FROM deletions WHERE paper_id=?", (paper.id,)
        ).fetchone()[0]


def test_deletion_cancels_queued_work_without_execution(tmp_path):
    workspace = Workspace(tmp_path)
    queued = workspace.queue_pdf(demo_pdf())
    workspace.store.request_delete(queued["id"])
    assert not workspace.process_one()
    assert not (tmp_path / "papers" / queued["id"]).exists()


def test_deletion_retries_locked_files_without_stopping_worker(tmp_path, monkeypatch):
    workspace = Workspace(tmp_path)
    queued = workspace.queue_pdf(demo_pdf())
    workspace.store.request_delete(queued["id"])
    with monkeypatch.context() as patch:

        def locked(_path):
            raise PermissionError("File is temporarily in use")

        patch.setattr("paper2proof.workspace.shutil.rmtree", locked)
        assert not workspace.process_one()
        assert workspace.store.list("paper") == []
        with workspace.store.connect() as db:
            assert db.execute("SELECT completed FROM deletions").fetchone()[0] is None
    assert not workspace.process_one()
    assert not (tmp_path / "papers" / queued["id"]).exists()
    with workspace.store.connect() as db:
        assert db.execute("SELECT completed FROM deletions").fetchone()[0] is not None
