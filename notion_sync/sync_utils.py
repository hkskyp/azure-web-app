"""Sync utilities: config discovery, student DB creation and lookup.

This module is the single source of truth. It is copied to
functions/, timer/, and webapp/ at deploy time via GitHub Actions.
Do NOT edit the copies directly — edit this file instead.
"""

import logging
import os

from notion_sync import notion_helpers
from notion_sync.notion_helpers import query_database, _block_to_ds_id

logger = logging.getLogger("sync_utils")

WATCH_URL = os.environ.get("WATCH_URL", "").rstrip("/")


# ---------------------------------------------------------------------------
# Config DB discovery
# ---------------------------------------------------------------------------

_DB_NAME_MAP = {
    "학생 DB": "student",
    "수업영상 DB": "video",
    "과제 DB": "assignment",
    "학습일지 DB": "study_log",
    "시청기록 DB": "watch_history",
    "학부모 DB": "parent",
}


def discover_config_db(parent_page_id: str) -> str | None:
    """Search for 서버 설정 DB under parent page and return its data_source_id."""
    try:
        resp = notion_helpers.notion.blocks.children.list(block_id=parent_page_id)
        for block in resp.get("results", []):
            if block["type"] != "child_page":
                continue
            page_id = block["id"]
            children = notion_helpers.notion.blocks.children.list(block_id=page_id)
            for child in children.get("results", []):
                if child["type"] != "child_database":
                    continue
                title = child["child_database"].get("title", "")
                if "서버 설정" in title:
                    ds_id = _block_to_ds_id(child["id"])
                    logger.info(f"Discovered config DB: {ds_id}")
                    return ds_id
    except Exception as e:
        logger.error(f"Failed to discover config DB: {e}")
    return None


def load_shared_db_ids(config_db_id: str) -> dict:
    """Query config DB and return a dict mapping logical name to data_source_id.

    Example return: {"student": "ds-xxx", "video": "ds-yyy", ...}
    """
    result = {}
    try:
        resp = query_database(config_db_id)
        for page in resp.get("results", []):
            props = page.get("properties", {})
            db_name = "".join(
                t["plain_text"] for t in props.get("DB명", {}).get("title", [])
            )
            ds_id = "".join(
                t["plain_text"]
                for t in props.get("data_source_id", {}).get("rich_text", [])
            )
            key = _DB_NAME_MAP.get(db_name)
            if key and ds_id:
                result[key] = ds_id
        logger.info(f"Config loaded: {list(result.keys())}")
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
    return result


# ---------------------------------------------------------------------------
# Student child DB lookup (with caching)
# ---------------------------------------------------------------------------

_CHILD_DB_CACHE: dict[str, dict] = {}


def get_student_child_dbs(student_page_id: str) -> dict:
    """Get individual DB data_source_ids under a student page (cached).

    Returns: {"enrollment": ds_id, "assignment": ds_id, "study_log": ds_id}
    """
    if student_page_id in _CHILD_DB_CACHE:
        return _CHILD_DB_CACHE[student_page_id]
    resp = notion_helpers.notion.blocks.children.list(block_id=student_page_id)
    result = {}
    for block in resp.get("results", []):
        if block["type"] != "child_database":
            continue
        title = block["child_database"].get("title", "")
        ds_id = _block_to_ds_id(block["id"])
        if "수강목록" in title:
            result["enrollment"] = ds_id
        elif "과제" in title:
            result["assignment"] = ds_id
        elif "학습일지" in title:
            result["study_log"] = ds_id
    _CHILD_DB_CACHE[student_page_id] = result
    return result


# ---------------------------------------------------------------------------
# Individual DB schemas
# ---------------------------------------------------------------------------

