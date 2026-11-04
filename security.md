# Security policy

## MVP status and version-two security roadmap

Recon AI is an MVP built as part of the **Meta Global Hackathon**. It demonstrates
snapshot-backed cloud analysis and is not production-ready. Security
considerations remain incomplete; existing authentication, bounded S3 reads and
tool-call validation do not constitute a comprehensive security architecture.

The following controls are **not implemented** and are planned for version two:

- An LLM firewall for inspecting prompts, retrieved evidence, tool requests and
  outputs, including prompt-injection and data-exfiltration defenses.
- Confidence-based output with evidence-quality checks, calibrated uncertainty,
  and abstention or escalation when evidence is insufficient. Model-reported
  confidence alone will not be treated as a reliable security control.
- Sensitive-data detection and redaction before evidence reaches the model,
  plus output validation for unintended disclosure.
- Stronger identity and session controls: expiry, MFA, per-user authorization,
  tenant isolation and more secure token handling.
- Login/API rate limiting, concurrency limits and model cost controls.
- Structured audit trails, security monitoring, adversarial evaluations,
  dependency scanning and production deployment hardening.
- Human approval and explicit policy checks before any future write-capable
  cloud actions; the current application only reads evidence.

These are planned improvements, not guarantees or protections available in the
MVP. Prompt instructions alone do not prevent injection, hallucinations or
sensitive-data disclosure. Do not treat generated recommendations as validated
changes or deploy this MVP as a production security boundary.

## Implemented scope

Recon AI supports single-account JWT login and authenticated model chat using a configured S3 document or up to three newest JSON snapshots under a configured prefix. Chat reads the document and sends it, with the user's question, to the configured LLM provider. It does not modify AWS resources. The separate reconnaissance API returns `not_executed` and performs no scanning, DNS lookup, or outbound request to submitted targets. Agents have no shell execution capability.

## Authentication and sessions

- Only `POST /api/v1/auth/login` is public. All other routes, including health and API docs, require a Bearer token. Valid browser CORS preflights are exempt.
- Username and password are configured in the backend environment and compared using constant-time comparisons. There are no default credentials, registration, or password reset endpoints.
- PyJWT signs and verifies HS256 tokens using `JWT_SECRET`, which must be at least 32 bytes. Use a randomly generated secret. Verification pins the algorithm, requires subject/session ID/issue time/issuer/audience claims, and validates issuer and audience.
- Tokens have no automatic expiry. The browser stores the username and token in local storage until sign-out. Same-origin JavaScript, including injected scripts, can access that token. Use HTTPS outside loopback and prevent XSS; a stolen token can remain usable until revoked.
- SQLite stores token hashes and credential fingerprints. The active record must match the current account. Sign-out deletes the record; changing credentials or the JWT secret invalidates existing sessions. Logout applies to the current session, not all devices.
- Browser entries remain after validation failures or network outages. If sign-out cannot reach the backend, the UI keeps the session and reports an error for retry. User/browser storage clearing can also remove the local entry without revoking the server session.
- `backend/.data/sessions.sqlite3` contains sensitive session/account metadata. Restrict access to the file and backups. Preserve it across restarts for continuity. The configured password remains a backend environment secret, not a user password database.

## S3 and model boundaries

The only enabled execution tool is `service/tools/call_s3.py`. It accepts no arguments and reads the bucket/key fixed by backend settings, or JSON files under the configured snapshot prefix. Prefix mode follows paginated listings recursively and reads up to three newest JSON files by S3 LastModified with a combined context size limit. The files may all be from the same day; S3_HISTORY_DAYS no longer controls selection. It requires scoped ListBucket permission alongside GetObject. AWS authorization comes from the SDK credential chain and IAM/bucket policies. Grant only the permissions required for the configured object; the separate bucket helper also performs a bucket access check. Never grant write access solely for this feature.

The S3 reader bounds content size using `S3_MAX_BYTES`, rejects empty or invalid UTF-8 documents, and closes response streams. It performs no writes or bucket creation. The workflow validates one known tool request with empty arguments, returns a matching LangChain `ToolMessage`, and rejects further tool requests during the final model turn. There are at most two model turns per chat request.

The configured document and user question leave the application for the model provider. Review the document for credentials or confidential information and choose an appropriate provider before enabling chat. Model endpoints are server configuration, not user-supplied URLs. Prompts identify document content as untrusted evidence, but prompts do not guarantee resistance to injection or factual errors. A CloudFormation document does not establish current resource state, utilization, or costs. Review generated recommendations before acting.

## Reconnaissance authorization

Recon tool registry entries are metadata. `policy.py` denies their execution, including when authorization and scope values are supplied. Nmap is marked active and would require explicit permission and separately approved scope before future enablement. This policy does not govern the explicitly enabled S3 read tool. Submitting a target does not establish authorization to investigate it.

Target validation is syntactic. Before adding collectors, enforce approved scope, resolved-address restrictions, safe redirects, and defenses against DNS rebinding. No such future network collector should rely on domain syntax alone as an SSRF defense.

## Configuration, logs, and deployment

Keep `.env`, AWS credentials, JWT secrets, and the session database out of source control. Never place secrets in frontend `VITE_*` variables. CORS restricts browser origins but is neither authentication nor protection against direct API calls.

Workflow, model, and tool stage logs omit questions, document contents, tokens, passwords, and raw provider errors. They include counts, timings, stage names, and error types. Unexpected API exceptions are logged with tracebacks; restrict access to logs and review changes that could expose sensitive context. Enabling third-party tracing or verbose SDK logs can introduce additional data exposure and is not part of the default application logging configuration.

This remains a local development application. Login rate limiting, account lockouts, MFA, automatic session expiry, per-user authorization, production hosting controls, and a session cleanup policy are not implemented. Model timeouts and document size limits do not provide global request/concurrency limits. Keep development servers on loopback. Production exposure requires additional operational controls and review.

## Reporting a vulnerability

On GitHub, use **Security → Report a vulnerability** if private reporting is enabled. Otherwise contact the maintainer privately through a published contact method. A dedicated security contact and response timeline have not been established.

Do not include exploit details, credentials, sensitive S3 contents, or personal data in public issues. Provide the affected revision, environment, a minimal reproduction using local or authorized resources, expected/actual behavior, and potential impact. Maintainers should assess reports privately and coordinate fixes and disclosure; no response-time guarantee is offered.

## Maintenance and verification

This pre-release project has no supported-release window. Review dependency updates and use the current revision. Automated tests cover JWT/session behavior, route protection, tool-call validation, bounded S3 reads, cleanup, reconnaissance validation, and policy denial. Mocked tests and lint checks are not a comprehensive security audit or proof of live model/AWS compatibility.
