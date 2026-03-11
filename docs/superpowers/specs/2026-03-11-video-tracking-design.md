# Video Tracking Server Design

## Overview

Notion 데이터베이스의 Dropbox 동영상 시청 추적 서버. 기존 FastAPI 앱에 API를 추가하여 Azure Web App에서 운영.

## User Flow

1. Notion 데이터베이스 행의 URL 속성 클릭 (`https://서버/watch?id={notion_page_id}`)
2. 서버가 Notion API로 해당 행의 Dropbox URL 조회 (`pages.retrieve(page_id)` 사용, database_id 불필요)
3. 동영상 재생 페이지 렌더링, 시청시간을 현재 시간으로 업데이트
4. 재생 중 30초 간격으로 진행률 서버에 전송 (일시정지 시 중지)
5. "수강 완료" 버튼 클릭 또는 영상 끝까지 재생 시 시청종료 + 진행률 업데이트
6. 페이지 이탈 시 현재 재생 위치 즉시 전송 (sendBeacon)
7. 새로고침/재진입 시 이전 재생 위치부터 이어보기

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/watch` | 동영상 재생 페이지 (query: `id={notion_page_id}`) |
| POST | `/api/tracking/progress` | 재생 위치 주기적 저장 (JSON + sendBeacon text/plain 둘 다 처리) |
| POST | `/api/tracking/complete` | 수강 완료 처리 |

### Request/Response Schemas

**POST `/api/tracking/progress`**
```json
{ "page_id": "string", "current_position": 0.0, "duration": 0.0 }
```

**POST `/api/tracking/complete`**
```json
{ "page_id": "string", "current_position": 0.0, "duration": 0.0 }
```

**GET `/watch`** template context:
```json
{ "page_id": "string", "dropbox_url": "string", "current_position": 0.0 }
```

## Data Model

### SQLite (`data/tracking.db`)

- DB 경로: Azure에서 영속적 스토리지 `/home/data/tracking.db` 사용
- WAL 모드 활성화 (동시성 개선)
- 앱 시작 시 테이블 자동 생성 (startup event)

Table: `watch_logs`

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto increment |
| page_id | TEXT UNIQUE | Notion 페이지 ID |
| watch_start | TEXT | 시청 시작 시간 (ISO 8601) |
| watch_end | TEXT | 시청 종료 시간 |
| current_position | REAL | 마지막 재생 위치 (초) |
| duration | REAL | 동영상 전체 길이 (초) |
| progress | REAL | 진행률 (0.0~100.0) — 최대 도달 재생 위치 기준 |
| notion_synced | INTEGER | Notion 동기화 완료 여부 (0/1) |
| updated_at | TEXT | 마지막 업데이트 시간 |

- `page_id` UNIQUE — 같은 동영상 재시청 시 UPSERT (이력 미보존, 최신 상태만 유지)
- Dropbox URL은 캐시하지 않음, 매번 Notion API에서 조회
- progress = 최대 도달 재생 위치 비율 (중간 건너뛰기 방지는 하지 않음)

## Notion Integration

- Package: `notion-client`
- Auth: 환경변수 `NOTION_API_KEY`
- 속성명은 모든 데이터베이스에서 동일 (하드코딩)
- API 호출: `pages.retrieve(page_id)` / `pages.update(page_id)` — database_id 불필요

### Notion Property Mapping

| Notion 속성 | Type | Server Action |
|-------------|------|---------------|
| Dropbox URL | URL | GET `/watch` 시 조회 |
| 시청시간 | Date | 시청 시작 시 현재 시간 기록 |
| 시청종료 | Date | 수강 완료 시 현재 시간 기록 |
| 진행률 | Number | `(current_position / duration) * 100` |

## Async Processing

1. 클라이언트 요청 → SQLite에 즉시 저장 → 200 응답 반환
2. FastAPI `BackgroundTasks`로 Notion API 업데이트 실행
3. 진행률 주기 전송(30초)마다 SQLite + Notion 동시 비동기 업데이트
4. 성공 시 `notion_synced = 1`, 실패 시 `0` 유지
5. 실패한 동기화: 앱 시작 시 `notion_synced = 0`인 레코드를 재동기화 시도

## Security

- page_id 입력값 검증 (UUID 형식, 32자 hex)
- API 요청 본문 크기 제한
- current_position / duration 범위 검증 (음수, 비정상 값 차단)
- Rate limiting: page_id당 progress 요청 10초 간격 제한
- SQLite 파라미터 바인딩 (SQL injection 방지)
- CORS 설정: 허용된 origin만

## Frontend

### Template: `templates/watch.html`

- `base.html` 상속하지 않음 — 독립된 단독 페이지
- Dropbox 공유 링크를 직접 스트리밍 URL로 변환 (`www.dropbox.com` → `dl.dropboxusercontent.com`, `dl=0` → `dl=1`)
- HTML5 `<video>` 태그 사용
- 헤더: 고정 배너 (광고성 텍스트/이미지, 서버 하드코딩)
- 푸터: 별도 고정 콘텐츠 (서버 하드코딩)
- 본문: 동영상 플레이어 + 진행률 바 + 수강완료 버튼 (미니멀)

### JavaScript Logic

- `video.onplay` → 30초 interval 시작, 최초 재생 시 시청 시작 알림
- `video.onpause` → interval 중지
- `video.onended` → interval 중지 + 자동 complete 호출
- `setInterval(30s)` → `POST /api/tracking/progress` (재생 중에만)
- "수강 완료" 버튼 → `POST /api/tracking/complete`
- `beforeunload` / `pagehide` → `navigator.sendBeacon`으로 현재 위치 즉시 전송
- 페이지 로드 시 SQLite의 `current_position`으로 이어보기 (`video.currentTime` 설정)

## Tech Stack

- Python 3.13, FastAPI (기존 앱 확장)
- SQLite3 (Python 내장, WAL 모드)
- notion-client (Notion API) — requirements.txt에 추가 필요
- Azure Web App (기존 배포 파이프라인)

## Environment Variables

- `NOTION_API_KEY`: Notion Integration 토큰
