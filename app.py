"""
CloudWatch Dashboard Builder — Streamlit UI.

Select resource types, preview the widget plan, and deploy or
export a CloudWatch dashboard in one click.

Usage:
    streamlit run app.py
"""

import json
import sys
sys.path.insert(0, ".")

import streamlit as st
from src.discovery import discover_all
from src.builder import build_dashboard, deploy_dashboard, export_dashboard

st.set_page_config(
    page_title="CloudWatch Dashboard Builder",
    page_icon="📊",
    layout="wide",
)

st.title("📊 CloudWatch Dashboard Builder")
st.caption("Auto-generate CloudWatch dashboards from your AWS resources.")

# Sidebar controls
with st.sidebar:
    st.header("Settings")
    dashboard_name = st.text_input("Dashboard name", value="AutoDashboard")
    resource_types = st.multiselect(
        "Resource types to include",
        options=["lambda", "kinesis_stream", "firehose", "s3", "ec2", "rds"],
        default=["lambda", "firehose"],
    )
    tag_key = st.text_input("Filter by tag key (optional)", placeholder="e.g. Project")
    tag_value = st.text_input("Filter by tag value (optional)", placeholder="e.g. churn-mlops")
    st.divider()
    discover_btn = st.button("Discover Resources", type="primary", use_container_width=True)
    tag_key = st.text_input("Filter by tag key (optional)", placeholder="e.g. Project")
    tag_value = st.text_input("Filter by tag value (optional)", placeholder="e.g. churn-mlops")

# Main area
col1, col2 = st.columns([1, 1])

if discover_btn:
    with st.spinner("Scanning your AWS account..."):
        tag_k = tag_key.strip() or None
        tag_v = tag_value.strip() or None
        resources = discover_all(resource_types if resource_types else None,
                                 tag_key=tag_k, tag_value=tag_v)

    st.session_state["resources"] = resources
    st.session_state["dashboard_body"] = build_dashboard(
        dashboard_name, resource_types or None, tag_key=tag_k, tag_value=tag_v)

if "resources" in st.session_state:
    resources = st.session_state["resources"]
    dashboard_body = st.session_state["dashboard_body"]

    with col1:
        st.subheader(f"Discovered Resources ({len(resources)})")
        by_type = {}
        for r in resources:
            by_type.setdefault(r["type"], []).append(r["name"])
        for rtype, names in by_type.items():
            with st.expander(f"{rtype} ({len(names)})"):
                for name in names:
                    st.markdown(f"- `{name}`")

    with col2:
        st.subheader(f"Dashboard Preview ({len(dashboard_body['widgets'])} widgets)")
        for w in dashboard_body["widgets"]:
            st.markdown(f"- **{w['properties']['title']}**")

    st.divider()
    col_deploy, col_export = st.columns(2)

    with col_deploy:
        if st.button("Deploy to CloudWatch", type="primary", use_container_width=True):
            with st.spinner("Deploying..."):
                deploy_dashboard(dashboard_name, dashboard_body)
            st.success(f"Dashboard '{dashboard_name}' deployed!")
            st.markdown(
                f"[Open in CloudWatch](https://us-east-1.console.aws.amazon.com/cloudwatch/home?"
                f"region=us-east-1#dashboards:name={dashboard_name})"
            )

    with col_export:
        json_str = json.dumps(dashboard_body, indent=2)
        st.download_button(
            label="Export JSON",
            data=json_str,
            file_name=f"{dashboard_name}.json",
            mime="application/json",
            use_container_width=True,
        )
else:
    st.info("Click **Discover Resources** in the sidebar to get started.")