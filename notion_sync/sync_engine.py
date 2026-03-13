"""Core sync logic: route webhook events to correct handler."""

import logging
import os

import httpx
from notion_client import Client

from . import schema_map

_NOTION_API_BASE = "https://api.notion.com/v1"
_NOTION_VERSION = "2022-06-28"


def _query_database(db_id: str, filter: dict = None) -> dict:
    """Query a Notion database via direct HTTP (bypasses notion-client version issues)."""
    token = os.environ.get("NOTION_API_KEY", "")
    body = {}
    if filter:
        body["filter"] = filter
    resp = httpx.post(
        f"{_NOTION_API_BASE}/databases/{db_id}/query",
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": _NOTION_VERSION,
        },
        json=body,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()

logger = logging.getLogger("notion_sync")

notion = None
shared_parent_db_id = None  # 학부모 DB ID (for payment → parent lookup)


def init_notion(token: str, parent_db_id: str = None):
    global notion, shared_parent_db_id
    notion = Client(auth=token)
    shared_parent_db_id = parent_db_id


# ── Notion API helpers ─────────────────────────────────────────────────────

def _get_student_child_dbs(student_page_id: str) -> dict:
    """Get individual DB IDs under a student page via Notion API.

    Returns: {"enrollment": db_id, "assignment": db_id, "study_log": db_id}
    """
    resp = notion.blocks.children.list(block_id=student_page_id)
    result = {}
    for block in resp.get("results", []):
        if block["type"] != "child_database":
            continue
        title = block["child_database"].get("title", "")
        bid = block["id"]
        if "수강목록" in title:
            result["enrollment"] = bid
        elif "과제" in title:
            result["assignment"] = bid
        elif "학습일지" in title:
            result["study_log"] = bid
    return result


def _get_parent_payment_dbs(student_page_id: str) -> list[str]:
    """Find payment DB IDs of parents who have this student as a child."""
    if not shared_parent_db_id:
        logger.warning("SHARED_PARENT_DB_ID not set; skipping payment sync")
        return []
    resp = _query_database(
        shared_parent_db_id,
        filter={"property": "자녀", "relation": {"contains": student_page_id}},
    )
    payment_dbs = []
    for page in resp.get("results", []):
        children = notion.blocks.children.list(block_id=page["id"])
        for block in children.get("results", []):
            if block["type"] != "child_database":
                continue
            title = block["child_database"].get("title", "")
            if "수강료" in title:
                payment_dbs.append(block["id"])
    return payment_dbs


def get_db_type_from_id(db_id: str) -> tuple[str, str] | None:
    """Given a DB ID, return (individual_type, parent_page_id) or None."""
    try:
        db_info = notion.databases.retrieve(db_id)
        parent = db_info.get("parent", {})
        if parent.get("type") != "page_id":
            return None
        page_id = parent["page_id"]
        title = "".join(t.get("plain_text", "") for t in db_info.get("title", []))
        if "수강목록" in title:
            return "individual_enrollment", page_id
        elif "과제" in title:
            return "individual_assignment", page_id
        elif "학습일지" in title:
            return "individual_study_log", page_id
        elif "수강료" in title:
            return "individual_payment", page_id
        return None
    except Exception as e:
        logger.warning(f"Failed to retrieve DB {db_id}: {e}")
        return None


# ── Property helpers ───────────────────────────────────────────────────────

def _extract_plain_text(prop: dict):
    ptype = prop.get("type", "")
    if ptype == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    elif ptype == "rich_text":
        return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
    elif ptype == "number":
        return prop.get("number")
    elif ptype == "checkbox":
        return prop.get("checkbox", False)
    elif ptype == "select":
        sel = prop.get("select")
        return sel["name"] if sel else None
    elif ptype == "date":
        d = prop.get("date")
        return d.get("start") if d else None
    elif ptype == "relation":
        return [r["id"] for r in prop.get("relation", [])]
    return None


def _extract_props(page: dict) -> dict:
    result = {}
    for name, prop in page.get("properties", {}).items():
        result[name] = _extract_plain_text(prop)
    return result


