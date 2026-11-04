# -*- coding: utf-8 -*-
"""z1191z4d 시험 — 수량 단위: 「대」 추가 · 완제품 「(대)」 고정 · 기타 단위 고르기(신규·추가 발주·수정) · 작업일정표·상세 표시
   이새롬 프로 요청(2026-11-04) 「등록 단위에 "대" 도 추가해줘.. PO유형이 "추가"일때는 수량에 대한 단위를 기록하는곳이 없어...
   다른데도 이런게 있는지 확인하고 단위를 넣을수있게 해줘.」 → 대표 「1. 진행 2. 추천 3. 추천」
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z4d-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z4d_")
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
                 "VALUES ('가상관리자', 'admin', 'T936', 'T936', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(conn.execute("SELECT * FROM users WHERE employee_no='T936'").fetchone())
    conn.execute("INSERT INTO customers (name) VALUES ('가상고객')")

import app.main as M                                        # noqa: E402
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
        "due_date": "2026-11-20", "currency": "KRW", "equip_name": "가상장비", "model": "Z4D-TEST",
        "unit_qty": "1"}


def post(**kw):
    f = dict(BASE)
    f.update(kw)
    r = q(cl.post, "/projects/new", data=f, follow_redirects=False)
    return r.status_code, r.headers.get("location", "")


def proj(name):
    with D.db_session() as c:
        r = c.execute("SELECT * FROM projects WHERE name=? ORDER BY id DESC", (name,)).fetchone()
        return dict(r) if r else None


def orders_of(pid):
    with D.db_session() as c:
        return [dict(r) for r in c.execute("SELECT * FROM orders WHERE project_id=? ORDER BY id", (pid,))]


print("§1 등록 화면")
h = q(cl.get, "/projects/new?type=NEW_EQUIP&biz_div=T").text
check("제품 단위(board_unit)에 EA · 식 · SET · 대", 'name="board_unit"' in h and h.count(">대</option>") >= 2)
check("기타 단위 칸(etc_unit) = 선택 · EA · 식 · SET · 대", 'name="etc_unit"' in h and '<option value="">선택</option>' in h)
check("완제품 수량 「(대)」 고정 글자 · 형태 바꾸면 보이기/숨기기", 'id="qQtyUnitFixed"' in h and "qEtcUnitCell" in h
      and "_qu.style.display=(v==='ASSEMBLY')" in h)

print("§2 서버 — 신규 · 추가 발주 · 수정")
st, loc = post(name="Z4D 기타1", shipment_form="ETC", etc_name="가상 기타 품목", unit_qty="3", unit_price="1000",
               order_amount="3000", etc_unit="SET")
p1 = proj("Z4D 기타1")
o1 = orders_of(p1["id"]) if p1 else []
check("신규 등록(기타 · SET) → 수주 단위 SET", st in (302, 303) and o1 and all(o.get("board_unit") == "SET" for o in o1),
      (st, loc, [(o.get("order_no"), o.get("board_unit"), o.get("unit_qty")) for o in o1]))
st, loc = post(name="Z4D 기타2", shipment_form="ETC", etc_name="가상 기타 품목2", unit_qty="2", unit_price="500",
               order_amount="1000", etc_unit="")
p2 = proj("Z4D 기타2")
o2 = orders_of(p2["id"]) if p2 else []
check("기타 단위를 고르지 않으면 저장 안 함(빈칸)", o2 and all(not o.get("board_unit") for o in o2), [(o.get("board_unit")) for o in o2])
st, loc = post(name="Z4D 완제품", shipment_form="ASSEMBLY", unit_qty="2", unit_price="1000", order_amount="2000", etc_unit="SET")
p3 = proj("Z4D 완제품")
o3 = orders_of(p3["id"]) if p3 else []
check("완제품은 etc_unit 이 와도 단위 저장 안 함(호기 = 대)", o3 and all(not o.get("board_unit") for o in o3), [(o.get("board_unit")) for o in o3])
st, loc = post(name="Z4D 제품", shipment_form="SEMI", unit_price="", order_amount="0", board_qty="10", board_unit="대",
               **{"it_name[]": ["가상 소켓"], "it_spec[]": ["SK-1"], "it_qty[]": ["2"], "it_price[]": ["5000"]})
p4 = proj("Z4D 제품")
o4 = orders_of(p4["id"]) if p4 else []
check("제품 표시수량 단위 「대」 저장(예전엔 EA 로 바뀜)", o4 and o4[-1].get("board_unit") == "대" and o4[-1].get("board_qty") == 10,
      [(o.get("board_qty"), o.get("board_unit")) for o in o4])
if p1:
    st, loc = post(name="Z4D 기타1", po_type="추가", mgmt_code=p1["mgmt_code"], shipment_form="ETC", etc_name="추가 기타",
                   unit_qty="4", unit_price="1000", order_amount="4000", etc_unit="대")
    o1b = orders_of(p1["id"])
    check("추가 발주(PO 추가 · 기타 · 대) → 새 수주만 단위 「대」 · 처음 수주는 SET 그대로",
          len(o1b) == len(o1) + 1 and o1b[-1].get("board_unit") == "대" and o1b[0].get("board_unit") == "SET",
          (st, loc, [(o.get("order_no"), o.get("board_unit")) for o in o1b]))

if p2:
    f = dict(BASE)
    f.update({"name": "Z4D 기타2", "shipment_form": "ETC", "etc_name": "가상 기타 품목2", "unit_qty": "2", "unit_price": "500",
              "order_amount": "1000", "etc_unit": "EA", "mgmt_code": p2["mgmt_code"], "customer_name": "가상고객",
              "unlock_verified": "1"})
    r = q(cl.post, "/projects/%d/edit" % p2["id"], data=f, follow_redirects=False)
    o2b = orders_of(p2["id"])
    check("수정(빠른 폼 · 기타 · EA) → 대표 수주 단위 EA", o2b and o2b[-1].get("board_unit") == "EA",
          (r.status_code, r.headers.get("location", ""), [(o.get("board_unit")) for o in o2b]))
    g = q(cl.get, "/projects/%d/quick-edit" % p2["id"]).text
    check("수정 화면 다시 열면 기타 단위 EA 선택돼 있음", '<option value="EA" selected>EA</option>' in g.replace("  ", " ") or
          'value="EA" selected' in g, g.count('selected'))

print("§3 표시 — 작업일정표 · 상세")
res = q(M.build_schedule_board_rows, ADMIN, 2026, 11)
rows = [r for r in (res.get("rows") or []) if p1 and r.get("ref_id") == p1["id"]]
check("작업일정표 줄(엑셀 경로)에 기타 단위가 실림(SET · 대)", rows and {"SET", "대"} <= {r.get("board_unit") for r in rows},
      [(r.get("qty"), r.get("board_unit")) for r in rows])
sb = q(cl.get, "/sales/schedule?ym=2026-11").text
check("작업일정표 화면 수량 칸 「… SET」 · 「4대」 · 제품 「10대」", " SET</td>" in sb and "4대</td>" in sb and "10대</td>" in sb,
      (sb.count(" SET</td>"), sb.count("4대</td>"), sb.count("10대</td>")))
if p1:
    dh = q(cl.get, "/project/%d" % p1["id"]).text
    # 이 시험은 화면이 만드는 줄 칸(unit_label[] 등)을 보내지 않아 신규 기타 수주가 「수량 1 · 줄 없음」으로 생긴다(운영 실데이터는 줄이 있다)
    check("상세 카드 아래 기타 수량에 단위 「SET」 · 추가 발주 「4대」", "수량 <b>1 SET</b>" in dh and "수량 <b>4대</b>" in dh,
          re.findall(r"수량 <b>[^<]*</b>", dh))
if p4:
    dh4 = q(cl.get, "/project/%d" % p4["id"]).text
    check("상세 제품 수주 = 「품목 1 · 수량 2대」(수주 단위) · ＋ 품목 추가 칸 「대 ×」", "품목 <b>1</b> · 수량 <b>2대</b>" in dh4 and ">대 ×</span>" in dh4,
          (dh4.count("품목 <b>"), dh4.count("대 ×")))
print("결과: 통과 %d / 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
