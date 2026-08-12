from typing import List, Dict
from database import list_all_tables, get_table_columns
from config import CASH_COUNTER_TABLES, DETECT_EXTRA_TABLES
import logging

logger = logging.getLogger(__name__)


def detect_cashcounter_tables() -> List[str]:
    """Return the set of tables to document: seed list plus detected tables that look like Cash Counter tables."""
    existing = set(list_all_tables())
    # Start with seed list but only include those that actually exist in DB
    result = set(CASH_COUNTER_TABLES) & existing

    if DETECT_EXTRA_TABLES:
        # Also detect tables that contain 'cash' or 'counter' keywords
        for t in existing:
            lname = t.lower()
            if ("cash" in lname) or ("counter" in lname):
                result.add(t)

    return sorted(result)


def build_current_schema(tables: List[str]) -> Dict[str, List[Dict]]:
    schema = {}
    for t in tables:
        try:
            cols = get_table_columns(t)
            schema[t] = cols
        except Exception as e:
            logger.exception("Failed to read schema for table %s", t)
    return schema
