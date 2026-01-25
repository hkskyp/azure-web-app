"""
bible_prompts.yaml에서 SEO용 경량 구절 데이터 생성
텍스트와 참조만 포함 (프롬프트, 이미지 정보 제외)
"""

import yaml
import json
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
data_dir = os.path.join(project_root, 'data')

yaml_file = os.path.join(data_dir, 'bible_prompts.yaml')
output_json = os.path.join(data_dir, 'bible_verses_seo.json')
output_py = os.path.join(data_dir, 'bible_verses_seo.py')

print(f"YAML 로딩 중: {yaml_file}")
with open(yaml_file, 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

print(f"총 {len(data['verses'])}개 구절 로드됨")

# 경량 구절 데이터 생성 (텍스트와 참조만)
verses_ko = []
verses_en = []

for idx, verse in enumerate(data['verses'], 1):
    # 한국어 버전 파싱 ("창세기 1:1" 또는 "사무엘상 1:1")
    ko_ref = verse['verse']
    ko_parts = ko_ref.rsplit(' ', 1)  # 마지막 공백으로 분리
    ko_book = ko_parts[0]
    ko_chapter_verse = ko_parts[1].split(':')

    ko_entry = {
        'id': idx,
        'text': verse['text_ko'],
        'reference': {
            'book': ko_book,
            'chapter': int(ko_chapter_verse[0]),
            'verse': int(ko_chapter_verse[1])
        }
    }
    verses_ko.append(ko_entry)

    # 영어 버전 파싱 ("Genesis 1:1" 또는 "1 Samuel 1:1")
    en_ref = verse['verse_en']
    en_parts = en_ref.rsplit(' ', 1)  # 마지막 공백으로 분리
    en_book = en_parts[0]
    en_chapter_verse = en_parts[1].split(':')

    en_entry = {
        'id': idx,
        'text': verse['text_en'],
        'reference': {
            'book': en_book,
            'chapter': int(en_chapter_verse[0]),
            'verse': int(en_chapter_verse[1])
        }
    }
    verses_en.append(en_entry)

# JSON 파일 생성
print(f"JSON 파일 생성 중: {output_json}")
with open(output_json, 'w', encoding='utf-8') as f:
    json.dump({
        'ko': verses_ko,
        'en': verses_en
    }, f, ensure_ascii=False, indent=2)

json_size = os.path.getsize(output_json) / 1024 / 1024
print(f"  - JSON 파일 크기: {json_size:.2f} MB")

# Python 파일 생성 (JSON 로더)
print(f"Python 파일 생성 중: {output_py}")
with open(output_py, 'w', encoding='utf-8') as f:
    f.write('"""\n')
    f.write('SEO용 전체 성경 구절 데이터 (경량 버전)\n')
    f.write('텍스트와 참조만 포함\n')
    f.write(f'총 {len(verses_ko):,}개 구절\n')
    f.write('"""\n\n')
    f.write('import json\n')
    f.write('import os\n\n')
    f.write('# JSON 파일 로드\n')
    f.write('_data_dir = os.path.dirname(os.path.abspath(__file__))\n')
    f.write('_json_file = os.path.join(_data_dir, "bible_verses_seo.json")\n\n')
    f.write('with open(_json_file, "r", encoding="utf-8") as _f:\n')
    f.write('    _data = json.load(_f)\n\n')
    f.write('BIBLE_VERSES_SEO_KO = _data["ko"]\n')
    f.write('BIBLE_VERSES_SEO_EN = _data["en"]\n')

print(f"완료!")
print(f"  - 한국어 구절: {len(verses_ko):,}개")
print(f"  - 영어 구절: {len(verses_en):,}개")
print(f"  - JSON 파일: {output_json} ({json_size:.2f} MB)")
print(f"  - Python 파일: {output_py}")
