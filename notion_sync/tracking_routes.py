import re
import json
import time

from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse

from . import tracking

router = APIRouter()
templates = Jinja2Templates(directory="templates")

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


@router.get("/watch", response_class=HTMLResponse)
async def watch_page(request: Request, id: str, background_tasks: BackgroundTasks):
    if not id or not validate_page_id(id):
        return HTMLResponse("<h1>잘못된 요청입니다.</h1>", status_code=400)

    try:
        dropbox_url = tracking.fetch_dropbox_url(id)
    except Exception:
        return HTMLResponse("<h1>동영상 정보를 가져올 수 없습니다.</h1>", status_code=404)

    if not dropbox_url:
        return HTMLResponse("<h1>동영상 URL이 없습니다.</h1>", status_code=404)

    stream_url = tracking.convert_dropbox_url(dropbox_url)
    log = tracking.get_watch_log(id)
    current_position = log["current_position"] if log else 0
    progress = log["progress"] if log else 0
    watched_seconds = log["watched_seconds"] if log and log["watched_seconds"] else 0
    is_completed = bool(log["watch_end"]) if log else False

    watch_start = tracking.upsert_watch_start(id)
    background_tasks.add_task(
        tracking.sync_to_notion, id,
        tracking.build_notion_start_properties(watch_start)
    )

    return templates.TemplateResponse("watch.html", {
        "request": request,
        "page_id": id,
        "stream_url": stream_url,
        "current_position": current_position,
        "progress": round(progress, 1),
        "watched_seconds": round(watched_seconds, 1),
        "is_completed": is_completed,
    })


@router.post("/api/webhook/tracking/progress")
async def tracking_progress(request: Request, background_tasks: BackgroundTasks):
    content_type = request.headers.get("content-type", "")
    try:
        if "application/json" in content_type:
            data = await request.json()
        else:
            body = await request.body()
            data = json.loads(body.decode("utf-8"))
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

    progress = tracking.upsert_progress(page_id, current_position, duration, watched_seconds)
    background_tasks.add_task(
        tracking.sync_to_notion, page_id,
        tracking.build_notion_progress_properties(progress, watched_seconds, duration)
    )

    return JSONResponse({"status": "ok", "progress": round(progress, 1)})


@router.post("/api/webhook/tracking/complete")
async def tracking_complete(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await request.json()
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

    watch_end, progress = tracking.upsert_complete(page_id, current_position, duration, watched_seconds)
    background_tasks.add_task(
        tracking.sync_to_notion, page_id,
        tracking.build_notion_complete_properties(watch_end, progress, watched_seconds, duration)
    )

    return JSONResponse({"status": "completed", "progress": round(progress, 1)})


@router.get("/api/webhook/tracking/refresh", response_class=HTMLResponse)
async def tracking_refresh(id: str):
    if not id or not validate_page_id(id):
        return HTMLResponse("<h1>잘못된 요청입니다.</h1>", status_code=400)

    log = tracking.get_watch_log(id)
    if not log:
        return HTMLResponse("<h1>시청 기록이 없습니다.</h1>", status_code=404)

    watched_seconds = log["watched_seconds"] or 0
    watched_minutes = round(watched_seconds / 60, 1)
    progress = round(log["progress"], 1)
    duration = log["duration"] or 0
    duration_minutes = round(duration / 60, 1)

    try:
        tracking.sync_to_notion(id, {
            "시청시간(분)": {"number": watched_minutes},
            "진도율": {"number": round(progress / 100, 3)},
            "동영상길이(분)": {"number": duration_minutes},
        })
        result = f"시청시간(분): {watched_minutes}분 / 진도율: {progress}% 갱신 완료"
    except Exception:
        result = "Notion 갱신에 실패했습니다."

    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><title>시청시간 갱신</title>
<style>body{{font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;background:#0a0a0a;color:#fff;margin:0}}
.card{{background:#1a1a2e;padding:32px 48px;border-radius:12px;text-align:center}}
h2{{margin:0 0 16px}}p{{color:#ccc;margin:0}}</style></head>
<body><div class="card"><h2>{result}</h2><p>이 창을 닫아도 됩니다.</p></div></body></html>""")
