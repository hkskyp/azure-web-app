"""Sync individual DB pages back to shared DBs."""

import logging

from notion_sync import schema_map
from notion_sync import notion_helpers
from notion_sync.notion_helpers import _extract_props, _build_notion_props, normalize_page_id
from notion_sync.sync.student_dbs import get_db_type_from_id

logger = logging.getLogger("webapp.sync.individual_sync")

_SHARED_ASSIGNMENT_TYPES = {
    "과제명": "title", "마감일": "date",
    "제출여부": "checkbox", "제출일시": "date",
    "학생": "relation", "과목": "relation", "_sync_id": "rich_text",
}

_SHARED_STUDY_LOG_TYPES = {
    "일지제목": "title", "날짜": "date", "학습시간(분)": "number",
    "자기평가": "select", "학습내용": "rich_text", "강사코멘트": "rich_text",
    "학생": "relation", "학습과목": "relation", "_sync_id": "rich_text",
}


def _find_subject_by_name(subject_name: str, shared_db_ids: dict) -> str | None:
    """Search shared 과목 DB for a subject by name, return page_id."""
    from notion_sync.routes import SHARED_DB_IDS
    subject_db_id = shared_db_ids.get("subject") or SHARED_DB_IDS.get("subject", "")
    if not subject_db_id or not subject_name:
        return None
    try:
        from notion_helpers import query_database
        resp = query_database(subject_db_id, filter={
            "property": "과목명", "title": {"equals": subject_name.strip()}
        })
        pages = resp.get("results", [])
        return pages[0]["id"] if pages else None
    except Exception as e:
        logger.warning(f"Failed to find subject '{subject_name}': {e}")
        return None


# --- Hook functions ---

def _set_submission_date(update_props, page_id):
    """제출여부 True → 제출일시 = now (개별 페이지에도 기록)."""
    if update_props.get("제출여부"):
        from datetime import datetime, timezone
        now_iso = datetime.now(timezone.utc).isoformat()
        update_props["제출일시"] = now_iso
        try:
            notion_helpers.notion.pages.update(page_id=page_id, properties={
                "제출일시": {"date": {"start": now_iso}}
            })
        except Exception as e:
            logger.warning(f"Failed to set 제출일시 on individual page {page_id}: {e}")


def _set_study_date(props, _page_id):
    """CREATE 시 날짜 = now (공유 페이지 생성용 props에만 설정)."""
    from datetime import datetime, timezone
    props["날짜"] = datetime.now(timezone.utc).isoformat()


# --- Build functions ---

def _build_assignment_mapped(props, student_page_id, page_id):
    """Build mapped dict for shared assignment."""
    subject_page_ids = props.get("과목명", []) or []
    if isinstance(subject_page_ids, str):
        # 레거시: text → relation 변환
        sid = _find_subject_by_name(subject_page_ids, {})
        subject_page_ids = [sid] if sid else []
    return schema_map.individual_assignment_to_shared(
        props, student_page_id=student_page_id,
        subject_page_ids=subject_page_ids, sync_id=page_id)


def _build_study_log_mapped(props, student_page_id, _page_id):
    """Build mapped dict for shared study log."""
    mapped = schema_map.individual_study_log_to_shared(props)
    if student_page_id:
        mapped["학생"] = [student_page_id]
    # 학습과목: relation(page ID 리스트) 또는 text
    subject_val = props.get("학습과목", "")
    if isinstance(subject_val, list):
        if subject_val:
            mapped["학습과목"] = subject_val
    elif subject_val:
        subject_ids = []
        for name in subject_val.split(","):
            sid = _find_subject_by_name(name.strip(), {})
            if sid:
                subject_ids.append(sid)
        if subject_ids:
            mapped["학습과목"] = subject_ids
    return mapped


# --- Sync config ---

_SYNC_CONFIG = {
    "assignment_submission": {
        "shared_key": "assignment",
        "create_prop_types": _SHARED_ASSIGNMENT_TYPES,
        "update_fn": schema_map.individual_assignment_to_shared_update,
        "update_prop_types": {"제출여부": "checkbox", "제출일시": "date"},
        "on_submit": _set_submission_date,
        "build_mapped": _build_assignment_mapped,
    },
    "study_log": {
        "shared_key": "study_log",
        "create_prop_types": _SHARED_STUDY_LOG_TYPES,
        "update_fn": None,
        "on_create": _set_study_date,
        "build_mapped": _build_study_log_mapped,
        "writeback_keys": ["날짜"],
    },
}


# --- Common sync logic ---

