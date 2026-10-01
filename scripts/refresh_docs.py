"""Explicit administrator refresh; chat users cannot choose URLs or change the corpus."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import httpx
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from academy.models import ROOT

SOURCES = [
    "https://prometheus.io/docs/prometheus/latest/querying/basics/",
    "https://prometheus.io/docs/prometheus/latest/querying/operators/",
    "https://prometheus.io/docs/prometheus/latest/querying/functions/",
    "https://prometheus.io/docs/concepts/metric_types/",
    "https://prometheus.io/docs/practices/histograms/",
    "https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/",
    "https://prometheus.io/docs/prometheus/latest/configuration/recording_rules/",
    "https://prometheus.io/docs/practices/naming/",
    "https://duckdb.org/docs/current/sql/query_syntax/select.html",
    "https://duckdb.org/docs/current/sql/query_syntax/groupby.html",
    "https://duckdb.org/docs/current/sql/functions/window_functions.html",
]


def refresh():
    documents = []
    for url in SOURCES:
        response = httpx.get(url, timeout=30, follow_redirects=True)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else url
        main = soup.find("main") or soup.find("article") or soup.body or soup
        for element in main.select("nav, footer, header, script, style, .sidebar"):
            element.decompose()
        for pre in main.find_all("pre"):
            pre.replace_with("\n\n```\n" + pre.get_text() + "\n```\n\n")
        text = main.get_text("\n", strip=True)
        if len(text) < 200:
            raise ValueError(f"Reference page did not contain enough readable text: {url}")
        # Preserve paragraphs as chunk boundaries and complete preformatted query examples.
        text = "\n\n".join(part for part in text.splitlines() if part.strip())
        documents.append(
            {
                "url": url,
                "title": title,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
                "text": text,
            }
        )
        print(title, len(text), flush=True)
    destination = ROOT / "content/reference_docs.json"
    destination.write_text(json.dumps(documents, indent=2))
    print("Wrote", destination)


if __name__ == "__main__":
    refresh()
