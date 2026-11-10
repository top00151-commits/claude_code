# -*- coding: utf-8 -*-
"""z1191z15 시험 — 안지연 프로 요청 「자동화 장비 상품: 개조는 1식, 신규·추가는 N대분(1대분도 1식이 아닌 1대분)」
   대표 「개조는 모두 식으로 표현 1식, 2식, 3식」 (2026-11-10)
  상품(부품 묶음) 수량 단위 = PO유형: 개조 → N식 · 신규·추가 → 완제품 N대분.
  확인: 단위 함수 한 곳 · 작업일정표 화면 · 엑셀 저장 줄 · 상세 수주 카드 · 합계 줄 · 수정 화면 수주 표 · 수량 칸(1도 보임)
  임시 DB · TestClient · 운영 아님
"""
import contextlib
import io
import os
import re
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z15-test-only-not-a-real-key"
import app.database as D  # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z15_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
                 "VALUES ('가상관리자', 'admin', 'T915', 'T915', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(conn.execute("SELECT * FROM users WHERE employee_no='T915'").fetchone())
    conn.execute("INSERT INTO customers (name) VALUES ('가상고객')")
import app.main as M  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

M.get_user = lambda request: ADMIN
cl = TestClient(M.app, follow_redirects=False)
OK = FAIL = 0


def check(cond, msg, got=None):
    global OK, FAIL
    if cond:
        OK += 1; print("  ✅", msg)
    else:
        FAIL += 1; print("  ❌", msg, "" if got is None else ("  ← %r" % (got,)))


def q(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


BASE = {"quick": "1", "customer_name": "가상고객", "biz_div": "M", "project_type": "NEW_EQUIP", "po_type": "신규", "status": "진행중",
        "confirm_now": "1", "order_date": "2026-11-04", "due_date": "2026-11-20", "currency": "USD", "fx_rate": "1400",
        "equip_name": "가상장비", "model": "MP15", "unit_qty": "1"}
PK = {"pk_name[]": ["볼트", "너트"], "pk_model[]": ["B", "N"], "pk_qty[]": ["10", "20"], "pk_price[]": ["1", "2"]}


def post_new(**kw):
    f = dict(BASE); f.update(PK); f.update(kw)
    r = q(cl.post, "/projects/new", data=f)
    if "error=" in (r.headers.get("location") or ""):
        print("   (등록 오류)", r.headers.get("location"))
    return r.status_code


def proj(name):
    with D.db_session() as c:
        return dict(c.execute("SELECT * FROM projects WHERE name=? ORDER BY id DESC", (name,)).fetchone())


def orders_of(pid):
    with D.db_session() as c:
        return [dict(r) for r in c.execute("SELECT * FROM orders WHERE project_id=? ORDER BY id", (pid,))]


print("§1 단위 함수(한 곳)")
F = M._parts_qty_z15
check(F(1, "신규")["label"] == "완제품 1대분" and F(1, "신규")["short"] == "1대분", "신규 1 → 완제품 1대분(예전 1식)")
check(F(11, "추가")["short"] == "11대분" and F(0, "추가")["short"] == "1대분" and F(None, "")["short"] == "1대분", "추가 11 → 11대분 · 0·빈칸 → 1대분")
check(F(1, "개조")["label"] == "1식" and F(2, "개조")["short"] == "2식" and F(3, " 개조 ")["short"] == "3식", "개조 → 1식·2식·3식(2 이상도 식)")
U = M._board_qty_unit
check(U({"is_parts": True, "qty": 1, "po_type": "신규"}) == "대분" and U({"is_parts": True, "qty": 2, "po_type": "개조"}) == "식"
      and U({"kind": "consumable", "is_parts": True}) == "건" and U({"form_type": "완제품"}) == "대", "작업일정표 단위 = 같은 함수 · 다른 형태는 그대로")

print("§2 화면 — 상품 수주 3건(신규 1 · 개조 2 · 추가 3)")
post_new(name="z15-상품", shipment_form="PARTS", unit_price="", order_amount="0", parts_units="1")
P = proj("z15-상품")
post_new(name="z15-상품", po_type="개조", mgmt_code=P["mgmt_code"], shipment_form="PARTS", unit_price="", order_amount="0", parts_units="2")
post_new(name="z15-상품", po_type="추가", mgmt_code=P["mgmt_code"], shipment_form="PARTS", unit_price="", order_amount="0", parts_units="3")
O = orders_of(P["id"])
check(len(O) == 3 and [int(o.get("unit_qty") or 0) for o in O] == [1, 2, 3], "자료: 수주 3건 · 수량 1·2·3",
      [(o["order_no"], o.get("unit_qty"), o.get("po_type"), o.get("so_type")) for o in O])
SO = {o["order_no"]: o for o in O}
NEW, MOD, ADD = O[0]["order_no"], O[1]["order_no"], O[2]["order_no"]

hd = q(cl.get, "/project/%d" % P["id"]).text
labels = re.findall(r"수량 <b>([^<]+)</b>", hd)
check(sorted(labels) == sorted(["완제품 1대분", "2식", "완제품 3대분"]), "상세 수주 카드 수량: 완제품 1대분 · 2식 · 완제품 3대분", labels)
check("완제품 4대분 · 2식" in hd, "상세 합계 줄: 완제품 4대분 · 2식", re.findall(r"총 수주번호[^<]{0,80}", hd))

he = q(cl.get, "/projects/%d/edit" % P["id"]).text
rows = {m.group(1): m.group(2) for m in re.finditer(r'data-so="([A-Z]-\d{6}-\d+)"[^>]*>[^<]*</a>.*?</td><td[^>]*>[^<]*</td><td[^>]*>[^<]*</td><td[^>]*>[^<]*</td><td[^>]*>([^<]*)</td>', he, re.S)} if False else {}
tbl = he.split('class="z14-common-note"')[1].split("</table>")[0] if 'class="z14-common-note"' in he else ""
check(">1대분<" in tbl and ">2식<" in tbl and ">3대분<" in tbl and "1식" not in tbl, "수정 화면 수주 표 수량: 1대분 · 2식 · 3대분", re.findall(r">(\d+(?:대분|식))<", tbl))
m = re.search(r'name="parts_units"[^>]*value="([^"]*)"', he)
check(m is not None and m.group(1) == "1", "수정 화면 상품 수량 칸: 1 도 보인다(예전엔 비워 1식)", m and m.group(1))

hs = q(cl.get, "/sales/schedule?ym=2026-11").text
units = {}
for tr in re.findall(r"<tr[^>]*>.*?</tr>", hs, re.S):
    for so in (NEW, MOD, ADD):
        if (">%s<" % so) in tr:
            mm = re.search(r'<span class="qn">([^<]*)</span><span class="qu">([^<]*)</span>', tr)
            if mm:
                units[so] = mm.group(1) + mm.group(2)
check(units.get(NEW) == "1대분" and units.get(MOD) == "2식" and units.get(ADD) == "3대분", "작업일정표 수량: 신규 1대분 · 개조 2식 · 추가 3대분", units)
check('상품 수량 — 신규·추가 = 완제품 몇 대분 · 개조 = 몇 식' in hs and "td.dataset.unit==='식'" in hs, "작업일정표 수량 칸 안내 · 고친 뒤 알림도 단위대로")

rx = q(cl.get, "/sales/schedule/export.xlsx?ym=2026-11")
eu = {}
try:
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(rx.content), read_only=True)
    ws = wb.worksheets[0]
    hdr = None
    for row in ws.iter_rows(values_only=True):
        row = list(row)
        if hdr is None and "수주번호" in row and "단위" in row:
            hdr = row
            continue
        if hdr and row[hdr.index("수주번호")] in (NEW, MOD, ADD):
            eu[row[hdr.index("수주번호")]] = row[hdr.index("단위")]
