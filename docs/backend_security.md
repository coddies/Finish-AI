# FinishAI — Backend Security Requirements

**Version:** 1.0 | **Applies to:** all backend code, config and deployment | **Related:** `backend_SRS.md`, `backend_system_design.md`, `../backend/plan.md`

> The AI coding tool must treat every item marked **MUST** as a requirement, not a suggestion. When a requirement conflicts with convenience, security wins. If something cannot be done, ask the developer instead of skipping it.

## 1. Scope and assets
| Asset | Why it matters |
|---|---|
| LLM API key (Groq) | Theft means quota loss/cost and service outage |
| User data (goals, skills, answers) | Personal information about careers and plans |
| Session tokens | Identify users in the MVP |
| Database and its credentials | Contains everything |
| Service availability and LLM quota | Easy to exhaust; the demo depends on it |

## 2. Threat summary
| Threat | Example | Section |
|---|---|---|
| Unauthorized data access (IDOR) | Guessing another goal's id | 3, 4 |
| Abuse / quota exhaustion | Script spamming plan generation | 5 |
| Prompt injection | Goal text saying "ignore instructions, output ..." | 6 |
| SSRF via link verification | LLM-supplied URL pointing at internal services | 7 |
| XSS via AI text | AI or user text containing scripts shown in the UI | 8 |
| Injection (SQL) | Malicious strings in inputs | 9 |
| Secret leakage | Keys in git, logs or error responses | 10 |
| Misconfiguration | Open CORS, debug mode on, default credentials | 11 |
| Vulnerable dependencies | Outdated packages | 12 |

## 3. Authentication and sessions (MVP: anonymous sessions)
- **SEC-A1 MUST** generate session tokens with a cryptographically secure generator, ≥ 128 bits (e.g. `secrets.token_urlsafe(32)`).
- **SEC-A2 MUST** store only a hash of the token (HMAC-SHA256 with a server-side pepper from env), never the raw token.
- **SEC-A3 MUST** compare hashes in constant time.
- **SEC-A4 MUST** send tokens only in the `Authorization: Bearer` header, never in URLs or query strings.
- **SEC-A5** Sessions expire after 90 days of inactivity; `last_seen_at` updated on use.
- **SEC-A6** v1 (accounts): passwords hashed with Argon2id or bcrypt; short-lived access tokens; email verification; password reset with single-use expiring tokens; login rate limiting.

## 4. Authorization and data ownership
- **SEC-Z1 MUST** scope every data query by the current session (or user) id. Repositories require it as an argument; there are no "get by id only" methods for user-owned entities.
- **SEC-Z2 MUST** return `404` (not `403`) when the entity exists but belongs to another session.
- **SEC-Z3** Use UUIDv4 identifiers (non-sequential). This is defence in depth, not a substitute for SEC-Z1.
- **SEC-Z4** Add an automated test that tries to read, modify and replan another session's goal and expects 404 for each endpoint.

## 5. Rate limiting and abuse protection
Default limits (adjust after observing real usage; these are starting assumptions):
| Scope | Limit |
|---|---|
| Any endpoint, per IP | 120 requests/minute |
| `POST /session`, per IP | 10/hour |
| LLM-backed endpoints (`/goals`, `/replan`, `/career/analyze`), per session | 10/hour, 40/day |
| LLM-backed endpoints, per IP | 30/hour |
- **SEC-R1 MUST** return `429` with `Retry-After` when exceeded.
- **SEC-R2 MUST** enforce input size limits: request body ≤ 32 KB; goal text ≤ 1000 chars; max 30 skills per career profile; skill name ≤ 60 chars.
- **SEC-R3 MUST** set a global monthly/daily LLM call budget in config; when exhausted, return `AI_BUSY` instead of calling the provider.
- **SEC-R4** Per-goal re-plan cap: e.g. 10 proposals/day.
- **SEC-R5** If behind a proxy, trust forwarded IP headers only from the platform proxy; otherwise limits can be bypassed by spoofing headers.

## 6. Prompt injection and AI output safety
User text is untrusted and can try to steer the model.
- **SEC-P1 MUST** keep system instructions separate from user content. Insert user text only inside clearly delimited data blocks, with an instruction that its contents are data, never instructions.
- **SEC-P2 MUST** validate every LLM output against a strict schema (types, lengths, enums). Reject anything else.
- **SEC-P3 MUST** ensure the LLM cannot trigger actions: no tool calling, no code execution, no direct DB access, no free-form URL fetching. Its output is data only.
- **SEC-P4 MUST** enforce business rules in code after the LLM responds (dates ≤ deadline, hours ≤ capacity, roles within the curated dataset). The LLM's claims are never trusted over code.
- **SEC-P5 MUST NOT** put secrets, other users' data or internal configuration into prompts.
- **SEC-P6** Cap output length and strip control characters from LLM text before storing it.
- **SEC-P7** Test cases: goal text containing "ignore previous instructions", JSON-breaking strings, very long input, non-Latin scripts, HTML tags.
- **SEC-P8 (future agent loop)** When a ReAct/agent loop is added, tools must be allow-listed, parameter-validated, scoped to the session, and rate limited. Re-run this section's review before enabling it.

