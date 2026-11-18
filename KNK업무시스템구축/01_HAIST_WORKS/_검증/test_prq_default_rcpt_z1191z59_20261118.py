# -*- coding: utf-8 -*-
"""z1191z59 시험 (대표 2026-11-18 「사업부별 기본 받는 부서 — 우선 만들고 실무자들이 선택해서 저장할수있게」)
  ① 저장·불러오기(사업부마다) · 고친 사람·시각 · 이력 · 비우기
  ② 권한(발행할 수 있는 사람만 저장) · 없는 사업부 거절 · 없어진 팀·퇴사자는 빼고 보임
  ③ 세 화면(등록 · 제작요청서 새 작성 · 소모품 통보)에 「⭐ 기본 받는 사람」 띠 — 사업부·체크 칸 바르게
  임시 DB · TestClient · 운영 아님
"""
import contextlib, io, os, re, sys, tempfile
from datetime import date, timedelta
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z59-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z59_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()


def ins(c, table, row):
    cols = {r[1] for r in c.execute("PRAGMA table_info(%s)" % table)}
    ks = [k for k in row if k in cols]
    c.execute("INSERT INTO %s (%s) VALUES (%s)" % (table, ",".join('"%s"' % k for k in ks), ",".join("?" * len(ks))), [row[k] for k in ks])
    return c.execute("SELECT last_insert_rowid()").fetchone()[0]


FUT = (date.today() + timedelta(days=20)).isoformat()
with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0"), ("biz_divs", "TEXT"), ("rank", "TEXT")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    T1 = ins(c, "teams", {"name": "가상설계팀", "code": "D59", "entity": "KOR", "display_order": 1})
    T2 = ins(c, "teams", {"name": "가상제조팀", "code": "P59", "entity": "KOR", "display_order": 2})
    T3 = ins(c, "teams", {"name": "가상구매팀", "code": "B59", "entity": "KOR", "display_order": 3})
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics, rank) "
              "VALUES ('가영업', 'member', 'T981', 'T981', 'sso_only_no_local_password', 1, 1, 1, 1, 0, 0, '프로')")
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
              "VALUES ('나물류', 'member', 'T982', 'T982', 'sso_only_no_local_password', 1, 1, 0, 0, 1, 1)")
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
              "VALUES ('다보기', 'member', 'T983', 'T983', 'sso_only_no_local_password', 1, 1, 1, 0, 1, 0)")
    UA = dict(c.execute("SELECT * FROM users WHERE employee_no='T981'").fetchone())
    UB = dict(c.execute("SELECT * FROM users WHERE employee_no='T982'").fetchone())
    UC = dict(c.execute("SELECT * FROM users WHERE employee_no='T983'").fetchone())
    for i, t in enumerate((T1, T1, T2)):
        c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id) VALUES (?, 'member', ?, ?, 'sso_only_no_local_password', 1, 1, ?)",
                  ("가상받는이%d" % i, "T99%d" % i, "T99%d" % i, t))
    M1 = c.execute("SELECT id FROM users WHERE employee_no='T990'").fetchone()[0]
    M2 = c.execute("SELECT id FROM users WHERE employee_no='T992'").fetchone()[0]
    CU = ins(c, "customers", {"name": "가상고객(주)"})
    P = ins(c, "projects", {"code": "080M2611", "name": "자동화", "mgmt_code": "080M2611", "customer_id": CU, "customer_name": "가상고객(주)", "biz_div": "M",
                            "project_type": "NEW_EQUIP", "status": "진행중", "model_name": "AM1", "equip_name": "가상 자동화", "is_archived": 0, "order_date": "2026-11-13", "due_date": FUT})
    ins(c, "orders", {"order_no": "M-261113-1", "customer_id": CU, "order_date": "2026-11-13", "status": "CONFIRMED", "project_id": P, "currency": "KRW"})
    CO = ins(c, "consumable_orders", {"co_no": "C-261118-5", "mgmt_code": "090C2611", "customer_id": CU, "customer_name": "가상고객(주)", "order_date": "2026-11-18", "status": "CONFIRMED"})

import app.main as M  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
CUR = {"u": UA}
M.get_user = lambda request: CUR["u"]
with contextlib.redirect_stdout(io.StringIO()):
    try:
        M.startup()
    except Exception as _e:
        print("startup:", _e)
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


