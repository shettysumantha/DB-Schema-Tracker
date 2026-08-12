import csv
from pathlib import Path
from typing import List, Dict, Any
import os


class LocalSheetsClient:
    def __init__(self, out_dir: str = "local_docs"):
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def list_sheets(self) -> List[str]:
        names = []
        for f in self.out_dir.glob("*.csv"):
            names.append(f.stem)
        return names

    def read_sheet_rows(self, title: str) -> List[Dict[str, Any]]:
        path = self.out_dir / f"{title}.csv"
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            return [r for r in reader]

    def update_table_sheet(self, table: str, columns: List[Dict[str, Any]]):
        path = self.out_dir / f"{table}.csv"
        header = [
            "Column Name",
            "Data Type",
            "Nullable",
            "Primary Key",
            "Foreign Key",
            "Referenced Table",
            "Referenced Column",
            "Default Value",
            "Description",
        ]
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(header)
            for c in sorted(columns, key=lambda x: x.get("ordinal_position", 0)):
                fk = c.get("foreign_key") or {}
                writer.writerow(
                    [
                        c.get("column_name"),
                        c.get("data_type"),
                        "YES" if c.get("is_nullable") else "NO",
                        "YES" if c.get("is_primary") else "",
                        fk.get("constraint_name") if fk else "",
                        fk.get("referenced_table") if fk else "",
                        fk.get("referenced_column") if fk else "",
                        c.get("column_default") if c.get("column_default") is not None else "",
                        c.get("column_comment") if c.get("column_comment") is not None else "",
                    ]
                )

    def update_table_index(self, index_rows: List[List[Any]]):
        path = self.out_dir / "Table_Index.csv"
        header = ["Table Name", "Description", "Number of Columns", "Primary Key", "Last Synchronized"]
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(header)
            for r in index_rows:
                writer.writerow(r)

    def delete_sheet(self, title: str):
        path = self.out_dir / f"{title}.csv"
        if path.exists():
            path.unlink()

    def update_table_relationships(self, rel_rows: List[List[Any]]):
        path = self.out_dir / "Table_Relationships.csv"
        header = ["Source Table", "Source Column", "Target Table", "Target Column", "Constraint Name"]
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(header)
            for r in rel_rows:
                writer.writerow(r)

    def update_readme(self, text_lines: List[str]):
        path = self.out_dir / "README.txt"
        with path.open("w", encoding="utf-8") as fh:
            for l in text_lines:
                fh.write(l + os.linesep)
