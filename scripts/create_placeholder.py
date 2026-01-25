"""
Placeholder 이미지 생성 (홈페이지 스타일 맞춤)
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_placeholder():
    """홈페이지 스타일에 맞춘 깔끔한 placeholder 이미지 생성"""

    # 이미지 크기 (16:9 비율)
    width = 768
    height = 432

    # 홈페이지 컬러 팔레트
    bg_light = (248, 249, 250)  # #f8f9fa
    primary_color = (255, 75, 75)  # #ff4b4b
    text_dark = (38, 39, 48)  # #262730
    border_color = (224, 224, 230)  # #e0e0e6

    # 배경 생성 (연한 회색)
    image = Image.new('RGB', (width, height), bg_light)
    draw = ImageDraw.Draw(image)

    # 중앙 장식 요소 (둥근 테두리 사각형)
    box_width = 400
    box_height = 200
    box_x = (width - box_width) // 2
    box_y = (height - box_height) // 2

    # 테두리 그리기
    draw.rounded_rectangle(
        [(box_x, box_y), (box_x + box_width, box_y + box_height)],
        radius=20,
        outline=border_color,
        width=2
    )

    # 텍스트 추가
    try:
        # 한글 폰트 시도 (Windows)
        font_large = ImageFont.truetype("malgun.ttf", 48)
        font_small = ImageFont.truetype("malgun.ttf", 24)
    except:
        # 폰트 로드 실패 시 기본 폰트
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # "준비중" 텍스트
    text_main = "준비중"
    text_sub = "Coming Soon"

    # 텍스트 위치 계산 (중앙)
    bbox_main = draw.textbbox((0, 0), text_main, font=font_large)
    text_width_main = bbox_main[2] - bbox_main[0]
    text_height_main = bbox_main[3] - bbox_main[1]

    bbox_sub = draw.textbbox((0, 0), text_sub, font=font_small)
    text_width_sub = bbox_sub[2] - bbox_sub[0]

    x_main = (width - text_width_main) // 2
    y_main = (height - text_height_main - 40) // 2

    x_sub = (width - text_width_sub) // 2
    y_sub = y_main + text_height_main + 20

    # 메인 텍스트 (Primary 컬러)
    draw.text((x_main, y_main), text_main, font=font_large, fill=primary_color)

    # 서브 텍스트 (어두운 회색)
    draw.text((x_sub, y_sub), text_sub, font=font_small, fill=text_dark)

    # 저장 경로
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    output_path = os.path.join(project_root, "static", "images", "bible", "placeholder.webp")

    # WebP로 저장
    image.save(output_path, 'WEBP', quality=85, method=6)

    file_size = os.path.getsize(output_path) / 1024  # KB
    print(f"[OK] Placeholder 이미지 생성 완료!")
    print(f"     경로: {output_path}")
    print(f"     크기: {width}x{height}")
    print(f"     파일 크기: {file_size:.1f} KB")

if __name__ == "__main__":
    create_placeholder()
