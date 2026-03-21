"""Weekly stats engine — aggregate learning data per parent."""

import logging

from notion_sync import notion_helpers
from notion_sync.notion_helpers import (
    query_database, query_database_all, extract_props, build_notion_props,
    api_call,
)
from notion_sync.sync_utils import ensure_parent_stats_db

from notion_sync.routes import SHARED_DB_IDS

logger = logging.getLogger("webapp.stats.engine")


# ---------------------------------------------------------------------------
# Prop types for stats row creation
# ---------------------------------------------------------------------------

_STATS_PROP_TYPES = {
    "주간 · 이름": "title",
    "기간시작": "date",
    "자녀": "select",
    "학습활동일": "number",
    "시청수": "number",
    "유효시청수": "number",
    "마감과제": "number",
    "제출과제": "number",
    "정시제출": "number",
    "평균점수": "number",
    "시청시간(분)": "number",
    "자습시간(분)": "number",
    "자기평가": "number",
    "유효시청률": "number",
    "과제제출률": "number",
    "활동일_변화": "number",
    "시청률_변화": "number",
    "제출률_변화": "number",
    "점수_변화": "number",
    "평가_변화": "number",
}

# Star select → numeric mapping
_STAR_MAP = {"⭐": 1, "⭐⭐": 2, "⭐⭐⭐": 3, "⭐⭐⭐⭐": 4, "⭐⭐⭐⭐⭐": 5}


# ---------------------------------------------------------------------------
# Reference page creation (1회만 생성)
# ---------------------------------------------------------------------------

_REFERENCE_CREATED = False


def _ensure_reference_pages():
    """NOTION_PARENT_PAGE_ID 하위에 참고문헌 + 지표 구성 설명 페이지 생성 (1회)."""
    global _REFERENCE_CREATED
    if _REFERENCE_CREATED:
        return

    import os
    parent_id = os.environ.get("NOTION_PARENT_PAGE_ID", "").strip()
    if not parent_id:
        logger.warning("NOTION_PARENT_PAGE_ID not set — skipping reference page creation")
        return

    # 이미 존재하는지 확인
    try:
        resp = notion_helpers.notion.blocks.children.list(block_id=parent_id)
        for block in resp.get("results", []):
            if block["type"] == "child_page":
                title = block.get("child_page", {}).get("title", "")
                if "학습현황 참고 자료" in title:
                    _REFERENCE_CREATED = True
                    return
    except Exception:
        return

    try:
        # 상위 페이지: 학습현황 리포트
        container = api_call(notion_helpers.notion.pages.create,
            parent={"page_id": parent_id},
            icon={"type": "external", "external": {
                "url": "https://www.notion.so/icons/chart-bar_blue.svg"}},
            properties={"title": [{"text": {"content": "학습현황 참고 자료"}}]},
        )
        container_id = container["id"]

        # 하위 페이지 2개
        _create_reference_page(container_id)
        _create_metrics_page(container_id)
        _REFERENCE_CREATED = True
        logger.info("Created 학습현황 리포트 + sub-pages under parent")
    except Exception as e:
        logger.error(f"Failed to create reference pages: {e}")


