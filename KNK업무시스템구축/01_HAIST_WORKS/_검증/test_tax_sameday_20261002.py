# -*- coding: utf-8 -*-
"""z1136 시험 — 세금계산서 「같은 날 함께 발행」 (이새롬·안지연 프로 요청 2026-10-02).

요청(녹음): "세금계산서에서 묶임이 표현됐으면 좋겠다 — 뭐하고 뭐하고 묶여서 발행이 됐다.
            말일자로 발행하는 게 많아서, 안 그러면 하나씩 다 눌러서 확인해야 한다."

이 시험은 **진짜 코드**만 본다.
  §1 은 app/database.py 의 tax_same_day 원문을 뽑아 메모리 DB 로 실제 실행한다.
     운영에서 찾은 함정을 그대로 넣는다 — 이름이 같은 다른 종사업장 · 발주처가 프로젝트 고객과 다른 수주 ·
     취소 수주 · 통화 섞임 · 프로젝트와 소모품 섞임.
  §2 는 공용 화면 부품(_v5_partials/knk_tax_sameday.html) 원문을 node 로 실제 실행한다.

실행:  python _검증/test_tax_sameday_20261002.py
"""
import ast
import io
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, "app", "templates")
PARTIAL = os.path.join(TPL, "_v5_partials", "knk_tax_sameday.html")

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


db_src = read(os.path.join(ROOT, "app", "database.py"))
main_src = read(os.path.join(ROOT, "app", "main.py"))

# ════════════════════════════════════════════════════════════════════
sec("§1. 서버 조회 — database.tax_same_day 원문을 메모리 DB 로 실행")
# ════════════════════════════════════════════════════════════════════
ns = {}
for n in ast.parse(db_src).body:
    if isinstance(n, ast.FunctionDef) and n.name in ("date_cell_ok", "tax_same_day"):
        exec(compile(ast.get_source_segment(db_src, n), n.name, "exec"), ns)
chk("서버 함수 2개 추출", "tax_same_day" in ns and "date_cell_ok" in ns)
tsd = ns["tax_same_day"]

c = sqlite3.connect(":memory:")
c.executescript("""
CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE projects (id INTEGER PRIMARY KEY, mgmt_code TEXT, name TEXT, customer_id INTEGER, customer_name TEXT);
CREATE TABLE orders (id INTEGER PRIMARY KEY, project_id INTEGER, order_no TEXT, customer_id INTEGER,
                     currency TEXT, status TEXT);
CREATE TABLE order_items (id INTEGER PRIMARY KEY, order_id INTEGER, unit_label TEXT, currency TEXT,
    tax_invoice_date TEXT, tax_invoice_amt1 REAL, tax_invoice_date2 TEXT, tax_invoice_amt2 REAL,
    tax_invoice_date3 TEXT, tax_invoice_amt3 REAL);
CREATE TABLE consumable_orders (id INTEGER PRIMARY KEY, mgmt_code TEXT, co_no TEXT, customer_id INTEGER,
    customer_name TEXT, currency TEXT, model_name TEXT, equip_name TEXT,
    tax_invoice_date TEXT, tax_invoice_amt1 REAL, tax_invoice_date2 TEXT, tax_invoice_amt2 REAL,
    tax_invoice_date3 TEXT, tax_invoice_amt3 REAL);

-- 운영 그대로: 본사(74)·아산(75)은 다른 거래처인데 프로젝트엔 둘 다 '(주) 드림텍' 이라는 이름이 붙어 있다
INSERT INTO customers VALUES (74,'드림텍(본사)'),(75,'드림텍(아산)'),(10,'한국성전(주)');
INSERT INTO projects VALUES
 (1,'011T2606','PBA',74,'(주) 드림텍'), (2,'012T2606','SENSOR',74,'(주) 드림텍'),
 (3,'013T2606','JIG',75,'(주) 드림텍'), (4,'014T2606','취소건',74,'(주) 드림텍'),
 (5,'015T2606','다른날',74,'(주) 드림텍'), (6,'016T2606','중도금',74,'(주) 드림텍');
INSERT INTO orders VALUES
 (11,1,'T-260909-1',74,'KRW',''),        -- 발주처 = 프로젝트 고객
 (12,2,'T-260909-2',75,'KRW',''),        -- ⚠ 발주처(아산)가 프로젝트 고객(본사)과 다르다
 (13,3,'T-260909-3',75,'KRW',''),
 (14,4,'T-260909-4',74,'KRW','CANCELLED'),
 (15,5,'T-260909-5',74,'KRW',''),
 (16,6,'T-260909-6',74,'KRW','');
INSERT INTO order_items (id,order_id,unit_label,currency,tax_invoice_date,tax_invoice_amt1,tax_invoice_date2,tax_invoice_amt2) VALUES
 (101,11,'1호기','', '2026-09-30',100, NULL,NULL),
 (102,11,'2호기','', '2026-09-30',100, NULL,NULL),
 (103,12,'1호기','', '2026-09-30',500, NULL,NULL),
 (104,13,'1호기','', '2026-09-30',700, NULL,NULL),
 (105,14,'1호기','', '2026-09-30',999, NULL,NULL),
 (106,15,'1호기','', '2026-09-29',111, NULL,NULL),
 (107,16,'1호기','', NULL,NULL, '2026-09-30',300);
INSERT INTO consumable_orders (id,mgmt_code,co_no,customer_id,customer_name,currency,model_name,equip_name,tax_invoice_date,tax_invoice_amt1) VALUES
 (201,'001C2609','C-260918-1',74,'(주) 드림텍','KRW','SM-S952','기능검사기','2026-09-30',50),
 (202,'002C2609','C-260918-2',74,'(주) 드림텍','USD','','','2026-09-30',20),
 (203,'003C2609','C-260918-3',10,'한국성전(주)','KRW','','','2026-09-30',77);
""")


