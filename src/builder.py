"""
Assembles discovered resources + widgets into a CloudWatch dashboard
and either deploys it to AWS or exports the JSON for review.

Usage:
    python src/builder.py --name "My Dashboard" --deploy
    python src/builder.py --name "My Dashboard" --output dashboard.json
    python src/builder.py --name "My Dashboard" --types lambda firehose
"""

import argparse
import json
import os
import sys
sys.path.insert(0, ".")
import boto3
from dotenv import load_dotenv

load_dotenv()

REGION = os.environ.get("AWS_REGION", "us-east-1")
PROFILE = os.environ.get("AWS_PROFILE", "churn-mlops-personal")


def build_dashboard(name: str, resource_types: list = None) -> dict:
    """Discover resources and generate a dashboard body dict."""
    from src.discovery import discover_all
    from src.widgets import generate_widgets

    print(f"Discovering resources...")
    resources = discover_all(resource_types)
    print(f"Found {len(resources)} resources.")

    print(f"Generating widgets...")
    widgets = generate_widgets(resources, REGION)
    print(f"Generated {len(widgets)} widgets.")

    dashboard_body = {"widgets": widgets}
    return dashboard_body


def deploy_dashboard(name: str, dashboard_body: dict):
    """Deploy the dashboard to CloudWatch."""
    session = boto3.Session(profile_name=PROFILE, region_name=REGION)
    cw = session.client("cloudwatch")

    cw.put_dashboard(
        DashboardName=name,
        DashboardBody=json.dumps(dashboard_body),
    )
    print(f"Dashboard '{name}' deployed to CloudWatch.")
    print(f"View at: https://{REGION}.console.aws.amazon.com/cloudwatch/home?region={REGION}#dashboards:name={name}")


def export_dashboard(dashboard_body: dict, output_path: str):
    """Export the dashboard JSON to a file."""
    with open(output_path, "w") as f:
        json.dump(dashboard_body, f, indent=2)
    print(f"Dashboard JSON exported to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Build and deploy CloudWatch dashboards.")
    parser.add_argument("--name", default="AutoDashboard", help="Dashboard name")
    parser.add_argument("--types", nargs="*",
                        choices=["lambda", "kinesis_stream", "firehose", "s3", "ec2", "rds"],
                        help="Resource types to include (default: all)")
    parser.add_argument("--deploy", action="store_true", help="Deploy dashboard to CloudWatch")
    parser.add_argument("--output", default=None, help="Export dashboard JSON to this file")
    args = parser.parse_args()

    dashboard_body = build_dashboard(args.name, args.types)

    if args.output:
        export_dashboard(dashboard_body, args.output)

    if args.deploy:
        deploy_dashboard(args.name, dashboard_body)

    if not args.output and not args.deploy:
        print("\nDashboard JSON preview:")
        print(json.dumps(dashboard_body, indent=2)[:2000] + "...")
        print("\nUse --deploy to push to CloudWatch or --output <file> to save.")


if __name__ == "__main__":
    main()