def _build_notion_props(data: dict, prop_types: dict) -> dict:
    props = {}
    for key, value in data.items():
        if key.startswith("_") and key != "_sync_id":
            continue
        if value is None:
            continue
        ptype = prop_types.get(key)
        if not ptype or ptype in ("formula", "rollup"):
            continue

        if ptype == "title":
            props[key] = {"title": [{"text": {"content": str(value)}}]}
        elif ptype == "rich_text":
            props[key] = {"rich_text": [{"text": {"content": str(value)}}]}
        elif ptype == "number":
            props[key] = {"number": value}
        elif ptype == "checkbox":
            props[key] = {"checkbox": bool(value)}
        elif ptype == "date":
            props[key] = {"date": {"start": str(value)}}
        elif ptype == "url":
            props[key] = {"url": str(value)}
        elif ptype == "select":
            props[key] = {"select": {"name": str(value)}}
        elif ptype == "relation":
            if isinstance(value, list):
                props[key] = {"relation": [{"id": pid} for pid in value]}
            else:
                props[key] = {"relation": [{"id": str(value)}]}
    return props


# ── Individual DB schemas ──────────────────────────────────────────────────

_ENROLLMENT_SCHEMA = {
    "매핑제목": {"title": {}},
    "영상제목": {"rich_text": {}},
    "소속과목": {"rich_text": {}},
    "시청링크": {"formula": {
        "expression": 'link("▶ 시청하기", "https://lucasoft.ai.kr/watch?id=" + id())',
    }},
    "시청완료": {"formula": {
        "expression": 'if(prop("진도율") >= 0.9, "✅ 완료", "⬜ 미완료")',
    }},
    "배정일": {"date": {}},
    "진도율": {"number": {"format": "percent"}},
    "시청시작시간": {"date": {}},
    "시청종료시간": {"date": {}},
    "시청시간(분)": {"number": {"format": "number"}},
    "영상URL": {"url": {}},
    "메모": {"rich_text": {}},
}

_ASSIGNMENT_SCHEMA = {
    "과제명": {"title": {}},
    "과목명": {"rich_text": {}},
    "마감일": {"date": {}},
    "지각여부": {"formula": {
        "expression": (
            'if(and(prop("제출여부"), and(not(empty(prop("제출일시"))), '
            'not(empty(prop("마감일"))))), '
            'if(prop("제출일시") > prop("마감일"), "⚠️ 지각", "✅ 정상"), "")'
        ),
    }},
    "제출여부": {"checkbox": {}},
    "제출일시": {"date": {}},
    "점수": {"number": {"format": "number"}},
    "피드백": {"rich_text": {}},
    "첨부파일": {"files": {}},
}

_STUDY_LOG_SCHEMA = {
    "일지제목": {"title": {}},
    "날짜": {"date": {}},
    "학습과목": {"rich_text": {}},
    "학습시간(분)": {"number": {"format": "number"}},
    "자기평가": {"select": {"options": [
        {"name": "⭐"}, {"name": "⭐⭐"}, {"name": "⭐⭐⭐"},
        {"name": "⭐⭐⭐⭐"}, {"name": "⭐⭐⭐⭐⭐"},
    ]}},
    "학습내용": {"rich_text": {}},
    "강사코멘트": {"rich_text": {}},
}


def _create_db(title: str, page_id: str, schema: dict, icon: str):
    return notion.databases.create(
        parent={"type": "page_id", "page_id": page_id},
        title=[{"type": "text", "text": {"content": title}}],
        icon={"type": "emoji", "emoji": icon},
        properties=schema,
    )


_SYNC_ID_PROP = {"_sync_id": {"rich_text": {}}}


def create_student_individual_dbs(student_page_id: str, student_name: str):
    """Create 3 individual DBs under a new student page."""
    r1 = _create_db(f"{student_name} 수강목록", student_page_id, _ENROLLMENT_SCHEMA, "🔗")
    notion.databases.update(database_id=r1["id"], properties=_SYNC_ID_PROP)
    r2 = _create_db(f"{student_name} 과제",     student_page_id, _ASSIGNMENT_SCHEMA,  "📝")
    notion.databases.update(database_id=r2["id"], properties=_SYNC_ID_PROP)
    r3 = _create_db(f"{student_name} 학습일지", student_page_id, _STUDY_LOG_SCHEMA,   "📖")
    notion.databases.update(database_id=r3["id"], properties=_SYNC_ID_PROP)
    logger.info(f"Created 3 individual DBs for student: {student_name}")


def _find_by_sync_id(db_id: str, sync_id: str) -> str | None:
    result = _query_database(
        db_id,
        filter={"property": "_sync_id", "rich_text": {"equals": sync_id}},
    )
    pages = result.get("results", [])
    return pages[0]["id"] if pages else None


