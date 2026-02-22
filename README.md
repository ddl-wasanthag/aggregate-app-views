# Domino App Views Aggregator

Tracks and visualizes Domino web app views over time, beyond the 1-month limit of the Domino UI.

## How It Works

A scheduled job runs every 30 days and appends a snapshot of all app view counts to a single CSV. A Streamlit dashboard reads that CSV to display historical trends.

Since the Domino API returns cumulative (all-time) view counts, the dashboard computes the delta between consecutive snapshots to show views per 30-day period.

## Project Structure

```
app-views/
├── collect_app_views.py   # Scheduled job — fetches and saves app views
├── app.py                 # Streamlit dashboard
├── app.sh                 # Domino app entrypoint
└── requirements.txt       # Python dependencies
```

## CSV Schema

Stored at `/domino/datasets/local/$DOMINO_PROJECT_NAME/app_views.csv`

| Column | Description |
|--------|-------------|
| `snapshot_date` | Date the job ran (YYYY-MM-DD) |
| `app_id` | Domino app ID |
| `app_name` | App name |
| `owner` | Project owner username |
| `views` | Cumulative all-time view count at time of snapshot |

## Setup

### 1. Dataset
Use the default Domino dataset in your project. The script writes to:
```
/domino/datasets/local/$DOMINO_PROJECT_NAME/app_views.csv
```

### 2. Scheduled Job
- **File:** `collect_app_views.py`
- **Schedule:** Every 30 days
- **Environment:** Must have `requests` available (included in most Domino base environments)
- **Dataset:** Mount the dataset with read/write access

### 3. Streamlit App
- **Entry point:** `app.sh`
- **Environment:** Must include `streamlit` and `pandas` (see `requirements.txt`)
- **Dataset:** Mount the dataset with read access

## Dashboard Features

- **Total apps tracked** — distinct apps seen across all snapshots
- **Latest snapshot date** — when data was last collected
- **Total views (latest period)** — views across all apps in the most recent 30-day window
- **All-time views bar chart** — latest cumulative count per app
- **Monthly trend line chart** — views per period per app over time
- **Raw data table** — full snapshot history with both cumulative and period view counts

## Notes

- No API authentication is needed — the script runs inside Domino where auth is pre-configured via `DOMINO_API_PROXY`
- `DOMINO_PROJECT_NAME` is automatically set by Domino at runtime
- Running the collection job multiple times on the same day will append duplicate rows — schedule it to run once per period
