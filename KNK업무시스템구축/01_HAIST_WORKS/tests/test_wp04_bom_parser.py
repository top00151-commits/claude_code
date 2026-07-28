# -*- coding: utf-8 -*-
"""WP-04 묶음 A 첫 관문 — BOM 파서 실물 검증 (P-1 ~ P-6)

근거: `CHATGPT_WP04_실물BOM_비교검증_및_데이터계약보정_2026-07-28_0954.md` §8
      `CHATGPT_WP04_베트남재고_범위판정_및_법인분리원칙_2026-07-28_1109.md`

⭐ 실물 파일 2개를 **양쪽 다** 시험한다. 한쪽만 통과한 것을 전체로 일반화하지 않기 위해서다
   (설계팀 파일은 단가·금액이 비어 있어 금액 계산 결함이 드러나지 않았다).

⛔ 읽기 전용 — DB 를 쓰지 않는다. 파싱 결과만 검사한다.
"""
import io
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

from app import bom  # noqa: E402

# 실물 BOM (대표 전달 · 참고자료)
#   ⛔ 고객 단가·금액이 들어 있어 **저장소에 커밋하지 않는다**(대표 판단 사항).
#      그래서 워크트리 → 메인 저장소 순으로 찾고, 없으면 이 시험은 SKIP 한다.
_ROOTS = [
    os.path.dirname(os.path.dirname(_HERE)),                       # (워크트리)/KNK업무시스템구축
    os.environ.get("KNK_REF_ROOT") or "",                          # 직접 지정
    r"C:\Users\top00\JR\Claude 코드\KNK업무시스템구축",              # 메인 저장소
]
_D_REL = os.path.join("참고자료", "설계팀", "001M2607-12대 구매품 LIST_260727-R1.xlsx")
_B_REL = os.path.join("참고자료", "구매팀",
                      "001M2607_AUTO TESTER HANDLER 구매품 (기구+전장) LIST_20260722.xlsx")


def _find(rel):
    for r in _ROOTS:
        if not r:
            continue
        p = os.path.join(r, rel)
        if os.path.exists(p):
            return p
    return os.path.join(_ROOTS[0], rel)     # 없으면 첫 경로를 SKIP 안내에 쓴다


F_DESIGN = _find(_D_REL)
F_BUY = _find(_B_REL)

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


def parse(path):
    return bom.parse_bom_file(path, os.path.basename(path))["sheets"][0]["items"]


def s(items, key):
    return sum(float(it.get(key) or 0) for it in items)


_missing = [p for p in (F_DESIGN, F_BUY) if not os.path.exists(p)]
if _missing:
    print("SKIP — 이 파일은 **실물 BOM 대조 전용**입니다(핵심 회귀는")
    print("       tests/test_wp04_bom_parser_synthetic.py 가 파일 없이 항상 수행).")
    print("  없는 파일:")
    for p in _missing:
        print("   " + p)
    sys.exit(0)

D = parse(F_DESIGN)
B = parse(F_BUY)

# ══════════ A. 두 파일 모두 줄 수가 맞는가 ══════════
print("\n── A. 줄 수 (설계팀 132 · 구매팀 160) ──")
chk("A-1 설계팀 BOM 132줄", len(D) == 132, f"{len(D)}줄")
chk("A-2 구매팀 최종본 160줄", len(B) == 160, f"{len(B)}줄")
chk("A-3 총계행을 품목으로 세지 않음",
    not [x for x in B if "합계" in (x.get("part_name") or "")])

# ══════════ B. P-1 재고·발주수량 열 (구매검토의 핵심) ══════════
print("\n── B. P-1 재고·발주수량 열 매핑 ──")
chk("B-1 사내 **배분**수량 칸이 있다", "source_stock_allocated_kor" in (B[0] if B else {}))
chk("B-2 베트남재고 **참고칸**이 있다", "stock_ref_vn" in (B[0] if B else {}))
chk("B-3 발주 **원본**수량 칸이 있다", "source_purchase_qty" in (B[0] if B else {}))
chk("B-4 사내 배분수량 합계 3", s(B, "source_stock_allocated_kor") == 3, f'{s(B, "source_stock_allocated_kor")}')
chk("B-5 베트남재고 합계 15 (참고수량)", s(B, "stock_ref_vn") == 15, f'{s(B, "stock_ref_vn")}')
chk("B-6 발주 원본수량 합계 5,183", s(B, "source_purchase_qty") == 5183, f'{s(B, "source_purchase_qty")}')
chk("B-7 [원본 파일 대조용] 총수량 = 사내배분 + 베트남참고 + 발주원본 (⛔운영 구매량 계산식 아님)",
    abs(s(B, "total_qty") - (s(B, "source_stock_allocated_kor") + s(B, "stock_ref_vn") + s(B, "source_purchase_qty"))) < 0.001,
    f'{s(B, "total_qty")} vs {s(B, "source_stock_allocated_kor") + s(B, "stock_ref_vn") + s(B, "source_purchase_qty")}')
chk("B-8 설계팀 파일엔 재고·발주 열이 없어 0",
    s(D, "source_stock_allocated_kor") == 0 and s(D, "source_purchase_qty") == 0)

# ══════════ C. P-2 금액 3종 분리 ══════════
print("\n── C. P-2 재고금액·발주금액·합계 분리 ──")
chk("C-1 재고금액 칸이 있다", "stock_amount" in (B[0] if B else {}))
chk("C-2 발주금액 칸이 있다", "order_amount" in (B[0] if B else {}))
chk("C-3 재고금액 합계 101,100", abs(s(B, "stock_amount") - 101100) < 0.01,
    f'{s(B, "stock_amount"):,.2f}')
