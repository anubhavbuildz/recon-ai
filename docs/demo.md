# Recon AI demo setup

Recon AI is an MVP built as part of the Meta Global Hackathon. This guide starts
the frontend and backend locally and deploys the AWS snapshot collector. Terraform
does not host the application. See [security considerations](../security.md)
before using sensitive data, and [coverage](coverage.md) for validation limits.

## 1. Prerequisites

- Python 3.12+.
- Node.js compatible with Vite 7: 20.19+ or 22.12+.
- Terraform 1.5+ and the AWS CLI.
- An AWS account/profile authorized to provision the collector's IAM, Lambda,
  S3, CloudWatch Logs and EventBridge resources.
- A configured OpenAI-compatible model provider with tool-calling support,
  model name, API key and, when required, base URL.

Run commands from the repository root unless a step changes directory. AWS
resources and model calls can incur charges. Use a disposable demo account or
approved environment. No real credentials belong in committed files.

## 2. Install the application

```sh
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -e './backend[dev]'
npm --prefix frontend ci
```

Copy configuration examples only if the destination does not already exist:

```sh
test -f backend/.env || cp backend/.env.example backend/.env
test -f frontend/.env || cp frontend/.env.example frontend/.env
test -f cloud-assets/.env || cp cloud-assets/.env.example cloud-assets/.env
```

## 3. Deploy the AWS collector

Edit `cloud-assets/.env`. For the default demo configuration:

```env
TF_VAR_aws_region=us-east-1
TF_VAR_project_name=cloud-optimizer
TF_VAR_retention_days=14
AWS_DEFAULT_REGION=us-east-1
# AWS_PROFILE=your-profile
```

Authenticate with your normal AWS credential chain before deployment. Export
these values in the terminal that runs Terraform and the collector commands:

```sh
cd cloud-assets
set -a
source .env
set +a
aws sts get-caller-identity
terraform init
terraform plan -out=demo.tfplan
terraform apply demo.tfplan
terraform output snapshot_bucket
terraform output collector_lambda
```

Review the plan before applying. Terraform creates the encrypted snapshot bucket,
read-only collector role, Lambda, logs and an EventBridge schedule every five
minutes. Snapshot lifecycle expiration defaults to 14 days. Terraform state and
saved plans can contain sensitive configuration; keep them local and out of Git.

The collector inventories **EC2 and EBS in one account and region**, with rolling
14-day EC2 CPU statistics. It does not currently inventory RDS, S3 buckets,
billing, memory metrics, or resource pricing. Empty EC2/EBS arrays are valid when
there are no matching resources.

## 4. Optional: create resources for the demo

Skip this step if your account already has suitable EC2/EBS resources. The
separate demo creates two EC2 instances, a VPC, and a private MySQL RDS instance:

```sh
cd demo-ec2-rds
terraform init
terraform plan -var='aws_region=us-east-1' -out=demo.tfplan
terraform apply demo.tfplan
terraform output instance_ids
cd ..
```

This configuration has separate Terraform state. The collector will see its EC2
instances and EBS volumes in the same region, but **will not collect the RDS
instance**. The database is a connectivity demo, not an application database.
See [demo details](../cloud-assets/demo-ec2-rds/README.md) for SSM connectivity
verification and limitations. Destroying this demo deletes the database without
a final snapshot.

## 5. Collect initial evidence

From `cloud-assets/`, using the exported region and profile:

```sh
aws lambda invoke \
  --function-name "$(terraform output -raw collector_lambda)" \
  --region "$AWS_DEFAULT_REGION" \
  /tmp/recon-collector-result.json
cat /tmp/recon-collector-result.json
aws s3 ls "s3://$(terraform output -raw snapshot_bucket)/snapshots/" --recursive
```

Check both Lambda's invocation metadata and result for errors; invocation HTTP
success alone does not prove that the handler succeeded. Deployment does not
invoke the collector immediately. Later scheduled invocations create additional
files; you do not need three files before using chat.

## 6. Configure the backend

Return to the repository root and edit `backend/.env`:

