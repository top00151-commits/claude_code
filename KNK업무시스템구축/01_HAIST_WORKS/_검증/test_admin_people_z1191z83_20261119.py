# -*- coding: utf-8 -*-
"""z1191z83 2단계 시험 — 관리 화면 다시 짜기 (대표 2026-11-19)
  「관리 항목 … 관리자, 권한 위임 … 쓰기가 상당히 어려워 … 권한을 부여하고 넘기고 등록하고 새로 만들고 하는 실무 담당자 입장에서」
  대표 고름: 권한 넘기기 = 담당 교체 + 기간 맡기기 · 맡기는 동안 보낸 사람 권한 그대로 · 관리자 권한은 대표만.
  임시 DB · 가짜 자료 · 운영 아님
"""
import contextlib, io, json, os, re, sys, tempfile
from datetime import datetime, timedelta
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z83-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z83_")
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
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_vi", "TEXT"),
                     ("rank", "TEXT"), ("biz_divs", "TEXT")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    T1 = ins(c, "teams", {"name": "가상영업팀", "code": "T83A", "display_order": 1})
    T2 = ins(c, "teams", {"name": "가상구매팀", "code": "T83B", "display_order": 2})
    T3 = ins(c, "teams", {"name": "가상조립", "code": "V83C", "display_order": 3, "entity": "VN"})
    c.execute("INSERT INTO field_access_policy(category, team_id) VALUES('sales_amount', ?)", (T1,))
    c.execute("INSERT INTO field_access_policy(category, team_id) VALUES('purchase_price', ?)", (T2,))

    def user(nm, emp, team, role="member", **kw):
        row = dict(name=nm, role=role, employee_no=emp, login_id=emp, password="sso_only_no_local_password", is_active=1,
                   password_version=1, team_id=team, rank="프로", email=emp.lower() + "@example.test")
        row.update(kw)
        ins(c, "users", row)
        return dict(c.execute("SELECT * FROM users WHERE employee_no=?", (emp,)).fetchone())
    CEO = user("가대표", "T831", T1, "ceo", rank="대표이사")
    ADM = user("나관리", "T832", T2, "admin")
    ADM2 = user("다관리", "T833", T2, "admin")
    A = user("라영업", "T834", T1, can_view_sales=1, can_use_sales=1, biz_divs="T,M")
    B = user("마영업", "T835", T1)
    P = user("바구매", "T836", T2, can_view_logistics=1, can_use_logistics=1)
    V = user("사조립", "VN837", T3, entity="VN")
    L = user("아팀장", "T838", T2, "leader")

import app.main as M  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
import app.admin_people as AP  # noqa: E402
CUR = {"u": CEO}


def _gu(request):
    with D.db_session() as c:
        r = c.execute("SELECT u.*, t.name AS team_name FROM users u LEFT JOIN teams t ON t.id=u.team_id WHERE u.id=? AND u.is_active=1",
                      (CUR["u"]["id"],)).fetchone()
    return dict(r) if r else None


M.get_user = _gu
cl = TestClient(M.app, follow_redirects=False)

OK = FAIL = 0


def chk(cond, msg):
    global OK, FAIL
    if cond:
        OK += 1
        print("  [OK] " + msg)
    else:
        FAIL += 1
        print("  [FAIL] " + msg)


def U(uid):
    with D.db_session() as c:
        return dict(c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())


def snap(uid):
    r = U(uid)
    v = {f: (1 if r.get(f) else 0) for f in ("can_view_sales", "can_use_sales", "can_view_logistics", "can_use_logistics")}
    v.update({"biz_divs": ",".join(k for k in "TMLE" if k in (r.get("biz_divs") or "")), "role": r.get("role") or "member",
              "team_id": str(r.get("team_id") or ""), "is_active": 1 if r.get("is_active") else 0})
    return v


def save(uid, **chg):
    old = snap(uid)
    new = dict(old, **chg)
    return cl.post("/admin/staff/%d/save" % uid, json={"old": old, "new": new})


def hist(uid):
    with D.db_session() as c:
        return [dict(r) for r in c.execute("SELECT * FROM user_history WHERE user_id=? ORDER BY id", (uid,))]


print("§1 관리 홈 · 직원 목록 · 부서 — 대표·관리자만")
CUR["u"] = CEO
r = cl.get("/admin")
chk(r.status_code == 200 and "⚙️ <em>관리</em>" in r.text, "/admin = 새 관리 홈")
for s in ("👤 직원", "👥 부서", "🔁 권한 넘기기", "🏢 회사 설정", "🧰 점검·위험 도구", "최근 바뀐 권한", "/admin/fx-rates", "/admin/reset-demo", "/admin/console"):
    chk(s in r.text, "관리 홈에 「%s」" % s)
