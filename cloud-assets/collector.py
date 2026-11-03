

"""Read-only AWS EC2/EBS collector. No secrets or instance user data collected."""
import json
import os

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import boto3

REGION = os.environ["TARGET_REGION"]
BUCKET = os.environ["SNAPSHOT_BUCKET"]


def metric_stats(client, instance_id, start, end):
    response = client.get_metric_statistics(
        Namespace="AWS/EC2",
        MetricName="CPUUtilization",
        Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
        StartTime=start,
        EndTime=end,
        Period=3600,
        Statistics=["Average", "Maximum"],
    )
    points = response.get("Datapoints", [])
    if not points:
        return {"average_percent": None, "maximum_percent": None, "sample_count": 0}
    # Each datapoint represents one hour. Average is the mean of hourly averages,
    # not a guarantee of exact time-weighted utilization across missing periods.
    return {
        "average_percent": round(sum(p["Average"] for p in points) / len(points), 3),
        "maximum_percent": round(max(p["Maximum"] for p in points), 3),
        "sample_count": len(points),
    }


def lambda_handler(event, context):
    ec2 = boto3.client("ec2", region_name=REGION)
    cw = boto3.client("cloudwatch", region_name=REGION)
    s3 = boto3.client("s3", region_name=REGION)
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=14)
    instances = []
    for page in ec2.get_paginator("describe_instances").paginate():
        for reservation in page.get("Reservations", []):
            for inst in reservation.get("Instances", []):
                instance_id = inst["InstanceId"]
                instances.append({
                    "resource_id": instance_id,
                    "service": "ec2",
                    "region": REGION,
                    "instance_type": inst["InstanceType"],
                    "state": inst["State"]["Name"],
                    "name": next((t["Value"] for t in inst.get("Tags", []) if t["Key"] == "Name"), None),
                    "cpu_14d": metric_stats(cw, instance_id, start, now),
                })
    volumes = []
    for page in ec2.get_paginator("describe_volumes").paginate():
        for volume in page.get("Volumes", []):
            volumes.append({
                "resource_id": volume["VolumeId"],
                "service": "ebs",
                "region": REGION,
                "size_gib": volume["Size"],
                "volume_type": volume["VolumeType"],
                "state": volume["State"],
                "attached_instance_ids": [a["InstanceId"] for a in volume.get("Attachments", []) if "InstanceId" in a],
            })
    payload = {
        "schema_version": "1.0",
        "collected_at": now.isoformat(),
        "region": REGION,
        "metric_window_start": start.isoformat(),
        "metric_window_end": now.isoformat(),
        "ec2_instances": instances,
        "ebs_volumes": volumes,
        "limitations": [
            "CPU metrics may be missing for stopped or recently launched instances.",
            "No RAM metrics, service pricing, or account billing data are included.",
            "This snapshot covers one AWS Region only."
        ]
    }
    key = f"snapshots/{now:%Y/%m/%d}/{now:%Y%m%dT%H%M%SZ}.json"
    s3.put_object(Bucket=BUCKET, Key=key, Body=json.dumps(payload).encode("utf-8"), ContentType="application/json", ServerSideEncryption="AES256")
    return {"bucket": BUCKET, "key": key, "ec2_count": len(instances), "ebs_count": len(volumes)}
