# Feature-wise test cases

Status recorded November 4, 2026. A passing automated test means the stated local
or mocked behavior was exercised; it does not imply AWS deployment or browser E2E
success. See [coverage](coverage-report.md) for the latest measured results.

## How testing was conducted

- Backend: pytest and FastAPI `TestClient`, temporary SQLite session databases,
  monkeypatched environment configuration, mock boto3 clients/streams, and async
  mock model responses. Tests include success, validation, authorization and failure paths.
- Frontend: Node's built-in test runner with mocked `fetch` and local storage;
  checks cover JavaScript API/auth/response contracts plus JSX components loaded
  through Vite and rendered with React server rendering. No browser is launched.
- Coverage: pytest-cov measures backend statements and branches; c8 measures
  `src/**/*.js` using the API/auth/resource utility test files. Component rendering
  tests run in `npm test` separately from c8 to avoid mixing Vite-transformed
  module coverage with native Node utility coverage. JSX, CSS, images, collector code and
  Terraform are outside those coverage denominators.
- Infrastructure: Terraform formatting and static validation were performed for
  collector and demo configurations. No `apply` is part of the test suite.
- Historical live smoke checks (not repeated against the recreated infrastructure):
  S3 bucket/object access, synthetic fixture upload/read-back,
  and real model → S3 tool → final answer were exercised manually during development.
  A real authenticated chat-route request was also exercised using TestClient.
  These checks are not automated browser E2E tests or a guarantee of future provider availability.

## Unit and component cases

| ID | Feature | Case / expected behavior | Evidence and status |
| --- | --- | --- | --- |
| U01 | Recon validation | Accept/normalize valid domains and HTTPS URLs; reject malformed names, local/IP targets, credentials and extra payload fields | Automated: `backend/tests/test_recon.py` via API validation |
| U02 | JWT verification | Require expected claims and signed HS256 token; reject tampering and unsigned tokens | Automated: `backend/tests/test_auth.py` |
| U03 | S3 bucket helper | Require valid configured/approved bucket and file key; never create/upload; propagate AWS errors | Automated: `backend/tests/test_aws.py` |
| U04 | Text evidence | Bound declared and actual bytes, reject empty/invalid UTF-8, close stream | Automated: `backend/tests/test_chat.py` |
| U05 | Latest-three snapshots | Paginate the configured prefix recursively; select up to three JSON files by LastModified, newest first; deterministic key tie-break; accept 1–2 files; reject empty prefix/oversized context/invalid JSON or UTF-8; close streams | Automated: `backend/tests/test_snapshot_history.py` |
| U06 | Tool requests | Reject unknown names, malformed arguments, missing first tool request and repeated final tool request | Automated: `backend/tests/test_chat.py` |
| U07 | Resource contracts | Validate resource identity, structured references and savings assumptions | Automated: `frontend/tests/resources.test.js` |
| U08 | Response adapter | Convert message/source into renderable answer; reject invalid source format | Automated: `frontend/tests/resources.test.js` |
| U09 | Session persistence | Save username/token, never password; retain on errors; remove on explicit sign-out, including revoked sessions | Automated: `frontend/tests/auth.test.js` |
| U10 | Role prompt | Load packaged Markdown role and reject an empty prompt | Loader exercised by workflow tests; empty/missing-file behavior not directly tested |
| U11 | Base LLM client | Timeout/API-error wrapping, tool binding and client cleanup | Largely mocked; direct unit coverage remains incomplete |
| U13 | Markdown rendering | Render GFM tables, lists and code; reject unsafe links/raw scripts | Automated: `frontend/tests/components.test.js` |
| U14 | Chat view states | Escape user text, expose loading status, preserve retry input and disable pending submission | Automated: `frontend/tests/components.test.js` |
| U12 | Collector | Pagination, CPU statistics, null metrics, JSON shape and S3 writes | No dedicated automated collector suite; fixture matches its fields, not proof of collector correctness |

## Integration cases