chk(r.text.index("🧰 점검·위험 도구") > r.text.index("최근 바뀐 권한") and "<details class=\"az-tools\">" in r.text, "위험 도구는 맨 아래 · 접어 둠")
chk(cl.get("/admin/console").status_code == 200, "예전 관리자 화면 = /admin/console 로 남음")
CUR["u"] = A
chk(cl.get("/admin").status_code == 303 and cl.get("/admin/staff").status_code == 303 and cl.get("/admin/handover").status_code == 303,
    "일반 직원은 관리 화면 못 들어옴")
chk(cl.post("/admin/staff/%d/save" % B["id"], json={"old": {}, "new": {}}).status_code == 401, "일반 직원은 저장도 못 함")
CUR["u"] = ADM
r = cl.get("/admin/staff")
chk(r.status_code == 200 and "라영업" in r.text and "사조립" in r.text and "가대표" in r.text, "관리자도 직원 목록(본사·법인 재직 전부)")
r = cl.get("/admin/staff?corp=vn")
chk("사조립" in r.text and "라영업" not in r.text, "법인 거르기 = 법인 사람만")
r = cl.get("/admin/staff?q=T834")
chk("라영업" in r.text and "마영업" not in r.text, "사번으로 찾기")
chk("매출 보기·수정" in cl.get("/admin/staff?q=라영업").text, "목록에 할 수 있는 것(매출 보기·수정)")   # z1191z200 (대표 11-28 권한 용어 통일 「권한 없음 / 보기 / 보기·수정」): 화면·이력 글자 「등록·편집」→「보기·수정」 · 저장값(can_use_*)은 그대로
r = cl.get("/admin/depts")
chk(r.status_code == 200 and "가상영업팀" in r.text and "매출금액" in r.text and "구매단가" in r.text, "부서 화면 = 부서별 민감 정보 보기 표시")

print("§2 직원 한 사람 — 할 수 있는 것이 한 장에")
r = cl.get("/admin/staff/%d" % A["id"])
t = r.text
chk(r.status_code == 200, "한 사람 화면 열림")
for s in ("매출영업센터", "자재구매센터", "담당 사업부", "민감 정보 보기", "부서 규칙 · 가상영업팀", "바뀐 기록", "○○○과 똑같이", "/admin/handover?frm=%d" % A["id"]):
    chk(s in t, "「%s」 보임" % s)
chk(re.search(r'data-k="can_use_sales" checked', t) is not None, "매출 등록·수정 켜짐(실제 값)")
chk(re.search(r'data-biz="T" checked', t) and re.search(r'data-biz="M" checked', t) and not re.search(r'data-biz="L" checked', t), "담당 사업부 검사기·자동화")
r = cl.get("/admin/staff/%d" % L["id"])
chk("팀장 역할로 항상 켜짐" in r.text, "팀장 = 보기 칸 「역할로 항상 켜짐」(잠금)")

print("§3 저장 — 바뀐 것만 · 기록 · 등록 켜면 보기도")
n0 = len(hist(B["id"]))
r = save(B["id"], can_use_sales=1, biz_divs="L")
j = r.json()
chk(j.get("ok") and j.get("n") == 3, "저장: 매출 보기·등록 + 사업부 = 3가지 · 실제 %s" % j)
b = U(B["id"])
chk(b["can_view_sales"] == 1 and b["can_use_sales"] == 1 and b["biz_divs"] == "L", "DB 에 그대로(등록 → 보기 자동)")
h = hist(B["id"])[n0:]
chk(len(h) == 3 and all(x["changed_by"] == ADM["id"] and x["note"] == "관리 화면" for x in h), "user_history 3줄 · 바꾼 사람 = 관리자")
chk(save(B["id"]).json().get("n") == 0, "안 바꾸고 저장 = 0가지")
r = save(B["id"], team_id=str(T2))
_h = hist(B["id"])[-1]
chk(r.json().get("ok") and U(B["id"])["team_id"] == T2 and (_h["field"], _h["old_value"], _h["new_value"]) == ("부서", "가상영업팀", "가상구매팀"), "부서 이동 · 기록에 부서 이름(번호 아님)")
old = snap(B["id"])
with D.db_session() as c:
    c.execute("UPDATE users SET can_view_logistics=1 WHERE id=?", (B["id"],))
