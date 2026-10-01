import json
import os
import pytest
from academy.models import curriculum
from academy.progress import ProgressStore
from academy.engine import ready


def test_profiles_cannot_read_each_others_memory(tmp_path):
    store = ProgressStore(tmp_path / "progress.db")
    alice, token = store.create("Alice")
    bob, _ = store.create("Bob")
    store.remember(alice, "user", "Explain histograms")
    assert store.history(bob) == []
    assert store.resume(token) == alice
    assert store.resume("incorrect-code") is None


def test_attempts_persist_and_locks_are_enforced(tmp_path):
    store = ProgressStore(tmp_path / "progress.db")
    alice, _ = store.create()
    first = store.start_attempt(alice, 0)
    assert ProgressStore(store.path).start_attempt(alice, 0)["id"] == first["id"]
    with pytest.raises(PermissionError):
        store.start_attempt(alice, 10)
    bob, _ = store.create()
    with pytest.raises(PermissionError):
        store.grade(bob, first["id"], {}, "app_active_sessions")


def test_entire_progression_and_awards_are_idempotent(tmp_path):
    if not ready():
        if os.getenv("REQUIRE_PROMETHEUS_TESTS") == "1":
            pytest.fail("Real engine required")
        pytest.skip("Real engine required")
    store = ProgressStore(tmp_path / "progress.db")
    learner, _ = store.create()
    for level in curriculum():
        attempt = store.start_attempt(learner, level.id)
        questions = {q.id: q for q in level.questions}
        answers = {ident: questions[ident].answer for ident in json.loads(attempt["question_ids"])}
        # Wrong practical work cannot unlock a level even with a perfect knowledge quiz.
        if level.id == 0:
            failed = store.grade(learner, attempt["id"], answers, "vector(0)")
            assert failed["score"] == 100 and not failed["passed"]
            assert store.summary(learner)["unlocked"] == 0
            attempt = store.start_attempt(learner, level.id)
            answers = {ident: questions[ident].answer for ident in json.loads(attempt["question_ids"])}
        result = store.grade(learner, attempt["id"], answers, level.lab_query)
        assert result["passed"]
        assert store.grade(learner, attempt["id"], {}, "wrong") == result
        assert store.summary(learner)["xp"] == (level.id + 1) * 100
    summary = store.summary(learner)
    assert len(summary["completed"]) == 11 and summary["xp"] == 1100
    assert ProgressStore(store.path).summary(learner)["xp"] == 1100


def test_concept_progress_is_scoped_and_does_not_award_badges(tmp_path):
    store = ProgressStore(tmp_path / "concepts.db")
    alice, _ = store.create()
    bob, _ = store.create()
    lesson = curriculum()[0].lessons[0].id
    store.mark_lesson(alice, 0, lesson)
    store.mark_lesson(alice, 0, lesson)
    assert ProgressStore(store.path).summary(alice)["read_lessons"] == [lesson]
    assert store.summary(alice)["xp"] == 0
    assert store.summary(bob)["read_lessons"] == []
    with pytest.raises(PermissionError):
        store.mark_lesson(alice, 1, curriculum()[1].lessons[0].id)
    with pytest.raises(ValueError):
        store.mark_lesson(alice, 0, "not-a-lesson")


def test_previous_course_badges_and_attempts_are_preserved_without_reinterpreting_them(tmp_path):
    import sqlite3

    path = tmp_path / "legacy.db"
    profile = ProgressStore.token_id("legacy-learner")
    with sqlite3.connect(path) as db:
        db.executescript("""CREATE TABLE profiles(id TEXT PRIMARY KEY, name TEXT NOT NULL);
            CREATE TABLE completions(profile TEXT, level INTEGER, score INTEGER, completed TEXT);
            CREATE TABLE attempts(id TEXT PRIMARY KEY, profile TEXT, level INTEGER, question_ids TEXT, result TEXT, created TEXT);""")
        db.execute("INSERT INTO profiles VALUES (?,?)", (profile, "Earlier learner"))
        db.execute("INSERT INTO completions VALUES (?,1,100,?)", (profile, "2026-09-30"))
        db.execute(
            "INSERT INTO attempts VALUES (?,?,1,?,NULL,?)",
            ("old-attempt", profile, '["old-question"]', "2026-09-30"),
        )
    store = ProgressStore(path)
    summary = store.summary(profile)
    assert summary["unlocked"] == summary["xp"] == summary["attempts"] == 0
    assert summary["completed"] == []
    assert summary["legacy_completed"][0]["level"] == 1
    assert store.resume("legacy-learner") == profile
    with pytest.raises(PermissionError):
        store.grade(profile, "old-attempt", {}, "up")
    with store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0] == 1
    current = store.start_attempt(profile, 0)
    assert all(ident.startswith("v2-") for ident in json.loads(current["question_ids"]))
