# -*- coding: utf-8 -*-
r"""WP-04 B단계 V5 — 장비대수 원천 · 구매요청/발주 현행 **읽기 전용** 실측
근거: 게이트 `CHATGPT_WP04_B단계_V4_최종설계검토_및_V5수정지시_2026-08-03_2345.md` §9

무엇을 답하려는 스크립트인가:
  게이트 P0-1 이 "Release 발행 시점의 **장비대수를 고정 저장**하라" 고 했다.
  그런데 **그 대수를 어디서 읽어야 하는지** 가 정해져 있지 않다. 후보가 셋이다.
    A안  order_items 중 정식 호기 라벨(z779 `^\d+호기$`) 행을 **센다**   (= 대수는 행 수)
    B안  그 호기 행들의 `qty` 를 **더한다**
    C안  project_items 중 shipment_form='ASSEMBLY' 인 것의 `qty` 를 더한다
  세 값이 늘 같으면 아무거나 써도 되고, 다르면 **사람이 고르게** 해야 한다.
  → 이 스크립트는 수주마다 셋을 계산해 **일치/불일치 건수만** 센다.

⛔ 절대 출력하지 않는 것 — 품명·품번·고객명·협력사명·담당자명 · 단가·금액·거래내용 ·
   메모/비고 원문 · 개별 행 원문 · 호기 라벨 원문 · 개인정보·토큰.
   → **집계 숫자와 스키마 칸 이름만** 출력한다.
⛔ 쓰기 없음(SELECT·PRAGMA 만) · mode=ro · 재시작 없음 · 마이그레이션 없음.

사용:  python3 b1_qty_source_readonly_audit.py [DB경로]
"""
import re
import sqlite3
import sys
import time

DB = sys.argv[1] if len(sys.argv) > 1 else "/opt/knk_haist/data/knk.db"
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
con.row_factory = sqlite3.Row
q = con.execute
T0 = time.time()

# z779 규약 — 정식 호기 라벨만 장비로 센다. 부속·부품 라인은 제외.
# (app/project_unit.py 의 HOGI_RE 와 **같은 정규식**. 다르면 실측이 무의미하므로 같이 둔다.)
HOGI_RE = re.compile(r"^\d+호기$")


def head(t):
    print("\n" + "=" * 74)
    print(f" {t}")
    print("=" * 74)


def exists(name, kind="table"):
    return bool(q("SELECT 1 FROM sqlite_master WHERE type=? AND name=?",
                  (kind, name)).fetchone())


def cnt(sql, args=()):
    try:
        return q(sql, args).fetchone()[0]
    except Exception as e:
        return f"(조회불가: {type(e).__name__})"


def cols(table):
    """칸 이름 목록 — 값은 읽지 않는다."""
    try:
        return [r["name"] for r in q(f"PRAGMA table_info({table})").fetchall()]
    except Exception:
        return []


def fks(table):
    """FK 관계 — (칸, 대상표, 대상칸, 삭제정책)."""
    try:
        return [(r["from"], r["table"], r["to"], r["on_delete"])
                for r in q(f"PRAGMA foreign_key_list({table})").fetchall()]
    except Exception:
        return []


print("=" * 74)
print(" WP-04 B단계 V5 — 장비대수 원천 · 구매요청/발주 읽기 전용 실측")
print("=" * 74)
print(f" DB      : {DB}")
print(f" 열기방식 : mode=ro (읽기 전용)")

# ══════════════════════════════════════════════════════════════════
head("① 표 존재 여부")
# ══════════════════════════════════════════════════════════════════
NEED = ("orders", "order_items", "project_items", "projects",
        "material_requests", "material_request_items",
        "purchase_orders", "po_items",
        "bom_uploads", "bom_items", "bom_item_history",
        "project_units")
have = {}
for t in NEED:
    have[t] = exists(t)
    print(f"  {'있음' if have[t] else '없음'}   {t}")