_ENROLLMENT_SCHEMA = {
    "강의명": {"title": {}},
    "수강과목": {"rich_text": {}},
    "시청링크": {"formula": {
        "expression": f'link("\u25b6 시청하기", "{WATCH_URL}/watch?id=" + id())',
    }},
    "시청완료": {"formula": {
        "expression": 'if(prop("진도율") >= 0.9, "\u2705 완료", "\u2b1c 미완료")',
    }},
    "진도율": {"number": {"format": "percent"}},
    "시청시작시간": {"date": {}},
    "시청종료시간": {"date": {}},
    "시청시간(분)": {"number": {"format": "number"}},
    "영상URL": {"url": {}},
    "_sync_id": {"rich_text": {}},
}

_ASSIGNMENT_SCHEMA = {
    "과제명": {"title": {}},
    "과목명": {"rich_text": {}},
    "마감일": {"date": {}},
    "지각여부": {"formula": {
        "expression": (
            'if(and(prop("제출여부"), and(not(empty(prop("제출일시"))), '
            'not(empty(prop("마감일"))))), '
            'if(prop("제출일시") > prop("마감일"), "\u26a0\ufe0f 지각", "\u2705 정상"), "")'
        ),
    }},
    "제출여부": {"checkbox": {}},
    "제출일시": {"date": {}},
    "점수": {"number": {"format": "number"}},
    "피드백": {"rich_text": {}},
    "첨부파일": {"files": {}},
    "_sync_id": {"rich_text": {}},
}

_STUDY_LOG_SCHEMA = {
    "일지제목": {"title": {}},
    "날짜": {"date": {}},
    "학습과목": {"rich_text": {}},
    "학습시간(분)": {"number": {"format": "number"}},
    "자기평가": {"select": {"options": [
        {"name": "\u2b50"}, {"name": "\u2b50\u2b50"}, {"name": "\u2b50\u2b50\u2b50"},
        {"name": "\u2b50\u2b50\u2b50\u2b50"}, {"name": "\u2b50\u2b50\u2b50\u2b50\u2b50"},
    ]}},
    "학습내용": {"rich_text": {}},
    "강사코멘트": {"rich_text": {}},
    "_sync_id": {"rich_text": {}},
}


# ---------------------------------------------------------------------------
# Individual DB creation
# ---------------------------------------------------------------------------

