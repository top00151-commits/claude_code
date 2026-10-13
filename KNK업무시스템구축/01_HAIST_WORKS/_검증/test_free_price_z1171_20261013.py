# -*- coding: utf-8 -*-
"""z1171 시험 — 무상 제품은 단가 0 으로 등록(이새롬 프로 요청 · 대표 「0을 적으면 무상」 2026-10-13).

규칙: 금액 칸을 **비워 두면** 아직 안 적은 것(지금처럼 막는다 — z876·z1050 깜빡함 잡기 유지) ·
      **0을 적으면** 무상(통과) · 합계가 0보다 크면 예전과 같다.

  §1 서버 /projects/new (임시 DB · TestClient) — 단가 칸 · 제품 항목 · 호기별 금액 · 추가 발주(개조) · 제안 단계
  §2 실제 화면(Chromium · 시험용 서버 · 임시 DB) — 이새롬 프로가 한 대로 채우고 「＋ 등록」
     · 브라우저는 Playwright 가 있는 파이썬이 따로 돌린다(이 PC 는 3.12) — 서버·DB 확인은 이 파이썬이 한다
  §3 바뀐 곳 원문(안내 글자 · 추가 수주 창 · 전체 등록 화면 안내)
"""
import contextlib
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1171-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1171_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"),
                     ("name_en", "TEXT"), ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"),
                     ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version) "
                 "VALUES ('가상관리자', 'admin', 'T901', 'T901', 'sso_only_no_local_password', 1, 1)")
    ADMIN = dict(conn.execute("SELECT * FROM users WHERE employee_no='T901'").fetchone())
    conn.execute("INSERT INTO customers (name) VALUES ('가상고객')")

import app.main as M                                        # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

M.get_user = lambda request: ADMIN
cl = TestClient(M.app, follow_redirects=False)

OK = FAIL = 0


def check(label, cond, got=None):
    global OK, FAIL
    if cond:
        OK += 1
        print("  [OK] " + label)
    else:
        FAIL += 1
        print("  [FAIL] " + label + ("   ← %r" % (got,) if got is not None else ""))


BASE = {"quick": "1", "customer_name": "가상고객", "biz_div": "T", "project_type": "NEW_EQUIP",
        "po_type": "신규", "status": "진행중", "confirm_now": "1", "order_date": "2026-10-08",
        "due_date": "2026-10-15", "currency": "KRW", "equip_name": "성능검사기", "model": "SM-TEST",
        "unit_qty": "1"}


def post(**kw):
    f = dict(BASE)
    f.update(kw)
    with contextlib.redirect_stdout(io.StringIO()):
        r = cl.post("/projects/new", data=f)
    return r.status_code, r.headers.get("location", "")


def proj(name):
    with D.db_session() as c:
        r = c.execute("SELECT * FROM projects WHERE name=? ORDER BY id DESC", (name,)).fetchone()
        return dict(r) if r else None


def orders_of(pid):
    with D.db_session() as c:
        return [dict(r) for r in c.execute("SELECT * FROM orders WHERE project_id=? ORDER BY id", (pid,))]


def items_of(oid):
    with D.db_session() as c:
        return [dict(r) for r in c.execute("SELECT * FROM order_items WHERE order_id=? ORDER BY id", (oid,))]


def semi(name, prices, names=None, **kw):
    names = names or ["TOP PINBLOCK"] * len(prices)
    return post(name=name, shipment_form="SEMI", unit_price="", order_amount="0",
                **{"it_name[]": names, "it_spec[]": names, "it_qty[]": ["1"] * len(prices),
                   "it_price[]": prices}, **kw)


def ok_new(label, res, name):
    st, loc = res
    p = proj(name)
    check(label + " → 등록됨", st == 303 and "error=" not in loc and p is not None, (st, loc))
    return p


def blocked(label, res, name=None):
    st, loc = res
    check(label + " → 막힘(unit_price_required)",
          st == 303 and "error=unit_price_required" in loc and (name is None or proj(name) is None), (st, loc))


