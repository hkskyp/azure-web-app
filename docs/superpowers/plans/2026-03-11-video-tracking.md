# Video Tracking Server Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Notion 데이터베이스의 Dropbox 동영상 시청 추적 API를 기존 FastAPI 앱에 추가

**Architecture:** SQLite(WAL) → 즉시 저장 → BackgroundTasks로 Notion 비동기 동기화. 독립 watch.html 페이지에서 HTML5 video + JS로 재생 추적.

**Tech Stack:** Python 3.13, FastAPI, SQLite3, notion-client, HTML5 Video API

**Spec:** `docs/superpowers/specs/2026-03-11-video-tracking-design.md`

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `tracking.py` | SQLite DB 초기화/CRUD + Notion API 연동 + Dropbox URL 변환 |
| Modify | `main.py` | 3개 라우트 추가 + startup에서 DB 초기화 |
| Create | `templates/watch.html` | 독립 동영상 재생 페이지 (base.html 미상속) |
| Create | `static/js/watch.js` | 재생 추적 JS (interval, sendBeacon, 이어보기) |
| Create | `static/css/watch.css` | watch 페이지 스타일 |
| Modify | `requirements.txt` | notion-client 추가 |

---

## Task 1: requirements.txt 업데이트

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1:** `requirements.txt`에 `notion-client>=2.0.0` 추가
- [ ] **Step 2:** `pip install -r requirements.txt` 실행
- [ ] **Step 3:** Commit

---

## Task 2: tracking.py — SQLite DB 모듈

**Files:**
- Create: `tracking.py`

- [ ] **Step 1:** SQLite 초기화 함수 작성

```python
import sqlite3
import os
from datetime import datetime, timezone

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
            progress REAL DEFAULT 0,
            notion_synced INTEGER DEFAULT 0,
            updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()
```

- [ ] **Step 2:** UPSERT/조회 함수 작성

```python
def upsert_watch_start(page_id: str):
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

def upsert_progress(page_id: str, current_position: float, duration: float):
    progress = (current_position / duration * 100) if duration > 0 else 0
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    conn.execute("""
        INSERT INTO watch_logs (page_id, current_position, duration, progress, notion_synced, updated_at)
        VALUES (?, ?, ?, ?, 0, ?)
        ON CONFLICT(page_id) DO UPDATE SET
            current_position = excluded.current_position,
            duration = excluded.duration,
            progress = MAX(watch_logs.progress, excluded.progress),
            notion_synced = 0,
            updated_at = excluded.updated_at
    """, (page_id, current_position, duration, progress, now))
    conn.commit()
    conn.close()
    return progress

def upsert_complete(page_id: str, current_position: float, duration: float):
    progress = (current_position / duration * 100) if duration > 0 else 0
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    conn.execute("""
        INSERT INTO watch_logs (page_id, watch_end, current_position, duration, progress, notion_synced, updated_at)
        VALUES (?, ?, ?, ?, ?, 0, ?)
        ON CONFLICT(page_id) DO UPDATE SET
            watch_end = excluded.watch_end,
            current_position = excluded.current_position,
            duration = excluded.duration,
            progress = MAX(watch_logs.progress, excluded.progress),
            notion_synced = 0,
            updated_at = excluded.updated_at
    """, (page_id, now, current_position, duration, progress, now))
    conn.commit()
    conn.close()
    return now, progress

def get_watch_log(page_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM watch_logs WHERE page_id = ?", (page_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_unsynced_logs() -> list[dict]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM watch_logs WHERE notion_synced = 0").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def mark_synced(page_id: str):
    conn = get_db()
    conn.execute("UPDATE watch_logs SET notion_synced = 1 WHERE page_id = ?", (page_id,))
    conn.commit()
    conn.close()
```

- [ ] **Step 3:** Notion API 연동 함수 작성