def _create_db(title: str, page_id: str, schema: dict, icon: str):
    """Create a child database under a page (API 2025-09-03)."""
    import httpx
    resp = httpx.post(
        "https://api.notion.com/v1/databases",
        headers={
            "Authorization": f"Bearer {notion_helpers.notion.options.auth}",
            "Notion-Version": "2025-09-03",
        },
        json={
            "parent": {"type": "page_id", "page_id": page_id},
            "title": [{"type": "text", "text": {"content": title}}],
            "icon": {"type": "emoji", "emoji": icon},
            "initial_data_source": {"properties": schema},
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Parent stats DB (학습현황)
# ---------------------------------------------------------------------------

_PARENT_STATS_SCHEMA = {
    # ── 식별 ──
    "주간 · 이름": {"title": {}},
    "기간시작": {"date": {}},
    "주차": {"formula": {
        "expression": 'format(month(prop("기간시작"))) + "월 " + format(ceil(date(prop("기간시작")) / 7)) + "주차"',
    }},
    "자녀": {"select": {"options": []}},

    # ── 5개 핵심 지표 (raw data) ──
    "학습활동일": {"number": {"format": "number"}},
    "시청수": {"number": {"format": "number"}},
    "유효시청수": {"number": {"format": "number"}},
    "마감과제": {"number": {"format": "number"}},
    "제출과제": {"number": {"format": "number"}},
    "정시제출": {"number": {"format": "number"}},
    "평균점수": {"number": {"format": "number"}},
    "시청시간(분)": {"number": {"format": "number"}},
    "자습시간(분)": {"number": {"format": "number"}},

    # ── 자기평가 추이 ──
    "자기평가": {"number": {"format": "number"}},

    # ── 비율 (서버 계산, percent 포맷) ──
    "유효시청률": {"number": {"format": "percent"}},
    "과제제출률": {"number": {"format": "percent"}},

    # ── 추세 (이전 주 대비 변화량, 서버 계산) ──
    "활동일_변화": {"number": {"format": "number"}},
    "시청률_변화": {"number": {"format": "percent"}},
    "제출률_변화": {"number": {"format": "percent"}},
    "점수_변화": {"number": {"format": "number"}},
    "평가_변화": {"number": {"format": "number"}},

    # ── 종합등급 (관리자가 Notion UI에서 lets/ifs 수식으로 교체) ──
    "종합등급": {"formula": {
        "expression": '"종합등급 수식을 입력하세요"',
    }},
}

_PARENT_STATS_CACHE: dict[str, str] = {}


def ensure_parent_stats_db(parent_page_id: str) -> str:
    """학부모 페이지 하위 '학습현황' child DB 확보. 없으면 생성."""
    from notion_sync.notion_helpers import _block_to_ds_id

    if parent_page_id in _PARENT_STATS_CACHE:
        return _PARENT_STATS_CACHE[parent_page_id]

    resp = notion_helpers.notion.blocks.children.list(block_id=parent_page_id)
    for block in resp.get("results", []):
        if block["type"] != "child_database":
            continue
        title = block["child_database"].get("title", "")
        if "학습현황" in title:
            ds_id = _block_to_ds_id(block["id"])
            _PARENT_STATS_CACHE[parent_page_id] = ds_id
            return ds_id

    # 없으면 생성
    db_resp = _create_db("학습현황", parent_page_id, _PARENT_STATS_SCHEMA, "📊")
    db_block_id = db_resp["id"]
    ds_list = db_resp.get("data_sources", [])
    ds_id = ds_list[0]["id"] if ds_list else db_block_id
    # creation 시 icon 무시될 수 있으므로 PATCH
    import httpx
    try:
        httpx.patch(f"https://api.notion.com/v1/databases/{db_block_id}",
            headers={
                "Authorization": f"Bearer {notion_helpers.notion.options.auth}",
                "Notion-Version": "2025-09-03",
            },
            json={"icon": {"type": "emoji", "emoji": "📊"}},
            timeout=30)
    except Exception:
        pass
    _PARENT_STATS_CACHE[parent_page_id] = ds_id
    logger.info(f"Created 학습현황 DB for parent: {parent_page_id}")
    return ds_id


def _build_schema_with_subject(base_schema, field_name, shared_db_ids):
    """Build schema replacing field_name with subject relation if available."""
    schema = dict(base_schema)
    subject_ds = (shared_db_ids or {}).get("subject", "")
    if subject_ds:
        schema[field_name] = {"relation": {
            "data_source_id": subject_ds,
            "type": "single_property",
            "single_property": {},
        }}
    return schema


def create_student_individual_dbs(
    student_page_id: str,
    student_name: str,
    shared_db_ids: dict | None = None,
):
    """Create 3 individual DBs (enrollment, assignment, study_log) under a student page.

    Skips creation if any individual DB already exists (duplicate prevention).
    """
    existing = get_student_child_dbs(student_page_id)
    if existing:
        logger.info(f"Individual DBs already exist for {student_name}, skipping")
        return

    try:
        _create_db(f"{student_name} 수강목록", student_page_id,
                   _build_schema_with_subject(_ENROLLMENT_SCHEMA, "수강과목", shared_db_ids), "\U0001f517")
        _create_db(f"{student_name} 과제", student_page_id,
                   _build_schema_with_subject(_ASSIGNMENT_SCHEMA, "과목명", shared_db_ids), "\U0001f4dd")
        _create_db(f"{student_name} 학습일지", student_page_id,
                   _build_schema_with_subject(_STUDY_LOG_SCHEMA, "학습과목", shared_db_ids), "\U0001f4d6")
        logger.info(f"Created 3 individual DBs for student: {student_name}")
    except Exception as e:
        logger.error(
            f"Failed to create individual DBs for {student_name} ({student_page_id}): {e}"
        )