# Prop types for individual DBs
_IND_ENROLLMENT_TYPES = {
    "매핑제목": "title", "영상제목": "rich_text", "영상URL": "url",
    "소속과목": "rich_text", "배정일": "date", "시청시작시간": "date",
    "시청종료시간": "date", "진도율": "number", "시청시간(분)": "number",
    "메모": "rich_text", "_sync_id": "rich_text",
}
_IND_ASSIGNMENT_TYPES = {
    "과제명": "title", "과목명": "rich_text", "제출여부": "checkbox",
    "제출일시": "date", "마감일": "date", "점수": "number",
    "피드백": "rich_text", "_sync_id": "rich_text",
}
_IND_PAYMENT_TYPES = {
    "납부제목": "title", "자녀이름": "rich_text", "청구월": "date",
    "수강과목": "rich_text", "청구금액": "number", "할인금액": "number",
    "납부여부": "checkbox", "납입일자": "date", "납부메모": "rich_text",
    "_sync_id": "rich_text",
}


# ── Sync functions ─────────────────────────────────────────────────────────

def sync_shared_to_individual(source_db_type: str, page_id: str, page_data: dict):
    """Sync a shared DB page → individual student/parent DB."""
    props = _extract_props(page_data) if "properties" in page_data else page_data

    if source_db_type in ("enrollment", "assignment"):
        student_page_ids = props.get("학생", []) or []
        type_key = "enrollment" if source_db_type == "enrollment" else "assignment"
        prop_types = _IND_ENROLLMENT_TYPES if source_db_type == "enrollment" else _IND_ASSIGNMENT_TYPES
        map_fn = schema_map.shared_enrollment_to_individual if source_db_type == "enrollment" \
            else schema_map.shared_assignment_to_individual

        for stu_page_id in student_page_ids:
            child_dbs = _get_student_child_dbs(stu_page_id)
            target_db = child_dbs.get(type_key)
            if not target_db:
                logger.warning(f"No {type_key} DB found under student {stu_page_id}")
                continue
            mapped = map_fn(props, sync_id=page_id)
            notion_props = _build_notion_props(mapped, prop_types)
            existing = _find_by_sync_id(target_db, page_id)
            if existing:
                notion.pages.update(page_id=existing, properties=notion_props)
            else:
                notion.pages.create(parent={"database_id": target_db}, properties=notion_props)
            logger.info(f"Synced {source_db_type} to student {stu_page_id}")

    elif source_db_type == "payment":
        student_page_ids = props.get("학생", []) or []
        for stu_page_id in student_page_ids:
            payment_dbs = _get_parent_payment_dbs(stu_page_id)
            for target_db in payment_dbs:
                mapped = schema_map.shared_payment_to_individual(props, sync_id=page_id)
                notion_props = _build_notion_props(mapped, _IND_PAYMENT_TYPES)
                existing = _find_by_sync_id(target_db, page_id)
                if existing:
                    notion.pages.update(page_id=existing, properties=notion_props)
                else:
                    notion.pages.create(parent={"database_id": target_db}, properties=notion_props)
            logger.info(f"Synced payment to parents of student {stu_page_id}")


def sync_individual_to_shared(source_db_type: str, page_id: str,
                               page_data: dict, shared_db_id: str):
    """Sync an individual DB page → shared DB."""
    props = _extract_props(page_data) if "properties" in page_data else page_data
    sync_id = props.get("_sync_id", "")

    if source_db_type == "assignment_submission":
        if not sync_id:
            logger.warning("Individual assignment has no _sync_id")
            return
        update_props = schema_map.individual_assignment_to_shared_update(props)
        notion_props = _build_notion_props(update_props, {
            "제출여부": "checkbox", "제출일시": "date",
        })
        notion.pages.update(page_id=sync_id, properties=notion_props)
        logger.info("Synced assignment submission back to shared DB")

    elif source_db_type == "study_log":
        mapped = schema_map.individual_study_log_to_shared(props)
        notion_props = _build_notion_props(mapped, {
            "일지제목": "title", "날짜": "date", "학습시간(분)": "number",
            "자기평가": "select", "학습내용": "rich_text", "강사코멘트": "rich_text",
        })
        if sync_id:
            notion.pages.update(page_id=sync_id, properties=notion_props)
        else:
            notion.pages.create(parent={"database_id": shared_db_id}, properties=notion_props)
        logger.info("Synced study log to shared DB")
