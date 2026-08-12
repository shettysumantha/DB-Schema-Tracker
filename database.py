import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
import logging

from config import PUBLIC_SCHEMA

logger = logging.getLogger(__name__)


def _build_connection_params(connection_data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "host": connection_data["host"],
        "port": connection_data["port"],
        "dbname": connection_data["database"],
        "user": connection_data.get("username", connection_data.get("user")),
        "password": connection_data["password"],
    }


@contextmanager
def get_connection_from(connection_record: Dict[str, Any]):
    conn = None
    try:
        params = _build_connection_params(connection_record)
        conn = psycopg2.connect(**params)
        yield conn
    except Exception:
        logger.exception("PostgreSQL connection failed")
        raise
    finally:
        if conn:
            conn.close()


def test_connection(connection_data: Dict[str, Any]) -> None:
    with psycopg2.connect(**_build_connection_params(connection_data)) as conn:
        with conn.cursor():
            pass


def list_tables(connection_record: Dict[str, Any], schema: Optional[str] = None, limit: int = 100) -> List[str]:
    schema = schema or connection_record.get("schema") or PUBLIC_SCHEMA
    query = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = %s
      AND table_type = 'BASE TABLE'
    ORDER BY table_name
    LIMIT %s
    """
    with get_connection_from(connection_record) as conn:
        with conn.cursor() as cur:
            cur.execute(query, (schema, limit))
            return [r[0] for r in cur.fetchall()]


def search_tables(connection_record: Dict[str, Any], q: str, exact: bool = False, limit: int = 50) -> List[str]:
    schema = connection_record.get("schema") or PUBLIC_SCHEMA
    if exact:
        query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = %s
          AND table_type = 'BASE TABLE'
          AND table_name = %s
        ORDER BY table_name
        LIMIT 1
        """
        params = (schema, q)
    else:
        query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = %s
          AND table_type = 'BASE TABLE'
          AND table_name ILIKE %s
        ORDER BY table_name
        LIMIT %s
        """
        params = (schema, f"%{q}%", limit)
    with get_connection_from(connection_record) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return [r[0] for r in cur.fetchall()]


def get_table_columns(connection_record: Dict[str, Any], table_name: str) -> List[Dict[str, Any]]:
    schema = connection_record.get("schema") or PUBLIC_SCHEMA
    cols_query = """
    SELECT
      a.attnum as ordinal_position,
      a.attname as column_name,
      format_type(a.atttypid, a.atttypmod) as data_type,
      (SELECT pg_get_expr(def.adbin, def.adrelid) FROM pg_attrdef def WHERE def.adrelid = a.attrelid AND def.adnum = a.attnum) as column_default,
      NOT a.attnotnull as is_nullable,
      col_description(a.attrelid, a.attnum) as column_comment
    FROM pg_attribute a
    JOIN pg_class c ON a.attrelid = c.oid
    JOIN pg_namespace n ON c.relnamespace = n.oid
    WHERE c.relname = %s AND n.nspname = %s AND a.attnum > 0 AND NOT a.attisdropped
    ORDER BY a.attnum
    """

    pk_query = """
    SELECT kcu.column_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
    WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_name = %s AND tc.table_schema = %s
    """

    fk_query = """
    SELECT
      kcu.column_name,
      ccu.table_name AS foreign_table_name,
      ccu.column_name AS foreign_column_name,
      tc.constraint_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage ccu
      ON tc.constraint_name = ccu.constraint_name AND tc.constraint_schema = ccu.constraint_schema
    WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = %s AND tc.table_schema = %s
    """

    with get_connection_from(connection_record) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(cols_query, (table_name, schema))
            columns = cur.fetchall()

            cur.execute(pk_query, (table_name, schema))
            pk_rows = cur.fetchall()
            if pk_rows and isinstance(pk_rows[0], dict):
                pk_columns = {r.get("column_name") for r in pk_rows if r.get("column_name")}
            else:
                pk_columns = {r[0] for r in pk_rows}

            cur.execute(fk_query, (table_name, schema))
            fk_rows = cur.fetchall()
            fk_map = {}
            for r in fk_rows:
                if isinstance(r, dict):
                    col = r.get("column_name")
                    foreign_table = r.get("foreign_table_name")
                    foreign_column = r.get("foreign_column_name")
                    constraint = r.get("constraint_name")
                else:
                    col = r[0]
                    foreign_table = r[1]
                    foreign_column = r[2]
                    constraint = r[3]
                if col:
                    fk_map[col] = {
                        "referenced_table": foreign_table,
                        "referenced_column": foreign_column,
                        "constraint_name": constraint,
                    }

    result = []
    for c in columns:
        colname = c["column_name"]
        result.append(
            {
                "column_name": colname,
                "ordinal_position": c["ordinal_position"],
                "data_type": c["data_type"],
                "is_nullable": bool(c["is_nullable"]),
                "column_default": c.get("column_default"),
                "column_comment": c.get("column_comment"),
                "is_primary": colname in pk_columns,
                "foreign_key": fk_map.get(colname),
            }
        )

    return result


