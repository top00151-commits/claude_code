# -*- coding: utf-8 -*-
"""z1191z4e 시험 — 작업일정표 수량 단위 통일 + 숫자/단위 줄맞춤 · 부서 일정표 · 엑셀 「단위」 칸
   이새롬 프로 요청(2026-11-04) 「수량에 단위가 있는게 있고 없는게 있어 이거 일괄적으로 통일」 → 대표 「1. 추천 2. 추천」
   + 「문자를 중앙정렬로 잡으면 … 숫자와 단위가 일정하게 줄맞춤이 안되게 보여 … 줄맞춤으로 제대로 보이게」
   규칙: 완제품 대 · 제품(등록 단위, 없으면 EA) · 상품 대분/식 · 기타(고른 단위, 없으면 식) · 소모품 건
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z4e-test-only-not-a-real-key"   # 시험용 가짜 값

import openpyxl                                            # noqa: E402
import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z4e_")
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
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
                 "VALUES ('가상관리자', 'admin', 'T938', 'T938', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(conn.execute("SELECT * FROM users WHERE employee_no='T938'").fetchone())
    conn.execute("INSERT INTO customers (name) VALUES ('가상고객')")

import app.main as M                                        # noqa: E402
from app import consumables as CO                          # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

M.get_user = lambda request: ADMIN
cl = TestClient(M.app)
OK = FAIL = 0


def check(label, cond, got=None):
    global OK, FAIL
    if cond:
        OK += 1
        print("  [OK] " + label)
    else:
        FAIL += 1
        print("  [FAIL] " + label + ("   ← %r" % (got,) if got is not None else ""))


def q(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


BASE = {"quick": "1", "customer_name": "가상고객", "biz_div": "T", "project_type": "NEW_EQUIP",
        "po_type": "신규", "status": "진행중", "confirm_now": "1", "order_date": "2026-11-04",
        "due_date": "2026-11-20", "currency": "KRW", "equip_name": "가상장비", "unit_qty": "1"}


def post(**kw):
    f = dict(BASE)
    f.update(kw)
    return q(cl.post, "/projects/new", data=f, follow_redirects=False).status_code


print("§1 단위 정하기(한 곳)")
U = M._board_qty_unit
check("소모품 줄 = 건(형태가 상품이라 적혀 있어도)", U({"kind": "consumable", "form_type": "상품", "qty": 1}) == "건")
# z1191z15 (대표 「개조는 모두 식으로 1식, 2식, 3식」 2026-11-10): 상품 단위 = PO유형 — 개조 식 · 그 밖 대분(1대분 포함)
check("상품 = 개조 식 · 신규·추가 대분(1이어도 대분)", U({"is_parts": True, "qty": 3, "po_type": "추가"}) == "대분"
      and U({"is_parts": True, "qty": 1, "po_type": "신규"}) == "대분" and U({"is_parts": True, "qty": 2, "po_type": "개조"}) == "식"
      and U({"is_parts": True, "qty": 1, "po_type": "개조"}) == "식")
check("적어 둔 단위가 먼저(SET · 대)", U({"board_unit": "SET", "form_type": "제품"}) == "SET" and U({"board_unit": "대", "form_type": "기타"}) == "대")
check("형태별 기본: 완제품 대 · 제품 EA · 기타 식 · 모름 대",
      U({"form_type": "완제품"}) == "대" and U({"form_type": "제품"}) == "EA" and U({"form_type": "기타"}) == "식" and U({}) == "대")
check("부서 일정표 줄은 이 수주 형태(qty_form)를 먼저 본다", U({"qty_form": "제품", "form_type": "완제품"}) == "EA")

print("§2 작업일정표 화면 · 부서 일정표 · 엑셀")
post(name="Z4E 완제품", model="M-ASSY", shipment_form="ASSEMBLY", unit_qty="2", unit_price="1000", order_amount="2000")
post(name="Z4E 제품표시", model="M-SEMI1", shipment_form="SEMI", unit_price="", order_amount="0", board_qty="10", board_unit="SET",
     **{"it_name[]": ["소켓"], "it_spec[]": ["SK"], "it_qty[]": ["2"], "it_price[]": ["100"]})
post(name="Z4E 제품", model="M-SEMI2", shipment_form="SEMI", unit_price="", order_amount="0",
     **{"it_name[]": ["핀"], "it_spec[]": ["P"], "it_qty[]": ["7"], "it_price[]": ["100"]})
post(name="Z4E 기타", model="M-ETC", shipment_form="ETC", etc_name="가상 기타", unit_qty="1", unit_price="500", order_amount="500")
cid, _ = q(CO.co_create, customer_name="가상고객", biz_div="T", order_date="2026-11-04", due_date="2026-11-20", source_file="직접등록")
res = q(M.build_schedule_board_rows, ADMIN, 2026, 11)
rows = res.get("rows") or []
byname = {}
for r in rows:
    byname.setdefault(r.get("name") or "", []).append(r)
units = {k: [(v.get("qty"), M._board_qty_unit(v)) for v in vs] for k, vs in byname.items() if k.startswith("Z4E") or k == "소모품"}
check("줄마다 단위: 완제품 대 · 제품(표시 SET) · 제품 EA · 기타 식 · 소모품 건",
      all(u == "대" for _, u in units.get("Z4E 완제품", [("", "x")])) and units.get("Z4E 제품표시", [("", "")])[0][1] == "SET"
      and units.get("Z4E 제품", [("", "")])[0][1] == "EA" and units.get("Z4E 기타", [("", "")])[0][1] == "식"
      and any(u == "건" for _, u in units.get("소모품", [])), units)
sb = q(cl.get, "/sales/schedule?ym=2026-11").text
cells = re.findall(r'<span class="qwrap"><span class="qn">([^<]*)</span><span class="qu">([^<]*)</span></span>', sb)
check("화면 수량 칸 = 숫자 칸 + 단위 칸(줄맞춤 틀)", len(cells) >= 5 and {"대", "SET", "EA", "식", "건"} <= {u for _, u in cells}, cells)
check("화면 수량 칸에 data-unit(저장·취소 뒤 다시 그릴 단위)", 'data-col="qty" data-unit="대"' in sb and 'data-unit="건"' in sb)
check("수량 칸 기본 폭 84px(단위가 들어가게)", "note:130,qty:84,price:96" in sb)
check("편집 스크립트: 단위 빼고 숫자만 · 다시 그리기", "function _qtyNum(s)" in sb and "cur=_qtyNum(cur)" in sb and "function _qtyPaint(td)" in sb)
css = open(os.path.join(ROOT, "static", "css", "schedule_board.css"), encoding="utf-8").read()
check("줄맞춤 CSS: 숫자 오른쪽 · 단위 왼쪽 · 고정 폭", ".qwrap { display:inline-grid; grid-template-columns:2.9em 2.3em;" in css
      and ".qwrap .qn { text-align:right;" in css and ".qwrap .qu { text-align:left;" in css)
ds = q(cl.get, "/dept/schedule?ym=2026-11")
dcells = re.findall(r'<span class="qn">([^<]*)</span><span class="qu">([^<]*)</span>', ds.text)
check("부서 일정표 수량에도 단위 · 줄맞춤", ds.status_code == 200 and dcells and ".qwrap { display:inline-grid;" in ds.text, (ds.status_code, dcells[:6]))
xr = q(cl.get, "/sales/schedule/export.xlsx?ym=2026-11")
wb = openpyxl.load_workbook(io.BytesIO(xr.content))
ws = wb["일괄등록"]
hdr = [c.value for c in ws[1]]
iq, iu = hdr.index("수량"), (hdr.index("단위") if "단위" in hdr else -1)
vals = [(row[iq].value, row[iu].value) for row in ws.iter_rows(min_row=2) if iu >= 0]
check("엑셀: 수량 바로 옆 「단위」 칸 · 수량은 숫자", iu == iq + 1 and vals and all(isinstance(v, (int, float)) or v in (None, "") for v, _ in vals)
      and {"대", "SET", "EA", "식", "건"} <= {u for _, u in vals}, (hdr[:9], vals[:8]))
check("올리기 파서가 「단위」를 다른 칸으로 잘못 읽지 않음(단가·수량·통화·담당자 등과 안 겹침)",
      not any(s in "단위" for s in ("관리번호", "프로젝트명", "모델", "장비", "고객사", "발주일", "납기", "납품일", "수량", "단가", "통화",
                                     "거래", "PO", "형태", "상태", "담당자", "연락처", "납품위치", "비고", "기타사항", "영업", "세금계산서", "거래명세서")))
print("결과: 통과 %d / 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
