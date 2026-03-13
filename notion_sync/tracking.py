import json
import os
import logging
import subprocess
from datetime import datetime, timezone

from notion_client import Client as NotionClient

logger = logging.getLogger(__name__)


# --- Notion API ---

def get_notion_client() -> NotionClient:
    return NotionClient(auth=os.environ.get("NOTION_API_KEY", ""))


def fetch_dropbox_url(page_id: str) -> str | None:
    client = get_notion_client()
    page = client.pages.retrieve(page_id=page_id)
    props = page.get("properties", {})
    url_prop = props.get("영상URL", {})

    # 직접 URL 속성인 경우
    if url_prop.get("type") == "url":
        return url_prop.get("url")

    # relation인 경우 — 관련 페이지에서 URL 조회
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

    return None


def probe_video_duration(url: str) -> float | None:
    """ffprobe로 영상 길이(초) 추출. ffprobe 없으면 None."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", url],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            logger.warning(f"ffprobe failed: {result.stderr[:200]}")
            return None
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except FileNotFoundError:
        logger.error("ffprobe not installed")
        return None
    except Exception as e:
        logger.error(f"probe_video_duration failed: {e}")
        return None


def convert_dropbox_url(url: str) -> str:
    if not url:
        return ""
    url = url.replace("www.dropbox.com", "dl.dropboxusercontent.com")
    url = url.replace("&dl=0", "&dl=1").replace("?dl=0", "?dl=1")
    return url


def fetch_watch_state(page_id: str) -> dict | None:
    """Notion 수강목록 페이지에서 시청 상태를 가져온다."""
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


def get_watch_log(page_id: str) -> dict | None:
    """Notion에서 현재 시청 상태 반환 (SQLite 대체)."""
    return fetch_watch_state(page_id)


def upsert_watch_start(page_id: str) -> str:
    now = datetime.now(timezone.utc).isoformat()
    return now


def upsert_progress(page_id: str, current_position: float, duration: float, watched_seconds: float) -> float:
    progress = min(100.0, max(0.0, (current_position / duration * 100))) if duration > 0 else 0
    return progress


def upsert_complete(page_id: str, current_position: float, duration: float, watched_seconds: float) -> tuple[str, float]:
    progress = min(100.0, max(0.0, (current_position / duration * 100))) if duration > 0 else 0
    now = datetime.now(timezone.utc).isoformat()
    return now, progress


def sync_to_notion(page_id: str, properties: dict):
    try:
        client = get_notion_client()
        # 개별 수강목록 페이지 업데이트
        client.pages.update(page_id=page_id, properties=properties)
        logger.info(f"Notion synced: {page_id}")

        # _sync_id가 있으면 공유 수강목록 페이지도 업데이트
        page = client.pages.retrieve(page_id=page_id)
        sync_id_prop = page.get("properties", {}).get("_sync_id", {})
        sync_id = "".join(
            t.get("plain_text", "") for t in sync_id_prop.get("rich_text", [])
        )
        if sync_id:
            client.pages.update(page_id=sync_id, properties=properties)
            logger.info(f"Shared synced: {sync_id}")
    except Exception as e:
        logger.error(f"Notion sync failed for {page_id}: {e}")


def build_notion_start_properties(watch_start: str) -> dict:
    return {
        "시청시작시간": {"date": {"start": watch_start}}
    }


def build_notion_progress_properties(progress: float, watched_seconds: float, duration: float) -> dict:
    return {
        "진도율": {"number": round(progress / 100, 3)},
        "시청시간(분)": {"number": round(watched_seconds / 60, 1)},
    }


def build_notion_complete_properties(watch_end: str, progress: float, watched_seconds: float, duration: float) -> dict:
    return {
        "시청종료시간": {"date": {"start": watch_end}},
        "진도율": {"number": round(progress / 100, 3)},
        "시청시간(분)": {"number": round(watched_seconds / 60, 1)},
    }