def _build_reference_blocks() -> list:
    """참고 문헌 블록 목록 반환."""
    return [
        _h2("참고 문헌"),
        _divider(),

        _h3("[#1] Fredricks, Blumenfeld & Paris (2004)"),
        _para("School Engagement: Potential of the Concept, State of the Evidence"),
        _bullet_link("원문 보기", "https://journals.sagepub.com/doi/10.3102/00346543074001059"),
        _bullet("적용: 학생 참여의 3차원 모델 (행동적·인지적·정서적) → 시청(행동) + 과제(인지) + 자기평가(정서)"),
        _divider(),

        _h3("[#2] J-PAL — 학부모 문자 메시지 RCT"),
        _para("Sending text-messages to parents to improve student achievement"),
        _bullet_link("원문 보기", "https://www.povertyactionlab.org/evaluation/sending-text-messages-parents-improve-student-achievement-middle-and-high-schools-united"),
        _bullet('인용: "treatment group failed 0.71 classes vs control 0.97 (27% 감소)"'),
        _divider(),

        _h3("[#4] Langberg et al. (2016)"),
        _para("Longitudinal Evaluation of the Importance of Homework Assignment Completion"),
        _bullet_link("원문 보기", "https://pmc.ncbi.nlm.nih.gov/articles/PMC5134299/"),
        _bullet('인용: "academically impaired = 45% 제출, non-impaired = 83.7%"'),
        _divider(),

        _h3("[#6] Fleming & Lau (2014)"),
        _para("How to measure metacognition"),
        _bullet_link("원문 보기", "https://pmc.ncbi.nlm.nih.gov/articles/PMC4097944/"),
        _bullet("적용: 자기평가-점수 직접 비교는 구인 불일치로 부적절 → 추세 비교만 사용"),
        _divider(),

        _h3("[#7] IES (2014)"),
        _para("Effects of Increased Learning Time on Student Academic and Nonacademic Outcomes"),
        _bullet_link("원문 보기", "https://ies.ed.gov/use-work/resource-library/report/descriptive-study/effects-increased-learning-time-student-academic-and-nonacademic-outcomes-findings-meta-analytic"),
        _bullet("적용: 학습시간 증가 효과는 교사 주도 수업에서만 유의미 → 시청/자습 분리 표시"),
        _divider(),

        _h3("[#8] Cristia et al. (2024)"),
        _para("Streaking to Success: Effects of Highlighting Streaks on Student Effort"),
        _bullet_link("원문 보기", "https://publications.iadb.org/publications/english/document/Streaking-to-Success-The-Effects-of-Highlighting-Streaks-on-Student-Effort-and-Achievement.pdf"),
        _bullet("적용: 학습 일관성 강조 → 학습활동일(/7) 지표 근거"),
        _divider(),

        _h3("[#9] Wu et al. (2023)"),
        _para("Using learning analytics with temporal modeling to uncover before-class video viewing engagement"),
        _bullet_link("원문 보기 (DOI)", "https://doi.org/10.1016/j.compedu.2023.104975"),
        _bullet('인용: "consistent viewing pattern has significant relationship with academic performance"'),
        _divider(),

        _h3("[#10] Cuccolo & DeBruler (2024)"),
        _para("Assignment submission patterns and performance in K-12 online STEM courses"),
        _bullet_link("원문 보기", "https://www.tandfonline.com/doi/full/10.1080/23735082.2024.2441113"),
        _bullet('인용: "submitting out of order negatively correlated with final grades"'),
        _divider(),

        _h3("[#12] IES (2020)"),
        _para("Can Texting Parents Improve Attendance in Elementary School?"),
        _bullet_link("원문 보기", "https://ies.ed.gov/ncee/pubs/2020006/"),
        _bullet('인용: "reduced chronic absence but did not improve achievement after one school year"'),
    ]


def _create_reference_page(parent_id: str):
    """참고 문헌 페이지 생성."""
    page = api_call(notion_helpers.notion.pages.create,
        parent={"page_id": parent_id},
        icon={"type": "external", "external": {
            "url": "https://www.notion.so/icons/book_blue.svg"}},
        properties={"title": [{"text": {"content": "참고 문헌"}}]},
    )
    _append_blocks_batched(page["id"], _build_reference_blocks())


