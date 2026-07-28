# -*- coding: utf-8 -*-
"""WP-04 파서 — **비식별 자동시험** (실물 파일 없이 항상 실행)

근거: `CHATGPT_WP04_파서보수_완료보고_검토판정_및_V2수정지시_2026-07-28_1435.md`
      §4 P0-1 · §5 P0-2 · §6 P0-3 · §7 P0-4

⛔ **이 시험은 어떤 경우에도 SKIP 하지 않는다.**
   실물 BOM 은 고객 단가가 있어 저장소에 올리지 않으므로, 다른 PC·CI 에서도
   핵심 회귀를 반드시 돌리려면 시험이 **엑셀을 직접 만들어** 써야 한다.
   (실물 대조는 `test_wp04_bom_parser.py` 가 따로 맡고, 파일이 없으면 그쪽만 SKIP 한다.)

⛔ 실제 회사명·품번·단가를 쓰지 않는다. 전부 `TEST-...` 와 가상 금액이다.
"""
import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

import openpyxl                                    # noqa: E402
from openpyxl.styles import Font, PatternFill      # noqa: E402

from app import bom                                # noqa: E402

ok = 0
fail = 0


def chk(name, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS {name}")
    else:
        fail += 1
        print(f"  FAIL {name} {detail}")


_YELLOW = PatternFill(start_color="FFFFFF00", end_color="FFFFFF00", fill_type="solid")

# 헤더(구매팀 최종본 양식) — 실물과 같은 낱말을 쓰되 값은 전부 가상
_FULL_HDR = ["NO.", "CATEGORY 구분 / Danh mục", "CODE", "PRODUCT NAME 제품명",
             "PRODUCT CODE 코드명", "MANUFACTURER 제조사", "UNIT COUNT 수량",
             "TOTAL 수량", "UNIT 단위", "사내 재고", "베트남 재고", "발주 수량",
             "UNIT PRICE 단가", "재고 금액", "발주 금액", "AMOINT 합계",
             "DELIVERY 납기", "REMARKS(NOTE) 비고"]
# 합계 열 자체가 없는 양식(설계팀 초기본처럼)
_NOAMT_HDR = ["NO.", "CATEGORY 구분", "CODE", "PRODUCT NAME 제품명",
              "PRODUCT CODE 코드명", "MANUFACTURER 제조사", "UNIT COUNT 수량",
              "TOTAL 수량", "UNIT 단위", "UNIT PRICE 단가", "DELIVERY 납기",
              "REMARKS(NOTE) 비고"]


def _write(ws, header, rows):
    ws.cell(2, 3, "999T9901 구매품 BOM (시험용)")
    for i, h in enumerate(header, start=2):
        ws.cell(7, i, h)
    for r, row in enumerate(rows, start=8):
        for i, v in enumerate(row, start=2):
            ws.cell(r, i, v)


def build_full(path):
    """모든 열이 있는 양식 + 판정서 §4.2 필수 사례 전부."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "1. 구매품"
    rows = [
        # NO cat  code  품명            품번               제조사     대분 총량 단위 사내 VN 발주 단가   재고금  발주금  합계    납기      비고
        [1, "UNIT-A", "A1", "TEST NORMAL", "TEST-PART-A", "TESTMAKER", 1, 10, "EA", 2, 3, 5, 100, 200, 500, 1000, "1 WEEK", ""],
        [2, "UNIT-A", "A2", "TEST BLANK AMT", "TEST-PART-B", "TESTMAKER", 1, 4, "EA", 0, 0, 4, 50, None, None, None, "2 WEEK", ""],
        [3, "UNIT-A", "A3", "TEST ZERO AMT", "TEST-PART-C", "TESTMAKER", 1, 6, "EA", 0, 0, 6, 70, 0, 0, 0, "2 WEEK", "무상"],
        [4, "UNIT-A", "A4", "TEST NO PRICE", "TEST-PART-D", "TESTMAKER", 1, 3, "EA", 0, 0, 3, None, None, None, None, "미정", ""],
        [5, "UNIT-B", "B1", "TEST ONE STEP", "TEST-OLD-E->TEST-NEW-E", "TESTMAKER", 1, 2, "EA", 0, 0, 2, 30, 0, 60, 60, "1 WEEK", ""],
        [6, "UNIT-B", "B2", "TEST TWO STEP",
         "TEST-OLD-F->TEST-MID-F->TEST-NEW-F", "TESTOLD->TESTNEW", 1, 2, "EA", 0, 0, 2, 40, 0, 80, 80, "1 WEEK", ""],
        [7, "UNIT-C", "C1", "해외 출장비 (TEST)", "TEST-SVC-1", "TESTMAKER", 1, 1, "EA", 0, 0, 1, 500, 0, 500, 500, "협의", ""],
        [8, "UNIT-C", "C2", "TEST NEW MARK", "TEST-PART-H", "TESTMAKER", 1, 1, "EA", 0, 0, 1, 10, 0, 10, 10, "1 WEEK", ""],
        [9, "UNIT-C", "C3", "TEST DEL MARK", "TEST-PART-I", "TESTMAKER", 1, 1, "EA", 0, 0, 1, 10, 0, 10, 10, "1 WEEK", ""],
    ]
    _write(ws, _FULL_HDR, rows)
    ws.cell(15, 5).fill = _YELLOW          # 8번 줄(15행) 품명 = 노랑 → 신규 표시
    ws.cell(16, 5).font = Font(strike=True)  # 9번 줄(16행) 품명 = 취소선 → 삭제 표시
    ws.cell(16, 6).font = Font(strike=True)
    wb.save(path)


def build_noamt(path):
    """합계 열 **자체가 없는** 양식 — 이때만 계산이 허용된다."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "1. 구매품"
    _write(ws, _NOAMT_HDR, [
        [1, "UNIT-A", "A1", "TEST NO AMT COL", "TEST-PART-X", "TESTMAKER", 1, 5, "EA", 100, "1 WEEK", ""],
        [2, "UNIT-A", "A2", "TEST NO AMT NO PRICE", "TEST-PART-Y", "TESTMAKER", 1, 5, "EA", None, "1 WEEK", ""],
    ])
    wb.save(path)


_tmp = tempfile.mkdtemp(prefix="knk_bom_test_")
P_FULL = os.path.join(_tmp, "999T9901 구매품 LIST_TEST.xlsx")
P_NOAMT = os.path.join(_tmp, "999T9902 구매품 LIST_TEST.xlsx")
build_full(P_FULL)
build_noamt(P_NOAMT)

F = bom.parse_bom_file(P_FULL, os.path.basename(P_FULL))["sheets"][0]["items"]
N = bom.parse_bom_file(P_NOAMT, os.path.basename(P_NOAMT))["sheets"][0]["items"]
by = {x["part_no"]: x for x in F}

# ══════════ A. 양식 인식 ══════════
print("\n── A. 양식 인식 (파일 없이도 항상 실행) ──")
chk("A-1 전체 양식 9줄", len(F) == 9, f"{len(F)}줄")
chk("A-2 합계 열 없는 양식 2줄", len(N) == 2, f"{len(N)}줄")
chk("A-3 관리번호 자동추출",
    bom.parse_bom_file(P_FULL, os.path.basename(P_FULL))["mgmt_code"] == "999T9901")

# ══════════ B. P-1/P-4 원본 수량 필드 (이름이 업무 의미와 맞는가) ══════════
print("\n── B. 원본 수량 필드 (P0-4 이름 보정) ──")
chk("B-1 사내 **배분**수량 필드명 source_stock_allocated_kor",
    "source_stock_allocated_kor" in F[0])
chk("B-2 발주 **원본**수량 필드명 source_purchase_qty", "source_purchase_qty" in F[0])
chk("B-3 베트남은 참고수량 stock_ref_vn", "stock_ref_vn" in F[0])
chk("B-4 ⛔운영 오해 이름(stock_qty_kor·order_qty)은 없다",
    "stock_qty_kor" not in F[0] and "order_qty" not in F[0])
chk("B-5 값 읽기: 사내배분 2 · 베트남참고 3 · 발주원본 5",
    (F[0]["source_stock_allocated_kor"], F[0]["stock_ref_vn"], F[0]["source_purchase_qty"]) == (2, 3, 5),
    str((F[0]["source_stock_allocated_kor"], F[0]["stock_ref_vn"], F[0]["source_purchase_qty"])))
chk("B-6 [원본 파일 대조용] 총량 = 사내배분+베트남참고+발주원본 (운영 계산식 아님)",
    F[0]["total_qty"] == F[0]["source_stock_allocated_kor"] + F[0]["stock_ref_vn"] + F[0]["source_purchase_qty"])

# ══════════ C. P0-2 금액 네 상태 ══════════
print("\n── C. P0-2 금액: 원본값·명시적 0·빈칸·열없음 ──")
a, b, c, d = by["TEST-PART-A"], by["TEST-PART-B"], by["TEST-PART-C"], by["TEST-PART-D"]
chk("C-1 ①원본값 있음 → 그대로 보존 (1000)",
    a["amount"] == 1000 and a["amount_source_present"] and not a["amount_is_calculated"],
    f'{a["amount"]}/{a["amount_source_present"]}/{a["amount_is_calculated"]}')
chk("C-2 ①원본값 별도 보관 amount_source_value=1000", a["amount_source_value"] == 1000)
chk("C-3 ③빈칸 + 단가·수량 있음 → **계산**하고 표시 (50×4=200)",
    b["amount"] == 200 and not b["amount_source_present"] and b["amount_is_calculated"],
    f'{b["amount"]}/{b["amount_source_present"]}/{b["amount_is_calculated"]}')
chk("C-4 ⭐②명시적 0 → **계산 금지**, 0 그대로 (70×6=420 이 되면 안 됨)",
    c["amount"] == 0 and c["amount_source_present"] and not c["amount_is_calculated"],
    f'{c["amount"]}/{c["amount_source_present"]}/{c["amount_is_calculated"]}')
chk("C-5 ⭐계산 근거 없음(단가 없음) → **0 이라고 단정하지 않음**",
    not d["amount_source_present"] and not d["amount_is_calculated"],
    f'present={d["amount_source_present"]} calc={d["amount_is_calculated"]}')
chk("C-6 ④합계 열 자체가 없음 + 단가 있음 → 계산 (100×5=500)",
    N[0]["amount"] == 500 and N[0]["amount_is_calculated"] and not N[0]["amount_source_present"],
    f'{N[0]["amount"]}/{N[0]["amount_is_calculated"]}')
chk("C-7 ④합계 열 없음 + 단가도 없음 → 계산 안 함(모름)",
    not N[1]["amount_is_calculated"] and not N[1]["amount_source_present"])
chk("C-8 재고금액·발주금액도 따로 읽힌다 (200 / 500)",
    a["stock_amount"] == 200 and a["order_amount"] == 500,
    f'{a["stock_amount"]}/{a["order_amount"]}')

# ══════════ D. P-4 화살표 ══════════
print("\n── D. 화살표 분해 ──")
e1 = by.get("TEST-NEW-E")
f1 = by.get("TEST-NEW-F")
chk("D-1 A→B 1회 변경 → 새 값이 품번", bool(e1))
chk("D-2 A→B→C 2회 변경 → **마지막 값**이 품번", bool(f1))
chk("D-3 남은 화살표 0줄",
    not [x for x in F if "->" in (x.get("part_no") or "") or "->" in (x.get("maker") or "")])
_fc = [ch for ch in (f1 or {}).get("excel_changes", []) if ch["field"] == "part_no"]
chk("D-4 체인 전체 보존 [A,B,C]",
    bool(_fc) and _fc[0].get("chain") == ["TEST-OLD-F", "TEST-MID-F", "TEST-NEW-F"],
    str(_fc[0].get("chain") if _fc else None))
chk("D-5 제조사 화살표도 분해 (TESTOLD→TESTNEW)", (f1 or {}).get("maker") == "TESTNEW")

# ══════════ E. P0-3 변경 매칭 (§6.3 표 4가지) ══════════
print("\n── E. P0-3 A→B→C 매칭 (기존 저장값이 A든 B든) ──")


def _board(part_nos):
    return [{"category": "UNIT-B", "part_no": p, "part_name": "TEST TWO STEP",
             "id": i} for i, p in enumerate(part_nos, start=1)]


_two = [f1] if f1 else []
p1, a1, _ = bom._pair_items(_board(["TEST-OLD-F"]), _two)
chk("E-1 기존=A → A에서 C로 **변경으로 연결**", len(p1) == 1 and not a1,
    f"pairs={len(p1)} adds={len(a1)}")
p2, a2, _ = bom._pair_items(_board(["TEST-MID-F"]), _two)
chk("E-2 ⭐기존=B(중간값) → B에서 C로 **변경으로 연결**", len(p2) == 1 and not a2,
    f"pairs={len(p2)} adds={len(a2)}")
p3, a3, _ = bom._pair_items(_board(["TEST-OTHER"]), _two)
chk("E-3 기존 없음 → 신규 추가", len(p3) == 0 and len(a3) == 1)
chk("E-3' 신규여도 원문 체인은 보존",
    bool(a3) and any(ch.get("chain") for ch in a3[0].get("excel_changes", [])))
p4, a4, _ = bom._pair_items(_board(["TEST-MID-F", "TEST-MID-F"]), _two)
chk("E-4 ⭐같은 이전값이 **여러 줄** → 자동 확정 금지",
    len(p4) == 0 and len(a4) == 1, f"pairs={len(p4)} adds={len(a4)}")
chk("E-4' 모호 매칭으로 **표시**된다", bool(a4) and a4[0].get("match_ambiguous") is True)
p5, a5, _ = bom._pair_items(_board(["TEST-NEW-F"]), _two)
chk("E-5 기존이 이미 최종값 C → 그대로 같은 줄로 연결", len(p5) == 1 and not a5)

# ══════════ F. P-5 서비스 의심 · 색·취소선 ══════════
print("\n── F. 서비스 의심 · 엑셀 표기 ──")
chk("F-1 출장비 줄에 의심 표시", by["TEST-SVC-1"]["is_service_suspect"] is True)
chk("F-2 일반 자재는 표시 없음", by["TEST-PART-A"]["is_service_suspect"] is False)
chk("F-3 ⭐노랑 배경 = 신규 표시가 읽힌다", by["TEST-PART-H"]["is_new_marked"] is True)
chk("F-4 ⭐취소선 = 삭제 표시가 읽힌다", by["TEST-PART-I"]["is_deleted_marked"] is True)
chk("F-5 표시 없는 줄은 False",
    not by["TEST-PART-A"]["is_new_marked"] and not by["TEST-PART-A"]["is_deleted_marked"])

print(f"\n{'=' * 52}\n결과: PASS {ok} · FAIL {fail}")
sys.exit(0 if fail == 0 else 1)
