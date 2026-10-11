# -*- coding: utf-8 -*-
"""z1155 시험 — 사람마다의 WORKS 화면 언어 = 이음 메신저에서 고른 언어(직원 동기화) · 한국어·베트남어.

대표 지시(2026-10-10): 「웍스에는 기본적으로 한국어, 베트남어 적용을 해줘... 사용자 설정은 이음메신저에서
  직원동기화할때 이음메신저 선택 언어로 동일하게 개인별 적용하면 됨」 · 「내 프로필」은 「이음 따름 표시만」.
발단(세션 16 지시서): 「내 프로필」 언어 칸에 베트남어가 없어, 베트남어(vi)인 사람이 이메일만 고쳐 저장해도
  말없이 한국어로 바뀌었다.

실행: python _검증/test_user_lang_z1155_20261011.py      (기본 python 3.12 로 된다 — fastapi 불필요)
      화면·주소(route)까지는 test_user_lang_z1155_e2e_20261011.py (fastapi 있는 파이썬)

§1 기준 한 곳(i18n)            — 실제 모듈을 불러 값으로 확인
§2 upsert_user_from_payload    — 진짜 함수 · 운영과 같은 모양의 표(메모리 DB)
§3 _sync_employees_core        — 미리보기(되돌림)·두 번 돌려도 같음·이음이 언어를 안 보낼 때
§4 이음 명부 받는 두 창구       — 진짜 함수 · 이음 응답만 가짜(httpx.get 바꿔치기)
§5 배포 전 검사기               — 지금 코드 통과 + 옛 모양으로 되돌린 11가지를 전부 잡는가
"""
import contextlib
import io
import os
import shutil
import sqlite3
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "deploy"))
os.environ["KNK_SSO_SERVICE_KEY"] = "z1155-test-only-not-a-real-key"   # 시험용 가짜 값

from app import i18n                 # noqa: E402
from app import sso_client as SC     # noqa: E402
import check_standards as CS         # noqa: E402

OK = FAIL = 0


def check(cond, what):
    global OK, FAIL
    if cond:
        OK += 1
        print("  ✅", what)
    else:
        FAIL += 1
        print("  ❌", what)


# 운영 표 구조 그대로(2026-10-11 운영 DB 를 읽기 전용으로 열어 CREATE 문만 확인 — users 28칸)
USERS_SQL = """CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    login_id TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    email TEXT,
    team_id INTEGER REFERENCES teams(id),
    rank TEXT,
    role TEXT DEFAULT 'member',
    is_active INTEGER DEFAULT 1,
    lang TEXT DEFAULT 'ko',
    created_at TEXT DEFAULT (datetime('now','localtime'))
, can_use_logistics INTEGER DEFAULT 0, is_admin INTEGER DEFAULT 0, can_use_sales INTEGER DEFAULT 0, can_edit_changes INTEGER DEFAULT 0, can_close_tickets INTEGER DEFAULT 0, can_view_sales INTEGER DEFAULT 0, can_view_logistics INTEGER DEFAULT 0, can_use_quality INTEGER DEFAULT 0, employee_no TEXT, entity TEXT, password_version INTEGER DEFAULT 1, name_en TEXT, name_vi TEXT, phone TEXT, dept_code TEXT, must_change_pw INTEGER DEFAULT 0, biz_divs TEXT DEFAULT '')"""
TEAMS_SQL = """CREATE TABLE teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    leader_id INTEGER,
    is_lab INTEGER DEFAULT 0,
    sector TEXT,
    parent_team_id INTEGER REFERENCES teams(id),
    display_order INTEGER DEFAULT 0
, entity TEXT)"""
NOTIF_SQL = """CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    link TEXT,
    task_id INTEGER,
    comment_id INTEGER,
    is_read INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now','localtime'))
, prod_prid INTEGER, is_revision INTEGER DEFAULT 0, superseded INTEGER DEFAULT 0, card_json TEXT, revision_note TEXT)"""