```python
import os
import logging
from notion_client import Client as NotionClient

logger = logging.getLogger(__name__)

def get_notion_client() -> NotionClient:
    return NotionClient(auth=os.environ.get("NOTION_API_KEY", ""))

def fetch_dropbox_url(page_id: str) -> str | None:
    """Notion 페이지에서 Dropbox URL 조회"""
    client = get_notion_client()
    page = client.pages.retrieve(page_id=page_id)
    props = page.get("properties", {})
    url_prop = props.get("Dropbox URL", {})
    return url_prop.get("url")

def convert_dropbox_url(url: str) -> str:
    """Dropbox 공유 링크를 직접 스트리밍 URL로 변환"""
    if not url:
        return ""
    url = url.split("?")[0]
    url = url.replace("www.dropbox.com", "dl.dropboxusercontent.com")
    return url

def sync_to_notion(page_id: str, properties: dict):
    """Notion 페이지 속성 업데이트 (BackgroundTask에서 호출)"""
    try:
        client = get_notion_client()
        client.pages.update(page_id=page_id, properties=properties)
        mark_synced(page_id)
        logger.info(f"Notion synced: {page_id}")
    except Exception as e:
        logger.error(f"Notion sync failed for {page_id}: {e}")

def build_notion_start_properties(watch_start: str) -> dict:
    return {
        "시청시간": {"date": {"start": watch_start}}
    }

def build_notion_progress_properties(progress: float) -> dict:
    return {
        "진행률": {"number": round(progress, 1)}
    }

def build_notion_complete_properties(watch_end: str, progress: float) -> dict:
    return {
        "시청종료": {"date": {"start": watch_end}},
        "진행률": {"number": round(progress, 1)}
    }

def retry_unsynced():
    """앱 시작 시 미동기화 레코드 재시도"""
    logs = get_unsynced_logs()
    for log in logs:
        try:
            props = {}
            if log.get("watch_start"):
                props.update(build_notion_start_properties(log["watch_start"]))
            if log.get("watch_end"):
                props.update(build_notion_complete_properties(log["watch_end"], log["progress"]))
            elif log.get("progress"):
                props.update(build_notion_progress_properties(log["progress"]))
            if props:
                sync_to_notion(log["page_id"], props)
        except Exception as e:
            logger.error(f"Retry sync failed for {log['page_id']}: {e}")
```

- [ ] **Step 4:** Commit

---

## Task 3: main.py — 라우트 추가

**Files:**
- Modify: `main.py`

- [ ] **Step 1:** import 및 startup 이벤트 추가 (main.py 상단)

```python
import re
import json
import time
from fastapi import BackgroundTasks, Body
from fastapi.responses import JSONResponse
import tracking
```

app 생성 후 startup 이벤트:

```python
@app.on_event("startup")
async def startup_event():
    tracking.init_db()
    tracking.retry_unsynced()
```

- [ ] **Step 2:** page_id 검증 + rate limiting 유틸 추가

```python
# page_id UUID 검증 (Notion page ID: 32자 hex, 하이픈 포함/미포함)
PAGE_ID_PATTERN = re.compile(r'^[a-f0-9\-]{32,36}$')

def validate_page_id(page_id: str) -> bool:
    return bool(PAGE_ID_PATTERN.match(page_id))

# Rate limiting: page_id당 최소 10초 간격
_progress_timestamps: dict[str, float] = {}

def check_rate_limit(page_id: str) -> bool:
    now = time.time()
    last = _progress_timestamps.get(page_id, 0)
    if now - last < 10:
        return False
    _progress_timestamps[page_id] = now
    return True
```

- [ ] **Step 3:** GET `/watch` 라우트 추가

```python
@app.get("/watch", response_class=HTMLResponse)
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

    # 시청 시작 기록
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
    })
```

- [ ] **Step 4:** POST `/api/tracking/progress` 라우트 추가 (JSON + sendBeacon 처리)

```python
@app.post("/api/tracking/progress")
async def tracking_progress(request: Request, background_tasks: BackgroundTasks):
    # sendBeacon은 text/plain, fetch는 application/json
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

    if not validate_page_id(page_id):
        return JSONResponse({"error": "invalid page_id"}, status_code=400)
    if not isinstance(current_position, (int, float)) or current_position < 0:
        return JSONResponse({"error": "invalid position"}, status_code=400)
    if not isinstance(duration, (int, float)) or duration <= 0:
        return JSONResponse({"error": "invalid duration"}, status_code=400)

    if not check_rate_limit(page_id):
        return JSONResponse({"status": "rate_limited"}, status_code=429)

    progress = tracking.upsert_progress(page_id, current_position, duration)
    background_tasks.add_task(
        tracking.sync_to_notion, page_id,
        tracking.build_notion_progress_properties(progress)
    )

    return JSONResponse({"status": "ok", "progress": round(progress, 1)})
```

