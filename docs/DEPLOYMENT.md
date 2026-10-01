# Running and configuring the academy

## Tested local path

From the repository root, create a Python 3.12 virtual environment, install `pip install -e '.[dev]'`, run `python scripts/bootstrap.py`, then `streamlit run app.py`. Bootstrap makes outbound requests only to the official Prometheus GitHub release. Runtime inference does not download binaries.

The native Prometheus process runs independently of Streamlit. Its PID and log are in `.runtime/prometheus.pid` and `.runtime/prometheus.log`. Stop that specific process when finished (`kill "$(cat .runtime/prometheus.pid)"` after checking the PID is still the fixture engine). The next app launch can restart it. Do not replace a running fixture database; stop the engine before reseeding. Deleting `.runtime` also deletes local progress.

## Upgrading from the first course

Keep the existing progress database and restart Streamlit after updating the checkout. The foundations curriculum uses separate versioned completion, attempt, and concept-reading tables. Original completion and attempt records remain intact; earlier badges appear in the previous-course archive under their original names. Existing recovery codes and OIDC identities continue to work. The new level order begins at Level 0 because old level numbers no longer describe the same topics. Back up the SQLite database before any deployment update.

## Configuration

Copy `.env.example` to `.env`. Never commit `.env`, `.streamlit/secrets.toml`, runtime databases, provider traces, or model weights.

| Variable | Purpose | Default |
|---|---|---|
| `PROMETHEUS_URL` | Administrator-owned fixture endpoint | `http://127.0.0.1:9098` |
| `SQL_RUNNER_URL` | Internal isolated SQL service | Empty: local subprocess |
| `ACADEMY_DB` | Persistent SQLite progress path | `.runtime/progress.sqlite3` |
| `LLM_BASE_URL` | Chat-completions base URL, ending `/v1` | Unconfigured |
| `LLM_MODEL`, `LLM_API_KEY` | Tutor model and provider credential | Unconfigured |
| `ROUTER_BASE_URL`, `ROUTER_MODEL`, `ROUTER_API_KEY` | Optional evaluated routing model | Deterministic router |
| `EMBEDDING_MODEL` | Optional Sentence Transformers model | Local LSA embeddings |
| `LANGSMITH_TRACING` | Send LangGraph traces to LangSmith | `false` |
| `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT` | Tracing destination | Unconfigured |
| `REQUIRE_LOGIN` | Require Streamlit OIDC authentication | `false` for localhost |

Model endpoints are fixed administrator configuration. Learner text cannot choose an endpoint. HTTPS is required except explicitly allowed local inference hosts. Providers must accept JSON-mode chat completions; incompatible output causes a reference-mode fallback. Planning and answering can make two model calls, plus an optional router call. Each call has a 20-second timeout and one retry for selected transient HTTP errors; reported usage is tokens, not an invented dollar estimate.

To refresh the evidence snapshot, run `python scripts/refresh_docs.py`, inspect the source URLs and diff, run the evaluation suite, and restart the app. Retrieval indexes are cached for the process lifetime. Optional transformer weights are downloaded on first use and Chroma stores vectors under `.runtime/chroma`.

## Docker services

Use current Docker Compose v2 supporting optional `env_file` entries. Run `docker compose up --build --wait`, then visit `http://localhost:8501`. `docker compose down` stops the services and retains named volumes. Avoid `down -v` unless you intend to delete progress and fixture storage.

The app, SQL worker, and Prometheus run as UID 10001, with dropped Linux capabilities, read-only root filesystems, bounded temporary storage, and CPU/memory/PID limits. Only the app receives `.env`; the two engines use an internal Docker network, publish no host ports, and receive no provider credentials. The SQL worker has no mounted volumes. A separate app network permits configured inference requests.

Use `docker compose exec -T academy python scripts/docker_smoke.py` to check all lesson queries against the container services. GitHub Actions runs this check. Docker was not installed on the initial development laptop; remote CI is the container verification environment.

## Hosting for multiple learners

The included Compose binding is localhost-only. For a public service, put the app behind a TLS reverse proxy with authentication, request-rate limits, concurrency limits, and provider spending controls. Retain Streamlit's CORS and XSRF defaults. Expose only Streamlit, never the query engines. Use dedicated synthetic-fixture Prometheus; do not point this public query playground at production telemetry.

Use a durable disk for `.runtime` and back up the SQLite database consistently. A single Streamlit instance with WAL SQLite supports a small class. Multiple replicas need a shared transactional database and a separate identity/session design; they must not each maintain their own independent progress file.

For OIDC, install Streamlit's authentication dependency (`pip install Authlib`) and set `REQUIRE_LOGIN=true`. Configure your identity provider's application and put its settings in the ignored `.streamlit/secrets.toml`:

```toml
[auth]
redirect_uri = "https://your-academy.example/oauth2callback"
cookie_secret = "REPLACE_WITH_A_LONG_RANDOM_SERVER_SECRET"
client_id = "YOUR_PROVIDER_APPLICATION_ID"
client_secret = "YOUR_PROVIDER_CLIENT_SECRET"
server_metadata_url = "https://YOUR_PROVIDER/.well-known/openid-configuration"
```

Mount that file read-only into `/app/.streamlit/secrets.toml` for Docker; do not bake it into the image. The app derives learner identity from verified issuer and subject claims. An unauthenticated visitor is stopped before lesson access when login is required. The actual provider callback and cookie configuration require a deployment-specific integration test.

Streamlit Community Cloud can run the Python interface using `requirements.txt`. Its ephemeral filesystem is unsuitable for durable learner progress without an external state store, and the real Prometheus fixture service must be provisioned separately. The repository alone does not provision a hosted URL or a managed database.

## Troubleshooting

- **Engine offline:** run bootstrap; inspect the fixture log. Check that port 9098 is available. A custom endpoint must serve the same generated data, at the fixed fixture timestamps, for grading to be meaningful.
- **Empty results:** select a fixture scenario. The demonstration data is historical; querying the real current time is expected to be empty.
- **Model unavailable:** check the base URL, model name, provider JSON support, and quota. The UI deliberately shows retrieved material when inference fails.
- **Progress missing:** resume with the saved recovery code on the same server, or verify the configured persistent volume and OIDC issuer. Local recovery codes are bearer secrets.
- **SQL rejected:** only `SELECT` over `samples`, `snapshot`, and derived CTEs with an explicit function allowlist is supported. This is a teaching sandbox, not a general database client.
