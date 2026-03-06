"""
Domino App Views Dashboard
--------------------------
Streamlit app that reads the accumulated app_views.csv from the Domino dataset
and displays historical app view trends.

The CSV stores cumulative (all-time) view counts from the API.
Views per period are computed as the delta between consecutive snapshots per app.
"""

import os
import pandas as pd
import streamlit as st

# --- Config ---
PROJECT_NAME = os.environ.get("DOMINO_PROJECT_NAME", "")
CSV_FILE = f"/domino/datasets/local/{PROJECT_NAME}/app_views.csv"

VISIBILITY_LABELS = {
    "PUBLIC": "Public (Anonymous Access)",
    "AUTHENTICATED": "Authenticated (Anyone with an account)",
    "GRANT_BASED": "Grant-Based (Invited users, others may request)",
    "GRANT_BASED_STRICT": "Grant-Based Strict (Invited users only)",
}

st.set_page_config(page_title="App Views Dashboard", layout="wide")
st.title("Domino App Views Dashboard")


def load_data(path):
    """Read CSV fresh on every call — no caching."""
    df = pd.read_csv(path, parse_dates=["snapshot_date"])
    df = df.sort_values(["app_id", "snapshot_date"])

    # Compute views per period as delta between consecutive snapshots per app.
    # First snapshot for each app has no prior value, so delta = views itself.
    df["views_period"] = df.groupby("app_id")["views"].diff().fillna(df["views"])
    df["views_period"] = df["views_period"].clip(lower=0).astype(int)

    df["visibility_label"] = df["visibility"].map(VISIBILITY_LABELS).fillna(df["visibility"])

    return df


# --- Load Data ---
if not os.path.isfile(CSV_FILE):
    st.warning(f"No data file found at `{CSV_FILE}`. Run the collection job first.")
    st.stop()

df = load_data(CSV_FILE)

# --- Sidebar Filters ---
st.sidebar.header("Filters")

all_owners = sorted(df["owner"].dropna().unique())
selected_owners = st.sidebar.multiselect("Owner", all_owners, default=all_owners)

all_apps = sorted(df[df["owner"].isin(selected_owners)]["app_name"].unique())
selected_apps = st.sidebar.multiselect("App", all_apps, default=all_apps)

all_visibility = sorted(df["visibility"].dropna().unique())
selected_visibility = st.sidebar.multiselect(
    "Visibility",
    options=all_visibility,
    default=all_visibility,
    format_func=lambda v: VISIBILITY_LABELS.get(v, v),
)

st.sidebar.divider()
st.sidebar.caption("**Visibility legend**")
for code, label in VISIBILITY_LABELS.items():
    st.sidebar.caption(f"- **{code}**: {label}")

filtered = df[
    df["owner"].isin(selected_owners)
    & df["app_name"].isin(selected_apps)
    & df["visibility"].isin(selected_visibility)
]

# --- Summary Metrics ---
latest_snapshot = filtered["snapshot_date"].max()
latest = filtered[filtered["snapshot_date"] == latest_snapshot]

col1, col2, col3 = st.columns(3)
col1.metric("Total Apps Tracked", filtered["app_id"].nunique())
col2.metric("Latest Snapshot", latest_snapshot.strftime("%Y-%m-%d") if pd.notna(latest_snapshot) else "N/A")
col3.metric("Total Views (Latest Period)", int(latest["views_period"].sum()))

st.divider()

# --- All-Time Views by App (latest cumulative value per app) ---
st.subheader("All-Time Views by App")
alltime = (
    filtered.sort_values("snapshot_date")
    .groupby("app_name")["views"]
    .last()
    .sort_values(ascending=False)
    .reset_index()
    .rename(columns={"app_name": "App", "views": "Total Views (All Time)"})
)
st.bar_chart(alltime.set_index("App"))

st.divider()

# --- Views Per Period Trend ---
st.subheader("Views Per Period (Monthly Trend)")
trend = (
    filtered.groupby(["snapshot_date", "app_name"])["views_period"]
    .sum()
    .reset_index()
    .pivot(index="snapshot_date", columns="app_name", values="views_period")
    .fillna(0)
)
st.line_chart(trend)

st.divider()

# --- Raw Data Table ---
st.subheader("Raw Data")
st.dataframe(
    filtered[["snapshot_date", "app_name", "owner", "visibility_label", "views", "views_period"]]
    .rename(columns={
        "visibility_label": "visibility",
        "views": "cumulative_views",
        "views_period": "period_views",
    })
    .sort_values(["snapshot_date", "app_name"], ascending=[False, True]),
    use_container_width=True,
)