- [ ] **Step 5:** POST `/api/tracking/complete` 라우트 추가

```python
@app.post("/api/tracking/complete")
async def tracking_complete(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid body"}, status_code=400)

    page_id = data.get("page_id", "")
    current_position = data.get("current_position", 0)
    duration = data.get("duration", 0)

    if not validate_page_id(page_id):
        return JSONResponse({"error": "invalid page_id"}, status_code=400)
    if not isinstance(current_position, (int, float)) or current_position < 0:
        return JSONResponse({"error": "invalid position"}, status_code=400)
    if not isinstance(duration, (int, float)) or duration <= 0:
        return JSONResponse({"error": "invalid duration"}, status_code=400)

    watch_end, progress = tracking.upsert_complete(page_id, current_position, duration)
    background_tasks.add_task(
        tracking.sync_to_notion, page_id,
        tracking.build_notion_complete_properties(watch_end, progress)
    )

    return JSONResponse({"status": "completed", "progress": round(progress, 1)})
```

- [ ] **Step 6:** Commit

---

## Task 4: templates/watch.html

**Files:**
- Create: `templates/watch.html`

- [ ] **Step 1:** 독립 HTML 페이지 작성 (base.html 미상속)

```html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>동영상 시청</title>
    <link rel="stylesheet" href="/static/css/watch.css">
</head>
<body>
    <!-- 헤더 배너 (추후 내용 교체) -->
    <header class="watch-header">
        <div class="banner-placeholder">배너 영역</div>
    </header>

    <!-- 메인 콘텐츠 -->
    <main class="watch-main">
        <div class="video-container">
            <video id="videoPlayer" controls preload="metadata">
                <source src="{{ stream_url }}" type="video/mp4">
                브라우저가 동영상을 지원하지 않습니다.
            </video>
        </div>

        <div class="controls-container">
            <div class="progress-info">
                <div class="progress-bar-wrapper">
                    <div class="progress-bar" id="progressBar" style="width: 0%"></div>
                </div>
                <span class="progress-text" id="progressText">0%</span>
            </div>
            <button class="complete-btn" id="completeBtn">수강 완료</button>
        </div>
    </main>

    <!-- 푸터 (추후 내용 교체) -->
    <footer class="watch-footer">
        <div class="footer-placeholder">푸터 영역</div>
    </footer>

    <script>
        window.__WATCH_CONFIG = {
            pageId: "{{ page_id }}",
            currentPosition: {{ current_position }},
        };
    </script>
    <script src="/static/js/watch.js"></script>
</body>
</html>
```

- [ ] **Step 2:** Commit

---

## Task 5: static/css/watch.css

**Files:**
- Create: `static/css/watch.css`

- [ ] **Step 1:** 미니멀 스타일 작성

```css
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Pretendard', -apple-system, sans-serif;
    background: #0a0a0a;
    color: #fff;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}

.watch-header {
    background: #1a1a2e;
    padding: 12px 24px;
    text-align: center;
}

.banner-placeholder {
    color: #888;
    font-size: 14px;
}

.watch-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 24px;
    gap: 20px;
}

.video-container {
    width: 100%;
    max-width: 960px;
}

.video-container video {
    width: 100%;
    border-radius: 8px;
    background: #000;
}

.controls-container {
    width: 100%;
    max-width: 960px;
    display: flex;
    align-items: center;
    gap: 16px;
}

.progress-info {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 12px;
}

.progress-bar-wrapper {
    flex: 1;
    height: 8px;
    background: #333;
    border-radius: 4px;
    overflow: hidden;
}

.progress-bar {
    height: 100%;
    background: #4f46e5;
    border-radius: 4px;
    transition: width 0.3s ease;
}

.progress-text {
    font-size: 14px;
    color: #ccc;
    min-width: 48px;
    text-align: right;
}

.complete-btn {
    padding: 10px 24px;
    background: #4f46e5;
    color: #fff;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    cursor: pointer;
    transition: background 0.2s;
}

.complete-btn:hover { background: #4338ca; }
.complete-btn:disabled { background: #555; cursor: not-allowed; }

.watch-footer {
    background: #1a1a2e;
    padding: 12px 24px;
    text-align: center;
}

.footer-placeholder {
    color: #888;
    font-size: 12px;
}

@media (max-width: 640px) {
    .controls-container { flex-direction: column; }
    .watch-main { padding: 12px; }
}
```

