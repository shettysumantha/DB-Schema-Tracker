import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import CONNECTIONS_FILE

SUPPORTED_DB_TYPES = {"postgresql"}


def _ensure_connections_file() -> None:
    if not CONNECTIONS_FILE.exists():
        CONNECTIONS_FILE.write_text("[]", encoding="utf-8")


def load_connections() -> List[Dict[str, Any]]:
    _ensure_connections_file()
    try:
        return json.loads(CONNECTIONS_FILE.read_text(encoding="utf-8"))
    except Exception:
        CONNECTIONS_FILE.write_text("[]", encoding="utf-8")
        return []


def save_connections(connections: List[Dict[str, Any]]) -> None:
    CONNECTIONS_FILE.write_text(json.dumps(connections, indent=2), encoding="utf-8")


def get_connection_record(connection_id: str) -> Optional[Dict[str, Any]]:
    for conn in load_connections():
        if conn.get("id") == connection_id:
            return conn
    return None


def _public_connection(conn: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": conn["id"],
        "name": conn["name"],
        "type": conn["type"],
        "host": conn["host"],
        "port": conn["port"],
        "database": conn["database"],
        "schema": conn.get("schema", "public"),
        "created_at": conn.get("created_at"),
    }


def list_connections() -> List[Dict[str, Any]]:
    return [_public_connection(conn) for conn in load_connections()]


def save_connection(connection_data: Dict[str, Any]) -> Dict[str, Any]:
    cleaned_data = {}
    for key, value in connection_data.items():
        if isinstance(value, str):
            cleaned_data[key] = value.strip()
        else:
            cleaned_data[key] = value

    connections = load_connections()
    if cleaned_data["type"] not in SUPPORTED_DB_TYPES:
        raise ValueError(f"Unsupported database type: {cleaned_data['type']}")

    existing = next((c for c in connections if c.get("id") == cleaned_data.get("id")), None)
    if existing:
        existing.update({
            "name": cleaned_data["name"],
            "type": cleaned_data["type"],
            "host": cleaned_data["host"],
            "port": cleaned_data["port"],
            "database": cleaned_data["database"],
            "username": cleaned_data["username"],
            "password": cleaned_data["password"],
            "schema": cleaned_data.get("schema", "public"),
            "updated_at": datetime.utcnow().isoformat(),
        })
    else:
        new_connection = {
            "id": cleaned_data.get("id") or str(uuid.uuid4()),
            "name": cleaned_data["name"],
            "type": cleaned_data["type"],
            "host": cleaned_data["host"],
            "port": cleaned_data["port"],
            "database": cleaned_data["database"],
            "username": cleaned_data["username"],
            "password": cleaned_data["password"],
            "schema": cleaned_data.get("schema", "public"),
            "created_at": datetime.utcnow().isoformat(),
        }
        connections.append(new_connection)
        existing = new_connection

    save_connections(connections)
    return _public_connection(existing)


def delete_connection(connection_id: str) -> bool:
    connections = load_connections()
    filtered = [c for c in connections if c.get("id") != connection_id]
    if len(filtered) == len(connections):
        return False
    save_connections(filtered)
    return True
