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
        resp = sync_engine._query_database(config_db_id)
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


def _get_db_id(page: dict) -> str:
    return page.get("parent", {}).get("database_id", "")


def _identify_source_from_page(page: dict) -> str:
    """Identify source DB type from a full Notion page object."""
    db_id = _get_db_id(page)
    if not db_id:
        return "unknown"

    for db_type, sid in SHARED_DB_IDS.items():
        if sid and db_id.replace("-", "") == sid.replace("-", ""):
            return db_type

    result = sync_engine.get_db_type_from_id(db_id)
    return result[0] if result else "unknown"


@router.post("/notion")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Notion automation webhook."""
    payload = await request.json()
    page_id = payload.get("id", "")
    logger.warning(f"Webhook received, page_id={page_id}")

    if not page_id:
        return {"status": "ignored", "reason": "no page_id"}

    # Notion 자동화 webhook payload는 내용이 불완전할 수 있으므로 API로 직접 조회
    try:
        page = sync_engine.notion.pages.retrieve(page_id)
    except Exception as e:
        logger.error(f"Failed to retrieve page {page_id}: {e}")
        return {"status": "error", "reason": str(e)}

    source_type = _identify_source_from_page(page)
    logger.warning(f"Source: {source_type}, page: {page_id}")

    if source_type == "student":
        name_prop = page.get("properties", {}).get("이름", {})
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
            source_type, page_id, page)
        return {"status": "accepted", "direction": "shared→individual"}

    elif source_type == "individual_study_log":
        background_tasks.add_task(
            sync_engine.sync_individual_to_shared,
            "study_log", page_id, page,
            SHARED_DB_IDS.get("study_log", ""))
        return {"status": "accepted", "direction": "individual→shared"}

    elif source_type == "individual_assignment":
        background_tasks.add_task(
            sync_engine.sync_individual_to_shared,
            "assignment_submission", page_id, page,
            SHARED_DB_IDS.get("assignment", ""))
        return {"status": "accepted", "direction": "individual→shared"}

    return {"status": "ignored", "source": source_type}