def _build_metrics_blocks() -> list:
    """지표 구성 설명 블록 목록 반환."""
    return [
        _h2("5개 핵심 지표"),
        _divider(),

        _h3("1. 학습활동일 (/7)"),
        _bullet("정의: 7일 중 시청/과제/학습일지 활동이 있는 날 수"),
        _bullet("공식: 시청일 ∪ 제출일 ∪ 학습일지 날짜의 고유 날짜 count"),
        _bullet("근거: 학습 일관성이 성과와 유의미한 관계 [#8]"),
        _divider(),

        _h3("2. 유효시청률"),
        _bullet("정의: 실질적으로 시청한 영상 비율"),
        _bullet("공식: 유효시청수 / 전체 시청수"),
        _bullet("유효시청 = (시청비율 + 진도율) / 2 ≥ 0.6"),
        _bullet("시청비율 = 시청시간(분) / 동영상길이(분)"),
        _bullet("진도율 = track bar 위치 (0~1.0)"),
        _bullet("근거: 일관된 시청 패턴이 주간 성과와 유의미한 관계 [#9]"),
        _callout("⚠️", "알려진 한계: 50% 수강 + trackbar 100% 이동 vs 2x 배속 완강은 현재 구별 불가"),
        _divider(),

        _h3("3. 과제제출률"),
        _bullet("정의: 해당 주 마감 과제 중 제출 완료 비율"),
        _bullet("공식: 제출과제 / 마감과제"),
        _bullet("보조: 정시제출 (마감일 이내 제출 수)"),
        _bullet("근거: 미제출 학생 45% vs 정상 83.7% [#4], K-12 제출 패턴 [#10]"),
        _divider(),

        _h3("4. 평균점수"),
        _bullet("정의: 해당 주 점수가 있는 과제의 평균"),
        _bullet("공식: sum(점수) / count(점수 있는 과제)"),
        _bullet("근거: 학부모에게 성적 요약 제공 → 학업 실패 27% 감소 [#2]"),
        _divider(),

        _h3("5. 시청시간(분) + 자습시간(분)"),
        _bullet("정의: 영상 시청시간과 학습일지 자습시간을 분리 표시"),
        _bullet("시청시간(분) = 서버 측 Date.now() 델타 누적 (조작 불가)"),
        _bullet("자습시간(분) = 학습일지에 학생이 기록한 시간"),
        _bullet("근거: 학습시간 증가 효과는 교사 주도 시만 유효 → 분리 필요 [#7]"),
        _divider(),

        _h3("자기평가 추이"),
        _bullet("정의: 학습일지 자기평가(1~5)의 주간 평균"),
        _bullet("용도: 주간 추세 비교용 (절대값 해석 부적절)"),
        _bullet("근거: 괴리도 공식은 척도·구인·시점 불일치로 무효 [#6]"),
        _divider(),

        _h2("유효시청 검증 케이스"),
        _table(
            ["시나리오", "시청비율", "진도율", "점수", "판정"],
            [
                ["1x 완강", "1.0", "1.0", "1.0", "유효"],
                ["1.5x 완강", "0.67", "1.0", "0.84", "유효"],
                ["2x 완강", "0.50", "1.0", "0.75", "유효"],
                ["70% 정상 시청", "0.70", "0.70", "0.70", "유효"],
                ["1분+trackbar 100%", "0.03", "1.0", "0.52", "무효"],
                ["재시청 10% 중단", "0.10", "0.10", "0.10", "무효"],
                ["절반만 시청", "0.50", "0.50", "0.50", "무효"],
            ],
        ),
    ]


def _create_metrics_page(parent_id: str):
    """지표 구성 설명 페이지 생성."""
    page = api_call(notion_helpers.notion.pages.create,
        parent={"page_id": parent_id},
        icon={"type": "external", "external": {
            "url": "https://www.notion.so/icons/science_blue.svg"}},
        properties={"title": [{"text": {"content": "학습현황 지표 구성 설명"}}]},
    )
    _append_blocks_batched(page["id"], _build_metrics_blocks())


# ---------------------------------------------------------------------------
# Block helpers (inline — guide_blocks는 builder 전용)
# ---------------------------------------------------------------------------

def _h2(t):
    return {"type": "heading_2", "heading_2": {"rich_text": [{"text": {"content": t}}]}}

def _h3(t):
    return {"type": "heading_3", "heading_3": {"rich_text": [{"text": {"content": t}}]}}

def _para(t):
    return {"type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": t}}]}}

def _bullet(t):
    return {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"text": {"content": t}}]}}

def _bullet_link(label, url):
    return {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [
        {"type": "text", "text": {"content": label, "link": {"url": url}}}
    ]}}

def _callout(emoji, t):
    return {"type": "callout", "callout": {"rich_text": [{"text": {"content": t}}], "icon": {"emoji": emoji}}}

def _divider():
    return {"type": "divider", "divider": {}}

def _table(headers, rows):
    def _cell(text):
        return [{"type": "text", "text": {"content": str(text)}}]
    table_rows = [
        {"type": "table_row", "table_row": {"cells": [_cell(h) for h in headers]}}
    ]
    for row in rows:
        table_rows.append(
            {"type": "table_row", "table_row": {"cells": [_cell(c) for c in row]}}
        )
    return {
        "type": "table",
        "table": {
            "table_width": len(headers),
            "has_column_header": True,
            "has_row_header": False,
            "children": table_rows,
        },
    }


