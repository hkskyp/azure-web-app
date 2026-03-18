"""Notion watch-state management: read/write tracking data."""

import os
import logging
from datetime import datetime, timezone

from notion_client import Client as NotionClient

logger = logging.getLogger("webapp.tracking.state")


# ── Notion API ─────────────────────────────────────────────────────────────

def get_notion_client() -> NotionClient:
    return NotionClient(auth=os.environ.get("NOTION_API_KEY", ""))


def fetch_dropbox_url(page_id: str) -> str | None:
    """Read the video URL from an individual enrollment page."""
    client = get_notion_client()
    page = client.pages.retrieve(page_id=page_id)
    props = page.get("properties", {})
    url_prop = props.get("영상URL", {})

    # Direct URL property
    if url_prop.get("type") == "url":
        return url_prop.get("url")

    # Relation: look up the related page for a URL
    if url_prop.get("type") == "relation":
        relations = url_prop.get("relation", [])
        if not relations:
            return None
        related_page = client.pages.retrieve(page_id=relations[0]["id"])
        related_props = related_page.get("properties", {})
        for key in ("URL", "url", "영상URL", "Dropbox URL"):
            if key in related_props and related_props[key].get("type") == "url":
                return related_props[key].get("url")
        return None

    # Rollup: extract URL from rollup array
    if url_prop.get("type") == "rollup":
        rollup = url_prop.get("rollup", {})
        for item in rollup.get("array", []):
            if item.get("type") == "url" and item.get("url"):
                return item["url"]
        return None

    return None


# ── Watch state ────────────────────────────────────────────────────────────

def fetch_watch_state(page_id: str) -> dict | None:
    """Read watch state from an individual enrollment page in Notion."""
    try:
        client = get_notion_client()
        page = client.pages.retrieve(page_id=page_id)
        props = page.get("properties", {})

        watched_minutes = (props.get("시청시간(분)") or {}).get("number") or 0
        duration_minutes = (props.get("동영상길이(분)") or {}).get("number") or 0
        progress_ratio = (props.get("진도율") or {}).get("number") or 0
        watch_end_date = (props.get("시청종료시간") or {}).get("date") or {}

        duration_seconds = duration_minutes * 60
        return {
            "current_position": progress_ratio * duration_seconds,
            "duration": duration_seconds,
            "progress": round(progress_ratio * 100, 1),
            "watched_seconds": watched_minutes * 60,
            "watch_end": watch_end_date.get("start"),
        }
    except Exception as e:
        logger.error(f"Failed to fetch watch state from Notion ({page_id}): {e}")
        return None


def fetch_initial_watched_time(page_id: str) -> float:
    """Read watched time from the individual enrollment page. Returns seconds."""
    try:
        client = get_notion_client()
        page = client.pages.retrieve(page_id=page_id)
        props = page.get("properties", {})
        watched_minutes = (props.get("시청시간(분)") or {}).get("number") or 0
        return watched_minutes * 60
    except Exception as e:
        logger.error(f"Failed to fetch initial watched time for {page_id}: {e}")
        return 0.0


def get_watch_log(page_id: str) -> dict | None:
    """Return current watch state from Notion."""
    return fetch_watch_state(page_id)


# ── Watch event helpers ────────────────────────────────────────────────────

def upsert_watch_start(page_id: str) -> str:
    """Record watch start; returns ISO timestamp."""
    now = datetime.now(timezone.utc).isoformat()
    return now


def upsert_progress(page_id: str, current_position: float,
                     duration: float, watched_seconds: float) -> float:
    """Calculate progress percentage from position/duration."""
    progress = min(100.0, max(0.0, (current_position / duration * 100))) if duration > 0 else 0
    return progress


def upsert_complete(page_id: str, current_position: float,
                     duration: float, watched_seconds: float) -> tuple[str, float]:
    """Mark watch as complete; returns (end_timestamp, progress)."""
    progress = min(100.0, max(0.0, (current_position / duration * 100))) if duration > 0 else 0
    now = datetime.now(timezone.utc).isoformat()
    return now, progress


# ── Notion sync ────────────────────────────────────────────────────────────

def sync_to_notion(page_id: str, properties: dict):
    """Update individual enrollment page with tracking properties."""
    try:
        client = get_notion_client()
        client.pages.update(page_id=page_id, properties=properties)
        logger.info(f"Notion synced (individual): {page_id}")
    except Exception as e:
        logger.error(f"Notion sync failed for {page_id}: {e}")