def _do_update(config, sync_id, page_id, props, page_data, parent_db_id):
    """Common UPDATE logic: update_fn 호출 or webhook key 필터링."""
    update_fn = config.get("update_fn")
    if update_fn:
        update_props = update_fn(props)
        on_submit = config.get("on_submit")
        if on_submit:
            on_submit(update_props, page_id)
        notion_props = _build_notion_props(update_props, config["update_prop_types"])
    else:
        # Full mapping → filter by webhook keys
        student_page_id = ""
        if parent_db_id:
            db_result = get_db_type_from_id(parent_db_id)
            student_page_id = db_result[1] if db_result else ""
        mapped = config["build_mapped"](props, student_page_id, page_id)
        notion_props = _build_notion_props(mapped, config["create_prop_types"])
        webhook_keys = set(page_data.get("properties", {}).keys())
        notion_props = {k: v for k, v in notion_props.items()
                       if k == "_sync_id" or k in webhook_keys}
    if notion_props:
        try:
            notion_helpers.notion.pages.update(page_id=sync_id, properties=notion_props)
            logger.info(f"Updated {config['shared_key']} in shared DB")
        except Exception as e:
            logger.error(f"Failed to update shared {config['shared_key']} {sync_id}: {e}")


def _do_create(config, page_id, props, page_data, shared_db_id, parent_db_id):
    """Common CREATE logic: build_mapped 호출 + 학생/과목 조회 + _sync_id 양방향 기록."""
    if not shared_db_id:
        logger.error(f"Shared DB ID not set for {config['shared_key']}; cannot create")
        return
    # 중복 CREATE 방지: 공유 DB에 같은 _sync_id가 이미 있으면 skip
    normalized_id = normalize_page_id(page_id)
    try:
        from notion_sync.notion_helpers import query_database
        existing = query_database(shared_db_id,
            filter={"property": "_sync_id", "rich_text": {"equals": normalized_id}})
        if existing.get("results"):
            logger.info(f"Skipping duplicate create: {config['shared_key']} _sync_id={normalized_id}")
            return
    except Exception:
        pass
    # Apply on_create hook (e.g., set date=now)
    on_create = config.get("on_create")
    if on_create:
        on_create(props, page_id)
    # Resolve student
    student_page_id = ""
    if parent_db_id:
        db_result = get_db_type_from_id(parent_db_id)
        student_page_id = db_result[1] if db_result else ""
    logger.info(f"Creating shared {config['shared_key']}: student={student_page_id}")
    mapped = config["build_mapped"](props, student_page_id, page_id)
    mapped["_sync_id"] = normalize_page_id(page_id)
    notion_props = _build_notion_props(mapped, config["create_prop_types"])
    new_page = notion_helpers.notion.pages.create(
        parent={"data_source_id": shared_db_id}, properties=notion_props)
    logger.info(f"Created shared {config['shared_key']} page: {new_page['id']}")
    # _sync_id + writeback_keys를 한 번의 PATCH로 개별 페이지에 기록
    sync_id_props = {
        "_sync_id": {"rich_text": [{"text": {"content": normalize_page_id(new_page["id"])}}]}
    }
    writeback = dict(sync_id_props)
    for key in config.get("writeback_keys", []):
        val = props.get(key)
        if val is not None:
            writeback.update(_build_notion_props({key: val}, config["create_prop_types"]))
    try:
        notion_helpers.notion.pages.update(page_id=page_id, properties=writeback)
    except Exception:
        # writeback_keys 실패 시 _sync_id만 재시도 (중복 방지 필수)
        try:
            notion_helpers.notion.pages.update(page_id=page_id, properties=sync_id_props)
        except Exception as e:
            logger.warning(f"Failed to write _sync_id on individual {config['shared_key']}: {e}")


def sync_individual_to_shared(source_db_type: str, page_id: str,
                               page_data: dict, shared_db_id: str):
    """Sync an individual DB page to shared DB (assignment_submission + study_log)."""
    config = _SYNC_CONFIG.get(source_db_type)
    if not config:
        logger.warning(f"Unsupported source_db_type: {source_db_type}")
        return

    parent_db_id = ""
    if "properties" in page_data:
        parent = page_data.get("parent", {})
        parent_db_id = parent.get("database_id", "") or parent.get("data_source_id", "")
        props = _extract_props(page_data)
    else:
        props = page_data
        parent_db_id = page_data.get("_parent_db_id", "")
    sync_id = props.get("_sync_id", "")

    if sync_id:
        _do_update(config, sync_id, page_id, props, page_data, parent_db_id)
    else:
        _do_create(config, page_id, props, page_data, shared_db_id, parent_db_id)
