"""Start the fixture-only Prometheus service in Docker."""

import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.bootstrap import seed
from academy.models import ROOT

seed(export=False)
config = ROOT / ".runtime/prometheus.yml"
config.write_text("global:\n  scrape_interval: 30s\nscrape_configs: []\n")
binary = str(ROOT / ".tools/prometheus")
os.execv(
    binary,
    [
        binary,
        "--config.file=" + str(config),
        "--storage.tsdb.path=" + str(ROOT / ".runtime/prometheus"),
        "--web.listen-address=0.0.0.0:9090",
        "--query.timeout=3s",
        "--query.max-samples=100000",
        "--query.max-concurrency=4",
        "--storage.tsdb.retention.time=36500d",
    ],
)
