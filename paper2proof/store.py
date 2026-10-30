"""Single-user SQLite development store; production PostgreSQL/RQ remains separate."""

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from paper2proof.artifacts.evidence import canonical_json, digest

TERMINAL = {"completed", "failed", "canceled", "awaiting_sandbox"}


class Conflict(ValueError):
    pass


class Store:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "workspace.sqlite3"
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS records (
                    id TEXT PRIMARY KEY, kind TEXT NOT NULL, parent TEXT,
                    payload TEXT NOT NULL, created REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS approvals (
                    spec_id TEXT PRIMARY KEY REFERENCES records(id), spec_hash TEXT NOT NULL,
                    approved REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, spec_id TEXT NOT NULL REFERENCES records(id),
                    kind TEXT NOT NULL, idempotency TEXT UNIQUE NOT NULL,
                    request_hash TEXT NOT NULL,
                    state TEXT NOT NULL, result TEXT, error TEXT, created REAL NOT NULL,
                    lease_until REAL, canceled INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS events (
                    job_id TEXT NOT NULL REFERENCES jobs(id), sequence INTEGER NOT NULL,
                    payload TEXT NOT NULL, PRIMARY KEY(job_id, sequence)
                );
                CREATE TABLE IF NOT EXISTS deletions (
                    paper_id TEXT PRIMARY KEY, requested REAL NOT NULL, completed REAL
                );
                CREATE TABLE IF NOT EXISTS exports (
                    filename TEXT PRIMARY KEY, job_id TEXT NOT NULL
                );
                PRAGMA user_version=1;
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def put(self, kind: str, payload: dict, parent: str | None = None) -> dict:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if parent and self.hidden(parent):
                raise KeyError("Parent has been deleted")
            if parent and not db.execute("SELECT 1 FROM records WHERE id=?", (parent,)).fetchone():
                raise KeyError("Parent does not exist")
            db.execute(
                "INSERT INTO records VALUES (?,?,?,?,?)",
                (payload["id"], kind, parent, canonical_json(payload).decode(), time.time()),
            )
        return payload

    def hidden(self, identifier: str) -> bool:
        with self.connect() as db:
            return (
                db.execute(
                    """WITH RECURSIVE ancestors(id,parent) AS (
                SELECT id,parent FROM records WHERE id=? UNION ALL
                SELECT r.id,r.parent FROM records r JOIN ancestors a ON r.id=a.parent
            ) SELECT 1 FROM ancestors JOIN deletions d ON d.paper_id=ancestors.id LIMIT 1""",
                    (identifier,),
                ).fetchone()
                is not None
            )

    def get(self, identifier: str, kind: str, *, include_deleted=False) -> dict:
        if not include_deleted and self.hidden(identifier):
            raise KeyError("Resource deleted")
        with self.connect() as db:
            row = db.execute(
                "SELECT payload FROM records WHERE id=? AND kind=?", (identifier, kind)
            ).fetchone()
        if not row:
            raise KeyError("Resource not found")
        return json.loads(row["payload"])

    def list(self, kind: str, parent: str | None = None) -> list[dict]:
        with self.connect() as db:
            if parent:
                rows = db.execute(
                    "SELECT payload FROM records WHERE kind=? AND parent=? ORDER BY created",
                    (kind, parent),
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT payload FROM records WHERE kind=? ORDER BY created", (kind,)
                ).fetchall()
        results = [json.loads(row["payload"]) for row in rows]
        return [item for item in results if not self.hidden(item["id"])]

    def approve(self, identifier: str, spec_hash: str):
        from paper2proof.review import verify_spec
        from paper2proof.schemas.workflow import SpecVersion

        spec = self.get(identifier, "spec")
        if spec["spec_hash"] != spec_hash:
            raise Conflict("Specification hash changed")
        if spec["blockers"]:
            raise Conflict("Resolve the specification blockers before approval")
        verify_spec(SpecVersion.model_validate(spec))
        with self.connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO approvals VALUES (?,?,?)",
                (identifier, spec_hash, time.time()),
            )

    def enqueue_extraction(self, paper_id):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if self.hidden(paper_id):
                raise Conflict("Paper has been deleted")
            if db.execute("SELECT COUNT(*) FROM jobs WHERE state='queued'").fetchone()[0] >= 5:
                raise Conflict("Local queue is full (five queued jobs)")
            identifier = uuid4().hex
            db.execute(
                "INSERT INTO jobs(id,spec_id,kind,idempotency,request_hash,state,created) "
                "VALUES (?,?,'extract_pdf',?,?,'queued',?)",
                (identifier, paper_id, f"extract:{paper_id}", paper_id, time.time()),
            )
            self._event(db, identifier, "queued", "PDF extraction saved to the durable queue.")
        return self.job(identifier)

    def finish_paper(self, identifier, payload):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT payload FROM records WHERE id=? AND kind='paper'", (identifier,)
            ).fetchone()
            if not row:
                raise KeyError("Paper not found")
            old = json.loads(row[0])
            if old.get("state") != "queued" or payload["sha256"] != old["sha256"]:
                raise Conflict(
                    "Paper extraction may finish only once without changing source bytes"
                )
            db.execute("UPDATE records SET payload=? WHERE id=?", (json.dumps(payload), identifier))

    @staticmethod
    def _event(db, job_id, stage, message):
        sequence = db.execute(
            "SELECT COALESCE(MAX(sequence),0)+1 FROM events WHERE job_id=?", (job_id,)
        ).fetchone()[0]
        event = {"sequence": sequence, "timestamp": time.time(), "stage": stage, "message": message}
        db.execute("INSERT INTO events VALUES (?,?,?)", (job_id, sequence, json.dumps(event)))

    def enqueue(self, spec_id: str, spec_hash: str, kind: str, key: str) -> dict:
        request_hash = digest(
            canonical_json({"spec_id": spec_id, "spec_hash": spec_hash, "kind": kind})
        )
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if self.hidden(spec_id):
                raise Conflict("Workspace has been deleted")
            existing = db.execute("SELECT * FROM jobs WHERE idempotency=?", (key,)).fetchone()
            if existing:
                if existing["request_hash"] != request_hash:
                    raise Conflict("Idempotency key already used for a different request")
                return self._job(existing)
            if not db.execute(
                "SELECT 1 FROM approvals WHERE spec_id=? AND spec_hash=?", (spec_id, spec_hash)
            ).fetchone():
                raise Conflict("Approve this exact specification before starting")
            if db.execute("SELECT COUNT(*) FROM jobs WHERE state='queued'").fetchone()[0] >= 5:
                raise Conflict("Local queue is full (five queued jobs)")
            identifier = uuid4().hex
            db.execute(
                "INSERT INTO jobs(id,spec_id,kind,idempotency,request_hash,state,created) "
                "VALUES (?,?,?,?,?,'queued',?)",
                (identifier, spec_id, kind, key, request_hash, time.time()),
            )
            self._event(db, identifier, "queued", "Saved to the local durable queue.")
        return self.job(identifier)

    @staticmethod
    def _job(row):
        result = dict(row)
        result.pop("request_hash", None)
        result.pop("idempotency", None)
        result["result"] = json.loads(result["result"]) if result["result"] else None
        return result

    def job(self, identifier, *, include_deleted=False):
        with self.connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (identifier,)).fetchone()
        if not row:
            raise KeyError("Job not found")
        if not include_deleted and self.hidden(row["spec_id"]):
            raise KeyError("Job deleted")
        return self._job(row)

    def jobs(self):
        with self.connect() as db:
            rows = [
                self._job(row)
                for row in db.execute("SELECT * FROM jobs ORDER BY created DESC LIMIT 100")
            ]
        return [row for row in rows if not self.hidden(row["spec_id"])]

    def events(self, identifier, after=0):
        self.job(identifier)
        with self.connect() as db:
            return [
                json.loads(row[0])
                for row in db.execute(
                    "SELECT payload FROM events WHERE job_id=? AND sequence>? ORDER BY sequence",
                    (identifier, after),
                )
            ]

    def event(self, identifier, stage, message):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT state FROM jobs WHERE id=?", (identifier,)).fetchone()
            if row and row[0] not in TERMINAL:
                self._event(db, identifier, stage, message)

    def claim_job(self):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            stale = db.execute(
                "SELECT id,spec_id,kind FROM jobs WHERE state='running' AND lease_until<?",
                (time.time(),),
            ).fetchall()
            for row in stale:
                if row["kind"] == "extract_pdf":
                    paper = json.loads(
                        db.execute(
                            "SELECT payload FROM records WHERE id=?", (row["spec_id"],)
                        ).fetchone()[0]
                    )
                    if paper.get("state") == "queued":
                        paper.update(
                            state="rejected",
                            error="Parser worker interrupted; upload again to retry.",
                        )
                        db.execute(
                            "UPDATE records SET payload=? WHERE id=?",
                            (json.dumps(paper), row["spec_id"]),
                        )
                db.execute(
                    "UPDATE jobs SET state='failed',error='worker_interrupted' WHERE id=?",
                    (row[0],),
                )
                self._event(
                    db, row[0], "failed", "Worker lease expired; no automatic duplicate execution."
                )
            if db.execute("SELECT 1 FROM jobs WHERE state='running'").fetchone():
                return None
            row = db.execute(
                "SELECT id FROM jobs WHERE state='queued' ORDER BY created LIMIT 1"
            ).fetchone()
            if not row:
                return None
            db.execute(
                "UPDATE jobs SET state='running',lease_until=? WHERE id=?",
                (time.time() + 30, row[0]),
            )
            self._event(db, row[0], "running", "Local worker acquired the job.")
            identifier = row[0]
        return self.job(identifier)

    def renew_lease(self, identifier):
        with self.connect() as db:
            return (
                db.execute(
                    "UPDATE jobs SET lease_until=? WHERE id=? AND state='running'",
                    (time.time() + 30, identifier),
                ).rowcount
                == 1
            )

    def cancel(self, identifier):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT state,kind,spec_id FROM jobs WHERE id=?", (identifier,)
            ).fetchone()
            if not row:
                raise KeyError("Job not found")
            if row[0] not in TERMINAL:
                state = "canceled" if row[0] == "queued" else row[0]
                db.execute("UPDATE jobs SET canceled=1,state=? WHERE id=?", (state, identifier))
                if row[0] == "queued" and row[1] == "extract_pdf":
                    paper = json.loads(
                        db.execute("SELECT payload FROM records WHERE id=?", (row[2],)).fetchone()[
                            0
                        ]
                    )
                    paper.update(state="rejected", error="PDF extraction was canceled.")
                    db.execute(
                        "UPDATE records SET payload=? WHERE id=?", (json.dumps(paper), row[2])
                    )
                self._event(db, identifier, "cancel_requested", "Cancellation requested.")

    def finish(self, identifier, state, *, result=None, error=None):
        if state not in TERMINAL:
            raise ValueError("Invalid terminal job state")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT state,canceled FROM jobs WHERE id=?", (identifier,)).fetchone()
            if not row or row[0] != "running":
                raise Conflict("Only a running job may finish; terminal states are immutable")
            state = "canceled" if row[1] else state
            db.execute(
                "UPDATE jobs SET state=?,result=?,error=?,lease_until=NULL WHERE id=?",
                (state, json.dumps(result) if result else None, error, identifier),
            )
            self._event(db, identifier, state, error or "Job finished; see recorded evidence.")

    def descendants(self, paper_id):
        with self.connect() as db:
            records = db.execute(
                """WITH RECURSIVE children(id) AS (
                SELECT id FROM records WHERE id=? UNION ALL
                SELECT r.id FROM records r JOIN children c ON r.parent=c.id
            ) SELECT id FROM children""",
                (paper_id,),
            ).fetchall()
            ids = [row[0] for row in records]
            jobs = [
                dict(row)
                for row in db.execute("SELECT id,spec_id,state FROM jobs")
                if row["spec_id"] in ids
            ]
        return ids, jobs

    def request_delete(self, paper_id):
        self.get(paper_id, "paper")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            _, jobs = self.descendants(paper_id)
            db.execute("INSERT OR IGNORE INTO deletions VALUES (?,?,NULL)", (paper_id, time.time()))
            for job in jobs:
                if job["state"] not in TERMINAL:
                    state = "canceled" if job["state"] == "queued" else job["state"]
                    db.execute("UPDATE jobs SET state=?,canceled=1 WHERE id=?", (state, job["id"]))
                    self._event(db, job["id"], "cancel_requested", "Workspace deletion requested.")
