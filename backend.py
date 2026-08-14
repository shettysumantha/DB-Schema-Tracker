import csv
import json
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

import openpyxl
import psycopg2
import xlrd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, validator

import connection_manager
import document_generator
import job_store
from database import get_table_columns, list_tables, search_tables, test_connection
from google_sheets import GoogleSheetsClient

app = FastAPI(title="Database Schema Documentation API", version="1.0")


@app.get("/")
def root() -> Dict[str, str]:
    return {"status": "ok", "message": "Backend is running", "docs": "/docs"}


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DatabaseConnectionCreate(BaseModel):
    id: Optional[str] = None
    name: str = Field(..., min_length=1)
    type: str = Field(...)
    host: str = Field(..., min_length=1)
    port: int = Field(default=5432)
    database: str = Field(..., min_length=1)
    username: str = Field(..., min_length=1)
    password: Optional[str] = Field(default="")
    schema: str = Field(default="public")

    @validator("name", "host", "database", "username", "password", "schema", pre=True)
    def strip_whitespace(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value

    @validator("type")
    def validate_db_type(cls, value: str) -> str:
        if value.lower() != "postgresql":
            raise ValueError("Only PostgreSQL is supported")
        return value.lower()


class TableDocumentationRequest(BaseModel):
    connection_id: str
    table_name: str


class UploadDocumentationRequest(BaseModel):
    connection_id: str


class JobStatusResponse(BaseModel):
    id: str
    type: str
    status: str
    connection_id: str
    tables: List[str]
    summary: Dict[str, Any]
    artifact: Dict[str, Any]
    errors: List[Any]
    created_at: str
    updated_at: str


@app.post("/api/databases/test")
def api_test_connection(connection: DatabaseConnectionCreate) -> Dict[str, Any]:
    try:
        test_connection(connection.dict())
        return {"ok": True, "message": "Database connection successful"}
    except psycopg2.Error:
        raise HTTPException(status_code=400, detail="Unable to connect to database. Please verify the connection details.")
    except Exception:
        raise HTTPException(status_code=400, detail="Unable to connect to database. Please verify the connection details.")


@app.post("/api/databases")
def api_save_database(connection: DatabaseConnectionCreate) -> Dict[str, Any]:
    try:
        test_connection(connection.dict())
        connection_record = connection_manager.save_connection(connection.dict())
        return connection_record
    except psycopg2.Error:
        raise HTTPException(status_code=400, detail="Unable to connect to database. Please verify the connection details.")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/databases")
def api_list_databases() -> List[Dict[str, Any]]:
    return connection_manager.list_connections()


@app.put("/api/databases/{connection_id}/connect")
def api_connect_database(connection_id: str) -> Dict[str, Any]:
    connection_record = connection_manager.get_connection_record(connection_id)
    if not connection_record:
        raise HTTPException(status_code=404, detail="Database connection not found")
    try:
        test_connection(connection_record)
        updated = connection_manager.set_connection_status(connection_id, True)
        return updated
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc) or "Unable to connect to database")


@app.put("/api/databases/{connection_id}/disconnect")
def api_disconnect_database(connection_id: str) -> Dict[str, Any]:
    try:
        return connection_manager.set_connection_status(connection_id, False)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.delete("/api/databases/{connection_id}")