r = cl.post("/admin/staff/%d/save" % B["id"], json={"old": old, "new": dict(old, can_use_sales=0)})
chk(r.status_code == 409 and U(B["id"])["can_use_sales"] == 1, "화면 연 뒤 남이 먼저 바꿨으면 멈춤(덮어쓰기 없음)")

print("§4 관리자 권한은 대표만 (대표 11-19)")
CUR["u"] = ADM
r = save(B["id"], role="admin")
chk(r.status_code == 403 and U(B["id"])["role"] == "member", "관리자가 직원을 관리자로 = 막힘")
r = save(ADM2["id"], role="member")
chk(r.status_code == 403 and U(ADM2["id"])["role"] == "admin", "관리자가 다른 관리자 빼기 = 막힘")
r = save(ADM2["id"], is_active=0)
chk(r.status_code == 403 and U(ADM2["id"])["is_active"] == 1, "관리자가 다른 관리자 잠금 = 막힘")
r = save(CEO["id"], can_use_logistics=1)
chk(r.status_code == 403, "관리자가 대표 계정 고치기 = 막힘")
chk("대표만 바꿀 수 있습니다" in cl.get("/admin/staff/%d" % CEO["id"]).text, "대표 계정 화면 = 보기만 안내")
r = save(B["id"], role="leader")
chk(r.json().get("ok") and U(B["id"])["role"] == "leader", "일반 직원 ↔ 팀장은 관리자도 됨")
save(B["id"], role="member")
r = save(ADM["id"], is_active=0)
chk(r.status_code == 403 and U(ADM["id"])["is_active"] == 1, "내 계정은 스스로 잠그지 못함")
r = save(ADM2["id"], can_use_logistics=1)
chk(r.json().get("ok"), "다른 관리자의 센터 칸은 관리자도 바꿀 수 있음(역할·잠금만 대표)")
# 예전 수정 화면도 같은 규칙
r = cl.post("/admin/users/%d/edit" % B["id"], data={"name": "마영업", "role": "admin", "login_id": "T835", "is_active": "1"})
chk(r.status_code == 303 and "error=ceo_only" in r.headers.get("location", "") and U(B["id"])["role"] == "member", "예전 수정 화면에서도 관리자 주기 막힘")
r = cl.post("/admin/users/%d/edit" % CEO["id"], data={"name": "가대표", "role": "ceo", "login_id": "T831", "is_active": "1"})
chk("error=ceo_only" in r.headers.get("location", ""), "예전 수정 화면에서도 대표 계정 고치기 막힘")
r = cl.post("/admin/users/%d/edit" % B["id"], data={"name": "마영업", "role": "member", "login_id": "T835", "is_active": "1", "team_id": str(T2)})
chk(r.headers.get("location") == "/admin/staff/%d" % B["id"], "예전 수정 화면 저장 뒤 → 그 사람 화면으로")
CUR["u"] = CEO
r = save(B["id"], role="admin")
chk(r.json().get("ok") and U(B["id"])["role"] == "admin", "대표는 관리자 줄 수 있음")
r = save(B["id"], role="member")
chk(r.json().get("ok") and U(B["id"])["role"] == "member", "대표는 관리자 뺄 수 있음")
r = save(CEO["id"], role="member")
chk(r.status_code == 403, "대표도 내 역할은 스스로 못 바꿈")
src = io.open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
chk('# is_admin 은 대표만 변경 가능' in src and 'if u["role"] == "ceo":\n                adm =' in src, "팀 화면의 관리자 표시도 대표만")

print("§5 「○○○과 똑같이」")
CUR["u"] = ADM
j = cl.get("/admin/staff/%d/like?src=%d" % (B["id"], A["id"])).json()
chk(j["ok"] and j["vals"] == {"can_view_sales": 1, "can_use_sales": 1, "can_view_logistics": 0, "can_use_logistics": 0, "biz_divs": "T,M"},
    "라영업 값 = 매출 보기·등록 · 검사기·자동화 · 실제 %s" % j.get("vals"))
chk("role" not in j["vals"], "역할은 복사 대상 아님")

print("§6 담당 교체")
CUR["u"] = ADM
pv = cl.post("/admin/handover/preview", json={"kind": "transfer", "from": P["id"], "to": V["id"], "items": ["can_use_logistics"], "remove": True}).json()
chk(pv["ok"] and pv["added"] == ["자재구매센터 보기", "자재구매센터 보기·수정"] and set(pv["removed"]) == {"자재구매센터 보기·수정"},
    "미리보기: 받는 사람 + 보기·등록 · 보낸 사람 − 등록 · 실제 %s" % pv)
