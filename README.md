<div align="center">

# 🔥 PromQL Zero to Hero

**Start at zero. Think in signals.**

An animated Python + Streamlit academy that teaches PromQL through the SQL you already know.

[![Academy checks](https://github.com/sivalinb/promql-zero-to-hero/actions/workflows/tests.yml/badge.svg)](https://github.com/sivalinb/promql-zero-to-hero/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/Python-3.11–3.13-3776AB)
![Streamlit](https://img.shields.io/badge/Built_with-Streamlit-FF4B4B)
[![License: MIT](https://img.shields.io/badge/License-MIT-72dfb8)](LICENSE)

**11 levels · 77 quiz questions · 11 animated explainers · Real Prometheus + DuckDB**

</div>

![The academy overview with a learning journey, progress, and level cards](docs/assets/overview.png)

## Learn by watching, comparing, and doing

Every level follows the same loop:

1. **Watch it move.** Play an animated diagram, pause, scrub through five steps, and read the narration. Samples become series, labels filter signals, counters reset, windows slide, and histograms accumulate.
2. **Build a SQL bridge.** Read the related SQL concept and compare executable examples. Each comparison explicitly explains where the languages differ.
3. **Try a real query.** Run PromQL in an actual Prometheus server and SQL in DuckDB. Switch between normal traffic and an incident using reproducible synthetic data.
4. **Earn the next level.** Answer five randomly selected questions and submit a PromQL solution. A score of at least **80% plus a successful query in both scenarios** awards a badge and 100 XP.
5. **Ask for help.** Retrieve detailed teaching material with sources. Add a model endpoint for generated explanations and bounded query-debugging tools.

Progress and conversation history are scoped to the learner. A private recovery code resumes a local profile; hosted deployments can use Streamlit OIDC sign-in.

![An interactive lesson with an animated time-series diagram, playback controls, narration, and a SQL connection](docs/assets/lesson.png)

## Illustrated architecture

![PromQL Zero to Hero: a learner progresses through animated lessons, SQL comparisons, query labs, quizzes, and badges. Below, a bounded tutor uses retrieval and read-only query tools; optional LoRA training builds a router. Security and evaluations support the system.](docs/assets/architecture.png)

The illustration combines the learning experience with the supporting AI workflow. The **trained router is optional**: the repository includes the complete training pipeline, but no trained adapter or claimed fine-tuning result. The app starts with a deterministic router and reference tutor.

```mermaid
flowchart TD
    U["Learner · Streamlit"] --> L["11 lessons + Canvas animations + SQL bridges"]
    U --> Q["Quiz and practical challenge"]
    Q --> G["Python grading · 80% + two fixture scenarios"]
    G --> P["SQLite · level unlocks · badges · XP"]
    U --> T["LangGraph tutor"]
    T --> R["Route request"]
    FT["Optional evaluated LoRA router"] -.-> R
    R --> H["BM25 + embeddings · fusion · reranking"]
    D["Curated lessons + official documentation"] --> H
    H --> PLAN["Validated plan · at most one query tool"]
    PLAN --> PROM["Prometheus · synthetic metrics"]
    PLAN --> SQL["Restricted DuckDB worker"]
    G --> PROM
    PLAN --> A["Grounded answer or reference fallback"]
    PROM --> A
    SQL --> A
    A --> V["Structured output + citation validation"]
    V --> U
    E["Golden cases · adversarial tests · optional LangSmith"] -.-> T
```

The LLM has **no progress-writing tool**. Python alone validates attempts, checks ownership and prerequisites, compares actual engine results, and awards badges transactionally. Equivalent expressions can pass; grading does not compare query strings.

## Your path: level 0 → level 10

| Level | PromQL skill | SQL connection | Badge |
|---:|---|---|---|
| 0 | Samples, series, instant vs. range queries | Timestamped rows and snapshots | 🌱 First Observer |
| 1 | Label selection and matchers | `WHERE` and regular expressions | 🔎 Metric Explorer |
| 2 | Counters, gauges, metric types | Cumulative totals vs. current values | 🧭 Metric Mapper |
| 3 | Aggregation and label preservation | `GROUP BY`, `SUM`, `AVG` | 🧩 Aggregation Ace |
| 4 | `rate`, resets, rates before aggregation | `LAG` and reset-aware deltas | ⚡ Rate Ranger |
| 5 | Ratios, comparison filters, `bool` | Conditional aggregation and predicates | 🛠️ Query Builder |
| 6 | Range functions, offsets, subqueries | Time predicates and windows | ⏳ Time Traveller |
| 7 | `on`, `ignoring`, `group_left` | Joins and key uniqueness | 🔗 Matchmaker |
| 8 | Cumulative histograms and quantiles | Bucket counts vs. raw percentiles | 📊 Latency Detective |
| 9 | Missing data, recording rules, alerts, cardinality | Missing rows, materialization, state | 🛡️ Reliability Engineer |
| 10 | Incident investigation and SLO signals | Grouped thresholds and population alignment | 🏆 PromQL Hero |

**SQL is a teaching bridge, not an automatic translation promise.** `rate()` is not `AVG()`. Prometheus handles counter resets and extrapolates. `group_left` is not a SQL left outer join. Missing series are not automatically zero. Histogram quantiles estimate from buckets. Every lesson carries its own comparison limits.

## Run locally

Use Python **3.12** for the tested setup. macOS and Linux, Intel and ARM, are supported by the native bootstrap; Windows users can use Docker or WSL.

```bash
git clone https://github.com/sivalinb/promql-zero-to-hero.git
cd promql-zero-to-hero
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python scripts/bootstrap.py
streamlit run app.py
```

Open **http://localhost:8501**. If that port is occupied, add `--server.port=8517`.

The bootstrap downloads the official **Prometheus 3.15.0** binaries, checks the release SHA-256, and imports the fixtures. It starts a fixture-only engine on `127.0.0.1:9098`; no production credentials or telemetry are needed. Subsequent app launches can restart an already-installed engine. Runtime state stays in ignored `.runtime/`; binaries stay in ignored `.tools/`.

No API key is needed for lessons, animations, real query labs, quizzes, badges, or reference retrieval. Without the bootstrap, lessons remain readable but PromQL execution and badge grading require the engine.

### Docker Compose

```bash
docker compose up --build --wait
```

Open **http://localhost:8501**. Compose separates the app, Prometheus, and SQL worker. The query services have an internal network, no published ports, no provider secrets, and resource limits. Only the app can use outbound networking for a configured tutor. Progress and metrics use named volumes. See [deployment details](docs/DEPLOYMENT.md).

### Enable generated tutor answers

```bash
cp .env.example .env
```

Set `LLM_BASE_URL` (ending in `/v1`), `LLM_MODEL`, and `LLM_API_KEY` for a provider that supports the chat-completions JSON contract. Restart Streamlit. The example uses Nebius Token Factory; model availability and credentials depend on your account. A compatible local endpoint also works.

The workflow retrieves evidence, validates a one-tool plan, optionally queries fixtures, and validates the answer's cited passage IDs. Provider errors or malformed answers fall back to clearly labeled **Reference tutor** material. Valid citations do not by themselves prove factual correctness; the evaluation workflow addresses that separately. The tutor covers PromQL and related SQL within its retrieved evidence, and should acknowledge gaps.

Optional integrations:

- **Transformer retrieval:** `pip install -e '.[embeddings]'`, then set `EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2`. This downloads model weights and uses persistent Chroma. The default is lightweight local LSA embeddings, accurately labeled in the evaluation output.
- **LangSmith:** set `LANGSMITH_TRACING=true`, an API key, and a project. Tracing is off by default because prompts and answers may be sent to that service.
- **LoRA router:** follow [training/README.md](training/README.md), evaluate the merged model, then configure `ROUTER_BASE_URL` and `ROUTER_MODEL`. The tutor model and routing model are separate roles.

## How the six course weeks become a product

| Week | Techniques | Where and how they are used |
|---|---|---|
| 1 | Python, Streamlit, CSV, pandas, Plotly, AI-assisted development | `app.py`, `academy/data.py`; explore synthetic CSV data, render real query results, build the learning interface. Canvas adds controllable concept animations. |
| 2 | RAG, chunking, embeddings, hybrid retrieval, fusion, reranking, citations | `academy/retrieval.py`; preserve code fences in paragraph chunks, combine BM25 and vector similarity with reciprocal-rank fusion, rerank technical terms, retain source IDs. Optional Sentence Transformers + Chroma. |
| 3 | Stateful agents, tools, structured output, failure handling, human review | `academy/tutor.py`; a bounded LangGraph routes, retrieves, plans, optionally executes one read-only query, and explains. Pydantic schemas and fallbacks constrain failures. Learners inspect sources and run examples. |
| 4 | Golden sets, baselines, code graders, LLM judges, trace analysis | `evals/`; 40 versioned cases, measured baseline/hybrid results, guardrail checks, optional model judge with a human-calibration field, and opt-in LangSmith traces. |
| 5 | Synthetic classification data, leakage-aware splits, LoRA, merge, comparison | `training/`; 50 authored seed questions, split before variations, Qwen3-1.7B-Base LoRA configs, Colab notebook, baseline/merged evaluation, optional local routing endpoint. |
| 6 | Security and guardrails | `academy/security.py`, `progress.py`, worker isolation and tests; SQL AST allowlists, query budgets, scoped memory, untrusted retrieval, citation checks, server-owned grading, and safe secret configuration. |

Course handouts informed this mapping. Their administrative/submission instructions are not application requirements, and the PDFs are not included in the public repository.

## Data and query semantics

The bundled [CSV](data/samples.csv) contains **6,100 synthetic samples**, generated by `academy/data.py`. Normal traffic and incident windows include two services, two instances each, a deliberate counter reset, errors, gauges, scrape availability, service metadata, and classic histogram buckets. No real infrastructure or learner data is committed.

- `samples` is the historical DuckDB table; `snapshot` contains samples at the chosen evaluation time.
- Evaluation times are fixed in January 2025, intentionally making demonstrations repeatable. Prometheus retention is configured to retain these historical blocks.
- PromQL gets the real Prometheus parser, evaluation semantics, and result types. SQL executes in a fresh worker with a timeout, disabled external access, and a row cap.
- Two-scenario practical checks catch many hard-coded answers, but this is an educational assessment, not a secure certification exam. Source code and answer keys are public.

## Verification and measured results

```bash
REQUIRE_PROMETHEUS_TESTS=1 pytest -q
python evals/run.py
# Optional provider-backed judge; incurs your provider's usage charges:
python evals/judge.py
```

Tests cover all levels, real fixture queries, equivalent expressions, rate/reset behavior, ownership and unlock rules, repeat submissions, forbidden SQL, model failures and citations, and Streamlit flows. GitHub Actions also builds Compose and runs every SQL and PromQL example in both scenarios.

The checked-in [evaluation report](evals/REPORT.md) records **91.7% BM25** vs. **83.3% hybrid** expected-lesson hit@4 across 36 authored retrieval cases, plus 4/4 selected guardrail checks. **The hybrid configuration did not beat the baseline on this dataset.** Official documentation can displace lesson passages; this metric measures lesson retrieval, not generated-answer accuracy. Retain the baseline, inspect misses, and evaluate on independent human-authored questions before making quality claims. The report includes actual latency and per-case evidence.

Generated tutor quality, human judge calibration, transformer retrieval, OIDC provider integration, and GPU fine-tuning require their respective external configurations. No scores are invented for runs that have not happened.

## Project guide

```text
app.py                         Streamlit learning experience
academy/                       Engines, progress, guardrails, retrieval, tutor
academy/components/concept/    Animated HTML/Canvas teaching component
content/                       Typed curriculum and attributed reference snapshot
data/                          Reproducible synthetic CSV
scripts/                       Verified bootstrap, docs refresh, container smoke check
tests/                         Behavior, security, engine, and UI tests
evals/                         Golden cases, measured reports, optional model judge
training/                      Synthetic router data, LoRA, merge, evaluation, notebook
docs/                          Illustrated architecture, setup, security, attribution
```

Read [deployment](docs/DEPLOYMENT.md), [security boundaries](docs/SECURITY.md), [evaluation guide](evals/README.md), and [training guide](training/README.md) for the operational details.

MIT for original code and lessons. Bundled reference material retains its upstream licenses; see [NOTICE.md](NOTICE.md). This is an independent educational project.
