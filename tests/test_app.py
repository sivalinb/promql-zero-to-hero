from streamlit.testing.v1 import AppTest
from academy.models import ROOT, CURRICULUM_VERSION, curriculum
from academy.progress import ProgressStore


def test_beginner_flow_reviews_one_concept_then_practices_and_takes_a_quiz(monkeypatch, tmp_path):
    db = tmp_path / "ui.db"
    monkeypatch.setenv("ACADEMY_DB", str(db))
    app = AppTest.from_file(ROOT / "app.py", default_timeout=45).run()
    app.radio(key="page").set_value("Learn").run()
    assert not app.exception
    assert app.title[0].value == "What is a time series?"
    assert len(app.radio) == 3  # navigation, route, one practice check; no premature quiz
    check = curriculum()[0].lessons[0].check
    check_radio = next(r for r in app.radio if r.label == check.prompt)
    check_radio.set_value(check.answer)
    next(b for b in app.button if b.label == "Check my understanding").click().run()
    assert any(check.explanation in s.value for s in app.success)
    for _ in range(3):
        app.button(key="next-concept").click().run()
        assert not app.exception
    view_key = f"level-view-{CURRICULUM_VERSION}-0"
    assert app.radio(key=view_key).value == "Practice the query"
    app.checkbox(key=f"lesson-{CURRICULUM_VERSION}-0-compare").check().run()
    app.button(key=f"lesson-{CURRICULUM_VERSION}-0-run-sql").click().run(timeout=20)
    assert not app.exception and not app.error
    assert len(app.dataframe) >= 1
    app.radio(key=view_key).set_value("Earn the badge").run()
    assert len(app.radio) == 7  # five assessed questions, route, navigation
    assert len(ProgressStore(db).summary(app.session_state["profile"])["read_lessons"]) == 3
    app.radio(key="page").set_value("Word guide").run()
    app.text_input[0].set_value("bucket").run()
    assert not app.exception
    assert any("upper bound" in m.value.lower() for m in app.markdown)
    app.radio(key="page").set_value("My badges").run()
    assert not app.exception


def test_all_37_concepts_render_and_navigation_state_is_per_level(monkeypatch, tmp_path):
    db = tmp_path / "all-concepts.db"
    monkeypatch.setenv("ACADEMY_DB", str(db))
    store = ProgressStore(db)
    learner, _ = store.create("UI fixture")
    # UI-only fixture. Real grading and all prerequisites are exercised in test_progress.
    with store.connect() as con:
        con.executemany(
            "INSERT INTO completions_v2 VALUES (?,?,100,?)", [(learner, i, "2026-09-30") for i in range(11)]
        )
    app = AppTest.from_file(ROOT / "app.py", default_timeout=45)
    app.session_state["profile"] = learner
    app.session_state["page"] = "Learn"
    app.run()
    for level in curriculum():
        app.selectbox(key="level").set_value(level.id).run()
        for i, lesson in enumerate(level.lessons):
            app.selectbox(key=f"chapter-{CURRICULUM_VERSION}-{level.id}").set_value(i).run()
            assert not app.exception, lesson.id
            assert any(lesson.definition in m.value for m in app.markdown)


def test_returning_learner_starts_at_first_unread_concept(monkeypatch, tmp_path):
    db = tmp_path / "resume-reading.db"
    monkeypatch.setenv("ACADEMY_DB", str(db))
    store = ProgressStore(db)
    learner, _ = store.create()
    store.mark_lesson(learner, 0, curriculum()[0].lessons[0].id)
    app = AppTest.from_file(ROOT / "app.py", default_timeout=45)
    app.session_state["profile"] = learner
    app.session_state["page"] = "Learn"
    app.run()
    assert not app.exception
    assert app.selectbox(key=f"chapter-{CURRICULUM_VERSION}-0").value == 1
    assert store.summary(learner)["xp"] == 0
