"""
05_소모품 reset_to_empty.py
현재 xlsx 데이터를 참고용으로 보존 후 빈 양식으로 초기화.
실행: python scripts/reset_to_empty.py
"""
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_DIR = os.path.dirname(SCRIPT_DIR)
BASE_DIR   = os.path.dirname(MODULE_DIR)
sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, BASE_DIR)

from shared.reset_utils import reset_module


if __name__ == "__main__":
    print("=" * 60)
    print(f"  [RESET] 소모품 — R5+ 데이터 비움 + 원본 참고용 보존")
    print("=" * 60)
    reset_module(MODULE_DIR)
    print("=" * 60)
    print("  다음 단계:")
    print("    1. python scripts/apply_standard.py  (스펙 20항 재적용)")
    print("=" * 60)
