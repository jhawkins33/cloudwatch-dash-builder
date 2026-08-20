"""
Defines which CloudWatch metrics to include per resource type,
and generates CloudWatch dashboard widget definitions (JSON).

Each widget is a dict following the CloudWatch dashboard JSON format.
Reference: https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/CloudWatch-Dashboard-Body-Structure.html
"""

# Dashboard layout constants
WIDGET_WIDTH = 12   # half-width (dashboard is 24 units wide)
WIDGET_HEIGHT = 6


def _metric_widget(title, metrics, region, x, y,
                   width=WIDGET_WIDTH, height=WIDGET_HEIGHT,
                   period=300, stat="Average"):
    """Build a single CloudWatch metric widget dict."""
    return {
        "type": "metric",
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "properties": {
            "title": title,
            "metrics": metrics,
            "period": period,
            "stat": stat,
            "region": region,
            "view": "timeSeries",
            "stacked": False,
        },
    }


def widgets_for_lambda(resource: dict, region: str, x: int, y: int) -> list:
    """Generate widgets for a Lambda function."""
    name = resource["name"]
    dim = [["FunctionName", name]]
    ns = "AWS/Lambda"
    return [
        _metric_widget(
            f"Lambda: {name} — Invocations & Errors",
            [
                [ns, "Invocations", "FunctionName", name, {"stat": "Sum", "label": "Invocations"}],
                [ns, "Errors", "FunctionName", name, {"stat": "Sum", "label": "Errors", "color": "#d62728"}],
            ],
            region, x, y, stat="Sum"
        ),
        _metric_widget(
            f"Lambda: {name} — Duration (ms)",
            [[ns, "Duration", "FunctionName", name]],
            region, x + WIDGET_WIDTH, y, stat="p99"
        ),
    ]


def widgets_for_kinesis_stream(resource: dict, region: str, x: int, y: int) -> list:
    """Generate widgets for a Kinesis Data Stream."""
    name = resource["name"]
    ns = "AWS/Kinesis"
    return [
        _metric_widget(
            f"Kinesis: {name} — Records",
            [
                [ns, "PutRecords.Records", "StreamName", name, {"stat": "Sum", "label": "Put Records"}],
                [ns, "GetRecords.Records", "StreamName", name, {"stat": "Sum", "label": "Get Records"}],
            ],
            region, x, y, stat="Sum"
        ),
        _metric_widget(
            f"Kinesis: {name} — Throttling",
            [
                [ns, "WriteProvisionedThroughputExceeded", "StreamName", name, {"stat": "Sum"}],
                [ns, "ReadProvisionedThroughputExceeded", "StreamName", name, {"stat": "Sum"}],
            ],
            region, x + WIDGET_WIDTH, y, stat="Sum"
        ),
    ]


def widgets_for_firehose(resource: dict, region: str, x: int, y: int) -> list:
    """Generate widgets for a Kinesis Firehose delivery stream."""
    name = resource["name"]
    ns = "AWS/Firehose"
    return [
        _metric_widget(
            f"Firehose: {name} — Delivery Success",
            [[ns, "DeliveryToS3.Success", "DeliveryStreamName", name, {"stat": "Sum"}]],
            region, x, y, stat="Sum"
        ),
        _metric_widget(
            f"Firehose: {name} — Data Freshness (sec)",
            [[ns, "DeliveryToS3.DataFreshness", "DeliveryStreamName", name]],
            region, x + WIDGET_WIDTH, y, stat="Maximum"
        ),
    ]


def widgets_for_s3(resource: dict, region: str, x: int, y: int) -> list:
    """Generate widgets for an S3 bucket."""
    name = resource["name"]
    ns = "AWS/S3"
    return [
        _metric_widget(
            f"S3: {name} — Requests",
            [
                [ns, "NumberOfObjects", "BucketName", name, "StorageType", "AllStorageTypes",
                 {"stat": "Average", "label": "Object Count"}],
                [ns, "BucketSizeBytes", "BucketName", name, "StorageType", "StandardStorage",
                 {"stat": "Average", "label": "Bucket Size (bytes)"}],
            ],
            region, x, y
        ),
    ]


WIDGET_GENERATORS = {
    "lambda": widgets_for_lambda,
    "kinesis_stream": widgets_for_kinesis_stream,
    "firehose": widgets_for_firehose,
    "s3": widgets_for_s3,
}


def generate_widgets(resources: list, region: str) -> list:
    """
    Generate all dashboard widgets for a list of discovered resources.
    Lays them out in a 2-column grid (24 units wide, each widget 12 wide).
    """
    widgets = []
    y = 0
    col = 0

    for resource in resources:
        rtype = resource["type"]
        if rtype not in WIDGET_GENERATORS:
            continue

        x = col * WIDGET_WIDTH
        new_widgets = WIDGET_GENERATORS[rtype](resource, region, x, y)
        widgets.extend(new_widgets)

        # Advance layout — each resource gets a full row
        y += WIDGET_HEIGHT
        col = 0  # reset to left column for next resource

    return widgets