# -*- coding: utf-8 -*-
"""z1191z8 시험 — 이새롬 프로 요청 2건(2026-11-06 · 대표 「① 1·2·3·4 / ② 1 진행해」)
  ① 작업일정표 단가·금액 칸 「무상」: 단가 0 을 적은 완제품 수주·소모품 → 「무상」 알약 · 값 있는 줄은 금액 그대로 ·
     품목 없는 소모품(작성중)은 빈칸 · 단가 있고 금액 0 인 프로젝트 줄은 무상 아님 · 엑셀 저장도 「무상」 · JS 편집 규칙(원문)
  ② 소모품 탭 안 하위 책갈피: 전체/검사기/자동화 건수 · cbiz=T/M 필터 · 소모품 탭 아닐 땐 무시 · 전사 일정표(/dept/schedule) 도 같음 ·
     달 이동·엑셀·기간 찾기 링크에 cbiz 유지
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z8-test-only-not-a-real-key"
import app.database as D  # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z8_")
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
                 "VALUES ('가상관리자', 'admin', 'T908', 'T908', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(conn.execute("SELECT * FROM users WHERE employee_no='T908'").fetchone())
    conn.execute("INSERT INTO customers (name) VALUES ('가상고객')")
import app.main as M  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

M.get_user = lambda request: ADMIN
cl = TestClient(M.app, follow_redirects=False)
OK = FAIL = 0


def check(cond, msg):
    global OK, FAIL
    if cond:
        OK += 1; print("  ✅", msg)
    else:
        FAIL += 1; print("  ❌", msg)


def q(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


YM = "2026-11"
BASE = {"quick": "1", "customer_name": "가상고객", "biz_div": "M", "project_type": "NEW_EQUIP", "po_type": "신규", "status": "진행중",
        "confirm_now": "1", "order_date": "2026-11-04", "due_date": "2026-11-20", "currency": "KRW", "equip_name": "가상장비", "unit_qty": "1"}


def post_new(**kw):
    f = dict(BASE); f.update(kw)
    return q(cl.post, "/projects/new", data=f)


def proj(name):
    with D.db_session() as c:
        return dict(c.execute("SELECT * FROM projects WHERE name=? ORDER BY id DESC", (name,)).fetchone())


def row_html(h, code):
    """작업일정표에서 관리번호 code 줄(tr) 전부(여러 줄이면 합침)"""
    return "\n".join(m for m in re.findall(r"<tr[^>]*>.*?</tr>", h, re.S) if (">%s<" % code) in m)


print("§1 작업일정표 「무상」 — 완제품 2대 단가 0(무상) vs 값 있는 프로젝트")
r = post_new(name="무상-설비", model="MF", shipment_form="ASSEMBLY", unit_qty="2", unit_price="0", order_amount="0", **{"unit_amount[]": ["0", "0"]})
PF = proj("무상-설비")
check(r.status_code in (200, 303) and "error=" not in (r.headers.get("location") or ""), "단가 0 완제품 등록 통과(z1171 「0 을 적으면 무상」) — %s" % (r.headers.get("location") or "")[:40])
with D.db_session() as c:   # 호기 있는 무상 수주도(운영 12건 꼴): 호기 2대 단가·금액 0 을 직접 넣음
    _so = c.execute("SELECT id FROM orders WHERE project_id=?", (PF["id"],)).fetchone()[0]
    for _i in (1, 2):
        c.execute("INSERT INTO order_items (order_id, unit_label, unit_price, amount, qty) VALUES (?,?,?,?,?)", (_so, "%d호기" % _i, 0, 0, 1))
post_new(name="무상-빈수주", model="MF0", shipment_form="ASSEMBLY", unit_qty="1", unit_price="0", order_amount="0")
PF0 = proj("무상-빈수주")
post_new(name="유상-설비", model="MP", shipment_form="ASSEMBLY", unit_qty="1", unit_price="1500000", order_amount="1500000", **{"unit_amount[]": ["1500000"]})
PP = proj("유상-설비")
h = q(cl.get, "/sales/schedule?ym=%s" % YM).text
rf, rp = row_html(h, PF["mgmt_code"]), row_html(h, PP["mgmt_code"])
check(rf and rf.count('class="free-tag"') == 2, "무상 줄: 단가·금액 칸 둘 다 「무상」 알약 — %d개" % rf.count('class="free-tag"'))
check('cw-price editable filled free' in rf and 'cw-amount editable filled free' in rf, "무상 줄: filled+free 클래스(편집 가능 유지)")
check(rp and "free-tag" not in rp and "₩1,500,000" in rp, "값 있는 줄: 「무상」 없음 · ₩1,500,000 그대로")
check(row_html(h, PF0["mgmt_code"]).count('class="free-tag"') == 2, "호기 없는 단일 수주(수주금액 0 으로 적음): 「무상」")

print("§2 소모품 — 단가 0(무상) · 값 있음 · 품목 없음 + 진행 사업부 T/M")
with D.db_session() as c:
    def _co(no, code, biz, total, items, status="CONFIRMED"):
        c.execute("INSERT INTO consumable_orders (co_no, customer_name, order_date, due_date, currency, total_amount, status, mgmt_code, biz_div, equip_name) "
                  "VALUES (?,?,?,?,?,?,?,?,?,?)", (no, "가상고객", "2026-11-03", "2026-11-18", "USD", total, status, code, biz, "소모품 %d종" % max(1, len(items))))
        cid = c.execute("SELECT id FROM consumable_orders WHERE co_no=?", (no,)).fetchone()[0]
        for i, (nm, qty, up) in enumerate(items, 1):
            c.execute("INSERT INTO consumable_order_items (co_id, line_no, part_name, qty, unit, unit_price, amount) VALUES (?,?,?,?,?,?,?)",
                      (cid, i, nm, qty, "EA", up, (None if up is None else up * qty)))
        return cid
    CO_FREE = _co("C-261103-91", "901C2611", "T", 0, [("POGO PIN", 2, 0.0)])
    CO_PAID = _co("C-261103-92", "902C2611", "M", 465.6, [("DSV 소모품", 4, 116.4)])
    CO_EMPTY = _co("C-261103-93", "903C2611", "T", 0, [], status="DRAFT")
    CO_NULL = _co("C-261103-94", "904C2611", "M", 0, [("단가 안 적음", 1, None)])
h = q(cl.get, "/sales/schedule?ym=%s" % YM).text
check(row_html(h, "901C2611").count('class="free-tag"') == 2, "소모품 단가 0: 단가·금액 「무상」")
rp2 = row_html(h, "902C2611")
check("free-tag" not in rp2 and "$465.60" in rp2, "소모품 값 있음: $465.60 그대로")
re3 = row_html(h, "903C2611")
check(re3 and "free-tag" not in re3 and re.search(r'cw-price[^"]*"[^>]*>\s*</td>', re3), "소모품 품목 없음(작성중): 빈칸(무상 아님)")
check("free-tag" not in row_html(h, "904C2611"), "소모품 단가 NULL(안 적음): 무상 아님")

print("§3 수주 없는 프로젝트 줄 — 단가 있고 금액 0 은 무상 아님 · 둘 다 0 이면 무상")
with D.db_session() as c:
    c.execute("INSERT INTO projects (name, mgmt_code, customer_name, biz_div, project_type, status, order_date, due_date, unit_qty, unit_price, order_amount, currency, model_name) "
              "VALUES ('예정-단가만','905M2611','가상고객','M','NEW_EQUIP','수주예정','2026-11-05','2026-11-25',1,500000,0,'KRW','MX')")
    c.execute("INSERT INTO projects (name, mgmt_code, customer_name, biz_div, project_type, status, order_date, due_date, unit_qty, unit_price, order_amount, currency, model_name) "
              "VALUES ('예정-무상','906M2611','가상고객','M','NEW_EQUIP','수주예정','2026-11-05','2026-11-25',1,0,0,'KRW','MX')")
h = q(cl.get, "/sales/schedule?ym=%s" % YM).text
check("free-tag" not in row_html(h, "905M2611") and "₩500,000" in row_html(h, "905M2611"), "단가 500,000·금액 0: 무상 아님(단가 그대로)")
check(row_html(h, "906M2611").count('class="free-tag"') == 2, "단가 0·금액 0: 「무상」")

print("§4 소모품 탭 안 하위 책갈피")
h = q(cl.get, "/sales/schedule?ym=%s&biz=C" % YM).text
check('class="sbm-sub"' in h and "소모품 나눠 보기" in h, "소모품 탭: 하위 책갈피 띠")
check(re.search(r'cbiz=T[^>]*>.*?검사기 <b>2</b>', h) and re.search(r'cbiz=M[^>]*>.*?자동화 <b>2</b>', h) and re.search(r'전체 <b>4</b>', h), "건수: 전체 4 · 검사기 2 · 자동화 2")
for code in ("901C2611", "902C2611", "903C2611", "904C2611"):
    pass
hT = q(cl.get, "/sales/schedule?ym=%s&biz=C&cbiz=T" % YM).text
check(row_html(hT, "901C2611") and row_html(hT, "903C2611") and not row_html(hT, "902C2611") and not row_html(hT, "904C2611"), "cbiz=T: 검사기 소모품 2건만")
hM = q(cl.get, "/sales/schedule?ym=%s&biz=C&cbiz=M" % YM).text
check(row_html(hM, "902C2611") and row_html(hM, "904C2611") and not row_html(hM, "901C2611"), "cbiz=M: 자동화 소모품 2건만")
check('class="sbm sbm-s on"' in hT and hT.count('sbm-s on') == 1, "검사기 책갈피 켜짐 표시")
hX = q(cl.get, "/sales/schedule?ym=%s&cbiz=T" % YM).text
check(row_html(hX, "902C2611") and row_html(hX, PF["mgmt_code"]) and 'class="sbm-sub"' not in hX, "소모품 탭 아니면 cbiz 무시 · 띠 없음")
h0 = q(cl.get, "/sales/schedule?ym=%s&biz=T" % YM).text
check('class="sbm-sub"' not in h0, "검사기 탭: 하위 책갈피 없음")
check("&cbiz=T" in hT.split("<tbody")[0] and "export.xlsx?ym=%s&biz=C&cbiz=T" % YM in hT and '_SCHED_CBIZ = "T"' in hT, "달 이동·엑셀·기간 찾기 링크에 cbiz 유지")
hP = q(cl.get, "/sales/schedule?pf=2026-11-01&pt=2026-11-30&biz=C&cbiz=M").text
check(row_html(hP, "902C2611") and not row_html(hP, "901C2611") and "pf=2026-11-01&amp;pt=2026-11-30&biz=C&cbiz=T" in hP, "기간 모드에서도 필터·링크")

print("§5 엑셀 저장 — 무상 줄 단가·금액 「무상」 · cbiz 필터")
import openpyxl  # noqa: E402
r = q(cl.get, "/sales/schedule/export.xlsx?ym=%s" % YM)
wb = openpyxl.load_workbook(io.BytesIO(r.content)); ws = wb.active
hdr = [c.value for c in ws[1]]
ip, ia, ic = hdr.index("단가"), hdr.index("금액"), hdr.index("관리번호")
vals = {str(rw[ic]): (rw[ip], rw[ia]) for rw in ws.iter_rows(min_row=2, values_only=True) if rw[ic]}
check(vals.get(PF["mgmt_code"]) == ("무상", "무상") and vals.get("901C2611") == ("무상", "무상"), "엑셀: 무상 줄 단가·금액 = 「무상」")
check(vals.get(PP["mgmt_code"], (None,))[0] == 1500000 and vals.get("902C2611", (None,))[0] == 465.6, "엑셀: 값 있는 줄은 숫자 그대로")
r2 = q(cl.get, "/sales/schedule/export.xlsx?ym=%s&biz=C&cbiz=T" % YM)
ws2 = openpyxl.load_workbook(io.BytesIO(r2.content)).active
codes2 = {str(rw[ic]) for rw in ws2.iter_rows(min_row=2, values_only=True) if rw[ic]}
check(codes2 == {"901C2611", "903C2611"}, "엑셀 cbiz=T: 검사기 소모품 2건만 — %s" % sorted(codes2))

print("§6 전사 일정표(/dept/schedule) 소모품 하위 책갈피")
hd = q(cl.get, "/dept/schedule?ym=%s&biz=C" % YM).text
check('class="dsx-sub"' in hd and "검사기 2" in hd and "자동화 2" in hd, "전사 일정표 소모품 탭: 하위 책갈피 + 건수")
hdT = q(cl.get, "/dept/schedule?ym=%s&biz=C&cbiz=T" % YM).text
check("901C2611" in hdT and "902C2611" not in hdT and "&biz=C&cbiz=T" in hdT.split("dsx-tabs")[0] + hdT, "전사 일정표 cbiz=T: 검사기 소모품만 · 달 이동 링크 유지")

print("§7 화면 JS 규칙(원문)")
b = io.open(os.path.join(ROOT, "app", "templates", "schedule_board.html"), encoding="utf-8").read()
check("|무상/g" in b and "function _knkFreeShow" in b and "_knkIsZero(val)) _knkFreeShow" in b, "「무상」 글자는 편집 때 0 · 0 저장하면 「무상」 표시")
check("priceTd.classList.contains('free')) _knkFreeShow(amtTd" in b, "수량×단가 재계산 뒤 금액 칸도 「무상」")
print("결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
