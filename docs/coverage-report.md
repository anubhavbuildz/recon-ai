# Test and coverage report

Run date: November 3, 2026 (Asia/Kolkata). Python 3.14.3; Node.js 24.10.0.

## Results

| Suite | Passed | Failed | Line coverage | Branch coverage |
| --- | ---: | ---: | ---: | ---: |
| Backend (`app/`) | 98 | 0 | 90.64% | 84.31% |
| Frontend JavaScript (`src/**/*.js`) | 11 | 0 | 84.61% | 81.89% |

Backend combined statement-and-branch coverage: **89.51%**.
Frontend function coverage: **88.88%**.

Backend: 426 of 470 executable lines and
86 of 102 branches covered. Frontend:
154 of 182 lines and
95 of 116 branches covered.
Do not combine percentages across tools: their counting rules and scope differ.

## How measurements were collected

pytest-cov executed the complete pytest suite with `--cov=app --cov-branch`.
Tests use temporary session databases, FastAPI TestClient, mocked boto3 streams
and asynchronous model responses. c8 executed Node tests, merged process coverage,
and included `src/**/*.js`; fetch and browser storage are mocked.

React JSX components, CSS, images, Terraform, and `cloud-assets/collector.py` are
outside these coverage scopes. No browser E2E runner is configured. This coverage
run did not call live AWS or model services. Separate live smoke tests from prior
development are described in [test cases](test_case.md). Coverage is not a
correctness/security audit, and no threshold is currently enforced.

## Local artifacts

Generated files are ignored by Git and exist after running the commands below:

- [Backend HTML](../backend/coverage/html/index.html)
- [Backend XML](../backend/coverage/coverage.xml)
- [Backend JSON](../backend/coverage/coverage.json)
- [Frontend HTML](../frontend/coverage/index.html)
- [Frontend LCOV](../frontend/coverage/lcov.info)
- [Frontend JSON summary](../frontend/coverage/coverage-summary.json)

## Module coverage and gaps

| Module | Coverage | Remaining area |
| --- | ---: | --- |
| `app/service/llm/base/client.py` | 33.33% combined | Initialization, direct invocation, provider errors and HTTP client cleanup are largely mocked. |
| `app/service/llm/role/__init__.py` | 75.00% combined | Empty prompt failure. |
| `app/api/routes.py` | 90.70% combined | Non-timeout chat configuration/S3/model error mappings. |
| `app/service/llm/workflow/chain.py` | 92.41% combined | Missing source configuration and initialization failure. |
| `app/service/provide/aws/base.py` | 92.44% combined | Some absent configuration, invalid JSON shape and edge branches. |
| `frontend/src/api.js` | 63.15% lines | Recon/connection flows, network failure branches and custom integration settings. |
| `frontend/src/auth.js` | 100.00% lines | Some storage/configuration/error branches remain. |
| `frontend/src/resources.js` | 100.00% lines | Some malformed-input and multi-source branches remain. |

See [feature-wise cases](test_case.md) for specific unit/integration evidence,
manual E2E procedures, and pending collector/component tests.

## Other checks

Frontend ESLint and production build passed in this run. Backend Ruff lint and
format checks are recorded with the documentation validation. Pytest reported
13 upstream LangSmith deprecation warnings. Vite ignored dependency `use client`
directives; the build completed successfully.

## Reproduce

Install backend dev dependencies and frontend dependencies as described in
[CONTRIBUTING](../CONTRIBUTING.md). From `backend/`:

```sh
python -m pytest --cov=app --cov-branch \
  --cov-report=term-missing \
  --cov-report=html:coverage/html \
  --cov-report=xml:coverage/coverage.xml \
  --cov-report=json:coverage/coverage.json
```

From `frontend/`:

```sh
npm run test:coverage
```

This is a snapshot of the dated run, not an automatically updated badge. Regenerate
artifacts and update this summary when source or tests change.