SEED = [
    # name, login_id, employee_no, lang, entity, role
    ("가법인장", "VN001", "VN001", "vi", "VN", "member"),     # 한국 직원인데 vi 로 들어가 있던 모양(실측 5명)
    ("나베트남", "VN265", "VN265", "ko", None, "member"),     # 베트남 직원인데 법인 칸이 비어 ko 로 들어간 모양(실측 26명)
    ("다본사", "101", "101", "ko", "KOR", "member"),
    ("라널", "102", "102", None, "KOR", "member"),            # lang 이 비어 있는 사람
    ("마레거시", "legacy_ma", None, "ko", None, "member"),    # 사번 없는 옛 계정(이름으로 병합되는 길)
    ("바관리", "100", "100", "ko", "KOR", "admin"),
    ("사베트남", "VN266", "VN266", "vi", "VN", "member"),
]


def mkdb():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute(USERS_SQL)
    c.execute(TEAMS_SQL)
    c.execute(NOTIF_SQL)
    for name, lid, eno, lang, ent, role in SEED:
        c.execute("INSERT INTO users(name, login_id, password, employee_no, lang, entity, role, email, phone) "
                  "VALUES(?,?,?,?,?,?,?,?,?)",
                  (name, lid, "x", eno, lang, ent, role, lid + "@t.test", "010-0000-" + lid[-4:].rjust(4, "0")))
    c.commit()
    return c


def lang_of(c, eno=None, name=None):
    if eno is not None:
        r = c.execute("SELECT lang FROM users WHERE employee_no=?", (eno,)).fetchone()
    else:
        r = c.execute("SELECT lang FROM users WHERE name=?", (name,)).fetchone()
    return r["lang"] if r else "(없음)"


def row_of(c, eno):
    r = c.execute("SELECT * FROM users WHERE employee_no=?", (eno,)).fetchone()
    return dict(r) if r else None


def pl(eno, name, lang="__absent__", **kw):
    d = {"sub": eno, "employee_no": eno, "name_kr": name}
    if lang != "__absent__":
        d["lang"] = lang
    d.update(kw)
    return d


# ════════════════════════════════════════════════════════════════════
print("\n§1 기준 한 곳 — app/i18n.py")
check(getattr(i18n, "USER_LANGS", None) == ("ko", "vi"), "USER_LANGS = (ko, vi) — 대표 결정 「한국어·베트남어」")
check(set(i18n.LANGS) == {"ko", "vi", "en"}, "LANGS(번역 사전·견적서 인쇄용 ko·vi·en)는 그대로")
f = i18n.user_lang_from_messenger
for v, want in [(None, None), ("", None), ("  ", None), ("ko", "ko"), ("vi", "vi"), ("VI", "vi"),
                (" vi ", "vi"), ("en", "ko"), ("zh", "ko"), ("xx", "ko")]:
    check(f(v) == want, "user_lang_from_messenger(%r) = %r" % (v, want))
lab = i18n.user_lang_label
check(lab("ko") == "한국어" and lab("vi") == "Tiếng Việt", "user_lang_label: ko→한국어 · vi→Tiếng Việt")
check(lab(None) == "한국어" and lab("") == "한국어", "user_lang_label: 비어 있으면 한국어(화면도 한국어)")
check(lab("zh") == "zh (목록에 없음 · 화면은 한국어)", "user_lang_label: 목록 밖 값은 숨기지 않고 그대로 보여 준다")

# ════════════════════════════════════════════════════════════════════
print("\n§2 upsert_user_from_payload — 진짜 함수 · 운영 모양 표")
c = mkdb()
before_101 = row_of(c, "101")
ch = []
SC.upsert_user_from_payload(c, pl("VN001", "가법인장", "ko"), lang_changes=ch)
check(lang_of(c, "VN001") == "ko", "이음 ko → WORKS vi 였던 사람이 ko 로")
check(ch == [{"id": row_of(c, "VN001")["id"], "employee_no": "VN001", "name": "가법인장", "old": "vi", "new": "ko"}],
      "바뀐 사람이 {id·사번·이름·old vi·new ko} 로 남는다")
ch = []
SC.upsert_user_from_payload(c, pl("VN265", "나베트남", "vi"), lang_changes=ch)
check(lang_of(c, "VN265") == "vi" and len(ch) == 1 and ch[0]["old"] == "ko" and ch[0]["new"] == "vi",
      "이음 vi → WORKS ko 였던 베트남 직원이 vi 로 · 기록 1건")
