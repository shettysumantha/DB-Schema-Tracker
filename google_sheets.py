import gspread
import time
from gspread.exceptions import APIError
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from pathlib import Path

from config import GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_FILE

logger = logging.getLogger(__name__)


class GoogleSheetsClient:
    def __init__(self, creds_path: str | None = None):
        if creds_path is None:
            creds_path = str(GOOGLE_CREDENTIALS_FILE)
        creds = Path(creds_path)
        if not creds.exists():
            raise FileNotFoundError(
                f"Google credentials file not found: {creds.resolve()}.\n" \
                "Place your Google service account JSON at this path or update `GOOGLE_CREDENTIALS_FILE` in config.py."
            )
        self.client = gspread.service_account(filename=str(creds))
        self.spreadsheet = self.client.open_by_key(GOOGLE_SHEET_ID)

    def get_or_create_sheet(self, title: str, rows: int = 1000, cols: int = 20, create: bool = True):
        """Fetch worksheet with retries on API read/quota errors. If create=True, create when not found."""
        backoff = 1
        for attempt in range(8):
            try:
                ws = self.spreadsheet.worksheet(title)
                return ws
            except APIError as e:
                msg = str(e)
                if "429" in msg or "quota" in msg or "Rate" in msg:
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 30)
                    continue
                raise
            except gspread.WorksheetNotFound:
                if not create:
                    return None
                # try to create the sheet with backoff
                create_backoff = 1
                for c_attempt in range(6):
                    try:
                        ws = self.spreadsheet.add_worksheet(title=title, rows=str(rows), cols=str(cols))
                        return ws
                    except APIError as e:
                        msg = str(e)
                        if "429" in msg or "quota" in msg or "Rate" in msg:
                            time.sleep(create_backoff)
                            create_backoff = min(create_backoff * 2, 30)
                            continue
                        raise
                return self.spreadsheet.add_worksheet(title=title, rows=str(rows), cols=str(cols))

    def read_sheet_rows(self, title: str) -> List[Dict[str, Any]]:
        ws = self.get_or_create_sheet(title, create=False)
        if not ws:
            return []

        vals = ws.get_all_values()
        if not vals:
            return []
        headers = vals[0]
        rows = []
        for r in vals[1:]:
            row = {headers[i]: (r[i] if i < len(r) else "") for i in range(len(headers))}
            rows.append(row)
        return rows

    def update_table_sheet(self, table: str, columns: List[Dict[str, Any]]):
        ws = self.get_or_create_sheet(table)
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
        title_row = [f"Table Documentation - {table}"] + [""] * (len(header) - 1)
        rows = [title_row, header]
        for c in sorted(columns, key=lambda x: x.get("ordinal_position", 0)):
            fk = c.get("foreign_key") or {}
            rows.append(
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

        backoff = 1
        for attempt in range(6):
            try:
                ws.clear()
                ws.update(rows)
                break
            except APIError as e:
                msg = str(e)
                if "429" in msg or "quota" in msg or "Rate" in msg:
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 30)
                    continue
                raise
        self._format_sheet(ws, len(rows), len(header), header_color={"red": 0.16, "green": 0.32, "blue": 0.56})

    def _format_sheet(self, ws: Any, row_count: int, col_count: int, header_color: Dict[str, float]):
        if row_count < 1 or col_count < 1:
            return
        try:
            sheet_id = ws._properties["sheetId"]
            requests = [
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": sheet_id,
                            "gridProperties": {"frozenRowCount": 2},
                        },
                        "fields": "gridProperties.frozenRowCount",
                    }
                },
                {
                    "mergeCells": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": col_count},
                        "mergeType": "MERGE_ALL",
                    }
                },
                {
                    "repeatCell": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": col_count},
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {"red": 0.16, "green": 0.32, "blue": 0.56},
                                "horizontalAlignment": "CENTER",
                                "textFormat": {"bold": True, "fontSize": 12, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)",
                    }
                },
                {
                    "repeatCell": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 2, "startColumnIndex": 0, "endColumnIndex": col_count},
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": header_color,
                                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat)",
                    }
                },
                {
                    "autoResizeDimensions": {
                        "dimensions": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": col_count}
                    }
                },
                {
                    "updateBorders": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": row_count, "startColumnIndex": 0, "endColumnIndex": col_count},
                        "top": {"style": "SOLID", "width": 1, "color": {"red": 0.7, "green": 0.7, "blue": 0.7}},
                        "bottom": {"style": "SOLID", "width": 1, "color": {"red": 0.7, "green": 0.7, "blue": 0.7}},
                        "left": {"style": "SOLID", "width": 1, "color": {"red": 0.7, "green": 0.7, "blue": 0.7}},
                        "right": {"style": "SOLID", "width": 1, "color": {"red": 0.7, "green": 0.7, "blue": 0.7}},
                        "innerHorizontal": {"style": "SOLID", "width": 1, "color": {"red": 0.9, "green": 0.9, "blue": 0.9}},
                        "innerVertical": {"style": "SOLID", "width": 1, "color": {"red": 0.9, "green": 0.9, "blue": 0.9}},
                    }
                },
            ]
            self.spreadsheet.batch_update({"requests": requests})

            if row_count > 2:
                banding = {
                    "addBanding": {
                        "bandedRange": {
                            "range": {"sheetId": sheet_id, "startRowIndex": 2, "endRowIndex": row_count, "startColumnIndex": 0, "endColumnIndex": col_count},
                            "rowProperties": {
                                "firstBandColor": {"red": 0.96, "green": 0.96, "blue": 0.96},
                                "secondBandColor": {"red": 1, "green": 1, "blue": 1},
                            },
                        }
                    }
                }
                try:
                    self.spreadsheet.batch_update({"requests": [banding]})
                except APIError as e:
                    msg = str(e)
                    if "already has alternating background colors" not in msg:
                        raise
        except Exception:
            logger.exception("Failed to apply formatting to sheet %s", ws.title)

    def update_table_index(self, index_rows: List[List[Any]]):
        ws = self.get_or_create_sheet("Table_Index")
        header = ["Table Name", "Description", "Number of Columns", "Primary Key", "Last Synchronized"]
        rows = [header] + index_rows
        backoff = 1
        for attempt in range(6):
            try:
                ws.clear()
                ws.update(rows)
                break
            except APIError as e:
                msg = str(e)
                if "429" in msg or "quota" in msg or "Rate" in msg:
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 30)
                    continue
                raise
        self._format_sheet(ws, len(rows), len(header), header_color={"red": 0.16, "green": 0.32, "blue": 0.56})

    def update_table_relationships(self, rel_rows: List[List[Any]]):
        ws = self.get_or_create_sheet("Table_Relationships")
        header = ["Source Table", "Source Column", "Target Table", "Target Column", "Constraint Name"]
        rows = [header] + rel_rows
        backoff = 1
        for attempt in range(6):
            try:
                ws.clear()
                ws.update(rows)
                break
            except APIError as e:
                msg = str(e)
                if "429" in msg or "quota" in msg or "Rate" in msg:
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 30)
                    continue
                raise
        self._format_sheet(ws, len(rows), len(header), header_color={"red": 0.16, "green": 0.32, "blue": 0.56})

    def update_readme(self, text_lines: List[str]):
        ws = self.get_or_create_sheet("README")
        ws.clear()
        # write as rows
        rows = [[l] for l in text_lines]
        backoff = 1
        for attempt in range(6):
            try:
                ws.update(rows)
                break
            except APIError as e:
                msg = str(e)
                if "429" in msg or "quota" in msg or "Rate" in msg:
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 30)
                    continue
                raise

    def list_sheets(self) -> List[str]:
        backoff = 1
        for attempt in range(8):
            try:
                sheets = self.spreadsheet.worksheets()
                return [s.title for s in sheets]
            except APIError as e:
                msg = str(e)
                if "429" in msg or "quota" in msg or "Rate" in msg:
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 30)
                    continue
                raise
        sheets = self.spreadsheet.worksheets()
        return [s.title for s in sheets]

    def delete_sheet(self, title: str):
        ws = self.get_or_create_sheet(title, create=False)
        if not ws:
            return
        try:
            self.spreadsheet.del_worksheet(ws)
        except APIError:
            logger.exception("Failed to delete sheet %s", title)

    def update_documentation(self, connection_name: str, schema_map: Dict[str, List[Dict[str, Any]]]):
        readme_lines = [
            "Database Schema Documentation",
            "",
            f"Connection: {connection_name}",
            "",
            "This spreadsheet contains generated schema documentation for the selected tables.",
            "",
            "Included tables:",
        ]
        for table_name in sorted(schema_map.keys()):
            readme_lines.append(f"- {table_name}")

        self.update_readme(readme_lines)

        index_rows = []
        rel_rows = []
        for table_name, columns in schema_map.items():
            pk_columns = [c["column_name"] for c in columns if c.get("is_primary")]
            fk_columns = [c["column_name"] for c in columns if c.get("foreign_key")]
            index_rows.append([
                table_name,
                "",
                len(columns),
                ", ".join(pk_columns) if pk_columns else "-",
                ", ".join(fk_columns) if fk_columns else "-",
            ])
            for c in columns:
                fk = c.get("foreign_key")
                if fk:
                    rel_rows.append([
                        table_name,
                        c.get("column_name"),
                        fk.get("referenced_table"),
                        fk.get("referenced_column"),
                        fk.get("constraint_name"),
                    ])

        self.update_table_index(index_rows)
        self.update_table_relationships(rel_rows)

        for table_name, columns in schema_map.items():
            self.update_table_sheet(table_name, columns)