def keys(res):
    return sorted("%s:%s" % (x["kind"][0].upper(), x["mgmt_code"]) for x in res["items"])


r = tsd(c, 1, "2026-09-30", iid=101)
chk("본사(74) 묶음 = 프로젝트 1 + 소모품 2", keys(r) == ["C:001C2609", "C:002C2609", "P:011T2606"], keys(r))
chk("⭐이름이 같아도 다른 종사업장(아산 75)은 안 섞인다", "P:013T2606" not in keys(r), keys(r))
chk("⭐발주처가 아산인 수주(012T2606)는 본사 묶음에 안 들어온다", "P:012T2606" not in keys(r), keys(r))
chk("취소된 수주는 빠진다", "P:014T2606" not in keys(r))
chk("다른 날 발행은 빠진다", "P:015T2606" not in keys(r))
chk("다른 차수(2차)는 빠진다", "P:016T2606" not in keys(r))
chk("다른 고객사 소모품은 빠진다", "C:003C2609" not in keys(r))
p1 = [x for x in r["items"] if x["mgmt_code"] == "011T2606"][0]
chk("호기는 수주 단위로 모은다(2대 · 200)", p1["units"] == 2 and p1["amount"] == 200.0, (p1["units"], p1["amount"]))
chk("누른 건에 '지금 보는 건' 표시", p1["is_self"] is True and sum(1 for x in r["items"] if x["is_self"]) == 1)
chk("⭐통화별로만 합친다 — KRW 250(2건) · USD 20(1건)",
    r["totals"] == {"KRW": [250.0, 2], "USD": [20.0, 1]}, r["totals"])
chk("환산 없이 통화를 섞어 더하지 않았다", 270.0 not in [v[0] for v in r["totals"].values()])

r2 = tsd(c, 1, "2026-09-30", iid=103)
chk("⭐아산 발주 수주를 누르면 아산(75) 묶음 — 012T2606 + 013T2606",
    keys(r2) == ["P:012T2606", "P:013T2606"] and r2["customer_id"] == 75, (keys(r2), r2["customer_id"]))

r3 = tsd(c, 2, "2026-09-30", iid=107)
chk("2차는 2차끼리만(혼자)", keys(r3) == ["P:016T2606"] and r3["items"][0]["amount"] == 300.0, keys(r3))

r4 = tsd(c, 1, "2026-09-30", kind="consumable", ref_id=201)
chk("소모품을 눌러도 같은 묶음이 나온다", keys(r4) == keys(r), keys(r4))
chk("이때 '지금 보는 건'은 그 소모품", [x["mgmt_code"] for x in r4["items"] if x["is_self"]] == ["001C2609"])

r5 = tsd(c, 1, "2026-09-30", kind="consumable", ref_id=203)
chk("혼자뿐인 날 — 자기 한 건만", len(r5["items"]) == 1 and r5["items"][0]["is_self"])

r6 = tsd(c, 1, "2026-09-30", kind="project", ref_id=1)
chk("호기 없이 프로젝트만 줘도 된다(프로젝트 고객 기준)", "P:011T2606" in keys(r6) and r6["customer_id"] == 74)

chk("없는 호기 → 빈 결과(오류 아님)", tsd(c, 1, "2026-09-30", iid=99999) == {
    "ok": True, "customer_id": None, "items": [], "totals": {}})
chk("차수가 1~3 이 아니면 거부", tsd(c, 4, "2026-09-30", iid=101)["ok"] is False
    and tsd(c, 0, "2026-09-30", iid=101)["ok"] is False)
chk("날짜가 아니면 거부(주입 방지 포함)",
    tsd(c, 1, "2026-09-30' OR 1=1 --", iid=101)["ok"] is False and tsd(c, 1, "", iid=101)["ok"] is False
    and tsd(c, 1, "2,280,000", iid=101)["ok"] is False)
