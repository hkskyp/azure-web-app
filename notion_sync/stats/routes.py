"""Weekly parent stats report endpoint."""

import logging
import os

from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import JSONResponse

from notion_sync.stats.engine import generate_weekly_stats

logger = logging.getLogger("webapp.stats")
router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.post("/weekly-report")
async def weekly_report(request: Request, background_tasks: BackgroundTasks):
    """주간 학습현황 리포트 생성 (background task)."""
    # Bearer token 인증
    secret = os.environ.get("STATS_API_SECRET", "")
    if secret:
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {secret}":
            return JSONResponse({"status": "unauthorized"}, status_code=401)
    else:
        logger.warning("STATS_API_SECRET not set — auth disabled")

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"status": "error", "reason": "invalid JSON body"},
            status_code=400)

    week_start = body.get("week_start", "")
    week_end = body.get("week_end", "")
    if not week_start or not week_end:
        return JSONResponse(
            {"status": "error", "reason": "week_start and week_end required"},
            status_code=400)

    background_tasks.add_task(generate_weekly_stats, week_start, week_end)
    return JSONResponse({"status": "accepted"}, status_code=202)
