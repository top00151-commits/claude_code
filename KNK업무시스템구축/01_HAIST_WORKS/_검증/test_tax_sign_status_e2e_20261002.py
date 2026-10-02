#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""z1137 통짜 시험 — 마이너스 세금계산서도 「발행」으로 (이새롬 프로 신고 2026-10-02).

`test_tax_sign_status_20261002.py` 는 함수 원문을 하나씩 뽑아 본다. 이 파일은 **앱을 통째로 띄워**
진짜 주소로 들어가 본다 — 서버가 그린 화면 값이 화면 판정 함수로 그대로 넘어가는지까지.

  §1 납품·수금 화면(/sales/shipments-receipts) — 위쪽 숫자 = 아래 목록 · 마이너스 건의 상태
  §2 작업일정표(/sales/schedule) — 서버가 그린 수주금액·세금계산서 값을, **그 화면에 실린** 판정 함수로 돌린다

⛔ 운영 DB 를 열지 않는다(임시 DB). 실명·실거래처 없음(가상 자료) — 관리번호 999T2606 만 신고 건과 같은 꼴.
   fastapi 가 깔린 파이썬이 필요하다(`test_po_ccy_total_20260910.py` 와 같은 방식).

실행:  python _검증/test_tax_sign_status_e2e_20261002.py
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "deploy"))

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1137_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
D.init_db()

import app.main as appmain                                 # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402
import check_standards as CS                               # noqa: E402

BOSS = {"id": 901, "name": "시험대표", "role": "ceo", "team_id": None}
appmain.get_user = lambda request: BOSS
cl = TestClient(appmain.app, follow_redirects=False)

FAIL, CNT = [], 0


def check(name, ok, detail=""):
    global CNT
    CNT += 1
    print(("  ✅" if ok else "  ❌") + " %02d %s" % (CNT, name) + ("" if ok else "   ← %s" % (detail,)))
    if not ok:
        FAIL.append(name)


