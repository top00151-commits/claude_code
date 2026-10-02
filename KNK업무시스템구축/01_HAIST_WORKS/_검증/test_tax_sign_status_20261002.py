# -*- coding: utf-8 -*-
"""z1137 시험 — 마이너스 세금계산서도 「발행」으로 (이새롬 프로 신고 2026-10-02).

신고 원문: "마이너스 세금계산서는 미발행으로 인식 됩니다. 마이너스 세금계산서도 발행으로 처리될수있게"
실물(운영 읽기 전용): 999T2606 SENSOR · 수주 -1,865,000 · 1차 세금계산서 2026-06-30 -1,865,000.

뿌리는 하나다 — 「금액은 플러스」라는 가정이 **판정**에 남아 있었다(z1135 는 **입력**에서 같은 가정을 고쳤다).
  · 작업일정표 색 판정이 `total>0` 일 때만 돌았다            → 무색(미발행처럼)
  · 작업일정표 1차 금액 미리 채움이 `rt>0` 일 때만 채웠다     → 마이너스 건만 빈칸
  · 납품·수금이 `발행합계 <= 0` 을 「전부 미발행」으로 셌다    → 위쪽 숫자에 들어감
  · 납품·수금이 `잔액 > 0` 일 때만 「발행 대기」로 봤다        → 마이너스 수주를 안 끊으면 조용히 빠짐

이 시험은 **진짜 코드**만 본다.
  §1 작업일정표 색 판정 — schedule_board.html 의 refreshTaxStatus 원문을 node 로 실행
  §2 작업일정표 1차 금액 미리 채움 — 그 줄 원문을 node 로 실행
  §3 납품·수금 판정 — main.py 의 _sr_bill_state 원문을 실행 + 예전 식과 전수 대조(플러스 건 무변화 증명)
  §4 납품·수금 화면 — 진짜 화면 함수(sales_shipments_receipts_page) 원문을 메모리 DB 로 실행
  §5 납품·수금 한 줄 — _sr_row.html 을 진짜 Jinja 로 그림
  §6 검사기 — 지금 코드는 통과, **일부러 예전 코드로 되돌리면 잡는다**(되돌림 8가지)

실행:  python _검증/test_tax_sign_status_20261002.py
"""
import ast
import asyncio
import io
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, "app", "templates")
BOARD = os.path.join(TPL, "schedule_board.html")
MAIN = os.path.join(ROOT, "app", "main.py")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

sys.path.insert(0, os.path.join(ROOT, "deploy"))
import check_standards as CS   # noqa: E402

OK = FAIL = 0


def sec(t):
    print("\n" + "━" * 72)
    print(t)
    print("━" * 72)


