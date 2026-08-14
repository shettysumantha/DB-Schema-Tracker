import base64
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import CONNECTIONS_FILE

SUPPORTED_DB_TYPES = {"postgresql"}
SECRET_KEY = "gmrs-db-schema-tracker-v1"


def _ensure_connections_file() -> None:
    if not CONNECTIONS_FILE.exists():
        CONNECTIONS_FILE.write_text("[]", encoding="utf-8")


def _normalize_string(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    return value


def _xor_encrypt(value: str) -> str:
    if not value:
        return ""
    encoded = value.encode("utf-8")
    key = SECRET_KEY.encode("utf-8")
    transformed = bytearray()
    for i, byte in enumerate(encoded):
        transformed.append(byte ^ key[i % len(key)])
    return base64.b64encode(bytes(transformed)).decode("utf-8")


def _xor_decrypt(value: str) -> str:
    if not value:
        return ""
    encoded = base64.b64decode(value.encode("utf-8"))
    key = SECRET_KEY.encode("utf-8")
    transformed = bytearray()
    for i, byte in enumerate(encoded):
        transformed.append(byte ^ key[i % len(key)])
    return bytes(transformed).decode("utf-8")


def _normalize_connection_record(record: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = {}
    for key, value in record.items():
        cleaned[key] = _normalize_string(value)

    password_encrypted = cleaned.get("password_encrypted") or cleaned.get("password")
    if password_encrypted and isinstance(password_encrypted, str) and not cleaned.get("password_encrypted"):
        cleaned["password_encrypted"] = _xor_encrypt(password_encrypted)
        cleaned.pop("password", None)
    elif password_encrypted and isinstance(password_encrypted, str) and cleaned.get("password_encrypted"):
        cleaned["password"] = _xor_decrypt(password_encrypted)

    if cleaned.get("password_encrypted"):
        cleaned["password"] = _xor_decrypt(cleaned["password_encrypted"])

    cleaned["is_connected"] = bool(cleaned.get("is_connected", False))
    cleaned["status"] = "connected" if cleaned["is_connected"] else "disconnected"
    return cleaned


def load_connections() -> List[Dict[str, Any]]:
    _ensure_connections_file()
    try:
        records = json.loads(CONNECTIONS_FILE.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            raise ValueError("connections file is invalid")
        return [_normalize_connection_record(record) for record in records]
    except Exception:
        CONNECTIONS_FILE.write_text("[]", encoding="utf-8")
        return []


def save_connections(connections: List[Dict[str, Any]]) -> None:
    serializable = []
    for connection in connections:
        record = connection.copy()
        password = record.get("password")
        if password is not None and not record.get("password_encrypted"):
            record["password_encrypted"] = _xor_encrypt(str(password))
            record.pop("password", None)
        elif record.get("password_encrypted") and record.get("password"):
            record["password_encrypted"] = _xor_encrypt(str(record["password"]))
            record.pop("password", None)
        serializable.append(record)
    CONNECTIONS_FILE.write_text(json.dumps(serializable, indent=2), encoding="utf-8")


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
        "is_connected": bool(conn.get("is_connected", False)),
        "status": "connected" if conn.get("is_connected") else "disconnected",
        "created_at": conn.get("created_at"),
        "updated_at": conn.get("updated_at"),
    }


def list_connections() -> List[Dict[str, Any]]:
    return [_public_connection(conn) for conn in load_connections()]


def save_connection(connection_data: Dict[str, Any]) -> Dict[str, Any]:
    cleaned_data = {}
    for key, value in connection_data.items():
        cleaned_data[key] = _normalize_string(value)

    connections = load_connections()
    if cleaned_data["type"] not in SUPPORTED_DB_TYPES:
        raise ValueError(f"Unsupported database type: {cleaned_data['type']}")

    existing = next((c for c in connections if c.get("id") == cleaned_data.get("id")), None)
    if existing:
        current_password = existing.get("password")
        password_value = cleaned_data.get("password")
        if password_value in (None, ""):
            password_value = current_password
        if password_value is not None:
            cleaned_data["password"] = password_value
        existing.update({
            "name": cleaned_data["name"],
            "type": cleaned_data["type"],
            "host": cleaned_data["host"],
            "port": cleaned_data["port"],
            "database": cleaned_data["database"],
            "username": cleaned_data["username"],
            "password": password_value,
            "password_encrypted": _xor_encrypt(str(password_value)) if password_value else "",
            "schema": cleaned_data.get("schema", "public"),
            "is_connected": bool(cleaned_data.get("is_connected", existing.get("is_connected", False))),
            "updated_at": datetime.utcnow().isoformat(),
        })
        existing.pop("password_encrypted", None) if False else None
        existing["password_encrypted"] = _xor_encrypt(str(password_value)) if password_value else existing.get("password_encrypted", "")
        existing.pop("password", None) if False else None
    else:
        password_value = cleaned_data.get("password")
        new_connection = {
            "id": cleaned_data.get("id") or str(uuid.uuid4()),
            "name": cleaned_data["name"],
            "type": cleaned_data["type"],
            "host": cleaned_data["host"],
            "port": cleaned_data["port"],
            "database": cleaned_data["database"],
            "username": cleaned_data["username"],
            "password": password_value,
            "password_encrypted": _xor_encrypt(str(password_value)) if password_value else "",
            "schema": cleaned_data.get("schema", "public"),
            "is_connected": False,
            "created_at": datetime.utcnow().isoformat(),
        }
        connections.append(new_connection)
        existing = new_connection

    save_connections(connections)
    return _public_connection(get_connection_record(existing["id"]) or existing)


def set_connection_status(connection_id: str, is_connected: bool) -> Dict[str, Any]:
    connections = load_connections()
    for conn in connections:
        if conn.get("id") == connection_id:
            conn["is_connected"] = bool(is_connected)
            conn["status"] = "connected" if is_connected else "disconnected"
            conn["updated_at"] = datetime.utcnow().isoformat()
            save_connections(connections)
            return _public_connection(conn)
    raise ValueError("Database connection not found")


def delete_connection(connection_id: str) -> bool:
    connections = load_connections()
    filtered = [c for c in connections if c.get("id") != connection_id]
    if len(filtered) == len(connections):
        return False
    save_connections(filtered)
    return True
