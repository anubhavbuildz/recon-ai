# AWS infrastructure setup

The Terraform projects create AWS resources, not application hosting:

| Directory | Resources |
| --- | --- |
| `cloud-assets/` | Snapshot S3 bucket, IAM roles/policies, Python Lambda, log group and five-minute EventBridge test schedule |
| `cloud-assets/demo-ec2-rds/` | Separate demo VPC, two EC2 instances, private MySQL RDS and SSM access |

The backend and frontend run separately. They are not deployed by either project.
See [current diagrams](diagrams/README.md) for component relationships.

## Prerequisites

Install Terraform >= 1.5 and AWS CLI. Select an AWS account and region in which you
are authorized to provision IAM, Lambda, S3, logs and EventBridge resources; the
optional demo additionally needs EC2, networking, RDS and Secrets Manager access.
Prefer a named profile or temporary credentials. Never commit access keys,
Terraform state, saved plans, or local `.env` files. Review costs and the Terraform
plan before applying; this guide does not authorize deployment to an arbitrary account.

Confirm your identity before any deployment:

```sh
aws sts get-caller-identity
```

The local identity needs provisioning permissions. The Lambda execution role and
backend reader identity have separate runtime permissions; do not use a broad
provisioning role as the application's permanent credentials.

## 1. Deploy the collector

From the repository root:

```sh
cd cloud-assets
cp .env.example .env
```

If `.env` already exists, edit it rather than overwriting it. Set:

```env
TF_VAR_aws_region=us-east-1
TF_VAR_project_name=cloud-optimizer
TF_VAR_retention_days=14
TF_VAR_backend_role_arn=
AWS_DEFAULT_REGION=us-east-1
# AWS_PROFILE=your-authorized-profile
```

The optional backend role ARN identifies an existing IAM role trusted to assume
the reader role Terraform can create. Leave it empty if using another authorized
identity. Load configuration and inspect the plan:

```sh
set -a
source .env
set +a
terraform init
terraform fmt -check
terraform validate
terraform plan
terraform apply
```

Terraform does not automatically read `.env`; `TF_VAR_*` exports supply its inputs.
The AWS provider packages `collector.py` through the archive provider and uploads
it to Lambda with `collector.lambda_handler` and Python 3.12. Terraform sets
`TARGET_REGION` and `SNAPSHOT_BUCKET` on the Lambda. Do not add notebook commands
such as `!pip install` to this module; Lambda provides boto3 for this runtime.

The EventBridge rule uses `rate(5 minutes)` for testing. It does not invoke the
function immediately on apply. Each invocation collects EC2 and EBS metadata and
rolling 14-day CPU statistics, and writes JSON to:

```text
snapshots/YYYY/MM/DD/YYYYMMDDTHHMMSSZ.json
```

Dates are UTC. The collector does not retrieve RDS inventory, S3 inventory, RAM,
disk/network metrics, or account billing/pricing. Collection is scoped to one region.
A frequent schedule does not turn the rolling CPU aggregates into five-minute metrics.

## 2. Verify the collector

From the collector Terraform directory:

```sh
terraform output
aws lambda invoke \
  --function-name "$(terraform output -raw collector_lambda)" \
  --region "$TF_VAR_aws_region" \
  /tmp/collector-result.json
cat /tmp/collector-result.json
aws s3 ls "s3://$(terraform output -raw snapshot_bucket)/snapshots/" --recursive
```

A Lambda invocation's HTTP success alone does not prove the handler succeeded.
Check the CLI result for `FunctionError`, the payload for counts and an object key,
and CloudWatch logs if errors occur. Confirm that another snapshot appears after
the schedule runs. Use the actual project name for the log group:

```sh
aws logs tail "/aws/lambda/${TF_VAR_project_name}-collector" --since 30m \
  --region "$TF_VAR_aws_region"
```

Snapshot expiration uses asynchronous S3 lifecycle rules, not an exact deletion
deadline. Restore a slower schedule in `main.tf` after testing and apply that change.

