from typing import List, Dict, Tuple, Any
from datetime import datetime

def compare_table_schema(old: List[Dict[str, Any]], new: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Compare old (documented) and new (database) column lists.

    Columns are matched by name. Returns dict with keys: added, removed, modified.
    Modified entries include old and new definitions.
    """
    old_map = {c["column_name"]: c for c in old} if old else {}
    new_map = {c["column_name"]: c for c in new} if new else {}

    added = []
    removed = []
    modified = []

    for name, newc in new_map.items():
        if name not in old_map:
            added.append(newc)
        else:
            oldc = old_map[name]
            diffs = {}
            fields = [
                "data_type",
                "is_nullable",
                "column_default",
                "is_primary",
                "foreign_key",
                "column_comment",
            ]
            for f in fields:
                if (oldc.get(f) != newc.get(f)):
                    diffs[f] = {"old": oldc.get(f), "new": newc.get(f)}
            if diffs:
                modified.append({"column_name": name, "diffs": diffs, "old": oldc, "new": newc})

    for name, oldc in old_map.items():
        if name not in new_map:
            removed.append(oldc)

    return {"added": added, "removed": removed, "modified": modified}