def _append_blocks_batched(page_id: str, blocks: list, batch_size: int = 100):
    """Notion API limit: 100 blocks per request."""
    for i in range(0, len(blocks), batch_size):
        api_call(notion_helpers.notion.blocks.children.append,
                 block_id=page_id, children=blocks[i:i + batch_size])


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_weekly_stats(week_start: str, week_end: str):
    """학부모별 주간 학습현황 생성 (background task)."""
    logger.info(f"Generating weekly stats: {week_start} ~ {week_end}")

    # 관리자 참고문헌/지표 페이지 생성 (최초 1회)
    _ensure_reference_pages()

    # 1. 배치 쿼리
    watch_records = query_database_all(SHARED_DB_IDS.get("watch_history", ""),
        filter={"and": [
            {"property": "시청일", "date": {"on_or_after": week_start}},
            {"property": "시청일", "date": {"on_or_before": week_end}},
        ]})

    # 영상 동영상길이 맵 구축 (유효시청 판정용)
    video_ids = _collect_video_ids(watch_records, "수업영상")
    video_durations = _fetch_video_durations(video_ids)

    assignment_records = query_database_all(SHARED_DB_IDS.get("assignment", ""),
        filter={"and": [
            {"property": "마감일", "date": {"on_or_after": week_start}},
            {"property": "마감일", "date": {"on_or_before": week_end}},
        ]})

    study_log_records = query_database_all(SHARED_DB_IDS.get("study_log", ""),
        filter={"and": [
            {"property": "날짜", "date": {"on_or_after": week_start}},
            {"property": "날짜", "date": {"on_or_before": week_end}},
        ]})

    # 2. student_id 기준 그룹화
    watch_by_student = _group_by_student(watch_records, "학생")
    assign_by_student = _group_by_student(assignment_records, "학생")
    log_by_student = _group_by_student(study_log_records, "학생")

    # 3. 학생 이름 맵 구축
    student_names = _build_student_name_map(SHARED_DB_IDS.get("student", ""))

    # 4. 학부모별 처리 (_new 제외, rate limit은 api_call 429 retry로 자동 처리)
    parents = query_database_all(SHARED_DB_IDS.get("parent", ""))
    parents = [p for p in parents
               if (extract_props(p).get("학부모명") or "") != "_new"]
    logger.info(f"Processing {len(parents)} parents, "
                f"records: watch={len(watch_records)}, "
                f"assign={len(assignment_records)}, log={len(study_log_records)}")

    for parent in parents:
        try:
            _process_parent(parent, week_start, week_end, student_names,
                            watch_by_student, assign_by_student, log_by_student,
                            video_durations)
        except Exception as e:
            logger.error(f"Parent stats failed: {parent['id']}: {e}")
            continue

    logger.info(f"Weekly stats complete: {week_start} ~ {week_end}")


# ---------------------------------------------------------------------------
# Data collection helpers
# ---------------------------------------------------------------------------

def _collect_video_ids(watch_records: list, relation_prop: str) -> set:
    """시청기록에서 고유 영상 page_id 수집."""
    ids = set()
    for rec in watch_records:
        props = rec.get("properties", {})
        rel = props.get(relation_prop, {})
        for r in rel.get("relation", []):
            ids.add(r["id"])
    return ids


def _fetch_video_durations(video_ids: set) -> dict:
    """영상 page_id → 동영상길이(분) 딕셔너리 구축."""
    durations = {}
    for vid in video_ids:
        try:
            page = api_call(notion_helpers.notion.pages.retrieve, vid)
            props = extract_props(page)
            duration = props.get("동영상길이(분)")
            if duration and duration > 0:
                durations[vid] = duration
        except Exception as e:
            logger.warning(f"Failed to fetch video duration {vid}: {e}")
    return durations


def _group_by_student(records: list, student_prop: str) -> dict:
    """records를 student_id 기준으로 그룹화."""
    grouped = {}
    for rec in records:
        props = rec.get("properties", {})
        rel = props.get(student_prop, {})
        for r in rel.get("relation", []):
            sid = r["id"]
            grouped.setdefault(sid, []).append(rec)
    return grouped