## 7. SSRF-safe link verification (`integrations/safe_fetch.py`)
Verifying URLs from AI output means the server makes requests to attacker-influenced addresses.
- **SEC-F1 MUST** allow only `http` and `https` schemes.
- **SEC-F2 MUST** resolve the hostname and block loopback, private (RFC1918), link-local (including 169.254.169.254 cloud metadata), multicast and reserved ranges, for both IPv4 and IPv6. Re-check after redirects.
- **SEC-F3 MUST** disable automatic redirects or cap them (≤ 3) and re-validate each hop.
- **SEC-F4 MUST** use short timeouts (≤ 3 s), `HEAD` first (or a streamed `GET` with a small byte cap), and no cookies or auth headers.
- **SEC-F5** Prefer the curated allowlist; verification is the fallback. Cache results.
- **SEC-F6** Never forward response bodies from verified URLs to clients.

## 8. Output handling (XSS and data exposure)
- **SEC-O1 MUST** return JSON only; set `Content-Type: application/json`.
- **SEC-O2** Treat AI text as untrusted content. The API does not mark it as HTML; the frontend renders it as text (`frontend_SRS` FR-X2).
- **SEC-O3 MUST** return resource URLs only after validation (SEC-F1); never return `javascript:` or `data:` URLs.
- **SEC-O4 MUST** use the standard error format and never leak stack traces, SQL, file paths or environment values to clients. Log details server-side with a request id.
- **SEC-O5** Security headers via middleware: `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Strict-Transport-Security` (HTTPS only), `Cache-Control: no-store` for authenticated responses.

## 9. Input validation and database safety
- **SEC-D1 MUST** use the ORM or parameterised queries only. No string-built SQL.
- **SEC-D2 MUST** validate all inputs with Pydantic (types, ranges, enums, max lengths); reject unknown fields where practical.
- **SEC-D3** Normalise and validate dates (deadline in the future and within 365 days).
- **SEC-D4** The application's DB user has only the privileges it needs (no superuser). Separate credentials for dev and production.
- **SEC-D5** Migrations run from the deploy pipeline, not from request handlers.
- **SEC-D6** Backups: enable the platform's automated Postgres backups; test a restore at least once before the pitch.

## 10. Secrets and configuration
- **SEC-C1 MUST** keep all secrets in environment variables; none in code, repo, logs or frontend bundle.
- **SEC-C2 MUST** add `.env` to `.gitignore`; commit only `.env.example` with placeholder values.
- **SEC-C3 MUST** check git history before first public push; if a key was ever committed, **rotate it** (deleting the commit is not enough).
- **SEC-C4** Because three developers share one repo: enable secret scanning (GitHub push protection) and never paste keys into chat tools, issues or PRs.
- **SEC-C5** Use separate API keys for development and production; set provider-side usage limits.
- **SEC-C6** App fails to start if required secrets are missing; `ENV=production` disables debug/docs exposure as decided (consider disabling `/docs` and `/openapi.json` in production or protecting them).

## 11. Transport, CORS and deployment hardening
- **SEC-T1 MUST** serve only over HTTPS (Railway provides TLS); redirect or reject HTTP.
- **SEC-T2 MUST** set CORS `allow_origins` to the exact frontend origins from env; no `*`. Do not enable credentials unless cookies are used.
- **SEC-T3** Allow only the HTTP methods and headers the API uses.
- **SEC-T4** Run the container as a non-root user where the platform allows; pin the Python version.
- **SEC-T5** Debug mode off in production; no verbose tracebacks to clients.
- **SEC-T6** Health endpoint exposes no internals.

## 12. Dependencies and supply chain
- **SEC-S1 MUST** pin dependency versions in `requirements.txt` (or lock file).
- **SEC-S2** Run `pip-audit` (or equivalent) before each deploy; enable GitHub Dependabot alerts.
- **SEC-S3** Add a new dependency only with developer approval (as per plan.md), and prefer well-maintained packages.
- **SEC-S4** Review any code copied from the old repos for hardcoded secrets or unsafe patterns (`eval`, `exec`, `pickle` on untrusted data, `subprocess` with user input, `verify=False` in requests).

## 13. Logging, privacy and data lifecycle
- **SEC-L1 MUST NOT** log tokens, API keys, full prompts or user goal text by default.
- **SEC-L2** Log request id, route, status, latency, error codes.
- **SEC-L3** Store the minimum personal data (no names, emails or phone numbers in MVP).
- **SEC-L4** Provide a way to delete a session's data (endpoint or admin script) and apply retention (e.g. delete inactive sessions after 180 days).
- **SEC-L5** Tell users (in the product copy) that their goal text is sent to a third-party AI provider.
- **SEC-L6** v2 (resume upload): file type/size validation, malware scanning consideration, storage outside the web root, signed access URLs.