print("=" * 78)
print("§1 서버 /projects/new")
print("=" * 78)
p1 = ok_new("1 신규·완제품·단가 1,000(예전과 같음)", post(name="z1171-1", unit_price="1000", order_amount="1000"), "z1171-1")
M1 = (p1 or {}).get("mgmt_code")
check("   관리번호가 붙음(추가 발주 시험에 씀)", bool(M1), M1)

p2 = ok_new("2 신규·완제품·단가 0(무상)", post(name="z1171-2", unit_price="0", order_amount="0"), "z1171-2")
if p2:
    os2 = orders_of(p2["id"])
    check("   수주 1건 · 금액 0", len(os2) == 1 and float(os2[0]["total_amount"] or 0) == 0.0,
          [(o["order_no"], o["total_amount"]) for o in os2])
blocked("3 신규·완제품·단가 비움", post(name="z1171-3", unit_price="", order_amount=""), "z1171-3")

p4 = ok_new("4 신규·제품·항목 TOP PINBLOCK 단가 0(이새롬 프로 화면)", semi("z1171-4", ["0"]), "z1171-4")
if p4:
    os4 = orders_of(p4["id"])
    it4 = items_of(os4[0]["id"]) if os4 else []
    check("   항목 1줄 저장 · 단가 0 · 금액 0 · 수주 금액 0",
          len(it4) == 1 and float(it4[0]["unit_price"] or 0) == 0.0 and float(it4[0]["amount"] or 0) == 0.0
          and float(os4[0]["total_amount"] or 0) == 0.0,
          [(i.get("unit_label"), i.get("unit_price"), i.get("amount")) for i in it4])
blocked("5 신규·제품·항목 단가 비움", semi("z1171-5", [""]), "z1171-5")
p6 = ok_new("6 신규·제품·1,000 + 비움(합계>0 — 예전과 같음)", semi("z1171-6", ["1000", ""], ["A", "B"]), "z1171-6")
if p6:
    it6 = items_of(orders_of(p6["id"])[0]["id"])
    check("   항목 2줄(1,000 · 0)", [float(i["unit_price"] or 0) for i in it6] == [1000.0, 0.0],
          [i["unit_price"] for i in it6])
ok_new("7 신규·제품·0 + 0(모두 무상)", semi("z1171-7", ["0", "0"], ["A", "B"]), "z1171-7")
blocked("8 신규·제품·0 + 비움", semi("z1171-8", ["0", ""], ["A", "B"]), "z1171-8")
blocked("9 신규·제품·-100(합계가 마이너스 — 예전과 같음)", semi("z1171-9", ["-100"]), "z1171-9")

n_before = len(orders_of(p1["id"])) if p1 else 0
st, loc = semi("z1171-10", ["0"], po_type="개조", mgmt_code=M1 or "")
os10 = orders_of(p1["id"]) if p1 else []
new10 = os10[n_before:]
check("10 개조(추가 발주)·관리번호·제품·항목 0 → 기존 프로젝트에 수주 추가(이새롬 프로 상황 그대로)",
      st == 303 and "error=" not in loc and len(new10) == 1, (st, loc, len(new10)))
if new10:
    it10 = items_of(new10[0]["id"])
    check("   새 수주 금액 0 · 항목 TOP PINBLOCK 단가 0 · PO유형 개조",
          float(new10[0]["total_amount"] or 0) == 0.0 and len(it10) == 1
          and float(it10[0]["unit_price"] or 0) == 0.0 and (new10[0].get("po_type") or "") == "개조",
          (new10[0]["total_amount"], [(i["unit_label"], i["unit_price"]) for i in it10], new10[0].get("po_type")))
st, loc = semi("z1171-11", [""], po_type="개조", mgmt_code=M1 or "")
check("11 개조(추가 발주)·제품·항목 단가 비움 → 막힘", st == 303 and "error=unit_price_required" in loc
      and len(orders_of(p1["id"]) if p1 else []) == len(os10), (st, loc))