def api_delete_database(connection_id: str) -> Dict[str, Any]:
    deleted = connection_manager.delete_connection(connection_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Database connection not found")
    return {"ok": True}


@app.get("/api/tables")
def api_list_tables(connection_id: str, q: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    connection_record = connection_manager.get_connection_record(connection_id)
    if not connection_record:
        raise HTTPException(status_code=404, detail="Database connection not found")
    if q:
        tables = search_tables(connection_record, q, exact=False, limit=limit)
    else:
        tables = list_tables(connection_record, limit=limit)
    return {"tables": tables}


@app.get("/api/tables/search")
def api_search_tables(connection_id: str, q: Optional[str] = None) -> Dict[str, Any]:
    if not q:
        return {"tables": []}
    connection_record = connection_manager.get_connection_record(connection_id)
    if not connection_record:
        raise HTTPException(status_code=404, detail="Database connection not found")
    tables = search_tables(connection_record, q)
    return {"tables": tables}


@app.get("/api/tables/{table_name}/schema")
def api_get_table_schema(table_name: str, connection_id: str) -> Dict[str, Any]:
    connection_record = connection_manager.get_connection_record(connection_id)
    if not connection_record:
        raise HTTPException(status_code=404, detail="Database connection not found")
    try:
        tables = search_tables(connection_record, table_name, exact=True)
        if table_name not in tables:
            raise HTTPException(status_code=404, detail="Table not found in selected database")
        columns = get_table_columns(connection_record, table_name)
        return {
            "table_name": table_name,
            "connection_name": connection_record["name"],
            "schema": connection_record.get("schema", "public"),
            "columns": columns,
            "column_count": len(columns),
        }
    except psycopg2.Error:
        raise HTTPException(status_code=500, detail="Unable to retrieve table schema")


@app.post("/api/documentation/table")
def api_document_single_table(request: TableDocumentationRequest) -> Dict[str, Any]:
    connection_record = connection_manager.get_connection_record(request.connection_id)
    if not connection_record:
        raise HTTPException(status_code=404, detail="Database connection not found")

    try:
        tables = search_tables(connection_record, request.table_name, exact=True)
        if request.table_name not in tables:
            raise HTTPException(status_code=404, detail="Table not found in selected database")
        columns = get_table_columns(connection_record, request.table_name)
        job = job_store.create_job("single", request.connection_id, [request.table_name])
        output_path = job_store.download_path(job["id"])
        document_generator.generate_excel_documentation({request.table_name: columns}, output_path, connection_record["name"])
        job_store.update_job(job["id"], status="completed", summary={"processed": 1, "not_found": 0}, artifact={"excel": str(output_path.name)})
        return {"job_id": job["id"], "download_url": f"/api/documentation/{job['id']}/download"}
    except psycopg2.Error:
        raise HTTPException(status_code=500, detail="Unable to retrieve table schema")
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to generate documentation")


def _load_table_names_from_csv(content: str) -> List[str]:
    reader = csv.DictReader(content.splitlines())
    if not reader.fieldnames:
        raise ValueError("Uploaded file does not contain a valid header row.")
    mapping = {field.strip().lower(): field for field in reader.fieldnames}
    accepted = ["table_name", "table", "tablename", "table name"]
    column_name = next((mapping[name] for name in accepted if name in mapping), None)
    if column_name is None:
        # If the file has only one column, assume that column contains table names
        if len(reader.fieldnames) == 1:
            column_name = reader.fieldnames[0]
        else:
            raise ValueError("Uploaded file does not contain a valid table name column.")
    result = [row[column_name].strip() for row in reader if row.get(column_name) and row[column_name].strip()]
    return result


def _load_table_names_from_excel(file_bytes: bytes, is_xls: bool = False) -> List[str]:
    if is_xls:
        workbook = xlrd.open_workbook(file_contents=file_bytes)
        sheet = workbook.sheet_by_index(0)
        rows = [sheet.row_values(i) for i in range(sheet.nrows)]
    else:
        workbook = openpyxl.load_workbook(BytesIO(file_bytes), read_only=True, data_only=True)
        sheet = workbook.active
        rows = [[cell.value for cell in row] for row in sheet.iter_rows(values_only=True)]
    if not rows:
        raise ValueError("Uploaded file is empty")
    headers = [str(cell).strip().lower() if cell is not None else "" for cell in rows[0]]
    accepted = ["table_name", "table", "tablename", "table name"]
    column_index = next((idx for idx, name in enumerate(headers) if name in accepted), None)
    if column_index is None and len(rows[0]) == 1:
        column_index = 0
    if column_index is None:
        raise ValueError("Uploaded file does not contain a valid table name column.")
    result = []
    for row in rows[1:]:
        if len(row) > column_index and row[column_index] is not None:
            value = str(row[column_index]).strip()
            if value:
                result.append(value)
    return result


@app.post("/api/documentation/upload")
def api_upload_documentation(connection_id: str, file: UploadFile = File(...)) -> Dict[str, Any]:
    connection_record = connection_manager.get_connection_record(connection_id)
    if not connection_record:
        raise HTTPException(status_code=404, detail="Database connection not found")

    try:
        raw_bytes = file.file.read()
        if file.filename.lower().endswith(".csv"):
            table_names = _load_table_names_from_csv(raw_bytes.decode("utf-8-sig"))
        elif file.filename.lower().endswith(".xlsx"):
            table_names = _load_table_names_from_excel(raw_bytes)
        elif file.filename.lower().endswith(".xls"):
            table_names = _load_table_names_from_excel(raw_bytes, is_xls=True)
        else:
            raise ValueError("Unsupported file type. Supported files: CSV, XLSX, XLS.")

        table_names = [name.strip() for name in table_names if name.strip()]
        table_names = list(dict.fromkeys(table_names))
        if not table_names:
            raise ValueError("Uploaded file does not contain any table names.")

        found = []
        not_found = []
        schema_map: Dict[str, Any] = {}
        for table_name in table_names:
            matches = search_tables(connection_record, table_name, exact=True)
            if table_name in matches:
                try:
                    schema_map[table_name] = get_table_columns(connection_record, table_name)
                    found.append(table_name)
                except Exception:
                    not_found.append(table_name)
            else:
                not_found.append(table_name)

        job = job_store.create_job("bulk", connection_id, table_names)
        output_path = job_store.download_path(job["id"])
        document_generator.generate_excel_documentation(schema_map, output_path, connection_record["name"])
        job_store.update_job(
            job["id"],
            status="completed",
            summary={
                "total": len(table_names),
                "processed": len(found),
                "not_found": len(not_found),
                "found": found,
                "not_found_list": not_found,
            },
            artifact={"excel": str(output_path.name)},
        )
        return {
            "job_id": job["id"],
            "summary": {
                "total": len(table_names),
                "processed": len(found),
                "not_found": len(not_found),
                "found": found,
                "not_found": not_found,
            },
            "download_url": f"/api/documentation/{job['id']}/download",
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=500, detail="Unable to process uploaded table list")


@app.get("/api/documentation/jobs")
def api_list_jobs() -> Dict[str, Any]:
    return {"jobs": job_store.list_jobs(20)}


@app.get("/api/documentation/{job_id}/status")
def api_job_status(job_id: str) -> JobStatusResponse:
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(**job)


@app.get("/api/documentation/{job_id}/download")
def api_job_download(job_id: str) -> FileResponse:
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    excel_file = job_store.download_path(job_id)
    if not excel_file.exists():
        raise HTTPException(status_code=404, detail="Documentation file not found")
    return FileResponse(excel_file, filename=excel_file.name, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.get("/api/documentation/{job_id}/excel")
def api_job_excel(job_id: str) -> FileResponse:
    return api_job_download(job_id)


@app.post("/api/documentation/{job_id}/google-sheet")
def api_job_google_sheet(job_id: str) -> Dict[str, Any]:
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    connection_record = connection_manager.get_connection_record(job["connection_id"])
    if not connection_record:
        raise HTTPException(status_code=404, detail="Database connection not found")

    try:
        schema_map = {}
        for table_name in job.get("tables", []):
            matches = search_tables(connection_record, table_name, exact=True)
            if table_name in matches:
                schema_map[table_name] = get_table_columns(connection_record, table_name)
        if not schema_map:
            raise HTTPException(status_code=400, detail="No valid tables available to publish")
        gs = GoogleSheetsClient()
        gs.update_documentation(connection_record["name"], schema_map)
        return {"ok": True, "message": "Google Sheet generated successfully"}
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Google credentials are not configured on the backend.")
    except Exception:
        raise HTTPException(status_code=500, detail="Unable to generate Google Sheet documentation")
