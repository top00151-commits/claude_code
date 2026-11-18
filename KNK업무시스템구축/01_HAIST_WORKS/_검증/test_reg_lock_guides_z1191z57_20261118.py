# -*- coding: utf-8 -*-
"""z1191z57 시험 (대표 2026-11-18 등록 화면)
  ① 「등록화면을 동시에 열리지 않게 · 누가 열고 작업중이면 누가 열고 있다고 안내」 — 한 번에 한 사람 · 기다리는 사람 화면 가림 ·
     창 닫힘(신호 끊김 75초)·10분 무입력이면 넘어감 · 다른 사람 저장 막음 · 같은 사람 다른 탭은 됨
  ① 「지금 몇번을 사용해서 등록할껀지 먼저」 — 잡은 사람에게 다음 관리번호·수주번호(저장 때와 같은 함수)
  ② 프로젝트명·모델명·장비명 ⓘ 입력 기준 — 등록 권한자 누구나 고침 · 이력 · 최근 등록 예 · 수정 화면에도
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z57-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z57_")
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


def page():
    h = q(cl.get, "/projects/quick?biz_div=T").text
    m = re.search(r'name="lock_token" id="qLockTok" value="([0-9a-f]+)"', h)
    cov = re.search(r'<div id="qLockCover" class="z57-cover"( hidden)?>', h)
    who = re.search(r'id="qLockWho">([^<]*)<', h)
    return h, (m.group(1) if m else ""), bool(cov and cov.group(1)), (who.group(1) if who else "")


def beat(tok, **kw):
    b = {"token": tok, "active": True, "biz_div": "T", "ptype": "NEW_EQUIP", "po_type": "신규", "order_date": ""}
    b.update(kw)
    return q(cl.post, "/api/project-reg-lock/beat", json=b).json()


def lock_set(**kw):
    with D.db_session() as c:
        for k, v in kw.items():
            c.execute("UPDATE screen_locks SET %s=? WHERE name='project_new'" % k, (v,))


print("§1 한 번에 한 사람")
as_(UA); hA, TA, coverA_hidden, _ = page()
check(TA and coverA_hidden and 'id="qLockBar" class="z57-bar">' in hA, "가영업이 먼저 열면 잡음 · 가림막 없음 · 「나만 쓰는 중」 띠")
as_(UB); hB, TB, coverB_hidden, whoB = page()
check(TB and not coverB_hidden and whoB.startswith("가영업"), "나영업이 열면 가림막 「지금 가영업 프로 님이 등록 화면에서 작업 중」", whoB)
check("이 화면이 저절로 열립니다" in hB, "「끝나면 이 화면이 저절로 열립니다」 안내")
jb = beat(TB)
check(jb["held"] is False and jb["holder"].startswith("가영업") and "mgmt" not in jb, "나영업 신호: 못 잡음 · 다음 번호도 안 줌", jb)
as_(UA); ja = beat(TA)
check(ja["held"] and ja["waiters"] and ja["waiters"][0].startswith("나영업"), "가영업 화면에 「기다리는 분: 나영업 프로」", ja.get("waiters"))

print("§2 잡은 사람에게 다음 번호(저장 때와 같은 함수)")
check(ja["mgmt"] == "036T" + YYMM and ja["mgmt"] == D.generate_mgmt_code("T"), "다음 관리번호 = 036T%s(지금 035 까지)" % YYMM, ja.get("mgmt"))
check(ja["so"] == "T-%s-3" % TODAY6, "다음 수주번호 = T-%s-3(발주일 비면 오늘 · 오늘 2건 있음)" % TODAY6, ja.get("so"))
j2 = beat(TA, order_date="2026-12-01")
check(j2["so"] == "T-261201-1", "발주일 12-01 → T-261201-1", j2.get("so"))
j3 = beat(TA, po_type="추가")
check(j3["mgmt"] == "" and j3["so"], "추가 발주(PO≠신규)는 관리번호 미리보기 없음(기존 번호) · 수주번호만", j3)
j4 = beat(TA, manual=True)
check(j4["mgmt"] == "", "수동발행 켜면 관리번호 미리보기 없음", j4)
j5 = beat(TA, biz_div="M")
check(j5["mgmt"] == "011M" + YYMM, "자동화 탭 = 011M%s" % YYMM, j5.get("mgmt"))
j6 = beat(TA, biz_div="E", ptype="OTHER")
check(j6["mgmt"] == "001E" + YYMM and j6["so"].startswith("E-"), "기타 = 001E · E- 수주번호", j6)

print("§3 다른 사람 저장 막음 · 잡은 사람은 됨")
as_(UB)
r = q(cl.post, "/projects/new", data={"quick": "1", "lock_token": TB, "name": "X", "customer_name": "가상고객(주)", "biz_div": "T"})
loc = r.headers.get("location", "")
check(r.status_code == 303 and "error=reg_locked" in loc and "holder=" in loc, "나영업이 [등록] → 저장 안 함(reg_locked · 누가 잡았는지)", loc)
with D.db_session() as c:
    n = c.execute("SELECT COUNT(*) FROM projects WHERE name='X'").fetchone()[0]
check(n == 0, "프로젝트 안 생김")
check(M._z57_lock_other(UA, TA) == "" and M._z57_lock_other(UA, "") == "" and M._z57_lock_other(UB, TB).startswith("가영업"), "저장 확인: 가영업(잡은 사람·다른 탭 포함)은 통과 · 나영업은 막힘")
check("reg_locked:" in hA and "입력한 내용은 이 기기에 남아 있습니다" in hA, "화면의 오류 글(입력은 이 기기에 남음)")

print("§4 풀림 · 넘김")
as_(UA); q(cl.post, "/api/project-reg-lock/release", content='{"token":"%s"}' % TA, headers={"Content-Type": "application/json"})
as_(UB); jb = beat(TB)
check(jb["held"] and jb["mgmt"] == "036T" + YYMM, "가영업이 창을 닫으면(풀림) → 나영업 화면이 열리고 번호가 보임", jb)
as_(UA); ja = beat(TA)
check(ja["held"] is False and ja["holder"].startswith("나영업"), "이제 가영업은 기다림(나영업 작업 중)", ja)
lock_set(beat_at=0)
ja = beat(TA)
check(ja["held"], "나영업 신호가 75초 끊기면(창 닫힘·잠자기) 가영업이 잡음")
lock_set(active_at=1)   # 가영업 10분 넘게 입력 없음
as_(UB); jb = beat(TB)
check(jb["held"], "잡은 사람이 10분 넘게 입력이 없으면 기다리던 나영업에게 넘어감")
as_(UA); ja = beat(TA)
check(ja["held"] is False and ja["idle_min"] == 0, "가영업 화면은 다시 가림막(입력은 그대로 남음)", ja)
jb_inactive = None
as_(UB); jb_inactive = beat(TB, active=False)
lock_set(active_at=__import__("time").time() - 300)
as_(UA); ja = beat(TA)
check(ja["held"] is False and ja["idle_min"] == 5, "5분 무입력은 아직 안 넘어감 · 「마지막 입력 5분 전」", ja)

print("§5 같은 사람 다른 탭 · 권한")
as_(UB); _, TB2, cov2, _ = page()
check(TB2 and cov2, "같은 사람(나영업)이 다른 탭으로 열어도 열림")
as_(UC)
r = q(cl.post, "/api/project-reg-lock/beat", json={"token": "abcdefgh123"})
check(r.status_code == 403, "등록 권한 없는 사람은 잡을 수 없음")

print("§6 ⓘ 입력 기준")
as_(UA); h, _, _, _ = page()
check(len(re.findall(r'class="qf-gi" data-gk="(project_name|model_name|equip_name)"', h)) == 3, "프로젝트명·모델명·장비명 옆 ⓘ 3개")
r = q(cl.post, "/api/field-guides/model_name", json={"body": "고객사 제품 모델명 그대로\n여러 개면 쉼표(,) · 버전까지"})
j = r.json()
check(j.get("ok") and j["guide"]["by"].startswith("가영업") and j["guide"]["at"], "가영업이 모델명 기준 저장 · 고친 사람·시각", j)
as_(UB); h2, _, _, _ = page()
m = re.search(r"var FG=(\{.*?\}), CAN=", h2)
import json  # noqa: E402
fg = json.loads(m.group(1)) if m else {}
check(fg.get("model_name", {}).get("body", "").startswith("고객사 제품 모델명") and fg["model_name"]["by"].startswith("가영업"), "나영업 화면에도 같은 기준이 보임", fg.get("model_name"))
q(cl.post, "/api/field-guides/model_name", json={"body": "고객사 모델명 그대로 · 버전까지"})
hi = q(cl.get, "/api/field-guides/model_name/history").json()["items"]
check(len(hi) == 2 and hi[0]["by"].startswith("나영업") and hi[1]["by"].startswith("가영업"), "이력 2개(최근 먼저 · 누가)", [(x["by"], x["body"][:10]) for x in hi])
r = q(cl.post, "/api/field-guides/model_name", json={"body": "고객사 모델명 그대로 · 버전까지"})
check(r.json().get("same") and len(q(cl.get, "/api/field-guides/model_name/history").json()["items"]) == 2, "같은 글로 다시 저장하면 이력 안 늘어남")
ex = q(cl.get, "/api/field-guides/examples?key=model_name&biz=T").json()["items"]
check([x["v"] for x in ex] == ["VPL2133,2134-0126000", "VPL2132-0126000"] and ex[0]["mgmt"] == "034T" + YYMM, "최근 등록 예(검사기만 · 최근 먼저 · 관리번호)", ex)
ex2 = q(cl.get, "/api/field-guides/examples?key=equip_name&biz=M").json()["items"]
check([x["v"] for x in ex2] == ["AUTO TESTER HANDLER"], "자동화 탭은 자동화 예만", ex2)
as_(UC)
r = q(cl.post, "/api/field-guides/model_name", json={"body": "몰래"})
check(r.status_code == 403, "등록 권한 없는 사람은 기준을 못 고침")
check(q(cl.post, "/api/field-guides/nope", json={"body": "x"}).status_code in (400, 403), "정해진 세 칸 말고는 안 받음")
as_(UA)
with D.db_session() as c:
    pid0 = c.execute("SELECT id FROM projects WHERE mgmt_code=?", ("035T" + YYMM,)).fetchone()[0]
he = q(cl.get, "/projects/%d/quick-edit" % pid0).text
check(len(re.findall(r'class="qf-gi"', he)) == 3 and 'name="lock_token"' not in he and 'id="qLockCover"' not in he, "수정 화면에도 ⓘ · 수정은 잠그지 않음")

print()
print("결과: PASS %d / FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
