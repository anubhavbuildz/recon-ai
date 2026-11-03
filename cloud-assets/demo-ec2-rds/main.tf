terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = var.project_name
      Environment = "demo"
      ManagedBy   = "Terraform"
    }
  }
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "recon-demo"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,29}$", var.project_name)) && !endswith(var.project_name, "-") && !strcontains(var.project_name, "--")
    error_message = "Use 3–30 lowercase letters, digits or hyphens; start with a letter and avoid trailing or consecutive hyphens."
  }
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

variable "db_instance_class" {
  type    = string
  default = "db.t3.micro"
}

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_ssm_parameter" "amazon_linux" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

data "aws_partition" "current" {}

resource "aws_vpc" "demo" {
  cidr_block           = "10.42.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "${var.project_name}-vpc" }
}

resource "aws_internet_gateway" "demo" {
  vpc_id = aws_vpc.demo.id
}

resource "aws_subnet" "compute" {
  count                   = 2
  vpc_id                  = aws_vpc.demo.id
  cidr_block              = cidrsubnet(aws_vpc.demo.cidr_block, 8, count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
  tags                    = { Name = "${var.project_name}-compute-${count.index + 1}" }
}

resource "aws_subnet" "database" {
  count             = 2
  vpc_id            = aws_vpc.demo.id
  cidr_block        = cidrsubnet(aws_vpc.demo.cidr_block, 8, count.index + 10)
  availability_zone = data.aws_availability_zones.available.names[count.index]
  tags              = { Name = "${var.project_name}-database-${count.index + 1}" }
}

resource "aws_route_table" "compute" {
  vpc_id = aws_vpc.demo.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.demo.id
  }
}

resource "aws_route_table_association" "compute" {
  count          = 2
  subnet_id      = aws_subnet.compute[count.index].id
  route_table_id = aws_route_table.compute.id
}

# Explicitly isolated database route table: only the VPC-local route.
resource "aws_route_table" "database" {
  vpc_id = aws_vpc.demo.id
}

resource "aws_route_table_association" "database" {
  count          = 2
  subnet_id      = aws_subnet.database[count.index].id
  route_table_id = aws_route_table.database.id
}

resource "aws_security_group" "compute" {
  name_prefix = "${var.project_name}-compute-"
  description = "No inbound access; HTTPS for SSM and MySQL to the demo database"
  vpc_id      = aws_vpc.demo.id
}

resource "aws_security_group" "database" {
  name_prefix = "${var.project_name}-database-"
  description = "MySQL access only from demo EC2 instances"
  vpc_id      = aws_vpc.demo.id
}

resource "aws_vpc_security_group_egress_rule" "https" {
  security_group_id = aws_security_group.compute.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "mysql" {
  security_group_id            = aws_security_group.compute.id
  referenced_security_group_id = aws_security_group.database.id
  from_port                    = 3306
  to_port                      = 3306
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "mysql" {
  security_group_id            = aws_security_group.database.id
  referenced_security_group_id = aws_security_group.compute.id
  from_port                    = 3306
  to_port                      = 3306
  ip_protocol                  = "tcp"
}

resource "aws_db_subnet_group" "demo" {
  name       = "${var.project_name}-database"
  subnet_ids = aws_subnet.database[*].id
}

resource "aws_db_instance" "demo" {
  identifier                  = "${var.project_name}-mysql"
  engine                      = "mysql"
  instance_class              = var.db_instance_class
  allocated_storage           = 20
  storage_type                = "gp3"
  storage_encrypted           = true
  db_name                     = "recondemo"
  username                    = "demoadmin"
  manage_master_user_password = true
  publicly_accessible         = false
  multi_az                    = false
  db_subnet_group_name        = aws_db_subnet_group.demo.name
  vpc_security_group_ids      = [aws_security_group.database.id]
  backup_retention_period     = 1
  # Disposable demo only: destroy deletes the DB without a final snapshot.
  deletion_protection = false
  skip_final_snapshot = true
}

resource "aws_iam_role" "compute" {
  name_prefix = "${var.project_name}-compute-"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.compute.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "compute" {
  name_prefix = "${var.project_name}-compute-"
  role        = aws_iam_role.compute.name
}

resource "aws_instance" "demo" {
  count                  = 2
  ami                    = data.aws_ssm_parameter.amazon_linux.value
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.compute[count.index].id
  vpc_security_group_ids = [aws_security_group.compute.id]
  iam_instance_profile   = aws_iam_instance_profile.compute.name
  metadata_options {
    http_tokens = "required"
  }
  root_block_device {
    volume_size = 8
    encrypted   = true
  }
  user_data                   = <<-SCRIPT
    #!/bin/bash
    # TCP reachability only. This does not authenticate to MySQL or run SQL.
    exec > /var/log/demo-db-connectivity.log 2>&1
    for attempt in {1..30}; do
      if timeout 5 bash -c 'echo > /dev/tcp/${aws_db_instance.demo.address}/3306'; then
        echo "SUCCESS: demo RDS MySQL TCP endpoint reachable"
        exit 0
      fi
      sleep 10
    done
    echo "FAILED: RDS MySQL TCP endpoint not reachable"
    exit 1
  SCRIPT
  user_data_replace_on_change = true
  tags                        = { Name = "${var.project_name}-ec2-${count.index + 1}" }
  depends_on = [
    aws_route_table_association.compute,
    aws_iam_role_policy_attachment.ssm,
    aws_vpc_security_group_egress_rule.mysql,
    aws_vpc_security_group_ingress_rule.mysql,
  ]
}

output "instance_ids" {
  value = aws_instance.demo[*].id
}

output "database_endpoint" {
  value = aws_db_instance.demo.endpoint
}

output "database_secret_arn" {
  description = "RDS-managed credentials; retrieving them requires separate IAM permission."
  value       = aws_db_instance.demo.master_user_secret[0].secret_arn
}
