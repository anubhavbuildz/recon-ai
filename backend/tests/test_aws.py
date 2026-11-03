from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError, NoCredentialsError

from app.core.config import Settings, get_settings
from app.service.provide.aws import base


@pytest.fixture
def aws(monkeypatch):
    client = Mock()
    client.meta.service_model.service_name = "s3"
    factory = Mock(return_value=client)
    monkeypatch.setattr(base.boto3, "client", factory)
    monkeypatch.setattr(base, "VALID_BUCKET_NAMES", ["approved-bucket"])
    provider = base.Aws(settings=Settings())
    factory.assert_called_once_with("s3")
    return provider


def test_existing_bucket_returns_uri_without_creating_resources(aws):
    assert aws._setup_bucket("approved-bucket", "reports/result.json") == (
        "s3://approved-bucket/reports/result.json"
    )
    aws.aws_client.head_bucket.assert_called_once_with(Bucket="approved-bucket")
    aws.aws_client.create_bucket.assert_not_called()
    aws.aws_client.put_object.assert_not_called()


@pytest.mark.parametrize(
    "bucket,key,message",
    [
        ("", "file.json", "bucket_name must not be empty"),
        ("   ", "file.json", "bucket_name must not be empty"),
        ("unapproved-bucket", "file.json", "not in VALID_BUCKET_NAMES"),
        ("approved-bucket", "", "file_key must not be empty"),
        ("approved-bucket", "   ", "file_key must not be empty"),
    ],
)
def test_invalid_inputs_do_not_call_s3(aws, bucket, key, message):
    with pytest.raises(ValueError, match=message):
        aws._setup_bucket(bucket, key)
    assert aws.aws_client.mock_calls == []


def test_empty_allowlist_rejects_all_buckets(aws, monkeypatch):
    monkeypatch.setattr(base, "VALID_BUCKET_NAMES", [])
    with pytest.raises(ValueError, match="not in VALID_BUCKET_NAMES"):
        aws._setup_bucket("approved-bucket", "file.json")
    assert aws.aws_client.mock_calls == []


def test_non_s3_client_is_rejected(aws):
    aws.aws_client.meta.service_model.service_name = "ec2"
    with pytest.raises(ValueError, match="requires an S3 client"):
        aws._setup_bucket("approved-bucket", "file.json")
    assert aws.aws_client.mock_calls == []


@pytest.mark.parametrize("code", ["404", "403"])
def test_bucket_errors_propagate_without_creating_bucket(aws, code):
    error = ClientError({"Error": {"Code": code}}, "HeadBucket")
    aws.aws_client.head_bucket.side_effect = error
    with pytest.raises(ClientError) as caught:
        aws._setup_bucket("approved-bucket", "file.json")
    assert caught.value is error
    aws.aws_client.create_bucket.assert_not_called()


def test_missing_credentials_propagate(aws):
    aws.aws_client.head_bucket.side_effect = NoCredentialsError()
    with pytest.raises(NoCredentialsError):
        aws._setup_bucket("approved-bucket", "file.json")
    aws.aws_client.create_bucket.assert_not_called()


def test_manual_bucket_location_from_environment(monkeypatch):
    monkeypatch.setenv("S3_BUCKET_NAME", " configured-bucket ")
    monkeypatch.setenv("S3_REGION", " ap-south-1 ")
    client = Mock()
    client.meta.service_model.service_name = "s3"
    factory = Mock(return_value=client)
    monkeypatch.setattr(base.boto3, "client", factory)
    monkeypatch.setattr(base, "VALID_BUCKET_NAMES", [])

    provider = base.Aws()

    factory.assert_called_once_with("s3", region_name="ap-south-1")
    assert provider._setup_bucket(file_key="reports/result.json") == (
        "s3://configured-bucket/reports/result.json"
    )
    client.head_bucket.assert_called_once_with(Bucket="configured-bucket")
    with pytest.raises(ValueError, match="not in VALID_BUCKET_NAMES"):
        provider._setup_bucket("other-bucket", "file.json")


def test_blank_s3_settings_are_optional(monkeypatch):
    monkeypatch.setenv("S3_BUCKET_NAME", "   ")
    monkeypatch.setenv("S3_REGION", "")
    settings = get_settings()
    assert settings.s3_bucket_name is None
    assert settings.s3_region is None


def test_missing_default_bucket_fails_before_s3_call(aws):
    with pytest.raises(ValueError, match="bucket_name must not be empty"):
        aws._setup_bucket(file_key="file.json")
    assert aws.aws_client.mock_calls == []