chk("조회만 한다 — 데이터가 안 바뀐다",
    c.execute("SELECT COUNT(*), SUM(tax_invoice_amt1) FROM order_items").fetchone() == (7, 2510.0))

# ════════════════════════════════════════════════════════════════════
sec("§2. 화면 부품 — knk_tax_sameday.html 원문을 node 로 실행")
# ════════════════════════════════════════════════════════════════════
part = read(PARTIAL)
m = re.search(r"<script>\s*(\(function\(\)\{.*?\}\)\(\);)\s*</script>", part, re.S)
chk("화면 부품 스크립트 추출", m is not None)
PROBE = """
'use strict';
var __appended = [], __fetched = [];
function mkEl(){ var e = { className:'', innerHTML:'', _removed:false, children:[],
  appendChild: function(x){ this.children.push(x); __appended.push(x); return x; },
  remove: function(){ this._removed = true; } }; return e; }
globalThis.window = {};
globalThis.document = { createElement: function(){ return mkEl(); } };
var __resp = null;
globalThis.fetch = function(url){ __fetched.push(url);
  return Promise.resolve({ json: function(){ return Promise.resolve(__resp); } }); };
__SCRIPT__
var T = window.knkTaxSameDayTier, F = window.knkTaxSameDay;
var out = {};
out.tier = [T('tax_invoice_date'), T('tax_invoice_date2'), T('tax_invoice_date3'), T('statement_date'), T('')];
(async function(){
  /* (가) 여러 건 */
  __resp = { ok:true, tier:1, date:'2026-09-30', customer:{id:74, name:'드림텍(본사)'},
    items:[ {kind:'project', mgmt_code:'011T2606', order_no:'T-260909-1', name:'PBA', units:2, amount_text:'\\u20a9200', url:'/project/1?so=T-260909-1', is_self:true},
            {kind:'consumable', mgmt_code:'001C2609', order_no:'C-260918-1', name:'<b>x</b>', units:1, amount_text:'\\u20a950', url:'/consumables/201', is_self:false},
            {kind:'consumable', mgmt_code:'002C2609', order_no:'C-260918-2', name:'', units:1, amount_text:'$20.00', url:'/consumables/202', is_self:false} ],
    totals:[ {currency:'KRW', n:2, text:'\\u20a9250'}, {currency:'USD', n:1, text:'$20.00'} ] };
  var host = mkEl(); F(host, {datefield:'tax_invoice_date', date:'2026-09-30', iid:101});
  await new Promise(function(r){ setTimeout(r, 20); });
  var box = host.children[0];
  out.url = __fetched[0];
  out.html = box.innerHTML; out.removed = box._removed;
  /* (나) 혼자뿐 */
  __resp = { ok:true, tier:1, date:'2026-09-30', customer:{name:'한국성전(주)'},
    items:[ {kind:'consumable', mgmt_code:'003C2609', is_self:true, amount_text:'\\u20a977', url:'/consumables/203'} ], totals:[] };
  var h2 = mkEl(); F(h2, {datefield:'tax_invoice_date', date:'2026-09-30', kind:'consumable', ref_id:203});
  await new Promise(function(r){ setTimeout(r, 20); });
  out.alone_removed = h2.children[0]._removed; out.url2 = __fetched[1];
  /* (다) 부르지 않아야 하는 경우 */
  var n0 = __fetched.length;
  F(mkEl(), {datefield:'statement_date', date:'2026-09-30', iid:1});   // 거래명세서
  F(mkEl(), {datefield:'tax_invoice_date', date:'', iid:1});            // 발행일 없음
  F(mkEl(), {datefield:'tax_invoice_date', date:'2,280,000', iid:1});   // 날짜 아님
  F(mkEl(), {datefield:'tax_invoice_date', date:'2026-09-30'});         // 누른 건을 모름
  out.no_call = __fetched.length - n0;
  /* (라) 서버 오류 */
  __resp = { ok:false, error:'permission_denied' };
  var h3 = mkEl(); F(h3, {datefield:'tax_invoice_date2', date:'2026-09-30', iid:5});
  await new Promise(function(r){ setTimeout(r, 20); });
  out.err_removed = h3.children[0]._removed; out.url3 = __fetched[__fetched.length-1];
  console.log(JSON.stringify(out));
})();
"""
tmpd = tempfile.mkdtemp(prefix="z1136_")
jsf = os.path.join(tmpd, "probe.js")
io.open(jsf, "w", encoding="utf-8", newline="\n").write(PROBE.replace("__SCRIPT__", m.group(1) if m else ""))
node_ok = True
try:
    raw = subprocess.check_output(["node", jsf], stderr=subprocess.STDOUT).decode("utf-8", "replace")
    R = json.loads(raw.strip().splitlines()[-1])
