# Current features and limitations

Recon AI is an MVP built as part of the Meta Global Hackathon. This version
focuses on read-only analysis of AWS snapshots through a local chat interface.
It is not a production-ready cloud management or security platform.

## What this version supports

- Environment-configured login with signed JWTs and server-side session revocation.
- Scheduled collection of EC2/EBS metadata and rolling 14-day EC2 CPU statistics.
- S3-backed chat using one configured object or up to three newest JSON files
  under a configured prefix.
- Markdown answers, tables and source URIs in a modular React frontend.
- Unit, component-rendering and integration tests, plus an opt-in live S3/model
  integration check.

## Limitations

| Area | Current limitation | Practical implication |
| --- | --- | --- |
| Environment-based authentication | A shared username, password and JWT signing secret are configured in the backend environment. No user registration, password reset, MFA, per-user roles or tenant isolation. | Access is suitable for a controlled demo, not a multi-user production service. |
| Sessions | Tokens have no automatic expiry and are stored in browser local storage. Session revocation records are stored in local SQLite. | Token theft and host/database access require additional protections; sign-out revokes only the current session. |
| Database integration | No application database integration for user accounts, chat history, cloud inventory or analysis results. Local SQLite is used only for session records. | Chat history is held in frontend memory and does not survive reloads; durable application data and database-backed user management are not available. |
| Region coverage | Each collector deployment targets one AWS account and one configured region. | This version does not automatically discover or aggregate resources across regions or accounts. |
| Environment-based bucket selection | The backend bucket, region, prefix and optional object key are fixed through `S3_BUCKET_NAME`, `S3_REGION`, `S3_SNAPSHOT_PREFIX` and `S3_OBJECT_KEY`. | There is no UI bucket picker or per-user data-source selection. Configuration changes require a backend restart. |
| Snapshot selection | Prefix mode selects up to three newest JSON files by S3 modification time, including nested folders. The files may all be from one day. | This is not a full historical query engine; older evidence is excluded and fewer than three files are used when fewer exist. |
| Evidence size and format | Prefix snapshots must be JSON objects, and combined context must fit `S3_MAX_BYTES`. | Oversized, empty, invalid UTF-8 or malformed evidence fails rather than being silently truncated. |
| AWS service coverage | The collector currently covers EC2 and EBS, with EC2 CPU metrics. RDS, S3 inventory, billing, memory metrics and resource pricing are not collected. | The model cannot substantiate findings about data that was not collected, including exact cost savings. |
| Snapshot freshness | Collection is scheduled every five minutes, and chat reads stored evidence rather than live AWS resource state. | Resources can change after a snapshot. CPU values are rolling 14-day aggregates, not separate daily or five-minute measurements. |
| Conversation context | The built-in backend analyzes each question independently. | Previous questions, answers and attached resource context are not sent through the default chat API. |
| Optional integrations | Inventory browsing, resource details and AWS account connection depend on external APIs that the built-in backend does not implement. | Default S3 chat works without them; live explorer functionality is not available out of the box. The regional resource map has been removed. |
| Model reliability | Answers depend on the configured provider and tool-calling support. No LLM firewall, calibrated confidence-based output or dedicated pre-model sensitive-data redaction pipeline is implemented. | Prompt instructions do not guarantee factual accuracy, injection resistance or prevention of sensitive-data disclosure. |
| Cloud actions | The enabled tool reads S3 evidence; it cannot change AWS resources. The reconnaissance endpoint is a placeholder and performs no scanning. | Recommendations require independent review and manual implementation. |
| Hosting and operations | Terraform deploys the collector infrastructure, not the frontend/backend. Production hosting controls, login rate limiting, global concurrency limits and centralized security monitoring are not implemented. | Local application startup and additional production hardening are required. |
| Test scope | Automated coverage excludes browser E2E, collector code, Terraform and JSX coverage percentages. JSX rendering is tested separately. | Passing unit/integration tests does not establish complete UI behavior, collector correctness or production readiness. |

## Version-two direction

Planned work includes an LLM firewall, confidence/evidence-based output checks,
sensitive-data controls, stronger identity and sessions, durable application data,
and broader cloud coverage. These are roadmap items, not features available in
this release. See [security considerations](../security.md) for the detailed
security gaps and planned controls.

For setup and verification, see [demo setup](demo.md), [test cases](test_case.md)
and [coverage](coverage.md).
