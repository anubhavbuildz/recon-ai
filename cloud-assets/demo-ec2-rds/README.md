# Demo: two EC2 instances connected to MySQL RDS

This standalone Terraform project creates an isolated VPC, two Amazon Linux 2023
EC2 instances in different availability zones, and one private MySQL RDS instance.
It is separate from the snapshot collector Terraform and uses separate state.
It does not deploy an application or populate tables.

EC2 security groups allow outbound MySQL only to the database security group.
The database accepts port 3306 only from those instances. EC2 has no inbound rules
or SSH keys; use AWS Systems Manager Session Manager for administration. EC2 has
public IPv4 addresses for outbound HTTPS to SSM without a NAT gateway. RDS has no
public address and its subnets have no internet route. RDS generates and manages
the database password in Secrets Manager; no password is output or placed in
user data. Instance roles do not automatically have access to that secret.

## Deploy

Requires Terraform >= 1.5, an AWS identity authorized to provision the resources,
and a region with at least two availability zones. Defaults use x86 EC2 types;
if changing `instance_type`, keep it compatible with the x86 Amazon Linux AMI.

From the repository root:

```sh
cd cloud-assets/demo-ec2-rds
terraform init
terraform plan -var='aws_region=us-east-1'
terraform apply -var='aws_region=us-east-1'
```

Optional inputs: `project_name`, `instance_type` (default `t3.micro`), and
`db_instance_class` (default `db.t3.micro`). The parent folder's exported `TF_VAR_*`
values also apply to matching names here. Review the plan before applying.
No deployment has been performed as part of adding these files.

## Verify connectivity

Each instance runs a bootstrap TCP check against the RDS endpoint. After creation,
open the instance's Session Manager session (allow several minutes for SSM
registration), or use the CLI with Session Manager plugin and operator permissions:

```sh
terraform output instance_ids
aws ssm start-session --target <instance-id> --region us-east-1
```

Inside each instance:

```sh
sudo cat /var/log/demo-db-connectivity.log
```

Look for `SUCCESS: demo RDS MySQL TCP endpoint reachable`. Terraform completing
successfully does not establish that this bootstrap check passed. This checks
network reachability only, not authenticated SQL. Use `terraform output
database_secret_arn` to locate the RDS-managed secret; an appropriately authorized
operator can retrieve it to perform a separate SQL test. Do not paste credentials
into logs or commit them. Outputs also expose the database endpoint.

## Cost and cleanup

EC2, EBS, public IPv4, RDS, Secrets Manager and related services can incur charges.
This is a disposable, single-AZ database demo, not a production architecture.
**Destroy deletes the database without a final snapshot.** Do not store important
data here. To remove the demo, use the same region/variable values used to create it:

```sh
terraform destroy -var='aws_region=us-east-1'
```
