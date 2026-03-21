"""Video tracking HTTP endpoints: watch page, progress, complete, refresh, preview."""

import os
import re
import json
import time

from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse

from notion_sync.tracking.state import (
    get_notion_client,
    fetch_dropbox_url,
    fetch_watch_state,
    fetch_initial_watched_time,
    get_watch_log,
    upsert_watch_start,
    upsert_progress,
    upsert_complete,
    sync_to_notion,
    build_notion_start_properties,
    build_notion_progress_properties,
    build_notion_complete_properties,
    create_watch_history_snapshot,
)
from notion_sync.tracking.video_parser import convert_dropbox_url, convert_dropbox_stream_url, probe_video_duration

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "..", "templates"))

PAGE_ID_PATTERN = re.compile(r'^[a-f0-9\-]{32,36}$')
_progress_timestamps: dict[str, float] = {}


def validate_page_id(page_id: str) -> bool:
    return bool(PAGE_ID_PATTERN.match(page_id))


def check_rate_limit(page_id: str) -> bool:
    now = time.time()
    last = _progress_timestamps.get(page_id, 0)
    if now - last < 10:
        return False
    _progress_timestamps[page_id] = now
    return True


async def parse_body(request: Request) -> dict:
    """Parse JSON body from both application/json and text/plain (sendBeacon)."""
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        return await request.json()
    body = await request.body()
    return json.loads(body.decode("utf-8"))


@router.get("/watch", response_class=HTMLResponse)
async def watch_page(request: Request, id: str, background_tasks: BackgroundTasks):
    if not id or not validate_page_id(id):
        return HTMLResponse("<h1>잘못된 요청입니다.</h1>", status_code=400)

    try:
        dropbox_url = fetch_dropbox_url(id)
    except Exception:
        return HTMLResponse("<h1>동영상 정보를 가져올 수 없습니다.</h1>", status_code=404)

    if not dropbox_url:
        return HTMLResponse("<h1>동영상 URL이 없습니다.</h1>", status_code=404)

    stream_url = convert_dropbox_stream_url(dropbox_url)

    # Anti-tampering: read watched time from SHARED page
    watched_seconds = fetch_initial_watched_time(id)

    log = get_watch_log(id)
    current_position = log["current_position"] if log else 0
    progress = log["progress"] if log else 0
    is_completed = bool(log["watch_end"]) if log else False

    watch_start = upsert_watch_start(id)
    background_tasks.add_task(
        sync_to_notion, id,
        build_notion_start_properties(watch_start)
    )

    return templates.TemplateResponse("watch.html", {
        "request": request,
        "page_id": id,
        "stream_url": stream_url,
        "current_position": current_position,
        "progress": round(progress, 1),
        "watched_seconds": round(watched_seconds, 1),
        "is_completed": is_completed,
        "preview_mode": False,
    })


@router.get("/preview", response_class=HTMLResponse)
async def preview_page(request: Request, id: str):
    """Preview mode: video playback only, NO tracking."""
    if not id or not validate_page_id(id):
        return HTMLResponse("<h1>잘못된 요청입니다.</h1>", status_code=400)

    try:
        dropbox_url = fetch_dropbox_url(id)
    except Exception:
        return HTMLResponse("<h1>동영상 정보를 가져올 수 없습니다.</h1>", status_code=404)

    if not dropbox_url:
        return HTMLResponse("<h1>동영상 URL이 없습니다.</h1>", status_code=404)

    stream_url = convert_dropbox_stream_url(dropbox_url)

    return templates.TemplateResponse("watch.html", {
        "request": request,
        "page_id": id,
        "stream_url": stream_url,
        "current_position": 0,
        "progress": 0,
        "watched_seconds": 0,
        "is_completed": False,
        "preview_mode": True,
    })


