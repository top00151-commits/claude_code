# -*- coding: utf-8 -*-
"""z1191z200 권한 용어 통일(대표 2026-11-28 결정 「권한 없음 / 보기 / 보기·수정」) — 시험 사본(임시 DB · 가상 직원 · 운영 DB 아님)
   §1 관리 화면 8곳을 관리자(267)·대표(85)로 열어 옛 말(열람 권한·열람 허용·등록·편집·등록·수정·보기·등록·읽기 전용·VIEW·R/W·쓰기 권한·편집 권한)이
      화면에 없고 새 말(보기·수정 · 민감 정보 보기 권한 · 부서별 보기 권한)이 있는지
   §2 권한 저장 세 길(여러 명 한꺼번에 · 한 사람 화면 · 부서별 민감 정보) — 저장값(can_*·field_access_policy)이 바뀐 글자와 상관없이 같은지
      · Z200_OUT 에 저장값을 적어 두면 원래 판(W199)과 이 판(W200)의 저장값을 그대로 비교할 수 있다
   §3 업무 화면 🔒 안내(수주·프로젝트·수출 서류·찾아가는 길) 원본 글자 — 「열람 권한자만」이 없고 「보기 권한이 있는 분만」이 있는지
   원래 판에서 돌리기: Z200_ROOT=<W199 의 01_HAIST_WORKS> 로 주면 그 판의 app 을 읽는다(§1·§3 이 실패해야 정상)."""
