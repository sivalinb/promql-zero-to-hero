import pytest
from academy.models import curriculum
from academy.engine import sql_query


def test_all_levels_have_complete_original_material():
    levels = curriculum()
    assert len(levels) == 11
    assert len({l.badge for l in levels}) == 11
    assert len({l.animation["kind"] for l in levels}) == 11
    assert sum(len(l.questions) for l in levels) == 77
    for level in levels:
        assert len(level.animation["steps"]) == 5
        assert all(len(lesson.body) > 200 and len(lesson.sql_connection) > 100 for lesson in level.lessons)
        assert level.lab_query and level.sql and level.sources and level.equivalence


@pytest.mark.parametrize("level", curriculum(), ids=lambda x: f"level-{x.id}")
def test_all_sql_examples_execute(level):
    result = sql_query(level.sql)
    assert result["columns"]
