import sqlite3
import os
import logging
from datetime import datetime, timezone

from notion_client import Client as NotionClient

logger = logging.getLogger(__name__)

# --- SQLite ---

DB_PATH = os.environ.get("TRACKING_DB_PATH", "data/tracking.db")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS watch_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id TEXT UNIQUE NOT NULL,
            watch_start TEXT,
            watch_end TEXT,
            current_position REAL DEFAULT 0,
            duration REAL DEFAULT 0,
            watched_seconds REAL DEFAULT 0,
            progress REAL DEFAULT 0,
            notion_synced INTEGER DEFAULT 0,
            updated_at TEXT
        )
    """)
    try:
        conn.execute("SELECT watched_seconds FROM watch_logs LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE watch_logs ADD COLUMN watched_seconds REAL DEFAULT 0")
    conn.commit()
    conn.close()


def upsert_watch_start(page_id: str) -> str:
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    conn.execute("""
        INSERT INTO watch_logs (page_id, watch_start, notion_synced, updated_at)
        VALUES (?, ?, 0, ?)
        ON CONFLICT(page_id) DO UPDATE SET
            watch_start = excluded.watch_start,
            notion_synced = 0,
            updated_at = excluded.updated_at
    """, (page_id, now, now))
    conn.commit()
    conn.close()
    return now


def upsert_progress(page_id: str, current_position: float, duration: float, watched_seconds: float) -> float:
    progress = min(100.0, max(0.0, (current_position / duration * 100))) if duration > 0 else 0
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    conn.execute("""
        INSERT INTO watch_logs (page_id, current_position, duration, watched_seconds, progress, notion_synced, updated_at)
        VALUES (?, ?, ?, ?, ?, 0, ?)
        ON CONFLICT(page_id) DO UPDATE SET
            current_position = excluded.current_position,
            duration = excluded.duration,
            watched_seconds = MAX(watch_logs.watched_seconds, excluded.watched_seconds),
            progress = MAX(watch_logs.progress, excluded.progress),
            notion_synced = 0,
            updated_at = excluded.updated_at
    """, (page_id, current_position, duration, watched_seconds, progress, now))
    conn.commit()
    conn.close()
    return progress


def upsert_complete(page_id: str, current_position: float, duration: float, watched_seconds: float) -> tuple[str, float]:
    progress = min(100.0, max(0.0, (current_position / duration * 100))) if duration > 0 else 0
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    conn.execute("""
        INSERT INTO watch_logs (page_id, watch_end, current_position, duration, watched_seconds, progress, notion_synced, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 0, ?)
        ON CONFLICT(page_id) DO UPDATE SET
            watch_end = excluded.watch_end,
            current_position = excluded.current_position,
            duration = excluded.duration,
            watched_seconds = MAX(watch_logs.watched_seconds, excluded.watched_seconds),
            progress = MAX(watch_logs.progress, excluded.progress),
            notion_synced = 0,
            updated_at = excluded.updated_at
    """, (page_id, now, current_position, duration, watched_seconds, progress, now))
    conn.commit()
    conn.close()
    return now, progress


def get_watch_log(page_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM watch_logs WHERE page_id = ?", (page_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_unsynced_logs() -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM watch_logs WHERE notion_synced = 0"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_synced(page_id: str):
    conn = get_db()
    conn.execute(
        "UPDATE watch_logs SET notion_synced = 1 WHERE page_id = ?", (page_id,)
    )
    conn.commit()
    conn.close()


# --- Notion API ---

def get_notion_client() -> NotionClient:
    return NotionClient(auth=os.environ.get("NOTION_API_KEY", ""))


def fetch_dropbox_url(page_id: str) -> str | None:
    client = get_notion_client()
    page = client.pages.retrieve(page_id=page_id)
    props = page.get("properties", {})
    url_prop = props.get("url", {})

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
        # 관련 DB의 URL 속성 (대문자 "URL")
        for key in ("URL", "url", "Dropbox URL"):
            if key in related_props and related_props[key].get("type") == "url":
                return related_props[key].get("url")
        return None

    return None


def convert_dropbox_url(url: str) -> str:
    if not url:
        return ""
    url = url.replace("www.dropbox.com", "dl.dropboxusercontent.com")
    url = url.replace("&dl=0", "&dl=1").replace("?dl=0", "?dl=1")
    return url


def sync_to_notion(page_id: str, properties: dict):
    try:
        client = get_notion_client()
        client.pages.update(page_id=page_id, properties=properties)
        mark_synced(page_id)
        logger.info(f"Notion synced: {page_id}")
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
        "동영상길이(분)": {"number": round(duration / 60, 1)}
    }


def build_notion_complete_properties(watch_end: str, progress: float, watched_seconds: float, duration: float) -> dict:
    return {
        "시청종료시간": {"date": {"start": watch_end}},
        "진도율": {"number": round(progress / 100, 3)},
        "시청시간(분)": {"number": round(watched_seconds / 60, 1)},
        "동영상길이(분)": {"number": round(duration / 60, 1)}
    }


def retry_unsynced():
    logs = get_unsynced_logs()
    for log in logs:
        try:
            props = {}
            if log.get("watch_start"):
                props.update(build_notion_start_properties(log["watch_start"]))
            if log.get("watch_end"):
                props.update(
                    build_notion_complete_properties(log["watch_end"], log["progress"], log.get("watched_seconds", 0), log.get("duration", 0))
                )
            elif log.get("progress"):
                props.update(build_notion_progress_properties(log["progress"], log.get("watched_seconds", 0), log.get("duration", 0)))
            if props:
                sync_to_notion(log["page_id"], props)
        except Exception as e:
            logger.error(f"Retry sync failed for {log['page_id']}: {e}")
