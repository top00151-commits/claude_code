# -*- coding: utf-8 -*-
"""z1173 시험 — 수주 상세 비고 칸에 로그인 ID(사번)가 저절로 들어가는 것 막기 + 등록 때 빈 호기 비고는 NULL
   (이새롬 프로 신고 「비고에 적었던 내용은 사라지고 사번으로 표기」 · 대표 「A. 세 겹 막기 + 4건 정리」·「등록 메모 같이 고친다」 2026-10-13)

  §1 서버(임시 DB · TestClient): 등록 호기 비고 NULL · 거부 5경로(호기 라인 수정 · 호기 추가 · 일정표 칸 · 수주 머리 · 추가 발주)
     — 자기 로그인 ID·사번과 같은 값만 거부(다른 사람 사번·긴 글은 통과) · 안내문 글자
  §2 실제 화면(Chromium · 시험용 서버 · 임시 DB): 열자마자 글자 칸이 읽기전용인지 · 누르면 풀려 입력·저장되는지 ·
     되돌리기 함수(knkDropAutofill)의 판정 · 스크립트 오류 0
     · 브라우저는 Playwright 가 있는 파이썬이 따로 돌린다(이 PC 는 3.12) — 서버·DB 확인은 이 파이썬이 한다
     · 한계: 자동 시험용 브라우저에는 저장된 로그인 정보가 없어 **진짜 자동 채움은 못 만든다** → 막는 논리만 시험한다
  §3 바뀐 곳 원문(읽기전용 표시 · 도우미 · 서버 판정 5곳 · 등록 NULL · 템플릿 JS 주석에 Jinja 기호 없음)
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1173-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1173_")
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
    for nm, eno, lid in (("가상306", "306", "306"), ("가상777", "T777", "T777")):
        # z1191g(2026-10-21 대표): 관리자는 역할만으로 매출·자재가 열리지 않는다 → 이 시험의 가상 관리자는 센터 4칸을 켠 관리자로
        conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
                     "VALUES (?, 'admin', ?, ?, 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)", (nm, eno, lid))
    U306 = dict(conn.execute("SELECT * FROM users WHERE login_id='306'").fetchone())
    U777 = dict(conn.execute("SELECT * FROM users WHERE login_id='T777'").fetchone())
    conn.execute("INSERT INTO customers (name) VALUES ('가상고객')")

import app.main as M                                        # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

CUR = {"u": U306}
M.get_user = lambda request: CUR["u"]
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
        "due_date": "2026-10-15", "currency": "KRW", "equip_name": "INDEX검사기", "model": "ON4 IF CTC PBA",
        "unit_qty": "1"}


def post(path, **kw):
    f = dict(BASE) if path == "/projects/new" else {}
    f.update(kw)
    with contextlib.redirect_stdout(io.StringIO()):
        r = cl.post(path, data=f)
    return r


def jpost(path, data=None, js=None):
    with contextlib.redirect_stdout(io.StringIO()):
        r = cl.post(path, data=data) if js is None else cl.post(path, json=js)
    try:
        j = r.json()
    except Exception:
        j = {}
    return r.status_code, j


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


def note_of(iid):
    with D.db_session() as c:
        r = c.execute("SELECT line_note FROM order_items WHERE id=?", (iid,)).fetchone()
        return r[0] if r else "(행 없음)"


def edit(iid, **kw):
    body = {"base_ts": "", "label": "1호기", "amount": "1000", "note": ""}
    body.update(kw)
    return jpost("/sales/orders/items/%d/edit" % iid, data=body)


print("=" * 78)
print("§1 서버 — 등록 호기 비고 NULL · 거부 5경로")
print("=" * 78)
# 등록 화면은 1대일 때도 숨은 칸 unit_amount[](#qUnitAmount)으로 호기 1줄을 보낸다(운영 T-260929-3 의 1호기 줄이 이 경로)
r = post("/projects/new", name="z1173-1", unit_price="1000", order_amount="1000", **{"unit_amount[]": ["1000"]})
p1 = proj("z1173-1")
check("1 등록(1대) 됨", r.status_code == 303 and "error=" not in r.headers.get("location", "") and p1 is not None,
      (r.status_code, r.headers.get("location", "")))
o1 = orders_of(p1["id"])[0] if p1 else None
it1 = items_of(o1["id"]) if o1 else []
i1 = it1[0]["id"] if it1 else None
check("   호기 1줄 · 비고가 NULL(빈 글자 '' 아님)", len(it1) == 1 and it1[0]["line_note"] is None,
      [i.get("line_note") for i in it1])

r = post("/projects/new", name="z1173-2", unit_qty="2", multi_unit="1", unit_price="", order_amount="0",
         **{"unit_amount[]": ["1000", "2000"]})
p2 = proj("z1173-2")
it2 = items_of(orders_of(p2["id"])[0]["id"]) if p2 else []
check("2 등록(2대·호기별) — 두 줄 다 비고 NULL", len(it2) == 2 and all(i["line_note"] is None for i in it2),
      [i.get("line_note") for i in it2])
check("   z983 3상태: 전부 NULL → None(등록 메모 폴백) · '' → ''(폴백 안 함)",
      M._join_notes981([None, None]) is None and M._join_notes981([""]) == "" and M._join_notes981(["a", None]) == "a")

st, j = edit(i1, note="306")
check("3 호기 라인 수정 · 비고='306'(자기 로그인 ID) → 400 + 안내문", st == 400 and j.get("ok") is False
      and "비고" in (j.get("message") or "") and "로그인 ID" in (j.get("message") or ""), (st, j))
check("   DB 비고 그대로(NULL)", note_of(i1) is None, note_of(i1))
check("   안내문: 왜 막혔고 무엇을 하면 되는지", "브라우저가 저절로 채운 값" in (j.get("message") or "")
      and "다시 적은 뒤 저장" in (j.get("message") or ""), j.get("message"))
st, j = edit(i1, note=" 306 ")
check("4 비고=' 306 '(공백 포함) → 400", st == 400, (st, j))
st, j = edit(i1, note="3060")
check("5 비고='3060'(다른 글) → 저장됨", st == 200 and j.get("ok") is True and note_of(i1) == "3060", (st, j, note_of(i1)))
st, j = edit(i1, note="")
check("6 비고 비움 → 저장(NULL)", st == 200 and j.get("ok") is True and note_of(i1) is None, (st, j, note_of(i1)))
st, j = edit(i1, ship_to="306")
check("7 납품처='306' → 400 + 「납품처」", st == 400 and "납품처" in (j.get("message") or ""), (st, j))
st, j = edit(i1, label="306")
check("   호기='306' → 400 + 「호기」", st == 400 and "호기" in (j.get("message") or ""), (st, j))
st, j = edit(i1, note="67")
check("8 비고='67'(다른 사람 사번) → 막지 않음(저장)", st == 200 and note_of(i1) == "67", (st, j, note_of(i1)))
edit(i1, note="")

n0 = len(items_of(o1["id"]))
st, j = jpost("/sales/orders/%d/add-unit" % o1["id"], data={"label": "2호기", "amount": "1000", "note": "306", "qty": "1"})
check("9 호기 추가 · 비고='306' → 400 · 줄 수 그대로", st == 400 and len(items_of(o1["id"])) == n0, (st, j))
st, j = jpost("/sales/orders/%d/add-unit" % o1["id"], data={"label": "2호기", "amount": "1000", "note": "memo", "qty": "1"})
check("   호기 추가 · 비고='memo' → 저장(+1)", st == 200 and j.get("ok") is True and len(items_of(o1["id"])) == n0 + 1
      and items_of(o1["id"])[-1]["line_note"] == "memo", (st, j, len(items_of(o1["id"]))))

st, j = jpost("/sales/schedule/unit-field", js={"iid": i1, "field": "note", "value": "306"})
check("10 일정표 칸 · 비고='306' → 400 + error 안내문", st == 400 and "로그인 ID" in (j.get("error") or ""), (st, j))
st, j = jpost("/sales/schedule/unit-field", js={"iid": i1, "field": "note", "value": "x"})
check("   일정표 칸 · 비고='x' → 저장", st == 200 and j.get("ok") is True and note_of(i1) == "x", (st, j, note_of(i1)))
st, j = jpost("/sales/schedule/unit-field", js={"iid": i1, "field": "ship_to", "value": "306"})
check("   일정표 칸 · 납품처='306' → 400", st == 400, (st, j))
jpost("/sales/schedule/unit-field", js={"iid": i1, "field": "note", "value": ""})

st, j = jpost("/sales/orders/%d/quick-edit" % o1["id"], data={"ship_to": "306"})
check("11 수주 머리 · 납품처='306' → 400 + 「납품처」", st == 400 and "납품처" in (j.get("message") or ""), (st, j))
st, j = jpost("/sales/orders/%d/quick-edit" % o1["id"], data={"ship_to": "본사"})
with D.db_session() as c:
    _sh = c.execute("SELECT ship_to FROM orders WHERE id=?", (o1["id"],)).fetchone()[0]
check("   수주 머리 · 납품처='본사' → 저장", st == 200 and j.get("ok") is True and _sh == "본사", (st, j, _sh))

FUP = {"order_date": "2026-10-09", "due_date": "2026-10-20", "total_amount": "1000", "qty": "1", "po_number": "",
       "so_type": "EQUIPMENT", "currency": "KRW"}
nb = len(orders_of(p1["id"]))
st, j = jpost("/projects/%d/add-followup-order" % p1["id"], data=dict(FUP, ship_to="306"))
check("12 추가 발주 · 납품처='306' → 400 · 수주 수 그대로", st == 400 and len(orders_of(p1["id"])) == nb, (st, j))
st, j = jpost("/projects/%d/add-followup-order" % p1["id"], data=dict(FUP, note="306"))
check("   추가 발주 · 비고='306' → 400", st == 400 and len(orders_of(p1["id"])) == nb, (st, j))
st, j = jpost("/projects/%d/add-followup-order" % p1["id"], data=dict(FUP, ship_to="평택"))
os_after = orders_of(p1["id"])
check("   추가 발주 · 납품처='평택' → 수주 +1 · 그 호기 비고 NULL", st == 200 and j.get("ok") is True and len(os_after) == nb + 1
      and all(i["line_note"] is None for i in items_of(os_after[-1]["id"])),
      (st, j, [i.get("line_note") for i in items_of(os_after[-1]["id"])] if len(os_after) > nb else None))

CUR["u"] = U777
st, j = edit(i1, note="306")
check("13 다른 사람(T777)이 비고='306' → 막지 않음(자기 ID 가 아님)", st == 200 and note_of(i1) == "306", (st, j, note_of(i1)))
st, j = edit(i1, note="t777")
check("   T777 이 비고='t777'(대소문자 다름) → 400", st == 400, (st, j))
edit(i1, note="")
CUR["u"] = U306
check("   정리: 비고 NULL 로 되돌림(화면 시험 전)", note_of(i1) is None, note_of(i1))

print()
print("=" * 78)
print("§2 실제 화면 — Chromium · 시험용 서버(임시 DB)")
print("=" * 78)

DRIVER = r'''
import json, sys
from playwright.sync_api import sync_playwright
BASEURL, PID1, IID1 = sys.argv[1], sys.argv[2], sys.argv[3]
ROW = 'tr[data-uid="' + IID1 + '"]'          # 1호기 줄은 id 로 집는다(화면의 줄 순서는 id 순이 아니다)
out = {"page_errors": [], "cases": {}}

def open_detail(pg):
    pg.goto(BASEURL + "/project/" + PID1)
    try:
        pg.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass

STATE = """()=>{
  var txt = Array.prototype.slice.call(document.querySelectorAll('.so-card input[type="text"]'));
  var note = Array.prototype.slice.call(document.querySelectorAll('.note-inp'));
  return {
    text_all: txt.length,
    text_ro: txt.filter(function(i){ return i.readOnly; }).length,
    text_mark: txt.filter(function(i){ return i.getAttribute('data-knk-ro')==='1'; }).length,
    not_ro: txt.filter(function(i){ return !i.readOnly; }).map(function(i){ return (i.className||'') + '|' + (i.name||'') + '|' + (i.id||''); }),
    note_n: note.length,
    note_ro: note.filter(function(i){ return i.readOnly; }).length,
    add_note_ro: (document.querySelector('.so-card input[name="note"]')||{}).readOnly,
    fup_ro: (document.getElementById('fup_ship_to')||{}).readOnly,
    helpers: (typeof window.knkDropAutofill==='function') && (typeof window.knkAutofilled==='function') && (typeof window.knkAutofillNotice==='function'),
    toggle: !!document.querySelector('.so-card .toggle-edit'),
    saveall: !!document.querySelector('.so-card .save-all-btn')
  }; }"""

def a_load(pg):
    open_detail(pg)
    return pg.evaluate(STATE)

def b_click_type_save(pg):
    dialogs = []
    pg.on("dialog", lambda d: (dialogs.append(d.message), d.accept()))
    open_detail(pg)
    pg.click(ROW + " >> xpath=ancestor::div[contains(@class,'so-card')] >> .toggle-edit")
    pg.wait_for_timeout(300)
    pg.click(ROW + " .note-inp")
    after_click = pg.evaluate("(sel)=>{ var i=document.querySelector(sel + ' .note-inp'); return {ro:i.readOnly, mark:i.getAttribute('data-knk-ro'), active: document.activeElement===i, before:i.value}; }", ROW)
    pg.keyboard.type("비고 abc")
    val = pg.evaluate("(sel)=>document.querySelector(sel + ' .note-inp').value", ROW)
    pg.click(ROW + " >> xpath=ancestor::div[contains(@class,'so-card')] >> .save-all-btn")
    pg.wait_for_timeout(2500)
    return {"after_click": after_click, "value": val, "dialogs": dialogs}

def c_focus_type(pg):
    open_detail(pg)
    pg.click(ROW + " >> xpath=ancestor::div[contains(@class,'so-card')] >> .toggle-edit")
    pg.wait_for_timeout(300)
    before = pg.evaluate("(sel)=>document.querySelector(sel + ' .note-inp').value", ROW)
    pg.focus(ROW + " .note-inp")
    pg.keyboard.type("X")
    r = pg.evaluate("(sel)=>{ var i=document.querySelector(sel + ' .note-inp'); return {ro:i.readOnly, value:i.value}; }", ROW)
    r["before"] = before
    return r

def d_logic(pg):
    open_detail(pg)
    return pg.evaluate("""()=>{
      var mk = function(v, o, af){ return {type:'text', value:v, dataset:{orig:o}, matches:function(s){ return af && s.indexOf('autofill')>=0; }}; };
      var a = mk('306', '', true), b = mk('306', '', false), c = mk('306', '306', true), d = mk('메모', '1호기 메모', true), e = mk('306', '', true); e.type = 'date';
      var n = knkDropAutofill([a, b, c, d, e]);
      return {n:n, a:a.value, b:b.value, c:c.value, d:d.value, e:e.value, real: knkAutofilled(document.querySelector('.note-inp')), zero_notice: (function(){ try{ knkAutofillNotice(0); return true; }catch(err){ return false; } })()}; }""")

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
    for k, fn in (("A", a_load), ("B", b_click_type_save), ("C", c_focus_type), ("D", d_logic)):
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

cases, page_errors = {}, []
if PWPY and p1:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    rr = subprocess.run([PWPY, DRV, BASEURL, str(p1["id"]), str(i1)], capture_output=True, text=True, encoding="utf-8",
                        errors="replace", timeout=600, env=env)
    line = [x for x in (rr.stdout or "").splitlines() if x.startswith("@@RESULT@@")]
    if line:
        res = json.loads(line[-1][len("@@RESULT@@"):])
        cases, page_errors = res["cases"], res["page_errors"]
    else:
        print("   (브라우저 쪽 출력)", (rr.stdout or "")[-800:], (rr.stderr or "")[-1500:])
        page_errors = ["(브라우저 결과 없음)"]


def case(k):
    return cases.get(k) or {}


A = case("A")
check("A 상세 화면: 글자 입력칸이 모두 읽기전용(열자마자)", A.get("text_all", 0) > 0 and A.get("text_ro") == A.get("text_all")
      and A.get("text_mark") == A.get("text_all"), A)
check("   비고 칸 · 호기 추가 폼 비고 · 추가 발주 납품처도 읽기전용", A.get("note_n", 0) >= 1 and A.get("note_ro") == A.get("note_n")
      and A.get("add_note_ro") is True and A.get("fup_ro") is True, A)
check("   되돌리기 도우미 3개 있음 · 수정 단추 · 모두 저장 단추", A.get("helpers") is True and A.get("toggle") and A.get("saveall"), A)
B = case("B")
check("B 1호기 비고 칸을 누르면 읽기전용이 풀리고 입력됨", (B.get("after_click") or {}).get("ro") is False
      and (B.get("after_click") or {}).get("mark") is None and (B.get("after_click") or {}).get("before") == ""
      and B.get("value") == "비고 abc", B)
check("   「모두 저장」 → DB 에 '비고 abc' 저장 · 알림창 없음", note_of(i1) == "비고 abc" and not B.get("dialogs"), (note_of(i1), B.get("dialogs")))
C = case("C")
check("C 키보드로 들어가도(focus) 풀려서 입력됨", C.get("ro") is False and "X" in str(C.get("value") or "")
      and len(str(C.get("value") or "")) == len(str(C.get("before") or "")) + 1, C)
Dd = case("D")
check("D knkDropAutofill: 브라우저가 채운 칸만 원래 값으로(2칸) · 사람이 적은 칸·같은 값·날짜 칸은 그대로",
      Dd.get("n") == 2 and Dd.get("a") == "" and Dd.get("b") == "306" and Dd.get("c") == "306"
      and Dd.get("d") == "1호기 메모" and Dd.get("e") == "306", Dd)
check("   보통 입력칸은 「채워진 것」으로 보지 않음 · 0칸이면 알림 없음", Dd.get("real") is False and Dd.get("zero_notice") is True, Dd)
check("화면 스크립트 오류 0", not page_errors, page_errors)

print()
print("=" * 78)
print("§3 바뀐 곳 원문")
print("=" * 78)
tpl = io.open(os.path.join(ROOT, "app", "templates", "project_detail.html"), encoding="utf-8").read()
mn = io.open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
pw = io.open(os.path.join(ROOT, "app", "project_workflow.py"), encoding="utf-8").read()
check("템플릿: 비고 칸 마크업에 readonly + data-knk-ro", 'autocomplete="off" readonly data-knk-ro="1" data-orig=' in tpl)
check("템플릿: 읽기전용 스윕·풀기(knkRoUnlock) · 도우미 3개 정의",
      "knkRoUnlock" in tpl and "window.knkDropAutofill = function" in tpl and "window.knkAutofilled = function" in tpl
      and "window.knkAutofillNotice = function" in tpl)
check("템플릿: 되돌리기를 부르는 곳 5(호기 줄 · 수주 머리(모두 저장) · 수주 머리 저장 · 호기 추가 · 추가 발주)",
      tpl.count("knkDropAutofill(") == 5, tpl.count("knkDropAutofill("))
check("템플릿: 나중에 생기는 칸도 잠금(MutationObserver) · 풀린 칸은 다시 안 잠금(data-knk-ro-done)",
      "new MutationObserver(" in tpl and "data-knk-ro-done" in tpl and "knkRoApply(document)" in tpl)
check("템플릿: z1173 줄에 Jinja 기호 없음",
      not any(("{%" in l or "{{" in l) for l in tpl.splitlines() if "z1173" in l))
check("서버: 판정 함수 + 5경로", mn.count("_z1173_autofill_guard(") == 6 and mn.count("_z1173_autofill_msg(") == 6,
      (mn.count("_z1173_autofill_guard("), mn.count("_z1173_autofill_msg(")))
check("등록: 빈 호기 비고는 NULL", ".strip() or None   # z1173" in pw)

print()
print("결과: %d개 중 실패 %d" % (OK + FAIL, FAIL))
sys.exit(1 if FAIL else 0)