| ID | Feature | Steps and expected result | Evidence and status |
| --- | --- | --- | --- |
| I01 | Login lifecycle | Login, verify identity, create fresh app, verify persistent token, logout, reject revoked token | Automated: `test_auth.py`; isolated DB |
| I02 | Route protection | Missing/forged token cannot access health, docs, chat or recon; login remains available | Automated: `test_auth.py`, `test_health.py` |
| I03 | Credential rotation | Change account password or JWT secret; old token fails, new login works | Automated: `test_auth.py` |
| I04 | CORS/error envelopes | Allow configured preflights, deny untrusted origins, sanitize unhandled errors | Automated: health/recon tests |
| I05 | Chat API contract | Authenticated question reaches workflow; valid answer/source/sources returned; blank question rejected | Automated: `test_authenticated_chat_route`, workflow mocked |
| I06 | Model timeout | Mock APITimeoutError cause; return clear HTTP 504 | Automated: `test_chat_timeout_returns_clear_504` |
| I07 | Model/tool exchange | HumanMessage → AIMessage tool call → local tool → matching ToolMessage → final answer | Automated: `test_chat.py`, S3/model mocked |
| I08 | Latest-three exchange | Prefix mode calls the snapshot reader and returns selected source URIs | Automated: `test_latest_three_tool_and_multiple_sources` |
| I09 | Frontend API | Send JWT and question-only contract; surface authorization/upstream failures | Automated: frontend resource tests with mocked HTTP |
| I10 | Recon boundary | Invoke placeholder agent while model/network/process access is blocked | Automated: `test_recon.py` |
| I11 | Real provider integration | Authenticated in-process chat API invokes the real model and S3 tool; returns a nonempty answer and scoped source URIs | Passed November 4, 2026: HTTP 200, 687-character answer, Markdown table present, two sources |
| I12 | Real prefix access | Read up to three newest JSON snapshots under the configured prefix | Passed November 4, 2026: two eligible files available and read; newest-first modification timestamps verified |
| I13 | Answer rendering | Adapt backend message/source/sources, render a GFM table and all three sources; unverified references stay non-actionable | Automated: `frontend/tests/components.test.js` |

## End-to-end acceptance cases

E2E testing is excluded from this update and was not run.
No browser automation framework or automated browser E2E suite is configured.
The following are manual acceptance procedures, not claims of completed testing.

| ID | Scenario | Procedure | Expected result / status |
| --- | --- | --- | --- |
| E01 | Browser login | Start services, set credentials, submit login, refresh and reopen browser | Workspace opens and saved session persists. Manual verification pending |
| E02 | Browser sign-out | Sign out in one tab; check another tab; retry old JWT against API | Local session disappears across tabs and server token fails. Browser verification pending; API/storage portions tested separately |
| E03 | Synthetic chat | Configure labeled fixture, log in, ask about underutilized EC2 and unattached volumes | Render answer/source; acknowledge synthetic data; no invented exact savings. Model smoke passed separately; browser flow pending |
| E04 | Error recovery | Interrupt backend/network or force invalid model configuration while submitting | Show error, restore question, retain login and allow retry. Automated API mocks only; browser verification pending |
| E05 | Real collection | Apply collector, invoke once, inspect payload/logs and S3, wait for next five-minute run | Successful handler and new timestamped snapshot. Deployment verification pending |
| E06 | Historical comparisons | Provide dated files for today/yesterday/day before in UTC, enable prefix mode, ask what changed | Three newest JSON files by S3 modification time, all selected source URIs and rolling-metric caveat. Real E2E pending |
| E07 | Demo network | Apply EC2/RDS demo; inspect both bootstrap logs with SSM | TCP 3306 check succeeds; RDS not public. Pending; SQL authentication is a separate test |
| E08 | Responsive UI | Check login, sidebar, messages, theme and keyboard controls on desktop/mobile | Readable layout, accessible controls and no obscured composer. Manual verification pending |
| E09 | Cleanup | Destroy disposable demo and collector with reviewed retained-data handling | Resources removed intentionally; snapshot bucket retention respected. Pending |

## Execution and evidence