ch = []
SC.upsert_user_from_payload(c, pl("101", "다본사", "ko"), lang_changes=ch)
check(lang_of(c, "101") == "ko" and ch == [], "같은 값(ko→ko)이면 기록에 안 남는다")
after_101 = row_of(c, "101")
check({k: v for k, v in before_101.items() if k != "lang"} == {k: v for k, v in after_101.items() if k != "lang"},
      "언어 말고 다른 칸은 그대로(payload 에 없는 칸은 COALESCE 로 보존)")
for absent, what in [("__absent__", "lang 칸 자체가 없다(지금 이음)"), (None, "lang=None"), ("", "lang=빈 값")]:
    ch = []
    SC.upsert_user_from_payload(c, pl("VN266", "사베트남", absent), lang_changes=ch)
    check(lang_of(c, "VN266") == "vi" and ch == [], "이음이 언어를 안 보냄(%s) → 손대지 않는다(vi 그대로)" % what)
ch = []
SC.upsert_user_from_payload(c, pl("VN266", "사베트남", "en"), lang_changes=ch)
check(lang_of(c, "VN266") == "ko" and ch and ch[0]["new"] == "ko", "이음 en(목록 밖) → 한국어로")
SC.upsert_user_from_payload(c, pl("VN266", "사베트남", "vi"))
ch = []
SC.upsert_user_from_payload(c, pl("VN266", "사베트남", "zh"), lang_changes=ch)
check(lang_of(c, "VN266") == "ko" and ch and ch[0]["old"] == "vi", "이음 zh(목록 밖) → 한국어로 · old vi 로 기록")
ch = []
SC.upsert_user_from_payload(c, pl("102", "라널", "ko"), lang_changes=ch)
check(lang_of(c, "102") == "ko" and ch == [], "WORKS 값이 비어 있던 사람 + 이음 ko → ko 로 채우되 「바뀜」은 아님(비어 있음=한국어)")
ch = []
SC.upsert_user_from_payload(c, pl("102", "라널", "vi"), lang_changes=ch)
check(lang_of(c, "102") == "vi" and ch and ch[0]["old"] == "ko", "그 사람이 이음에서 vi 로 바꾸면 WORKS 도 vi")
SC.upsert_user_from_payload(c, pl("VN001", "가법인장", "vi"))      # lang_changes 없이(SSO 로그인 길)
check(lang_of(c, "VN001") == "vi", "lang_changes 를 안 주는 길(SSO 로그인)도 오류 없이 반영")
# 새 직원
SC.upsert_user_from_payload(c, pl("VN999", "새베트남", "vi"))
check(lang_of(c, "VN999") == "vi", "새 직원 + 이음 vi(법인 칸 없음) → vi (예전엔 법인 칸이 비면 ko)")
SC.upsert_user_from_payload(c, pl("K997", "새본사", "ko", entity="VN"))
check(lang_of(c, "K997") == "ko", "새 직원 + 이음 ko → 법인이 VN 이어도 이음 값(ko)")
SC.upsert_user_from_payload(c, pl("VN998", "새법인", entity="VN"))
check(lang_of(c, "VN998") == "vi", "새 직원 + 이음이 언어를 안 보냄 + 법인 VN → 예전처럼 vi")
SC.upsert_user_from_payload(c, pl("K996", "새직원"))
check(lang_of(c, "K996") == "ko", "새 직원 + 이음이 언어를 안 보냄 + 법인 없음 → 예전처럼 ko")
# 사번 없는 옛 계정이 이름으로 병합되는 길
ch = []
SC.upsert_user_from_payload(c, pl("103", "마레거시", "vi"), lang_changes=ch)
check(lang_of(c, "103") == "vi" and ch and ch[0]["employee_no"] == "103", "이름으로 병합되는 옛 계정도 이음 언어로 · 기록")
check(SC.upsert_user_from_payload(c, pl("zz_bot", "봇", "vi")) is None, "봇·시스템 계정(zz*)은 예전처럼 건너뜀")

