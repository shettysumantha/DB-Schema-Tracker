# Cash Counter — Database Documentation Synchronizer

This tool extracts PostgreSQL schema metadata for the Cash Counter module and documents it into a Google Spreadsheet.

Usage

1. Place your Google service account JSON at `google_credentials.json` (do not commit it).
2. Update `config.py`:
   - Set `GOOGLE_SHEET_ID` to your spreadsheet id.
   - Keep `DB_CONFIG` as provided (do not log or display the password).
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run synchronization:

```bash
python sync_cashcounter_schema.py
```

What it does

- Reads PostgreSQL metadata using information_schema and pg_catalog
- Detects Cash Counter tables (seed list + tables containing 'cash' or 'counter')
- Compares current schema to documented sheets
- Updates or creates one sheet per table
- Removes legacy `Schema_Changes` sheet if present
- Maintains `Table_Index`, `Table_Relationships`, and `README`
- Formats header rows, freezes the header row, and applies banding/borders for readability

Security

- Do not commit `google_credentials.json`.
- The DB password is stored in `config.py` for convenience; avoid printing it.
