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
    elif ptype == "url":
        return prop.get("url")
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
    "시청시간 조회": {"formula": {
        "expression": 'link("🔄 조회", "https://lucasoft.ai.kr/api/webhook/tracking/refresh?id=" + id())',
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
    try:
        r1 = _create_db(f"{student_name} 수강목록", student_page_id, _ENROLLMENT_SCHEMA, "🔗")
        notion.databases.update(database_id=r1["id"], properties=_SYNC_ID_PROP)
        r2 = _create_db(f"{student_name} 과제",     student_page_id, _ASSIGNMENT_SCHEMA,  "📝")
        notion.databases.update(database_id=r2["id"], properties=_SYNC_ID_PROP)
        r3 = _create_db(f"{student_name} 학습일지", student_page_id, _STUDY_LOG_SCHEMA,   "📖")
        notion.databases.update(database_id=r3["id"], properties=_SYNC_ID_PROP)
        logger.info(f"Created 3 individual DBs for student: {student_name}")
    except Exception as e:
        logger.error(f"Failed to create individual DBs for {student_name} ({student_page_id}): {e}")


def _find_by_sync_id(db_id: str, sync_id: str) -> str | None:
    result = _query_database(
        db_id,
        filter={"property": "_sync_id", "rich_text": {"equals": sync_id}},
    )
    pages = result.get("results", [])
    return pages[0]["id"] if pages else None


def _find_by_title(db_id: str, title: str) -> str | None:
    """개별 수강목록 DB에서 매핑제목(title)으로 페이지 찾기."""
    result = _query_database(
        db_id,
        filter={"property": "매핑제목", "title": {"equals": title}},
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
_SHARED_ASSIGNMENT_TYPES = {
    "과제명": "title", "마감일": "date",
    "제출여부": "checkbox", "제출일시": "date",
    "학생": "relation", "_sync_id": "rich_text",
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

        # relation 속성에서 추가 정보 resolve
        extra_kwargs = {}
        if source_db_type == "enrollment":
            video_ids = props.get("수업영상", []) or []
            if video_ids:
                try:
                    extra_kwargs = _resolve_video_info(video_ids[0])
                except Exception as e:
                    logger.warning(f"Failed to resolve video info: {e}")
        elif source_db_type == "assignment":
            subject_ids = props.get("과목", []) or []
            if subject_ids:
                try:
                    extra_kwargs["subject_name"] = _resolve_page_title(subject_ids[0])
                except Exception as e:
                    logger.warning(f"Failed to resolve subject name: {e}")

        for stu_page_id in student_page_ids:
            child_dbs = _get_student_child_dbs(stu_page_id)
            target_db = child_dbs.get(type_key)
            if not target_db:
                logger.warning(f"No {type_key} DB found under student {stu_page_id}")
                continue
            mapped = map_fn(props, sync_id=page_id, **extra_kwargs)
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


def _resolve_page_title(page_id: str) -> str:
    """페이지의 title 속성에서 이름을 가져온다."""
    page = notion.pages.retrieve(page_id)
    for v in page.get("properties", {}).values():
        if v.get("type") == "title":
            return "".join(t.get("plain_text", "") for t in v.get("title", []))
    return ""


def _resolve_video_info(video_page_id: str) -> dict:
    """수업영상 페이지에서 영상 정보를 가져온다."""
    page = notion.pages.retrieve(video_page_id)
    props = _extract_props(page)
    # 소속과목이 relation인 경우 과목명 조회
    subject_name = ""
    raw_props = page.get("properties", {})
    subject_prop = raw_props.get("소속과목", {})
    if subject_prop.get("type") == "relation":
        rel_ids = [r["id"] for r in subject_prop.get("relation", [])]
        if rel_ids:
            sub_page = notion.pages.retrieve(rel_ids[0])
            sub_props = _extract_props(sub_page)
            # title 속성에서 과목명 추출
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


def sync_video_to_enrollments(video_page_id: str, enrollment_db_id: str):
    """수업영상 URL 변경 시 → 관련 공유 수강목록 → 개별 학생 수강목록 업데이트."""
    if not enrollment_db_id:
        logger.warning("No enrollment DB ID; skipping video sync")
        return

    video_info = _resolve_video_info(video_page_id)
    logger.info(f"Video info: {video_info}")

    # 공유 수강목록에서 이 영상을 참조하는 페이지 찾기
    resp = _query_database(
        enrollment_db_id,
        filter={"property": "수업영상", "relation": {"contains": video_page_id}},
    )
    enrollment_pages = resp.get("results", [])
    logger.info(f"Found {len(enrollment_pages)} enrollment(s) for video {video_page_id}")

    for enroll_page in enrollment_pages:
        enroll_id = enroll_page["id"]
        enroll_props = _extract_props(enroll_page)
        student_page_ids = enroll_props.get("학생", []) or []

        for stu_page_id in student_page_ids:
            child_dbs = _get_student_child_dbs(stu_page_id)
            target_db = child_dbs.get("enrollment")
            if not target_db:
                logger.warning(f"No enrollment DB found under student {stu_page_id}")
                continue

            # 개별 수강목록에서 _sync_id로 해당 페이지 찾기
            existing = _find_by_sync_id(target_db, enroll_id)

            # _sync_id가 없으면 매핑제목으로 fallback 매칭
            if not existing:
                enroll_title = enroll_props.get("매핑제목", "")
                if enroll_title:
                    existing = _find_by_title(target_db, enroll_title)
                    if existing:
                        # _sync_id 채워넣기 (향후 매칭용)
                        notion.pages.update(page_id=existing, properties={
                            "_sync_id": {"rich_text": [{"text": {"content": enroll_id}}]}
                        })
                        logger.info(f"Backfilled _sync_id on {existing}")

            update_props = _build_notion_props({
                "영상URL": video_info["video_url"],
                "영상제목": video_info["video_title"],
                "소속과목": video_info["subject_name"],
            }, _IND_ENROLLMENT_TYPES)

            if existing:
                notion.pages.update(page_id=existing, properties=update_props)
                logger.info(f"Updated video URL on individual enrollment {existing}")
            else:
                logger.warning(f"No individual enrollment found for enroll_id={enroll_id}")


def sync_individual_to_shared(source_db_type: str, page_id: str,
                               page_data: dict, shared_db_id: str):
    """Sync an individual DB page → shared DB."""
    # 부모 DB ID는 full page object에서만 추출 가능
    parent_db_id = ""
    if "properties" in page_data:
        parent_db_id = page_data.get("parent", {}).get("database_id", "")
        props = _extract_props(page_data)
    else:
        props = page_data
        parent_db_id = page_data.get("_parent_db_id", "")
    sync_id = props.get("_sync_id", "")

    if source_db_type == "assignment_submission":
        if sync_id:
            # 기존 공유 과제 페이지 업데이트 (제출 상태만)
            update_props = schema_map.individual_assignment_to_shared_update(props)
            notion_props = _build_notion_props(update_props, {
                "제출여부": "checkbox", "제출일시": "date",
            })
            notion.pages.update(page_id=sync_id, properties=notion_props)
            logger.info("Updated assignment submission in shared DB")
        else:
            # 신규 개별 과제 → 공유 과제 DB에 신규 생성
            if not shared_db_id:
                logger.warning("SHARED_ASSIGNMENT_DB_ID not set; cannot create shared assignment")
                return
            student_page_id = ""
            if parent_db_id:
                db_result = get_db_type_from_id(parent_db_id)
                student_page_id = db_result[1] if db_result else ""
            mapped = schema_map.individual_assignment_to_shared(
                props, student_page_id=student_page_id, sync_id=page_id)
            notion_props = _build_notion_props(mapped, _SHARED_ASSIGNMENT_TYPES)
            new_page = notion.pages.create(
                parent={"database_id": shared_db_id}, properties=notion_props)
            # 개별 과제 페이지에 _sync_id 기록 (공유 페이지 ID)
            notion.pages.update(page_id=page_id, properties={
                "_sync_id": {"rich_text": [{"text": {"content": new_page["id"]}}]}
            })
            logger.info(f"Created shared assignment from individual, student={student_page_id}")

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