def _build_student_name_map(student_db_id: str) -> dict:
    """학생 DB 전체 조회 → {page_id: 이름} 맵."""
    if not student_db_id:
        return {}
    names = {}
    students = query_database_all(student_db_id)
    for s in students:
        props = extract_props(s)
        name = props.get("이름", "")
        if name:
            names[s["id"]] = name
    return names


# ---------------------------------------------------------------------------
# Per-parent processing
# ---------------------------------------------------------------------------

def _process_parent(parent, week_start, week_end, student_names,
                    watch_by_student, assign_by_student, log_by_student,
                    video_durations):
    """학부모 1명 처리: 자녀별 주간 통계 row 생성."""
    props = extract_props(parent)
    child_ids = props.get("자녀") or []
    if not child_ids:
        return

    stats_db_id = ensure_parent_stats_db(parent["id"])

    for child_id in child_ids:
        try:
            child_name = student_names.get(child_id)
            if not child_name:
                continue  # 자녀가 아직 등록되지 않음
            title = f"{week_start[5:].replace('-', '.')}~{week_end[5:].replace('-', '.')} · {child_name}"

            # 중복 방지
            existing = query_database(stats_db_id,
                filter={"property": "주간 · 이름", "title": {"equals": title}})
            if existing.get("results"):
                continue

            # 통계 계산
            watch = _compute_watch_stats(
                watch_by_student.get(child_id, []), video_durations)
            assign = _compute_assignment_stats(
                assign_by_student.get(child_id, []))
            study = _compute_study_log_stats(
                log_by_student.get(child_id, []))
            active_days = _compute_active_days(
                child_id, watch_by_student, assign_by_student, log_by_student)

            # 추세: 이전 주 row 조회 → 변화량 계산
            current = {"학습활동일": active_days, **watch, **assign, **study}
            prev = _fetch_previous_week(stats_db_id, child_name, week_start)
            trends = _compute_trends(current, prev)

            # row 생성
            _create_stats_row(stats_db_id, title, week_start, child_name,
                              active_days, watch, assign, study, trends)
        except Exception as e:
            logger.error(f"Child stats failed: {child_id}: {e}")
            continue


# ---------------------------------------------------------------------------
# Stats computation
# ---------------------------------------------------------------------------

def _compute_watch_stats(records: list, video_durations: dict) -> dict:
    """시청수, 유효시청수, 시청시간(분) 계산."""
    total = len(records)
    effective = 0
    total_minutes = 0.0

    for rec in records:
        props = extract_props(rec)
        watch_min = props.get("시청시간(분)") or 0
        progress = props.get("진도율") or 0
        total_minutes += watch_min

        # 영상 길이 조회
        raw_props = rec.get("properties", {})
        rel = raw_props.get("수업영상", {})
        video_ids = [r["id"] for r in rel.get("relation", [])]
        video_id = video_ids[0] if video_ids else None

        video_len = video_durations.get(video_id, 0) if video_id else 0

        # 유효시청 판정: (시청비율 + 진도율) / 2 >= 0.6
        watch_ratio = (watch_min / video_len) if video_len > 0 else 0
        score = (watch_ratio + progress) / 2
        if score >= 0.6:
            effective += 1

    return {
        "시청수": total,
        "유효시청수": effective,
        "시청시간(분)": round(total_minutes, 1),
    }


def _compute_assignment_stats(records: list) -> dict:
    """마감과제, 제출과제, 정시제출, 평균점수 계산."""
    total = len(records)
    submitted = 0
    on_time = 0
    scores = []

    for rec in records:
        props = extract_props(rec)
        is_submitted = props.get("제출여부", False)
        if is_submitted:
            submitted += 1
            # 정시 판정: 제출일시 <= 마감일
            submit_date = props.get("제출일시", "")
            deadline = props.get("마감일", "")
            if submit_date and deadline and submit_date <= deadline:
                on_time += 1

        score = props.get("점수")
        if score is not None:
            scores.append(score)

    avg_score = round(sum(scores) / len(scores), 1) if scores else 0

    return {
        "마감과제": total,
        "제출과제": submitted,
        "정시제출": on_time,
        "평균점수": avg_score,
    }