# ════════════════════════════════════════════════════════════════════
print("\n§3 _sync_employees_core — 동기화 코어(관리자 화면·새벽 자동이 같이 쓴다)")
c = mkdb()
PAY = [pl(eno, name, lg) for eno, name, lg in [
    ("VN001", "가법인장", "ko"), ("VN265", "나베트남", "vi"), ("101", "다본사", "ko"), ("102", "라널", "ko"),
    ("100", "바관리", "ko"), ("VN266", "사베트남", "vi")]]
PAY.append(pl("103", "마레거시", "ko"))
res = SC._sync_employees_core(c, PAY, do_remove=False)
got = sorted((x["employee_no"], x["old"], x["new"]) for x in res.get("lang_changed", []))
check(got == [("VN001", "vi", "ko"), ("VN265", "ko", "vi")], "바뀌는 사람 = 정확히 둘(VN001 vi→ko · VN265 ko→vi): %s" % got)
check(res["updated"] == 7 and res["inserted"] == 0, "갱신·신규 세는 법은 예전 그대로(갱신 7 · 신규 0)")
c.rollback()                                 # 관리자 화면 「미리보기」 = 돌린 뒤 되돌림
check(lang_of(c, "VN001") == "vi" and lang_of(c, "VN265") == "ko", "미리보기(되돌림) 뒤 DB 는 그대로 — 화면엔 명단만")
res = SC._sync_employees_core(c, PAY, do_remove=False)
c.commit()
check(lang_of(c, "VN001") == "ko" and lang_of(c, "VN265") == "vi", "적용(commit)하면 바뀐다")
res2 = SC._sync_employees_core(c, PAY, do_remove=False)
check(res2.get("lang_changed") == [], "두 번 돌려도 같다 — 두 번째엔 바뀌는 사람 0")
c2 = mkdb()
before = {r["id"]: r["lang"] for r in c2.execute("SELECT id, lang FROM users")}   # id 로 짝 — 옛 계정은 동기화 때 사번을 받는다
res3 = SC._sync_employees_core(c2, [pl(p["sub"], p["name_kr"]) for p in PAY], do_remove=False)
after = {r["id"]: r["lang"] for r in c2.execute("SELECT id, lang FROM users")}
check(res3.get("lang_changed") == [] and before == after,
      "이음이 아직 언어를 안 보내면(지금 상태) 아무도 안 바뀐다 → WORKS 를 먼저 배포해도 안전")
c3 = mkdb()
res4 = SC._sync_employees_core(c3, PAY[:-1] + [pl("VN777", "새사람", "vi")], do_remove=True)
check([w["employee_no"] for w in res4["removed"]] == [] or all(w["employee_no"] not in [x["employee_no"] for x in res4["lang_changed"]] for w in res4["removed"]),
      "명부에 없는 사람 지우기(z1092)와 언어 기록이 섞이지 않는다")
check(lang_of(c3, "VN777") == "vi" and all(x["employee_no"] != "VN777" for x in res4["lang_changed"]),
      "새로 들어온 사람은 이음 언어로 만들어지고 「바뀜」 명단엔 안 들어간다")

# ════════════════════════════════════════════════════════════════════
print("\n§4 이음 명부를 받는 두 창구 — 진짜 함수 · 이음 응답만 가짜")


class FakeResp:
    def __init__(self, users):
        self.status_code = 200
        self._j = {"users": users, "count": len(users), "source": "knk-messenger"}

    def json(self):
        return self._j


def dir_user(eno, name, lang="__absent__", **kw):
    u = {"employee_no": eno, "name_kr": name, "name_en": None, "name_vi": None, "dept": None,
         "position": None, "entity": None, "email": None, "phone": None, "is_admin": False,
         "works_access": True, "portal_access": False, "active": True, "status": "online"}
    if lang != "__absent__":
        u["lang"] = lang
    u.update(kw)
    return u


u = dir_user("VN001", "가법인장", "ko", name_en="Ga", dept="02_VN/00_총괄", position="법인장",
             entity="VN", email="a@t.test", phone="1", is_admin=False)
