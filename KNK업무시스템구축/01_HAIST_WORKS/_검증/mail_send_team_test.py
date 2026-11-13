# -*- coding: utf-8 -*-
"""「내 메일 계정 연결」(보내기 전용) + 명단 모드 검증.

대표 지시 2026-11-13: 안지연 프로(사번 67)·이새롬 프로(사번 306)도 본인 주소로 보내게.
확정 범위 = 「보내기만, 명단 3명」.

운영 DB·운영 메일·운영 비밀번호 무접촉 — 전부 메모리 DB + 가짜 자격증명.

증명할 것
  ① 명단(list) 모드가 고른 사람에게만 열린다 · 기존 off/one/all 은 그대로
  ② ⭐「보내기 전용」 — 새로 연결하면 자동 가져오기가 꺼진 채로 만들어진다
  ③ ⭐⭐(회귀) 이미 받아오고 있던 사람(대표)이 다시 저장해도 **받기가 꺼지지 않는다**
  ④ 자동 가져오기를 꺼도 '보내기'는 된다 / 스케줄러는 그 사람을 안 집는다
  ⑤ 연결 풀기 = 비밀번호만 비우고 행은 남긴다(다시 연결해도 과거 메일 재수집 없음)
  ⑥ 연결 시험은 로그인만 하고 ⭐메일을 보내지 않는다
  ⑦ 연결 화면은 관리자가 아니어도 쓸 수 있다(라우트 구조로 확인)
  ⑧ 네트워크를 기다리는 동안 DB 세션을 쥐고 있지 않다(라우트 구조로 확인)
  ⑨ 비밀번호가 화면·응답 어디에도 새지 않는다
  ⑩ 템플릿 Jinja 문법 성립
"""
import ast
import io
import os
import smtplib
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from cryptography.fernet import Fernet  # noqa: E402
os.environ["KNK_MAIL_KEY"] = Fernet.generate_key().decode()

from app import mail_send as ms     # noqa: E402
from app import mail_fetch as mf    # noqa: E402

PASS = FAIL = 0

FAKE_PW = "FAKE-not-a-real-password-0000"
CEO, AJY, LSR, OTHER = 1, 67, 306, 999      # 시험용 users.id (운영 번호 아님)
A_CEO, A_AJY, A_LSR = ("ceo@knknara.co.kr", "aaa@knknara.co.kr", "bbb@knknara.co.kr")


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [PASS]", name)
    else:
        FAIL += 1
        print("  [FAIL]", name, extra)


def make_db():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE app_settings(key TEXT PRIMARY KEY, value TEXT)")
    mf._ensure_table(c)
    return c


