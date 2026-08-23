"""
Discovers AWS resources in the account and returns structured metadata
for dashboard generation.

Supported resource types:
  - Lambda functions
  - Kinesis Data Streams
  - Kinesis Firehose delivery streams
  - S3 buckets
  - CloudWatch log groups (useful for Lambda log monitoring)

Usage:
    python src/discovery.py
"""

import os
import boto3
from dotenv import load_dotenv

load_dotenv()

REGION = os.environ.get("AWS_REGION", "us-east-1")
PROFILE = os.environ.get("AWS_PROFILE", "churn-mlops-personal")


def get_session():
    return boto3.Session(profile_name=PROFILE, region_name=REGION)


def discover_lambda_functions(session) -> list:
    client = session.client("lambda")
    paginator = client.get_paginator("list_functions")
    functions = []
    for page in paginator.paginate():
        for fn in page["Functions"]:
            functions.append({
                "type": "lambda",
                "name": fn["FunctionName"],
                "arn": fn["FunctionArn"],
                "runtime": fn.get("Runtime", "unknown"),
            })
    return functions


def discover_kinesis_streams(session) -> list:
    client = session.client("kinesis")
    paginator = client.get_paginator("list_streams")
    streams = []
    for page in paginator.paginate():
        for name in page.get("StreamNames", []):
            streams.append({
                "type": "kinesis_stream",
                "name": name,
            })
    return streams


def discover_firehose_streams(session) -> list:
    client = session.client("firehose")
    response = client.list_delivery_streams()
    streams = []
    for name in response.get("DeliveryStreamNames", []):
        streams.append({
            "type": "firehose",
            "name": name,
        })
    return streams


def discover_s3_buckets(session) -> list:
    client = session.client("s3")
    response = client.list_buckets()
    buckets = []
    for bucket in response.get("Buckets", []):
        buckets.append({
            "type": "s3",
            "name": bucket["Name"],
            "arn": f"arn:aws:s3:::{bucket['Name']}",
        })
    return buckets
    
def discover_ec2_instances(session, tag_filter: dict = None) -> list:
    client = session.client("ec2")
    paginator = client.get_paginator("describe_instances")
    filters = [{"Name": "instance-state-name", "Values": ["running"]}]
    if tag_filter:
        filters.append({
            "Name": f"tag:{tag_filter['key']}",
            "Values": [tag_filter["value"]],
        })
    instances = []
    for page in paginator.paginate(Filters=filters):
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:
                # Use Name tag if present, otherwise instance ID
                name = instance["InstanceId"]
                for tag in instance.get("Tags", []):
                    if tag["Key"] == "Name":
                        name = tag["Value"]
                        break
            instances.append({
                "type": "rds",
                "name": db["DBInstanceIdentifier"],
                "engine": db.get("Engine", "unknown"),
                "arn": db.get("DBInstanceArn", ""),
            })
    return instances


def discover_rds_instances(session) -> list:
    client = session.client("rds")
    paginator = client.get_paginator("describe_db_instances")
    instances = []
    for page in paginator.paginate():
        for db in page["DBInstances"]:
            instances.append({
                "type": "rds",
                "name": db["DBInstanceIdentifier"],
                "engine": db.get("Engine", "unknown"),
            })
    return instances
    
def filter_by_tag(resources: list, tag_key: str, tag_value: str,
                  session) -> list:
    """
    Filter a list of discovered resources by tag, for resource types
    that don't support tag filtering natively in their list/describe APIs.
    Uses the Resource Groups Tagging API which works across most AWS services.
    """
    client = session.client("resourcegroupstaggingapi")
    paginator = client.get_paginator("get_resources")

    tagged_arns = set()
    for page in paginator.paginate(
        TagFilters=[{"Key": tag_key, "Values": [tag_value]}]
    ):
        for resource in page["ResourceTagMappingList"]:
            tagged_arns.add(resource["ResourceARN"])

    # Keep resources whose ARN appears in the tagged set,
    # or resources without an ARN field (keep them and let discovery handle it)
    return [r for r in resources if r.get("arn") in tagged_arns]


def discover_all(resource_types: list = None,
                 tag_key: str = None, tag_value: str = None) -> list:
    """
    Discover all supported resource types (or a filtered subset).
    resource_types: list of strings e.g. ["lambda", "firehose"]
                   None means discover everything.
    tag_key/tag_value: if both provided, filter results to only resources
                       with this tag.
    """
    session = get_session()
    tag_filter = {"key": tag_key, "value": tag_value} if tag_key and tag_value else None
    all_types = {
        "lambda": discover_lambda_functions,
        "kinesis_stream": discover_kinesis_streams,
        "firehose": discover_firehose_streams,
        "s3": discover_s3_buckets,
        "ec2": discover_ec2_instances,
        "rds": discover_rds_instances,
    }

    if resource_types:
        selected = {k: v for k, v in all_types.items() if k in resource_types}
    else:
        selected = all_types

    resources = []
    for rtype, fn in selected.items():
        try:
            # EC2 supports native tag filtering; others use post-filter
            if rtype == "ec2" and tag_filter:
                found = fn(session, tag_filter=tag_filter)
            else:
                found = fn(session)
            resources.extend(found)
            print(f"  {rtype}: {len(found)} found")
        except Exception as e:
            print(f"  {rtype}: error — {e}")

    if tag_key and tag_value and resources:
        print(f"  Filtering by tag {tag_key}={tag_value}...")
        resources = filter_by_tag(resources, tag_key, tag_value, session)
        print(f"  {len(resources)} resources match the tag filter.")

    return resources


if __name__ == "__main__":
    print("Discovering AWS resources...")
    resources = discover_all()
    print(f"\nTotal: {len(resources)} resources found")
    for r in resources:
        print(f"  [{r['type']}] {r['name']}")