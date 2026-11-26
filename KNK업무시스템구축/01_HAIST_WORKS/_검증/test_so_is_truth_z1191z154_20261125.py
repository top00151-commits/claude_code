# -*- coding: utf-8 -*-
"""z1191z154 (대표 11-25 「관리번호 = 공통만 · 나머지는 수주번호」 기준 1·2·3 「ok」):
   ① 새 등록 → 2차 고객·PO유형이 그 수주 칸에(2차 비우면 '' = 없음)
   ② 수주 1개 관리번호 정보 수정 → 바꾼 칸이 수주 칸에도
   ③ 추가 발주 「앞 수주와 같게」 자료(/api/projects/search so_last)
   ④ 「수주 칸 확인 필요」 목록 · 열기만으로 저장 안 함 · 대표값으로 확정·앞 수주와 같게·직접 · 관리번호 모두 확정 · 이력
   ⑤ 옛 자료 옮기기(mig154/migrate.py) — 수주 1개 = 그대로 · 수주 2개+ = 첫 수주만(이력 안 바뀐 값) · 이미 값 있는 칸 안 덮음
   임시 DB · TestClient · 운영 아님"""
import contextlib
import importlib.util
import io
import os
import re
import subprocess
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z154-test-only-not-a-real-key"
import app.database as D  # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z154_")
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
                 "VALUES ('가상영업', 'admin', 'T154', 'T154', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(conn.execute("SELECT * FROM users WHERE employee_no='T154'").fetchone())
    conn.execute("INSERT INTO customers (name) VALUES ('가상고객갑')")
    conn.execute("INSERT INTO customers (name) VALUES ('가상고객을')")
import app.main as M  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

M.get_user = lambda request: ADMIN
cl = TestClient(M.app, follow_redirects=False)
R = []


def check(l, c, g=""):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l + ("" if c else "  → " + str(g)[:300]))


