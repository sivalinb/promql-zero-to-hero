# Measured evaluation report

Run: 2026-10-01T03:16:09.124274+00:00

Dataset: 50 cases; SHA-256 `680e89783cba91c8fbe5b1e77455454e09534927f9bf381064df8c7a1596683c`.

| Check | Measured result |
|---|---:|
| BM25 baseline: expected lesson in top 4 | 91.3% |
| Hybrid: expected lesson in top 4 | 89.1% |
| Hybrid retrieval p95 | 1.9 ms |
| Selected guardrail cases | 4/4 |

Expected-lesson retrieval recall, not answer correctness. Cases are authored synthetic examples; no human-judge calibration, live model quality, or fine-tuning results are claimed.

A missed lesson does not necessarily mean missing factual evidence: official documentation chunks can also answer a question. Conversely, a retrieved lesson does not prove that a generated answer is faithful. Inspect per-case sources in [latest.json](latest.json).

GPU training, provider-backed answer evaluations, and human calibration are separate runs. Use `judge.py` and the training workflow when those resources are configured.
