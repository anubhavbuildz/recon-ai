terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "cloud-optimizer"
}

variable "retention_days" {
  type    = number
  default = 14
  validation {
    condition     = var.retention_days >= 1
    error_message = "retention_days must be at least 1."
  }
}

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

locals {
  prefix = "${var.project_name}-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
}

resource "aws_s3_bucket" "snapshots" {
  bucket        = "${local.prefix}-snapshots"
  force_destroy = false
}

resource "aws_s3_bucket_public_access_block" "snapshots" {
  bucket                  = aws_s3_bucket.snapshots.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "snapshots" {
  bucket = aws_s3_bucket.snapshots.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "snapshots" {
  bucket = aws_s3_bucket.snapshots.id
  versioning_configuration {
    status = "Suspended"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "snapshots" {
  bucket = aws_s3_bucket.snapshots.id
  rule {
    id     = "expire-dated-snapshots"
    status = "Enabled"
    filter {
      prefix = "snapshots/"
    }
    expiration {
      days = var.retention_days
    }
  }
}

resource "aws_s3_bucket_policy" "snapshots" {
  bucket = aws_s3_bucket.snapshots.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport"
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource  = [aws_s3_bucket.snapshots.arn, "${aws_s3_bucket.snapshots.arn}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "collector" {
  name               = "${var.project_name}-collector-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "collector" {
  statement {
    sid = "ReadEC2Inventory"
    actions = [
      "ec2:DescribeInstances",
      "ec2:DescribeVolumes"
    ]
    resources = ["*"]
  }
  statement {
    sid       = "ReadCloudWatchMetrics"
    actions   = ["cloudwatch:GetMetricStatistics"]
    resources = ["*"]
  }
  statement {
    sid       = "WriteSnapshots"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.snapshots.arn}/snapshots/*"]
  }
}

resource "aws_iam_role_policy" "collector" {
  name   = "${var.project_name}-collector-policy"
  role   = aws_iam_role.collector.id
  policy = data.aws_iam_policy_document.collector.json
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.collector.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_cloudwatch_log_group" "collector" {
  name              = "/aws/lambda/${var.project_name}-collector"
  retention_in_days = 7
}

data "archive_file" "collector" {
  type        = "zip"
  source_file = "${path.module}/collector.py"
  output_path = "${path.module}/collector.zip"
}

resource "aws_lambda_function" "collector" {
  function_name    = "${var.project_name}-collector"
  role             = aws_iam_role.collector.arn
  handler          = "collector.lambda_handler"
  runtime          = "python3.12"
  filename         = data.archive_file.collector.output_path
  source_code_hash = data.archive_file.collector.output_base64sha256
  timeout          = 180
  memory_size      = 256
  environment {
    variables = {
      SNAPSHOT_BUCKET = aws_s3_bucket.snapshots.id
      TARGET_REGION   = var.aws_region
    }
  }
  depends_on = [aws_iam_role_policy.collector, aws_iam_role_policy_attachment.lambda_logs, aws_cloudwatch_log_group.collector]
}

resource "aws_cloudwatch_event_rule" "daily" {
  name                = "${var.project_name}-daily-collection"
  description         = "Collect AWS inventory and utilization every 5 minutes"
  schedule_expression = "rate(5 minutes)"
}

resource "aws_cloudwatch_event_target" "collector" {
  rule = aws_cloudwatch_event_rule.daily.name
  arn  = aws_lambda_function.collector.arn
}

resource "aws_lambda_permission" "events" {
  statement_id  = "AllowEventBridgeDailyCollection"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.collector.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily.arn
}

# Optional role for an existing backend to assume. Configure the backend principal explicitly.
variable "backend_role_arn" {
  description = "IAM role ARN of the existing backend permitted to assume the snapshot reader role; empty disables creation."
  type        = string
  default     = ""
}

resource "aws_iam_role" "snapshot_reader" {
  count = var.backend_role_arn == "" ? 0 : 1
  name  = "${var.project_name}-snapshot-reader"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { AWS = var.backend_role_arn }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "snapshot_reader" {
  count = var.backend_role_arn == "" ? 0 : 1
  name  = "${var.project_name}-read-snapshots"
  role  = aws_iam_role.snapshot_reader[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject"]
      Resource = ["${aws_s3_bucket.snapshots.arn}/snapshots/*"]
      }, {
      Effect    = "Allow"
      Action    = ["s3:ListBucket"]
      Resource  = [aws_s3_bucket.snapshots.arn]
      Condition = { StringLike = { "s3:prefix" = ["snapshots/", "snapshots/*"] } }
    }]
  })
}

output "snapshot_bucket" {
  value = aws_s3_bucket.snapshots.id
}

output "collector_lambda" {
  value = aws_lambda_function.collector.function_name
}

output "reader_role_arn" {
  value = var.backend_role_arn == "" ? null : aws_iam_role.snapshot_reader[0].arn
}
