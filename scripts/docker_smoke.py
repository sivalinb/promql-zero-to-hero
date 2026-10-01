"""Run inside the academy container to exercise the isolated services."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from academy.models import curriculum
from academy.engine import prom_query, sql_query, query_rows, ready
from academy.data import EVALUATION_TIMES

assert ready(), "Prometheus must be ready"
for at in EVALUATION_TIMES:
    for level in curriculum():
        prom_query(level.lab_query, at)
        assert sql_query(level.sql, at)["columns"]
assert len(query_rows(prom_query("app_active_sessions"))) == 4
print("All 11 PromQL and SQL examples passed in both container scenarios.")
