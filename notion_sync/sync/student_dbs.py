"""Student individual DB creation and lookup.

Thin wrapper: schemas, creation, and child-DB lookup live in sync_utils
(copied from shared/ at deploy time). This module keeps only the functions
that need direct HTTP calls with notion_helpers.notion.options.auth.
"""

import logging

from notion_sync import notion_helpers
from notion_sync.sync_utils import (
    get_student_child_dbs as _get_student_child_dbs,
    create_student_individual_dbs,
)

logger = logging.getLogger("webapp.sync.student_dbs")


# ── HTTP-level helpers (not in sync_utils) ─────────────────────────────────

def _retrieve_data_source(db_id: str) -> dict:
    """Retrieve a data source via direct HTTP (API 2025-09-03)."""
    import httpx
    resp = httpx.get(
        f"https://api.notion.com/v1/data_sources/{db_id}",
        headers={
            "Authorization": f"Bearer {notion_helpers.notion.options.auth}",
            "Notion-Version": "2025-09-03",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _retrieve_database(db_id: str) -> dict:
    """Retrieve a database (block-level) via GET /databases/{id} (API 2025-09-03).

    Returns the database object which includes title and data_sources list.
    Use this as a fallback when the ID is a database_id rather than a data_source_id.
    """
    import httpx
    resp = httpx.get(
        f"https://api.notion.com/v1/databases/{db_id}",
        headers={
            "Authorization": f"Bearer {notion_helpers.notion.options.auth}",
            "Notion-Version": "2025-09-03",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def get_db_type_from_id(db_id: str) -> tuple[str, str] | None:
    """Given a DB ID (data_source_id or database_id), return (individual_type, parent_page_id) or None."""
    # Try data_source endpoint first
    try:
        db_info = _retrieve_data_source(db_id)
        dp = db_info.get("database_parent", {})
        if dp.get("type") != "page_id":
            return None
        page_id = dp["page_id"]
        title = "".join(t.get("plain_text", "") for t in db_info.get("title", []))
        if "수강목록" in title:
            return "individual_enrollment", page_id
        elif "과제" in title:
            return "individual_assignment", page_id
        elif "학습일지" in title:
            return "individual_study_log", page_id
        return None
    except Exception:
        pass

    # Fallback: try database endpoint (for database_ids / block-level IDs)
    try:
        db_info = _retrieve_database(db_id)
        title_parts = db_info.get("title", [])
        title = "".join(t.get("plain_text", "") for t in title_parts)
        # Extract parent page_id from the database object
        parent = db_info.get("parent", {})
        page_id = parent.get("page_id", "")
        if not page_id:
            return None
        if "수강목록" in title:
            return "individual_enrollment", page_id
        elif "과제" in title:
            return "individual_assignment", page_id
        elif "학습일지" in title:
            return "individual_study_log", page_id
        return None
    except Exception as e:
        logger.warning(f"Failed to retrieve DB {db_id}: {e}")
        return None
