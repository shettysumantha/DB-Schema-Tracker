from pathlib import Path
from typing import List

# PostgreSQL configuration (single source of truth)
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "MyDatabase",
    "user": "postgres",
    "password": "Shetty123@",
}

# Initial Cash Counter table scope (seed list)
CASH_COUNTER_TABLES: List[str] = [
    "receipts",
    "receiptaccountheaddetails",
    "denomination",
    "denomination_details",
    "denomination_rejection_history",
    "device_types_master",
    "device_registration",
    "device_registration_status_log",
    "device_status",
    "t_cardinfo",
    "tblbank_carddetails",
    "tbl_cashcollection_details",
    "tbl_cashcollection_header",
    "tblautodebit_paymentlog",
    "counter_login",
    "cashcountertypes",
    "cash_counter_logs",
    "subcashcounter",
    "paymenttype",
]

# Google Sheets configuration
# Replace with your spreadsheet id. Keep in one place.
GOOGLE_SHEET_ID = "1j1u_F3bwjTVEClpQWiRos8Tt6Ax8XuVxJUgMzkOGKBg"
# Path to the service account JSON file. Do NOT commit this file.
GOOGLE_CREDENTIALS_FILE = Path("google_credentials.json")

# Other settings
PUBLIC_SCHEMA = "public"

# If True, detect additional tables whose names contain 'cash' or 'counter'.
# Set to False to restrict synchronization to the explicit `CASH_COUNTER_TABLES` list.
DETECT_EXTRA_TABLES = False