# ══════════════════════════════════════════════════════════════════
head("② 장비대수 원천 — 세 후보 비교 (게이트 §9-1 · §9-2)")
# ══════════════════════════════════════════════════════════════════
if not (have.get("order_items") and have.get("orders")):
    print("  order_items / orders 가 없어 비교 불가")
else:
    oi_cols = cols("order_items")
    pi_cols = cols("project_items") if have.get("project_items") else []
    print(f"  order_items 칸수   : {len(oi_cols)}")
    print(f"  unit_label 칸 존재 : {'예' if 'unit_label' in oi_cols else '아니오 (A·B안 불가)'}")
    print(f"  qty 칸 존재        : {'예' if 'qty' in oi_cols else '아니오'}")
    print(f"  project_items 칸수 : {len(pi_cols)}")
    print(f"  shipment_form 존재 : {'예' if 'shipment_form' in pi_cols else '아니오 (C안 불가)'}")

    if "unit_label" in oi_cols and "qty" in oi_cols:
        # 수주별 A안(호기 행 수) · B안(호기 행 qty 합)
        rows = q("SELECT order_id, unit_label, qty FROM order_items").fetchall()
        per = {}                      # order_id -> [행수, qty합]
        nonint = 0                    # 호기 행인데 qty 가 정수가 아닌 것
        qty_not_1 = 0                 # 호기 행인데 qty 가 1 이 아닌 것
        for r in rows:
            lb = (r["unit_label"] or "").strip()
            if not HOGI_RE.match(lb):
                continue
            v = r["qty"] if r["qty"] is not None else 0
            a = per.setdefault(r["order_id"], [0, 0.0])
            a[0] += 1
            a[1] += float(v)
            if float(v) != int(float(v)):
                nonint += 1
            if float(v) != 1.0:
                qty_not_1 += 1

        print(f"\n  [A안] 정식 호기 라인을 가진 수주 : {len(per)} 건")
        print(f"        정식 호기 라인 총 행수     : {sum(a[0] for a in per.values())}")
        print(f"  [B안] 그 행들의 qty 합계         : {sum(a[1] for a in per.values()):.4g}")
        print(f"\n  🔴 호기 행인데 qty 가 1 이 아닌 것 : {qty_not_1} 행")
        print(f"  🔴 호기 행인데 qty 가 정수 아님    : {nonint} 행")
        print("     → 둘 다 0 이면 'A안 = B안' (행 수로 세도 같다)")

        # 수주별 호기 행수 분포 — 12대짜리가 실제로 있는지 확인
        dist = {}
        for a in per.values():
            k = a[0]
            b = ("1" if k == 1 else "2~5" if k <= 5 else "6~11" if k <= 11
                 else "12~23" if k <= 23 else "24+")
            dist[b] = dist.get(b, 0) + 1
        print("\n  수주별 호기 행수 분포 (게이트 §9-2):")
        for k in ("1", "2~5", "6~11", "12~23", "24+"):
            if k in dist:
                print(f"        {k:>6} 대 : {dist[k]} 개 수주")

        # C안과 대조
        if pi_cols and "shipment_form" in pi_cols and "order_id" in pi_cols:
            prows = q("SELECT order_id, qty FROM project_items "
                      "WHERE shipment_form='ASSEMBLY' AND order_id IS NOT NULL").fetchall()
            pper = {}
            for r in prows:
                pper[r["order_id"]] = pper.get(r["order_id"], 0.0) + float(r["qty"] or 0)
            both = set(per) & set(pper)
            same = sum(1 for o in both if abs(per[o][0] - pper[o]) < 1e-9)
            print(f"\n  [C안] project_items(ASSEMBLY) 로 대수를 읽을 수 있는 수주 : {len(pper)} 건")
            print(f"        A안과 둘 다 있는 수주 : {len(both)} 건")
            print(f"        그중 값이 같은 수주   : {same} 건")
            print(f"        🔴 값이 다른 수주     : {len(both) - same} 건")
            print(f"        A안에만 있음 : {len(set(per) - set(pper))} · C안에만 있음 : {len(set(pper) - set(per))}")
            print("\n     → '다른 수주 0 · 한쪽에만 0' 이면 어느 안을 써도 같다.")
            print("        하나라도 다르면 **자동 합산 기준을 만들지 말고 사람이 확인**해야 한다(게이트 P0-1).")

