"""Reproducible retrieval/guardrail baseline. Metrics are not a claim of human-rated correctness."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from academy.models import ROOT
from academy.retrieval import HybridRetriever
from academy.security import validate_sql, RejectedQuery
from academy.tutor import baseline_route


def run():
    path = ROOT / "evals/golden.json"
    cases = json.loads(path.read_text())
    retriever = HybridRetriever()
    rows = []
    for case in cases:
        if case["kind"] == "retrieval":
            row = {"id": case["id"], "kind": case["kind"]}
            for mode in ("baseline", "hybrid"):
                before = time.perf_counter()
                passages = retriever.search(case["question"], level=0, k=4, hybrid=mode == "hybrid")
                row[mode + "_hit"] = any(p.level == case["expected_level"] for p in passages)
                row[mode + "_ms"] = (time.perf_counter() - before) * 1000
                row[mode + "_sources"] = [p.id for p in passages]
            rows.append(row)
        elif case["kind"] == "sql_guardrail":
            try:
                validate_sql(case["question"])
                passed = False
            except RejectedQuery:
                passed = True
            rows.append({"id": case["id"], "kind": case["kind"], "passed": passed})
        else:
            rows.append(
                {
                    "id": case["id"],
                    "kind": case["kind"],
                    "passed": baseline_route(case["question"]) == "needs_clarification",
                }
            )
    retrieval = [r for r in rows if r["kind"] == "retrieval"]
    guards = [r for r in rows if r["kind"] != "retrieval"]
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "cases": len(rows),
        "retrieval_cases": len(retrieval),
        "guardrail_cases": len(guards),
        "retrieval_mode": retriever.mode,
        "baseline_lesson_hit_at_4": sum(r["baseline_hit"] for r in retrieval) / len(retrieval),
        "hybrid_lesson_hit_at_4": sum(r["hybrid_hit"] for r in retrieval) / len(retrieval),
        "hybrid_p95_retrieval_ms": float(np.percentile([r["hybrid_ms"] for r in retrieval], 95)),
        "guardrail_pass_rate": sum(r["passed"] for r in guards) / len(guards),
        "notes": "Expected-lesson retrieval recall, not answer correctness. Cases are authored synthetic examples; no human-judge calibration, live model quality, or fine-tuning results are claimed.",
        "results": rows,
    }
    (ROOT / "evals/latest.json").write_text(json.dumps(result, indent=2))
    report = (
        f"# Measured evaluation report\n\nRun: {result['timestamp']}\n\n"
        f"Dataset: {len(rows)} cases; SHA-256 `{result['dataset_sha256']}`.\n\n"
        f"| Check | Measured result |\n|---|---:|\n"
        f"| BM25 baseline: expected lesson in top 4 | {result['baseline_lesson_hit_at_4']:.1%} |\n"
        f"| Hybrid: expected lesson in top 4 | {result['hybrid_lesson_hit_at_4']:.1%} |\n"
        f"| Hybrid retrieval p95 | {result['hybrid_p95_retrieval_ms']:.1f} ms |\n"
        f"| Selected guardrail cases | {sum(r['passed'] for r in guards)}/{len(guards)} |\n\n"
        f"{result['notes']}\n\nA missed lesson does not necessarily mean missing factual evidence: official documentation chunks can also answer a question. Conversely, a retrieved lesson does not prove that a generated answer is faithful. Inspect per-case sources in [latest.json](latest.json).\n\n"
        "GPU training, provider-backed answer evaluations, and human calibration are separate runs. Use `judge.py` and the training workflow when those resources are configured.\n"
    )
    (ROOT / "evals/REPORT.md").write_text(report)
    print(report)
    if not all(r["passed"] for r in guards):
        raise SystemExit("A guardrail regression needs investigation")


if __name__ == "__main__":
    run()
