"""
Domino App Views Collector
--------------------------
Scheduled job that runs every 30 days.
Fetches all apps and their per-user viewer data, producing two CSVs:

  app_views.csv   — one row per app per snapshot (summary)
  app_viewers.csv — one row per viewer per app per snapshot (detail)

Both written to /domino/datasets/local/$DOMINO_PROJECT_NAME/
"""

import os
import csv
import requests
from datetime import date

# --- Config ---
API_BASE = os.environ["DOMINO_API_PROXY"]
PROJECT_NAME = os.environ["DOMINO_PROJECT_NAME"]
DATASET_PATH = f"/domino/datasets/local/{PROJECT_NAME}"

APP_VIEWS_CSV = os.path.join(DATASET_PATH, "app_views.csv")
APP_VIEWERS_CSV = os.path.join(DATASET_PATH, "app_viewers.csv")

APP_VIEWS_HEADERS = ["snapshot_date", "app_id", "app_name", "owner", "visibility", "views"]
APP_VIEWERS_HEADERS = ["snapshot_date", "app_id", "app_name", "owner", "viewer_id", "viewer_full_name", "viewer_email", "views_30d"]

PAGE_SIZE = 100


def fetch_json(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


# --- Apps ---

def get_all_apps():
    """Fetch all apps with pagination using totalCount from response metadata."""
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
        offset += len(items)

        total_count = data.get("metadata", {}).get("totalCount")
        if total_count is not None:
            if offset >= total_count:
                break
        else:
            if len(items) < PAGE_SIZE:
                break

    return apps


def extract_app_row(app, snapshot_date):
    return {
        "snapshot_date": snapshot_date,
        "app_id": app.get("id", ""),
        "app_name": app.get("name", ""),
        "owner": app.get("project", {}).get("ownerUsername", ""),
        "visibility": app.get("visibility", ""),
        "views": app.get("views", 0),
    }


# --- Viewers ---

def build_user_cache():
    """Fetch all Domino users at once and return a {user_id: {full_name, email}} dict."""
    try:
        users = fetch_json(f"{API_BASE}/v4/users")
        return {
            u["id"]: {"full_name": u.get("fullName", ""), "email": u.get("email", "")}
            for u in users
            if "id" in u
        }
    except Exception as e:
        print(f"Warning: could not preload user list: {e}. Will fall back to user IDs.")
        return {}


def get_user_info(user_id, user_cache):
    info = user_cache.get(user_id, {})
    return info.get("full_name", user_id), info.get("email", "")


def get_app_viewers(app_id):
    """Return the top-level users dict {userId: viewCount} for the past 30 days."""
    url = f"{API_BASE}/api/apps/beta/apps/{app_id}/views"
    data = fetch_json(url)
    return data.get("users", {})


def extract_viewer_rows(app, snapshot_date, user_cache):
    app_id = app.get("id", "")
    app_name = app.get("name", "")
    owner = app.get("project", {}).get("ownerUsername", "")

    try:
        users = get_app_viewers(app_id)
    except Exception as e:
        print(f"  Warning: could not fetch viewers for '{app_name}' ({app_id}): {e}")
        return []

    rows = []
    for user_id, view_count in users.items():
        full_name, email = get_user_info(user_id, user_cache)
        rows.append({
            "snapshot_date": snapshot_date,
            "app_id": app_id,
            "app_name": app_name,
            "owner": owner,
            "viewer_id": user_id,
            "viewer_full_name": full_name,
            "viewer_email": email,
            "views_30d": view_count,
        })
    return rows


# --- CSV ---

def append_to_csv(csv_file, headers, rows):
    os.makedirs(DATASET_PATH, exist_ok=True)
    file_exists = os.path.isfile(csv_file)

    with open(csv_file, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


# --- Main ---

def main():
    snapshot_date = date.today().isoformat()
    print(f"Collecting app views snapshot for {snapshot_date}...")

    apps = get_all_apps()
    print(f"Found {len(apps)} apps. Loading user list...")

    user_cache = build_user_cache()
    print(f"Loaded {len(user_cache)} users. Fetching viewer data...")

    app_rows = []
    viewer_rows = []

    for i, app in enumerate(apps, 1):
        app_name = app.get("name") or app.get("id", "")
        print(f"  [{i}/{len(apps)}] {app_name}")

        app_rows.append(extract_app_row(app, snapshot_date))
        viewer_rows.extend(extract_viewer_rows(app, snapshot_date, user_cache))

    append_to_csv(APP_VIEWS_CSV, APP_VIEWS_HEADERS, app_rows)
    print(f"Appended {len(app_rows)} rows to {APP_VIEWS_CSV}")

    append_to_csv(APP_VIEWERS_CSV, APP_VIEWERS_HEADERS, viewer_rows)
    print(f"Appended {len(viewer_rows)} viewer rows to {APP_VIEWERS_CSV}")

    print("Done.")


if __name__ == "__main__":
    main()