# ── 가상 자료 ─────────────────────────────────────────────────────────
#   (관리번호, 수주번호, 수주금액, 1차 발행일, 1차 금액)  — 전부 2026-06 · 1대 · 출하
SEED = [
    ("999T2606", "T-260611-1", -1865000, "2026-06-30", -1865000),   # 🔴 신고 건과 같은 꼴: 마이너스로 전액 발행
    ("001T2606", "T-260601-1", 1000000, "2026-06-30", 1000000),     # 플러스 · 전액 발행
    ("002T2606", "T-260601-2", 1000000, None, None),                # 플러스 · 하나도 안 끊음   → 마감이월
    ("003T2606", "T-260601-3", -500000, None, None),                # 마이너스 · 하나도 안 끊음 → 마감이월
    ("004T2606", "T-260601-4", 0, "2026-06-30", None),              # 0원 수주 · 발행일만
    ("005T2606", "T-260601-5", -700000, "2026-06-30", 700000),      # 🔴 마이너스 건에 플러스로 잘못 넣음
]
with D.db_session() as conn:
    conn.execute("INSERT INTO users(id, name, login_id, password, role) VALUES(?,?,?,'x',?)",
                 (BOSS["id"], BOSS["name"], "T901", BOSS["role"]))
    conn.execute("INSERT INTO customers(id, name, pay_days) VALUES(42, '시험고객(주)', 30)")
    for i, (mg, so, amt, tdate, tamt) in enumerate(SEED, start=1):
        conn.execute(
            "INSERT INTO projects(id, name, mgmt_code, biz_div, customer_id, customer_name, order_amount, currency, "
            "order_date, due_date, status) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (i, "SENSOR", mg, "T", 42, "시험고객(주)", amt, "KRW", "2026-06-11", "2026-06-29", "진행중"))
        conn.execute(
            "INSERT INTO orders(id, order_no, project_id, customer_id, order_date, due_date, total_amount, currency, status) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (i, so, i, 42, "2026-06-11", "2026-06-29", amt, "KRW", "SHIPPED"))
        conn.execute(
            "INSERT INTO order_items(id, order_id, qty, unit_price, amount, unit_status, due_date, "
            "tax_invoice_date, tax_invoice_amt1) VALUES(?,?,?,?,?,?,?,?,?)",
            (100 + i, i, 1, amt, amt, "출하", "2026-06-29", tdate, tamt))

print("=" * 72)
print("  z1137 통짜 시험 — 마이너스 세금계산서도 「발행」으로")
print("=" * 72)

# ══════════════════════════════════════════════════════════════════════
print("\n§1. 납품·수금 화면 (/sales/shipments-receipts)")
# ══════════════════════════════════════════════════════════════════════
r = cl.get("/sales/shipments-receipts")
check("화면이 정상으로 뜬다(200)", r.status_code == 200, r.status_code)
t = r.text


def row_of(html, so):
    """한 수주의 첫 줄(tr.sr-recA) — data-* 값을 읽는다."""
    m = re.search(r'<tr class="sr-recA[^>]*>(?:(?!</tr>).)*?>%s</a>' % re.escape(so), html, re.S)
    if not m:
        return None, ""
    tag = re.match(r"<tr[^>]*>", m.group(0)).group(0)
    end = html.find("</tr>", m.start())
    return dict(re.findall(r'data-([a-z]+)="([^"]*)"', tag)), html[m.start():end]


m = re.search(r"마감이월\(전부 미발행\)</div><div class=\"val\">(\d+)건", t)
kpi_carry = int(m.group(1)) if m else -1
n_carry = len(re.findall(r'<tr class="sr-recA[^>]*data-state="마감이월"', t))
check("🔴 위쪽 「마감이월(전부 미발행)」 %d건 = 아래 목록의 마감이월 %d줄" % (kpi_carry, n_carry),
      kpi_carry == n_carry == 2, (kpi_carry, n_carry))

d, h = row_of(t, "T-260611-1")
check("🔴 999T2606(마이너스 전액 발행) 줄이 있고 「마감이월」이 아니다", bool(d) and d.get("state") != "마감이월", d)
check("   · 세금계산서 칸 「전액 ✓ 06-30」 · 「미발행」 딱지 없음", "전액 ✓ 06-30" in h and ">미발행<" not in h)
check("   · 발행합계 값이 마이너스 그대로(-1865000.0)", bool(d) and d.get("issued") == "-1865000.0", d and d.get("issued"))
d, h = row_of(t, "T-260601-3")
check("마이너스 수주 · 안 끊음 → 「마감이월」로 목록에 뜬다(예전엔 안 나왔다)", bool(d) and d.get("state") == "마감이월", d)
check("   · 미발행 잔액 -500000.0 · 화면 글 ₩-500,000", bool(d) and d.get("unbilled") == "-500000.0" and "₩-500,000" in h, d)
d, h = row_of(t, "T-260601-2")
check("플러스 수주 · 안 끊음 → 「마감이월」 (무변화)", bool(d) and d.get("state") == "마감이월" and d.get("unbilled") == "1000000.0", d)
d, h = row_of(t, "T-260601-1")
check("플러스 전액 발행 → 「수금예정」 (무변화)", bool(d) and d.get("state") == "수금예정", d)
d, h = row_of(t, "T-260601-4")
check("0원 수주 → 「마감이월」에 안 들어간다", bool(d) and d.get("state") != "마감이월", d)

# ══════════════════════════════════════════════════════════════════════
print("\n§2. 작업일정표 (/sales/schedule?ym=2026-06) — 서버가 그린 값을 그 화면의 판정 함수로")
# ══════════════════════════════════════════════════════════════════════
r = cl.get("/sales/schedule?ym=2026-06")
check("화면이 정상으로 뜬다(200)", r.status_code == 200, r.status_code)
page = r.text


def board_row(html, mg):
    """관리번호가 든 줄(tr[data-ref])의 수주금액과 세금계산서 1·2·3차 값."""
    for m in re.finditer(r"<tr\b[^>]*\bdata-ref=\"\d+\"[^>]*>", html):
        end = html.find("</tr>", m.end())
        body = html[m.start():end]
        if mg not in body:
            continue
        rowamt = re.search(r'data-rowamt="([^"]*)"', m.group(0))
        amts = []
        for k in ("1", "2", "3"):
            c = re.search(r'<td class="[^"]*\btaxinv-cell\b[^"]*"[^>]*data-edit="taxinv%s"[^>]*data-amt="([^"]*)"' % k, body)
            amts.append(c.group(1) if c else None)
        return (rowamt.group(1) if rowamt else None), amts
    return None, []


fn = CS._js_func(page, "refreshTaxStatus")
check("화면에 실린 판정 함수를 찾음(주석 뺀 본문에 `total>0` 없음)",
      bool(fn) and not re.search(r"\btotal\s*>\s*0", re.sub(r"//[^\n]*", "", fn or "")))

rows = {}
for mg, _so, _amt, _d, _a in SEED:
    rows[mg] = board_row(page, mg)
check("여섯 건 모두 일정표에 그려졌다", all(v[0] is not None and len(v[1]) == 3 for v in rows.values()), rows)
# 서버는 수주금액을 소수꼴(-1865000.0)로, 세금계산서 금액은 정수로 떨어지면 정수꼴(-1865000)로 그린다(z986).
#   두 꼴이 달라도 화면 판정은 숫자로 견준다 — 아래에서 그 값 그대로 판정 함수에 넣어 본다.
check("🔴 서버가 그린 999T2606 — 수주금액 -1865000.0 · 1차 -1865000 (마이너스 그대로)",
      rows["999T2606"] == ("-1865000.0", ["-1865000", "", ""]), rows["999T2606"])

JS = r"""
function mkCell(edit, amt){ var cls={}; return { dataset:{edit:edit, amt:amt},
  classList:{ add:function(c){cls[c]=1;}, remove:function(){ for(var i=0;i<arguments.length;i++) delete cls[arguments[i]]; } },
  querySelector:function(){return null;}, _cls:cls }; }
function stat(rowamt, a){ var cells=[mkCell('taxinv1',a[0]||''), mkCell('taxinv2',a[1]||''), mkCell('taxinv3',a[2]||'')];
  var tr={ dataset:{rowamt:rowamt}, querySelectorAll:function(){return cells;}, querySelector:function(){return cells[0];} };
  refreshTaxStatus(tr); var c=cells[0]._cls; return c['tax-ok']?'ok':(c['tax-mismatch']?'mis':'none'); }
""" + (fn or "") + "\nvar R=" + json.dumps({k: [v[0], v[1]] for k, v in rows.items()}) + \
    ";\nvar out={}; Object.keys(R).forEach(function(k){ out[k]=stat(R[k][0], R[k][1]); }); console.log(JSON.stringify(out));"
d = tempfile.mkdtemp(prefix="z1137e_")
try:
    p = os.path.join(d, "t.js")
    io.open(p, "w", encoding="utf-8").write(JS)
    pr = subprocess.run(["node", p], capture_output=True, text=True, encoding="utf-8")
    got = json.loads(pr.stdout.strip().splitlines()[-1]) if pr.returncode == 0 else {"error": pr.stderr[-400:]}
finally:
    shutil.rmtree(d, ignore_errors=True)
check("🔴 999T2606 → 초록(전액 발행)", got.get("999T2606") == "ok", got)
check("플러스 전액 → 초록 (무변화)", got.get("001T2606") == "ok", got)
check("플러스 · 안 끊음 → 무색 (무변화)", got.get("002T2606") == "none", got)
check("마이너스 · 안 끊음 → 무색", got.get("003T2606") == "none", got)
check("0원 수주 → 무색 (무변화)", got.get("004T2606") == "none", got)
check("🔴 마이너스 건에 플러스로 잘못 넣은 것 → 주황(이제 걸러진다)", got.get("005T2606") == "mis", got)
check("범례 풍선말에 「마이너스(네고·할인) 건도 같은 기준」", "마이너스(네고·할인) 건도 같은 기준" in page)

print("-" * 72)
print("  시험 %d건 · 실패 %d건" % (CNT, len(FAIL)))
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if FAIL else 0)
