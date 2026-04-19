"""
01_검사기_완제품 reset_to_empty.py

현재 xlsx 데이터(R5+)를 _참고용_원본데이터/{timestamp}/ 하위로 백업 후
빈 양식으로 초기화. 실행 후 sync.py + apply_standard.py로 스펙 준수 마무리.

실행: python scripts/reset_to_empty.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import MODULE_DIR, TYPE_NAME
from shared.reset_utils import reset_module


if __name__ == "__main__":
    print("=" * 60)
    print(f"  [RESET] {TYPE_NAME} — R5+ 데이터 비움 + 원본 참고용 보존")
    print("=" * 60)
    reset_module(MODULE_DIR)
    print("=" * 60)
    print("  다음 단계:")
    print("    1. python scripts/sync.py            (빈 상태에서 대장 정리)")
    print("    2. python scripts/apply_standard.py  (스펙 20항 재적용)")
    print("=" * 60)
