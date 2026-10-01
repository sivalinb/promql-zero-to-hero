# Evaluate what the product actually does

`golden.json` is a versioned 40-case authored dataset: 36 retrieval cases, two SQL boundary cases, and two prompt-boundary cases. It is a starting set, not a large independent benchmark. Pytest covers additional safety and behavioral cases.

Run `python evals/run.py` from the repository root. The script compares sparse and hybrid retrieval under the same technical-term/current-level reranking, writes actual per-case sources to `latest.json`, and records the dataset hash, lesson hit@4, latency, and guardrail results in `REPORT.md`. Neither hit@4 nor passing four guardrail examples establishes answer correctness or comprehensive security.

The initial hybrid configuration underperforms the sparse baseline on expected-lesson retrieval. Do not hide that delta. Inspect documentation-versus-lesson ranking and duplicate concepts, gather independent learner questions, and compare a candidate change on a held-out set before promotion. A relevant official-document passage may answer a question even when the expected lesson is absent.

`chunk_text(..., semantic=False)` provides a fixed-character chunking baseline. The default preserves paragraphs and fenced code. A proper chunking experiment should compare retrieval and answer metrics using the same corpus and questions, rather than assuming semantic chunking is better.

## Optional live answer judging

Configure a model in `.env`, then run `python evals/judge.py`. This calls the tutor and a model judge, consumes provider usage, and writes private runtime results to `.runtime/live-judge.json`. Each record contains actual mode, latency, tokens, model scores, and a null `human_review` field. A reference-mode fallback must not be counted as a successful generative answer.

Use a different judge model if possible to reduce self-preference. The initial script uses the configured provider/model for both roles; treat scores as a diagnostic. Before trusting aggregate results:

1. Have a PromQL-capable reviewer independently score a stratified subset, including rates, missing data, vector matching, histograms, and refusals.
2. Use a 1–5 rubric: **faithfulness** to evidence, **relevance** to the question, and **SQL accuracy**, including stated analogy limits.
3. Record reviewer scores and rationale under `human_review`; compare agreement and investigate confident but unsupported responses.
4. Separate syntax/execution success, retrieval success, citation validity, and factual quality. One is not a substitute for the others.
5. Report provider/model versions, prompt/corpus/dataset hashes, mode/fallback rates, token usage, latency, and uncertainty. Price cost using the provider's actual dated price schedule.

## LangSmith

With `LANGSMITH_TRACING=true` and credentials configured, the LangGraph run emits node-level traces tagged `curriculum-v1`, including the lesson level. Traces may contain learner questions and history; keep access private.

`python evals/upload_dataset.py` explicitly uploads only the authored synthetic golden set to a new version-named LangSmith dataset. It does not upload learner chats or make datasets public. Run it only for an account/project you intend to use. The local JSON remains the reviewable source of truth.
