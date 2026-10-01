from streamlit.testing.v1 import AppTest
from academy.models import ROOT


def test_overview_lessons_and_labs_render_without_exceptions(monkeypatch, tmp_path):
    monkeypatch.setenv("ACADEMY_DB", str(tmp_path / "ui.db"))
    app = AppTest.from_file(ROOT / "app.py", default_timeout=45).run()
    assert not app.exception
    app.button[0].click().run() if app.button[0].label == "Start level 0 →" else None
    # The sidebar navigation key is stable even if recovery controls change order.
    app.radio(key="page").set_value("Learn").run()
    assert not app.exception
    assert app.title[0].value == "Meet your metrics"
    assert len(app.radio) >= 8  # navigation, scenario, view, five quiz questions
    app.radio(key="page").set_value("Query lab").run()
    app.button(key="lab-0-run-sql").click().run(timeout=20)
    assert not app.exception and not app.error
    assert len(app.dataframe) >= 1
    app.radio(key="page").set_value("My badges").run()
    assert not app.exception
