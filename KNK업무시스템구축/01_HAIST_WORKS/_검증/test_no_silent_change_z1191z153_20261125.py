# -*- coding: utf-8 -*-
"""z1191z153 (대표 11-25 「실제로 사용자가 입력한 게 우선이야. 비워놓은 건 비우고 이상하면 알람만」 · 원칙 4개):
   A 2차 고객 일부러 비움('') = 빈칸(대표값 안 따라감) · NULL = 아직 안 정함(대표값 · 「(대표값)」 표시)
   B 고급 편집 = 수주 2개+ 면 수주별 값 잠금(대표값 안 바뀜)
   C 화면 열기(GET)만으로 저장 안 함 — 상세·정보 수정·고급 편집 · 관리자 일괄 주소 = GET 미리보기만
   D 수주 2개+ 면 상태·납기·발주일·통화를 수주들에 퍼뜨리지 않음(allow_multi 일 때만)
   E 고객사 이름 짝짓기 = 같은 이름이 딱 1곳일 때만"""
import os, sqlite3, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
R = []


def check(l, c, g=""):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l + ("" if c else "  → " + str(g)[:300]))


import app.main as M
from app import project_workflow as W

# ── A: 화면 값 규칙(_z152_effective)
proj = {"customer_id": 58, "customer_name": "KNK VINA", "secondary_customer": "SEV", "currency": "USD"}
e_null = M._z152_effective(proj, {"customer_id": 58, "end_customer": None})
e_blank = M._z152_effective(proj, {"customer_id": 58, "end_customer": ""})
e_val = M._z152_effective(proj, {"customer_id": 58, "end_customer": "SEVT"})
check("A 2차 NULL(안 정함) = 대표값 SEV", e_null["secondary_customer"] == "SEV", e_null)
check("A 2차 ''(일부러 비움) = 빈칸(대표값 안 따라감)", e_blank["secondary_customer"] == "", e_blank)
check("A 2차 값 있음 = 그 값", e_val["secondary_customer"] == "SEVT", e_val)

# ── D: 퍼뜨리기(수주 2개+ = 안 함)
def mk(sos):
    c = sqlite3.connect(":memory:"); c.row_factory = sqlite3.Row
    c.executescript("""
    CREATE TABLE projects(id INTEGER PRIMARY KEY, status TEXT, due_date TEXT, order_date TEXT, currency TEXT);
    INSERT INTO projects VALUES(1,'진행중','2026-12-01','2026-10-01','USD');
    CREATE TABLE orders(id INTEGER PRIMARY KEY, project_id INTEGER, status TEXT, due_date TEXT, order_date TEXT, currency TEXT);
    CREATE TABLE order_items(id INTEGER PRIMARY KEY, order_id INTEGER, unit_status TEXT, due_date TEXT, order_date TEXT, currency TEXT);
    CREATE TABLE project_history(id INTEGER PRIMARY KEY, project_id INTEGER, changed_at TEXT, changed_by INTEGER, field TEXT, old_value TEXT, new_value TEXT, note TEXT);
    """)
    for i, st in sos:
        c.execute("INSERT INTO orders VALUES(?,1,?,'2026-12-01','2026-10-01','USD')", (i, st))
        c.execute("INSERT INTO order_items VALUES(?,?,'진행중','2026-12-01','2026-10-01','USD')", (i, i))
    return c


c = mk([(1, "CONFIRMED"), (2, "CONFIRMED")])
W.cascade_project_meta_to_so(c, 1, {"due_date": "2026-12-01"}, {"due_date": "2027-01-15"}, None)
check("D 수주 2개: 프로젝트 납기를 바꿔도 수주 납기 그대로", [r[0] for r in c.execute("SELECT due_date FROM orders ORDER BY id")] == ["2026-12-01", "2026-12-01"])
check("D 수주 2개: 이력에 「그대로」 남음", c.execute("SELECT COUNT(*) FROM project_history WHERE note LIKE '%z1191z153%'").fetchone()[0] >= 1)
W.cascade_project_status_to_so(c, 1, "출하", None)
check("D 수주 2개: 상태 출하로 바꿔도 수주·호기 그대로", [r[0] for r in c.execute("SELECT status FROM orders")] == ["CONFIRMED", "CONFIRMED"]
      and [r[0] for r in c.execute("SELECT unit_status FROM order_items")] == ["진행중", "진행중"])
W.cascade_project_meta_to_so(c, 1, {"due_date": "2026-12-01"}, {"due_date": "2027-01-15"}, None, allow_multi=True)
check("D 수주 2개 + 사람이 「함께 바꾸기」 확인(allow_multi) = 퍼뜨림", [r[0] for r in c.execute("SELECT due_date FROM orders")] == ["2027-01-15", "2027-01-15"])
c1 = mk([(1, "CONFIRMED")])
W.cascade_project_meta_to_so(c1, 1, {"due_date": "2026-12-01"}, {"due_date": "2027-01-15"}, None)
check("D 수주 1개 = 예전대로 퍼뜨림", c1.execute("SELECT due_date FROM orders").fetchone()[0] == "2027-01-15")
c2 = mk([(1, "CONFIRMED"), (2, "CANCELLED")])
W.cascade_project_meta_to_so(c2, 1, {"due_date": "2026-12-01"}, {"due_date": "2027-01-15"}, None)
check("D 취소 수주는 세지 않음(살아 있는 수주 1개 = 예전대로)", c2.execute("SELECT due_date FROM orders WHERE id=1").fetchone()[0] == "2027-01-15")

# ── E: 이름 짝짓기 = 딱 1곳일 때만(confirm_order_multi 쪽 코드 확인)
src = open(os.path.join(ROOT, "app", "project_workflow.py"), encoding="utf-8").read()
# z1191z157: 같은 규칙을 공용 해석(resolve_customer_by_name = 지금 이름→시스템명→옛 이름 · 단일 후보만)으로 옮김 — 둘 중 하나면 통과
check("E 수주 발행: 같은 이름 여러 곳이면 연결 안 함(LIMIT 2 · 1곳일 때만)",
      ("SELECT id FROM customers WHERE name=? LIMIT 2" in src and "len(_rows153) == 1" in src)
      or ("resolve_customer_by_name" in src and "_z157_res(c, proj[\"customer_name\"])[\"id\"]" in src))
dsrc = open(os.path.join(ROOT, "app", "database.py"), encoding="utf-8").read()
check("E 서버 시작: 이름 짝짓기 = 같은 이름 1곳일 때만", "WHERE customers.name = projects.customer_name) = 1" in dsrc)
check("E 서버 시작: 수주 고객사 빈칸을 프로젝트 값으로 채우던 것 없앰", "UPDATE orders SET customer_id = (" not in dsrc)

# ── C: 화면 열기(GET)만으로 저장하는 코드가 「알림만」으로 바뀌었는지(코드 확인)
msrc = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
check("C 상세: 맞추기 단추 POST /project/{pid}/heal 있음", '@app.post("/project/{pid}/heal")' in msrc)
check("C 상세: 수주액 자가치유 = 열기만이면 알림(heal153)", "저장된 수주액" in msrc and "and not _w153" in msrc)
check("C 정보 수정 화면 열기 저장 없앰", "_heal153q = _heal" in msrc)
check("C 고급 편집 화면 열기 저장 없앰", "_heal153 = heal_pairs" in msrc)
check("C 관리자 일괄 = POST 로만 반영", 'req.method == "POST"' in msrc and 'request.method == "POST"' in msrc)
check("B 고급 편집 수주 2개+ 잠금", "_b153_locked = True" in msrc)

print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