def setopt(c, k, v):
    c.execute("INSERT INTO app_settings(key,value) VALUES(?,?) "
              "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, str(v)))


def link_as_route(c, uid, addr, pw):
    """/mail/account POST 가 하는 일을 그대로 흉내 낸다."""
    exist = mf.get_account(c, uid)
    mf.save_account(c, uid, protocol="pop3", host="pop3s.hiworks.com", port=995,
                    use_ssl=1, username=addr,
                    password_enc=(ms.encrypt(pw) if pw else None), label="")
    if not exist:
        mf.set_enabled(c, uid, False)       # ⭐보내기 전용
    return exist is None


def unlink_as_route(c, uid):
    c.execute("UPDATE mail_fetch_accounts SET password_enc='', enabled=0 WHERE owner_user_id=?",
              (uid,))


# ════════════ §1 명단 모드 ════════════
print("\n§1 명단(list) 모드 — 고른 사람에게만")
c = make_db()
check("설정 없으면 기본 off", ms.via_fetch_mode(c) == "off")
setopt(c, "mail_send_via_fetch", "list")
check("'list' 를 알아본다", ms.via_fetch_mode(c) == "list")
setopt(c, "mail_send_via_fetch_uids", "1,67,306")
check("명단이 읽힌다", ms.via_fetch_uids(c) == {"1", "67", "306"}, ms.via_fetch_uids(c))
check("대표 = 대상", ms.via_fetch_allowed(c, CEO))
check("안지연 = 대상", ms.via_fetch_allowed(c, AJY))
check("이새롬 = 대상", ms.via_fetch_allowed(c, LSR))
check("명단 밖 사람 = 대상 아님", not ms.via_fetch_allowed(c, OTHER))
check("대상 미지정(None) = 아님", not ms.via_fetch_allowed(c, None))

for raw, want in [("1; 67 ;306", {"1", "67", "306"}),
                  ("1,,67", {"1", "67"}),
                  ("67 306", {"67", "306"}),
                  ("abc,67", {"67"}),
                  ("", set()),
                  ("   ", set())]:
    setopt(c, "mail_send_via_fetch_uids", raw)
    check("명단 글자 %-12r → %s" % (raw, sorted(want)), ms.via_fetch_uids(c) == want,
          ms.via_fetch_uids(c))

setopt(c, "mail_send_via_fetch_uids", "")
check("명단이 비면 아무도 대상 아님", not ms.via_fetch_allowed(c, CEO))

print("\n  (회귀) 기존 모드는 그대로")
c = make_db()
setopt(c, "mail_send_via_fetch", "one"); setopt(c, "mail_send_via_fetch_uid", str(CEO))
check("one — 본인만", ms.via_fetch_allowed(c, CEO) and not ms.via_fetch_allowed(c, AJY))
setopt(c, "mail_send_via_fetch", "all")
check("all — 모두", ms.via_fetch_allowed(c, CEO) and ms.via_fetch_allowed(c, OTHER))
setopt(c, "mail_send_via_fetch", "off")
check("off — 아무도", not ms.via_fetch_allowed(c, CEO))
setopt(c, "mail_send_via_fetch", "LIST")
check("대문자 'LIST' 도 명단 모드", ms.via_fetch_mode(c) == "list")
setopt(c, "mail_send_via_fetch", "listed")
check("비슷한 엉뚱한 값 'listed' → off", ms.via_fetch_mode(c) == "off")


# ════════════ §2·§3 보내기 전용 + 대표 받기 보존 ════════════
print("\n§2 「보내기 전용」 — 새로 연결하면 가져오기가 꺼진 채로")
c = make_db()
isnew = link_as_route(c, AJY, A_AJY, FAKE_PW)
acct = mf.get_account(c, AJY)
check("새 연결이다", isnew)
check("⭐자동 가져오기 꺼짐(enabled=0)", int(acct["enabled"]) == 0, acct["enabled"])
check("아이디가 저장됐다", acct["username"] == A_AJY)
check("비밀번호가 저장됐다", bool(acct["password_enc"]))
check("받기 호스트가 하이웍스로 채워졌다", acct["host"] == "pop3s.hiworks.com")

print("\n§3 ⭐⭐(회귀) 이미 받아오던 사람(대표)이 다시 저장해도 받기가 안 꺼진다")
c = make_db()
link_as_route(c, CEO, A_CEO, FAKE_PW)
mf.set_enabled(c, CEO, True)                       # 대표는 받기를 켜 둔 상태
check("준비: 대표 받기 켜짐", int(mf.get_account(c, CEO)["enabled"]) == 1)
isnew = link_as_route(c, CEO, A_CEO, "")           # 비번 없이 주소만 다시 저장
check("기존 계정이라 '새 연결'이 아니다", not isnew)
check("⭐대표 받기가 그대로 켜져 있다", int(mf.get_account(c, CEO)["enabled"]) == 1,
      mf.get_account(c, CEO)["enabled"])
check("비번 빈칸으로 저장해도 기존 비번 유지",
      ms.decrypt(mf.get_account(c, CEO)["password_enc"]) == FAKE_PW)
link_as_route(c, CEO, A_CEO, "NEW-FAKE-pw-1111")   # 비번을 바꿔도
check("비번을 바꿔도 받기는 그대로 켜짐", int(mf.get_account(c, CEO)["enabled"]) == 1)
check("바뀐 비번이 저장됐다",
      ms.decrypt(mf.get_account(c, CEO)["password_enc"]) == "NEW-FAKE-pw-1111")

print("\n§4 가져오기를 꺼도 '보내기'는 된다 / 스케줄러는 안 집는다")
c = make_db()
link_as_route(c, LSR, A_LSR, FAKE_PW)
setopt(c, "mail_send_via_fetch", "list"); setopt(c, "mail_send_via_fetch_uids", str(LSR))
cfg = ms.get_fetch_send_config(c, LSR)
check("⭐가져오기 꺼져 있어도 발송 설정이 만들어진다", cfg is not None)
check("보내기 서버 = smtps.hiworks.com", cfg and cfg["host"] == "smtps.hiworks.com")
check("보내는 주소 = 본인 주소", cfg and cfg["from"] == A_LSR)
check("발송 준비됨으로 판정", ms.system_send_ready(c, LSR) is True)
picked = [r[0] for r in c.execute(
    "SELECT owner_user_id FROM mail_fetch_accounts WHERE enabled=1").fetchall()]
check("⭐자동 가져오기 대상(enabled=1)에 안 들어 있다", LSR not in picked, picked)

print("\n§5 연결 풀기 — 비밀번호만 비우고 행은 남긴다")
c = make_db()
link_as_route(c, AJY, A_AJY, FAKE_PW)
aid_before = mf.get_account(c, AJY)["id"]
c.execute("INSERT INTO mail_fetch_seen(account_id, uidl) VALUES(?,?)", (aid_before, "UID-1"))
unlink_as_route(c, AJY)
acct = mf.get_account(c, AJY)
check("행이 남아 있다", acct is not None)
check("⭐계정 번호가 그대로다(과거 메일 재수집 방지)", acct and acct["id"] == aid_before)
check("'이미 가져온 메일' 기록이 남아 있다",
      len(mf.get_seen(c, aid_before)) == 1, mf.get_seen(c, aid_before))
check("비밀번호가 비워졌다", (acct["password_enc"] or "") == "")
check("가져오기도 꺼졌다", int(acct["enabled"]) == 0)
setopt(c, "mail_send_via_fetch", "list"); setopt(c, "mail_send_via_fetch_uids", str(AJY))
check("푼 뒤에는 발송 설정이 안 만들어진다", ms.get_fetch_send_config(c, AJY) is None)
st = ms.fetch_send_status(c, AJY)
check("화면에 이유가 나온다", (not st["ok"]) and "비밀번호가 없습니다" in st["why"], st["why"])


# ════════════ §6 연결 시험은 메일을 보내지 않는다 ════════════
print("\n§6 연결 시험 — 로그인만, ⭐메일은 안 보낸다")
sent = {"login": 0, "send_message": 0}


class FakeSMTP:
    def __init__(self, host, port, context=None, timeout=None):
        FakeSMTP.host = host

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def login(self, u, p):
        sent["login"] += 1

    def send_message(self, m):
        sent["send_message"] += 1


real = smtplib.SMTP_SSL
smtplib.SMTP_SSL = FakeSMTP
try:
    ok, msg = ms.smtp_login_test("smtps.hiworks.com", 465, A_AJY, FAKE_PW)
    check("연결 성공으로 돌아온다", ok, msg)
    check("로그인은 1번 했다", sent["login"] == 1, sent["login"])
    check("⭐메일을 보내지 않았다", sent["send_message"] == 0, sent["send_message"])

    class AuthFail(FakeSMTP):
        def login(self, u, p):
            raise smtplib.SMTPAuthenticationError(535, b"bad")

    smtplib.SMTP_SSL = AuthFail
    ok, msg = ms.smtp_login_test("smtps.hiworks.com", 465, A_AJY, FAKE_PW)
    check("로그인 실패를 알려 준다", not ok)
    check("⭐'메일 전용 비밀번호' 라고 짚어 준다", "메일 전용 비밀번호" in msg, msg)
    check("안내문에 비밀번호가 안 들어 있다", FAKE_PW not in msg)
finally:
    smtplib.SMTP_SSL = real

for label, args in [("빈 호스트", ("", 465, A_AJY, FAKE_PW)),
                    ("빈 계정", ("h", 465, "", FAKE_PW)),
                    ("빈 비밀번호", ("h", 465, A_AJY, ""))]:
    ok, msg = ms.smtp_login_test(*args)
    check("정보가 모자라면 시도조차 안 한다 — %s" % label,
          (not ok) and "모자랍니다" in msg, msg)


# ════════════ §7·§8 라우트 구조 ════════════
print("\n§7 연결 화면은 관리자가 아니어도 쓸 수 있다 (구조 확인)")
src = io.open(os.path.join(ROOT, "app", "main.py"), "r", encoding="utf-8").read()
tree = ast.parse(src)


def fn(name):
    return next((n for n in ast.walk(tree)
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name), None)


def calls(node):
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            nm = getattr(n.func, "attr", None) or getattr(n.func, "id", None)
            if nm:
                out.append(nm)
    return out


for name in ("mail_account_page", "mail_account_save", "mail_account_test", "mail_account_unlink"):
    f = fn(name)
    check("%s 라우트가 있다" % name, f is not None)
    if f:
        cs = calls(f)
        check("  · %s 는 관리자 전용이 아니다(require 안 씀)" % name, "require" not in cs, cs[:6])
        check("  · %s 는 로그인 확인은 한다(get_user)" % name, "get_user" in cs)

f = fn("mail_account_save")
if f:
    cs = calls(f)
    check("저장은 본인 것만 — set_enabled 를 쓴다", "set_enabled" in cs)
    guarded = False
    for n in ast.walk(f):
        if isinstance(n, ast.If) and "exist" in ast.dump(n.test):
            if any("set_enabled" in calls(b) for b in n.body):
                guarded = True
    check("⭐set_enabled 는 '새 연결일 때만' 안에 있다 (대표 받기 보존)", guarded)

print("\n§8 네트워크를 기다리는 동안 DB 세션을 쥐고 있지 않다")
f = fn("mail_account_test")
if f:
    inside = False
    for n in ast.walk(f):
        if isinstance(n, ast.With) and "db_session" in ast.dump(n):
            if "smtp_login_test" in calls(n):
                inside = True
    check("⭐smtp_login_test 가 db_session 블록 밖에 있다", not inside)
    check("(대조군) 이 검사가 'with 안'을 실제로 들여다본다",
          any(isinstance(n, ast.With) and "db_session" in ast.dump(n) for n in ast.walk(f)))


# ════════════ §9 비밀번호 누출 ════════════
print("\n§9 비밀번호가 새지 않는다")
c = make_db()
link_as_route(c, AJY, A_AJY, FAKE_PW)
st = ms.fetch_send_status(c, AJY)
check("화면용 상태에 평문 비밀번호 없음", FAKE_PW not in repr(st))
check("화면용 상태에 암호문 없음", "gAAAAA" not in repr(st) and "password" not in st)
tpl_src = io.open(os.path.join(ROOT, "app", "templates", "mail_account.html"),
                  encoding="utf-8").read()
check("연결 화면이 저장된 비밀번호를 value 로 뿌리지 않는다",
      'id="acPw"' in tpl_src and 'value="{{' not in tpl_src.split('id="acPw"')[1][:200])
check("저장 뒤 비밀번호 칸을 비운다", "acPw').value = ''" in tpl_src)


# ════════════ §10 템플릿 ════════════
print("\n§10 템플릿 Jinja 문법")
from jinja2 import Environment  # noqa: E402
for name in ("mail_account.html", "mail_compose.html", "admin_mail_send.html"):
    pth = os.path.join(ROOT, "app", "templates", name)
    try:
        Environment().parse(io.open(pth, encoding="utf-8").read())
        check("%s 문법 성립" % name, True)
    except Exception as e:
        check("%s 문법 성립" % name, False, "%s: %s" % (type(e).__name__, e))

comp = io.open(os.path.join(ROOT, "app", "templates", "mail_compose.html"), encoding="utf-8").read()
check("메일 쓰기에 「📮 내 계정」 들어가는 길이 생겼다 (위·아래 두 줄)",
      comp.count('href="/mail/account"') == 3, comp.count('href="/mail/account"'))
adm = io.open(os.path.join(ROOT, "app", "templates", "admin_mail_send.html"), encoding="utf-8").read()
check("관리 화면에 「고른 사람만」이 있다", 'name="via_fetch" value="list"' in adm)
check("관리 화면에 사람 고르기 칸이 있다", 'name="via_fetch_uids"' in adm)
check("끄는 길이 그대로 있다", 'name="via_fetch" value="off"' in adm)

# ════════════ §11 새 화면을 실제로 그려 본다 ════════════
# ⭐Jinja 문법 통과 ≠ 렌더 성공. 없는 칸·필터는 그릴 때만 터진다(2026-11-13 오전 사고).
print("\n§11 새 화면 실제 렌더")
import jinja2                                   # noqa: E402
from jinja2 import FileSystemLoader             # noqa: E402


class Lenient(jinja2.Undefined):
    """앱이 넣어 주는 전역·함수의 대역(둘레 장식용). 불러도·칸을 따도 빈 값."""
    __slots__ = ()

    def __call__(self, *a, **k):
        return ""

    def __getattr__(self, k):
        if k.startswith("__"):
            raise AttributeError(k)
        return ""

    def __getitem__(self, k):
        return ""

    def __str__(self):
        return ""

    def __iter__(self):
        return iter(())

    def __bool__(self):
        return False


class Blank(dict):
    def __getattr__(self, k):
        return self.get(k, "")

    def __missing__(self, k):
        return ""


env = Environment(loader=FileSystemLoader(os.path.join(ROOT, "app", "templates")),
                  autoescape=True, undefined=Lenient)
env.globals.update(i=Blank(), cfg=Blank(), settings=Blank())
ME = {"id": 67, "name": "안지연", "role": "member"}


def render(name, **kw):
    try:
        return env.get_template(name).render(user=ME, mail_app=True, **kw)
    except Exception as e:
        import traceback
        check("렌더 성공 (%s · %s)" % (name, kw.get("_case", "")), False,
              traceback.format_exc()[-900:])
        return None


ST_OK = {"ok": True, "why": "", "addr": A_AJY, "host": "smtps.hiworks.com", "port": 465,
         "fetch_host": "pop3s.hiworks.com", "protocol": "pop3", "has_pass": True}
ST_NO = {"ok": False, "why": "「메일 가져오기」에 등록된 받기 계정이 없습니다. 그걸 먼저 등록하세요.",
         "addr": "", "host": "", "port": 465, "fetch_host": "", "protocol": "", "has_pass": False}

h = render("mail_account.html", _case="연결됨·대상", addr=A_AJY, has_pass=True,
           fetch_on=False, allowed=True, st=ST_OK, my_from=A_AJY, mail_key=True)
if h:
    check("렌더 성공 (내 계정 · 연결됨·대상)", True)
    check("· 보내는 주소가 보인다", A_AJY in h)
    check("· '지금 바로 쓸 수 있습니다' 표시", "지금 바로 쓸 수 있습니다" in h)
    check("· '보내기 전용' 안내가 있다", "보내기 전용" in h)
    check("· 연결 시험·연결 풀기 단추가 있다", "연결 시험" in h and "연결 풀기" in h)
    check("⭐비밀번호가 화면에 없다", FAKE_PW not in h and "gAAAAA" not in h)

h = render("mail_account.html", _case="연결됨·대상아님", addr=A_AJY, has_pass=True,
           fetch_on=False, allowed=False, st=ST_OK, my_from="test@knk-mailtest.com", mail_key=True)
if h:
    check("렌더 성공 (내 계정 · 연결됐지만 명단 밖)", True)
    check("· 명단에 넣어 달라고 안내한다", "명단에 넣어" in h)
    check("· 지금 나가는 주소를 알려 준다", "test@knk-mailtest.com" in h)

h = render("mail_account.html", _case="미연결", addr="", has_pass=False,
           fetch_on=False, allowed=True, st=ST_NO, my_from="test@knk-mailtest.com", mail_key=True)
if h:
    check("렌더 성공 (내 계정 · 아직 연결 안 함)", True)
    check("· 이유가 보인다", "아직 못 씁니다" in h)
    check("· 연결 풀기 단추는 숨어 있다", "연결 풀기" not in h)
    check("· 「메일 전용 비밀번호」 받는 법이 적혀 있다", "메일 전용 비밀번호" in h)

h = render("mail_account.html", _case="받기 켜진 사람", addr=A_CEO, has_pass=True,
           fetch_on=True, allowed=True, st=ST_OK, my_from=A_CEO, mail_key=True)
if h:
    check("렌더 성공 (내 계정 · 받기 켜진 사람)", True)
    check("⭐받기도 멈춘다고 경고한다", "받아오기도 멈춥니다" in h)

# 직원 고르기 = KNK 공용 선택위젯(z886 대표 지시 규정) — 법인 책갈피 + 검색 + 선택칩 + 부서 묶음
GROUPS = {
    "KOR": [
        {"team": "총괄", "has_checked": True,
         "members": [{"id": "1", "label": "김정락 대표이사 총괄", "no": "5", "linked": True}]},
        {"team": "관리팀", "has_checked": True,
         "members": [{"id": "67", "label": "안지연 프로 관리팀", "no": "67", "linked": False}]},
        {"team": "영업팀", "has_checked": True,
         "members": [{"id": "306", "label": "이새롬 프로 영업팀", "no": "306", "linked": False}]},
    ],
    "VN": [
        {"team": "베트남법인", "has_checked": False,
         "members": [{"id": "500", "label": "Nguyen (응우옌) 매니저 베트남법인",
                      "no": "VN01", "linked": False}]},
    ],
    "ETC": [],
}
ADMIN_CTX = dict(active="admin", ready=True, relay_ready=True, via_on=True, mail_key=True,
                 cur_host="smtp.mx.cloudflare.net", cur_port="465", cur_user="relay-user",
                 has_pass=True, cur_from="test@knk-mailtest.com",
                 fetch_st=ST_OK, my_from=A_CEO, cur_fetch_host="", cur_fetch_port="465",
                 saved=False)

h = render("admin_mail_send.html", _case="명단 모드", fetch_mode="list",
           emp_groups=GROUPS, fetch_uids={"1", "67", "306"}, **ADMIN_CTX)
if h:
    t = " ".join(h.split())
    check("렌더 성공 (관리 · 명단 모드)", True)
    check("· 꼬리표가 「켜짐 · 고른 3명」", "켜짐 · 고른 3명" in t)
    print("   — 대표 지시: 본사/베트남 책갈피 · 검색 · 부서별 —")
    check("⭐공용 선택위젯을 쓴다(직접 만든 목록 아님)",
          "data-knk-picker" in h and "knkpStyle" in h)
    check("⭐🏢본사 책갈피가 있다", 'data-entity="KOR"' in h and "🏢 본사" in h)
    check("⭐🌏베트남 책갈피가 있다", 'data-entity="VN"' in h and "🌏 베트남" in h)
    check("· 빈 법인(기타)은 책갈피를 안 만든다", 'data-entity="ETC"' not in h)
    check("⭐검색칸 안내문이 이름·부서·사번을 말한다",
          "data-knkp-ph" in h and "부서" in h and "사번" in h)
    check("⭐부서별로 묶여 있다", h.count('class="vf-team"') == 4, h.count('class="vf-team"'))
    check("· 부서 이름이 보인다", "관리팀" in h and "영업팀" in h and "베트남법인" in h)
    check("· 부서별 인원수가 보인다", "1명" in h)
    check("⭐검색이 부서·사번까지 걸린다(data-label)",
          'data-label="안지연 프로 관리팀 67"' in h)
    check("· 고른 사람이 있는 부서는 펼쳐져 있다",
          h.count("vf-members knkp-collapse open") == 3,
          h.count("vf-members knkp-collapse open"))
    check("· 아무도 안 고른 부서는 접혀 있다",
          h.count('class="vf-members knkp-collapse"') == 1)
    # 위젯 소스에도 'knkp-item' 글자가 들어 있으므로 라벨 자리만 센다
    check("· 사람 줄이 위젯이 아는 항목(knkp-item)이다",
          h.count('class="vf-radio knkp-item"') == 4,
          h.count('class="vf-radio knkp-item"'))
    check("· 네 사람 모두 고를 수 있다", t.count('name="via_fetch_uids"') == 4)
    check("· 고른 사람에 체크 표시", t.count('value="67" checked') == 1)
    check("· 안 고른 사람은 체크 없음", 'value="500" checked' not in t)
    check("· 이름이 「이름 직책 부서」 규칙", "안지연 프로 관리팀" in h)
    check("· 베트남 이름 병기가 그대로 나온다", "Nguyen (응우옌)" in h)
    check("· 사번이 함께 보인다", "(306)" in h)
    check("· 연결을 마친 사람에 📮 표시", "📮" in h)
    check("· 끄는 길이 그대로 있다", 'value="off"' in h)

# has_checked 는 서버가 fetch_uids 로 계산해 넘기는 값 → 빈 명단이면 전부 False
GROUPS_NONE = {k: [dict(g, has_checked=False) for g in v] for k, v in GROUPS.items()}
h = render("admin_mail_send.html", _case="명단 비었을 때", fetch_mode="list",
           emp_groups=GROUPS_NONE, fetch_uids=set(), **ADMIN_CTX)
if h:
    check("렌더 성공 (관리 · 명단 비었을 때)", True)
    check("· 체크된 사람이 없다", "checked" not in h.split('name="via_fetch_uids"')[1][:60])
    check("· 모든 부서가 접혀 있다", h.count("knkp-collapse open") == 0,
          h.count("knkp-collapse open"))

h = render("admin_mail_send.html", _case="베트남만 있을 때", fetch_mode="list",
           emp_groups={"KOR": [], "VN": GROUPS["VN"], "ETC": []},
           fetch_uids=set(), **ADMIN_CTX)
if h:
    check("렌더 성공 (베트남만 있을 때)", True)
    check("· 본사 책갈피를 안 만든다", 'data-entity="KOR"' not in h)
    check("· 베트남 책갈피만 만든다", 'data-entity="VN"' in h)


print("\n" + "=" * 56)
print("  통과 %d / 실패 %d" % (PASS, FAIL))
print("=" * 56)
sys.exit(1 if FAIL else 0)
