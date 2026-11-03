# AI Cloud Resource Optimizer — AWS snapshot collector

Terraform deploys a read-only EC2/EBS/CloudWatch collector into one AWS account and Region.

## Requirements
- Terraform >= 1.5
- AWS CLI configured with permissions to create IAM roles/policies, Lambda, S3, CloudWatch Logs, and EventBridge rules
- AWS account in the desired region

## Deploy
From the `cloud-assets/` directory, create your local configuration:

```bash
cp .env.example .env
# Edit .env with your region, project settings, and optional AWS profile.
set -a
source .env
set +a
```

Terraform does not load `.env` automatically. Exporting the file makes its
`TF_VAR_*` values available as Terraform inputs. Keep `AWS_DEFAULT_REGION` aligned
with `TF_VAR_aws_region` for AWS CLI commands. The local `.env` is ignored by Git;
the example contains no credentials. Lambda's `TARGET_REGION` and
`SNAPSHOT_BUCKET` are configured by Terraform rather than this file.

```bash
terraform init
terraform plan
terraform apply
```

Optionally set `-var='aws_region=us-east-1'`, `-var='retention_days=14'`, or `-var='backend_role_arn=arn:aws:iam::123456789012:role/YourBackendRole'`.

## Test immediately
```bash
aws lambda invoke --function-name cloud-optimizer-collector --region us-east-1 /tmp/collector-result.json
cat /tmp/collector-result.json
aws s3 ls "s3://$(terraform output -raw snapshot_bucket)/snapshots/" --recursive
```

Terraform packages `collector.py` into a ZIP and uploads it to Lambda with the
`collector.lambda_handler` entry point. EventBridge invokes it every 5 minutes
using `rate(5 minutes)` for testing. This creates more snapshots and increases
API activity; restore a slower schedule after testing. Deployment does not invoke the collector immediately;
use the manual invocation above when you need an initial snapshot. Each snapshot includes EC2 metadata, 14-day CPU stats, and EBS volume metadata. No AWS Config, EC2 user data, secrets, or application data are collected.

## Scope and limitations
- The collector covers only the configured AWS Region.
- It does **not** collect RDS, S3 inventory, Cost Explorer billing, or exact EC2/EBS pricing yet.
- The AI backend, frontend, and agent orchestration are **not deployed** by this Terraform.
- A backend reader role is optionally created, but the backend's own role must also be permitted to call `sts:AssumeRole` on it.
- S3 lifecycle expiration is asynchronous and is not an exact deletion deadline.
- The bucket has `force_destroy = false`; destroy may require emptying snapshot objects first.
- IAM permissions with `Resource = "*"` are used only for AWS describe/metric operations that do not support resource-level restrictions.
- AWS services and API calls can incur charges; review estimated costs and AWS budgets before deployment.

## Destroy
```bash
terraform destroy
```

To destroy a nonempty bucket, delete its snapshot objects first after confirming they are no longer needed.

## Demo infrastructure

For a separate demo VPC with two EC2 instances connected to a private MySQL RDS
database, see [demo-ec2-rds](demo-ec2-rds/README.md). It has its own Terraform
state and is not deployed by the collector configuration.

## Synthetic snapshot for chat testing

[fixtures/demo-snapshot.json](fixtures/demo-snapshot.json) provides clearly labeled
synthetic EC2/EBS collector output. See the [fixture guide](fixtures/README.md)
for scenarios, suggested questions, and switching back to real data.
