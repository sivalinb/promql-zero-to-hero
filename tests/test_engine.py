import os
import pytest
from academy.data import CALM_TIME, BURST_TIME
from academy.models import curriculum
from academy.engine import prom_query, query_rows, results_equal, ready


@pytest.fixture(scope="module", autouse=True)
def engine_required():
    if not ready():
        if os.getenv("REQUIRE_PROMETHEUS_TESTS") == "1":
            pytest.fail("CI requires the real Prometheus fixture engine")
        pytest.skip("Run python scripts/bootstrap.py for real-engine integration tests")


@pytest.mark.parametrize("level", curriculum(), ids=lambda x: f"level-{x.id}")
def test_query_examples_in_both_scenarios(level):
    for timestamp in (CALM_TIME, BURST_TIME):
        result = prom_query(level.lab_query, timestamp)
        assert result["resultType"] == "vector"


def test_counter_reset_does_not_make_rates_negative():
    assert all(row["value"] > 0 for row in query_rows(prom_query("rate(http_requests_total[20m])")))


def test_incident_is_distinguishable_from_baseline():
    query = curriculum()[10].lab_query
    assert query_rows(prom_query(query, CALM_TIME)) == []
    assert len(query_rows(prom_query(query, BURST_TIME))) == 2
    failures = query_rows(prom_query("count by(service)(up == 0)", BURST_TIME))
    assert failures[0]["service"] == "web" and failures[0]["value"] == 1


def test_different_valid_query_syntax_is_accepted():
    assert results_equal(
        prom_query("sum(app_active_sessions) by(service)"), prom_query("sum by(service)(app_active_sessions)")
    )


def test_scalar_hardcoding_and_wrong_labels_are_rejected():
    correct = prom_query("sum by(service)(app_active_sessions)")
    assert not results_equal(prom_query("23"), correct)
    assert not results_equal(prom_query("sum(app_active_sessions)"), correct)
