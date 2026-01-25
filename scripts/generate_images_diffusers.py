"""
Stable Diffusion - diffusers 라이브러리로 성경 이미지 생성
YAML 프롬프트 기반 전체 이미지 생성
"""

import os
import sys
from PIL import Image

# 프로젝트 루트를 sys.path에 추가
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

# 프롬프트 데이터 import
from scripts.prompts import get_prompts_list, get_total_count

def generate_all_images():
    """
    전체 성경 구절 이미지 생성
    """
    # 패키지 임포트 시도
    try:
        from diffusers import StableDiffusionXLPipeline
        import torch
        from tqdm import tqdm
    except ImportError as e:
        print("[ERROR] 패키지가 설치되지 않았습니다.")
        print("\n다음 명령어를 실행하세요:")
        print("pip install diffusers transformers accelerate torch torchvision tqdm pyyaml")
        return

    print("="*80)
    print("성경 구절 이미지 생성 (Stable Diffusion)")
    print("="*80)

    # 프롬프트 로드
    prompts = get_prompts_list()
    total = len(prompts)
    print(f"\n[INFO] 총 {total}개 이미지 생성 예정")

    # GPU/CPU 확인
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[INFO] 사용 디바이스: {device}")

    if device == "cpu":
        print("[WARNING] GPU가 없어 CPU로 실행됩니다.")
        print(f"[WARNING] 예상 시간: 약 {total * 2}분")
        proceed = input("\n계속하시겠습니까? (y/n): ")
        if proceed.lower() != 'y':
            return
    else:
        gpu_name = torch.cuda.get_device_name(0)
        print(f"[INFO] GPU: {gpu_name}")
        print(f"[INFO] 예상 시간: 약 {total * 0.2:.1f}분 (GPU 기준)")

    # 출력 디렉토리 설정
    output_dir = os.path.join(project_root, "static", "images", "bible")
    os.makedirs(output_dir, exist_ok=True)
    print(f"[INFO] 저장 경로: {output_dir}\n")

    # 모델 로드 (SDXL 사용)
    print("[INFO] Stable Diffusion XL 모델 로딩 중... (첫 실행 시 약 7GB 다운로드)")

    pipe = StableDiffusionXLPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        use_safetensors=True,
        variant="fp16" if device == "cuda" else None
    )
    pipe = pipe.to(device)

    # 메모리 최적화
    if device == "cuda":
        pipe.enable_attention_slicing()

    print("[OK] 모델 로드 완료!\n")

    # 이미지 생성
    success_count = 0
    failed_list = []

    for idx, item in enumerate(tqdm(prompts, desc="이미지 생성 중")):
        try:
            # 이미지 생성
            image = pipe(
                prompt=item['prompt'],
                negative_prompt=item['negative'],
                num_inference_steps=item['steps'],
                guidance_scale=item['guidance_scale'],
                width=item['width'],
                height=item['height']
            ).images[0]

            # 저장
            output_path = os.path.join(output_dir, item['filename'])
            image.save(output_path)

            success_count += 1

        except Exception as e:
            print(f"\n[ERROR] {item['filename']} 생성 실패: {e}")
            failed_list.append(item['filename'])

    # 결과 출력
    print("\n" + "="*80)
    print("생성 완료!")
    print("="*80)
    print(f"[OK] 성공: {success_count}/{total}개")

    if failed_list:
        print(f"[ERROR] 실패: {len(failed_list)}개")
        print("실패한 파일:")
        for filename in failed_list:
            print(f"  - {filename}")

    print(f"\n[INFO] 저장 경로: {output_dir}")
    print(f"\n다음 단계: WebP 변환")
    print("python scripts/convert_to_webp.py")

if __name__ == "__main__":
    generate_all_images()