- [ ] **Step 2:** Commit

---

## Task 6: static/js/watch.js

**Files:**
- Create: `static/js/watch.js`

- [ ] **Step 1:** 재생 추적 JS 작성

```javascript
(function () {
    const config = window.__WATCH_CONFIG;
    const video = document.getElementById("videoPlayer");
    const progressBar = document.getElementById("progressBar");
    const progressText = document.getElementById("progressText");
    const completeBtn = document.getElementById("completeBtn");

    let intervalId = null;
    let hasStarted = false;
    let completed = false;

    // 이어보기: 이전 재생 위치 복원
    video.addEventListener("loadedmetadata", function () {
        if (config.currentPosition > 0) {
            video.currentTime = config.currentPosition;
        }
    });

    // 재생 시작/재개 → interval 시작
    video.addEventListener("play", function () {
        if (!hasStarted) {
            hasStarted = true;
        }
        startInterval();
    });

    // 일시정지 → interval 중지
    video.addEventListener("pause", function () {
        stopInterval();
    });

    // 영상 종료 → 자동 완료
    video.addEventListener("ended", function () {
        stopInterval();
        if (!completed) {
            sendComplete();
        }
    });

    // 30초 간격 진행률 전송
    function startInterval() {
        stopInterval();
        intervalId = setInterval(sendProgress, 30000);
    }

    function stopInterval() {
        if (intervalId) {
            clearInterval(intervalId);
            intervalId = null;
        }
    }

    function sendProgress() {
        const data = {
            page_id: config.pageId,
            current_position: video.currentTime,
            duration: video.duration,
        };
        fetch("/api/tracking/progress", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        })
            .then((r) => r.json())
            .then((res) => {
                if (res.progress !== undefined) {
                    updateProgressUI(res.progress);
                }
            })
            .catch(() => {});
    }

    function sendComplete() {
        completed = true;
        completeBtn.disabled = true;
        completeBtn.textContent = "완료됨";

        const data = {
            page_id: config.pageId,
            current_position: video.currentTime,
            duration: video.duration,
        };
        fetch("/api/tracking/complete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        })
            .then((r) => r.json())
            .then((res) => {
                if (res.progress !== undefined) {
                    updateProgressUI(res.progress);
                }
            })
            .catch(() => {});
    }

    function updateProgressUI(progress) {
        const p = Math.min(100, Math.max(0, progress));
        progressBar.style.width = p.toFixed(1) + "%";
        progressText.textContent = p.toFixed(1) + "%";
    }

    // 수강 완료 버튼
    completeBtn.addEventListener("click", function () {
        if (!completed) {
            sendComplete();
        }
    });

    // 페이지 이탈 시 sendBeacon으로 즉시 전송
    function sendBeaconProgress() {
        if (!video.duration) return;
        const data = JSON.stringify({
            page_id: config.pageId,
            current_position: video.currentTime,
            duration: video.duration,
        });
        navigator.sendBeacon("/api/tracking/progress", data);
    }

    window.addEventListener("pagehide", sendBeaconProgress);
    window.addEventListener("beforeunload", sendBeaconProgress);
})();
```

- [ ] **Step 2:** Commit

---

## Task 7: 통합 테스트

- [ ] **Step 1:** 서버 로컬 실행 (`uvicorn main:app --reload`)
- [ ] **Step 2:** `NOTION_API_KEY` 환경변수 설정 후 `/watch?id={실제 Notion page_id}` 접속 확인
- [ ] **Step 3:** 동영상 재생 → 30초 후 progress 전송 확인
- [ ] **Step 4:** 일시정지 → interval 중지 확인
- [ ] **Step 5:** 수강 완료 버튼 → Notion 속성 업데이트 확인
- [ ] **Step 6:** 페이지 새로고침 → 이어보기 확인
- [ ] **Step 7:** 최종 Commit
