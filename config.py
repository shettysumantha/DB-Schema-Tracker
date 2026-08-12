from pathlib import Path
from typing import List

# File storage for saved database connections and job artifacts
CONNECTIONS_FILE = Path("connections.json")
JOBS_FILE = Path("jobs.json")
DOWNLOADS_DIR = Path("downloads")

# Google Sheets configuration
# Replace with your spreadsheet id. Keep in one place.
GOOGLE_SHEET_ID = "1j1u_F3bwjTVEClpQWiRos8Tt6Ax8XuVxJUgMzkOGKBg"
# Path to the service account JSON file. Do NOT commit this file.
GOOGLE_CREDENTIALS_FILE = Path("google_credentials.json")

# Other settings
PUBLIC_SCHEMA = "public"

