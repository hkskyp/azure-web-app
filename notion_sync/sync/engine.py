"""Core sync logic: shared DB -> individual student DBs."""

import logging

from notion_sync import schema_map
from notion_sync import notion_helpers
from notion_sync.notion_helpers import _extract_props, _build_notion_props, _find_by_sync_id, normalize_page_id
from notion_sync.sync.student_dbs import _get_student_child_dbs

logger = logging.getLogger("webapp.sync.engine")

# Prop types for individual DBs (used by _build_notion_props)
_IND_ENROLLMENT_TYPES = {
    "강의명": "title", "영상URL": "url",
    "수강과목": "relation", "시청시작시간": "date",
    "시청종료시간": "date", "진도율": "number", "시청시간(분)": "number",
    "_sync_id": "rich_text",
}
_IND_ASSIGNMENT_TYPES = {
    "과제명": "title", "과목명": "relation", "제출여부": "checkbox",
    "제출일시": "date", "마감일": "date", "점수": "number",
    "피드백": "rich_text", "_sync_id": "rich_text",
}


def _resolve_page_title(page_id: str) -> str:
    """Retrieve the title property value from a page."""
    page = notion_helpers.notion.pages.retrieve(page_id)
    for v in page.get("properties", {}).values():
        if v.get("type") == "title":
            return "".join(t.get("plain_text", "") for t in v.get("title", []))
    return ""


def _resolve_video_info(video_page_id: str) -> dict:
    """Retrieve video info (title, URL, subject) from a video page."""
    page = notion_helpers.notion.pages.retrieve(video_page_id)
    props = _extract_props(page)

    # Resolve subject name from relation if applicable
    subject_name = ""
    raw_props = page.get("properties", {})
    subject_prop = raw_props.get("수강과목", {})
    if subject_prop.get("type") == "relation":
        rel_ids = [r["id"] for r in subject_prop.get("relation", [])]
        if rel_ids:
            sub_page = notion_helpers.notion.pages.retrieve(rel_ids[0])
            for v in sub_page.get("properties", {}).values():
                if v.get("type") == "title":
                    subject_name = "".join(
                        t.get("plain_text", "") for t in v.get("title", []))
                    break

    return {
        "video_title": props.get("영상제목", ""),
        "video_url": props.get("영상URL", ""),
        "subject_name": subject_name,
    }


# --- Shared->Individual sync config ---

_SHARED_SYNC_CONFIG = {
    "assignment": {
        "child_db_key": "assignment",
        "prop_types": _IND_ASSIGNMENT_TYPES,
        "map_fn": schema_map.shared_assignment_to_individual,
        "resolve_subject": True,
    },
    "grading": {
        "child_db_key": "assignment",
        "props": ["점수", "피드백"],
        "prop_types": {"점수": "number", "피드백": "rich_text"},
        "update_only": True,
    },
    "comment": {
        "child_db_key": "study_log",
        "props": ["강사코멘트"],
        "prop_types": {"강사코멘트": "rich_text"},
        "update_only": True,
    },
}


# --- Common sync functions ---

def _build_update_only_props(config, props):
    """Build Notion props for update_only sync types (grading, comment)."""
    filtered = {}
    for name in config["props"]:
        val = props.get(name)
        if val is None:
            continue
        if isinstance(val, str) and not val:
            continue
        filtered[name] = val
    if not filtered:
        return {}
    return _build_notion_props(filtered, config["prop_types"])


def _do_update_only(config, config_key, page_id, props, student_page_ids):
    """Update-only sync: grading or comment."""
    notion_props = _build_update_only_props(config, props)
    if not notion_props:
        return
    for stu_page_id in student_page_ids:
        child_dbs = _get_student_child_dbs(stu_page_id)
        target_db = child_dbs.get(config["child_db_key"])
        if not target_db:
            continue
        existing = _find_by_sync_id(target_db, page_id)
        if existing:
            notion_helpers.notion.pages.update(page_id=existing, properties=notion_props)
            logger.info(f"{config_key} synced to student {stu_page_id}")
        else:
            logger.warning(f"No matching individual page for {config_key}: {page_id}")


def _do_full_sync(config, config_key, page_id, page_data, props, student_page_ids):
    """Full sync: map_fn + UPDATE or CREATE with _sync_id bidirectional write-back."""
    # Loop guard: shared page's _sync_id → existing individual page
    shared_sync_id = props.get("_sync_id", "") or ""
    if not shared_sync_id and "properties" not in page_data:
        try:
            fresh = notion_helpers.notion.pages.retrieve(page_id)
            shared_sync_id = (_extract_props(fresh).get("_sync_id", "") or "")
        except Exception:
            pass

    extra_kwargs = {}
    if config.get("resolve_subject"):
        subject_ids = props.get("과목", []) or []
        if subject_ids:
            extra_kwargs["subject_page_ids"] = subject_ids

    for stu_page_id in student_page_ids:
        child_dbs = _get_student_child_dbs(stu_page_id)
        target_db = child_dbs.get(config["child_db_key"])
        if not target_db:
            logger.warning(f"No {config['child_db_key']} DB found under student {stu_page_id}")
            continue

        mapped = config["map_fn"](props, sync_id=page_id, **extra_kwargs)
        notion_props = _build_notion_props(mapped, config["prop_types"])

        existing = _find_by_sync_id(target_db, page_id)
        if not existing and shared_sync_id:
            existing = shared_sync_id
            logger.info(f"Loop guard: using shared._sync_id={shared_sync_id} as existing individual page")
        if existing:
            # UPDATE: webhook에 포함된 속성만 업데이트
            webhook_keys = set(page_data.get("properties", {}).keys())
            update_props = {k: v for k, v in notion_props.items()
                           if k == "_sync_id" or k in webhook_keys}
            if update_props:
                notion_helpers.notion.pages.update(page_id=existing, properties=update_props)
        else:
            new_page = notion_helpers.notion.pages.create(
                parent={"data_source_id": target_db}, properties=notion_props)
            # _sync_id 양방향 기록
            try:
                notion_helpers.notion.pages.update(page_id=page_id, properties={
                    "_sync_id": {"rich_text": [{"text": {"content": normalize_page_id(new_page["id"])}}]}
                })
                notion_helpers.notion.pages.update(page_id=new_page["id"], properties={
                    "_sync_id": {"rich_text": [{"text": {"content": normalize_page_id(page_id)}}]}
                })
            except Exception as e:
                logger.warning(f"Failed to write _sync_id: {e}")
        logger.info(f"Synced {config_key} to student {stu_page_id}")


def sync_shared_to_individual(config_key: str, page_id: str, page_data: dict):
    """Sync a shared DB page to individual student DBs.

    config_key: "assignment" (full sync), "grading" (점수/피드백 only),
                "comment" (강사코멘트 only)
    """
    config = _SHARED_SYNC_CONFIG.get(config_key)
    if not config:
        logger.warning(f"Unsupported config_key for shared->individual: {config_key}")
        return

    props = _extract_props(page_data) if "properties" in page_data else page_data
    student_page_ids = props.get("학생", []) or []
    if not student_page_ids:
        logger.warning(f"No student in {config_key} webhook, skipping")
        return

    if config.get("update_only"):
        _do_update_only(config, config_key, page_id, props, student_page_ids)
    else:
        _do_full_sync(config, config_key, page_id, page_data, props, student_page_ids)