pv = cl.post("/admin/handover/preview", json={"kind": "transfer", "from": P["id"], "to": V["id"], "items": ["can_use_sales"]}).json()
chk(not pv["ok"] and "없는 것" in pv["msg"], "보낸 사람에게 없는 것은 못 넘김")
pv = cl.post("/admin/handover/preview", json={"kind": "transfer", "from": P["id"], "to": P["id"], "items": ["can_use_logistics"]}).json()
chk(not pv["ok"], "같은 사람끼리 못 넘김")
r = cl.post("/admin/handover/apply", json={"kind": "transfer", "from": P["id"], "to": V["id"], "items": ["can_use_logistics"], "remove": True}).json()
chk(r["ok"], "담당 교체 적용 · %s" % r.get("msg"))
chk(U(V["id"])["can_use_logistics"] == 1 and U(V["id"])["can_view_logistics"] == 1, "받는 사람 자재 보기·등록 켜짐")
chk(U(P["id"])["can_use_logistics"] == 0 and U(P["id"])["can_view_logistics"] == 1, "보낸 사람 등록만 빠짐(보기는 남김)")
chk(any("담당 교체 바구매 → 사조립" in (x["note"] or "") for x in hist(V["id"])) and any("담당 교체" in (x["note"] or "") for x in hist(P["id"])), "두 사람 기록에 담당 교체")
with D.db_session() as c:
    chk(c.execute("SELECT COUNT(*) FROM perm_handover WHERE kind='transfer' AND status='done'").fetchone()[0] == 1, "넘기기 기록 1건")

print("§7 기간 맡기기 — 보낸 사람 그대로 · 더해진 것만 끝날 때 뺌")
CUR["u"] = ADM
with D.db_session() as c:
    c.execute("UPDATE users SET can_view_sales=1, can_use_sales=0, can_view_logistics=0, can_use_logistics=0, biz_divs='' WHERE id=?", (B["id"],))