```env
AUTH_USERNAME=your-demo-user
AUTH_PASSWORD=your-long-unique-password
JWT_SECRET=replace-with-a-random-secret-at-least-32-bytes
LLM_API_KEY=your-provider-key
LLM_MODEL=your-tool-capable-model
LLM_BASE_URL=https://your-provider.example/v1
LLM_TIMEOUT_SECONDS=30
S3_BUCKET_NAME=replace-with-terraform-snapshot-bucket-output
S3_REGION=us-east-1
S3_SNAPSHOT_PREFIX=snapshots/
S3_OBJECT_KEY=
S3_MAX_BYTES=200000
```

Use your actual provider URL; omit `LLM_BASE_URL` if the provider uses the client's
default endpoint. Generate a signing secret locally:

```sh
python -c 'import secrets; print(secrets.token_urlsafe(48))'
```

The backend AWS identity needs `s3:ListBucket` scoped to the configured prefix and
`s3:GetObject` for its objects. A profile exported in the Terraform terminal is
not automatically available in a different backend terminal: configure/export
`AWS_PROFILE` there too when needed. Terraform can optionally provision a reader
role using `TF_VAR_backend_role_arn`; the application does not automatically
assume that role. Use an appropriately configured SDK profile or role credentials.

Prefix mode reads **up to three newest JSON objects by S3 LastModified**, across
nested folders, newest first. It overrides `S3_OBJECT_KEY`. All three may be from
the same day. If one or two exist, those are used. `S3_HISTORY_DAYS` is a legacy
setting and no longer controls selection. The combined context must fit
`S3_MAX_BYTES`. To restrict the selection to a day, use a prefix such as
`snapshots/2026/11/04/`. For one exact file, unset the prefix and set its object key.

## 7. Start the backend and frontend

Backend terminal, from the repository root:

```sh
source backend/.venv/bin/activate
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend terminal, from the repository root:

```sh
cd frontend
npm run dev
```

Set `frontend/.env` to `VITE_API_BASE_URL=http://127.0.0.1:8000`. Optional inventory,
resource-detail and connection paths can stay blank: the built-in backend serves
S3 chat, not those optional integrations. Restart the relevant server after
changing environment settings. Backend process environment values override `.env`.

Open `http://127.0.0.1:5173`, sign in with the configured credentials, and ask:

> Summarize the supplied snapshots in a table with collection time, region,
> EC2 count and EBS count. Highlight changes supported by the evidence.

Answers render Markdown tables and list their S3 sources. The regional map has
been removed. Each question is independent. Snapshot CPU values are rolling
14-day aggregates, not independent measurements for each snapshot interval.
This browser step is a manual demo walkthrough, not an automated E2E test.

## 8. Validate without browser E2E

From `backend/`:

```sh
.venv/bin/python -m pytest tests -q
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
```

From `frontend/`:

```sh
npm test
npm run lint
npm run build
```

For an explicitly live integration check, from `backend/`:

```sh
PYTHONPATH=. .venv/bin/python scripts/check_live_integration.py
```

The live script reads real S3 evidence and calls the configured model through an
in-process authenticated API. It uses a temporary session database and prints
sanitized status metadata. It does not open a browser or modify cloud resources.
See [test cases](test_case.md) and [coverage](coverage.md) for results and gaps.

## 9. Troubleshooting and cleanup

- No snapshots: verify the bucket/prefix, region, collector result and Lambda logs.
- S3 access failure: verify the backend identity and scoped list/get permissions.
- Context too large: reduce snapshot content or raise the limit within the
  supported maximum of 2,000,000 bytes; do not assume files are truncated.
- Model failure: verify provider settings, tool support and timeout.
- No credentials configured: complete backend auth/model settings and restart.

Destroy optional demo resources from their own directory using the same variables:

```sh
cd cloud-assets/demo-ec2-rds
terraform plan -destroy -var='aws_region=us-east-1'
terraform destroy -var='aws_region=us-east-1'
```

Then, from `cloud-assets/`, review and destroy the collector:

```sh
terraform plan -destroy
terraform destroy
```

The snapshot bucket has `force_destroy = false`. A nonempty bucket can block
cleanup; inspect and back up needed evidence, then intentionally empty it before
retrying destruction. There is no automatic data-deletion command in this guide.
The application cannot read snapshots once its bucket is destroyed.
