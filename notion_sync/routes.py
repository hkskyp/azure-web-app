"""Webhook endpoint for Notion automation triggers."""

import logging

from fastapi import APIRouter, Request, BackgroundTasks

from notion_sync.sync.student_dbs import create_student_individual_dbs, get_db_type_from_id
from notion_sync.sync.engine import sync_shared_to_individual
from notion_sync.sync.individual_sync import sync_individual_to_shared
from notion_sync.notion_helpers import init_notion, query_database
from notion_sync.sync_utils import discover_config_db as _discover_config_db

logger = logging.getLogger("webapp.routes")
router = APIRouter(prefix="/api/webhook", tags=["notion-sync"])

SHARED_DB_IDS = {}
SHARED_DATABASE_IDS = {}

_DB_NAME_MAP = {
    "학생 DB": "student",
    "수업영상 DB": "video",
    "과제 DB": "assignment",
    "학습일지 DB": "study_log",
    "시청기록 DB": "watch_history",
    "학부모 DB": "parent",
}


def _load_config(config_db_id: str):
    """Query config DB (DB명/database_id/data_source_id/설명) and populate ID dicts."""
    try:
        resp = query_database(config_db_id)
        for page in resp.get("results", []):
            props = page.get("properties", {})
            db_name = "".join(t["plain_text"] for t in props.get("DB명", {}).get("title", []))
            ds_id = "".join(t["plain_text"] for t in props.get("data_source_id", {}).get("rich_text", []))
            db_id = "".join(t["plain_text"] for t in props.get("database_id", {}).get("rich_text", []))
            key = _DB_NAME_MAP.get(db_name)
            if key:
                if ds_id:
                    SHARED_DB_IDS[key] = ds_id
                if db_id:
                    SHARED_DATABASE_IDS[key] = db_id
        logger.info(f"Config loaded: data_source_ids={list(SHARED_DB_IDS.keys())}, "
                     f"database_ids={list(SHARED_DATABASE_IDS.keys())}")
    except Exception as e:
        logger.error(f"Failed to load config: {e}")


_CONFIG_CACHE_FILE = "/tmp/notion_config_db_id.txt"


def _get_config_db_id(parent_page_id: str) -> str | None:
    """Resolve config DB ID: cache file → discover from parent page.

    If cached ID is stale (config query returns empty), re-discovers.
    """
    import os
    parent_page_id = parent_page_id.strip() if parent_page_id else ""

    # 1. Try cached ID, validate it
    if os.path.exists(_CONFIG_CACHE_FILE):
        cached = open(_CONFIG_CACHE_FILE).read().strip()
        if cached:
            try:
                resp = query_database(cached)
                if resp.get("results"):
                    logger.info(f"Config DB ID from cache: {cached}")
                    return cached
            except Exception:
                pass
            logger.info("Cached config DB invalid, re-discovering...")

    # 2. NOTION_PARENT_PAGE_ID로 검색
    if parent_page_id:
        discovered = _discover_config_db(parent_page_id)
        if discovered:
            with open(_CONFIG_CACHE_FILE, "w") as f:
                f.write(discovered)
            logger.info(f"Config DB ID discovered and cached: {discovered}")
            return discovered

    return None


def init(notion_token: str, parent_page_id: str = None):
    init_notion(notion_token)
    resolved = _get_config_db_id(parent_page_id or "")
    if resolved:
        _load_config(resolved)
    else:
        logger.warning("No config DB ID found — sync routing will not work")


def _prop_empty(prop: dict) -> bool:
    ptype = prop.get("type", "")
    val = prop.get(ptype)
    if val is None:
        return True
    if isinstance(val, list):
        return len(val) == 0
    return False


def _validate_props(props: dict, required: list[str], context: str, page_id: str) -> list[str]:
    missing = []
    for key in required:
        if key not in props:
            missing.append(f"{key}(누락)")
        elif _prop_empty(props[key]):
            missing.append(f"{key}(빈값)")
    if missing:
        logger.warning(f"[{context}] page={page_id} 필수 속성 부족: {missing}")
    return missing


