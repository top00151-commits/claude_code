"""
╔══════════════════════════════════════════════════════════════╗
║  05_소모품 apply_standard.py                                   ║
║  스펙 §19 원칙 1 — 빌드·동기화 직후 이 스크립트 1회 실행       ║
║  실행: python scripts/apply_standard.py                       ║
╚══════════════════════════════════════════════════════════════╝
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    TYPE_NAME, YEAR,
    CONS_LIST_MAX_COL, CONS_LIST_LABELS, R3_MAP_CONS_LIST, R4_MAP_CONS_LIST,
    LI_MAX_COL, LI_HEADER_LABELS, R3_MAP_CONSUMABLES, LI_COL_AREA, LI,
    CONS_CATEGORIES, UNITS, ORIGINS, CURRENCIES,
    RECEIPT_STATUSES, SHIP_ITEM_STATUSES, TRADE_TYPES,
    CUSTOMS_TYPES, SHIP_TYPES, SHIP_STATUSES,
    consumables_path,
)
from shared.knk_standard import normalize_file


def _log(msg):
    print(msg)


def _specs():
    # 소모품목록
    cons_list_spec = {
        "title":   f"㈜케이엔케이 │ {TYPE_NAME} │ 소모품목록 │ {YEAR}",
        "purpose": "소모품 출하대장 전용",
        "max_col": CONS_LIST_MAX_COL,
        "labels":  list(CONS_LIST_LABELS),
        "r3_map":  dict(R3_MAP_CONS_LIST),
        "r4_map":  dict(R4_MAP_CONS_LIST),
        "freeze":  "auto",
        "money_cols": [7],  # 기본단가(KRW)
        "dropdown_map": {
            5: (UNITS, True),            # 단위
            8: (CONS_CATEGORIES, True),  # 카테고리
        },
    }

    # 출하관리 — LI_COL_AREA는 자체 색상 맵이지만 R4_AREA와 매칭 가능한 키로 통일 필요
    # 기존 코드가 쓰던 영역 매핑을 그대로 사용 (area_colors 직접 지정)
    # 현재 knk_standard.apply_r4는 R4_AREA를 씀 → area 키를 R4_AREA에 없는 값으로 두면 기본 회색
    # 대신 r4_map에 유사한 표준 area를 매핑
    AREA_REMAP = {
        "A_품목":  "id",
        "B_발주":  "po",
        "C_출하":  "ship",
        "C2_인보": "ship",
        "D_포장":  "dept",
        "E_통관":  "procure",
    }
    r4_map_ship = {c: AREA_REMAP.get(LI_COL_AREA.get(c), "id") for c in range(1, LI_MAX_COL + 1)}

    ship_spec = {
        "title":   f"㈜케이엔케이 │ {TYPE_NAME} │ 출하관리 │ {YEAR}",
        "purpose": "소모품 출하관리",
        "max_col": LI_MAX_COL,
        "labels":  list(LI_HEADER_LABELS),
        "r3_map":  dict(R3_MAP_CONSUMABLES),
        "r4_map":  r4_map_ship,
        "freeze":  "auto",
        "qty_cols":    [LI["수량"], LI["BOX수량"]],
        "money_cols":  [LI["단가"], LI["금액"], LI["INV단가"], LI["INV금액"],
                        LI["INV단가USD"], LI["INV금액USD"], LI["관세KRW"], LI["관세USD"]],
        "currency_col": LI["통화"],
        "row_end": 5000,
        "dropdown_map": {
            LI["통화"]:     (CURRENCIES, True),
            LI["입고상태"]: (RECEIPT_STATUSES, True),
            LI["출하상태"]: (SHIP_ITEM_STATUSES, True),
            LI["거래유형"]: (TRADE_TYPES, True),
            LI["통관구분"]: (CUSTOMS_TYPES, True),
            LI["통관분류"]: (SHIP_TYPES, True),
            LI["통관상태"]: (SHIP_STATUSES, True),
            LI["단위"]:     (UNITS, True),
            LI["원산지"]:   (ORIGINS, True),
        },
    }

    return {
        "소모품목록": cons_list_spec,
        "출하관리":   ship_spec,
    }


def apply_all():
    print("=" * 60)
    print(f"  [APPLY_STANDARD] {TYPE_NAME}")
    print(f"  스펙 v2026.04 — 체크리스트 20항 일괄 적용")
    print("=" * 60)

    fp = consumables_path()
    if os.path.exists(fp):
        normalize_file(fp, _specs(), fix_vml=True, log=_log)
    else:
        print(f"  ⚠ 파일 없음: {fp}")

    print("=" * 60)


if __name__ == "__main__":
    apply_all()
