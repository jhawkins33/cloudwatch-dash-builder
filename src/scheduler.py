"""
Scheduled auto-refresh for CloudWatch dashboards.

Rebuilds and redeploys a dashboard on a configurable interval,
picking up new resources as they appear and removing stale ones.

Runs as a local process — for production use, wrap this logic in
a Lambda function triggered by EventBridge on a cron schedule.

Usage:
    python src/scheduler.py --name "AutoDashboard" --interval 300
    python src/scheduler.py --name "AutoDashboard" --types lambda ec2 --interval 60 --update
"""

import argparse
import signal
import sys
import time
from datetime import datetime

sys.path.insert(0, ".")
from src.builder import build_dashboard, deploy_dashboard


def run_scheduler(name: str, resource_types: list, interval: int,
                  tag_key: str, tag_value: str, update: bool):
    """
    Rebuild and redeploy the dashboard every `interval` seconds.
    Runs until interrupted with Ctrl+C.
    """
    print(f"Starting scheduler — rebuilding '{name}' every {interval}s.")
    print(f"Resource types: {resource_types or 'all'}")
    if tag_key and tag_value:
        print(f"Tag filter: {tag_key}={tag_value}")
    print(f"Update mode: {'on (merge)' if update else 'off (replace)'}")
    print("Press Ctrl+C to stop.\n")

    run_count = 0

    def handle_interrupt(sig, frame):
        print(f"\nScheduler stopped after {run_count} run(s).")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_interrupt)

    while True:
        run_count += 1
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] Run #{run_count} — discovering resources...")

        try:
            dashboard_body = build_dashboard(
                name,
                resource_types or None,
                tag_key=tag_key or None,
                tag_value=tag_value or None,
            )
            deploy_dashboard(name, dashboard_body, update=update)
            print(f"[{now}] Done. Next run in {interval}s.\n")
        except Exception as e:
            print(f"[{now}] Error: {e}. Retrying in {interval}s.\n")

        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="Auto-refresh CloudWatch dashboards on a schedule.")
    parser.add_argument("--name", default="AutoDashboard", help="Dashboard name")
    parser.add_argument("--types", nargs="*",
                        choices=["lambda", "kinesis_stream", "firehose", "s3", "ec2", "rds"],
                        help="Resource types to include (default: all)")
    parser.add_argument("--interval", type=int, default=300,
                        help="Rebuild interval in seconds (default: 300 = 5 minutes)")
    parser.add_argument("--tag-key", default=None, help="Filter by tag key")
    parser.add_argument("--tag-value", default=None, help="Filter by tag value")
    parser.add_argument("--update", action="store_true",
                        help="Merge into existing dashboard instead of replacing")
    args = parser.parse_args()

    run_scheduler(
        name=args.name,
        resource_types=args.types,
        interval=args.interval,
        tag_key=args.tag_key,
        tag_value=args.tag_value,
        update=args.update,
    )


if __name__ == "__main__":
    main()