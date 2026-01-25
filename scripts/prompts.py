"""
성경 구절 이미지 프롬프트 로더
YAML 파일에서 프롬프트 데이터를 읽어옴
"""

import os
import yaml

def load_prompts():
    """YAML 파일에서 프롬프트 로드"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    yaml_path = os.path.join(project_root, "data", "bible_prompts.yaml")

    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    return data

def get_prompts_list():
    """프롬프트 리스트 반환 (Stable Diffusion용)"""
    data = load_prompts()
    common = data['common']
    verses = data['verses']

    prompts = []
    for verse in verses:
        # 프롬프트 조합: verse prompt + common style
        full_prompt = f"{verse['prompt']}, {common['watercolor_style']}"

        # Negative 프롬프트 조합
        negative = common['negative_prompt'] + verse.get('negative_extra', '')

        prompts.append({
            'filename': verse['filename'],
            'verse': verse['verse'],
            'prompt': full_prompt,
            'negative': negative,
            'width': common['settings']['width'],
            'height': common['settings']['height'],
            'steps': common['settings']['steps'],
            'guidance_scale': common['settings']['guidance_scale']
        })

    return prompts

def get_total_count():
    """전체 구절 개수"""
    data = load_prompts()
    return len(data['verses'])

if __name__ == "__main__":
    # 테스트 출력
    prompts = get_prompts_list()
    print(f"[INFO] 총 {len(prompts)}개 프롬프트 로드됨\n")

    # 첫 번째 프롬프트 샘플 출력
    print("="*80)
    print(f"Sample: {prompts[0]['filename']}")
    print(f"Verse: {prompts[0]['verse']}")
    print("="*80)
    print(f"Prompt: {prompts[0]['prompt']}")
    print(f"\nNegative: {prompts[0]['negative']}")
    print(f"\nSettings: {prompts[0]['width']}x{prompts[0]['height']}, steps={prompts[0]['steps']}, cfg={prompts[0]['guidance_scale']}")