except Exception as e:
    print("  ⚠ node 실행 불가 — §2 건너뜀: %s" % e)
    R, node_ok = {}, False

if node_ok:
    chk("날짜 칸 이름 → 차수(1·2·3) · 거래명세서는 0", R["tier"] == [1, 2, 3, 0, 0], R["tier"])
    chk("서버를 정확한 조건으로 부른다(호기)", R["url"] == "/sales/tax-invoice/same-day?tier=1&date=2026-09-30&iid=101", R["url"])
    chk("소모품은 kind·ref_id 로 부른다",
        R["url2"] == "/sales/tax-invoice/same-day?tier=1&date=2026-09-30&kind=consumable&ref_id=203", R["url2"])
    chk("차수 2는 tier=2 로 부른다", "tier=2" in R["url3"], R["url3"])
    h = R["html"]
    chk("⭐「같은 날 함께 발행 3건」이 그려진다", "같은 날 함께 발행" in h and ">3건<" in h, h[:120])
    chk("고객사·발행일·차수가 보인다", "드림텍(본사)" in h and "2026-09-30" in h and "1차" in h)
    chk("관리번호·수주번호·금액이 보인다", all(x in h for x in ("011T2606", "T-260909-1", "001C2609", "$20.00")))
    chk("지금 보는 건이 표시된다", "지금 보는 건" in h and 'knk-tsd-row self' in h)
    chk("소모품 표식이 붙는다", h.count(">소모품<") >= 2)
    chk("각 줄이 그 건으로 가는 링크다", 'href="/project/1?so=T-260909-1"' in h and 'href="/consumables/201"' in h)
    chk("통화가 섞이면 통화별 합계 2줄", h.count('knk-tsd-tot') == 2 and "(KRW)" in h and "(USD)" in h)
    chk("⭐이름에 든 태그는 글자로 바뀐다(화면 주입 방지)", "<b>x</b>" not in h and "&lt;b&gt;x&lt;/b&gt;" in h)
    chk("혼자뿐이면 아무것도 안 그린다", R["alone_removed"] is True and R["removed"] is False)
    chk("거래명세서·발행일 없음·날짜 아님·대상 모름 → 서버를 안 부른다", R["no_call"] == 0, R["no_call"])
    chk("서버가 거절하면 조용히 접는다(팝업은 그대로 쓴다)", R["err_removed"] is True)

# ════════════════════════════════════════════════════════════════════
sec("§3. 소스 — 연결과 권한")
# ════════════════════════════════════════════════════════════════════
detail = read(os.path.join(TPL, "project_detail.html"))
board = read(os.path.join(TPL, "schedule_board.html"))
chk("프로젝트 상세가 공용 부품을 포함한다", 'include "_v5_partials/knk_tax_sameday.html"' in detail)
chk("작업일정표가 공용 부품을 포함한다", 'include "_v5_partials/knk_tax_sameday.html"' in board)
chk("프로젝트 상세 세금계산서 팝업이 부른다", detail.count("window.knkTaxSameDay(pop,") == 1)
chk("작업일정표 팝업 2곳(호기별·행)이 부른다", board.count("window.knkTaxSameDay(pop,") == 2,
    board.count("window.knkTaxSameDay(pop,"))


def func_src(src, name):
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name:
            return ast.get_source_segment(src, n) or ""
    return ""


ep = func_src(main_src, "tax_invoice_same_day")
chk("입구가 있다", bool(ep))
chk("⭐세금계산서 금액은 영업·관리만(can_view_sales)", "can_view_sales(u)" in ep and "permission_denied" in ep)
chk("로그인 확인", "login_required" in ep)
chk("날짜·차수 검증", "date_cell_ok(date)" in ep and "tier not in (1, 2, 3)" in ep)
chk("금액 표기는 공용 money(z751)", "_fmt_money(" in ep)
chk("읽기만 한다(UPDATE·INSERT·DELETE 없음)",
    not re.search(r"\b(UPDATE|INSERT|DELETE)\b", ep + func_src(db_src, "tax_same_day")))
fn = func_src(db_src, "tax_same_day")
chk("⭐고객사를 이름이 아니라 id 로 맞춘다",
    "customer_id" in fn and not re.search(r"customer_name\s*=", fn) and "customer_name" not in
    "".join(l for l in fn.splitlines() if "WHERE" in l or "AND " in l))
chk("수주 발주처 id 가 우선", "COALESCE(o.customer_id, p.customer_id)" in fn)
chk("취소 수주 제외", "<>'CANCELLED'" in fn)

shutil.rmtree(tmpd, ignore_errors=True)
print("\n" + "=" * 72)
print("결과: %d/%d 통과%s" % (OK, OK + FAIL, "" if not FAIL else "  — ❌ 실패 %d" % FAIL))
print("=" * 72)
sys.exit(1 if FAIL else 0)
