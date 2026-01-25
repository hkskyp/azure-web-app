# LucaSoft 웹사이트

LucaSoft 회사 웹사이트 (lucasoft.ai.kr) - FastAPI 기반 웹 애플리케이션

## 기술 스택
- Python 3.13 / FastAPI / Jinja2
- 서버: Uvicorn + Gunicorn
- 배포: Azure Web App (GitHub Actions CI/CD)

## 설치 및 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 로컬 실행
python main.py

# 프로덕션 실행
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 디렉토리 구조
```
├── main.py                    # FastAPI 앱 진입점
├── coordinate_converter.py    # 좌표 변환 유틸리티
├── static/                    # 정적 파일 (CSS, JS, 이미지)
├── templates/                 # Jinja2 HTML 템플릿
│   ├── base.html             # 기본 레이아웃
│   ├── home/                 # 회사 소개 페이지
│   ├── products/             # 제품 페이지
│   └── developers/           # 개발자 도구
└── .github/workflows/         # CI/CD 파이프라인
```

## 주요 라우트
- `/home` - 회사 소개
- `/history` - 회사 연혁
- `/contact` - 연락처
- `/products/rearchai` - ReArchAI 제품
- `/developers/float-bits` - IEEE 754 분석기
- `/developers/coordinate-converter` - 좌표 변환기
- `/bible-landing` - 성경 구절 랜딩 페이지 (한국어)
- `/bible-landing/en` - 성경 구절 랜딩 페이지 (영어)

## 성경 이미지 생성

### Requirements
- Python 3.10 (PyTorch는 3.13 미지원)
- NVIDIA GPU + CUDA (로컬 생성 시)

### Quick Start

```bash
# 1. 가상환경 생성 및 활성화
py -3.10 -m venv .venv-img
.venv-img\Scripts\activate

# 2. 패키지 설치
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install diffusers transformers accelerate Pillow

# 3. GPU 확인
python scripts/check_gpu.py

# 4. 이미지 생성 (자동으로 WebP로 저장)
python scripts/generate_images_diffusers.py
```

### Image Specifications
- **Format**: WebP
- **Size**: 768x432 (16:9)
- **Style**: Watercolor painting
- **File size**: < 100KB
- **Location**: `static/images/bible/`
- **Naming**: `{book}_{chapter}_{verse}.webp` (e.g., `psalm_23_1.webp`)

### Scripts
- `scripts/prompts.py` - YAML 프롬프트 로더
- `scripts/generate_images_diffusers.py` - Stable Diffusion 이미지 생성 (WebP 자동 변환)
- `scripts/check_gpu.py` - GPU/CUDA 진단
- `scripts/create_placeholder.py` - Placeholder 이미지 생성

## 배포
`master` 브랜치 푸시 시 Azure Web App으로 자동 배포

## 라이선스
Apache License 2.0