def create_watch_history_snapshot(page_id: str, watched_seconds: float,
                                   duration: float, progress: float,
                                   session_start: str = ""):
    """Create a new watch history record (INSERT only, no update).

    Called on browser close (beforeunload) and watch complete.
    Each session produces a separate record for statistics.
    """
    try:
        from notion_sync.routes import SHARED_DB_IDS
        from notion_helpers import normalize_page_id
        watch_history_db = SHARED_DB_IDS.get("watch_history", "")
        if not watch_history_db:
            logger.warning("watch_history DB not configured, skipping")
            return

        client = get_notion_client()

        # Read individual enrollment page
        page = client.pages.retrieve(page_id=page_id)
        page_props = page.get("properties", {})

        # Get video title
        title_parts = page_props.get("강의명", {}).get("title", [])
        video_title = "".join(t.get("plain_text", "") for t in title_parts) if title_parts else "시청기록"

        # Find student page_id and name from individual enrollment DB's parent
        student_rel = []
        student_name = ""
        parent_info = page.get("parent", {})
        parent_db_id = parent_info.get("database_id", "") or parent_info.get("data_source_id", "")
        if parent_db_id:
            from notion_sync.sync.student_dbs import _retrieve_database
            try:
                db_info = _retrieve_database(parent_db_id)
                student_page_id = db_info.get("parent", {}).get("page_id", "")
                if student_page_id:
                    student_rel = [student_page_id]
                    stu_page = client.pages.retrieve(student_page_id)
                    for v in stu_page.get("properties", {}).values():
                        if v.get("type") == "title":
                            student_name = "".join(
                                t.get("plain_text", "") for t in v.get("title", []))
                            break
            except Exception:
                pass

        # Get video page ID from enrollment's _sync_id
        video_rel = []
        sync_id_parts = page_props.get("_sync_id", {}).get("rich_text", [])
        video_page_id = "".join(t.get("plain_text", "") for t in sync_id_parts)
        if video_page_id:
            video_rel = [video_page_id]

        # Get subject from enrollment's 수강과목 relation
        subject_rel = []
        subject_prop = page_props.get("수강과목", {})
        if subject_prop.get("type") == "relation":
            subject_rel = [r["id"] for r in subject_prop.get("relation", [])]

        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        watched_min = round(watched_seconds / 60, 1)

        # Title: "영상제목 - 학생명 - 2026.03.18 14:30 (45분)"
        date_str = now.strftime("%Y.%m.%d %H:%M")
        parts = [video_title]
        if student_name:
            parts.append(student_name)
        parts.append(f"{date_str} ({watched_min}분)")
        record_title = " - ".join(parts)

        history_props = {
            "시청기록": {"title": [{"text": {"content": record_title}}]},
            "시청일": {"date": {"start": now_iso}},
            "시청시간(분)": {"number": watched_min},
            "진도율": {"number": round(progress / 100, 3)},
            "종료시간": {"date": {"start": now_iso}},
            "_sync_id": {"rich_text": [{"text": {"content": normalize_page_id(page_id)}}]},
        }
        if session_start:
            history_props["시작시간"] = {"date": {"start": session_start}}
        if student_rel:
            history_props["학생"] = {"relation": [{"id": sid} for sid in student_rel]}
        if video_rel:
            history_props["수업영상"] = {"relation": [{"id": vid} for vid in video_rel]}
        if subject_rel:
            history_props["수강과목"] = {"relation": [{"id": sid} for sid in subject_rel]}

        client.pages.create(parent={"data_source_id": watch_history_db}, properties=history_props)
        logger.info(f"Watch history snapshot created for {page_id}")
    except Exception as e:
        logger.error(f"Failed to create watch history snapshot: {e}")


# ── Property builders ─────────────────────────────────────────────────────

def build_notion_start_properties(watch_start: str) -> dict:
    return {
        "시청시작시간": {"date": {"start": watch_start}}
    }


def build_notion_progress_properties(progress: float, watched_seconds: float,
                                      duration: float) -> dict:
    return {
        "진도율": {"number": round(progress / 100, 3)},
        "시청시간(분)": {"number": round(watched_seconds / 60, 1)},
    }


def build_notion_complete_properties(watch_end: str, progress: float,
                                      watched_seconds: float, duration: float) -> dict:
    return {
        "시청종료시간": {"date": {"start": watch_end}},
        "진도율": {"number": round(progress / 100, 3)},
        "시청시간(분)": {"number": round(watched_seconds / 60, 1)},
    }