Use commands in [CONTRIBUTING](../CONTRIBUTING.md#checks) to run tests and lint.
Coverage commands and local report links are in [coverage-report.md](coverage-report.md).
Use [AWS setup](aws.md) for live deployment checks; they require an approved AWS
identity and may incur charges. Record test date, source revision, sanitized
configuration, test question, HTTP status, duration, and observed result for live
checks. Do not store secrets or private snapshot contents as test evidence.

Priority gaps: direct base-client tests, collector unit tests, live prefix
integration and mounted React interaction tests. Browser E2E remains deferred. Also add assertions
for every advertised API error mapping as those branches evolve.

## Latest local unit/integration run

Re-run completed November 4, 2026 at 11:58 IST, after the infrastructure was
reported as provisioned again. Infrastructure status is user-reported; this run
did not access AWS, invoke the model, or provision/change resources.

| Check | Result | Evidence |
| --- | --- | --- |
| Backend unit and integration suite | 103 passed, 0 failed | `python -m pytest tests -q`; 5.10 seconds |
| Frontend unit, rendering and contract integration suite | 16 passed, 0 failed | `npm test`; approximately 1.27 seconds |
| Backend Ruff lint | Passed | `python -m ruff check .` |
| Backend formatting | Passed | `python -m ruff format --check .`; 32 files already formatted |
| Frontend ESLint | Passed | `npm run lint` |
| Live AWS/S3/model integration | Not run | AWS clients, streams and model calls are mocked |
| Browser E2E | Not run | Excluded from scope |

Latest-change coverage includes three-newest JSON selection across paginated
prefix listings, nested folders, modification-time ordering and tie-breaks,
fewer-than-three files, empty results, byte limits, malformed JSON/UTF-8, stream
cleanup, workflow source propagation, and Markdown rendering of all three sources.
Frontend tests exercise the modular components for answers, conversations and
composer state. No regional resource map or demo inventory is part of the UI.

Frontend component tests use React server rendering; they do not verify focus,
clicks, keyboard interactions, or browser layout. Mocked API integration does not
verify credentials, bucket existence, collector scheduling or live model
availability. Backend tests emitted 13 upstream LangSmith deprecation warnings;
there were no test failures. Coverage was not remeasured during this rerun; the
linked coverage report records the earlier coverage measurement separately.

```sh
cd backend
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m pytest tests -q
```

```sh
cd frontend
npm run lint
npm test
npm run build
```

## Latest live integration run

November 4, 2026: live S3 and configured-model integration **passed** in 18.79
seconds after network access was enabled. The preceding local-unit run remains
103 backend and 16 frontend tests passed; this opt-in script is separate from
those counts and from coverage measurements.

| Check | Observed result |
| --- | --- |
| Real S3 prefix listing and reads | Passed; two eligible JSON snapshots available and read, within the configured byte limit |
| Snapshot selection | Modification timestamps in newest-first order; the fewer-than-three path exercised live |
| Unauthenticated chat | HTTP 401 |
| Login with configured backend credentials | HTTP 200; token retained only in process memory |
| Real model → S3 tool → final answer via in-process API | HTTP 200; nonempty 687-character answer, Markdown table detected, two source URIs within configured scope |
| Primary source | Matches first returned source |
| Logout and revocation | Logout HTTP 200; subsequent identity request with the same token HTTP 401 |
| Browser E2E | Not run |

Reproduce explicitly from `backend/`:

```sh
PYTHONPATH=. .venv/bin/python scripts/check_live_integration.py
```

This check reads real AWS data and sends the configured evidence to the configured
model provider. It uses FastAPI TestClient, not a running HTTP server or browser.
Sessions are stored in an isolated temporary database; the application's session
database is unchanged. It does not upload S3 objects, invoke the collector,
provision infrastructure, or modify AWS resources. Output contains only status
metadata, not tokens, credentials, snapshot text or model answer text.

Limitations: no browser rendering, public/network HTTP transport, collector
scheduling or deployment configuration was verified. Table detection is a basic
format check, not a semantic correctness review of the answer. Only two files
were available live; selection from more than three objects remains covered by
mocked unit tests. The initial sandboxed S3 attempt failed with
`EndpointConnectionError`; the network-enabled rerun passed.
