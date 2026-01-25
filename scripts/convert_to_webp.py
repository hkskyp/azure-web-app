"""
PNG 이미지를 WebP로 변환 및 최적화
"""
from PIL import Image
import os

def convert_to_webp(input_folder, output_folder, quality=85, delete_original=True):
    """PNG/JPG를 WebP로 변환"""

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    converted_count = 0

    for filename in os.listdir(input_folder):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            input_path = os.path.join(input_folder, filename)
            output_filename = os.path.splitext(filename)[0] + '.webp'
            output_path = os.path.join(output_folder, output_filename)

            try:
                # 이미지 열기
                img = Image.open(input_path)

                # RGB 변환 (PNG의 경우 알파 채널 제거)
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background

                # WebP로 저장
                img.save(output_path, 'WEBP', quality=quality, method=6)

                # 파일 크기 비교
                original_size = os.path.getsize(input_path) / 1024  # KB
                webp_size = os.path.getsize(output_path) / 1024  # KB
                reduction = ((original_size - webp_size) / original_size) * 100

                print(f"[OK] {filename} -> {output_filename}")
                print(f"     {original_size:.1f}KB -> {webp_size:.1f}KB (압축률: {reduction:.1f}%)")

                converted_count += 1

                # 원본 파일 삭제
                if delete_original:
                    os.remove(input_path)

            except Exception as e:
                print(f"[ERROR] {filename} 변환 실패: {e}")

    print(f"\n[완료] 총 {converted_count}개 이미지 변환 완료!")

if __name__ == "__main__":
    print("PNG/JPG -> WebP 변환 도구\n")

    # 프로젝트 루트 경로 계산
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    # 기본 경로 설정 (같은 폴더에서 PNG → WebP 변환)
    default_input = os.path.join(project_root, "static", "images", "bible")
    default_output = os.path.join(project_root, "static", "images", "bible")

    print(f"입력 폴더: {default_input}")
    print(f"출력 폴더: {default_output}")
    print(f"품질: 85 (고품질)")
    print(f"원본 삭제: 예\n")

    convert_to_webp(default_input, default_output, quality=85, delete_original=True)