def _compute_study_log_stats(records: list) -> dict:
    """자습시간(분), 자기평가 평균 계산."""
    total_minutes = 0.0
    ratings = []

    for rec in records:
        props = extract_props(rec)
        minutes = props.get("학습시간(분)") or 0
        total_minutes += minutes

        rating_text = props.get("자기평가", "")
        if rating_text and rating_text in _STAR_MAP:
            ratings.append(_STAR_MAP[rating_text])

    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0

    return {
        "자습시간(분)": round(total_minutes, 1),
        "자기평가": avg_rating,
    }


def _compute_active_days(child_id, watch_by, assign_by, log_by) -> int:
    """3개 소스에서 고유 날짜 union → count."""
    dates = set()

    for rec in watch_by.get(child_id, []):
        props = extract_props(rec)
        d = props.get("시청일")
        if d:
            dates.add(d[:10])  # date part only

    for rec in assign_by.get(child_id, []):
        props = extract_props(rec)
        d = props.get("제출일시")
        if d:
            dates.add(d[:10])

    for rec in log_by.get(child_id, []):
        props = extract_props(rec)
        d = props.get("날짜")
        if d:
            dates.add(d[:10])

    return len(dates)


# ---------------------------------------------------------------------------
# Trend computation
# ---------------------------------------------------------------------------

def _fetch_previous_week(stats_db_id: str, child_name: str, current_week_start: str) -> dict | None:
    """동일 자녀의 이전 주 row 조회 → extract_props 반환."""
    from datetime import datetime, timedelta
    prev_start = (datetime.strptime(current_week_start, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")
    try:
        result = query_database(stats_db_id, filter={"and": [
            {"property": "자녀", "select": {"equals": child_name}},
            {"property": "기간시작", "date": {"equals": prev_start}},
        ]})
        pages = result.get("results", [])
        if not pages:
            return None
        return extract_props(pages[0])
    except Exception:
        return None


def _compute_trends(current: dict, prev: dict | None) -> dict:
    """이전 주 대비 변화량 계산. prev=None이면 빈 dict."""
    if prev is None:
        return {"활동일_변화": 0, "시청률_변화": 0, "제출률_변화": 0, "점수_변화": 0, "평가_변화": 0}

    def _safe(v):
        return v if v is not None else 0

    def _ratio(num_key, den_key, d):
        n, d_ = _safe(d.get(num_key)), _safe(d.get(den_key))
        return n / d_ if d_ > 0 else 0

    def _delta(curr, prev_val):
        return round(curr - prev_val, 2)

    return {
        "활동일_변화": _delta(_safe(current.get("학습활동일")), _safe(prev.get("학습활동일"))),
        "시청률_변화": _delta(
            _ratio("유효시청수", "시청수", current),
            _ratio("유효시청수", "시청수", prev)),
        "제출률_변화": _delta(
            _ratio("제출과제", "마감과제", current),
            _ratio("제출과제", "마감과제", prev)),
        "점수_변화": _delta(_safe(current.get("평균점수")), _safe(prev.get("평균점수"))),
        "평가_변화": _delta(_safe(current.get("자기평가")), _safe(prev.get("자기평가"))),
    }


# ---------------------------------------------------------------------------
# Row creation
# ---------------------------------------------------------------------------

def _create_stats_row(db_id, title, week_start, child_name,
                      active_days, watch, assign, study, trends=None):
    """학습현황 DB에 주간 통계 row 생성."""
    # 비율 계산 (percent 포맷: 0.67 → Notion에서 67% 표시)
    watch_rate = watch["유효시청수"] / watch["시청수"] if watch["시청수"] > 0 else 0
    submit_rate = assign["제출과제"] / assign["마감과제"] if assign["마감과제"] > 0 else 0

    data = {
        "주간 · 이름": title,
        "기간시작": week_start,
        "자녀": child_name,
        "학습활동일": active_days,
        **watch,
        **assign,
        **study,
        "유효시청률": round(watch_rate, 2),
        "과제제출률": round(submit_rate, 2),
        **(trends or {}),
    }
    props = build_notion_props(data, _STATS_PROP_TYPES)
    api_call(notion_helpers.notion.pages.create,
             parent={"data_source_id": db_id},
             properties=props)
