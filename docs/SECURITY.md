# Security boundaries and limitations

The app processes untrusted learner questions and queries. These controls are enforced outside model prompts.

| Boundary | Enforcement | Remaining limitation |
|---|---|---|
| Learner identity | Random 256-bit recovery secret; only its SHA-256 stored; optional verified OIDC subject | A recovery code grants access to its profile. Local mode is intended for a trusted workstation. |
| Progress | Profile-scoped queries, prerequisite checks, server-selected attempts, real engine grading, transactional unique badge awards | Public source includes answer keys. This is learning practice, not proctored certification. |
| SQL | SQLGlot AST allowlist; one SELECT; only fixture tables/CTEs; no file/table functions, DDL/DML, attach/copy/extensions, or recursive CTEs | Parser restrictions are defense in depth, not an OS security boundary. Use the container worker for hosted use. |
| SQL execution | Fresh process, clean environment without API keys, DuckDB external access disabled and configuration locked, 128 MB memory, one thread, 6-second process timeout, 200 rows | Native subprocesses share the host OS. Compose adds non-root/read-only/internal-network isolation and resource limits. |
| PromQL | 3,000-character input, bounded duration literals, 3-second engine timeout, 100,000 samples, four concurrent engine queries, 100-series response cap | Operator-supplied external engines must use equivalent limits. Only fixture data belongs in this playground. |
| Agent authority | Structured plan, fixed graph with recursion limit, at most one allowlisted read-only query tool | Prompt-injection classification alone is not a security guarantee. The model cannot write grades because no such tool exists. |
| Retrieved content | Fixed source inventory, source IDs, explicit evidence/instruction separation, answer citation validation | A valid citation ID does not establish entailment. Answer-quality evaluation and human review remain necessary. |
| Output | No model text passed to unsafe HTML; Markdown images/links and HTML tags stripped; queries shown as code | Natural-language errors remain possible. Sources and execution evidence are visible for review. |
| Network | Fixed administrator endpoints, no learner-selected URLs, model HTTPS requirement, no redirects in inference/query calls | The app can call its configured provider. Host-level egress policy is needed for stronger outbound restrictions. |
| Secrets and privacy | `.env`, OIDC secrets, runtime DB, traces, and model weights ignored; SQL child gets a minimal environment | Configured providers receive the question, relevant history, retrieved passages, and synthetic query results. |

Conversation memory retains at most 20 messages per learner. Learners can turn off remembering a new conversation or clear their stored history. SQLite is not encrypted at rest; use encrypted disks and a suitable backup policy for hosted use. LangSmith tracing is opt-in and can send question/answer content to that service. Do not enter production secrets into the tutor.

The UI's three-second question pacing is a convenience guard, not a distributed rate limiter. Public hosting needs authentication, a reverse-proxy rate limiter, bounded concurrent sessions, and provider budgets. OIDC, real provider behavior, adversarial-model robustness, and deployment policy require verification in the actual hosting environment.

The automated tests include file/network SQL attempts, multi-statement and write rejection, oversized inputs, cross-profile attempts, locked-level bypass attempts, idempotent awards, fabricated citations, and provider timeouts. They are useful regression evidence, not a claim that every attack is prevented.

To report an issue, describe the affected component and a minimal synthetic reproduction. Do not publish credentials, learner recovery codes, or real learner data in an issue.
