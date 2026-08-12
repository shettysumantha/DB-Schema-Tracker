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
    connections = load_connections()
    if connection_data["type"] not in SUPPORTED_DB_TYPES:
        raise ValueError(f"Unsupported database type: {connection_data['type']}")

    existing = next((c for c in connections if c.get("id") == connection_data.get("id")), None)
    if existing:
        existing.update({
            "name": connection_data["name"],
            "type": connection_data["type"],
            "host": connection_data["host"],
            "port": connection_data["port"],
            "database": connection_data["database"],
            "username": connection_data["username"],
            "password": connection_data["password"],
            "schema": connection_data.get("schema", "public"),
            "updated_at": datetime.utcnow().isoformat(),
        })
    else:
        new_connection = {
            "id": connection_data.get("id") or str(uuid.uuid4()),
            "name": connection_data["name"],
            "type": connection_data["type"],
            "host": connection_data["host"],
            "port": connection_data["port"],
            "database": connection_data["database"],
            "username": connection_data["username"],
            "password": connection_data["password"],
            "schema": connection_data.get("schema", "public"),
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