ok_new("12 신규·완제품 2대·호기별 0 · 0(모두 무상)",
       post(name="z1171-12", unit_qty="2", multi_unit="1", unit_price="", order_amount="0",
            **{"unit_amount[]": ["0", "0"]}), "z1171-12")
blocked("13 신규·완제품 2대·호기별 0 · 비움",
        post(name="z1171-13", unit_qty="2", multi_unit="1", unit_price="", order_amount="0",
             **{"unit_amount[]": ["0", ""]}), "z1171-13")
ok_new("14 제안 단계(초기협의)·단가 비움(예전과 같음 — 검사 안 함)",
       post(name="z1171-14", status="초기협의", confirm_now="", unit_price="", order_amount=""), "z1171-14")

print()
print("=" * 78)
print("§2 실제 화면 — Chromium · 시험용 서버(임시 DB)")
print("=" * 78)

# 브라우저 쪽(Playwright) — 화면을 채우고 「＋ 등록」을 누른 결과만 돌려준다. DB 확인은 아래(이 파이썬)에서.
DRIVER = r'''
import json, sys
from playwright.sync_api import sync_playwright
BASEURL, M1, PID2 = sys.argv[1], sys.argv[2], sys.argv[3]
MODE = sys.argv[4] if len(sys.argv) > 4 else "main"          # main = 등록 · edit = 정보 수정(quick-edit)
EDIT_IDS = sys.argv[5:]                                       # edit 일 때: 무상 제품 pid · 무상 완제품 pid
out = {"page_errors": [], "cases": {}}

def fill_common(pg, name, po="신규", mgmt=""):
    pg.goto(BASEURL + "/projects/quick?biz_div=T")
    pg.wait_for_load_state("domcontentloaded")
    pg.fill("input[data-cust-picker]", "가상고객")
    pg.wait_for_selector(".knkcust-it", timeout=8000)
    pg.dispatch_event(".knkcust-it >> nth=0", "mousedown")
    if po != "신규":
        pg.select_option("#qPoType", po)
        pg.fill("#qMgmtInput", mgmt)
    pg.evaluate("""(n)=>{ var s=document.getElementById('qNameSel'), i=document.getElementById('qNameInp');
                         if(s && s.offsetParent!==null){ s.value='__free__'; if(typeof qNamePick==='function') qNamePick('__free__'); }
                         if(i){ i.style.display=''; i.value=n; } }""", name)
    pg.fill("input[name=model]", "SM-G586B USB PBA")
    pg.fill("input[name=equip_name]", "성능+GRIP검사기_케이스 포함 MODIFY")
    pg.evaluate("""()=>{ var c=document.getElementById('qProdNotify'); if(c && c.checked) c.click(); }""")
    for sel, v in (("#qOrderDate", "2026-10-08"), ("#qDueDate", "2026-10-15")):
        if pg.query_selector(sel):
            pg.fill(sel, v)

def pick_semi(pg, rows):
    pg.click("#qFormBtn")
    pg.click(".qfsel-opt[data-v='SEMI']")
    while pg.evaluate("document.querySelectorAll('#qItemRows .qi-row').length") < len(rows):
        pg.evaluate("qItemAdd()")
    for k, (nm, price) in enumerate(rows):
        row = "#qItemRows .qi-row >> nth=%d" % k
        pg.fill(row + " >> .qi-name", nm)
        pg.fill(row + " >> .qi-spec", nm)
        pg.fill(row + " >> .qi-qty", "1")
        if price is not None:
            pg.fill(row + " >> .qi-price", price)

def submit(pg, path="/projects/new"):
    posts = []
    pg.on("request", lambda rq: posts.append(rq.url) if (rq.method == "POST" and path in rq.url) else None)
    pg.click("button.qf-save")
    pg.wait_for_timeout(1500)
    try:
        pg.wait_for_load_state("domcontentloaded", timeout=8000)
    except Exception:
        pass
    try:
        err = pg.evaluate("""()=>{ var e=document.getElementById('qfErr');
                                   return e ? {show:e.classList.contains('show'), text:(e.textContent||'').trim(),
                                               active:(document.activeElement||{}).className||''} : null; }""")
    except Exception:
        err = None
    return {"posts": len(posts), "err": err, "url": pg.url}

def fup(pg, price):
    # 프로젝트 상세 「추가 수주」 창 — 칸을 채우고 그 창의 등록 함수를 그대로 부른다(창 여는 단추는 안 누름)
    msgs, posts = [], []
    pg.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    pg.on("request", lambda rq: posts.append(rq.url) if (rq.method == "POST" and "add-followup-order" in rq.url) else None)
    pg.goto(BASEURL + "/project/" + PID2)
    try:
        pg.wait_for_load_state("networkidle", timeout=15000)   # 상세 화면은 열린 뒤 한 번 더 불리기도 한다
    except Exception:
        pass
    has = None
    for _t in range(5):
        try:
            has = pg.evaluate("typeof submitFollowupOrder==='function' && !!document.getElementById('fup_total_amount')")
            pg.evaluate("""(pr)=>{ document.getElementById('fup_order_date').value='2026-10-08';
                                   document.getElementById('fup_due_date').value='2026-10-15';
                                   document.getElementById('fup_total_amount').value=pr;
                                   document.getElementById('fup_qty').value='1'; }""", price) if has else None
            break
        except Exception:
            pg.wait_for_timeout(1000)
    if not has:
        return {"has": has}
    try:
        pg.evaluate("submitFollowupOrder()")
    except Exception:
        pass                                   # 성공하면 화면을 다시 불러 실행 문맥이 바뀐다
    pg.wait_for_timeout(2000)
    return {"has": True, "msgs": msgs, "posts": len(posts)}

with sync_playwright() as p:
    br = p.chromium.launch()
    def run(key, fn):
        # 시험마다 새 브라우저 상태 — 등록 화면은 막혔을 때 입력을 저장해 두었다가 다음에 되살리므로 섞이지 않게
        ctx = br.new_context(viewport={"width": 1400, "height": 1000})
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: out["page_errors"].append(key + ": " + str(e)[:200]))
        try:
            out["cases"][key] = fn(pg)
        except Exception as e:
            out["cases"][key] = {"exc": str(e)[:400]}
        finally:
            ctx.close()
    def a1(pg):
        fill_common(pg, "z1171-A1")
        ph1 = pg.evaluate("(document.getElementById('qUnitPrice')||{}).placeholder")
        pick_semi(pg, [("TOP PINBLOCK", "0")])
        ph2 = pg.evaluate("(document.querySelector('#qItemRows .qi-price')||{}).placeholder")
        r = submit(pg); r["ph"] = [ph1, ph2]; return r
    def a2(pg):
        fill_common(pg, "z1171-A2", po="개조", mgmt=M1); pick_semi(pg, [("TOP PINBLOCK", "0")]); return submit(pg)
    def b(pg):
        fill_common(pg, "z1171-B"); pick_semi(pg, [("TOP PINBLOCK", None)]); return submit(pg)
    def c(pg):
        fill_common(pg, "z1171-C"); pick_semi(pg, [("A", "0"), ("B", None)]); return submit(pg)
    def d(pg):
        fill_common(pg, "z1171-D"); pick_semi(pg, [("TOP PINBLOCK", "1000")]); return submit(pg)
    def c2(pg):
        fill_common(pg, "z1171-C2"); pick_semi(pg, [("A", "0"), ("B", "0")])
        r = submit(pg)
        r["units"] = pg.evaluate("document.querySelectorAll('#qUnitRows .qf-unit-amt').length") if r.get("posts") == 0 else None
        return r
    def d2(pg):
        fill_common(pg, "z1171-D2"); pick_semi(pg, [("A", "100"), ("B", "200")]); return submit(pg)
    def e1(pg):
        fill_common(pg, "z1171-E1"); pg.fill("#qUnitPrice", "0"); return submit(pg)
    def e2(pg):
        fill_common(pg, "z1171-E2"); return submit(pg)
    def f(pg):
        return fup(pg, "")
    def g(pg):
        return fup(pg, "0")
    def open_edit(pg, pid):
        navs = []
        pg.on("framenavigated", lambda fr: navs.append(fr.url) if fr == pg.main_frame else None)
        pg.goto(BASEURL + "/projects/" + pid + "/quick-edit")
        try:
            pg.wait_for_load_state("networkidle", timeout=15000)   # 열린 뒤 한 번 더 불리기도 한다(아래 navs 에 남김)
        except Exception:
            pass
        items = None
        for _t in range(5):
            try:
                pg.evaluate("""()=>{ var c=document.getElementById('qProdNotify'); if(c && c.checked) c.click(); }""")
                items = pg.evaluate("!!document.getElementById('qItemRows')")
                break
            except Exception:
                pg.wait_for_timeout(1000)
        return navs, items
    def h(pg):
        navs, items = open_edit(pg, EDIT_IDS[0])
        r = submit(pg, "/edit"); r["items"] = items; r["navs"] = navs[:4]; return r
    def i1(pg):
        navs, _ = open_edit(pg, EDIT_IDS[1])
        r = submit(pg, "/edit"); r["navs"] = navs[:4]; return r
    def i2(pg):
        open_edit(pg, EDIT_IDS[1])
        pg.fill("#qUnitPrice", "0")
        return submit(pg, "/edit")
    if MODE == "main":
        todo = (("A1", a1), ("A2", a2), ("B", b), ("C", c), ("C2", c2), ("D", d), ("D2", d2),
                ("E1", e1), ("E2", e2), ("F", f), ("G", g))
    else:
        todo = (("H", h), ("I1", i1), ("I2", i2))
    for k, fn in todo:
        run(k, fn)
    br.close()
print("@@RESULT@@" + json.dumps(out, ensure_ascii=False))
'''