old_dict = {   # 예전 sync_employees_from_messenger_api 가 만들던 dict 그대로
    "sub": u.get("employee_no"), "employee_no": u.get("employee_no"),
    "name_kr": u.get("name_kr"), "name_en": u.get("name_en"), "name_vi": u.get("name_vi"),
    "dept": u.get("dept"), "position": u.get("position"), "entity": u.get("entity"),
    "email": u.get("email"), "phone": u.get("phone"), "is_admin": u.get("is_admin")}
newp = SC._directory_user_to_payload(u)
check({k: v for k, v in newp.items() if k != "lang"} == old_dict and newp.get("lang") == "ko",
      "_directory_user_to_payload = 예전 dict 와 똑같고 lang 만 하나 더")
check(SC._directory_user_to_payload(dir_user("1", "x")).get("lang") is None, "이음이 lang 을 안 보내면 None")

_real_get = SC.httpx.get
DIR = [dir_user(eno, name, lg) for eno, name, lg in [
    ("VN001", "가법인장", "ko"), ("VN265", "나베트남", "vi"), ("101", "다본사", "ko"), ("102", "라널", "ko"),
    ("100", "바관리", "ko"), ("VN266", "사베트남", "vi"), ("103", "마레거시", "ko")]]
try:
    SC.httpx.get = lambda *a, **k: FakeResp(DIR)
    c = mkdb()
    r = SC.sync_employees_from_messenger_api(c, do_remove=False)
    check(r.get("ok") and sorted(x["employee_no"] for x in r["lang_changed"]) == ["VN001", "VN265"],
          "관리자·새벽 동기화 창구(sync_employees_from_messenger_api)가 이음 언어를 옮긴다")
    check(lang_of(c, "VN001") == "ko" and lang_of(c, "VN265") == "vi", "  → DB 도 그 값")
    c = mkdb()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r = SC.sync_directory_from_messenger(c)
    check(r.get("ok") and len(r.get("lang_changed", [])) == 2 and lang_of(c, "VN001") == "ko",
          "옛 창구(sync_directory_from_messenger · /admin/sync-directory)도 같은 함수로 같은 결과")
    check("언어 바뀜(이음 따름)" in buf.getvalue() and "VN001" in buf.getvalue(),
          "  → 옛 창구는 화면이 없어 기록(로그)에 이름·사번을 남긴다")
    SC.httpx.get = lambda *a, **k: FakeResp([{k2: v for k2, v in x.items() if k2 != "lang"} for x in DIR])
    c = mkdb()
    r = SC.sync_employees_from_messenger_api(c, do_remove=False)
    check(r.get("ok") and r["lang_changed"] == [] and lang_of(c, "VN001") == "vi",
          "지금 이음(언어 칸 없음)으로 돌리면 아무도 안 바뀐다 — 두 창구 모두")
    c = mkdb()
    with contextlib.redirect_stdout(io.StringIO()):
        r = SC.sync_directory_from_messenger(c)
    check(r.get("ok") and r["lang_changed"] == [] and lang_of(c, "VN001") == "vi", "  (옛 창구도)")
finally:
    SC.httpx.get = _real_get

# ════════════════════════════════════════════════════════════════════
print("\n§5 배포 전 검사기 — check_user_lang")
files = list(CS._walk(CS.TPL, (".html",))) if hasattr(CS, "_walk") else []
check(CS.check_user_lang(files) == [], "지금 코드: 위반 0")