## 3. Give the backend read access

The backend identity needs `s3:GetObject` for the selected object or snapshot prefix.
History mode additionally needs `s3:ListBucket` on the bucket, restricted to the
configured prefix. The optional Terraform reader policy scopes these to `snapshots/*`.
It does not permit reading the synthetic fixture's `testing/synthetic/` prefix.

When `backend_role_arn` is set, Terraform outputs `reader_role_arn`. The existing
backend role also needs `sts:AssumeRole` permission on that role. The application
uses boto3's standard credential chain; it does not explicitly assume the role.
Configure a role-based AWS profile, for example in your local AWS config:

```ini
[profile recon-snapshot-reader]
role_arn = arn:aws:iam::YOUR_ACCOUNT_ID:role/YOUR_READER_ROLE
source_profile = your-authorized-source-profile
region = us-east-1
```

Use the actual output ARN, then start the backend with `AWS_PROFILE` set to that
profile. In hosted environments, an appropriate workload role can supply credentials
instead. Bucket policies and encryption-key policies may also affect access.

## 4. Configure application data access

Copy the collector's `snapshot_bucket` output and region into `backend/.env`.
For one specific snapshot:

```env
S3_BUCKET_NAME=your-snapshot-bucket
S3_REGION=us-east-1
S3_OBJECT_KEY=snapshots/YYYY/MM/DD/YYYYMMDDTHHMMSSZ.json
```

For historical comparison:

```env
S3_SNAPSHOT_PREFIX=snapshots/
S3_HISTORY_DAYS=3
S3_MAX_BYTES=200000
```

Prefix mode takes precedence over the exact key. It reads the latest timestamped
JSON object per UTC day for today and previous days (1–14 days supported), includes
missing dates, and fails if no data exists. It does not wait for future snapshots
or read every file. Keep the combined evidence within the byte limit. To return
to single-file mode, unset or empty `S3_SNAPSHOT_PREFIX`.

Configure login and LLM settings using the [root README](../README.md), then restart
the backend and frontend as necessary. Questions send S3 data to the configured
model provider. For local synthetic testing, see the [fixture guide](../cloud-assets/fixtures/README.md).

## 5. Optional EC2/RDS demo

Use a separate terminal to avoid unintentionally reusing collector `TF_VAR_*`
exports such as `project_name`. From the repository root:

```sh
cd cloud-assets/demo-ec2-rds
terraform init
terraform validate
terraform plan -var='aws_region=us-east-1' -var='project_name=recon-demo'
terraform apply -var='aws_region=us-east-1' -var='project_name=recon-demo'
terraform output
```

Two EC2 instances use public subnets for outbound SSM HTTPS, but have no inbound
rules. A private single-AZ MySQL RDS database accepts TCP 3306 only from the EC2
security group. The password is RDS-managed in Secrets Manager and is not printed.
The instances' roles do not automatically have permission to retrieve it.

Use Session Manager with an authorized operator identity to inspect each
instance's `/var/log/demo-db-connectivity.log`. This bootstrap check proves TCP
reachability only; authenticated SQL requires a separate test and credential
access. See the [demo guide](../cloud-assets/demo-ec2-rds/README.md). The collector
can observe demo EC2/EBS resources in the same account/region, but not demo RDS.

## Cleanup and status

Run `terraform destroy` separately in each project's directory with the same input
values used for deployment. Demo database destruction skips the final snapshot:
never store important data there. The collector bucket uses `force_destroy=false`;
nonempty buckets can block destruction. Review and back up retained snapshots
before explicitly deleting data. Do not delete state just to bypass cleanup.

Both Terraform configurations have previously passed static validation. Deployment,
SSM/SQL connectivity, scheduled collection and full browser-to-collected-snapshot
operation have not been verified by the automated suite. Live S3 and model tool
smoke tests were run separately; see [test cases](test_case.md).
