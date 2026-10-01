"""Persistent, user-scoped attempts and idempotent badge awards."""

from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
from academy.models import ROOT, curriculum
from academy.data import EVALUATION_TIMES
from academy.engine import prom_query, results_equal


class ProgressStore:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path or ROOT / ".runtime/progress.sqlite3")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS profiles(id TEXT PRIMARY KEY, name TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS completions(
                    profile TEXT NOT NULL, level INTEGER NOT NULL, score INTEGER NOT NULL,
                    completed TEXT NOT NULL, PRIMARY KEY(profile, level));
                CREATE TABLE IF NOT EXISTS attempts(
                    id TEXT PRIMARY KEY, profile TEXT NOT NULL, level INTEGER NOT NULL,
                    question_ids TEXT NOT NULL, result TEXT, created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS messages(
                    id INTEGER PRIMARY KEY, profile TEXT NOT NULL, role TEXT NOT NULL, body TEXT NOT NULL);
            """)

    def connect(self):
        con = sqlite3.connect(self.path, timeout=10)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        return con

    @staticmethod
    def token_id(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def create(self, name: str = "Explorer") -> tuple[str, str]:
        token = secrets.token_urlsafe(32)
        identity = self.token_id(token)
        with self.connect() as db:
            db.execute("INSERT INTO profiles VALUES (?, ?)", (identity, name.strip()[:32] or "Explorer"))
        return identity, token

    def resume(self, token: str) -> str | None:
        identity = self.token_id(token.strip())
        with self.connect() as db:
            return (
                identity if db.execute("SELECT 1 FROM profiles WHERE id=?", (identity,)).fetchone() else None
            )

    def oidc_profile(self, issuer: str, subject: str, name: str) -> str:
        identity = self.token_id("oidc:" + issuer + ":" + subject)
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO profiles VALUES (?,?)", (identity, name[:32]))
        return identity

    def summary(self, profile: str) -> dict:
        with self.connect() as db:
            owner = db.execute("SELECT name FROM profiles WHERE id=?", (profile,)).fetchone()
            if not owner:
                raise ValueError("Unknown learner profile")
            completed = [
                dict(x)
                for x in db.execute(
                    "SELECT level, score, completed FROM completions WHERE profile=? ORDER BY level",
                    (profile,),
                )
            ]
            attempts = db.execute(
                "SELECT COUNT(*) FROM attempts WHERE profile=? AND result IS NOT NULL", (profile,)
            ).fetchone()[0]
        done = {row["level"] for row in completed}
        unlocked = 0
        while unlocked < 10 and unlocked in done:
            unlocked += 1
        return {
            "name": owner["name"],
            "completed": completed,
            "unlocked": unlocked,
            "attempts": attempts,
            "xp": len(done) * 100,
        }

    def start_attempt(self, profile: str, level: int) -> dict:
        if not 0 <= level <= 10 or level > self.summary(profile)["unlocked"]:
            raise PermissionError("Complete the preceding level first.")
        with self.connect() as db:
            previous = db.execute(
                "SELECT * FROM attempts WHERE profile=? AND level=? AND result IS NULL "
                "ORDER BY created DESC LIMIT 1",
                (profile, level),
            ).fetchone()
            if previous:
                return dict(previous)
            questions = secrets.SystemRandom().sample(list(curriculum()[level].questions), 5)
            attempt = {
                "id": secrets.token_hex(16),
                "profile": profile,
                "level": level,
                "question_ids": json.dumps([q.id for q in questions]),
                "result": None,
                "created": datetime.now(timezone.utc).isoformat(),
            }
            db.execute(
                "INSERT INTO attempts VALUES (:id,:profile,:level,:question_ids,:result,:created)", attempt
            )
            return attempt

    def grade(self, profile: str, attempt_id: str, answers: dict[str, int], query: str) -> dict:
        with self.connect() as db:
            attempt = db.execute(
                "SELECT * FROM attempts WHERE id=? AND profile=?", (attempt_id, profile)
            ).fetchone()
        if not attempt:
            raise PermissionError("Attempt does not belong to this learner.")
        if attempt["result"]:
            return json.loads(attempt["result"])
        level_id = attempt["level"]
        if level_id > self.summary(profile)["unlocked"]:
            raise PermissionError("This level is locked.")
        level = curriculum()[level_id]
        questions = {q.id: q for q in level.questions}
        selected = json.loads(attempt["question_ids"])
        feedback = [
            {
                "id": ident,
                "correct": answers.get(ident) == questions[ident].answer,
                "explanation": questions[ident].explanation,
                "answer": questions[ident].options[questions[ident].answer],
            }
            for ident in selected
        ]
        score = round(sum(item["correct"] for item in feedback) / len(feedback) * 100)
        # Always execute the submitted expression against both independent fixture scenarios.
        # No model output, widget flag, or client-supplied score is trusted here.
        lab_pass, lab_message = True, "Your query passed both the normal and incident scenarios."
        try:
            for at in EVALUATION_TIMES:
                if not results_equal(prom_query(query, at), prom_query(level.lab_query, at)):
                    lab_pass, lab_message = (
                        False,
                        "The result differs in at least one scenario. Check labels, values, and missing series.",
                    )
                    break
        except (ValueError, RuntimeError) as exc:
            lab_pass, lab_message = False, str(exc)
        result = {
            "score": score,
            "lab_pass": lab_pass,
            "passed": score >= 80 and lab_pass,
            "feedback": feedback,
            "lab_message": lab_message,
            "level": level_id,
        }
        with self.connect() as db:
            # Transaction plus unique constraint makes retries/concurrent submissions idempotent.
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT result FROM attempts WHERE id=? AND profile=?", (attempt_id, profile)
            ).fetchone()[0]
            if existing:
                return json.loads(existing)
            db.execute(
                "UPDATE attempts SET result=? WHERE id=? AND profile=?",
                (json.dumps(result), attempt_id, profile),
            )
            if result["passed"]:
                db.execute(
                    "INSERT OR IGNORE INTO completions VALUES (?,?,?,?)",
                    (profile, level_id, score, datetime.now(timezone.utc).isoformat()),
                )
        return result

    def remember(self, profile: str, role: str, body: str):
        if role not in ("user", "assistant"):
            raise ValueError("Invalid conversation role")
        with self.connect() as db:
            db.execute("INSERT INTO messages(profile,role,body) VALUES (?,?,?)", (profile, role, body[:6000]))
            db.execute(
                "DELETE FROM messages WHERE profile=? AND id NOT IN "
                "(SELECT id FROM messages WHERE profile=? ORDER BY id DESC LIMIT 20)",
                (profile, profile),
            )

    def history(self, profile: str) -> list[dict]:
        with self.connect() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT role,body FROM messages WHERE profile=? ORDER BY id", (profile,)
                )
            ]

    def clear_history(self, profile: str):
        with self.connect() as db:
            db.execute("DELETE FROM messages WHERE profile=?", (profile,))
