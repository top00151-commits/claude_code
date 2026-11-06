# -*- coding: utf-8 -*-
"""z1191z7 시험 — 안지연 프로 추가 신고 2건(2026-11-06 · 대표 「① 진행 / ② 1·2 진행」)
  ① 작업일정표 세금계산서 색: 정수 반올림 대신 1센트 미만 차이는 같은 금액(원문 검사 — JS 는 화면 실측에서)
  ② 정식 「프로젝트 수정」 폼: 수주 2건 이상이면 ③ 확정 금액이 수주별 표 + 합계(부품 수량을 더한 「호기 395대 · 단가 742」 없음) ·
     맨 위 안내 띠 · 형태/모델명/PO 유형/고객사1 에 (대표값) · 수주 1건이면 예전 그대로 · 저장(POST)은 그대로 통과
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z7-test-only-not-a-real-key"
import app.database as D  # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z7_")
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
                 "VALUES ('가상관리자', 'admin', 'T907', 'T907', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(conn.execute("SELECT * FROM users WHERE employee_no='T907'").fetchone())
    conn.execute("INSERT INTO customers (name) VALUES ('가상고객')")
    conn.execute("INSERT INTO customers (name) VALUES ('가상 VINA')")
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


BASE = {"quick": "1", "customer_name": "가상고객", "biz_div": "M", "project_type": "NEW_EQUIP", "po_type": "신규", "status": "진행중",
        "confirm_now": "1", "order_date": "2026-11-04", "due_date": "2026-11-20", "currency": "USD", "fx_rate": "1400", "equip_name": "가상장비", "unit_qty": "1"}


def post_new(**kw):
    f = dict(BASE); f.update(kw)
    return q(cl.post, "/projects/new", data=f).status_code


def proj(name):
    with D.db_session() as c:
        return dict(c.execute("SELECT * FROM projects WHERE name=? ORDER BY id DESC", (name,)).fetchone())


def orders_of(pid):
    with D.db_session() as c:
        return [dict(r) for r in c.execute("SELECT * FROM orders WHERE project_id=? ORDER BY id", (pid,))]


# 혼합: 완제품 신규(호기 2대) → 완제품 추가(2대) → 상품 개조(부품 3줄 · 수량 합 60 · 고객 다름)
print("§1 혼합 프로젝트(완제품 2건 + 상품 1건) 정식 수정 폼")
post_new(name="혼합-설비", model="MX", shipment_form="ASSEMBLY", unit_qty="2", unit_price="1000", order_amount="2000",
         **{"unit_amount[]": ["1000", "1000"]})
PA = proj("혼합-설비")
post_new(name="혼합-설비", po_type="추가", mgmt_code=PA["mgmt_code"], model="MX2", shipment_form="ASSEMBLY", unit_qty="2", unit_price="1500", order_amount="3000",
         **{"unit_amount[]": ["1500", "1500"]})
post_new(name="혼합-설비", po_type="개조", mgmt_code=PA["mgmt_code"], customer_name="가상 VINA", model="MP", shipment_form="PARTS", unit_price="", order_amount="0", parts_units="",
         **{"pk_name[]": ["볼트", "너트", "와셔"], "pk_model[]": ["B", "N", "W"], "pk_qty[]": ["10", "20", "30"], "pk_price[]": ["1", "2", "3"]})
OA = orders_of(PA["id"])
check(len(OA) == 3, "수주 3건 — %d" % len(OA))
h = q(cl.get, "/projects/%d/edit" % PA["id"]).text
check("전체(<b>수주 3건</b>" in h and "공통 정보" in h and "형태 섞임" in h, "맨 위 안내 띠: 관리번호 전체 · 수주 3건 · 형태 섞임")
for o in OA:
    check(('?so=%s' % o["order_no"]) in h, "수주별 표에 %s(상세 카드 링크)" % o["order_no"])
check("수주별 수량 · 금액" in h and h.count("<table") >= 2, "③ 확정 금액 = 수주별 표(맨 위 띠와 ③ 두 곳)")
check('type="hidden" id="pf_unit_qty"' in h and 'type="number" id="pf_unit_qty"' not in h, "1대 단가·수량 입력칸은 숨김(값은 그대로 보냄)")
m = re.search(r'id="pf_unit_qty" name="unit_qty" value="(\d+)"', h)
check(m and m.group(1) == "4", "숨은 수량 = 완제품 호기 4대(부품 60개를 더하지 않음) — %s" % (m.group(1) if m else None))
check("호기 4대" not in h.split("③")[0] and "60대" not in h and "64" not in re.sub(r"\d{2,}\.\d+", "", h.split("수주별 수량 · 금액")[1][:3000]), "395 같은 합산 숫자 없음")
check(h.count("(대표값)") >= 4, "형태·모델명·PO 유형·고객사1 에 (대표값) — %d곳" % h.count("(대표값)"))
check("상품" in h and "완제품" in h and "1식" in h and "2대" in h, "표에 형태(완제품/상품)와 수량(2대 · 1식)")
check("가상 VINA" in h and "개조" in h, "표에 수주별 고객사(가상 VINA)·PO유형(개조)")
check("수주별 실제 값은 아래 표" in h, "③ 머리 글: 수주별 실제 값은 아래 표")
# 저장(POST)은 그대로 통과(상태·비고 보존 · 수량/단가 변경 차단은 서버 그대로)
f = {"unlock_verified": "1", "name": "혼합-설비", "customer_name": "가상고객", "biz_div": "M", "project_type": "NEW_EQUIP", "model": "MX", "equip_name": "가상장비",
     "po_type": "신규", "status": "진행중", "currency": "USD", "is_export": "1", "order_date": "2026-11-04", "due_date": "2026-11-20", "shipment_form": "ASSEMBLY",
     "unit_qty": "4", "unit_price": "1250", "order_amount": "5060", "note": "혼합 비고"}
r = q(cl.post, "/projects/%d/edit" % PA["id"], data=f)
P2 = proj("혼합-설비")
check(r.status_code in (200, 303) and "error=" not in (r.headers.get("location") or "") and P2["logi_note"] == "혼합 비고" and P2["status"] == "진행중", "정식 폼 저장 통과 · 비고·상태 보존 — %s" % r.headers.get("location", "")[:40])

print("§2 수주 1건 프로젝트는 예전 그대로")
post_new(name="단일-설비", model="M1", shipment_form="ASSEMBLY", unit_qty="3", unit_price="100", order_amount="300", **{"unit_amount[]": ["100", "100", "100"]})
PB = proj("단일-설비")
h1 = q(cl.get, "/projects/%d/edit" % PB["id"]).text
check("수주별 수량 · 금액" not in h1 and "(대표값)" not in h1 and 'type="number" id="pf_unit_qty"' in h1, "수주 1건: 표·대표값 없음 · 수량 입력칸 그대로")
m1 = re.search(r'id="pf_unit_qty" name="unit_qty"[^>]*value="(\d+)"', h1)
check(m1 and m1.group(1) == "3", "수량 = 호기 3대 — %s" % (m1.group(1) if m1 else None))
check("완제품 호기 3대 합계" in h1, "머리 글: 완제품 호기 3대 합계")

print("§3 ① 작업일정표 세금계산서 색 판정(원문)")
b = io.open(os.path.join(ROOT, "app", "templates", "schedule_board.html"), encoding="utf-8").read()
check("status=(Math.abs(sum-total)<0.01)?'ok':'mismatch'" in b and "(ssum===total)" not in b and "Math.round(parseFloat(tr.dataset.rowamt" not in b, "정수 반올림 비교 → 0.01 미만 차이는 같은 금액(수주금액도 반올림 안 함)")
print("결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
