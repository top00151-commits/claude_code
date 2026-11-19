# -*- coding: utf-8 -*-
"""z1191z70 시험 (대표 2026-11-19): 등록 화면 잠금을 종류마다 따로 + 열고 있는 사람에게 「누가 기다립니다」 알림
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z70-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z70_")
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


YYMM = date.today().strftime("%y%m")
TODAY6 = date.today().strftime("%y%m%d")
with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0"), ("biz_divs", "TEXT"), ("rank", "TEXT")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    for emp, nm in (("T971", "가영업"), ("T972", "나영업")):
        c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics, rank) "
                  "VALUES (?, 'member', ?, ?, 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1, '프로')", (nm, emp, emp))
    c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales) "
              "VALUES ('다보기', 'member', 'T973', 'T973', 'sso_only_no_local_password', 1, 1, 1, 0)")
    UA = dict(c.execute("SELECT * FROM users WHERE employee_no='T971'").fetchone())
    UB = dict(c.execute("SELECT * FROM users WHERE employee_no='T972'").fetchone())
    UC = dict(c.execute("SELECT * FROM users WHERE employee_no='T973'").fetchone())
    CU = ins(c, "customers", {"name": "가상고객(주)"})
    for i, (code, model, equip) in enumerate((("035T" + YYMM, "VPL2132-0126000", "SENSOR OS 검사기 1연배"), ("034T" + YYMM, "VPL2133,2134-0126000", "SENSOR OS 검사기 MAP 2연배"),
                                              ("010M" + YYMM, "DWMT4400", "AUTO TESTER HANDLER"))):
        pid = ins(c, "projects", {"code": code, "name": "PBA", "mgmt_code": code, "customer_id": CU, "customer_name": "가상고객(주)", "biz_div": code[3],
                                  "project_type": "NEW_EQUIP", "status": "진행중", "model_name": model, "equip_name": equip, "is_archived": 0})
    ins(c, "orders", {"order_no": "T-%s-1" % TODAY6, "customer_id": CU, "order_date": date.today().isoformat(), "status": "CONFIRMED", "project_id": pid, "currency": "KRW"})
    ins(c, "orders", {"order_no": "T-%s-2" % TODAY6, "customer_id": CU, "order_date": date.today().isoformat(), "status": "CONFIRMED", "project_id": pid, "currency": "KRW"})

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


def as_(u):
    CUR["u"] = u




def pg(biz):
    h = q(cl.get, "/projects/quick?biz_div=%s" % biz).text
    m = re.search(r'name="lock_token" id="qLockTok" value="([0-9a-f]+)"', h)
    cov = re.search(r'<div id="qLockCover" class="z57-cover"( hidden)?>', h)
    who = re.search(r'id="qLockWho">([^<]*)<', h)
    return h, (m.group(1) if m else ""), bool(cov and cov.group(1)), (who.group(1) if who else "")


def bt(tok, biz, **kw):
    b = {"token": tok, "active": True, "biz_div": biz, "ptype": ("OTHER" if biz == "E" else "NEW_EQUIP"), "po_type": "신규", "order_date": ""}
    b.update(kw)
    return q(cl.post, "/api/project-reg-lock/beat", json=b).json()


print("§1 종류마다 따로 — 검사기를 열고 있어도 자동화·라이프밸류·기타는 열림")
as_(UA); hA, TA, okA, _ = pg("T")
check(TA and okA, "가영업이 검사기 등록을 엶(잡음)")
as_(UB)
for bz, ko in (("M", "자동화"), ("L", "라이프밸류"), ("E", "기타")):
    h, tk, ok, _ = pg(bz)
    check(tk and ok and ("지금 %s 등록 화면은 <b>나만</b>" % ko) in h, "나영업이 %s 등록은 바로 열림(가림막 없음 · 「지금 %s 등록 화면은 나만」)" % (ko, ko))
    j = bt(tk, bz)
    check(j["held"] and j.get("biz_ko") == ko, "%s 신호: 나영업이 잡음" % ko, j)
with D.db_session() as c:
    names = sorted(r[0] for r in c.execute("SELECT name FROM screen_locks"))
check(names == ["project_new:E", "project_new:L", "project_new:M", "project_new:T"], "잠금이 종류마다 따로 4개", names)

print("§2 같은 종류는 막힘 + 누가 열고 있는지")
hB, TB, okB, whoB = pg("T")
check(TB and not okB and whoB.startswith("가영업"), "나영업이 검사기를 열면 가림막 · 「가영업 프로 님이」", whoB)
check('<b class="z70-biz">검사기</b> 등록 화면에서 작업 중입니다' in hB, "가림막 글: 「… 님이 검사기 등록 화면에서 작업 중입니다」")
check("알림을 띄웠습니다" in hB, "가림막 글: 작업 중인 분 화면에 알림을 띄웠다고 안내")
check("다른 종류(자동화 · 라이프밸류 · 기타 · 소모품)는 위 탭에서 <b>바로 등록</b>" in hB, "가림막 글: 다른 종류는 위 탭에서 바로 등록")
check('class="reg-tab' in hB and hB.index('class="reg-tabs"') < hB.index('id="qLockCover"'), "탭은 가림막 밖(위) — 다른 종류로 바로 옮겨 감")
jb = bt(TB, "T")
check(jb["held"] is False and jb["holder"].startswith("가영업") and "mgmt" not in jb, "나영업 검사기 신호: 못 잡음 · 번호 안 줌", jb)

print("§3 열고 있는 사람에게 알림")
as_(UA); ja = bt(TA, "T")
check(ja["held"] and [w[:3] for w in ja["waiters"]] == ["나영업"], "가영업 신호에 「기다리는 분: 나영업」", ja.get("waiters"))
check('id="qLockAsk" class="z70-ask"' in hA and "님이 지금 <b>검사기</b> 등록 화면을 열려고 기다리고 있습니다" in hA, "가영업 화면에 알림 창(처음엔 숨김) — 「○○ 님이 지금 검사기 등록 화면을 열려고 기다리고 있습니다」")
check("빨리 마무리해 주세요" in hA and 'id="qLockAskOk">확인</button>' in hA, "알림 창: 「빨리 마무리해 주세요」 + [확인]")
check("askFor(held ? (j.waiters||[]) : [])" in hA and "held?10000:8000" in hA, "신호 받을 때마다 알림 판단 · 잡은 사람 신호 10초")
as_(UB); bt(pg("M")[1], "M")
as_(UA); ja2 = bt(TA, "T")
check([w[:3] for w in ja2["waiters"]] == ["나영업"], "다른 종류(자동화)를 연 사람은 검사기 대기자로 안 셈", ja2.get("waiters"))

print("§4 저장 막음은 같은 종류만")
check(M._z57_lock_other(UB, TB, "T").startswith("가영업"), "나영업 검사기 저장 → 막힘(가영업)")
check(M._z57_lock_other(UB, "", "M") == "" and M._z57_lock_other(UB, "", "E") == "", "나영업 자동화·기타 저장 → 통과")
check(M._z57_lock_other(UA, "", "M") .startswith("나영업"), "가영업이 자동화 저장 → 나영업이 잡고 있어 막힘")
as_(UB)
r = q(cl.post, "/projects/new", data={"quick": "1", "lock_token": TB, "name": "X", "customer_name": "가상고객(주)", "biz_div": "T"})
check(r.status_code == 303 and "error=reg_locked" in r.headers.get("location", ""), "나영업 검사기 [등록] → 저장 안 함", r.headers.get("location"))

print("§5 풀면 그 종류만 풀림")
as_(UA); q(cl.post, "/api/project-reg-lock/release", content='{"token":"%s","biz_div":"T"}' % TA, headers={"Content-Type": "application/json"})
as_(UB); jb = bt(TB, "T")
check(jb["held"], "가영업이 검사기 창을 닫으면 → 기다리던 나영업 화면이 열림")
with D.db_session() as c:
    live = sorted(r[0] for r in c.execute("SELECT name FROM screen_locks WHERE beat_at>0"))
check(live == ["project_new:E", "project_new:L", "project_new:M", "project_new:T"], "나영업의 다른 종류 잠금은 그대로", live)
check(M._z70_name("C") == "project_new:T" and M._z70_name("e") == "project_new:E" and M._z70_ko("L") == "라이프밸류", "종류 이름 정리(모르는 값은 검사기)")

print()
print("결과: PASS %d / FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
