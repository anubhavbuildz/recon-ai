import json
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import Mock

import pytest

from app.core.config import Settings
from app.service.provide.aws.base import Aws

NOW = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)


def provider(pages, limit=200000):
    aws = Aws.__new__(Aws)
    aws.settings = Settings(
        s3_bucket_name="bucket", s3_snapshot_prefix="snapshots/", s3_max_bytes=limit
    )
    aws.aws_client = Mock()
    aws.aws_client.get_paginator.return_value.paginate.side_effect = pages
    aws.aws_client.get_object.side_effect = lambda **kwargs: {
        "Body": BytesIO(b'{"ec2_instances": []}'),
        "ContentLength": 21,
    }
    return aws


def test_latest_per_day_and_missing_dates():
    aws = provider(
        [
            [
                {"Contents": [{"Key": "snapshots/2026/11/03/20261103T090000Z.json"}]},
                {
                    "Contents": [
                        {"Key": "snapshots/2026/11/03/20261103T120000Z.json"},
                        {"Key": "snapshots/2026/11/03/readme.txt"},
                    ]
                },
            ],
            [{"Contents": [{"Key": "snapshots/2026/11/02/20261102T120000Z.json"}]}],
            [{}],
        ]
    )
    result = json.loads(aws.read_snapshot_history(NOW))
    assert [item["snapshot_date"] for item in result["snapshots"]] == [
        "2026-11-03",
        "2026-11-02",
    ]
    assert result["snapshots"][0]["source"].endswith("20261103T120000Z.json")
    assert result["missing_dates"] == ["2026-11-01"]
    assert aws.aws_client.get_object.call_count == 2
    assert (
        aws.aws_client.get_paginator.return_value.paginate.call_args_list[2].kwargs[
            "Prefix"
        ]
        == "snapshots/2026/11/01/"
    )


def test_empty_history_fails_without_model_evidence():
    aws = provider([[{}], [{}], [{}]])
    with pytest.raises(ValueError, match="No snapshots"):
        aws.read_snapshot_history(NOW)
    aws.aws_client.get_object.assert_not_called()


def test_total_context_size_is_bounded():
    aws = provider(
        [
            [{"Contents": [{"Key": "snapshots/2026/11/03/20261103T120000Z.json"}]}],
            [{}],
            [{}],
        ],
        limit=100,
    )
    with pytest.raises(ValueError, match="Combined snapshot"):
        aws.read_snapshot_history(NOW)


def test_invalid_json_closes_body():
    aws = provider(
        [[{"Contents": [{"Key": "snapshots/2026/11/03/20261103T120000Z.json"}]}]]
    )
    body = BytesIO(b"not json")
    aws.aws_client.get_object.side_effect = None
    aws.aws_client.get_object.return_value = {"Body": body}
    with pytest.raises(ValueError):
        aws.read_snapshot_history(NOW)
    assert body.closed
