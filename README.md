# CloudWatch Dashboard Builder

Auto-generates CloudWatch dashboards from your AWS resources — no manual widget clicking required. Discovers Lambda functions, Kinesis streams, Firehose delivery streams, and S3 buckets, then builds and deploys a dashboard with the right metrics pre-wired for each resource type.

## Why

Anyone who's spun up a new AWS service knows the pain of manually building CloudWatch dashboards from scratch. This tool scans your account, knows which metrics matter per resource type, and deploys a complete dashboard in seconds.

## Architecture

```
User → Streamlit UI ─┐
User → CLI           ├→ Discovery → Widget generation → Dashboard JSON → CloudWatch API
```

## What's here

| Path | Purpose |
|---|---|
| `src/discovery.py` | Scans AWS account for Lambda, Kinesis, Firehose, and S3 resources |
| `src/widgets.py` | Defines which CloudWatch metrics matter per resource type |
| `src/builder.py` | Assembles widgets into a dashboard and deploys or exports it |
| `app.py` | Streamlit UI — select resource types, preview widgets, deploy or export |

## Supported resource types

| Type | Metrics |
|---|---|
| Lambda | Invocations, Errors, Duration (p99) |
| Kinesis Data Stream | Put/Get Records, throttling |
| Kinesis Firehose | Delivery success, data freshness lag |
| S3 | Object count, bucket size |
| EC2 | CPUUtilization, NetworkIn/Out |
| RDS | CPUUtilization, DatabaseConnections, ReadLatency, WriteLatency |

## Setup

**Prerequisites:** Python 3.12, AWS CLI configured with a named profile.

```bash
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt

cp .env.example .env
# edit .env with your AWS profile name
```

## Usage

User → Streamlit UI ─┐
User → CLI           ├→ Discovery → Widget generation → Dashboard JSON → CloudWatch API

**CLI:**
```bash
# Preview what would be generated
python src/builder.py --name "MyDashboard" --types lambda firehose

# Export to JSON for review
python src/builder.py --name "MyDashboard" --types lambda s3 --output dashboard.json

```bash
# Deploy directly to CloudWatch
python src/builder.py --name "MyDashboard" --deploy

# Update existing dashboard (merge, don't replace)
python src/builder.py --name "MyDashboard" --types ec2 --deploy --update

# Filter by tag
python src/builder.py --name "MyDashboard" --tag-key Project --tag-value churn-mlops --deploy
```

## Roadmap

- [x] Resource discovery (Lambda, Kinesis, Firehose, S3)
- [x] Per-resource metric widget generation
- [x] CloudWatch dashboard deployment via API
- [x] Streamlit UI with resource preview and one-click deploy
- [x] Add EC2 and RDS support
- [x] Filter resources by tag (e.g. only show resources tagged `Project=churn-mlops`)
- [x] Dashboard update mode (update existing rather than replace)
- [ ] Scheduled auto-refresh (rebuild dashboard as resources change)