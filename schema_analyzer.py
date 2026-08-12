from typing import List, Dict, Any
import logging

from database import list_tables, get_table_columns

logger = logging.getLogger(__name__)


def list_database_tables(connection_record: Dict[str, Any], limit: int = 100) -> List[str]:
    return list_tables(connection_record, limit=limit)


def build_current_schema(connection_record: Dict[str, Any], tables: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    schema = {}
    for t in tables:
        try:
            cols = get_table_columns(connection_record, t)
            schema[t] = cols
        except Exception:
            logger.exception("Failed to read schema for table %s", t)
    return schema
