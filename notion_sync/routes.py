"""Webhook endpoint for Notion automation triggers."""

import logging

from fastapi import APIRouter, Request, BackgroundTasks

from . import sync_engine

logger = logging.getLogger("notion_sync")
router = APIRouter(prefix="/api/webhook", tags=["notion-sync"])

SHARED_DB_IDS = {}

# Maps 설정명 → internal key used in SHARED_DB_IDS
_CONFIG_KEY_MAP = {
    "SHARED_STUDENT_DB_ID":    "student",
    "SHARED_ENROLLMENT_DB_ID": "enrollment",
    "SHARED_ASSIGNMENT_DB_ID": "assignment",
    "SHARED_STUDY_LOG_DB_ID":  "study_log",
    "SHARED_PAYMENT_DB_ID":    "payment",
    "SHARED_PARENT_DB_ID":     "parent",
}


def _load_config(config_db_id: str):
    """Query Notion config DB and populate SHARED_DB_IDS."""
    try:
        resp = sync_engine.notion.databases.query(database_id=config_db_id)
        for page in resp.get("results", []):
            props = page.get("properties", {})
            key = "".join(t["plain_text"] for t in props.get("설정명", {}).get("title", []))
            val = "".join(t["plain_text"] for t in props.get("값", {}).get("rich_text", []))
            internal = _CONFIG_KEY_MAP.get(key)
            if internal and val:
                SHARED_DB_IDS[internal] = val
        logger.info(f"Config loaded: {list(SHARED_DB_IDS.keys())}")
    except Exception as e:
        logger.error(f"Failed to load config from Notion: {e}")


def init(notion_token: str, config_db_id: str = None):
    """Initialize sync system — load config from Notion config DB."""
    sync_engine.init_notion(notion_token)
    if config_db_id:
        _load_config(config_db_id)
        sync_engine.shared_parent_db_id = SHARED_DB_IDS.get("parent", "")


def _identify_source(payload: dict) -> tuple[str, str]:
    """Identify source DB type and page_id from webhook payload."""
    page_id = payload.get("id", "")
    parent = payload.get("parent", {})
    db_id = parent.get("database_id", "")

    # Check shared DBs first (O(1), no API call)
    for db_type, sid in SHARED_DB_IDS.items():
        if sid and db_id.replace("-", "") == sid.replace("-", ""):
            return db_type, page_id

    # Identify individual DB type via Notion API
    result = sync_engine.get_db_type_from_id(db_id)
    if result:
        return result[0], page_id

    return "unknown", page_id


@router.post("/notion")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Notion automation webhook."""
    payload = await request.json()
    logger.info(f"Webhook received: {list(payload.keys())}")

    source_type, page_id = _identify_source(payload)
    logger.info(f"Source: {source_type}, page: {page_id}")

    if source_type == "student":
        props = payload.get("properties", {})
        name_prop = props.get("이름", {})
        student_name = "".join(
            t.get("plain_text", "") for t in name_prop.get("title", [])
        )
        if not student_name:
            return {"status": "ignored", "reason": "no student name"}
        background_tasks.add_task(
            sync_engine.create_student_individual_dbs, page_id, student_name)
        return {"status": "accepted", "direction": "new-student→individual-dbs"}

    if source_type in ("enrollment", "assignment", "payment"):
        background_tasks.add_task(
            sync_engine.sync_shared_to_individual,
            source_type, page_id, payload)
        return {"status": "accepted", "direction": "shared→individual"}

    elif source_type == "individual_study_log":
        background_tasks.add_task(
            sync_engine.sync_individual_to_shared,
            "study_log", page_id, payload,
            SHARED_DB_IDS.get("study_log", ""))
        return {"status": "accepted", "direction": "individual→shared"}

    elif source_type == "individual_assignment":
        background_tasks.add_task(
            sync_engine.sync_individual_to_shared,
            "assignment_submission", page_id, payload,
            SHARED_DB_IDS.get("assignment", ""))
        return {"status": "accepted", "direction": "individual→shared"}

    return {"status": "ignored", "source": source_type}
