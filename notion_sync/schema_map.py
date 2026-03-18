"""Property mapping between shared and individual DB schemas."""


def shared_enrollment_to_individual(shared_props: dict, video_title: str = "",
                                     video_url: str = "", subject_page_ids: list = None,
                                     sync_id: str = "") -> dict:
    result = {
        "강의명": shared_props.get("강의명", ""),
        "영상URL": video_url,
        "시청시작시간": shared_props.get("시청시작시간"),
        "시청종료시간": shared_props.get("시청종료시간"),
        "진도율": shared_props.get("진도율"),
        "시청시간(분)": shared_props.get("시청시간(분)"),
        "_sync_id": sync_id,
    }
    if subject_page_ids:
        result["수강과목"] = subject_page_ids
    return result


def shared_assignment_to_individual(shared_props: dict, subject_page_ids: list = None,
                                     sync_id: str = "") -> dict:
    result = {
        "과제명": shared_props.get("과제명", ""),
        "마감일": shared_props.get("마감일"),
        "점수": shared_props.get("점수"),
        "피드백": shared_props.get("피드백", ""),
        "_sync_id": sync_id,
    }
    if subject_page_ids:
        result["과목명"] = subject_page_ids
    return result


def individual_assignment_to_shared(ind_props: dict, student_page_id: str = "",
                                     subject_page_ids: list = None,
                                     sync_id: str = "") -> dict:
    result = {
        "과제명": ind_props.get("과제명", ""),
        "마감일": ind_props.get("마감일"),
        "제출여부": ind_props.get("제출여부", False),
        "제출일시": ind_props.get("제출일시"),
        "학생": [student_page_id] if student_page_id else [],
        "_sync_id": sync_id,
    }
    if subject_page_ids:
        result["과목"] = subject_page_ids
    return result


def individual_assignment_to_shared_update(ind_props: dict) -> dict:
    return {
        "제출여부": ind_props.get("제출여부"),
        "제출일시": ind_props.get("제출일시"),
    }


def individual_study_log_to_shared(ind_props: dict) -> dict:
    return {
        "일지제목": ind_props.get("일지제목", ""),
        "날짜": ind_props.get("날짜"),
        "학습시간(분)": ind_props.get("학습시간(분)"),
        "자기평가": ind_props.get("자기평가"),
        "학습내용": ind_props.get("학습내용", ""),
        "강사코멘트": ind_props.get("강사코멘트", ""),
    }
