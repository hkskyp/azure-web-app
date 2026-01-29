"""
SEO용 전체 성경 구절 데이터 (경량 버전)
텍스트와 참조만 포함
총 30,923개 구절
"""

import json
import os

# JSON 파일 로드
_data_dir = os.path.dirname(os.path.abspath(__file__))
_json_file = os.path.join(_data_dir, "bible_verses_seo.json")

with open(_json_file, "r", encoding="utf-8") as _f:
    _data = json.load(_f)

BIBLE_VERSES_SEO_KO = _data["ko"]
BIBLE_VERSES_SEO_EN = _data["en"]
