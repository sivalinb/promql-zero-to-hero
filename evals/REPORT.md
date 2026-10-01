# Measured evaluation report

Run: 2026-10-01T02:14:03.113966+00:00

Dataset: 40 cases; SHA-256 `66a385944a4e61bffcd8c9fcbdee075faf83160683b6901fae3555af0fe0c59a`.

| Check | Measured result |
|---|---:|
| BM25 baseline: expected lesson in top 4 | 91.7% |
| Hybrid: expected lesson in top 4 | 83.3% |
| Hybrid retrieval p95 | 1.6 ms |
| Selected guardrail cases | 4/4 |

Expected-lesson retrieval recall, not answer correctness. Cases are authored synthetic examples; no human-judge calibration, live model quality, or fine-tuning results are claimed.

A missed lesson does not necessarily mean missing factual evidence: official documentation chunks can also answer a question. Conversely, a retrieved lesson does not prove that a generated answer is faithful. Inspect per-case sources in [latest.json](latest.json).

GPU training, provider-backed answer evaluations, and human calibration are separate runs. Use `judge.py` and the training workflow when those resources are configured.