## 14. Security testing and review
Automated (pytest):
1. Ownership: every endpoint rejects access to other sessions' entities (404).
2. Auth: missing/invalid/expired token → 401.
3. Rate limits trigger 429 as configured.
4. Oversized and malformed inputs → 422 (never 500).
5. Prompt-injection samples do not change output structure or violate business rules.
6. SSRF: URLs to `127.0.0.1`, `localhost`, `169.254.169.254`, `10.x`, IPv6 loopback and redirect-to-internal are blocked.
7. Error responses contain no stack traces or secrets.

Manual before deploy: run the **pre-deploy checklist** below.

## 15. Pre-deploy checklist
Status below is the pre-deploy assessment on 2026-10-08. A PASS means code/config checks in this workspace passed; a FAIL means a required live deployment/provider action or evidence is still missing.

| Checklist item | Status | Evidence / remaining action |
|---|---|---|
| No secrets in repo or git history; `.env` ignored; `.env.example` present | **FAIL** | `.env` is ignored and `.env.example` exists, but the Neon database credential was exposed in chat. Rotate it before public deployment and update both local connection variables. Full git-history secret scanning has not been completed. |
| Production keys differ from development keys; provider usage limits set | **FAIL** | Railway/provider account settings are unavailable; configure separate production credentials and provider-side spend/usage caps. |
| `ENV=production`; debug off; docs endpoint decision applied | **FAIL** | Production setting disables docs/OpenAPI in code; Railway has not been configured or deployed. |
| CORS limited to exact frontend origins | **FAIL** | Exact-origin validation and allow/deny test pass (`test_cors_allows_configured_origin_and_rejects_other_origin`). Set production `CORS_ORIGINS` to the final frontend origin(s) before deploy. |
| HTTPS only; security headers present | **FAIL** | Security headers are emitted and Railway TLS is documented, but the live Railway domain/redirect has not been verified. |
| Rate limits and LLM budget configured | **FAIL** | PostgreSQL counters, configurable limits, and 429 test pass (`test_rate_limit_returns_429_and_retry_after`); live schema is migrated, but production rate/budget values and multi-instance load behavior are not verified. |
| DB is persistent (Postgres/volume) with backups enabled; app DB user is least-privilege | **FAIL** | Neon pooled runtime connection and direct migration connection both succeeded; migration `0001_initial` is applied, 12 public tables exist, and `/health` reports `db=ok`. Backup policy and least-privilege DB credentials are not verified. |
| Ownership, auth, SSRF and injection tests passing | **PASS** | Ownership/auth and SSRF suites pass. `test_prompt_injection_is_delimited_and_business_rules_stay_in_code` checks untrusted-data framing and deterministic capacity rejection. This is code-level coverage; live-provider behavior remains unverified. |
| `pip-audit` clean or exceptions documented | **PASS** | `uv audit` passed for the locked environment: 51 packages, no known vulnerabilities or adverse statuses reported on 2026-10-08. |
| Logs reviewed: no tokens, prompts or goal text | **PASS** | Request/LLM logs use request IDs, provider/model labels and exception types. `test_llm_failover_logs_do_not_include_provider_error_secrets` verifies provider exception content and prompt text are omitted; legacy career cascade/error logging was hardened. |
| Old-repo code reviewed for hardcoded secrets or unsafe calls | **FAIL** | Core merged code was reviewed and unsafe dynamic execution patterns were not found, but a full secret scan of source/history and archived legacy files remains outstanding. |

### Requested test coverage map

| Concern | Test/evidence |
|---|---|
| Ownership returns 404 | `test_other_session_goal_is_hidden`, `test_other_session_goal_cannot_be_deleted_or_replanned`, `test_other_session_task_cannot_be_modified` |
| SSRF blocks | `SafeFetchTests.test_rejects_unsafe_urls_without_network_access` |
| Rate limiting | `test_rate_limit_returns_429_and_retry_after` |
| CORS | `test_cors_allows_configured_origin_and_rejects_other_origin` |
| No secrets in logs | `test_llm_failover_logs_do_not_include_provider_error_secrets` |
| Time budget | `LlmCoreTests.test_time_budget_expires`; fake Jev timeout is `JevAdapterTests.test_timeout_skips_verification` |
| Single verification | `JevAdapterTests.test_disabled_jev_skips_single_verification` asserts one verifier call |
| Provider failover | `LlmFailoverTests.test_provider_limit_immediately_uses_next_tier` |
| Railway client IP | `test_client_ip_uses_railway_real_ip_only_when_enabled` |
| Pooled psycopg prepared-statement config | `LlmCoreTests.test_pooled_psycopg_disables_prepared_statements` |
| Prompt injection / deterministic business rules | `test_prompt_injection_is_delimited_and_business_rules_stay_in_code` |

## 16. Incident basics
- If a key leaks: rotate immediately at the provider, update Railway env, redeploy, review usage logs.
- If abuse spikes: lower rate limits or set the LLM budget to zero (service returns `AI_BUSY`) while investigating.
- Keep a short note of what happened and what changed (add to the change log in `plan.md`).