REL = ["app/i18n.py", "app/main.py", "app/sso_client.py", "app/templates/profile.html"]
MUT = [
    ("app/i18n.py", 'USER_LANGS = ("ko", "vi")', 'USER_LANGS = ("ko", "vi", "en")', "①", "USER_LANGS 에 en 을 되살림"),
    ("app/i18n.py", 'return s if s in USER_LANGS else "ko"', 'return s', "①", "목록 밖 값을 그대로 통과"),
    ("app/templates/profile.html", '<input type="text" value="{{ user_lang_label }}" disabled',
     '<select name="lang"><option value="ko">한국어</option><option value="en">English</option></select>'
     '<input type="text" value="{{ user_lang_label }}" disabled', "②", "옛 고르는 칸(한국어·English) 되살림"),
    ("app/templates/profile.html", '<input type="text" value="{{ user_lang_label }}" disabled',
     '<select name="lang"><option value="ko">한국어</option><option value="vi">Tiếng Việt</option></select>'
     '<input type="text" value="{{ user_lang_label }}" disabled', "③", "선택지를 다 갖춰도 「내 프로필」에 바꾸는 칸이면 위반"),
    ("app/main.py", '            sets.append("email=?"); vals.append(email)\n    # phone / dept',
     '            sets.append("email=?"); vals.append(email)\n    sets.append("lang=?"); vals.append("ko")\n    # phone / dept',
     "④", "/me 저장이 다시 언어를 씀"),
    ("app/main.py", '    if lang not in USER_LANGS:\n        if req.method == "GET":',
     '    if lang not in LANGS:\n        lang = "ko"\n    if lang not in USER_LANGS:\n        if req.method == "GET":',
     "⑤", "/api/set-lang 이 모르는 값을 한국어로 바꿔 저장"),
    ("app/main.py", '    if lang not in USER_LANGS:\n        lang = "ko"\n\n    # 번역 사전 생성', '\n    # 번역 사전 생성',
     "⑦", "ctx 가 목록 밖 값을 그대로 씀"),
    ("app/sso_client.py", '        "lang": u.get("lang"),\n    }', '    }', "⑥", "명부 → payload 에서 lang 을 뺌"),
    ("app/sso_client.py", '    payloads = [_directory_user_to_payload(u) for u in users]',
     '    payloads = [{"sub": u.get("employee_no"), "name_kr": u.get("name_kr")} for u in users]',
     "⑥", "API 창구가 dict 를 따로 만듦"),
    ("app/sso_client.py", '                 lang = COALESCE(?, lang),\n', '', "⑥", "upsert 가 기존 직원 언어를 안 맞춤"),
    ("app/sso_client.py", '    lang    = user_lang_from_messenger(payload.get("lang"))', '    lang    = payload.get("lang")',
     "⑥", "upsert 가 기준 함수를 안 거침"),
]
OTHER_TPL = '<select name="lang"><option value="ko">한국어</option><option value="en">English</option></select>'
_root, _tpl = CS.ROOT, CS.TPL
tmp = tempfile.mkdtemp(prefix="z1155chk_")
try:
    for rel, old, new, mark, what in MUT:
        shutil.rmtree(tmp, ignore_errors=True)
        for r_ in REL:
            os.makedirs(os.path.dirname(os.path.join(tmp, r_)), exist_ok=True)
            shutil.copyfile(os.path.join(ROOT, r_), os.path.join(tmp, r_))
        p = os.path.join(tmp, rel)
        s = io.open(p, encoding="utf-8", newline="").read().replace("\r\n", "\n")
        if s.count(old) != 1:
            check(False, "되돌림 준비 실패(%s) — 바꿀 글이 %d번" % (what, s.count(old)))
            continue
        io.open(p, "w", encoding="utf-8", newline="").write(s.replace(old, new))
        CS.ROOT, CS.TPL = tmp, os.path.join(tmp, "app", "templates")
        hits = CS.check_user_lang([])
        check(any(m.lstrip().startswith(mark) for _, _, m in hits), "되돌림 「%s」 → %s 로 잡힘 (%d건)" % (what, mark, len(hits)))
    # 다른 화면에 베트남어 빠진 고르는 칸(원래 사고의 모양)
    shutil.rmtree(tmp, ignore_errors=True)
    for r_ in REL:
        os.makedirs(os.path.dirname(os.path.join(tmp, r_)), exist_ok=True)
        shutil.copyfile(os.path.join(ROOT, r_), os.path.join(tmp, r_))
    other = os.path.join(tmp, "app", "templates", "some_new_screen.html")
    io.open(other, "w", encoding="utf-8").write("<form>" + OTHER_TPL + "</form>")
    CS.ROOT, CS.TPL = tmp, os.path.join(tmp, "app", "templates")
    hits = CS.check_user_lang([other])
    check(any(m.lstrip().startswith("②") and "vi" in m for _, _, m in hits),
          "다른 화면에 새로 만든 고르는 칸에 베트남어가 빠지면 ② 로 잡힘")
finally:
    CS.ROOT, CS.TPL = _root, _tpl
    shutil.rmtree(tmp, ignore_errors=True)

print("\n" + "=" * 60)
print("결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