chk("C-4 발주금액 합계 103,420,861.32", abs(s(B, "order_amount") - 103420861.32) < 0.01,
    f'{s(B, "order_amount"):,.2f}')
chk("C-5 ⭐합계금액이 **원본 그대로** 103,521,961.32",
    abs(s(B, "amount") - 103521961.32) < 0.01, f'{s(B, "amount"):,.2f}')
chk("C-6 합계 = 재고금액 + 발주금액",
    abs(s(B, "amount") - (s(B, "stock_amount") + s(B, "order_amount"))) < 0.01)
chk("C-7 단가 입력된 줄 159", sum(1 for x in B if x.get("unit_price")) == 159,
    str(sum(1 for x in B if x.get("unit_price"))))

# ══════════ D. P-3 원본 금액이 있으면 계산하지 않는다 ══════════
print("\n── D. P-3 계산 금지 (원본 우선) ──")
chk("D-1 계산값 표시 칸이 있다", "amount_is_calculated" in (B[0] if B else {}))
chk("D-2 ⭐구매팀 파일은 원본 합계가 있으므로 **계산한 줄 0**",
    sum(1 for x in B if x.get("amount_is_calculated")) == 0,
    str(sum(1 for x in B if x.get("amount_is_calculated"))))
_dcalc = sum(1 for x in D if x.get("amount_is_calculated"))
chk("D-3 설계팀 파일은 단가가 비어 계산도 하지 않음", _dcalc == 0, str(_dcalc))

# ══════════ E. P-4 다단 화살표 (A→B→C) ══════════
print("\n── E. P-4 대체품 화살표 ──")
ARROW = ("->", "→")


def has_arrow(x, f):
    return any(a in (x.get(f) or "") for a in ARROW)


left = [x for x in B if has_arrow(x, "part_no") or has_arrow(x, "maker") or has_arrow(x, "part_name")]
chk("E-1 ⭐분해되지 않고 남은 화살표 **0줄**", len(left) == 0,
    f"{len(left)}줄 예: " + (left[0].get("part_no") if left else ""))
chk("E-2 변경 기록이 78줄 이상 남는다",
    sum(1 for x in B if x.get("excel_changes")) >= 78,
    str(sum(1 for x in B if x.get("excel_changes"))))
_chain = [x for x in B if any(len(c.get("chain") or []) > 2 for c in (x.get("excel_changes") or []))]
chk("E-3 ⭐2회 변경(단종→대체→재대체) 5줄이 **중간값까지 보존**", len(_chain) == 5,
    f"{len(_chain)}줄")
_ex = None
for x in B:
    for c in (x.get("excel_changes") or []):
        if (c.get("chain") or [None])[0] == "MFMCA0030RJD":
            _ex = c
chk("E-4 예: MFMCA0030RJD → ELM-PWR3M0-A1 → E-CASP3M-N",
    bool(_ex) and _ex.get("chain") == ["MFMCA0030RJD", "ELM-PWR3M0-A1", "E-CASP3M-N"]
    and _ex.get("new") == "E-CASP3M-N", str(_ex))
_g = [x for x in B if x.get("part_no") == "KQ2Z08-03NS"]
chk("E-5 1회 변경은 그대로 동작 (GPA 0803 → KQ2Z08-03NS)",
    bool(_g) and any(c.get("old") == "GPA 0803" for c in (_g[0].get("excel_changes") or [])))

# ══════════ F. P-5 서비스성 항목 의심 표시 ══════════
print("\n── F. P-5 자재가 아닌 줄 (판정 아님·의심 표시) ──")
chk("F-1 의심 표시 칸이 있다", "is_service_suspect" in (B[0] if B else {}))
_svc = [x for x in B if x.get("is_service_suspect")]
chk("F-2 출장비·개발비 2줄이 표시된다", len(_svc) >= 2, f"{len(_svc)}줄")
chk("F-3 표시된 줄에 '해외 출장비 (VINA)' 포함",
    any("출장" in (x.get("part_name") or "") for x in _svc))
chk("F-4 일반 자재는 표시되지 않는다 (CASTER)",
    not [x for x in B if x.get("part_name") == "CASTER" and x.get("is_service_suspect")])

# ══════════ G. 회귀 — 기존 동작이 깨지지 않았는가 ══════════
print("\n── G. 회귀 (설계팀 파일 기존 동작) ──")
chk("G-1 설계팀 총수량 4,944", s(D, "total_qty") == 4944, f'{s(D, "total_qty")}')
chk("G-2 설계팀 핵심 7칸 빈칸 0",
    all(sum(1 for x in D if not x.get(k)) == 0
        for k in ("category", "part_no", "part_name", "maker", "unit_count", "total_qty", "unit")))
chk("G-3 관리번호 자동추출 001M2607 (양쪽)",
    bom.parse_bom_file(F_DESIGN, os.path.basename(F_DESIGN))["mgmt_code"] == "001M2607"
    and bom.parse_bom_file(F_BUY, os.path.basename(F_BUY))["mgmt_code"] == "001M2607")
chk("G-4 구매팀 총수량 5,201", s(B, "total_qty") == 5201, f'{s(B, "total_qty")}')
chk("G-5 납기 입력 160줄",
    sum(1 for x in B if (x.get("delivery_text") or "").strip()) == 160,
    str(sum(1 for x in B if (x.get("delivery_text") or "").strip())))
chk("G-6 전장 부품 21줄이 CATEGORY 로 구분됨",
    sum(1 for x in B if "전장" in (x.get("category") or "")) == 21,
    str(sum(1 for x in B if "전장" in (x.get("category") or ""))))

print(f"\n{'=' * 52}\n결과: PASS {ok} · FAIL {fail}")
sys.exit(0 if fail == 0 else 1)