def find_pw_python():
    cands = [sys.executable, os.environ.get("KNK_PW_PY", ""),
             os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python312\python.exe"), "python"]
    for c in cands:
        if not c:
            continue
        try:
            if subprocess.run([c, "-c", "import playwright.sync_api"], capture_output=True, timeout=60).returncode == 0:
                return c
        except Exception:
            pass
    return None


import uvicorn                                              # noqa: E402

_sk = socket.socket()
_sk.bind(("127.0.0.1", 0))
PORT = _sk.getsockname()[1]
_sk.close()
srv = uvicorn.Server(uvicorn.Config(M.app, host="127.0.0.1", port=PORT, lifespan="off", log_level="warning"))
threading.Thread(target=srv.run, daemon=True).start()
for _ in range(150):
    if srv.started:
        break
    time.sleep(0.1)
BASEURL = "http://127.0.0.1:%d" % PORT
check("시험용 서버 뜸(127.0.0.1 · 빈 포트 · 시작 작업 끔)", srv.started, PORT)

PWPY = find_pw_python()
check("Playwright 있는 파이썬 찾음", bool(PWPY), PWPY)
DRV = os.path.join(TMP, "pw_driver.py")
io.open(DRV, "w", encoding="utf-8").write(DRIVER)


def drive(mode, *ids):
    """브라우저 쪽을 한 번 돌려 (cases, page_errors) 를 받는다."""
    if not PWPY:
        return {}, ["(브라우저 못 돌림)"]
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run([PWPY, DRV, BASEURL, M1 or "", str((p2 or {}).get("id") or 0), mode] + [str(x) for x in ids],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600, env=env)
    line = [x for x in (r.stdout or "").splitlines() if x.startswith("@@RESULT@@")]
    if line:
        res = json.loads(line[-1][len("@@RESULT@@"):])
        return res["cases"], res["page_errors"]
    print("   (브라우저 쪽 출력)", (r.stdout or "")[-800:], (r.stderr or "")[-1500:])
    return {}, ["(브라우저 결과 없음)"]


nb = len(orders_of(p1["id"])) if p1 else 0
nb2 = len(orders_of(p2["id"])) if p2 else 0
cases, page_errors = drive("main")
na = len(orders_of(p1["id"])) if p1 else 0
na2 = len(orders_of(p2["id"])) if p2 else 0
_pa1, _pe1 = proj("z1171-A1"), proj("z1171-E1")
cases_e, page_errors_e = (drive("edit", _pa1["id"], _pe1["id"]) if (_pa1 and _pe1) else ({}, ["(수정 시험용 프로젝트 없음)"]))
cases.update(cases_e)
page_errors = page_errors + page_errors_e


def case(k):
    return cases.get(k) or {}


a1 = case("A1")
check("안내 글자: 위 단가 칸 · 항목 단가 칸 = 「무상이면 0」", a1.get("ph") == ["무상이면 0", "무상이면 0"], a1.get("ph"))
pa1 = proj("z1171-A1")
check("A1 신규·제품·단가 0 →「＋ 등록」이 서버로 감 · 저장됨", a1.get("posts") == 1 and pa1 is not None, a1)
if pa1:
    oa1 = orders_of(pa1["id"])
    ia1 = items_of(oa1[0]["id"]) if oa1 else []
    check("   저장된 항목 TOP PINBLOCK 단가 0 · 수주 금액 0",
          len(ia1) == 1 and float(ia1[0]["unit_price"] or 0) == 0.0 and float(oa1[0]["total_amount"] or 0) == 0.0,
          [(i["unit_label"], i["unit_price"]) for i in ia1])
a2 = case("A2")
check("A2 이새롬 프로 화면 그대로(개조·관리번호 %s·제품·TOP PINBLOCK 0) → 서버로 감 · 기존 프로젝트에 수주 1건 추가" % M1,
      a2.get("posts") == 1 and na == nb + 1, (a2, nb, na))
b = case("B")
eb = b.get("err") or {}
check("B 항목 단가 비움 → 서버로 안 감 · 「항목 단가를 적어 주세요 (무상이면 0).」 · 커서가 단가 칸",
      b.get("posts") == 0 and eb.get("show") and eb.get("text") == "항목 단가를 적어 주세요 (무상이면 0)."
      and "qi-price" in (eb.get("active") or ""), b)
check("   저장 안 됨", proj("z1171-B") is None)
c_ = case("C")
check("C 항목 2줄 0 + 비움 → 막힘 · 「항목 단가를 적어 주세요 (무상이면 0).」(호기 문구 아님)",
      c_.get("posts") == 0 and (c_.get("err") or {}).get("show")
      and (c_.get("err") or {}).get("text") == "항목 단가를 적어 주세요 (무상이면 0).", c_)
c2_ = case("C2")
check("C2 항목 2줄 0 + 0(모두 무상) → 통과 · 저장됨", c2_.get("posts") == 1 and proj("z1171-C2") is not None, c2_)
d_ = case("D")
check("D 항목 1,000 → 통과(예전과 같음)", d_.get("posts") == 1 and proj("z1171-D") is not None, d_)
d2_ = case("D2")
check("D2 항목 2줄 100 + 200 → 통과(예전과 같음)", d2_.get("posts") == 1 and proj("z1171-D2") is not None, d2_)
e1 = case("E1")
check("E1 완제품·단가 칸 0 → 통과 · 저장됨", e1.get("posts") == 1 and proj("z1171-E1") is not None, e1)
e2 = case("E2")
check("E2 완제품·단가 칸 비움 → 막힘 · 「단가를 입력하세요 (무상이면 0).」",
      e2.get("posts") == 0 and (e2.get("err") or {}).get("show")
      and (e2.get("err") or {}).get("text") == "단가를 입력하세요 (무상이면 0).", e2)
f_ = case("F")
check("F 프로젝트 상세 「추가 수주」·1대 단가 비움 → 서버로 안 감 · 「1대 단가를 입력하세요 (무상이면 0)」",
      f_.get("has") and f_.get("posts") == 0 and "1대 단가를 입력하세요 (무상이면 0)" in (f_.get("msgs") or []), f_)
g_ = case("G")
new_g = orders_of(p2["id"])[nb2:] if p2 else []
check("G 프로젝트 상세 「추가 수주」·1대 단가 0 → 서버로 감 · 수주 1건 추가 · 금액 0",
      g_.get("has") and g_.get("posts") == 1 and na2 == nb2 + 1 and len(new_g) == 1
      and float(new_g[0]["total_amount"] or 0) == 0.0, (g_, nb2, na2, [o["total_amount"] for o in new_g]))
h_ = case("H")
check("H 무상 제품 「정보 수정」 → 항목 칸 없음 · 그대로 저장이 서버로 감(금액 0 이라고 막히지 않음)",
      h_.get("items") is False and h_.get("posts") == 1, h_)
i1_ = case("I1")
check("I1 무상 완제품 「정보 수정」·단가 칸 빈 채 → 막힘 · 「단가를 입력하세요 (무상이면 0).」(깜빡함 잡기 그대로)",
      i1_.get("posts") == 0 and (i1_.get("err") or {}).get("text") == "단가를 입력하세요 (무상이면 0).", i1_)
i2_ = case("I2")
check("I2 같은 화면에 0 을 적으면 → 저장이 서버로 감", i2_.get("posts") == 1, i2_)
check("화면 스크립트 오류 0 (pageerror)", not page_errors, page_errors[:3])
srv.should_exit = True

print()
print("=" * 78)
print("§3 바뀐 곳 원문")
print("=" * 78)
TPL = os.path.join(ROOT, "app", "templates")
qf = io.open(os.path.join(TPL, "project_quick_form.html"), encoding="utf-8").read()
check("간편 등록: 빈칸·0 판정 함수 qPriceGiven 1개", qf.count("function qPriceGiven(") == 1)
check("간편 등록: 세 검사(호기별·제품 항목·단가 칸)가 qPriceGiven 을 씀", qf.count("qPriceGiven") >= 4, qf.count("qPriceGiven"))
check("간편 등록: 「0보다 커야」 문구 없음", "0보다 커야" not in qf)
check("간편 등록: 제품 항목·금액 검사는 항목 칸이 있을 때(새 등록)만 — 수정 화면은 건너뜀",
      "if(_semiAmt<=0 && document.getElementById('qItemRows')){" in qf)
check("간편 등록: 템플릿 주석에 Jinja 기호 없음(z1171 줄)",
      not any(("z1171" in ln) and ("{%" in ln or "{{" in ln) for ln in qf.splitlines()))
check("간편 등록: 제품(SEMI)은 등록할 때 호기별 금액 검사를 건너뜀(호기 없음 · 항목 검사가 함)",
      "toUpperCase()!=='SEMI')){   /* z1171: 제품(SEMI)은 호기 없음" in qf)
check("간편 등록: 단가 칸 안내 글자를 「0」으로 되돌리는 줄 없음(호기별 모드 오갈 때)",
      "up.placeholder='0'" not in qf and "up.placeholder=_eq?'0'" not in qf
      and qf.count("무상이면 0") >= 6, qf.count("무상이면 0"))
pd = io.open(os.path.join(TPL, "project_detail.html"), encoding="utf-8").read()
check("추가 수주 창: 0 은 적었을 때만 통과 · 「(무상이면 0)」",
      "(unit === 0 && unitRaw.trim() === '')" in pd and "1대 단가를 입력하세요 (무상이면 0)" in pd)
pf = io.open(os.path.join(TPL, "project_form.html"), encoding="utf-8").read()
check("전체 등록 화면 안내: 「무상이면 0 을 적으세요」 · 「0보다 큰 값」 없음",
      "무상이면 0 을 적으세요" in pf and "0보다 큰 값이어야" not in pf)
mp = io.open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
check("서버: _up_given · _z1050_blank · _ua_given 셋 다 있음",
      all(k in mp for k in ("_up_given = bool(", "_z1050_blank = False", "_ua_given = bool(")))
check("서버: 옛 조건 `if _z1050_total <= 0:` 없음", "if _z1050_total <= 0:" not in mp)

print()
print("=" * 78)
print("결과: %d개 중 실패 %d" % (OK + FAIL, FAIL))
print("=" * 78)
sys.exit(1 if FAIL else 0)
