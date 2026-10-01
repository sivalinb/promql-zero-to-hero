from http.server import HTTPServer
from threading import Thread
import httpx
import pytest
from academy.sql_server import Handler
from academy.data import CALM_TIME


@pytest.fixture
def endpoint(monkeypatch):
    monkeypatch.delenv("SQL_RUNNER_URL", raising=False)
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield "http://127.0.0.1:" + str(server.server_port)
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def test_sql_service_executes_only_fixture_queries(endpoint):
    with httpx.Client(base_url=endpoint, trust_env=False) as client:
        result = client.post(
            "/query", json={"query": "SELECT COUNT(*) AS n FROM snapshot WHERE metric='up'", "at": CALM_TIME}
        )
        assert result.status_code == 200
        assert result.json()["rows"] == [[4]]
        blocked = client.post(
            "/query", json={"query": "SELECT * FROM read_csv('/etc/passwd')", "at": CALM_TIME}
        )
        assert blocked.status_code == 400
        assert "error" in blocked.json()
        invalid_time = client.post("/query", json={"query": "SELECT 1", "at": 0})
        assert invalid_time.status_code == 400


def test_sidecar_failure_is_a_readable_engine_error(monkeypatch):
    from academy.engine import sql_query, EngineUnavailable

    monkeypatch.setenv("SQL_RUNNER_URL", "http://sql:8080")

    def unavailable(*args, **kwargs):
        raise httpx.ConnectError("raw network details")

    monkeypatch.setattr(httpx, "post", unavailable)
    with pytest.raises(EngineUnavailable, match="SQL worker is unavailable"):
        sql_query("SELECT 1")
