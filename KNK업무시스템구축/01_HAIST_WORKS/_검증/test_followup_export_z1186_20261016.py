# -*- coding: utf-8 -*-
"""z1186 시험 — 추가 발주 등록 때 거래구분(내수/수출)을 화면에 보이는 그대로 저장 + 발주처를 따라 미리 채움
   (이새롬 프로 신고 「011T2607 추가 발주를 드림텍(국내)로 작성하면 KNK VINA·수출로 바뀐다」 ·
    대표 「발주처 따라 채움 + 고른 대로 저장」 2026-10-16)

  §1 서버(임시 DB · TestClient)
     · /api/customers/options 의 foreign(나라 칸: 해외=True · 빈칸/'None'=False)
     · /projects/new 추가 발주: 화면의 거래구분이 새 수주의 호기마다 그대로(완제품 1대·2대 · 제품 항목) — 예전엔 비어 프로젝트 값 상속
     · 거래구분을 안 보낸 추가 발주 · 상세 「＋ 추가 발주」 창 · add_followup_order(is_export=None) = 예전 그대로(비움=상속)
     · 신규 등록은 그대로(프로젝트 거래구분)
  §2 실제 화면(Chromium · 시험용 서버 · 임시 DB) — 이새롬 프로가 하는 순서 그대로
     · 관리번호 먼저: 수출 프로젝트(해외 고객) → 같은 고객 채워짐 = 수출 · 발주처를 국내로 바꾸면 내수 → 등록 → DB 내수
     · 발주처 먼저(국내) → PO 개조 → 관리번호(수출 프로젝트) → 내수 그대로 → 등록 → DB 내수
     · 나라 빈칸인 수출 고객(삼성전자 같은 경우) 프로젝트의 같은 고객 추가 발주 = 프로젝트 값(수출)
     · 국내 프로젝트에 해외 발주처 = 수출 · 사람이 먼저 바꾼 값은 안 덮음 · 신규 등록·정보 수정 화면은 안 건드림 · 스크립트 오류 0
     · 브라우저는 Playwright 가 있는 파이썬이 따로 돌린다(이 PC 는 3.12) — 서버·DB 확인은 이 파이썬이 한다
  §3 바뀐 곳 원문
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1186-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1186_")
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
    ccols = {r[1] for r in conn.execute("PRAGMA table_info(customers)")}
    for col in ("alias", "country"):
        if col not in ccols:
            conn.execute("ALTER TABLE customers ADD COLUMN %s TEXT" % col)
    CUST = {}
    for key, name, alias, country in (("VINA", "가상 VINA", "가상 VINA", "Vietnam"),
                                      ("DOM", "(주) 가상국내", "가상국내(동탄)", ""),
                                      ("SAM", "가상삼성(주)", "가상삼성", ""),
                                      ("NONE", "가상널", "가상널", "None"),
                                      ("ASAN", "(주) 가상아산", "가상아산", "")):
        conn.execute("INSERT INTO customers (name, alias, country) VALUES (?,?,?)", (name, alias, country))
        CUST[key] = conn.execute("SELECT id FROM customers WHERE name=?", (name,)).fetchone()[0]

import app.main as M                                        # noqa: E402
import app.project_workflow as PW                          # noqa: E402
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


BASE = {"quick": "1", "biz_div": "T", "project_type": "NEW_EQUIP", "status": "진행중", "confirm_now": "1",
        "order_date": "2026-10-13", "due_date": "2026-10-27", "equip_name": "기능검사기", "model": "SM-TEST PBA",
        "unit_qty": "1", "shipment_form": "ASSEMBLY"}


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


def new_project(name, ckey, iex, ccy):
    alias = {"VINA": "가상 VINA", "DOM": "가상국내(동탄)", "SAM": "가상삼성", "NONE": "가상널", "ASAN": "가상아산"}[ckey]
    st, loc = post(name=name, po_type="신규", customer_name=alias, customer_id=str(CUST[ckey]), is_export=iex,
                   currency=ccy, unit_price="1000", order_amount="1000", **{"unit_amount[]": ["1000"]})
    p = proj(name)
    check("준비: 프로젝트 %s(%s · %s) 등록" % (name, alias, "수출" if iex == "1" else "내수"),
          st == 303 and "error=" not in loc and p is not None and p.get("mgmt_code"), (st, loc))
    return p


def followup(p, ckey, iex=None, n=1, sf="ASSEMBLY", items=None, po="개조", ccy="KRW"):
    alias = {"VINA": "가상 VINA", "DOM": "가상국내(동탄)", "SAM": "가상삼성", "NONE": "가상널", "ASAN": "가상아산"}[ckey]
    kw = dict(name=p["name"], po_type=po, mgmt_code=p["mgmt_code"], customer_name=alias, customer_id=str(CUST[ckey]),
              currency=ccy, shipment_form=sf, unit_qty=str(n))
    if iex is not None:
        kw["is_export"] = iex
    if items:
        kw.update({"unit_price": "", "order_amount": "0", "it_name[]": [x[0] for x in items], "it_spec[]": [x[0] for x in items],
                   "it_qty[]": ["1"] * len(items), "it_price[]": [x[1] for x in items]})
    elif n >= 2:
        kw.update({"unit_price": "", "order_amount": "0", "multi_unit": "1", "unit_amount[]": ["2000"] * n})
    else:
        kw.update({"unit_price": "2000", "order_amount": "2000", "unit_amount[]": ["2000"]})
    before = len(orders_of(p["id"]))
    st, loc = post(**kw)
    os_ = orders_of(p["id"])
    new = os_[before:]
    ok = st == 303 and "error=" not in loc and len(new) == 1
    return ok, (new[0] if new else None), (items_of(new[0]["id"]) if new else []), (st, loc)


print("=" * 78)
print("§1 서버")
print("=" * 78)
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.get("/api/customers/options")
opts = {o["id"]: o for o in (r.json().get("customers") or [])}
check("1 /api/customers/options 에 foreign — 해외(Vietnam)=True", opts.get(CUST["VINA"], {}).get("foreign") is True, opts.get(CUST["VINA"]))
check("   빈칸=False · 'None' 글자=False(국내)", opts.get(CUST["DOM"], {}).get("foreign") is False
      and opts.get(CUST["NONE"], {}).get("foreign") is False, (opts.get(CUST["DOM"]), opts.get(CUST["NONE"])))
check("   예전 칸(id·name·alias·sub_biz_no) 그대로", all(k in opts.get(CUST["VINA"], {}) for k in ("id", "name", "alias", "sub_biz_no")))

P1 = new_project("z1186-P1", "VINA", "1", "KRW")     # 011T2607 과 같은 꼴: 해외 고객 · 수출(통화는 시험에 무관 — USD 는 환율 칸이 따로 필요)
P2 = new_project("z1186-P2", "SAM", "1", "KRW")      # 나라 빈칸인 수출 고객(삼성전자 같은 경우)
P3 = new_project("z1186-P3", "ASAN", "0", "KRW")     # 국내 프로젝트(드림텍(아산) 같은 경우)
check("   신규 등록은 그대로 — 프로젝트 거래구분 = 고른 값(P1 수출 · P3 내수)",
      bool(P1) and bool(P3) and int(P1.get("is_export") or 0) == 1 and int(P3.get("is_export") or 0) == 0,
      (P1 and P1.get("is_export"), P3 and P3.get("is_export")))

ok, o, its, raw = followup(P1, "DOM", iex="0")
check("2 수출 프로젝트에 국내 발주처 추가 발주(이새롬 프로 그대로) → 등록됨", ok, raw)
check("   발주처 = 국내 고객 · 원화 · PO 개조", ok and o["customer_id"] == CUST["DOM"] and o.get("currency") == "KRW"
      and (o.get("po_type") or "") == "개조", o and (o["customer_id"], o.get("currency"), o.get("po_type")))
check("   🔴 호기 거래구분 = 내수(0) 로 저장 — 예전엔 비어 프로젝트 '수출'을 물려받았다",
      len(its) == 1 and its[0].get("is_export") == 0, [i.get("is_export") for i in its])
ok, o, its, raw = followup(P1, "VINA", iex="1")
check("3 같은 해외 고객 추가 발주 · 수출 → 호기 1", ok and len(its) == 1 and its[0].get("is_export") == 1,
      (raw, [i.get("is_export") for i in its]))
ok, o, its, raw = followup(P1, "DOM", iex="0", n=2)
check("4 2대 추가 발주 · 내수 → 두 호기 모두 0", ok and len(its) == 2 and all(i.get("is_export") == 0 for i in its),
      (raw, [i.get("is_export") for i in its]))
ok, o, its, raw = followup(P1, "DOM", iex="0", sf="SEMI", items=[("TOP PINBLOCK", "500"), ("SOCKET", "700")])
check("5 제품(항목 2줄) 추가 발주 · 내수 → 두 줄 모두 0", ok and len(its) == 2 and all(i.get("is_export") == 0 for i in its),
      (raw, [(i.get("unit_label"), i.get("is_export")) for i in its]))
ok, o, its, raw = followup(P3, "VINA", iex="1", po="추가")
check("6 국내 프로젝트에 해외 발주처 추가 발주 · 수출 → 호기 1(반대 방향)", ok and len(its) == 1 and its[0].get("is_export") == 1,
      (raw, [i.get("is_export") for i in its]))
ok, o, its, raw = followup(P1, "DOM", iex=None)
check("7 거래구분을 안 보낸 추가 발주 → 예전 그대로(비움 = 프로젝트 값 상속)", ok and len(its) == 1 and its[0].get("is_export") is None,
      (raw, [i.get("is_export") for i in its]))
ok, o, its, raw = followup(P1, "DOM", iex="x")
check("   이상한 값('x') → 비움(저장 안 함)", ok and len(its) == 1 and its[0].get("is_export") is None,
      (raw, [i.get("is_export") for i in its]))

nb = len(orders_of(P1["id"]))
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.post("/projects/%d/add-followup-order" % P1["id"],
                data={"order_date": "2026-10-14", "due_date": "2026-10-28", "total_amount": "3000", "qty": "1",
                      "po_number": "", "so_type": "EQUIPMENT", "currency": "USD", "ship_to": ""})
os_ = orders_of(P1["id"])
its = items_of(os_[-1]["id"]) if len(os_) > nb else []
check("8 상세 「＋ 추가 발주」 창 → 예전 그대로(발주처·거래구분 칸 없음 = 프로젝트 상속)",
      r.status_code == 200 and len(os_) == nb + 1 and os_[-1]["customer_id"] == CUST["VINA"]
      and len(its) == 1 and its[0].get("is_export") is None, (r.status_code, len(os_) - nb, [i.get("is_export") for i in its]))
with D.db_session() as c:
    r9 = PW.add_followup_order(c, P1["id"], order_date="2026-10-15", total_amount=10, qty=1)
    try:
        r10 = PW.add_followup_order(c, P1["id"], order_date="2026-10-15", total_amount=10, qty=1, is_export=0)
    except TypeError as _te:   # 고치기 전 코드엔 매개변수가 없다 — 시험은 멈추지 않고 실패로 적는다
        r10 = {"ok": False, "message": str(_te)}
i9 = items_of(r9.get("order_id")) if r9.get("ok") else []
i10 = items_of(r10.get("order_id")) if r10.get("ok") else []
check("9 add_followup_order(is_export 안 줌) → 비움 · (is_export=0) → 0",
      len(i9) == 1 and i9[0].get("is_export") is None and len(i10) == 1 and i10[0].get("is_export") == 0,
      ([i.get("is_export") for i in i9], [i.get("is_export") for i in i10]))

print()
print("=" * 78)
print("§2 실제 화면 — Chromium · 시험용 서버(임시 DB)")
print("=" * 78)

DRIVER = r'''
import json, sys
from playwright.sync_api import sync_playwright
BASEURL, M1, M2, M3, PID2 = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
out = {"page_errors": [], "cases": {}}
CP = "input[data-cust-picker][data-cust-name=customer_name]"

def open_new(pg):
    pg.goto(BASEURL + "/projects/quick?biz_div=T")
    try:
        pg.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass

def st(pg):
    return pg.evaluate("""()=>{ var s=document.getElementById('qIsExport'), h=document.getElementById('qIexHint'),
        c=document.querySelector('#quickForm input[name=customer_id]');
        return {iex: s ? s.value : null, cid: c ? c.value : null, hint: h ? (h.style.display !== 'none') : null}; }""")

def pick_cust(pg, text):
    for _t in range(3):
        pg.fill(CP, "")
        pg.type(CP, text, delay=30)
        try:
            pg.wait_for_selector(".knkcust-it", timeout=6000)
            break
        except Exception:
            pg.wait_for_timeout(700)
    pg.dispatch_event(".knkcust-it >> nth=0", "mousedown")
    pg.wait_for_timeout(700)

def pick_mgmt(pg, code):
    for _t in range(3):
        pg.fill("#qMgmtInput", "")
        pg.type("#qMgmtInput", code, delay=30)
        pg.wait_for_timeout(600)
        hit = pg.evaluate("""(code)=>{ var ds=[].slice.call(document.querySelectorAll('#qMgmtList > div'));
            var d=ds.filter(function(x){ var b=x.querySelector('b'); return b && b.textContent.trim()===code; })[0];
            if(!d) return false; d.dispatchEvent(new MouseEvent('mousedown', {bubbles:true, cancelable:true})); return true; }""", code)
        if hit:
            break
    pg.wait_for_timeout(900)   # 고객사 채움(입력 → 50ms 뒤 blur → 180ms 뒤 고르기) → 거래구분 채움(목록 받기)
    return hit

def fill_rest(pg, name):
    pg.evaluate("""(n)=>{ var s=document.getElementById('qNameSel'), i=document.getElementById('qNameInp');
                         if(s && s.offsetParent!==null){ s.value='__free__'; if(typeof qNamePick==='function') qNamePick('__free__'); }
                         if(i){ i.style.display=''; i.value=n; } }""", name)
    pg.fill("input[name=model]", "SM-S947 SIDE KEY")
    pg.fill("input[name=equip_name]", "기능검사기(UK4S)")
    pg.evaluate("""()=>{ var c=document.getElementById('qProdNotify'); if(c && c.checked) c.click(); }""")
    for sel, v in (("#qOrderDate", "2026-10-13"), ("#qDueDate", "2026-10-27")):
        if pg.query_selector(sel):
            pg.fill(sel, v)
    if pg.query_selector("#qUnitPrice"):
        pg.fill("#qUnitPrice", "2838000")

def submit(pg):
    posts = []
    pg.on("request", lambda rq: posts.append(rq.url) if (rq.method == "POST" and "/projects/new" in rq.url) else None)
    pg.click("button.qf-save")
    pg.wait_for_timeout(1500)
    try:
        pg.wait_for_load_state("domcontentloaded", timeout=8000)
    except Exception:
        pass
    try:
        err = pg.evaluate("()=>{ var e=document.getElementById('qfErr'); return e ? (e.classList.contains('show') ? (e.textContent||'').trim() : '') : null; }")
    except Exception:
        err = None
    return {"posts": len(posts), "err": err, "url": pg.url}

def a_mgmt_first(pg):
    # 이새롬 프로가 겪은 순서: PO 개조 → 관리번호(수출 프로젝트) 먼저 → 고객사가 프로젝트 고객으로 채워짐 → 국내로 바꿈
    open_new(pg)
    pg.select_option("#qPoType", "개조")
    pg.wait_for_timeout(300)
    hit = pick_mgmt(pg, M1)
    s1 = st(pg)
    pick_cust(pg, "가상국내(동탄)")
    s2 = st(pg)
    fill_rest(pg, "z1186-A")
    r = submit(pg)
    return {"hit": hit, "after_mgmt": s1, "after_cust": s2, "submit": r}

def b_cust_first(pg):
    # 발주처(국내)를 먼저 고르고 → PO 개조 → 관리번호(수출 프로젝트) → 내수 그대로
    open_new(pg)
    pick_cust(pg, "가상국내(동탄)")
    s0 = st(pg)
    pg.select_option("#qPoType", "개조")
    pg.wait_for_timeout(500)
    s1 = st(pg)
    hit = pick_mgmt(pg, M1)
    s2 = st(pg)
    fill_rest(pg, "z1186-B")
    r = submit(pg)
    return {"hit": hit, "after_cust_new": s0, "after_po": s1, "after_mgmt": s2, "submit": r}

def c_same_blank_country(pg):
    # 나라 빈칸인 수출 고객(삼성전자 같은 경우) 프로젝트 · 같은 고객 → 프로젝트 값(수출)
    open_new(pg)
    pg.select_option("#qPoType", "개조")
    pg.wait_for_timeout(300)
    hit = pick_mgmt(pg, M2)
    s1 = st(pg)
    pick_cust(pg, "가상국내(동탄)")
    s2 = st(pg)
    pick_cust(pg, "가상삼성")
    s3 = st(pg)
    return {"hit": hit, "same": s1, "other_dom": s2, "back_same": s3}

def d_reverse(pg):
    # 국내 프로젝트(아산 같은 경우)에 해외 발주처 → 수출
    open_new(pg)
    pg.select_option("#qPoType", "추가")
    pg.wait_for_timeout(300)
    hit = pick_mgmt(pg, M3)
    s1 = st(pg)
    pick_cust(pg, "가상 VINA")
    s2 = st(pg)
    return {"hit": hit, "same": s1, "vina": s2}

def e_touched(pg):
    # 사람이 거래구분을 먼저 바꾸면 그 뒤로는 덮지 않는다
    open_new(pg)
    pg.select_option("#qPoType", "개조")
    pg.wait_for_timeout(300)
    hit = pick_mgmt(pg, M1)
    s1 = st(pg)
    pg.select_option("#qIsExport", "0")
    pg.wait_for_timeout(200)
    s2 = st(pg)
    pick_cust(pg, "가상 VINA")
    s3 = st(pg)
    return {"hit": hit, "auto": s1, "by_hand": s2, "after_cust": s3}

def f_new_untouched(pg):
    # 신규 등록(PO 신규)은 건드리지 않는다 — 해외 고객을 골라도 거래구분은 사람이 고른 그대로(기본 내수)
    open_new(pg)
    s0 = st(pg)
    pick_cust(pg, "가상 VINA")
    s1 = st(pg)
    return {"before": s0, "after": s1}

def g_edit(pg):
    # 정보 수정 화면(수출 · 나라 빈칸 고객) — 저장된 거래구분을 건드리지 않는다
    pg.goto(BASEURL + "/projects/" + PID2 + "/quick-edit")
    try:
        pg.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    pg.wait_for_timeout(800)
    return st(pg)

with sync_playwright() as p:
    br = p.chromium.launch()
    def run(key, fn):
        ctx = br.new_context(viewport={"width": 1400, "height": 1000})
        ctx.add_init_script("try{sessionStorage.setItem('knkAutoReloadTs', String(Date.now()));}catch(e){}")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: out["page_errors"].append(key + ": " + str(e)[:200]))
        try:
            out["cases"][key] = fn(pg)
        except Exception as e:
            out["cases"][key] = {"exc": str(e)[:400]}
        finally:
            ctx.close()
    for k, fn in (("A", a_mgmt_first), ("B", b_cust_first), ("C", c_same_blank_country), ("D", d_reverse),
                  ("E", e_touched), ("F", f_new_untouched), ("G", g_edit)):
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

n1 = len(orders_of(P1["id"])) if P1 else 0
cases, page_errors = {}, []
if PWPY and P1 and P2 and P3:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    rr = subprocess.run([PWPY, DRV, BASEURL, P1["mgmt_code"], P2["mgmt_code"], P3["mgmt_code"], str(P2["id"])],
                        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900, env=env)
    line = [x for x in (rr.stdout or "").splitlines() if x.startswith("@@RESULT@@")]
    if line:
        res = json.loads(line[-1][len("@@RESULT@@"):])
        cases, page_errors = res["cases"], res["page_errors"]
    else:
        print("   (브라우저 쪽 출력)", (rr.stdout or "")[-800:], (rr.stderr or "")[-1500:])
        page_errors = ["(브라우저 결과 없음)"]


def case(k):
    return cases.get(k) or {}


S_DOM, S_VINA, S_SAM = str(CUST["DOM"]), str(CUST["VINA"]), str(CUST["SAM"])
A = case("A")
check("A 관리번호 먼저 → 고객사가 그 프로젝트 고객으로 채워지고 거래구분 = 수출(같은 고객 → 프로젝트 값) · 안내 보임",
      A.get("hit") and (A.get("after_mgmt") or {}).get("cid") == S_VINA and (A.get("after_mgmt") or {}).get("iex") == "1"
      and (A.get("after_mgmt") or {}).get("hint") is True, A)
check("   발주처를 국내로 바꾸면 거래구분 = 내수", (A.get("after_cust") or {}).get("cid") == S_DOM
      and (A.get("after_cust") or {}).get("iex") == "0", A.get("after_cust"))
os_ = orders_of(P1["id"])
newA = [o for o in os_[n1:] if o["customer_id"] == CUST["DOM"]]
itA = items_of(newA[0]["id"]) if newA else []
check("   「＋ 등록」 → 수주 1건(발주처 국내 · PO 개조) · 호기 거래구분 내수(0) 저장",
      (A.get("submit") or {}).get("posts") == 1 and len(newA) >= 1 and (newA[0].get("po_type") or "") == "개조"
      and len(itA) == 1 and itA[0].get("is_export") == 0,
      (A.get("submit"), [(o["order_no"], o["customer_id"]) for o in os_[n1:]], [i.get("is_export") for i in itA]))
B = case("B")
check("B 발주처(국내) 먼저 → PO 신규일 땐 안 건드림(내수 기본) · 개조로 바꿔도 내수",
      (B.get("after_cust_new") or {}).get("iex") == "0" and (B.get("after_cust_new") or {}).get("hint") is False
      and (B.get("after_po") or {}).get("iex") == "0", B)
check("   관리번호(수출 프로젝트)를 골라도 발주처는 국내 그대로 · 거래구분 내수",
      B.get("hit") and (B.get("after_mgmt") or {}).get("cid") == S_DOM and (B.get("after_mgmt") or {}).get("iex") == "0",
      B.get("after_mgmt"))
os2 = orders_of(P1["id"])
newB = [o for o in os2[n1:] if o["customer_id"] == CUST["DOM"]]
itB = items_of(newB[-1]["id"]) if len(newB) >= 2 else []
check("   「＋ 등록」 → 두 번째 국내 수주 · 호기 내수(0)", (B.get("submit") or {}).get("posts") == 1 and len(newB) == 2
      and len(itB) == 1 and itB[0].get("is_export") == 0, (B.get("submit"), len(newB), [i.get("is_export") for i in itB]))
C = case("C")
check("C 나라 빈칸 수출 고객(삼성전자 같은 경우) 프로젝트 · 같은 고객 → 수출(프로젝트 값)",
      C.get("hit") and (C.get("same") or {}).get("cid") == S_SAM and (C.get("same") or {}).get("iex") == "1", C.get("same"))
check("   다른 국내 고객 → 내수 · 다시 같은 고객 → 수출", (C.get("other_dom") or {}).get("iex") == "0"
      and (C.get("back_same") or {}).get("iex") == "1", (C.get("other_dom"), C.get("back_same")))
D_ = case("D")
check("D 국내 프로젝트(PO 추가) · 같은 고객 → 내수 · 해외 발주처로 바꾸면 수출(반대 방향)",
      D_.get("hit") and (D_.get("same") or {}).get("iex") == "0" and (D_.get("vina") or {}).get("cid") == S_VINA
      and (D_.get("vina") or {}).get("iex") == "1", D_)
E = case("E")
check("E 사람이 거래구분을 바꾸면(수출→내수) 그 뒤 해외 발주처를 골라도 덮지 않음 · 안내 숨김",
      (E.get("auto") or {}).get("iex") == "1" and (E.get("by_hand") or {}).get("iex") == "0"
      and (E.get("by_hand") or {}).get("hint") is False and (E.get("after_cust") or {}).get("iex") == "0", E)
F = case("F")
check("F 신규 등록(PO 신규) · 해외 고객 → 거래구분 그대로(내수 기본) · 안내 없음",
      (F.get("before") or {}).get("iex") == "0" and (F.get("after") or {}).get("cid") == S_VINA
      and (F.get("after") or {}).get("iex") == "0" and (F.get("after") or {}).get("hint") is False, F)
G = case("G")
check("G 정보 수정 화면(수출 · 나라 빈칸 고객) → 저장된 수출 그대로", G.get("iex") == "1", G)
check("화면 스크립트 오류 0", not page_errors, page_errors)

print()
print("=" * 78)
print("§3 바뀐 곳 원문")
print("=" * 78)
qf = io.open(os.path.join(ROOT, "app", "templates", "project_quick_form.html"), encoding="utf-8").read()
mn = io.open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
pw = io.open(os.path.join(ROOT, "app", "project_workflow.py"), encoding="utf-8").read()
check("등록 화면: 거래구분 칸 id · 안내 · 채우기 함수 · 정보 수정 화면 제외(QF_ED)",
      'name="is_export" id="qIsExport"' in qf and 'id="qIexHint"' in qf and "function qIexApply()" in qf
      and "if(QF_ED || _qIexTouched || !qIsFollowup()) return;" in qf)
check("등록 화면: z1186 줄에 Jinja 기호 없음", not any(("{%" in l or "{{" in l or "{#" in l) for l in qf.splitlines() if "z1186" in l))
check("서버: 해외 판정 한 곳 · 고객 목록 foreign · 추가 발주가 거래구분을 넘김",
      "def _cust_is_foreign(country)" in mn and '"foreign": _cust_is_foreign(r["country"])' in mn
      and "is_export=_fu_iex," in mn)
check("add_followup_order: is_export 매개변수 · 호기 줄에 적기",
      "is_export: int | None = None" in pw   # z1190: 뒤에 end_customer 가 붙어 머리줄 끝이 바뀜 — 이름만 본다
      and 'UPDATE order_items SET is_export=? WHERE order_id=?' in pw)

print()
print("결과: %d개 중 실패 %d" % (OK + FAIL, FAIL))
sys.exit(1 if FAIL else 0)