@router.post("/api/webhook/tracking/progress")
async def tracking_progress(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await parse_body(request)
    except Exception:
        return JSONResponse({"error": "invalid body"}, status_code=400)

    page_id = data.get("page_id", "")
    current_position = data.get("current_position", 0)
    duration = data.get("duration", 0)
    watched_seconds = data.get("watched_seconds", 0)

    if not validate_page_id(page_id):
        return JSONResponse({"error": "invalid page_id"}, status_code=400)
    if not isinstance(current_position, (int, float)) or current_position < 0:
        return JSONResponse({"error": "invalid position"}, status_code=400)
    if not isinstance(duration, (int, float)) or duration <= 0:
        return JSONResponse({"error": "invalid duration"}, status_code=400)
    if not isinstance(watched_seconds, (int, float)) or watched_seconds < 0:
        return JSONResponse({"error": "invalid watched_seconds"}, status_code=400)

    if not check_rate_limit(page_id):
        return JSONResponse({"status": "rate_limited"}, status_code=429)

    progress = upsert_progress(page_id, current_position, duration, watched_seconds)
    background_tasks.add_task(
        sync_to_notion, page_id,
        build_notion_progress_properties(progress, watched_seconds, duration)
    )

    return JSONResponse({"status": "ok", "progress": round(progress, 1)})


@router.post("/api/webhook/tracking/complete")
async def tracking_complete(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await parse_body(request)
    except Exception:
        return JSONResponse({"error": "invalid body"}, status_code=400)

    page_id = data.get("page_id", "")
    current_position = data.get("current_position", 0)
    duration = data.get("duration", 0)
    watched_seconds = data.get("watched_seconds", 0)

    if not validate_page_id(page_id):
        return JSONResponse({"error": "invalid page_id"}, status_code=400)
    if not isinstance(current_position, (int, float)) or current_position < 0:
        return JSONResponse({"error": "invalid position"}, status_code=400)
    if not isinstance(duration, (int, float)) or duration <= 0:
        return JSONResponse({"error": "invalid duration"}, status_code=400)

    watch_end, progress = upsert_complete(page_id, current_position, duration, watched_seconds)
    background_tasks.add_task(
        sync_to_notion, page_id,
        build_notion_complete_properties(watch_end, progress, watched_seconds, duration),
    )

    return JSONResponse({"status": "completed", "progress": round(progress, 1)})


@router.post("/api/webhook/tracking/session-end")
async def tracking_session_end(request: Request, background_tasks: BackgroundTasks):
    """Record watch history snapshot when browser closes (beforeunload)."""
    try:
        data = await parse_body(request)
    except Exception:
        return JSONResponse({"error": "invalid body"}, status_code=400)

    page_id = data.get("page_id", "")
    session_watched = data.get("session_watched_seconds", 0)
    duration = data.get("duration", 0)
    current_position = data.get("current_position", 0)
    session_start = data.get("session_start", "")

    if not validate_page_id(page_id):
        return JSONResponse({"error": "invalid page_id"}, status_code=400)

    progress = min(100.0, (current_position / duration * 100)) if duration > 0 else 0
    background_tasks.add_task(
        create_watch_history_snapshot, page_id, session_watched, duration, progress, session_start
    )
    return JSONResponse({"status": "ok"})


@router.get("/api/webhook/tracking/refresh")
async def tracking_refresh(id: str):
    """Refresh watch time / progress for a student enrollment page."""
    if not id or not validate_page_id(id):
        return JSONResponse({"error": "invalid id"}, status_code=400)

    log = get_watch_log(id)
    if not log:
        return JSONResponse({"error": "no watch log"}, status_code=404)

    watched_seconds = log["watched_seconds"] or 0
    watched_minutes = round(watched_seconds / 60, 1)
    progress = round(log["progress"], 1)

    try:
        sync_to_notion(id, {
            "시청시간(분)": {"number": watched_minutes},
            "진도율": {"number": round(progress / 100, 3)},
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    return JSONResponse({
        "status": "ok",
        "시청시간(분)": watched_minutes,
        "진도율": progress,
    })


@router.get("/api/webhook/video/duration")
async def video_duration(id: str):
    """Probe video metadata and update duration."""
    if not id or not validate_page_id(id):
        return JSONResponse({"error": "invalid id"}, status_code=400)

    try:
        dropbox_url = fetch_dropbox_url(id)
    except Exception:
        return JSONResponse({"error": "영상 정보 조회 실패"}, status_code=404)

    if not dropbox_url:
        return JSONResponse({"error": "영상 URL 없음"}, status_code=404)

    stream_url = convert_dropbox_url(dropbox_url)
    duration = probe_video_duration(stream_url)
    if duration is None:
        return JSONResponse({"error": "영상 길이 감지 실패"}, status_code=500)

    duration_minutes = round(duration / 60, 1)
    try:
        client = get_notion_client()
        client.pages.update(page_id=id, properties={
            "동영상길이(분)": {"number": duration_minutes},
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    return JSONResponse({
        "status": "ok",
        "동영상길이(분)": duration_minutes,
    })
