from datetime import datetime
from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.responses import PlainTextResponse
from starlette.middleware.gzip import GZipMiddleware
from coordinate_converter import CoordinateConverter
from data.certificates import CERTIFICATES
from data.bible_verses import BIBLE_VERSES
from data.bible_verses_en import BIBLE_VERSES_EN
from data.bible_verses_seo import BIBLE_VERSES_SEO_KO, BIBLE_VERSES_SEO_EN

# FastAPI 앱 생성
app = FastAPI(
    title="lucasoft에 오신걸 환영합니다",
    description="고객의 아이디어를 현실로 만드는 SW 개발 파트너",
    version="1.0.0"
)

# GZip 압축 미들웨어 (500바이트 이상 응답 압축)
app.add_middleware(GZipMiddleware, minimum_size=500)

# 정적 파일 서빙 설정
app.mount("/static", StaticFiles(directory="static"), name="static")

# 템플릿 설정
templates = Jinja2Templates(directory="templates")
templates.env.globals["current_year"] = datetime.now().year

converter = CoordinateConverter()

@app.get("/")
async def root():
    """루트 경로를 홈으로 리다이렉트"""
    return RedirectResponse(url="/home")

# robots.txt를 루트 경로에서 직접 서빙
@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    with open("static/robots.txt", "r") as f:
        return f.read()
    
@app.get("/home", response_class=HTMLResponse)
async def home_page(request: Request):
    """홈 페이지"""
    return templates.TemplateResponse(
        "home/intro.html", 
        {"request": request, "current_page": "home"}
    )

@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    """회사 연혁 페이지"""
    return templates.TemplateResponse(
        "home/history.html",
        {"request": request, "current_page": "history"}
    )

@app.get("/contact", response_class=HTMLResponse)
async def contact_page(request: Request):
    """연락처 페이지"""
    return templates.TemplateResponse(
        "home/contact.html",
        {"request": request, "current_page": "contact"}
    )

@app.get("/certificate", response_class=HTMLResponse)
async def certificate_page(request: Request):
    """인증현황 페이지"""
    return templates.TemplateResponse(
        "home/certificate.html",
        {"request": request, "current_page": "certificate", "certificates": CERTIFICATES}
    )

@app.get("/products/rearchai", response_class=HTMLResponse)
async def rearchai_page(request: Request):
    """ReArchAI 페이지"""
    return templates.TemplateResponse(
        "products/rearchai.html",
        {"request": request, "current_page": "rearchai"}
    )

@app.get("/products/wes", response_class=HTMLResponse)
async def wes_page(request: Request):
    """WES 무장 효과 분석 시뮬레이션 페이지"""
    return templates.TemplateResponse(
        "products/wes.html",
        {"request": request, "current_page": "wes"}
    )

@app.get("/bible", response_class=HTMLResponse)
async def bible_landing_page(request: Request, lang: str = "ko"):
    """성경 구절 랜딩 페이지 (한국어/English)"""
    # 언어 파라미터 검증 (ko 또는 en만 허용)
    if lang not in ["ko", "en"]:
        lang = "ko"

    # SEO용: 전체 30,923개 구절 (크롤러에게 노출)
    all_verses_seo = BIBLE_VERSES_SEO_KO if lang == "ko" else BIBLE_VERSES_SEO_EN

    return templates.TemplateResponse(
        "bible/landing.html",
        {
            "request": request,
            "current_page": "bible",
            "lang": lang,
            "all_verses": all_verses_seo  # SEO용 전체 구절 (30,923개)
        }
    )

@app.get("/api/bible-verses/random")
async def get_random_bible_verses(count: int = 3, ids: str = None):
    """랜덤 성경 구절 API (한국어) - 전체 30,923개 중 선택

    Args:
        count: 반환할 구절 수 (기본값: 3)
        ids: 쉼표로 구분된 id 목록 (예: "1,3,5")
    """
    import random

    if ids:
        # 특정 id들의 구절 반환
        id_list = [int(id.strip()) for id in ids.split(',')]
        selected = [v for v in BIBLE_VERSES_SEO_KO if v['id'] in id_list]
    else:
        # 전체 30,923개 중 랜덤 선택
        selected = random.sample(BIBLE_VERSES_SEO_KO, min(count, len(BIBLE_VERSES_SEO_KO)))

    return JSONResponse(content={"verses": selected})

@app.get("/api/bible-verses/random/en")
async def get_random_bible_verses_en(count: int = 3, ids: str = None):
    """Random Bible Verses API (English) - Select from all 30,923 verses

    Args:
        count: Number of verses to return (default: 3)
        ids: Comma-separated list of IDs (e.g., "1,3,5")
    """
    import random

    if ids:
        # Return specific verses by IDs
        id_list = [int(id.strip()) for id in ids.split(',')]
        selected = [v for v in BIBLE_VERSES_SEO_EN if v['id'] in id_list]
    else:
        # Random selection from all 30,923 verses
        selected = random.sample(BIBLE_VERSES_SEO_EN, min(count, len(BIBLE_VERSES_SEO_EN)))

    return JSONResponse(content={"verses": selected})

@app.get("/developers/float-bits", response_class=HTMLResponse)
async def float_bits_page(request: Request):
    """IEEE 754 부동소수점 비트 표현 분석기"""
    return templates.TemplateResponse(
        "developers/float_bits.html", 
        {"request": request, "current_page": "float-bits"}
    )

@app.get("/developers/coordinate-converter", response_class=HTMLResponse)
async def coordinate_converter_page(request: Request):
    """지리 좌표 변환기"""
    return templates.TemplateResponse(
        "developers/coordinate_converter.html", 
        {"request": request, "current_page": "coordinate-converter"}
    )


@app.post("/developers/coordinate-converter", response_class=HTMLResponse)
async def convert_coordinates(
    request: Request,
    coord_type: str = Form(...),
    lat: float = Form(None),
    lon: float = Form(None),
    zone_number: int = Form(None),
    zone_letter: str = Form(None),
    easting: float = Form(None),
    northing: float = Form(None),
    mgrs_coord: str = Form(None)
):
    result = {}
    try:
        if coord_type == "latlon":
            if converter.validate_lat_lon(lat, lon):
                result["lat"], result["lon"] = lat, lon
            else:
                raise ValueError("Invalid Latitude/Longitude")

        elif coord_type == "utm":
            if zone_letter and zone_number:
                latlon = converter.utm_to_lat_lon(zone_number, zone_letter.upper(), easting, northing)
                result["lat"], result["lon"] = latlon
            else:
                raise ValueError("Invalid UTM Zone")

        elif coord_type == "mgrs":
            if converter.validate_mgrs(mgrs_coord):
                result["lat"], result["lon"] = converter.mgrs_to_lat_lon(mgrs_coord.upper())
            else:
                raise ValueError("Invalid MGRS")

        lat, lon = result["lat"], result["lon"]
        result["utm"] = converter.lat_lon_to_utm(lat, lon)
        result["mgrs"] = converter.lat_lon_to_mgrs(lat, lon)
    except Exception as e:
        result["error"] = str(e)

    return templates.TemplateResponse("developers/coordinate_converter.html", {"request": request, "result": result})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)