def chk(name, cond, got=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  ✅ %s" % name)
    else:
        FAIL += 1
        print("  ❌ %s%s" % (name, ("   ← %s" % (got,)) if got != "" else ""))


def read(p):
    return io.open(p, encoding="utf-8").read()


def node(js):
    """js 를 임시 파일로 써서 node 로 돌리고 마지막 줄(JSON)을 돌려준다."""
    d = tempfile.mkdtemp(prefix="z1137_")
    try:
        p = os.path.join(d, "t.js")
        io.open(p, "w", encoding="utf-8").write(js)
        r = subprocess.run(["node", p], capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0:
            raise RuntimeError(r.stderr[-800:])
        return json.loads(r.stdout.strip().splitlines()[-1])
    finally:
        shutil.rmtree(d, ignore_errors=True)


board_src = read(BOARD)
main_src = read(MAIN)

# ══════════════════════════════════════════════════════════════════════
sec("§1. 작업일정표 색 판정 — refreshTaxStatus 원문을 node 로 실행")
# ══════════════════════════════════════════════════════════════════════
fn_status = CS._js_func(board_src, "refreshTaxStatus")
chk("refreshTaxStatus 원문 추출", bool(fn_status) and "tax-ok" in fn_status)

FAKE_DOM = r"""
function mkCell(edit, amt){
  var cls = {};
  return { dataset:{edit:edit, amt:amt},
           classList:{ add:function(c){cls[c]=1;},
                       remove:function(){ for(var i=0;i<arguments.length;i++) delete cls[arguments[i]]; },
                       contains:function(c){return !!cls[c];} },
           querySelector:function(){return null;}, _cls:cls };
}
function mkRow(rowamt, a1, a2, a3){
  var cells=[mkCell('taxinv1',a1), mkCell('taxinv2',a2), mkCell('taxinv3',a3)];
  return { dataset:{rowamt:String(rowamt)}, _cells:cells,
           querySelectorAll:function(){ return cells; }, querySelector:function(){ return cells[0]; } };
}
function color(tr){
  var out = tr._cells.map(function(c){ return c._cls['tax-ok']?'ok':(c._cls['tax-mismatch']?'mis':'none'); });
  return out.join(',');
}
function stat(rowamt, a1, a2, a3){ var tr=mkRow(rowamt,a1,a2||'',a3||''); refreshTaxStatus(tr); return color(tr); }
"""
CASES1 = [
    # (이름, 수주금액, 1차, 2차, 3차, 기대)
    ("🔴 신고 그대로 — 999T2606: 수주 -1,865,000 / 1차 -1,865,000 → 초록(전액 발행)", -1865000, "-1865000", "", "", "ok"),
    ("저장값 꼴 그대로(-1865000.0)도 초록", "-1865000.0", "-1865000.0", "", "", "ok"),
    ("마이너스 수주에 일부만(-1,000,000) → 주황", -1865000, "-1000000", "", "", "mis"),
    ("마이너스 수주를 나눠 끊음(-1,000,000 + -865,000) → 초록", -1865000, "-1000000", "-865000", "", "ok"),
    ("🔴 마이너스 수주에 플러스로 잘못 넣음(+1,865,000) → 주황(이제 걸러진다)", -1865000, "1865000", "", "", "mis"),
    ("마이너스 수주를 넘겨 끊음(-2,000,000) → 주황", -1865000, "-2000000", "", "", "mis"),
    ("마이너스 수주 · 아직 아무것도 안 넣음 → 무색", -1865000, "", "", "", "none"),
    ("외화 소수 마이너스(-1,234.56 / -1,234.56) → 초록", -1234.56, "-1234.56", "", "", "ok"),
    # ── 플러스 건은 예전과 똑같아야 한다
    ("플러스 전액(1,865,000 / 1,865,000) → 초록 (무변화)", 1865000, "1865000", "", "", "ok"),
    ("플러스 일부(1,865,000 / 1,000,000) → 주황 (무변화)", 1865000, "1000000", "", "", "mis"),
    ("플러스 3차 분할(5,310,000 = 2,124,000×2 + 1,062,000) → 초록 (무변화)", 5310000, "2124000", "2124000", "1062000", "ok"),
    ("플러스 넘겨 끊음 → 주황 (무변화)", 1000000, "1200000", "", "", "mis"),
    ("플러스 · 아직 아무것도 안 넣음 → 무색 (무변화)", 1865000, "", "", "", "none"),
    ("플러스 수주에 마이너스로 넣음 → 주황 (무변화)", 1865000, "-1865000", "", "", "mis"),
    # ── 수주금액 0(미입력)은 견줄 금액이 없다 → 판정 제외 그대로
    ("수주금액 0 · 금액 넣음 → 무색 (무변화 · 견줄 금액 없음)", 0, "500000", "", "", "none"),
    ("수주금액 0 · 마이너스 넣음 → 무색 (무변화)", 0, "-500000", "", "", "none"),
]
js = FAKE_DOM + fn_status + "\nvar C=" + json.dumps([[c[1], c[2], c[3], c[4]] for c in CASES1]) + \
    ";\nconsole.log(JSON.stringify(C.map(function(c){ return stat(c[0],c[1],c[2],c[3]); })));"
got = node(js)
for (name, _a, _b, _c, _d, want), g in zip(CASES1, got):
    chk(name, g == ",".join([want] * 3), g)

# 한 줄에서 값이 바뀌면 예전 색을 지우는가(초록 → 주황 → 무색 → 초록)
js = FAKE_DOM + fn_status + r"""
var tr=mkRow(-1865000,'-1865000','',''); var out=[];
refreshTaxStatus(tr); out.push(color(tr));
tr._cells[0].dataset.amt='-1000000'; refreshTaxStatus(tr); out.push(color(tr));
tr._cells[0].dataset.amt=''; refreshTaxStatus(tr); out.push(color(tr));
tr._cells[0].dataset.amt='-1865000'; refreshTaxStatus(tr); out.push(color(tr));
console.log(JSON.stringify(out));"""
got = node(js)
chk("값을 고치면 색이 따라 바뀐다(초록→주황→무색→초록) · 옛 색이 안 남는다",
    got == ["ok,ok,ok", "mis,mis,mis", "none,none,none", "ok,ok,ok"], got)

# ══════════════════════════════════════════════════════════════════════
sec("§2. 작업일정표 1차 금액 미리 채움 — 그 줄 원문을 node 로 실행")
# ══════════════════════════════════════════════════════════════════════
pre = [ln for ln in board_src.splitlines()
       if "td.dataset.edit==='taxinv1'" in ln and "rowamt" in ln and not ln.lstrip().startswith("//")]
chk("미리 채움 줄을 정확히 1개 찾음", len(pre) == 1, len(pre))
PRE_LINE = pre[0] if pre else ""
js = ("function pre(edit, amt, rowamt){ var td={dataset:{edit:edit, amt:amt}}, tr={dataset:{rowamt:String(rowamt)}};\n"
      "  let curAmt=td.dataset.amt||'';\n" + PRE_LINE + "\n  return curAmt; }\n"
      "console.log(JSON.stringify([pre('taxinv1','',-1865000), pre('taxinv1','',1865000), pre('taxinv1','',0),"
      " pre('taxinv1','-500000',-1865000), pre('taxinv2','',-1865000), pre('taxinv1','',-1234.56),"
      " pre('taxinv1','',1315.5), pre('taxinv1','','')]));")
got = node(js)
chk("🔴 마이너스 수주(-1,865,000) · 1차 빈칸 → 수주금액 그대로 미리 채움", got[0] == "-1865000", got[0])
chk("플러스 수주(1,865,000) · 1차 빈칸 → 미리 채움 (무변화)", got[1] == "1865000", got[1])
chk("수주금액 0 → 안 채움 (무변화)", got[2] == "", got[2])
chk("이미 적힌 값(-500,000)은 건드리지 않음", got[3] == "-500000", got[3])
chk("2차 칸은 안 채움 (무변화)", got[4] == "", got[4])
chk("외화 소수 마이너스(-1,234.56) 보존", got[5] == "-1234.56", got[5])
chk("외화 소수 플러스(1,315.5) 보존 (z986 무회귀)", got[6] == "1315.5", got[6])
chk("수주금액 칸이 비어 있으면 안 채움", got[7] == "", got[7])

# 미리 채운 값이 팝업 금액 칸에 그려질 때 — 공용 금액 포맷(z1135)이 마이너스를 지키는가
amt_src = read(os.path.join(TPL, "_v5_partials", "knk_amt.html"))
fmt_fn = CS._js_func(amt_src, "fmtAmtTyping")
got = node(fmt_fn + "\nconsole.log(JSON.stringify([fmtAmtTyping('-1865000'), fmtAmtTyping('-1234.56')]));")
chk("미리 채운 -1865000 이 팝업에 「-1,865,000」으로 보인다(공용 금액 포맷)", got[0] == "-1,865,000", got[0])
chk("외화 -1234.56 → 「-1,234.56」", got[1] == "-1,234.56", got[1])

# ══════════════════════════════════════════════════════════════════════
sec("§3. 납품·수금 판정 — _sr_bill_state 원문 실행 + 예전 식과 전수 대조")
# ══════════════════════════════════════════════════════════════════════
tree = ast.parse(main_src)
ns = {}
for n in tree.body:
    if isinstance(n, ast.FunctionDef) and n.name == "_sr_bill_state":
        exec(compile(ast.get_source_segment(main_src, n), n.name, "exec"), ns)
chk("_sr_bill_state 원문 추출", "_sr_bill_state" in ns)
bs = ns["_sr_bill_state"]
EPS = 0.5

r = bs(-1865000, -1865000, EPS)
chk("🔴 신고 그대로 — 마이너스로 다 끊음: 「하나도 안 끊음」이 아니다", r["nothing_issued"] is False, r)
chk("   · 미발행 잔액 0 · 발행 대기 아님", r["unbilled"] == 0 and r["billing_due"] is False, r)
r = bs(-1865000, 0, EPS)
chk("마이너스 수주를 안 끊음: 발행 대기 + 하나도 안 끊음(→ 마감이월)", r["billing_due"] and r["nothing_issued"], r)
chk("   · 미발행 잔액 = -1,865,000 (수주금액 방향 그대로)", r["unbilled"] == -1865000, r)
r = bs(-1865000, -1000000, EPS)
chk("마이너스 수주를 일부만 끊음: 발행 대기 · 잔액 -865,000",
    r["billing_due"] and r["unbilled"] == -865000 and not r["nothing_issued"], r)
r = bs(-1865000, -2000000, EPS)
chk("마이너스 수주를 넘겨 끊음: 잔액 0(초과 발행은 플러스 건과 같은 대우)", r["unbilled"] == 0 and not r["billing_due"], r)
r = bs(-1865000, 1865000, EPS)
chk("마이너스 수주에 플러스로 끊음: 잔액이 더 커진다(-3,730,000) · 발행 대기", r["unbilled"] == -3730000 and r["billing_due"], r)
r = bs(1865000, -1865000, EPS)
chk("플러스 수주에 마이너스로 끊음: 「하나도 안 끊음」이 아니다 · 잔액 3,730,000",
    (not r["nothing_issued"]) and r["unbilled"] == 3730000, r)
r = bs(None, None, EPS)
chk("빈 값(None)도 죽지 않는다", r == {"unbilled": 0, "billing_due": False, "nothing_issued": True}, r)
r = bs(-1234.56, -1234.56, 0.005)
chk("외화(오차 0.005) 마이너스 전액", (not r["billing_due"]) and (not r["nothing_issued"]), r)
r = bs(-1234.56, -1234.55, 0.005)
chk("외화 0.01 모자람 → 발행 대기(-0.01)", r["billing_due"] and abs(r["unbilled"] + 0.01) < 1e-6, r)
r = bs(-100, -99.7, EPS)
chk("원화 오차(0.5) 안쪽은 남은 것으로 안 본다(마이너스 쪽도 같은 오차)", r["unbilled"] == 0 and not r["billing_due"], r)


def old_formula(total, issued, eps):
    """고치기 전 식 그대로(대조용) — main.py z908."""
    unb = (total or 0) - issued
    unbilled = unb if unb > eps else 0
    return {"unbilled": unbilled, "billing_due": unbilled > eps, "nothing_issued": issued <= eps}


TOTS = [0, 0.4, 0.5, 0.6, 1, 100, 1234.56, 978000, 1865000, 5310000, 47595000]
ISSS = [0, 0.3, 0.5, 0.6, 1, 50, 100, 1234.56, 978000, 1000000, 1865000, 2124000, 5310000, 60000000]
n_same = n_all = 0
diff = []
for eps in (0.5, 0.005):
    for t in TOTS:
        for i in ISSS:
            n_all += 1
            if bs(t, i, eps) == old_formula(t, i, eps):
                n_same += 1
            else:
                diff.append((t, i, eps))
chk("🔴 수주금액 0 이상 · 발행합계 0 이상 = 예전 식과 **전부 같다** (%d/%d 조합)" % (n_same, n_all),
    n_same == n_all, diff[:3])
# 수주금액 0 이상 + 마이너스 발행: 잔액·발행대기는 예전과 같고 「하나도 안 끊음」만 달라진다
only_ni = True
for t in TOTS:
    for i in (-1, -100, -1865000):
        a, b = bs(t, i, EPS), old_formula(t, i, EPS)
        if a["unbilled"] != b["unbilled"] or a["billing_due"] != b["billing_due"] or a["nothing_issued"] is not False:
            only_ni = False
chk("플러스 수주 + 마이너스 발행: 잔액·발행대기는 예전 그대로, 「하나도 안 끊음」만 거짓으로", only_ni)

# ══════════════════════════════════════════════════════════════════════
sec("§4. 납품·수금 화면 — 진짜 화면 함수 원문을 메모리 DB 로 실행")
# ══════════════════════════════════════════════════════════════════════
MEM = sqlite3.connect(":memory:", check_same_thread=False)
MEM.row_factory = sqlite3.Row
MEM.executescript("""
CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, pay_days INTEGER);
CREATE TABLE projects (id INTEGER PRIMARY KEY, mgmt_code TEXT);
CREATE TABLE orders (id INTEGER PRIMARY KEY, order_no TEXT, project_id INTEGER, order_date TEXT,
    total_amount REAL, currency TEXT, customer_id INTEGER, status TEXT,
    statement_date TEXT, tax_invoice_date TEXT, tax_invoice_amt1 REAL,
    tax_invoice_date2 TEXT, tax_invoice_amt2 REAL, tax_invoice_date3 TEXT, tax_invoice_amt3 REAL);
CREATE TABLE order_items (id INTEGER PRIMARY KEY, order_id INTEGER, unit_status TEXT, is_export INTEGER,
    statement_date TEXT, tax_invoice_date TEXT, tax_invoice_amt1 REAL,
    tax_invoice_date2 TEXT, tax_invoice_amt2 REAL, tax_invoice_date3 TEXT, tax_invoice_amt3 REAL);
CREATE TABLE receipts_payment (id INTEGER PRIMARY KEY, order_id INTEGER, currency TEXT, amount REAL,
    received_at TEXT, method TEXT, note TEXT);
INSERT INTO customers VALUES (42,'에스제이아이티 주식회사',30);
INSERT INTO projects VALUES (1,'P-A'),(2,'P-B'),(3,'P-C'),(4,'999T2606'),(5,'N-E'),(6,'N-F'),(7,'Z-G'),
                            (8,'N-H'),(9,'X-I'),(10,'X-J'),(11,'Z-K');
INSERT INTO orders (id,order_no,project_id,order_date,total_amount,currency,customer_id,status) VALUES
 (1,'SO-A',1,'2026-06-01', 1000000,'KRW',42,'SHIPPED'),        -- 플러스 · 전액 발행
 (2,'SO-B',2,'2026-06-01', 1000000,'KRW',42,'SHIPPED'),        -- 플러스 · 하나도 안 끊음      → 마감이월
 (3,'SO-C',3,'2026-06-01', 1000000,'KRW',42,'SHIPPED'),        -- 플러스 · 일부(400,000)        → 발행 대기
 (4,'T-260611-1',4,'2026-06-11',-1865000,'KRW',42,'SHIPPED'),  -- 🔴 운영 실물: 마이너스 · 마이너스로 전액
 (5,'SO-E',5,'2026-06-01', -500000,'KRW',42,'SHIPPED'),        -- 마이너스 · 하나도 안 끊음    → 마감이월(예전엔 목록에서 사라짐)
 (6,'SO-F',6,'2026-06-01', -500000,'KRW',42,'SHIPPED'),        -- 마이너스 · 일부(-200,000)     → 발행 대기
 (7,'SO-G',7,'2026-06-01', 0,'KRW',42,'SHIPPED'),              -- 0원 수주 · 발행일만 적힘(운영의 6건 꼴)
 (8,'SO-H',8,'2026-06-01', -700000,'KRW',42,'SHIPPED'),        -- 마이너스 · 금액(-300,000)만 적고 발행일 없음
 (9,'SO-I',9,'2026-06-01', -900000,'KRW',42,'CONFIRMED'),      -- 출하 전 → 대상 아님
 (10,'SO-J',10,'2026-06-01',-900000,'KRW',42,'CANCELLED'),     -- 취소 → 대상 아님
 (11,'SO-K',11,'2026-06-01',0,'KRW',42,'SHIPPED');             -- 0원 수주 · 아무것도 안 적음
INSERT INTO order_items (id,order_id,unit_status,is_export,tax_invoice_date,tax_invoice_amt1) VALUES
 (101,1,'출하',0,'2026-06-30', 1000000),
 (102,2,'출하',0,NULL,NULL),
 (103,3,'출하',0,'2026-06-30', 400000),
 (104,4,'출하',0,'2026-06-30',-1865000),
 (105,5,'출하',0,NULL,NULL),
 (106,6,'출하',0,'2026-06-30',-200000),
 (107,7,'출하',0,'2026-06-30',NULL),
 (108,8,'출하',0,NULL,-300000),
 (109,9,'',0,NULL,NULL),
 (110,10,'출하',0,'2026-06-30',-900000),
 (111,11,'출하',0,NULL,NULL);
""")


class _NoClose:
    """화면 함수가 `with db_session() as c` 로 여닫아도 메모리 DB 가 사라지지 않게."""

    def __enter__(self):
        return MEM

    def __exit__(self, *a):
        return False


env = {"db_session": lambda: _NoClose(), "date": date, "datetime": datetime, "timedelta": timedelta,
       "_s1_guard": lambda req: {"id": 1}, "can_view_sales": lambda u: True,
       "ctx": lambda req, tpl, **kw: kw, "RedirectResponse": lambda *a, **k: None,
       "Request": object, "HTMLResponse": object}
WANT = {"sales_shipments_receipts_page", "_board_tax_oi_map", "_board_in_frag", "_fmt_money", "_sr_bill_state"}
got_fn = set()
for n in tree.body:
    if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "_CCY_SYMBOL" for t in n.targets):
        exec(compile(ast.get_source_segment(main_src, n), "sym", "exec"), env)
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in WANT:
        exec(compile(ast.get_source_segment(main_src, n), n.name, "exec"), env)
        got_fn.add(n.name)
chk("화면 함수와 딸린 함수 5개 원문 추출", got_fn == WANT, WANT - got_fn)


class _Req:
    query_params = {}


res = asyncio.run(env["sales_shipments_receipts_page"](_Req()))
rows = {o["order_no"]: o for o in (res["action"] + res["inmonth"])}
kpi = res["kpi"]
chk("목록에 나오는 수주 8건(출하 전·취소·아무것도 없는 0원 수주 제외)",
    set(rows) == {"SO-A", "SO-B", "SO-C", "T-260611-1", "SO-E", "SO-F", "SO-G", "SO-H"}, sorted(rows))

o = rows["T-260611-1"]
chk("🔴 999T2606(마이너스 전액 발행): 「하나도 안 끊음」 아님 · 발행 대기 아님",
    (not o["nothing_issued"]) and (not o["billing_due"]), (o["nothing_issued"], o["billing_due"]))
chk("   · 발행 표시 = 「전액 ✓ 2026-06-30 ₩-1,865,000」",
    [(t["label"], t["date"], t["amt_fmt"]) for t in o["tier_chips"]] == [("전액", "2026-06-30", "₩-1,865,000")], o["tier_chips"])
chk("   · 미발행 잔액 ₩0 · 부가세 -186,500", o["unbilled_fmt"] == "₩0" and o["vat"] == -186500, (o["unbilled_fmt"], o["vat"]))
chk("   · 「챙길 것」이 아니라 발행완료 쪽 목록에 있다", any(x["order_no"] == "T-260611-1" for x in res["inmonth"]))

o = rows["SO-E"]
chk("마이너스 수주 · 안 끊음 → 상태 「마감이월」(예전엔 어느 목록에도 안 나왔다)", o["state"] == "마감이월", o["state"])
chk("   · 미발행 잔액 ₩-500,000 · 「챙길 것」 목록에 뜬다",
    o["unbilled_fmt"] == "₩-500,000" and any(x["order_no"] == "SO-E" for x in res["action"]), o["unbilled_fmt"])
o = rows["SO-F"]
chk("마이너스 수주 · 일부만 끊음 → 「발행 대기」 · 잔액 ₩-300,000",
    o["state"] == "발행 대기" and o["unbilled_fmt"] == "₩-300,000", (o["state"], o["unbilled_fmt"]))
chk("   · 발행 표시 = 「계약금」(다 끊지 않았으므로)", [t["label"] for t in o["tier_chips"]] == ["계약금"], o["tier_chips"])
o = rows["SO-H"]
chk("마이너스 금액만 적고 발행일 없음 → 발행 표시가 뜬다(예전엔 금액이 있는데도 「미발행」 딱지)",
    len(o["tier_chips"]) == 1 and o["tier_chips"][0]["amt_fmt"] == "₩-300,000", o["tier_chips"])
chk("   · 「발행 대기」 · 잔액 ₩-400,000", o["state"] == "발행 대기" and o["unbilled_fmt"] == "₩-400,000", (o["state"], o["unbilled_fmt"]))

chk("플러스 전액 발행(SO-A) → 수금예정 (무변화)", rows["SO-A"]["state"] == "수금예정" and not rows["SO-A"]["billing_due"], rows["SO-A"]["state"])
chk("플러스 안 끊음(SO-B) → 마감이월 · 잔액 ₩1,000,000 (무변화)",
    rows["SO-B"]["state"] == "마감이월" and rows["SO-B"]["unbilled_fmt"] == "₩1,000,000")
chk("플러스 일부(SO-C) → 발행 대기 · 잔액 ₩600,000 (무변화)",
    rows["SO-C"]["state"] == "발행 대기" and rows["SO-C"]["unbilled_fmt"] == "₩600,000")
chk("0원 수주 · 발행일만 적힘(SO-G) → 수금완료 · 챙길 것 아님 (무변화)",
    rows["SO-G"]["state"] == "수금완료" and not rows["SO-G"]["billing_due"], rows["SO-G"]["state"])

n_carry_rows = sum(1 for o in rows.values() if o["state"] == "마감이월")
chk("🔴 위쪽 「마감이월」 숫자 = 목록에서 마감이월로 나오는 줄 수 (%d = %d)" % (kpi["carryover_cnt"], n_carry_rows),
    kpi["carryover_cnt"] == n_carry_rows == 2, (kpi["carryover_cnt"], n_carry_rows))
chk("   · 0원 수주 2건(SO-G·SO-K)과 마이너스 전액(999T2606)은 그 숫자에 안 들어간다 — 예전 식이면 5",
    kpi["carryover_cnt"] == 2 and "SO-K" not in rows and rows["SO-G"]["nothing_issued"] is True)
n_bill_rows = sum(1 for o in rows.values() if o["state"] in ("마감이월", "발행 대기"))
chk("위쪽 「발행 대기」 건수 = 목록의 마감이월+발행 대기 (%d = %d)" % (kpi["billing_cnt"], n_bill_rows),
    kpi["billing_cnt"] == n_bill_rows == 5, (kpi["billing_cnt"], n_bill_rows))
chk("위쪽 「발행 대기」 금액 = 잔액을 부호대로 더한 값 ₩400,000 (100만+60만−50만−30만−40만)",
    kpi["billing_sum"] == "₩400,000", kpi["billing_sum"])
order = [x["order_no"] for x in res["action"] if x["state"] in ("마감이월", "발행 대기")]
chk("「챙길 것」 순서 = 잔액 크기 순(마이너스도 크기로): B(100만)→C(60만)→E(-50만)→H(-40만)→F(-30만)",
    order == ["SO-B", "SO-C", "SO-E", "SO-H", "SO-F"], order)
after = tuple(MEM.execute("SELECT COUNT(*), SUM(total_amount) FROM orders").fetchone())
chk("화면 함수는 읽기만 한다(수주 11건·합계 그대로)", after == (11, -2365000.0), after)

# ══════════════════════════════════════════════════════════════════════
sec("§5. 납품·수금 한 줄 — _sr_row.html 을 진짜 Jinja 로 그림")
# ══════════════════════════════════════════════════════════════════════
try:
    import jinja2
    jenv = jinja2.Environment(loader=jinja2.FileSystemLoader(TPL), autoescape=True)
    tpl_row = jenv.get_template("_v5_partials/_sr_row.html")

    def draw(o):
        return tpl_row.render(o=o, can_money=True, today_iso="2026-10-02")

    def cell(html, label):
        m = re.search(r'<span class="sr-l">%s</span><span class="sr-v"( style="([^"]*)")?[^>]*>(.*?)</span></td>'
                      % re.escape(label), html, re.S)
        return ((m.group(2) or ""), re.sub(r"<[^>]+>", "", m.group(3)).strip()) if m else (None, None)

    h = draw(rows["SO-E"])
    st, tx = cell(h, "미발행 잔액")
    chk("마이너스 잔액(₩-500,000)도 강조색으로 보인다", "color:#b45309" in (st or "") and tx == "₩-500,000", (st, tx))
    chk("   · 상태 딱지 「마감이월」", 'pill-carry">마감이월' in h)
    h = draw(rows["SO-B"])
    st, tx = cell(h, "미발행 잔액")
    chk("플러스 잔액(₩1,000,000) 강조색 (무변화)", "color:#b45309" in (st or "") and tx == "₩1,000,000", (st, tx))
    h = draw(rows["T-260611-1"])
    st, tx = cell(h, "미발행 잔액")
    chk("잔액 0(999T2606)은 강조 안 함", "color:#b45309" not in (st or "") and tx == "₩0", (st, tx))
    chk("   · 세금계산서 칸에 「전액 ✓ 06-30」 · 「미발행」 딱지 없음", "전액 ✓ 06-30" in h and ">미발행<" not in h)
    h = draw(rows["SO-A"])
    st, tx = cell(h, "미발행 잔액")
    chk("플러스 전액 발행은 강조 안 함 (무변화)", "color:#b45309" not in (st or "") and tx == "₩0", (st, tx))
    h = draw(rows["SO-H"])
    chk("금액만 적은 마이너스 건(SO-H): 「미발행」 딱지 대신 발행 표시", ">미발행<" not in h and "계약금 ✓" in h)
except ImportError:
    chk("jinja2 가 없어 §5 를 못 돌렸다", False)

# ══════════════════════════════════════════════════════════════════════
sec("§6. 검사기 — 지금 코드는 통과, 일부러 예전 코드로 되돌리면 잡는다")
# ══════════════════════════════════════════════════════════════════════
files_now = CS.collect(False)
bad_now = CS.check_tax_sign(files_now)
chk("지금 코드: 위반 0건", bad_now == [], bad_now[:2])
chk("설명 주석에 옛 조건(`total>0`·`rt>0`)을 적어 둔 것은 안 잡는다(오탐 없음)",
    "`total>0`" in board_src and "`rt>0`" in board_src and bad_now == [])

COPY = ("app/main.py", "app/templates/schedule_board.html", "app/templates/_v5_partials/_sr_row.html",
        "app/templates/_v5_partials/knk_amt.html", "app/templates/sales_shipments_receipts.html")


def mutated(edits):
    """작업 사본을 만들어 (파일, 옛글, 새글) 로 되돌린 뒤 검사기를 돌린다. 원본은 안 건드린다.
    옛글·새글은 줄바꿈을 \\n 으로 쓴다(파일이 CRLF 여도 맞게 바꿔 준다)."""
    d = tempfile.mkdtemp(prefix="z1137m_")
    try:
        for rel in COPY:
            dst = os.path.join(d, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(os.path.join(ROOT, rel.replace("/", os.sep)), dst)
        for rel, old, new in edits:
            p = os.path.join(d, rel.replace("/", os.sep))
            raw = io.open(p, encoding="utf-8", newline="").read()
            crlf = "\r\n" in raw
            s = raw.replace("\r\n", "\n")
            assert s.count(old) == 1, "되돌릴 글이 %d번 나옴: %s" % (s.count(old), old[:60])
            s = s.replace(old, new)
            io.open(p, "w", encoding="utf-8", newline="").write(s.replace("\n", "\r\n") if crlf else s)
        keep = (CS.ROOT, CS.TPL)
        CS.ROOT, CS.TPL = d, os.path.join(d, "app", "templates")
        try:
            fl = [os.path.join(d, r.replace("/", os.sep)) for r in COPY if r.endswith(".html")]
            return CS.check_tax_sign(fl)
        finally:
            CS.ROOT, CS.TPL = keep
    finally:
        shutil.rmtree(d, ignore_errors=True)


def has(bad, mark):
    return any(mark in m for _f, _l, m in bad)


b = mutated([])
chk("사본을 그대로 두면 통과(되돌림 시험 장치 자체 확인)", b == [], b[:2])
b = mutated([("app/templates/schedule_board.html", "if(anyAmt && total!==0) status=", "if(anyAmt && total>0) status=")])
chk("되돌림 ① 색 판정을 `total>0` 으로 → 잡는다", has(b, "①"), b)
b = mutated([("app/templates/schedule_board.html", "if(rt!==0) curAmt=", "if(rt>0) curAmt=")])
chk("되돌림 ② 미리 채움을 `rt>0` 으로 → 잡는다", has(b, "②"), b)
b = mutated([("app/main.py", '"nothing_issued": abs(issued_amt) <= eps}', '"nothing_issued": issued_amt <= eps}')])
chk("되돌림 ③-a 「하나도 안 끊음」을 `발행합계 <= 0` 으로 → **돌려 보고** 잡는다",
    has(b, "③") and has(b, "마이너스로 다 끊었는데"), b)
b = mutated([("app/main.py",
              "    if total < 0:\n        unbilled = unb if unb < -eps else 0\n    else:\n        unbilled = unb if unb > eps else 0\n",
              "    unbilled = unb if unb > eps else 0\n")])
chk("되돌림 ③-b 잔액을 「0보다 클 때만」으로 → 돌려 보고 잡는다", has(b, "③") and has(b, "안 끊었는데"), b)
b = mutated([("app/main.py", "def _sr_bill_state(total, issued_amt, eps):", "def _sr_bill_state_old(total, issued_amt, eps):")])
chk("되돌림 ③-c 공용 판정 함수를 없앰(이름 바꿈) → 잡는다", has(b, "③ _sr_bill_state() 가 없다"), b)
b = mutated([("app/main.py", '        _bs = _sr_bill_state(o["total_amount"], o["issued_amt"], _eps)',
              '        _unb = (o["total_amount"] or 0) - o["issued_amt"]; _bs = {"unbilled": _unb if _unb > _eps else 0, '
              '"billing_due": _unb > _eps, "nothing_issued": o["issued_amt"] <= _eps}')])
chk("되돌림 ④ 화면 함수가 스스로 판정 → 잡는다(안 부름 + 스스로 판정)",
    has(b, "④ 납품·수금 화면이") and has(b, "④ 발행 판정을 스스로"), b)
b = mutated([("app/main.py", '"carryover_cnt": sum(1 for o in shipped if o.get("state") == "마감이월"),',
              '"carryover_cnt": sum(1 for o in shipped if o.get("nothing_issued")),')])
chk("되돌림 ⑤ 위쪽 숫자를 다른 조건으로 셈 → 잡는다(숫자≠목록 재발)", has(b, "⑤"), b)
b = mutated([("app/templates/_v5_partials/_sr_row.html", "{% if o.unbilled != 0 %}", "{% if o.unbilled > 0 %}")])
chk("되돌림 ⑥ 잔액 강조를 `> 0` 으로 → 잡는다", has(b, "⑥"), b)

# 검사기가 배포 전 검사(main)에 실제로 물려 있는가
cs_src = read(os.path.join(ROOT, "deploy", "check_standards.py"))
chk("check_tax_sign 이 배포 전 검사 실행부에 물려 있다",
    "ts_bad = check_tax_sign(files)" in cs_src and "fail += len(ts_bad)" in cs_src)

print("\n" + "═" * 72)
print("결과: 통과 %d · 실패 %d" % (OK, FAIL))
print("═" * 72)
sys.exit(1 if FAIL else 0)
