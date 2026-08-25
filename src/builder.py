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


def build_dashboard(name: str, resource_types: list = None,
                    tag_key: str = None, tag_value: str = None) -> dict:
    """Discover resources and generate a dashboard body dict."""
    from src.discovery import discover_all
    from src.widgets import generate_widgets

    print(f"Discovering resources...")
    resources = discover_all(resource_types, tag_key=tag_key, tag_value=tag_value)
    print(f"Found {len(resources)} resources.")

    print(f"Generating widgets...")
    widgets = generate_widgets(resources, REGION)
    print(f"Generated {len(widgets)} widgets.")

    dashboard_body = {"widgets": widgets}
    return dashboard_body
    
def get_dashboard(name: str) -> dict | None:
    """
    Fetch an existing CloudWatch dashboard by name.
    Returns the parsed dashboard body dict, or None if it doesn't exist.
    """
    session = boto3.Session(profile_name=PROFILE, region_name=REGION)
    cw = session.client("cloudwatch")
    try:
        response = cw.get_dashboard(DashboardName=name)
        return json.loads(response["DashboardBody"])
    except cw.exceptions.DashboardNotFoundError:
        return None


def merge_widgets(existing_body: dict, new_body: dict) -> dict:
    """
    Merge new widgets into an existing dashboard.
    - Widgets with the same title as an existing widget replace it.
    - Widgets with new titles are appended.
    - Widgets in the existing dashboard not touched by the new set are kept.
    """
    existing_widgets = existing_body.get("widgets", [])
    new_widgets = new_body.get("widgets", [])

    # Index existing widgets by title for fast lookup
    existing_by_title = {
        w["properties"]["title"]: w
        for w in existing_widgets
        if "properties" in w and "title" in w["properties"]
    }

    new_titles = {
        w["properties"]["title"]
        for w in new_widgets
        if "properties" in w and "title" in w["properties"]
    }

    # Keep existing widgets that aren't being replaced
    kept = [w for w in existing_widgets
            if w.get("properties", {}).get("title") not in new_titles]

    merged = kept + new_widgets
    print(f"  Merge: {len(kept)} existing kept, {len(new_widgets)} new/updated, "
          f"{len(merged)} total widgets.")
    return {"widgets": merged}


def deploy_dashboard(name: str, dashboard_body: dict, update: bool = False):
    """
    Deploy the dashboard to CloudWatch.
    update=True: merge new widgets into the existing dashboard (preserving
                 any manual customizations) rather than replacing it entirely.
    update=False: replace the dashboard wholesale (default).
    """
    if update:
        existing = get_dashboard(name)
        if existing:
            print(f"Updating existing dashboard '{name}'...")
            dashboard_body = merge_widgets(existing, dashboard_body)
        else:
            print(f"Dashboard '{name}' not found — creating fresh.")

    session = boto3.Session(profile_name=PROFILE, region_name=REGION)
    cw = session.client("cloudwatch")
    cw.put_dashboard(
        DashboardName=name,
        DashboardBody=json.dumps(dashboard_body),
    )
    action = "updated" if update else "deployed"
    print(f"Dashboard '{name}' {action} in CloudWatch.")
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
    parser.add_argument("--tag-key", default=None, help="Filter by tag key (e.g. Project)")
    parser.add_argument("--tag-value", default=None, help="Filter by tag value (e.g. churn-mlops)")
    parser.add_argument("--deploy", action="store_true", help="Deploy dashboard to CloudWatch")
    parser.add_argument("--update", action="store_true", help="Merge into existing dashboard instead of replacing")
    parser.add_argument("--output", default=None, help="Export dashboard JSON to this file")
    args = parser.parse_args()

    dashboard_body = build_dashboard(args.name, args.types,
                                     tag_key=args.tag_key, tag_value=args.tag_value)

    if args.output:
        export_dashboard(dashboard_body, args.output)

    if args.deploy:
        deploy_dashboard(args.name, dashboard_body, update=args.update)

    if not args.output and not args.deploy:
        print("\nDashboard JSON preview:")
        print(json.dumps(dashboard_body, indent=2)[:2000] + "...")
        print("\nUse --deploy to push to CloudWatch or --output <file> to save.")


if __name__ == "__main__":
    main()