# ══════════════════════════════════════════════════════════════════
head("③ 구매요청 현행 (게이트 §9-3)")
# ══════════════════════════════════════════════════════════════════
for t in ("material_requests", "material_request_items"):
    if not have.get(t):
        print(f"  {t} : 없음")
        continue
    print(f"\n  [{t}]  행수 = {cnt(f'SELECT COUNT(*) FROM {t}')}")
    print(f"    칸 : {', '.join(cols(t))}")
    f = fks(t)
    print(f"    FK : {f if f else '(없음)'}")

# ══════════════════════════════════════════════════════════════════
head("④ 발주 현행 · 구매요청→발주 연결 (게이트 §9-4)")
# ══════════════════════════════════════════════════════════════════
for t in ("purchase_orders", "po_items"):
    if not have.get(t):
        print(f"  {t} : 없음")
        continue
    print(f"\n  [{t}]  행수 = {cnt(f'SELECT COUNT(*) FROM {t}')}")
    print(f"    칸 : {', '.join(cols(t))}")
    f = fks(t)
    print(f"    FK : {f if f else '(없음)'}")

# 구매요청 라인 ↔ 발주 라인을 잇는 칸이 **실제로 있는지**
mri = cols("material_request_items") if have.get("material_request_items") else []
poi = cols("po_items") if have.get("po_items") else []
link_mri = [c for c in mri if "po" in c.lower() or "order" in c.lower()]
link_poi = [c for c in poi if "request" in c.lower() or "mri" in c.lower() or "req" in c.lower()]
print("\n  구매요청↔발주 연결 칸 탐색:")
print(f"    material_request_items 쪽 후보 : {link_mri if link_mri else '(없음)'}")
print(f"    po_items 쪽 후보               : {link_poi if link_poi else '(없음)'}")
print("    → 양쪽 다 '(없음)' 이면 **요청과 발주가 아직 연결되지 않는다**(V5 가 설계할 자리).")

# 별도 연결표가 있는지
for t in ("po_item_request_links", "material_request_po_links", "po_item_project_links"):
    if exists(t):
        print(f"    별도 연결표 발견: {t}  행수={cnt(f'SELECT COUNT(*) FROM {t}')}  칸={', '.join(cols(t))}")

# ══════════════════════════════════════════════════════════════════
head("⑤ 운영 BOM 재확인 (게이트 §9-5)")
# ══════════════════════════════════════════════════════════════════
for t in ("bom_uploads", "bom_items", "bom_item_history"):
    print(f"  {t:<20} 행수 = {cnt(f'SELECT COUNT(*) FROM {t}') if have.get(t) else '(표 없음)'}")
try:
    for r in q("SELECT name, seq FROM sqlite_sequence WHERE name LIKE 'bom%'").fetchall():
        print(f"    sqlite_sequence  {r['name']:<20} seq = {r['seq']}   (과거 사용 흔적)")
except Exception:
    pass

# ══════════════════════════════════════════════════════════════════
head("⑥ V5 가 쓸 FK 대상 표의 삭제정책 (게이트 P0-6)")
# ══════════════════════════════════════════════════════════════════
print("  V5 신규 표가 참조할 기존 표의 현행 FK 삭제정책:")
for t in ("po_items", "material_request_items", "order_items",
          "project_units", "bom_uploads"):
    if have.get(t):
        f = fks(t)
        print(f"    {t:<24} {f if f else '(FK 없음)'}")
print("\n  ⚠ po_items.po_id 가 CASCADE 면, V5 의 변경영향표가 po_items 를 RESTRICT 로")
print("     참조할 때 '발주 삭제'와 충돌한다 → V5 에서 정책을 명시해야 한다.")

print("\n" + "=" * 74)
print(f" 완료 — 소요 {time.time() - T0:.2f}초 · 쓰기 0건 · 출력은 집계와 칸 이름뿐")
print("=" * 74)
con.close()
