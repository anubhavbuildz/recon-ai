import json
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import Mock

import pytest

from app.core.config import Settings
from app.service.provide.aws.base import Aws


def item(key, hour):
    return {
        "Key": key,
        "LastModified": datetime(2026, 11, 4, hour, tzinfo=timezone.utc),
    }


def provider(pages, limit=200000, prefix="snapshots/"):
    aws = Aws.__new__(Aws)
    aws.settings = Settings(
        s3_bucket_name="bucket", s3_snapshot_prefix=prefix, s3_max_bytes=limit
    )
    aws.aws_client = Mock()
    aws.aws_client.get_paginator.return_value.paginate.return_value = pages
    aws.aws_client.get_object.side_effect = lambda **kwargs: {
        "Body": BytesIO(b'{"ec2_instances": []}'),
        "ContentLength": 21,
    }
    return aws


def test_latest_three_across_pages_by_modification_time():
    aws = provider(
        [
            {
                "Contents": [
                    item("snapshots/z.json", 1),
                    item("snapshots/old/a.json", 6),
                ]
            },
            {
                "Contents": [
                    item("snapshots/b.json", 5),
                    item("snapshots/c.json", 4),
                    item("snapshots/ignored.txt", 10),
                    item("other/outside.json", 11),
                ]
            },
        ]
    )
    result = json.loads(aws.read_snapshot_history())
    assert [s["source"] for s in result["snapshots"]] == [
        "s3://bucket/snapshots/old/a.json",
        "s3://bucket/snapshots/b.json",
        "s3://bucket/snapshots/c.json",
    ]
    assert aws.aws_client.get_object.call_count == 3
    aws.aws_client.get_paginator.return_value.paginate.assert_called_once_with(
        Bucket="bucket", Prefix="snapshots/"
    )


@pytest.mark.parametrize("count", [1, 2])
def test_reads_fewer_files_when_available(count):
    aws = provider(
        [{"Contents": [item(f"snapshots/{i}.json", i) for i in range(count)]}]
    )
    assert len(json.loads(aws.read_snapshot_history())["snapshots"]) == count


def test_empty_prefix_fails():
    aws = provider([{}])
    with pytest.raises(ValueError, match="No snapshots"):
        aws.read_snapshot_history()
    aws.aws_client.get_object.assert_not_called()


def test_dated_prefix_and_ties():
    prefix = "snapshots/2026/11/04/"
    aws = provider(
        [
            {
                "Contents": [
                    item(prefix + name + ".json", 1) for name in ["a", "c", "b", "d"]
                ]
            }
        ],
        prefix=prefix,
    )
    result = json.loads(aws.read_snapshot_history())
    assert [s["source"].rsplit("/", 1)[-1] for s in result["snapshots"]] == [
        "d.json",
        "c.json",
        "b.json",
    ]
    assert (
        aws.aws_client.get_paginator.return_value.paginate.call_args.kwargs["Prefix"]
        == prefix
    )


def test_total_context_size_is_bounded():
    aws = provider([{"Contents": [item("snapshots/a.json", 1)]}], limit=100)
    with pytest.raises(ValueError, match="Combined snapshot"):
        aws.read_snapshot_history()


@pytest.mark.parametrize("data", [b"not json", b"[]", b"\xff"])
def test_invalid_document_closes_body(data):
    aws = provider([{"Contents": [item("snapshots/a.json", 1)]}])
    body = BytesIO(data)
    aws.aws_client.get_object.side_effect = None
    aws.aws_client.get_object.return_value = {"Body": body}
    with pytest.raises(ValueError):
        aws.read_snapshot_history()
    assert body.closed
