# Security policy

## Current scope

Recon AI is a local development boilerplate for a reconnaissance-only platform. Valid requests return `not_executed`. The current workflow performs no scanning, DNS lookups, outbound requests to submitted targets, or LLM calls. Tool entries contain metadata only, and agents have no arbitrary shell access.

The optional LLM client is separate from the workflow. Explicitly configuring and invoking it would send the supplied prompt to the configured provider.

## Authorization and tool execution

All reconnaissance tools are disabled. Passive intelligence collection is planned first and must respect authorization and target scope before integration.

Nmap is classified as an active tool. Future execution requires explicit authorization and a separately approved target scope. The current policy denies execution even when those values are supplied. Submitting a domain does not establish permission to investigate it.

## Development limitations

- Authentication, rate limiting, and production deployment controls are not implemented. Keep development servers bound to loopback and do not expose this scaffold as a public service.
- CORS allows specific local frontend origins by default. CORS is a browser control, not authentication or protection against direct API requests.
- Target validation rejects malformed inputs, credentials, unsupported schemes, localhost, and IP literals. It checks syntax only; it does not prove ownership or prevent SSRF in future network integrations.
- Before adding network collectors, enforce approved scope, validate resolved addresses, and handle redirects and DNS rebinding safely.
- Keep credentials in backend environment configuration. Never commit secrets or place them in `VITE_*` variables, which are included in browser assets. Remove sensitive data from logs and reports.

## Reporting a vulnerability

For repositories hosted on GitHub, use **Security → Report a vulnerability** if private vulnerability reporting is enabled. Otherwise, contact the repository maintainer privately through a contact method they have published. A dedicated security contact and response timeline have not yet been established.

Do not put exploitable details, credentials, or sensitive target data in public issues. Include the affected revision, relevant environment, minimal reproduction using local or explicitly authorized targets, expected and actual behavior, and potential impact. Redact secrets and personal data.

Maintainers should acknowledge and assess reports privately and coordinate fixes and disclosure with the reporter. No response-time guarantee is currently offered.

## Maintenance

This pre-release scaffold has no defined supported-release window. Use the latest project revision and review dependency security updates. Existing tests cover validation, policy denial, and the absence of external execution in the placeholder request flow; they are not a comprehensive security audit.
