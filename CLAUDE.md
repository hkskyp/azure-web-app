# Project Overview

Lucasoft 회사 웹사이트 - FastAPI 기반, Azure Web App 배포

## Workflow Rules (MUST)

0. **세션 시작 시**: Serena MCP 초기화 수행
   - `execute /mcp__serena__initial_instructions`
1. **작업 시작 시**: `docs/tasks/` 문서를 읽고 작업 내용 파악, Phase별 Task를 todo 리스트에 등록
   - `execute /mcp__serena__activate_project`

# Code Style

- Python 3.13 사용
- FastAPI 라우트는 main.py에 정의
- 템플릿은 Jinja2 사용, templates/ 디렉토리에 저장
- 정적 파일은 static/ 디렉토리에 저장

# Architecture

```
main.py                    # FastAPI 앱 진입점, 모든 라우트 정의
coordinate_converter.py    # 좌표 변환 유틸리티 클래스
templates/base.html        # 공통 레이아웃 (사이드바 네비게이션)
static/                    # CSS, JS, 이미지
```

# Key Patterns

- 라우트 함수는 Jinja2 TemplateResponse 반환
- 새 페이지 추가 시 base.html 상속
- 한국어 콘텐츠 사용

# Deployment

- master 브랜치 푸시 시 GitHub Actions로 Azure 자동 배포
- CI/CD 설정: .github/workflows/master_webapp.yml