import contextlib, io, json, os, re, sys, tempfile
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
ROOT = os.environ.get("Z200_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z200-test-only-not-a-real-key"   # 시험용 가짜 값
import app.database as D   # noqa: E402
assert os.path.abspath(D.__file__).startswith(os.path.abspath(ROOT)), D.__file__
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(tempfile.mkdtemp(prefix="knk_z200_"), "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
OK = FAIL = 0


def check(cond, msg, got=None):
    global OK, FAIL
    if cond:
        OK += 1; print("  ✅", msg)
    else:
        FAIL += 1; print("  ❌", msg, " ←", got)


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
    T1 = ins(c, "teams", {"name": "가상영업팀", "code": "T200A", "display_order": 1})
    T2 = ins(c, "teams", {"name": "가상구매팀", "code": "T200B", "display_order": 2})

    def user(uid, nm, emp, team, role="member", **kw):
        row = dict(id=uid, name=nm, role=role, employee_no=emp, login_id=emp, password="sso_only_no_local_password", is_active=1,
                   password_version=1, team_id=team, rank="프로", email=emp.lower() + "@example.test")
        row.update(kw)
        ins(c, "users", row)
        return dict(c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())
    CEO = user(85, "가상대표", "T2085", T1, "ceo", rank="대표이사")
    ADM = user(267, "가상관리자", "T20267", T2, "admin")
    A = user(901, "가상영업", "T20901", T1, can_view_sales=1, can_use_sales=1, biz_divs="T")
    B = user(902, "가상직원", "T20902", T1)
    P = user(903, "가상구매", "T20903", T2, can_view_logistics=1)

import app.main as M   # noqa: E402
from fastapi.testclient import TestClient   # noqa: E402
CUR = {"u": ADM}


def _gu(request):
    with D.db_session() as c:
        r = c.execute("SELECT u.*, t.name AS team_name FROM users u LEFT JOIN teams t ON t.id=u.team_id WHERE u.id=? AND u.is_active=1",
                      (CUR["u"]["id"],)).fetchone()
    return dict(r) if r else None


M.get_user = _gu
cl = TestClient(M.app, follow_redirects=False)

OLD = ("열람 권한", "열람 허용", "열람권한", "등록·편집", "등록·수정", "보기·등록", "읽기 전용", "읽기전용", "R/W", "쓰기 권한", "편집 권한", "VIEW")


def visible(html):
    """화면에 나오는 글 + 화면 스크립트가 보여 주는 글(LBL 사전·안내 문구) — <style> · HTML 주석 · 스크립트 주석(개발 메모 · 화면에 안 나옴)만 뺀다."""
    h = re.sub(r"<style\b.*?</style>", "", html, flags=re.S | re.I)
    h = re.sub(r"<!--.*?-->", "", h, flags=re.S)

    def _js(m):
        b = re.sub(r"/\*.*?\*/", "", m.group(0), flags=re.S)
        return re.sub(r"(^|[\s;{}])//[^\n]*", r"\1", b)   # 줄 주석(앞이 빈칸·; 일 때만 — 'http://' 는 그대로)
    return re.sub(r"<script\b.*?</script>", _js, h, flags=re.S | re.I)


PAGES = [
    ("/admin", ("민감 정보 보기 권한",)),
    ("/admin/console", ("민감 정보 보기 권한",)),
    ("/admin/field-access", ("민감 정보 보기 권한", "부서별 보기 권한")),
    ("/admin/users/perms", ("보기·수정", "<b>보기·수정</b>을 켜면 <b>보기</b>도 켜집니다", "can_use_sales:'매출·영업 보기·수정'")),
    ("/admin/staff?q=가상영업", ("매출 보기·수정",)),
    ("/admin/staff/%d" % A["id"], ("보기·수정", "센터 보기·수정 칸과", "can_use_sales:'매출 보기·수정'")),
    ("/admin/users/%d/edit" % A["id"], ("매출·영업 <b>보기·수정</b>", "자재·구매 <b>보기·수정</b>")),
    ("/admin/handover", ("센터 보기·수정 칸",)),
]

print("§1 관리 화면 — 옛 말 없음 · 새 말 있음 (관리자 267 · 대표 85)")
for who, uu in (("관리자267", ADM), ("대표85", CEO)):
    CUR["u"] = uu
    for path, news in PAGES:
        r = cl.get(path)
        t = visible(r.text) if r.status_code == 200 else ""
        olds = [w for w in OLD if w in t]
        miss = [w for w in news if w not in t]
        check(r.status_code == 200 and not olds and not miss,
              "%s %s 열림 · 옛 말 없음 · 새 말 %d개 있음" % (who, path, len(news)),
              {"status": r.status_code, "옛말": olds, "없는 새말": miss})

print("§2 권한 저장 — 저장값은 글자와 상관없이 같다")
CUR["u"] = ADM
OUT = {}


def U(uid):
    with D.db_session() as c:
        return dict(c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())


def flags(uid):
    r = U(uid)
    return {f: (1 if r.get(f) else 0) for f in ("can_view_sales", "can_use_sales", "can_view_logistics", "can_use_logistics")}


def hist(uid):
    with D.db_session() as c:
        return [(r["field"], r["old_value"], r["new_value"]) for r in c.execute(
            "SELECT field, old_value, new_value FROM user_history WHERE user_id=? ORDER BY id", (uid,))]


# ① 여러 명 한꺼번에(/admin/users/perms) — 가상직원 매출 보기·수정 끔 → 켬(보기도 함께 켜져야)
r = cl.post("/admin/users/perms", json={"changes": [{"id": B["id"], "f": "can_use_sales", "old": 0, "new": 1}]})
j = r.json() if r.status_code == 200 else {}
fb = flags(B["id"])
check(j.get("ok") and fb == {"can_view_sales": 1, "can_use_sales": 1, "can_view_logistics": 0, "can_use_logistics": 0},
      "여러 명 한꺼번에 저장 — can_use_sales=1 · can_view_sales=1(보기 자동) · 자재 0", (r.status_code, j, fb))
hb = hist(B["id"])
check(("매출·영업 보기·수정", "끔", "켬") in hb, "변경 이력 칸 이름 = 「매출·영업 보기·수정」(화면 글자와 같음)", hb)
OUT["bulk"] = fb

# ② 한 사람 화면(/admin/staff/{id}/save) — 가상구매 자재 보기·수정 켬
def snap(uid):
    r = U(uid)
    v = flags(uid)
    v.update({"biz_divs": ",".join(k for k in "TMLE" if k in (r.get("biz_divs") or "")), "role": r.get("role") or "member",
              "team_id": str(r.get("team_id") or ""), "is_active": 1 if r.get("is_active") else 0})
    return v


old = snap(P["id"])
r = cl.post("/admin/staff/%d/save" % P["id"], json={"old": old, "new": dict(old, can_use_logistics=1)})
j = r.json() if r.status_code == 200 else {}
fp = flags(P["id"])
check(j.get("ok") and fp == {"can_view_sales": 0, "can_use_sales": 0, "can_view_logistics": 1, "can_use_logistics": 1},
      "한 사람 화면 저장 — can_use_logistics=1 · can_view_logistics=1 · 매출 0", (r.status_code, j, fp))
hp = hist(P["id"])
check(any(f == "자재구매센터 보기·수정" and nv == "켬" for f, _o, nv in hp), "변경 이력 칸 이름 = 「자재구매센터 보기·수정」", hp)
OUT["person"] = fp

# ③ 부서별 민감 정보(/admin/field-access) — 영업팀 매출금액 · 구매팀 구매단가·구매처
r = cl.post("/admin/field-access", data={"fa__sales_amount__%d" % T1: "1", "fa__purchase_price__%d" % T2: "1",
                                         "fa__supplier_info__%d" % T2: "1"})
with D.db_session() as c:
    pol = sorted([r_[0], r_[1]] for r_ in c.execute("SELECT category, team_id FROM field_access_policy"))
want = sorted([["sales_amount", T1], ["purchase_price", T2], ["supplier_info", T2]])
check(r.status_code == 303 and pol == want, "부서별 보기 권한 저장 — field_access_policy 3줄 그대로", (r.status_code, pol))
r2 = cl.get("/admin/field-access?saved=1")
check("바뀐 보기 권한이 반영됩니다" in r2.text, "저장 뒤 안내 = 「바뀐 보기 권한이 반영됩니다」")
OUT["policy"] = [[c_, ("T1" if t_ == T1 else "T2")] for c_, t_ in pol]

# ④ 대표 계정은 관리자가 못 바꿈(판정 그대로) — 403 · 값 그대로
oc = snap(CEO["id"])
r = cl.post("/admin/staff/%d/save" % CEO["id"], json={"old": oc, "new": dict(oc, can_use_sales=1)})
check(r.status_code == 403 and flags(CEO["id"]) == {k: oc[k] for k in flags(CEO["id"])}, "대표 계정 = 관리자 저장 403 · 값 그대로(판정 코드 안 건드림)",
      (r.status_code, r.text[:80]))
OUT["ceo_after_admin_try"] = flags(CEO["id"])

if os.environ.get("Z200_OUT"):
    with io.open(os.environ["Z200_OUT"], "w", encoding="utf-8") as f:
        json.dump(OUT, f, ensure_ascii=False, sort_keys=True, indent=1)
    print("  (저장값 적음 →", os.environ["Z200_OUT"], ")")

print("§3 업무 화면 🔒 안내 원본 글자")
TPL = os.path.join(ROOT, "app", "templates")
for rel, new in (("sales_order_detail.html", "매출금액은 보기 권한이 있는 분만 보입니다"),
                 ("project_detail.html", "매출금액은 보기 권한이 있는 분만 보입니다"),
                 ("project_detail.html", "※ 보기 권한(영업/기술)이 있어야 보입니다."),
                 ("project_detail.html", "작업일정표는 매출 보기 권한이 있는 분만 열 수 있습니다"),
                 ("consumable_prod_request.html", "작업일정표는 매출 보기 권한이 있는 분만 열 수 있습니다"),
                 ("dept_schedule.html", "작업일정표는 매출 보기 권한이 있는 분만 열 수 있습니다"),
                 ("prod_request_edit.html", "작업일정표는 매출 보기 권한이 있는 분만 열 수 있습니다"),
                 ("export_doc_pick.html", "매출 금액 보기 권한이 있는 분만 보입니다"),
                 (os.path.join("_v5_partials", "page_path_guide.html"), "※ 보기 권한이 있어야 보입니다.")):
    s = io.open(os.path.join(TPL, rel), encoding="utf-8").read()
    s_nc = re.sub(r"\{#.*?#\}", "", s, flags=re.S)   # Jinja 주석(개발 메모)은 화면에 안 나온다
    check(new in s_nc and "열람 권한" not in s_nc,
          "%s — 「%s」 있음 · 「열람 권한」 안내 없음" % (rel, new))

print("\n결과: %d 통과 / %d 실패" % (OK, FAIL))
sys.exit(0 if FAIL == 0 else 1)
