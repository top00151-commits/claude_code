# -*- coding: utf-8 -*-
"""z1191z16 시험 — 안지연 프로 확인 · 대표 「1,2,3 진행해」 (2026-11-10)
  ① 상세 화면: 작업일정표에서 수주번호를 눌러 들어오면(?so=) 위쪽 프로젝트 정보(고객사·PO유형·형태·모델·장비·거래구분·2차·수량)가
     그 수주 값 · 「관리번호 대표값 보기」(?hdr=rep) · 수주 1건/so 없음은 예전 그대로
  ② 상품 수량 0·빈칸 = 「⚠ 미입력」(작업일정표·부서 일정표·엑셀 단위·상세 카드·합계·수정 화면 표) — 1대분으로 숨기지 않음
  ③ 수정 화면 「고칠 대상」 상품 수주에 「수량」 칸 → 이 수주만 저장
  + 수주로 안 갈라진 상품 줄도 PO유형 단위 규칙
  임시 DB · TestClient · 운영 아님 · (선택) Z16_SHOT_DIR 이 있으면 화면 사진
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z16-test-only-not-a-real-key"
import app.database as D  # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z16_")
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
                 "VALUES ('가상관리자', 'admin', 'T916', 'T916', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(conn.execute("SELECT * FROM users WHERE employee_no='T916'").fetchone())
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
        "equip_name": "대표장비", "model": "대표모델", "unit_qty": "1"}
PK = {"pk_name[]": ["볼트", "너트"], "pk_model[]": ["B", "N"], "pk_qty[]": ["10", "20"], "pk_price[]": ["1", "2"]}


def post_new(**kw):
    f = dict(BASE); f.update(kw)
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


# 자료: 완제품 신규(대표모델) + 상품 추가(모델 MP16 · 장비 EQ16) · 상품 수량을 0 으로(운영 M-251127-2 와 같은 꼴)
post_new(name="z16-P", shipment_form="ASSEMBLY", unit_price="1000", order_amount="1000", **{"unit_amount[]": ["1000"]})
P = proj("z16-P")
post_new(name="z16-P", po_type="추가", mgmt_code=P["mgmt_code"], shipment_form="PARTS", unit_price="", order_amount="0", parts_units="3",
         model="MP16", equip_name="EQ16", **PK)
O = orders_of(P["id"])
S1, S2 = O[0], O[-1]
with D.db_session() as c:
    c.execute("UPDATE orders SET unit_qty=0, model_name='MP16', equip_name='EQ16' WHERE id=?", (S2["id"],))
post_new(name="z16-ONE", shipment_form="ASSEMBLY", unit_price="500", order_amount="500", **{"unit_amount[]": ["500"]})
P1 = proj("z16-ONE")
S1one = orders_of(P1["id"])[0]

print("§0 자료")
check(len(O) == 2 and (S2.get("so_type") or "").upper() == "PARTS_EXPORT", "수주 2건(완제품 · 상품)", [(o["order_no"], o.get("so_type")) for o in O])

print("§1 상세 화면 위쪽 = 고른 수주")
h = q(cl.get, "/project/%d?so=%s" % (P["id"], S2["order_no"])).text
dl = h.split("<h3>프로젝트 정보</h3>")[1].split("</dl>")[0] if "<h3>프로젝트 정보</h3>" in h else ""
check(("수주 %s</b> 기준으로 보는 중" % S2["order_no"]) in dl and "hdr=rep" in dl, "「📌 수주 … 기준으로 보는 중」 · 「관리번호 대표값 보기」 링크")
check("<dd>MP16</dd>" in dl and "<dd>EQ16</dd>" in dl and "대표모델" not in dl, "모델명·장비명 = 그 수주 값(MP16 · EQ16)", re.findall(r"<dt>모델명.*?</dd>", dl, re.S)[:1])
check(re.search(r"<dt>형태 <span class=\"hso-tag\"[^>]*>\(수주\)</span></dt>\s*<dd>상품</dd>", dl) is not None, "형태 = 상품(수주)")
check(re.search(r"<dt>PO유형 <span class=\"hso-tag\"", dl) is not None and "추가" in dl, "PO유형 = 추가(수주)")
check("⚠ 수량 미입력" in dl, "수량(수주) = ⚠ 수량 미입력")
check(dl.count('class="hso-tag"') >= 7, "(수주) 표시 칸 7개 이상 — %d" % dl.count('class="hso-tag"'))
check(('href="/projects/%d/edit?so=%s"' % (P["id"], S2["order_no"])) in h, "「프로젝트 정보 수정」 단추 = 보던 수주를 고른 채로(?so=) — 안지연 프로 순서 재검증에서 찾음")
hr = q(cl.get, "/project/%d?so=%s&hdr=rep" % (P["id"], S2["order_no"])).text
dlr = hr.split("<h3>프로젝트 정보</h3>")[1].split("</dl>")[0]
check("관리번호 대표값</b>을 보는 중" in dlr and "<dd>대표모델</dd>" in dlr and 'class="hso-tag"' not in dlr, "?hdr=rep → 관리번호 대표값 · 「수주 … 기준으로 보기」")
hn = q(cl.get, "/project/%d" % P["id"]).text
check('class="hso-bar"' not in hn and "<dd>대표모델</dd>" in hn, "?so= 없이 열면 예전 그대로(대표값)")
h1 = q(cl.get, "/project/%d?so=%s" % (P1["id"], S1one["order_no"])).text
check('class="hso-bar"' not in h1, "수주 1건 프로젝트는 예전 그대로")

print("§2 상품 수량 0 = ⚠ 미입력")
F = M._parts_qty_z15
check(F(0, "추가")["missing"] and F(0, "추가")["short"] == "미입력" and F(3, "개조")["short"] == "3식", "단위 함수: 0 → 미입력 · 3 개조 → 3식")
U = M._board_qty_unit
check(U({"form_type": "상품", "po_type": "개조"}) == "식" and U({"form_type": "상품", "po_type": "신규"}) == "대분"
      and U({"form_type": "기타"}) == "식", "수주로 안 갈라진 상품 줄도 PO유형 단위(개조 식 · 신규 대분) · 기타는 그대로")
labels = re.findall(r"수량 <b>([^<]+)</b>", h)
check("⚠ 수량 미입력" in labels, "상세 수주 카드 수량 = ⚠ 수량 미입력", labels)
check("⚠ 수량 미입력 1건" in h, "상세 합계 줄 「⚠ 수량 미입력 1건」")
hs = q(cl.get, "/sales/schedule?ym=2026-11").text
row = [tr for tr in re.findall(r"<tr[^>]*>.*?</tr>", hs, re.S) if (">%s<" % S2["order_no"]) in tr]
check(row and "⚠ 미입력" in row[0], "작업일정표 상품 줄 수량 = ⚠ 미입력", len(row))
rx = q(cl.get, "/sales/schedule/export.xlsx?ym=2026-11")
unit = None
try:
    import openpyxl
    ws = openpyxl.load_workbook(io.BytesIO(rx.content), read_only=True).worksheets[0]
    hdr = None
    for r_ in ws.iter_rows(values_only=True):
        r_ = list(r_)
        if hdr is None and "수주번호" in r_ and "단위" in r_:
            hdr = r_; continue
        if hdr and r_[hdr.index("수주번호")] == S2["order_no"]:
            unit = r_[hdr.index("단위")]
except Exception as _e:
    unit = repr(_e)
check(unit == "대분 미입력", "엑셀 단위 칸 = 「대분 미입력」", unit)
he = q(cl.get, "/projects/%d/edit?so=%s" % (P["id"], S2["order_no"])).text
tbl = he.split('class="z14-common-note"')[1].split("</table>")[0]
check(">미입력<" in tbl, "수정 화면 수주 표 수량 = 미입력")

print("§3 수정 화면 수주 칸에 수량")
pn = {}
for m in re.finditer(r'<div class="z14-panel" data-so="([^"]+)" data-soid="(\d+)".*?(?=<div class="z14-panel"|<datalist id="z14CustList")', he, re.S):
    pn[m.group(1)] = m.group(0)
p2, p1 = pn.get(S2["order_no"], ""), pn.get(S1["order_no"], "")
check('data-field="unit_qty" data-orig="" value=""' in p2 and "⚠ 미입력" in p2 and "완제품 대분" in p2, "상품 수주 패널: 수량 칸(빈칸 · ⚠ 미입력 · 단위 완제품 대분)")
check('data-field="unit_qty"' not in p1, "완제품 수주 패널엔 수량 칸 없음(호기 수 = 상세 카드)")
check("u16.textContent = (po16.value === '개조') ? '식' : '완제품 대분'" in he, "PO유형을 바꾸면 단위 글자도 바뀜(JS)")
with contextlib.redirect_stdout(io.StringIO()):
    rq = cl.post("/sales/orders/%d/quick-edit" % S2["id"], data={"unit_qty": "4"})
a1, a2 = orders_of(P["id"])
check(rq.json().get("ok") and int(a2["unit_qty"]) == 4 and a1["unit_qty"] == S1["unit_qty"], "이 수주만 수량 4 저장(같은 저장 경로) · 다른 수주 그대로", (rq.json(), a2["unit_qty"]))
h2 = q(cl.get, "/project/%d?so=%s" % (P["id"], S2["order_no"])).text
check("완제품 4대분" in h2 and "⚠ 수량 미입력" not in h2, "저장 뒤 상세 = 완제품 4대분 · 미입력 사라짐")
hs2 = q(cl.get, "/sales/schedule?ym=2026-11").text
row2 = [tr for tr in re.findall(r"<tr[^>]*>.*?</tr>", hs2, re.S) if (">%s<" % S2["order_no"]) in tr]
mm = re.search(r'<span class="qn">([^<]*)</span><span class="qu">([^<]*)</span>', row2[0]) if row2 else None
check(mm is not None and (mm.group(1) + mm.group(2)) == "4대분", "저장 뒤 작업일정표 = 4대분", mm and mm.groups())

if os.environ.get("Z16_SHOT_DIR"):
    import socket, threading, time, subprocess
    import uvicorn
    with D.db_session() as c:
        c.execute("UPDATE orders SET unit_qty=0 WHERE id=?", (S2["id"],))   # 사진용: 미입력 상태로 되돌림
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
B, PID, SO, D = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 1500, "height": 950})
    pg.goto(B + "/project/" + PID + "?so=" + SO); pg.wait_for_timeout(1500)
    pg.locator(".proj-info-2col").first.locator("xpath=..").screenshot(path=D + "/z16_detail_top.png")
    pg.goto(B + "/sales/schedule?ym=2026-11"); pg.wait_for_timeout(1500)
    pg.locator("table").first.screenshot(path=D + "/z16_board.png")
    pg.goto(B + "/projects/" + PID + "/edit?so=" + SO); pg.wait_for_timeout(1500)
    pg.locator("#z14Box").screenshot(path=D + "/z16_edit_panel.png")
    br.close()
''')
    _r = subprocess.run([os.environ.get("KNK_PW_PY") or sys.executable, _drv, "http://127.0.0.1:%d" % _port, str(P["id"]), S2["order_no"],
                         os.environ["Z16_SHOT_DIR"]], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    print("   (사진)", _r.returncode, (_r.stderr or "")[-300:])

print("\n결과: %d 통과 / %d 실패" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