def _identify_source(page: dict) -> str:
    parent = page.get("parent", {})
    db_id = parent.get("database_id", "") or parent.get("data_source_id", "")
    if not db_id:
        return "unknown"
    db_id_clean = db_id.replace("-", "")
    # 1. data_source_id로 직접 매칭
    for db_type, sid in SHARED_DB_IDS.items():
        if sid and db_id_clean == sid.replace("-", ""):
            return db_type
    # 2. database_id (block-level ID)로 매칭
    for db_type, did in SHARED_DATABASE_IDS.items():
        if did and db_id_clean == did.replace("-", ""):
            return db_type
    # 3. 개별 DB 확인 (API 호출)
    result = get_db_type_from_id(db_id)
    return result[0] if result else "unknown"


# --- Handler functions ---

def _handle_student(config, source_type, page_id, props, page_data, background_tasks):
    if _validate_props(props, config.get("validate", []), "student", page_id):
        return {"status": "ignored", "reason": "missing props"}
    name = "".join(t.get("plain_text", "") for t in props["이름"].get("title", []))
    background_tasks.add_task(create_student_individual_dbs, page_id, name, SHARED_DB_IDS)
    return {"status": "accepted", "action": "create-individual-dbs"}


def _handle_shared_sync(config, source_type, page_id, props, page_data, background_tasks):
    # Pre-filter (e.g., study_log requires 강사코멘트)
    pre_filter = config.get("filter")
    if pre_filter and not pre_filter(props):
        return {"status": "ignored", "source": source_type}

    has_student = "학생" in props and not _prop_empty(props["학생"])
    has_sync_id = "_sync_id" in props and not _prop_empty(props["_sync_id"])
    if not has_student and not has_sync_id:
        return {"status": "ignored", "reason": "missing props"}

    # 채점 sub-path (assignment: 점수/피드백만 전달)
    grading_filter = config.get("grading_filter")
    if grading_filter and grading_filter(props):
        background_tasks.add_task(
            sync_shared_to_individual, config["grading_config"], page_id, page_data)
        return {"status": "accepted", "action": config["grading_config"]}

    background_tasks.add_task(
        sync_shared_to_individual, config["sync_config"], page_id, page_data)
    return {"status": "accepted", "direction": "shared->individual"}


def _handle_individual(config, source_type, page_id, props, page_data, background_tasks):
    has_sync_id = "_sync_id" in props and not _prop_empty(props["_sync_id"])
    if has_sync_id:
        background_tasks.add_task(
            sync_individual_to_shared,
            config["sync_type"], page_id, page_data,
            SHARED_DB_IDS.get(config["shared_key"], ""))
        return {"status": "accepted", "direction": "individual->shared", "action": "update"}
    # CREATE: validate required props
    create_validate = config.get("create_validate", [])
    if create_validate:
        if _validate_props(props, create_validate, f"{source_type}_create", page_id):
            return {"status": "ignored", "reason": "missing props"}
    background_tasks.add_task(
        sync_individual_to_shared,
        config["sync_type"], page_id, page_data,
        SHARED_DB_IDS.get(config["shared_key"], ""))
    return {"status": "accepted", "direction": "individual->shared", "action": "create"}


# --- Handler config ---

_HANDLERS = {
    "student": {
        "validate": ["이름"],
        "action": _handle_student,
    },
    "assignment": {
        "action": _handle_shared_sync,
        "grading_filter": lambda props: ("점수" in props or "피드백" in props) and "과제명" not in props,
        "grading_config": "grading",
        "sync_config": "assignment",
    },
    "study_log": {
        "action": _handle_shared_sync,
        "filter": lambda props: "강사코멘트" in props,
        "sync_config": "comment",
    },
    "individual_assignment": {
        "sync_type": "assignment_submission",
        "shared_key": "assignment",
        "create_validate": ["과제명"],
        "action": _handle_individual,
    },
    "individual_study_log": {
        "sync_type": "study_log",
        "shared_key": "study_log",
        "create_validate": ["일지제목"],
        "action": _handle_individual,
    },
}


@router.post("/notion")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    page_data = payload.get("data") or {}
    page_id = (page_data.get("id") or "").strip()

    if not page_id or not page_data:
        return {"status": "ignored", "reason": "no data"}

    source_type = _identify_source(page_data)
    logger.info(f"Webhook: source={source_type}, page={page_id}")
    props = page_data.get("properties", {})

    handler = _HANDLERS.get(source_type)
    if not handler:
        return {"status": "ignored", "source": source_type}
    return handler["action"](handler, source_type, page_id, props, page_data, background_tasks)
