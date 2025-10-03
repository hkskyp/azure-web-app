from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.responses import PlainTextResponse
from coordinate_converter import CoordinateConverter

# FastAPI 앱 생성
app = FastAPI(
    title="lucasoft에 오신걸 환영합니다",
    description="고객의 아이디어를 현실로 만드는 SW 개발 파트너",
    version="1.0.0"
)

# 정적 파일 서빙 설정
app.mount("/static", StaticFiles(directory="static"), name="static")

# 템플릿 설정
templates = Jinja2Templates(directory="templates")

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

@app.get("/products/rearchai", response_class=HTMLResponse)
async def rearchai_page(request: Request):
    """ReArchAI 페이지"""
    return templates.TemplateResponse(
        "products/rearchai.html",
        {"request": request, "current_page": "rearchai"}
    )

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