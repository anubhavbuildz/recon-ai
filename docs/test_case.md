# Feature-wise test cases

Status recorded November 3, 2026. A passing automated test means the stated local
or mocked behavior was exercised; it does not imply AWS deployment or browser E2E
success. See [coverage](coverage-report.md) for the latest measured results.

## How testing was conducted

- Backend: pytest and FastAPI `TestClient`, temporary SQLite session databases,
  monkeypatched environment configuration, mock boto3 clients/streams, and async
  mock model responses. Tests include success, validation, authorization and failure paths.
- Frontend: Node's built-in test runner with mocked `fetch` and local storage;
  checks cover JavaScript API/auth/response contracts, not mounted React components.
- Coverage: pytest-cov measures backend statements and branches; c8 merges Node
  test-process coverage for `src/**/*.js`. JSX, CSS, images, collector code and
  Terraform are outside those coverage denominators.
- Infrastructure: Terraform formatting and static validation were performed for
  collector and demo configurations. No `apply` is part of the test suite.
- Live smoke checks: S3 bucket/object access, synthetic fixture upload/read-back,
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
| U05 | Snapshot history | Paginate dates, choose latest timestamped JSON, report missing dates, reject empty history/oversized context/invalid JSON | Automated: `backend/tests/test_snapshot_history.py` |
| U06 | Tool requests | Reject unknown names, malformed arguments, missing first tool request and repeated final tool request | Automated: `backend/tests/test_chat.py` |
| U07 | Resource contracts | Validate resource identity, structured references and savings assumptions | Automated: `frontend/tests/resources.test.js` |
| U08 | Response adapter | Convert message/source into renderable answer; reject invalid source format | Automated: `frontend/tests/resources.test.js` |
| U09 | Session persistence | Save username/token, never password; retain on errors; remove on explicit sign-out, including revoked sessions | Automated: `frontend/tests/auth.test.js` |
| U10 | Role prompt | Load packaged Markdown role and reject an empty prompt | Loader exercised by workflow tests; empty/missing-file behavior not directly tested |
| U11 | Base LLM client | Timeout/API-error wrapping, tool binding and client cleanup | Largely mocked; direct unit coverage remains incomplete |
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
| I08 | History exchange | Prefix mode calls history reader and returns all source URIs | Automated: `test_history_tool_and_multiple_sources` |
| I09 | Frontend API | Send JWT and question-only contract; surface authorization/upstream failures | Automated: frontend resource tests with mocked HTTP |
| I10 | Recon boundary | Invoke placeholder agent while model/network/process access is blocked | Automated: `test_recon.py` |
| I11 | Real provider smoke | Read configured S3 object via model tool and return nonempty answer with matching source | Manually passed during development; not re-run by ordinary tests |
| I12 | Real history | Compare real collector files across three dates | Pending; automated selection tests use fake objects |

## End-to-end acceptance cases

No browser automation framework or automated browser E2E suite is configured.
The following are manual acceptance procedures, not claims of completed testing.

| ID | Scenario | Procedure | Expected result / status |
| --- | --- | --- | --- |
| E01 | Browser login | Start services, set credentials, submit login, refresh and reopen browser | Workspace opens and saved session persists. Manual verification pending |
| E02 | Browser sign-out | Sign out in one tab; check another tab; retry old JWT against API | Local session disappears across tabs and server token fails. Browser verification pending; API/storage portions tested separately |
| E03 | Synthetic chat | Configure labeled fixture, log in, ask about underutilized EC2 and unattached volumes | Render answer/source; acknowledge synthetic data; no invented exact savings. Model smoke passed separately; browser flow pending |
| E04 | Error recovery | Interrupt backend/network or force invalid model configuration while submitting | Show error, restore question, retain login and allow retry. Automated API mocks only; browser verification pending |
| E05 | Real collection | Apply collector, invoke once, inspect payload/logs and S3, wait for next five-minute run | Successful handler and new timestamped snapshot. Deployment verification pending |
| E06 | Historical comparisons | Provide dated files for today/yesterday/day before in UTC, enable prefix mode, ask what changed | Latest file/date, all source URIs, explicit missing dates and rolling-metric caveat. Real E2E pending |
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

Priority gaps: direct base-client tests, collector unit tests, real history
integration, React component tests and automated browser E2E. Also add assertions
for every advertised API error mapping as those branches evolve.
