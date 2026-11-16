# -*- coding: utf-8 -*-
"""z1191z37 시험 — 제작요청서 사업부 아이콘 = 프로젝트 등록 화면(대표 「제작요청서 아이콘도 똑같이 맞춰줘」 2026-11-16)
  ① 작성 화면 사업부 고르기(2곳) · 위쪽 사업부 표시  ② 소모품 제작요청서  ③ 연구(R)는 검사기와 겹치지 않게 🧪
  임시 DB · TestClient · 운영 아님
"""
import contextlib, io, os, re, sys, tempfile
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z37-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z37_")
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


with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    if "alias" not in {r[1] for r in c.execute("PRAGMA table_info(customers)")}:
        c.execute("ALTER TABLE customers ADD COLUMN alias TEXT")
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
              "VALUES ('가상관리자', 'admin', 'T937', 'T937', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(c.execute("SELECT * FROM users WHERE employee_no='T937'").fetchone())
    CU = ins(c, "customers", {"name": "가상고객(주)", "alias": "가상고객"})
    PIDS = {}
    for bd in ("T", "M", "L", "E"):
        PIDS[bd] = ins(c, "projects", {"code": "001%s2611" % bd, "name": "P-" + bd, "mgmt_code": "001%s2611" % bd, "customer_id": CU,
                                       "customer_name": "가상고객(주)", "currency": "KRW", "status": "진행중", "biz_div": bd,
                                       "project_type": "NEW_EQUIP", "shipment_form": "ASSEMBLY", "order_date": "2026-11-01", "due_date": "2026-11-20", "is_archived": 0})
    CO = ins(c, "consumable_orders", {"co_no": "C1", "mgmt_code": "001C2611", "customer_name": "가상고객(주)", "currency": "KRW", "total_amount": 1000,
                                      "status": "CONFIRMED", "biz_div": "T", "order_date": "2026-11-02", "due_date": "2026-11-10"})

import app.main as M  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
M.get_user = lambda request: ADMIN
with D.db_session() as c:   # 운영은 기동 때 더해지는 칸(main.py 기동 훅) — 빈 시험 DB 에 맞춰 줌
    _have = {r[1] for r in c.execute("PRAGMA table_info(prod_requests)")}
    for _col in ("recipients", "wt_team_ids", "user_ids", "updated_at", "updated_by_name", "dept_names", "sent_to", "dept_count",
                 "msg_sent", "created_date", "issued_by_name", "cust_req", "note", "mgmt_code", "issued_by"):
        if _col not in _have:
            c.execute("ALTER TABLE prod_requests ADD COLUMN %s TEXT" % _col)
    for _bd, _pid in PIDS.items():   # 저장된 제작요청서(보기 화면에 위쪽 「사업부」 칸이 그려짐)
        ins(c, "prod_requests", {"project_id": _pid, "mgmt_code": "001%s2611" % _bd, "cust_req": "시험", "created_at": "2026-11-16 20:00:00",
                                 "created_date": "2026-11-16", "issued_by_name": "가상관리자"})
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


_chooser = open(os.path.join(ROOT, "app", "templates", "project_new_chooser.html"), encoding="utf-8").read()
IC = dict(zip("TMLEC", re.findall(r'<div class="ic">([^<]+)</div>', _chooser)[:5]))
print("등록 화면 아이콘:", IC)
print("§1 제작요청서 작성 화면")
for bd, pid in PIDS.items():
    r = q(cl.get, "/project/%d/prod-request/edit" % pid)
    h = r.text
    top = re.search(r'<span class="k">사업부</span><span class="v">([^<]*)</span>', h)
    check(r.status_code == 200 and top and top.group(1).strip().split()[0] == IC[bd], "%s 프로젝트 — 위쪽 사업부 표시 = %s" % (bd, IC[bd]), top and top.group(1))
opts = re.findall(r'<option[^>]*value="([TMLECR])"[^>]*>\s*([^<\s]+)', h)
o = {}
for v, ic in opts:
    o.setdefault(v, set()).add(ic)
check(all(o.get(k) == {IC[k]} for k in "TMLEC") and o.get("R") == {"🧪"}, "사업부 고르기 = 등록 화면 아이콘 · 연구 🧪(검사기 🔬 와 안 겹침)", o)
print("§2 소모품 제작요청서")
h2 = q(cl.get, "/consumables/%d/prod-request" % CO).text
m2 = re.search(r'<span class="k">사업부</span><span class="v">([^<]*)</span>', h2)
check(m2 and m2.group(1).strip().split()[0] == IC["C"], "소모품 제작요청서 사업부 = %s" % IC["C"], m2 and m2.group(1))
print("§3 제작요청서 목록(이미 같음)")
h3 = q(cl.get, "/prod-requests").text if q(cl.get, "/prod-requests").status_code == 200 else ""
l3 = dict(re.findall(r"prqurl\('([TMLEC])'[^>]*>\s*([^<\s]+)", open(os.path.join(ROOT, "app", "templates", "prod_requests_list.html"), encoding="utf-8").read()))
check(l3 == IC, "제작요청서 목록 사업부 칩 = 등록 화면", l3)

print("§4 앱 전체 훑기(z1191z38) — 옛 사업부 아이콘(🔎 ⚙ 💡 🧴 💗 · 사업부 「🗂 기타」) 0곳 · 연구 = 🧪")
_OLD = re.compile(r"(🔎|⚙️|⚙|💡|🧴|💗) ?(검사기|자동화|라이프밸류|소모품|연구)|🗂 ?기타|🔬 ?(연구|Đề tài)")
_FORM_OK = re.compile(r"완제품|📦 제품|🧰|_FORM|_form_lbl|_qFormLbl|qFormPick|v5H226z448|_sf == 'ETC'|\(그 외\)")
bad = []
for _dp, _dn, _fs in os.walk(os.path.join(ROOT, "app")):
    if "_v4_backup" in _dp or "_legacy_base" in _dp:
        continue
    for _f in _fs:
        if not _f.endswith((".html", ".py", ".js")):
            continue
        for _i, _ln in enumerate(io.open(os.path.join(_dp, _f), encoding="utf-8", errors="replace"), 1):
            if _OLD.search(_ln) and not _FORM_OK.search(_ln) and "{#" not in _ln and "#}" not in _ln                     and not _ln.lstrip().startswith("#"):   # 주석(화면에 안 나옴)은 뺌
                bad.append("%s:%d %s" % (_f, _i, _ln.strip()[:80]))
check(not bad, "옛 사업부 아이콘 남은 곳 없음(출고 형태 「🗂 기타」·주석 빼고)", bad[:8])
print("§5 고친 화면 직접 그리기")
_pages = {"/projects/quick?biz_div=T": ["🤖 자동화", "🌐 기타", "📦 소모품", "🔬 검사기"], "/rnd": ["🧪 연구개발 과제"],
          "/dept/schedule?biz=C": ["🤖 자동화"], ("/admin/users/%d/edit" % ADMIN["id"]): ["> 🔬 검사기", "> 🤖 자동화", "> 💄 라이프밸류", "> 🌐 기타"]}
for _u, _want in _pages.items():
    _r = q(cl.get, _u)
    _miss = [w for w in _want if w not in _r.text]
    check(_r.status_code == 200 and not _miss, "%s — %s" % (_u, " · ".join(_want)), (_r.status_code, _miss))

print()
print("결과: %d 통과 / %d 실패" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
