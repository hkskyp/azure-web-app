"""
GPU 및 CUDA 설치 상태 확인
"""

print("=" * 50)
print("GPU 진단 스크립트")
print("=" * 50)

# 1. PyTorch 설치 확인
try:
    import torch
    print("\n[OK] PyTorch 설치됨")
    print(f"    버전: {torch.__version__}")
except ImportError:
    print("\n[ERROR] PyTorch가 설치되지 않았습니다.")
    print("    pip install torch torchvision 실행 필요")
    exit(1)

# 2. CUDA 사용 가능 여부
cuda_available = torch.cuda.is_available()
print(f"\n[INFO] CUDA 사용 가능: {cuda_available}")

if cuda_available:
    print(f"    CUDA 버전: {torch.version.cuda}")
    print(f"    GPU 개수: {torch.cuda.device_count()}")
    print(f"    현재 GPU: {torch.cuda.current_device()}")
    print(f"    GPU 이름: {torch.cuda.get_device_name(0)}")
    print(f"    GPU 메모리: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
else:
    print("\n[WARNING] CUDA를 사용할 수 없습니다.")
    print("\n가능한 원인:")
    print("  1. CPU 버전의 PyTorch가 설치됨")
    print("  2. NVIDIA 그래픽 드라이버 미설치")
    print("  3. CUDA Toolkit 미설치")

    print("\n해결 방법:")
    print("  1. PyTorch 재설치 (CUDA 버전):")
    print("     pip uninstall torch torchvision torchaudio")
    print("     pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
    print("\n  2. NVIDIA 드라이버 확인:")
    print("     nvidia-smi 명령어 실행")

# 3. NVIDIA 드라이버 확인
print("\n" + "=" * 50)
print("NVIDIA 드라이버 확인")
print("=" * 50)
import subprocess
try:
    result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
    if result.returncode == 0:
        print("\n[OK] NVIDIA 드라이버 설치됨")
        print(result.stdout)
    else:
        print("\n[ERROR] nvidia-smi 실행 실패")
except FileNotFoundError:
    print("\n[ERROR] nvidia-smi를 찾을 수 없습니다.")
    print("    NVIDIA 그래픽 드라이버가 설치되지 않았습니다.")
    print("    https://www.nvidia.com/Download/index.aspx 에서 드라이버 다운로드")

print("\n" + "=" * 50)
