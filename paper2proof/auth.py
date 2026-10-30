"""Local single-owner sessions. No external identity service or network calls."""

import hashlib
import hmac
import json
import secrets
import time

from paper2proof.store import Store


class LocalAuth:
    def __init__(self, store: Store):
        self.store = store
        path = store.root / "auth.json"
        if not path.exists():
            salt = secrets.token_bytes(32)
            code = secrets.token_urlsafe(24)
            record = {"salt": salt.hex(), "hash": self.derive(code, salt).hex()}
            with path.open("x", encoding="utf-8") as stream:
                json.dump(record, stream)
            # User retrieves this locally; never print it or serve it over HTTP.
            with (store.root / "access-code.txt").open("x", encoding="utf-8") as stream:
                stream.write(code)
        self.record = json.loads(path.read_text(encoding="utf-8"))
        with store.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY, expires REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS login_failures (at REAL NOT NULL);
            """)

    @staticmethod
    def derive(code, salt):
        return hashlib.pbkdf2_hmac("sha256", code.encode(), salt, 200000)

    def login(self, code: str) -> str | None:
        with self.store.connect() as db:
            db.execute("DELETE FROM login_failures WHERE at<?", (time.time() - 60,))
            if db.execute("SELECT COUNT(*) FROM login_failures").fetchone()[0] >= 5:
                raise ValueError("Too many failed sign-ins. Wait one minute.")
        candidate = self.derive(code, bytes.fromhex(self.record["salt"]))
        if not hmac.compare_digest(candidate.hex(), self.record["hash"]):
            with self.store.connect() as db:
                db.execute("INSERT INTO login_failures VALUES (?)", (time.time(),))
            return None
        token = secrets.token_urlsafe(32)
        with self.store.connect() as db:
            db.execute("DELETE FROM sessions WHERE expires<?", (time.time(),))
            db.execute(
                "INSERT INTO sessions VALUES (?,?)",
                (hashlib.sha256(token.encode()).hexdigest(), time.time() + 12 * 3600),
            )
        return token

    def authenticated(self, token: str | None) -> bool:
        if not token or len(token) > 200:
            return False
        with self.store.connect() as db:
            return (
                db.execute(
                    "SELECT 1 FROM sessions WHERE token_hash=? AND expires>?",
                    (hashlib.sha256(token.encode()).hexdigest(), time.time()),
                ).fetchone()
                is not None
            )

    def logout(self, token: str | None):
        if token:
            with self.store.connect() as db:
                db.execute(
                    "DELETE FROM sessions WHERE token_hash=?",
                    (hashlib.sha256(token.encode()).hexdigest(),),
                )
