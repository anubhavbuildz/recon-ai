# Contributing

Read the [README](README.md), [architecture](docs/architecture.md),
[code of conduct](CODE_OF_CONDUCT.md), and [security policy](security.md) first.
This project is in development; discuss changes to public contracts, dependencies,
AWS permissions, and deployment behavior in an issue or pull request.

## Local setup

Use Python 3.12+ and a Node.js version supported by Vite 7. From the repository root:

```sh
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -e './backend[dev]'
cd frontend
npm ci
```

Copy each project's `.env.example` only if its local `.env` does not already exist.
Use your own credentials and a random JWT secret. Never include secrets, session
records, Terraform state, private model responses or real account snapshots in
commits. Prefer the labeled synthetic fixture for local development.

## Making changes

1. Create a focused branch and describe the behavior you intend to change.
2. Preserve existing uncommitted work and keep unrelated changes out of your PR.
3. Implement the change and update relevant documentation and example configuration.
4. Add or adjust meaningful tests for changed behavior, error handling, and contracts.
5. Run the applicable checks below and record results and remaining limitations.

Keep model provider configuration inside the base client, role instructions in
`backend/app/service/llm/role/role.md`, and AWS reads behind the scoped `call_s3`
tool. Do not expand a tool's permissions or accept arbitrary resource paths without
reviewing the authorization boundary. Preserve explicit synthetic-data labels.

## Checks

From `backend/` with the virtual environment active:

```sh
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
python -m pytest --cov=app --cov-branch --cov-report=term-missing --cov-report=html:coverage/html --cov-report=json:coverage/coverage.json
```

From `frontend/`:

```sh
npm run lint
npm test
npm run test:coverage
npm run build
```

For Terraform changes, from the relevant project directory:

```sh
terraform fmt -check
terraform init -backend=false
terraform validate
```

These Terraform commands validate configuration; they do not establish deployment
success. `plan` can read live AWS resources and `apply` provisions them. Live
model/AWS tests can incur charges and send document contents outside the app;
run them only against an approved account/provider. No AWS or model credentials
are required for the existing mocked test suites. CI enforcement is not assumed.

See [test cases](docs/test_case.md) for scope and manual E2E procedures. Coverage
has no enforced threshold and excludes React screens. Do not present utility
coverage or a passing build as proof of browser behavior.

## Pull requests and reports

Explain the concrete problem, resulting behavior, relevant API/schema changes,
validation performed, and material limitations. Include screenshots for visual
changes when available. For infrastructure changes include the relevant plan
summary with sensitive values removed; do not deploy just to submit a PR.

Report ordinary bugs with reproduction steps, expected/actual behavior, versions,
and redacted logs. Use the [security reporting process](security.md#reporting-a-vulnerability)
for vulnerabilities instead of public issues. Avoid submitting tokens, credentials,
personal information, account identifiers, or private infrastructure data.
