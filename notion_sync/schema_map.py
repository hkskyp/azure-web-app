"""Property mapping between shared and individual DB schemas."""


def shared_enrollment_to_individual(shared_props: dict, video_title: str = "",
                                     video_url: str = "", subject_name: str = "",
                                     sync_id: str = "") -> dict:
    """Map shared 수강목록 page properties → individual DB row."""
    return {
        "매핑제목": shared_props.get("매핑제목", ""),
        "영상제목": video_title,
        "영상URL": video_url,
        "소속과목": subject_name,
        "배정일": shared_props.get("배정일"),
        "시청시작시간": shared_props.get("시청시작시간"),
        "시청종료시간": shared_props.get("시청종료시간"),
        "진도율": shared_props.get("진도율"),
        "시청시간(분)": shared_props.get("시청시간(분)"),
        "메모": shared_props.get("메모", ""),
        "_sync_id": sync_id,
    }


def shared_assignment_to_individual(shared_props: dict, subject_name: str = "",
                                     sync_id: str = "") -> dict:
    """Map shared 과제 page properties → individual DB row."""
    return {
        "과제명": shared_props.get("과제명", ""),
        "과목명": subject_name,
        "제출여부": shared_props.get("제출여부", False),
        "제출일시": shared_props.get("제출일시"),
        "마감일": shared_props.get("마감일"),
        "점수": shared_props.get("점수"),
        "피드백": shared_props.get("피드백", ""),
        "_sync_id": sync_id,
    }


def individual_assignment_to_shared_update(ind_props: dict) -> dict:
    """Map individual 과제 changes → shared DB update (student submissions only)."""
    return {
        "제출여부": ind_props.get("제출여부"),
        "제출일시": ind_props.get("제출일시"),
    }


def individual_study_log_to_shared(ind_props: dict, student_page_id: str) -> dict:
    """Map individual 학습일지 → shared DB row."""
    return {
        "일지제목": ind_props.get("일지제목", ""),
        "날짜": ind_props.get("날짜"),
        "학습시간(분)": ind_props.get("학습시간(분)"),
        "자기평가": ind_props.get("자기평가"),
        "학습내용": ind_props.get("학습내용", ""),
        "강사코멘트": ind_props.get("강사코멘트", ""),
        "_student_page_id": student_page_id,
    }


def shared_payment_to_individual(shared_props: dict, child_name: str = "",
                                  subject_names: str = "",
                                  sync_id: str = "") -> dict:
    """Map shared 수강료 page properties → parent individual DB row."""
    return {
        "납부제목": shared_props.get("납부제목", ""),
        "자녀이름": child_name,
        "청구월": shared_props.get("청구월"),
        "수강과목": subject_names,
        "청구금액": shared_props.get("청구금액"),
        "할인금액": shared_props.get("할인금액"),
        "납부여부": shared_props.get("납부여부", False),
        "납입일자": shared_props.get("납입일자"),
        "납부메모": shared_props.get("납부메모", ""),
        "_sync_id": sync_id,
    }
