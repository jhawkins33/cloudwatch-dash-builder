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
        })
    return buckets


def discover_all(resource_types: list = None) -> list:
    """
    Discover all supported resource types (or a filtered subset).
    resource_types: list of strings e.g. ["lambda", "firehose"]
                   None means discover everything.
    """
    session = get_session()
    all_types = {
        "lambda": discover_lambda_functions,
        "kinesis_stream": discover_kinesis_streams,
        "firehose": discover_firehose_streams,
        "s3": discover_s3_buckets,
    }

    if resource_types:
        selected = {k: v for k, v in all_types.items() if k in resource_types}
    else:
        selected = all_types

    resources = []
    for rtype, fn in selected.items():
        try:
            found = fn(session)
            resources.extend(found)
            print(f"  {rtype}: {len(found)} found")
        except Exception as e:
            print(f"  {rtype}: error — {e}")

    return resources


if __name__ == "__main__":
    print("Discovering AWS resources...")
    resources = discover_all()
    print(f"\nTotal: {len(resources)} resources found")
    for r in resources:
        print(f"  [{r['type']}] {r['name']}")