now = M._kst_wall_now()
end1 = (now + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M")
r = cl.post("/admin/handover/apply", json={"kind": "delegate", "from": A["id"], "to": B["id"], "items": ["can_use_sales", "biz:T"], "ends": end1}).json()
quiet = M._nas_quiet_now()
chk(r["ok"], "맡기기 등록 · %s" % r.get("msg"))
b = U(B["id"])
if not quiet:
    chk(b["can_use_sales"] == 1 and (b["biz_divs"] or "") == "T", "지금부터 = 받은 사람에게 매출 등록·검사기 더해짐")
a = U(A["id"])
chk(a["can_use_sales"] == 1 and a["biz_divs"] == "T,M", "보낸 사람 권한 그대로(대표 고름)")
with D.db_session() as c:
    g = dict(c.execute("SELECT * FROM perm_handover WHERE kind='delegate' ORDER BY id DESC LIMIT 1").fetchone())
if not quiet:
    chk(g["status"] == "active" and set(json.loads(g["added_json"])) == {"can_use_sales", "biz:T"}, "더해진 것 = 등록·검사기(보기는 원래 있어 안 더함) · %s" % g["added_json"])
chk(cl.post("/admin/handover/apply", json={"kind": "delegate", "from": A["id"], "to": B["id"], "items": ["can_use_sales"],
                                            "ends": (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")}).json()["ok"] is False, "끝나는 때가 지난 시각이면 막힘")
r = cl.get("/admin/handover")
chk("지금 맡겨 둔 것" in r.text and "라영업 → <b>마영업</b>" in r.text, "맡겨 둔 목록에 보임")
chk("진행 중인 맡기기" in cl.get("/admin/staff/%d" % B["id"]).text, "받은 사람 화면에도 진행 중 표시")
# 끝나는 시각이 지나면 — 페이지를 열 때(5분 타이머와 같은 run_due) 처리
with D.db_session() as c:
    c.execute("UPDATE perm_handover SET ends_at=? WHERE id=?", ((now - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M"), g["id"]))
r = cl.get("/admin/handover")   # 페이지를 열면 끝난 맡기기를 처리한다(5분 타이머와 같은 함수)
b = U(B["id"])
if not quiet:
    chk(b["can_use_sales"] == 0 and (b["biz_divs"] or "") == "" and b["can_view_sales"] == 1, "끝남 → 더해진 것만 빠짐 · 원래 있던 매출 보기는 남음")
    with D.db_session() as c:
        chk(c.execute("SELECT status, end_note FROM perm_handover WHERE id=?", (g["id"],)).fetchone()[0] == "ended", "상태 = 끝남(기간 끝)")
    chk(any("기간 맡기기 끝" in (x["note"] or "") for x in hist(B["id"])), "기록에 「기간 맡기기 끝」")
chk(U(A["id"])["can_use_sales"] == 1, "끝나도 보낸 사람 권한 그대로")
# 일찍 끝내기 + 겹친 맡기기
r1 = cl.post("/admin/handover/apply", json={"kind": "delegate", "from": A["id"], "to": B["id"], "items": ["can_use_sales"], "ends": end1}).json()
with D.db_session() as c:
    P2 = ins(c, "users", dict(name="자영업", role="member", employee_no="T839", login_id="T839", password="x", is_active=1, team_id=T1, can_view_sales=1, can_use_sales=1))
r2 = cl.post("/admin/handover/apply", json={"kind": "delegate", "from": P2, "to": B["id"], "items": ["can_use_sales"], "ends": end1}).json()
with D.db_session() as c:
    ids = [x[0] for x in c.execute("SELECT id FROM perm_handover WHERE kind='delegate' AND status='active' ORDER BY id")]
if not quiet:
    chk(len(ids) == 2, "같은 사람에게 맡기기 두 건 진행 중")
    e = cl.post("/admin/handover/%d/end" % ids[0]).json()
    chk(e["ok"] and U(B["id"])["can_use_sales"] == 1, "첫째를 일찍 끝내도 둘째가 같은 칸을 맡기고 있어 남음 · %s" % e.get("msg"))
    with D.db_session() as c:
        chk("can_use_sales" in json.loads(c.execute("SELECT added_json FROM perm_handover WHERE id=?", (ids[1],)).fetchone()[0]),
            "그 칸은 둘째 몫으로 옮겨짐(둘째가 끝날 때 빠지게)")
    e2 = cl.post("/admin/handover/%d/end" % ids[1]).json()
    chk(e2["ok"] and "1가지" in e2["msg"] and U(B["id"])["can_use_sales"] == 0, "둘째 끝냄 → 등록 빠짐 · %s" % e2.get("msg"))
    chk(not cl.post("/admin/handover/%d/end" % ids[1]).json()["ok"], "이미 끝난 것은 다시 못 끝냄")
# 시작 전 맡기기 · 취소
st = (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
r = cl.post("/admin/handover/apply", json={"kind": "delegate", "from": A["id"], "to": B["id"], "items": ["can_use_sales"], "starts": st, "ends": end1}).json()
chk(r["ok"] and "부터" in r["msg"] and U(B["id"])["can_use_sales"] == 0, "내일 시작 = 지금은 안 더함")
with D.db_session() as c:
    pid = c.execute("SELECT id FROM perm_handover WHERE status='pending'").fetchone()[0]
chk(cl.post("/admin/handover/%d/end" % pid).json()["ok"] and U(B["id"])["can_use_sales"] == 0, "시작 전 취소")

print("§8 NAS 백업 시간(월 02:00~07:30)엔 미룸")
src = io.open(os.path.join(ROOT, "app", "admin_people.py"), encoding="utf-8").read()
chk("if nas_quiet():\n            return {\"skipped\": \"nas_quiet\"}" in src, "run_due 맨 앞에서 백업 시간이면 아무것도 안 함")
chk('"nas_quiet": _nas_quiet_now' in io.open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read(), "main.py 의 같은 백업 시간 판정을 씀")

print("§9 왼쪽 메뉴 — 관리 묶음 = 「⚙️ 관리」 하나")
from app.i18n import get_all_translations  # noqa
chk(get_all_translations("ko")["ch_m_admin"] == "⚙️ 관리", "메뉴 이름 = ⚙️ 관리")
ch = io.open(os.path.join(ROOT, "app", "templates", "_v5_partials", "chrome.html"), encoding="utf-8").read()
blk = ch[ch.index("<div class=\"sb-group\">{{ i.ch_g_admin }}</div>"):ch.index('<details class="sb-fold"')]
chk(re.findall(r"a\('(/admin[^']*)'", blk) == ["/admin"], "관리 묶음 메뉴 = /admin 하나 · 실제 %s" % re.findall(r"a\('(/admin[^']*)'", blk))
for p in ("/admin/fx-rates", "/admin/ai-settings", "/admin/reset-demo", "/admin/test-data", "/admin/permissions"):
    chk(cl.get(p).status_code in (200, 303, 307), "주소 %s 는 그대로 열림(메뉴만 옮김)" % p)

print("\n결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
