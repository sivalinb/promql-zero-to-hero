import pytest
from academy.models import curriculum, glossary
from academy.engine import sql_query


def test_every_concept_has_a_complete_guided_explanation():
    levels = curriculum()
    assert len(levels) == 11
    assert len({level.badge for level in levels}) == 11
    assert sum(len(level.questions) for level in levels) == 77
    assert sum(len(level.lessons) for level in levels) == 37
    for level in levels:
        for lesson in level.lessons:
            assert len(lesson.body) > 200 and len(lesson.sql_connection) > 100
            assert len(lesson.animation["steps"]) == 5
            assert all(step["title"] and len(step["explanation"]) > 35 for step in lesson.animation["steps"])
            assert lesson.definition and lesson.analogy and lesson.remember
            assert all(term in glossary() for term in lesson.terms)
            assert len(lesson.check.explanation) > 30
        assert level.lab_query and level.sql and level.sources and level.equivalence


def test_foundations_do_not_require_advanced_queries_to_earn_badges():
    # Raw measurements should be understood before rate, aggregation, or percentile functions.
    levels = curriculum()
    assert [level.lab_query for level in levels[:3]] == [
        "app_active_sessions",
        "http_requests_total",
        "http_request_duration_seconds_bucket",
    ]
    first_rate = next(level.id for level in levels if "rate(" in level.lab_query)
    assert first_rate > 2
    assert "sum_over_time" in levels[5].lab_query


@pytest.mark.parametrize("level", curriculum(), ids=lambda x: f"level-{x.id}")
def test_all_sql_examples_execute(level):
    result = sql_query(level.sql)
    assert result["columns"]