get = lambda b: q(cl.get, "/api/prq-default-recipients?biz=" + b).json()
save = lambda b, t, u: q(cl.post, "/api/prq-default-recipients/" + b, json={"team_ids": t, "user_ids": u})

print("§1 저장·불러오기")
j = get("T")
check(j["ok"] and j["d"]["teams"] == [] and j["d"]["users"] == [] and j["d"]["by"] == "", "처음엔 비어 있음")
r = save("T", [T1, T2], [M2]).json()
check(r["ok"] and [t["name"] for t in r["d"]["teams"]] == ["가상설계팀", "가상제조팀"] and r["d"]["users"][0]["id"] == M2 and r["d"]["by"].startswith("가영업") and r["d"]["at"],
      "검사기 기본 = 설계·제조팀 + 개별 1명 · 정한 사람·시각", r)
j = get("T")
check([t["id"] for t in j["d"]["teams"]] == [T1, T2] and [u["id"] for u in j["d"]["users"]] == [M2], "다시 불러와도 같음")
check(get("M")["d"]["teams"] == [], "자동화는 따로(비어 있음)")
CUR["u"] = UB
r = save("C", [T3], []).json()
check(r["ok"] and r["d"]["teams"][0]["name"] == "가상구매팀" and r["d"]["by"].startswith("나물류"), "소모품 기본 = 구매팀(물류 권한자도 저장 가능)", r)
CUR["u"] = UA
r = save("T", [T1], []).json()
with D.db_session() as c:
    nh = c.execute("SELECT COUNT(*) FROM prq_default_rcpt_hist WHERE biz='T'").fetchone()[0]
check(r["ok"] and [t["id"] for t in r["d"]["teams"]] == [T1] and r["d"]["users"] == [] and nh == 2, "고쳐 저장 → 바뀜 · 이력 2줄", (r["d"], nh))
r = save("T", [], []).json()
check(r["ok"] and r["d"]["teams"] == [] and r["d"]["users"] == [], "비우기")
save("T", [T1, T2], [M1])

print("§2 권한 · 거절 · 없어진 것")
CUR["u"] = UC
check(save("T", [T3], []).status_code == 403, "발행 권한 없는 사람은 저장 못 함(보기만 권한)")
CUR["u"] = UA
check(q(cl.get, "/api/prq-default-recipients?biz=R").status_code == 400 and save("X", [T1], []).status_code == 400, "없는 사업부는 거절")
check(save("M", [T1, 99999], [88888]).json()["d"]["teams"] == [{"id": T1, "name": "가상설계팀"}], "없는 팀·사람 번호는 저장 안 함")
with D.db_session() as c:
    c.execute("UPDATE users SET is_active=0 WHERE id=?", (M1,))
check(get("T")["d"]["users"] == [], "퇴사(비활성)한 사람은 기본에서 빠져 보임")

print("§3 세 화면에 띠")
h = q(cl.get, "/projects/quick?biz_div=M").text
m = re.search(r'<div class="z59-dr" data-biz="([A-Z])" data-root="([^"]+)" data-team="([^"]+)" data-user="([^"]+)" data-apply="1">', h)
check(m and m.groups() == ("M", "knkpPr", ".pr-team", ".pr-user") and "기본 받는 사람 · <b>자동화</b>" in h, "등록 화면(자동화 탭) — 사업부 M · 등록 체크 칸", m and m.groups())
h = q(cl.get, "/project/%d/prod-request/edit?new=1" % P).text
m = re.search(r'<div class="z59-dr" data-biz="([A-Z])" data-root="([^"]+)" data-team="([^"]+)" data-user="([^"]+)" data-apply="1">', h)
check(m and m.groups() == ("M", "knkpPns", "input[name=add_team_ids]", "input[name=add_user_ids]"), "제작요청서 새 작성 — 그 프로젝트 사업부(M)", m and m.groups())
check(h.count('class="z59-dr"') == 1, "새 작성 칸에만(수정발행 받는 사람 추가 칸에는 안 넣음)")
h = q(cl.get, "/consumables/%d" % CO).text
m = re.search(r'<div class="z59-dr" data-biz="([A-Z])" data-root="([^"]+)" data-team="([^"]+)" data-user="([^"]+)" data-apply="1">', h)
check(m and m.groups() == ("C", "knkpNtf", ".ntf-ck", ".ntf-uck"), "소모품 관련부서 통보 — 소모품(C)", m and m.groups())
check(h.count("if(window.__z59) return") == 1, "스크립트 한 번만")

print()
print("결과: PASS %d / FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