except Exception as _e:
    eu = {"err": repr(_e), "status": rx.status_code}
check(eu.get(NEW) == "대분" and eu.get(MOD) == "식" and eu.get(ADD) == "대분", "엑셀 저장 줄 단위: 대분 · 식 · 대분", eu)

# ── (선택) 화면 사진: 환경변수 Z15_SHOT_DIR 가 있을 때만 · 시험 판정과 무관 ──
if os.environ.get("Z15_SHOT_DIR"):
    import socket, threading, time, subprocess, json
    import uvicorn
    _sk = socket.socket(); _sk.bind(("127.0.0.1", 0)); _port = _sk.getsockname()[1]; _sk.close()
    _srv = uvicorn.Server(uvicorn.Config(M.app, host="127.0.0.1", port=_port, lifespan="off", log_level="warning"))
    threading.Thread(target=_srv.run, daemon=True).start()
    for _ in range(150):
        if _srv.started:
            break
        time.sleep(0.1)
    _drv = os.path.join(TMP, "shot.py")
    io.open(_drv, "w", encoding="utf-8").write(r'''
import sys
from playwright.sync_api import sync_playwright
B, PID, D, TAG = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 1500, "height": 900})
    pg.goto(B + "/sales/schedule?ym=2026-11"); pg.wait_for_timeout(1500)
    pg.locator("table").first.screenshot(path=D + "/" + TAG + "_board.png")
    pg.goto(B + "/project/" + PID); pg.wait_for_timeout(1500)
    pg.locator(".so-grand-total").first.scroll_into_view_if_needed(); pg.evaluate("window.scrollBy(0,-500)"); pg.wait_for_timeout(300)
    pg.screenshot(path=D + "/" + TAG + "_detail.png")
    br.close()
''')
    _r = subprocess.run([os.environ.get("KNK_PW_PY") or sys.executable, _drv, "http://127.0.0.1:%d" % _port, str(P["id"]), os.environ["Z15_SHOT_DIR"], os.environ.get("Z15_TAG", "shot")],
                        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    print("   (사진)", _r.returncode, (_r.stderr or "")[-300:])

print("\n결과: %d 통과 / %d 실패" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
