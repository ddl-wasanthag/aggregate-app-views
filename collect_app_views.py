"""
Domino App Views Collector
--------------------------
Scheduled job that runs every 30 days.
Fetches all app views from the Domino API and appends a snapshot to the
cumulative CSV at /domino/datasets/local/$DOMINO_PROJECT_NAME/app_views.csv

Each row represents one app's views for the 30-day window ending on snapshot_date.
"""

import os
import csv
import requests
from datetime import date

# --- Config ---
API_BASE = os.environ["DOMINO_API_PROXY"]
PROJECT_NAME = os.environ["DOMINO_PROJECT_NAME"]
DATASET_PATH = f"/domino/datasets/local/{PROJECT_NAME}"
CSV_FILE = os.path.join(DATASET_PATH, "app_views.csv")
CSV_HEADERS = ["snapshot_date", "app_id", "app_name", "owner", "visibility", "views"]
PAGE_SIZE = 100


def fetch_json(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def get_all_apps():
    """Fetch all apps with pagination."""
    apps = []
    offset = 0

    while True:
        url = (
            f"{API_BASE}/api/apps/beta/apps"
            f"?sortField=name&sortOrder=asc&limit={PAGE_SIZE}&offset={offset}"
        )
        data = fetch_json(url)
        items = data.get("items", [])
        apps.extend(items)

        # Stop if we got fewer items than page size (last page)
        if len(items) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    return apps


def extract_row(app, snapshot_date):
    return {
        "snapshot_date": snapshot_date,
        "app_id": app.get("id", ""),
        "app_name": app.get("name", ""),
        "owner": app.get("project", {}).get("ownerUsername", ""),
        "visibility": app.get("visibility", ""),
        "views": app.get("views", 0),
    }


def append_to_csv(rows):
    os.makedirs(DATASET_PATH, exist_ok=True)
    file_exists = os.path.isfile(CSV_FILE)

    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

    print(f"Appended {len(rows)} rows to {CSV_FILE}")


def main():
    snapshot_date = date.today().isoformat()
    print(f"Collecting app views snapshot for {snapshot_date}...")

    apps = get_all_apps()
    print(f"Found {len(apps)} apps")

    rows = [extract_row(app, snapshot_date) for app in apps]
    append_to_csv(rows)

    print("Done.")


if __name__ == "__main__":
    main()
