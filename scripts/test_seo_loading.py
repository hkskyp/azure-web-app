"""
SEO 구절 파일 로딩 속도 테스트
"""

import time
import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

print("=" * 60)
print("SEO 구절 파일 로딩 테스트")
print("=" * 60)

# SEO 파일 로딩
start = time.time()
from data.bible_verses_seo import BIBLE_VERSES_SEO_KO, BIBLE_VERSES_SEO_EN
seo_load_time = time.time() - start

print(f"로딩 시간: {seo_load_time:.3f}초")
print(f"한국어 구절: {len(BIBLE_VERSES_SEO_KO):,}개")
print(f"영어 구절: {len(BIBLE_VERSES_SEO_EN):,}개")

# 기존 파일 로딩
print("\n" + "=" * 60)
print("기존 큐레이션 파일 로딩 테스트")
print("=" * 60)

start = time.time()
from data.bible_verses import BIBLE_VERSES
from data.bible_verses_en import BIBLE_VERSES_EN
original_load_time = time.time() - start

print(f"로딩 시간: {original_load_time:.3f}초")
print(f"한국어 구절: {len(BIBLE_VERSES)}개")
print(f"영어 구절: {len(BIBLE_VERSES_EN)}개")

# 결과 비교
print("\n" + "=" * 60)
print("결과 비교")
print("=" * 60)
print(f"SEO 파일 (30,923개):  {seo_load_time:.3f}초")
print(f"큐레이션 파일 (50개):  {original_load_time:.3f}초")
print(f"속도 차이:            {seo_load_time / original_load_time:.1f}배")

print("\n" + "=" * 60)
print("FastAPI 앱 시작 시나리오")
print("=" * 60)
print(f"현재 방식:        {original_load_time:.3f}초")
print(f"SEO 통합 방식:    {seo_load_time:.3f}초")
print(f"추가 시간:        +{seo_load_time - original_load_time:.3f}초")
print("\n페이지 로딩 속도: 동일 (메모리에서 읽음)")
print("SEO 크롤링: 전체 30,923개 구절 노출")
