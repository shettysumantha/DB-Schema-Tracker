import logging
from datetime import datetime

from connection_manager import load_connections
from schema_analyzer import build_current_schema, list_database_tables
from google_sheets import GoogleSheetsClient
from local_writer import LocalSheetsClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("sync")


def main():
    connections = load_connections()
    if not connections:
        logger.error("No configured database connections found.")
        return

    connection = connections[0]
    try:
        gs = GoogleSheetsClient()
        mode = "google"
    except FileNotFoundError as e:
        logger.warning("%s", e)
        print()
        print("Google credentials not found — falling back to local CSV output in ./local_docs")
        gs = LocalSheetsClient(out_dir="local_docs")
        mode = "local"

    logger.info("Starting database schema synchronization (mode=%s)", mode)
    logger.info("Database: Host : %s  Database : %s", connection["host"], connection["database"])

    tables = list_database_tables(connection, limit=1000)
    current_schema = build_current_schema(connection, tables)
    existing_sheets = set(gs.list_sheets())
    protected = {"Table_Index", "Table_Relationships", "README"}
    doc_tables = {t for t in existing_sheets if t not in protected}

    index_rows = []
    rel_rows = []
    for table, cols in current_schema.items():
        pk_cols = [c["column_name"] for c in cols if c.get("is_primary")]
        index_rows.append([table, "", len(cols), ",".join(pk_cols), datetime.now().isoformat()])
        for c in cols:
            fk = c.get("foreign_key")
            if fk:
                rel_rows.append([table, c.get("column_name"), fk.get("referenced_table"), fk.get("referenced_column"), fk.get("constraint_name")])

    gs.update_table_index(index_rows)
    gs.update_table_relationships(rel_rows)

    readme = [
        "Database Schema Documentation",
        "",
        f"Database Host: {connection['host']}",
        f"Database Name: {connection['database']}",
        "",
        "Tables:",
    ]
    readme.extend([f"- {t}" for t in sorted(current_schema.keys())])
    readme.extend(["", f"Last synchronization: {datetime.now().isoformat()}"])
    gs.update_readme(readme)

    print("Synchronization completed")


if __name__ == "__main__":
    main()
