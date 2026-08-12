import logging
from datetime import datetime

from config import DB_CONFIG, CASH_COUNTER_TABLES
from schema_analyzer import detect_cashcounter_tables, build_current_schema
from schema_comparator import compare_table_schema
from google_sheets import GoogleSheetsClient
from local_writer import LocalSheetsClient
import sys


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("sync")


def load_documented_columns(gs_client, table):
    rows = gs_client.read_sheet_rows(table)
    if not rows:
        return []
    result = []
    for r in rows:
        result.append(
            {
                "column_name": r.get("Column Name", "").strip(),
                "data_type": r.get("Data Type", "").strip(),
                "is_nullable": (r.get("Nullable", "").strip().upper() == "YES"),
                "column_default": r.get("Default Value", None) if r.get("Default Value", "") != "" else None,
                "column_comment": r.get("Description", ""),
                "is_primary": (r.get("Primary Key", "").strip().upper() == "YES"),
                "foreign_key": {
                    "constraint_name": r.get("Foreign Key", "") or None,
                    "referenced_table": r.get("Referenced Table", "") or None,
                    "referenced_column": r.get("Referenced Column", "") or None,
                }
                if r.get("Foreign Key", "")
                else None,
            }
        )
    return result


def main():
    start = datetime.now()
    try:
        gs = GoogleSheetsClient()
        mode = "google"
    except FileNotFoundError as e:
        logger.warning("%s", e)
        print()
        print("Google credentials not found — falling back to local CSV output in ./local_docs")
        gs = LocalSheetsClient(out_dir="local_docs")
        mode = "local"

    logger.info("Starting Cash Counter database schema synchronization (mode=%s)", mode)
    logger.info("Database: Host : %s  Database : %s", DB_CONFIG["host"], DB_CONFIG["database"]) 

    # detect tables
    detected = detect_cashcounter_tables()

    # Build current schema
    current_schema = build_current_schema(detected)

    # existing sheet tabs (use client's list_sheets to handle retries)
    existing_sheets = set(gs.list_sheets())
    if "Schema_Changes" in existing_sheets:
        try:
            gs.delete_sheet("Schema_Changes")
            existing_sheets.discard("Schema_Changes")
            logger.info("Removed legacy Schema_Changes sheet")
        except Exception:
            logger.exception("Unable to remove legacy Schema_Changes sheet")

    # track summary
    summary = {
        "tables_checked": len(detected),
        "new_tables": 0,
        "removed_tables": 0,
        "new_columns": 0,
        "removed_columns": 0,
        "modified_columns": 0,
        "pk_changes": 0,
        "fk_changes": 0,
    }

    # handle new tables and updates
    for table, cols in current_schema.items():
        if table not in existing_sheets:
            summary["new_tables"] += 1

        # load documented columns
        old_cols = load_documented_columns(gs, table)

        comp = compare_table_schema(old_cols, cols)
        for c in comp.get("added", []):
            summary["new_columns"] += 1
        for c in comp.get("removed", []):
            summary["removed_columns"] += 1
        for m in comp.get("modified", []):
            summary["modified_columns"] += 1

        # write current table sheet (representing current schema)
        gs.update_table_sheet(table, cols)

    # detect removed tables (present in sheets but not in current schema or special tabs)
    protected = {"Table_Index", "Table_Relationships", "README"}
    doc_tables = {t for t in existing_sheets if t not in protected}
    for t in doc_tables:
        if t not in current_schema:
            summary["removed_tables"] += 1

    # Update Table_Index
    index_rows = []
    for table, cols in current_schema.items():
        pk_cols = [c["column_name"] for c in cols if c.get("is_primary")]
        index_rows.append([table, "", len(cols), ",".join(pk_cols), datetime.now().isoformat()])
    gs.update_table_index(index_rows)

    # Update Table_Relationships
    rel_rows = []
    for table, cols in current_schema.items():
        for c in cols:
            fk = c.get("foreign_key")
            if fk:
                rel_rows.append([table, c.get("column_name"), fk.get("referenced_table"), fk.get("referenced_column"), fk.get("constraint_name")])
    gs.update_table_relationships(rel_rows)

    # Update README
    readme = [
        "Cash Counter – Database Documentation",
        "",
        f"Database Host: {DB_CONFIG['host']}",
        f"Database Name: {DB_CONFIG['database']}",
        "Module: Cash Counter",
        "",
        "Tables:",
    ]
    readme.extend([f"- {t}" for t in sorted(current_schema.keys())])
    readme.extend(["", f"Last synchronization: {datetime.now().isoformat()}"])
    gs.update_readme(readme)

    # print summary
    print("==================================================")
    print(" CASH COUNTER DATABASE SCHEMA SYNCHRONIZATION")
    print("==================================================")
    print()
    print("Database:")
    print(f"Host       : {DB_CONFIG['host']}")
    print(f"Database   : {DB_CONFIG['database']}")
    print("Module     : Cash Counter")
    print()
    print(f"Tables checked       : {summary['tables_checked']}")
    print(f"New tables           : {summary['new_tables']}")
    print(f"Removed tables       : {summary['removed_tables']}")
    print(f"New columns          : {summary['new_columns']}")
    print(f"Removed columns      : {summary['removed_columns']}")
    print(f"Modified columns     : {summary['modified_columns']}")
    print()
    print("Google Spreadsheet:")
    print("Cash Counter – Database Documentation")
    print()
    print("Status: SUCCESS")
    print()
    print("Synchronization completed:")
    print(datetime.now().isoformat())
    print("==================================================")


if __name__ == "__main__":
    main()