def q(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def one(sql, *a):
    with D.db_session() as c:
        r = c.execute(sql, a).fetchone()
        return tuple(r) if r else None


def fp():   # DB 지문 — 열기만으로 바뀌는지
    with D.db_session() as c:
        return (c.execute("SELECT COUNT(*) FROM project_history").fetchone()[0],
                c.execute("SELECT group_concat(COALESCE(end_customer,'∅')||'/'||COALESCE(po_type,'∅'), ',') FROM orders").fetchone()[0])


BASE = {"quick": "1", "biz_div": "M", "project_type": "NEW_EQUIP", "status": "진행중", "confirm_now": "1",
        "order_date": "2026-03-04", "due_date": "2026-03-20", "currency": "KRW", "equip_name": "가상장비", "unit_qty": "1",
        "shipment_form": "ASSEMBLY", "unit_price": "1000000", "order_amount": "1000000", "unit_amount[]": ["1000000"]}

print("[1] 새 등록 → 2차 고객·PO유형이 그 수주 칸에")
q(cl.post, "/projects/new", data=dict(BASE, name="Z154가", model="MZ154A", customer_name="가상고객갑", po_type="신규", secondary_customer="SEV"))
q(cl.post, "/projects/new", data=dict(BASE, name="Z154나", model="MZ154B", customer_name="가상고객갑", po_type="신규", secondary_customer=""))
PA = one("SELECT id FROM projects WHERE name='Z154가'")[0]
PB = one("SELECT id FROM projects WHERE name='Z154나'")[0]
check("새 등록: 수주 2차 = SEV · PO유형 = 신규", one("SELECT end_customer, po_type FROM orders WHERE project_id=?", PA) == ("SEV", "신규"),
      one("SELECT end_customer, po_type FROM orders WHERE project_id=?", PA))
check("새 등록: 2차 비우고 등록 → 수주 2차 = ''(없음) · NULL 아님", one("SELECT end_customer FROM orders WHERE project_id=?", PB) == ("",),
      one("SELECT end_customer FROM orders WHERE project_id=?", PB))

code_a = one("SELECT mgmt_code FROM projects WHERE id=?", PA)[0]
q(cl.post, "/projects/new", data=dict(BASE, name="Z154가", model="MZ154A", customer_name="가상고객을", po_type="추가", mgmt_code=code_a, secondary_customer="", currency="KRW"))
r2 = one("SELECT end_customer, po_type FROM orders WHERE project_id=? ORDER BY id DESC LIMIT 1", PA)
check("추가 발주: 2차 비우고 등록 → 새 수주 2차 = ''(없음) · PO유형 = 추가", r2 == ("", "추가"), r2)
check("추가 발주: 관리번호(프로젝트) 2차·고객은 그대로", one("SELECT secondary_customer FROM projects WHERE id=?", PA) == ("SEV",))
with D.db_session() as c:   # 이 뒤 시험은 수주 1개 기준 — 추가 수주는 취소로
    c.execute("UPDATE orders SET status='CANCELLED' WHERE id=(SELECT MAX(id) FROM orders WHERE project_id=?)", (PA,))

print("[2] 수주 1개 정보 수정 → 바꾼 칸이 수주 칸에도")
with D.db_session() as c:
    pa = dict(c.execute("SELECT * FROM projects WHERE id=?", (PA,)).fetchone())
    ch = M._z152_save_so_fields(c, PA, {"po_type": "개조", "secondary_customer": "SEVT"}, pa, ADMIN, allow_single=True)
check("수주 1개 + allow_single: 바꾼 칸(PO유형·2차) 수주에 저장", one("SELECT end_customer, po_type FROM orders WHERE project_id=?", PA) == ("SEVT", "개조")
      and ch and len(ch) == 2, (one("SELECT end_customer, po_type FROM orders WHERE project_id=?", PA), ch))
with D.db_session() as c:
    check("기본(allow_single 없음) = 예전처럼 None", M._z152_save_so_fields(c, PA, {"po_type": "수리"}, pa, ADMIN) is None)
src = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
check("정보 수정 저장: 수주 1개면 allow_single=True 로 부름", "_z152_save_so_fields(_c154, int(pid), form, _old10, _u, allow_single=True)" in src)

print("[3] 추가 발주 「앞 수주와 같게」 자료")
r = q(cl.get, "/api/projects/search", params={"q": "Z154가"})
rows = (r.json() or {}).get("rows") or []
sl = rows[0].get("so_last") if rows else None
check("so_last = 가장 최근 수주 값(2차 SEVT · 통화 KRW · 형태)", sl and sl.get("end_customer") == "SEVT" and sl.get("currency") == "KRW" and sl.get("shipment_form"), sl)
t = open(os.path.join(ROOT, "app", "templates", "project_quick_form.html"), encoding="utf-8").read()
check("등록 화면: 「앞 수주와 같게」 단추 · 누를 때만 채움", "qSameAsPrevBtn" in t and "b.onclick=function()" in t)

print("[4] 수주 칸 확인 필요")
with D.db_session() as c:   # 수주 2개 관리번호: 옛 자료처럼 수주 칸 비움
    cid = c.execute("SELECT customer_id FROM projects WHERE id=?", (PB,)).fetchone()[0]
    c.execute("UPDATE projects SET secondary_customer='SEV', po_type='추가' WHERE id=?", (PB,))
    c.execute("UPDATE orders SET end_customer=NULL, po_type=NULL WHERE project_id=?", (PB,))
    c.execute("INSERT INTO orders(order_no, customer_id, project_id, order_date, status) VALUES('M-Z154-2', ?, ?, '2026-05-01', 'CONFIRMED')", (cid, PB))
    c.execute("INSERT INTO orders(order_no, customer_id, project_id, order_date, status) VALUES('M-Z154-3', ?, ?, '2026-06-01', 'CONFIRMED')", (cid, PB))
f0 = fp()
r = q(cl.get, "/projects/so-check")
check("목록 200 · 수주 3건(2차·PO유형 비어 있음)", r.status_code == 200 and r.text.count('data-oid="') == 3 and "(대표값 · 확인 필요)" in r.text, r.status_code)
check("목록을 여는 것만으로는 저장 안 함", fp() == f0)
check("프로젝트 목록에 「⚠ 수주 칸 확인 필요 3」", "수주 칸 확인 필요 <b>3</b>" in q(cl.get, "/projects").text)
with D.db_session() as c:
    o1, o2, o3 = [x[0] for x in c.execute("SELECT id FROM orders WHERE project_id=? ORDER BY order_date, id", (PB,)).fetchall()]
j = q(cl.post, "/api/so-check/%d" % o1, data={"field": "end_customer", "action": "rep"}).json()
check("대표값으로 확정: 첫 수주 2차 = SEV", j.get("ok") and one("SELECT end_customer FROM orders WHERE id=?", o1) == ("SEV",), j)
j = q(cl.post, "/api/so-check/%d" % o2, data={"field": "end_customer", "action": "prev"}).json()
check("앞 수주와 같게: 둘째 수주 2차 = SEV", j.get("ok") and one("SELECT end_customer FROM orders WHERE id=?", o2) == ("SEV",), j)
j = q(cl.post, "/api/so-check/%d" % o3, data={"field": "end_customer", "action": "set", "value": ""}).json()
check("직접 넣기(비움) = '' 없음", j.get("ok") and one("SELECT end_customer FROM orders WHERE id=?", o3) == ("",), j)
j = q(cl.post, "/api/so-check/%d" % o3, data={"field": "end_customer", "action": "rep"}).json()
check("이미 정해진 칸은 다시 안 바꿈(409)", not j.get("ok"), j)
j = q(cl.post, "/api/so-check-proj/%d" % PB, data={"field": "po_type"}).json()
check("관리번호 모두 대표값으로 확정: PO유형 3건 = 추가", j.get("ok") and j.get("n") == 3
      and one("SELECT COUNT(*) FROM orders WHERE project_id=? AND po_type='추가'", PB) == (3,), j)
check("이력: 수주마다 「칸 확인」 남음", one("SELECT COUNT(*) FROM project_history WHERE project_id=? AND note LIKE 'z1191z154 수주 %칸 확인%'", PB)[0] >= 6)
# z1191z159: 거래구분이 빈 품목 줄도 목록에 — 「내수로 확정」·「수출」(사람이 고름 · 빈 줄만 · 이력)
with D.db_session() as c:
    _iex_o = [x[0] for x in c.execute("SELECT DISTINCT o.id FROM orders o JOIN order_items i ON i.order_id=o.id JOIN projects p ON p.id=o.project_id "
                                       "WHERE i.is_export IS NULL AND COALESCE(o.status,'')<>'CANCELLED'").fetchall()]
_iex_ok = True
for _k, _oid in enumerate(_iex_o):
    _v = "수출" if _k == 0 else "내수"
    _j = q(cl.post, "/api/so-check/%d" % _oid, data={"field": "is_export", "action": "set", "value": _v}).json()
    _iex_ok = _iex_ok and bool(_j.get("ok")) and one("SELECT COUNT(*) FROM order_items WHERE order_id=? AND is_export IS NULL", _oid) == (0,)
check("거래구분 빈 줄 = 사람이 고른 값으로(%d건)" % len(_iex_o), _iex_ok)
if _iex_o:
    _j = q(cl.post, "/api/so-check/%d" % _iex_o[0], data={"field": "is_export", "action": "set", "value": "내수"}).json()
    check("거래구분 이미 정한 수주는 다시 안 바꿈(409)", not _j.get("ok") and one("SELECT MIN(is_export) FROM order_items WHERE order_id=?", _iex_o[0]) == (1,), _j)
check("모두 정하면 목록 비어 「✅ 완료」", "✅ 완료 — 확인할 수주가 없습니다" in q(cl.get, "/projects/so-check").text)
tt = open(os.path.join(ROOT, "app", "templates", "so_check_z154.html"), encoding="utf-8").read()
check("목록 화면 ✕ 닫기", "knk_close_btn.html" in tt)
js = "\n;\n".join(re.sub(r"\{\{.*?\}\}", "0", re.sub(r"\{%.*?%\}", "", re.sub(r"\{#.*?#\}", "", x, flags=re.S), flags=re.S), flags=re.S)
                  for x in re.findall(r"<script(?![^>]*src=)[^>]*>(.*?)</script>", tt + t, re.S))
jp = os.path.join(TMP, "z154.js"); open(jp, "w", encoding="utf-8").write(js)
try:
    rr = subprocess.run(["node", "--check", jp], capture_output=True, text=True, encoding="utf-8")
    check("목록·등록 화면 스크립트 문법(node)", rr.returncode == 0, rr.stderr[-300:])
except FileNotFoundError:
    print("· node 없음 — 문법 검사 건너뜀")

print("[5] 옛 자료 옮기기(mig154/migrate.py)")
MIG = os.environ.get("Z154_MIG") or os.path.join(ROOT, "..", "..", "..", "mig154", "migrate.py")
if os.path.isfile(MIG):
    spec = importlib.util.spec_from_file_location("mig154", MIG); mg = importlib.util.module_from_spec(spec); spec.loader.exec_module(mg)
    with D.db_session() as c:   # 수주 1개 관리번호 하나를 옛 자료처럼(수주 칸 비움) · 수주 2개 관리번호 첫 수주 PO 비움
        c.execute("UPDATE orders SET end_customer=NULL, po_type=NULL WHERE project_id=?", (PA,))
        c.execute("UPDATE projects SET secondary_customer='SEV', po_type='신규' WHERE id=?", (PA,))
        c.execute("UPDATE orders SET po_type=NULL WHERE id=?", (o2,))
    mg.DB = D.DB_PATH; mg.ROOT = TMP
    os.makedirs(os.path.join(TMP, "data", "backups"), exist_ok=True)
    with contextlib.redirect_stdout(io.StringIO()):
        rc = mg.main("CHECK")
    check("확인 모드 = 아무것도 안 바뀜", rc == 0 and one("SELECT end_customer FROM orders WHERE project_id=?", PA) == (None,))
    mg.ROOT = TMP; os.makedirs(TMP + "/data/backups", exist_ok=True)
    with contextlib.redirect_stdout(io.StringIO()):
        rc = mg.main("APPLY")
    check("적용: 수주 1개 → 2차 SEV · PO 신규 그대로 옮김", rc == 0 and one("SELECT end_customer, po_type FROM orders WHERE project_id=?", PA) == ("SEV", "신규"))
    check("적용: 수주 2개+ 둘째 수주 PO유형은 안 채움(확인 필요로)", one("SELECT po_type FROM orders WHERE id=?", o2) in ((None,), ("",)))
    check("적용: 이미 값 있는 칸 안 덮음(셋째 수주 2차 '' 그대로)", one("SELECT end_customer FROM orders WHERE id=?", o3) == ("",))
    check("적용 이력 남음", one("SELECT COUNT(*) FROM project_history WHERE note LIKE 'z1191z154 관리번호 값을 수주로 옮김%'")[0] >= 2)
else:
    print("· mig154/migrate.py 없음 — 옮기기 시험 건너뜀(%s)" % MIG)

print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
