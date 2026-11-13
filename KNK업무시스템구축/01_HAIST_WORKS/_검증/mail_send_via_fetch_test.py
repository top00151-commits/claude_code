# -*- coding: utf-8 -*-
"""'내 받기 계정으로 보내기' 검증 (대표 지시 2026-11-13 「완료 처리해」).

운영 DB·운영 메일·운영 비밀번호 무접촉 — 전부 메모리 DB + 가짜 자격증명.

증명할 것
  ① 받기 호스트 → 보내기(SMTP) 호스트 변환이 아는 곳만 되고, 모르는 곳은 짐작하지 않는다
  ② 스위치(off/one/all)가 정확히 그 사람에게만 열린다
  ③ 받기 계정 자격증명으로 발송 설정이 만들어진다 (비밀번호 재입력 없음)
  ④ 못 만들 땐 왜 못 만드는지 화면에 쓸 이유가 나온다
  ⑤ ⭐화면용 상태 dict 에 비밀번호 값이 절대 섞이지 않는다 (심으면 잡히는지도 확인)
  ⑥ 보내는 주소가 '받기 계정 주소'로 고정된다 — 제공사가 남의 주소 발송을 막으므로
  ⑦ ⭐(회귀) 기본값 off 면 지금 동작과 완전히 같다 — 켜기 전까지 변화 0
  ⑧ ⭐두 폼이 주소를 공유하므로, 한 폼 저장이 다른 폼 설정을 빈 값으로 덮지 않는다
  ⑨ 템플릿 Jinja 문법이 성립한다 (화면 500 방지)
"""
import ast
import io
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ⭐키를 먼저 넣는다 — 안 넣으면 data/.mail_key 파일을 만들어 버린다(작업폴더 오염).
from cryptography.fernet import Fernet  # noqa: E402
os.environ["KNK_MAIL_KEY"] = Fernet.generate_key().decode()

from app import mail_send as ms          # noqa: E402
from app import mail_fetch as mf         # noqa: E402

PASS = FAIL = 0

# 가짜 값만 — 실제 비밀번호 아님
FAKE_ADDR = "tester@knk-mailtest.com"
FAKE_PW = "FAKE-not-a-real-password-0000"
ME, OTHER = 5, 99


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


def add_fetch(c, owner=ME, host="pop3s.hiworks.com", user=FAKE_ADDR,
              pw=FAKE_PW, proto="pop3", enc=None):
    mf.save_account(c, owner, protocol=proto, host=host, port=995, use_ssl=1,
                    username=user,
                    password_enc=(enc if enc is not None else ms.encrypt(pw)),
                    label="시험")


def add_system_relay(c):
    """기존 시스템 발송망(가짜)."""
    setopt(c, "mail_send_host", "smtp.fake-relay.example")
    setopt(c, "mail_send_port", "465")
    setopt(c, "mail_send_user", "relay-user")
    setopt(c, "mail_send_pass_enc", ms.encrypt("FAKE-relay-pw"))


# ════════════════ §1 받기 호스트 → 보내기 호스트 ════════════════
print("\n§1 받기 호스트 → 보내기(SMTP) 호스트 — 아는 곳만, 짐작 금지")
for h in ("pop3s.hiworks.com", "POP3S.HIWORKS.COM", " pop3.hiworks.com ",
          "imap.hiworks.com", "imaps.hiworks.com"):
    check("하이웍스 %-22s → smtps.hiworks.com" % h.strip(),
          ms.smtp_host_from_fetch(h) == "smtps.hiworks.com",
          "실제=%r" % ms.smtp_host_from_fetch(h))
for h in ("pop.gmail.com", "imap.gmail.com", "mail.naver.com", "", None, "pop3s.hiworks.com.evil.kr"):
    check("모르는 곳 %-26r → 빈 값(짐작 안 함)" % h, ms.smtp_host_from_fetch(h) == "",
          "실제=%r" % ms.smtp_host_from_fetch(h))


# ════════════════ §2 스위치 ════════════════
print("\n§2 스위치(off/one/all) — 정확히 그 사람에게만")
c = make_db()
check("설정 없으면 기본 off", ms.via_fetch_mode(c) == "off", ms.via_fetch_mode(c))
check("기본 off 면 누구도 대상 아님", not ms.via_fetch_allowed(c, ME))
for junk in ("yes", "1", "ON", "", "  "):
    setopt(c, "mail_send_via_fetch", junk)
    check("엉뚱한 값 %-6r → off" % junk, ms.via_fetch_mode(c) == "off", ms.via_fetch_mode(c))
setopt(c, "mail_send_via_fetch", " ALL ")
check("대소문자·공백 섞인 'ALL' → all", ms.via_fetch_mode(c) == "all")
check("all 이면 그 사람도 대상", ms.via_fetch_allowed(c, ME))
check("all 이면 다른 사람도 대상", ms.via_fetch_allowed(c, OTHER))
check("all 이어도 대상 미지정(None)은 아님", not ms.via_fetch_allowed(c, None))

setopt(c, "mail_send_via_fetch", "one")
setopt(c, "mail_send_via_fetch_uid", str(ME))
check("one + 번호 일치 → 대상", ms.via_fetch_allowed(c, ME))
check("one + 번호 불일치 → 대상 아님", not ms.via_fetch_allowed(c, OTHER))
check("one + 숫자/문자 섞여도 비교됨", ms.via_fetch_allowed(c, "5"))
setopt(c, "mail_send_via_fetch_uid", "")
check("one 인데 번호가 비면 아무도 대상 아님", not ms.via_fetch_allowed(c, ME))


# ════════════════ §3 받기 자격증명으로 발송 설정 ════════════════
print("\n§3 받기 계정 자격증명으로 발송 설정 만들기 (비밀번호 재입력 없음)")
c = make_db()
check("받기 계정 없으면 None", ms.get_fetch_send_config(c, ME) is None)
add_fetch(c)
cfg = ms.get_fetch_send_config(c, ME)
check("설정이 만들어진다", cfg is not None)
check("보내기 호스트 = smtps.hiworks.com", cfg and cfg["host"] == "smtps.hiworks.com",
      cfg and cfg.get("host"))
check("포트 기본 465", cfg and cfg["port"] == 465, cfg and cfg.get("port"))
check("로그인 계정 = 받기 아이디", cfg and cfg["user"] == FAKE_ADDR)
check("보내는 주소 = 받기 아이디", cfg and cfg["from"] == FAKE_ADDR)
check("출처 표시 src='fetch'", cfg and cfg.get("src") == "fetch")
check("⭐저장된 비밀번호가 제대로 풀린다", cfg and cfg["password"] == FAKE_PW)

c = make_db(); add_fetch(c, user="kjr")        # 아이디가 메일주소가 아님
check("아이디가 메일주소가 아니면 None(보내는 주소로 못 씀)", ms.get_fetch_send_config(c, ME) is None)

c = make_db(); add_fetch(c, host="pop.someisp.example")
check("모르는 받기 호스트 + 수동 호스트 없음 → None", ms.get_fetch_send_config(c, ME) is None)
setopt(c, "mail_send_fetch_host", "smtp.someisp.example")
setopt(c, "mail_send_fetch_port", "587")
cfg = ms.get_fetch_send_config(c, ME)
check("수동 호스트를 넣으면 만들어진다", cfg and cfg["host"] == "smtp.someisp.example")
check("수동 포트가 반영된다(587)", cfg and cfg["port"] == 587, cfg and cfg.get("port"))

c = make_db(); add_fetch(c, enc="이건-복호화-안-되는-값")
check("비밀번호를 못 풀면 None(조용히 틀린 값 안 씀)", ms.get_fetch_send_config(c, ME) is None)
c = make_db(); add_fetch(c, enc="")
check("비밀번호가 비어 있으면 None", ms.get_fetch_send_config(c, ME) is None)

c = make_db(); add_fetch(c)
setopt(c, "mail_send_fetch_port", "포트아님")
cfg = ms.get_fetch_send_config(c, ME)
check("포트가 숫자가 아니면 465 로 되돌아감", cfg and cfg["port"] == 465, cfg and cfg.get("port"))


# ════════════════ §4·§5 화면용 상태 + 비밀번호 누출 가드 ════════════════
print("\n§4 화면용 상태 — 왜 못 쓰는지 이유가 나온다")
c = make_db()
st = ms.fetch_send_status(c, ME)
check("받기 계정 없음 → ok=False", st["ok"] is False)
check("받기 계정 없음 → 이유 있음", "등록된 받기 계정이 없습니다" in st["why"], st["why"])
check("대상 미지정(None) → 이유 있음", bool(ms.fetch_send_status(c, None)["why"]))

c = make_db(); add_fetch(c, user="kjr")
st = ms.fetch_send_status(c, ME)
check("아이디가 메일주소 아님 → ok=False + 이유", st["ok"] is False and "메일주소 형태가 아닙니다" in st["why"],
      st["why"])

c = make_db(); add_fetch(c, enc="")
st = ms.fetch_send_status(c, ME)
check("비밀번호 없음 → ok=False + 이유", st["ok"] is False and "비밀번호가 없습니다" in st["why"], st["why"])
check("비밀번호 없음 → has_pass=False", st["has_pass"] is False)

c = make_db(); add_fetch(c, host="pop.someisp.example")
st = ms.fetch_send_status(c, ME)
check("모르는 호스트 → ok=False + 직접 입력 안내", st["ok"] is False and "직접 입력" in st["why"], st["why"])

c = make_db(); add_fetch(c, enc="복호화-불가")
st = ms.fetch_send_status(c, ME)
check("복호화 실패 → ok=False + 다시 저장 안내", st["ok"] is False and "다시 저장" in st["why"], st["why"])

c = make_db(); add_fetch(c)
st = ms.fetch_send_status(c, ME)
check("정상 → ok=True", st["ok"] is True, st["why"])
check("정상 → 보내는 주소 표시", st["addr"] == FAKE_ADDR)
check("정상 → 보내기 서버 표시", st["host"] == "smtps.hiworks.com" and st["port"] == 465)
check("정상 → 받기 호스트·규약 표시", st["fetch_host"] == "pop3s.hiworks.com" and st["protocol"] == "pop3")
check("정상 → has_pass=True (있다는 사실만)", st["has_pass"] is True)
check("정상 → 이유칸은 비어 있음", st["why"] == "", st["why"])

print("\n§5 ⭐비밀번호가 화면용 상태에 절대 섞이지 않는다")
blob = repr(st)
check("상태 dict 어디에도 비밀번호 평문 없음", FAKE_PW not in blob)
check("상태 dict 어디에도 암호문(password_enc) 없음",
      "gAAAAA" not in blob and "password_enc" not in blob)
check("password 라는 칸 자체가 없음", "password" not in st)
# 심으면 잡히는지 (시험이 '누출'을 실제로 잡아낼 수 있음을 증명)
poisoned = dict(st); poisoned["password"] = FAKE_PW
check("(대조군) 비밀번호를 심으면 이 검사가 잡는다", FAKE_PW in repr(poisoned))


# ════════════════ §6 보내는 주소 고정 + 경로 선택 ════════════════
print("\n§6 발송 — 어느 자격으로 로그인하고, 보내는 주소는 무엇인가")
seen = {}


def fake_smtp(host, port, login_user, login_pass, from_email, to_email,
              subject, body, from_name="", cc="", attachments=None, bcc="", html=""):
    seen.clear()
    seen.update(host=host, port=port, user=login_user, pw=login_pass, frm=from_email)
    return (True, "발송 완료")


real_smtp = ms._smtp_send
ms._smtp_send = fake_smtp
try:
    # (가) 스위치 off → 기존 시스템 발송망 그대로
    c = make_db(); add_fetch(c); add_system_relay(c)
    ok, _ = ms.send_system(c, "test@knk-mailtest.com", "x@example.com", "제목", "본문", owner_id=ME)
    check("off → 발송 성공", ok)
    check("off → 시스템 발송망 호스트 사용", seen.get("host") == "smtp.fake-relay.example", seen.get("host"))
    check("off → 보내는 주소 그대로(바뀌지 않음)",
          seen.get("frm") == "test@knk-mailtest.com", seen.get("frm"))

    # (나) 스위치 one + 본인 → 받기 계정으로
    setopt(c, "mail_send_via_fetch", "one"); setopt(c, "mail_send_via_fetch_uid", str(ME))
    ok, _ = ms.send_system(c, "test@knk-mailtest.com", "x@example.com", "제목", "본문", owner_id=ME)
    check("one(본인) → 발송 성공", ok)
    check("one(본인) → 하이웍스 보내기 서버 사용", seen.get("host") == "smtps.hiworks.com", seen.get("host"))
    check("one(본인) → 받기 계정으로 로그인", seen.get("user") == FAKE_ADDR, seen.get("user"))
    check("one(본인) → ⭐보내는 주소가 내 계정 주소로 고정",
          seen.get("frm") == FAKE_ADDR, seen.get("frm"))

    # (다) 스위치 one + 다른 사람 → 시스템 발송망
    ok, _ = ms.send_system(c, "test@knk-mailtest.com", "x@example.com", "제목", "본문", owner_id=OTHER)
    check("one(다른 사람) → 시스템 발송망", seen.get("host") == "smtp.fake-relay.example", seen.get("host"))
    check("one(다른 사람) → 보내는 주소 그대로", seen.get("frm") == "test@knk-mailtest.com")

    # (라) owner_id 를 아예 안 주면(옛 호출부) 시스템 발송망
    ok, _ = ms.send_system(c, "test@knk-mailtest.com", "x@example.com", "제목", "본문")
    check("owner_id 없는 옛 호출 → 시스템 발송망(하위호환)",
          seen.get("host") == "smtp.fake-relay.example", seen.get("host"))

    # (마) 스위치 켜졌는데 받기 계정이 깨졌으면 → 시스템 발송망으로 안전 복귀
    c2 = make_db(); add_fetch(c2, enc="복호화-불가"); add_system_relay(c2)
    setopt(c2, "mail_send_via_fetch", "all")
    ok, _ = ms.send_system(c2, "test@knk-mailtest.com", "x@example.com", "제목", "본문", owner_id=ME)
    check("켜졌지만 받기 계정이 깨짐 → 시스템 발송망으로 안전 복귀",
          ok and seen.get("host") == "smtp.fake-relay.example", seen.get("host"))

    # (바) 둘 다 없으면 발송 안 되고 안내 문구
    c3 = make_db()
    ok, msg = ms.send_system(c3, "test@knk-mailtest.com", "x@example.com", "제목", "본문", owner_id=ME)
    check("둘 다 없으면 실패 + 안내", (not ok) and "보내기 설정" in msg, msg)
finally:
    ms._smtp_send = real_smtp


# ════════════════ §7 준비 여부 ════════════════
print("\n§7 '발송 준비됨' 판정")
c = make_db()
check("아무것도 없으면 준비 안 됨", ms.system_send_ready(c, ME) is False)
add_fetch(c)
check("받기 계정만 있고 스위치 off → 준비 안 됨", ms.system_send_ready(c, ME) is False)
setopt(c, "mail_send_via_fetch", "one"); setopt(c, "mail_send_via_fetch_uid", str(ME))
check("스위치 one(본인) → 시스템 발송망 없이도 준비됨", ms.system_send_ready(c, ME) is True)
check("스위치 one, 다른 사람 → 준비 안 됨", ms.system_send_ready(c, OTHER) is False)
c = make_db(); add_system_relay(c)
check("시스템 발송망만 있어도 준비됨(기존 동작)", ms.system_send_ready(c) is True)


# ════════════════ §8 ⭐회귀: 켜기 전까지 변화 0 ════════════════
print("\n§8 ⭐(회귀) 기본값 off 면 지금 동작과 완전히 같다")
c = make_db(); add_system_relay(c); add_fetch(c)
old = ms.get_send_config(c)
new = ms.get_send_config_for(c, ME)
check("off → get_send_config_for 가 기존 get_send_config 와 같은 값",
      old == new, "old=%r new=%r" % (old and old.get("host"), new and new.get("host")))
check("off → 기존 system_send_ready(c) 호출도 그대로 동작", ms.system_send_ready(c) is True)
check("off → src 표시가 없다(=시스템 발송망)", "src" not in (new or {}))


# ════════════════ §9 ⭐두 폼이 서로를 덮지 않는다 ════════════════
print("\n§9 ⭐한 폼 저장이 다른 폼 설정을 지우지 않는다 (section 분리)")
# (가) 위험이 실재함을 먼저 증명 — 빈 값으로 저장하면 정말 지워진다
c = make_db(); add_system_relay(c)
ms.save_send_config(c, "", "465", "", "")
check("(대조군) 빈 값으로 save_send_config → 호스트가 실제로 지워진다",
      ms._setting(c, "mail_send_host") == "",
      ms._setting(c, "mail_send_host"))

# (나) 그래서 라우트가 section 으로 갈라 놓았는지 구조로 확인
src = io.open(os.path.join(ROOT, "app", "main.py"), "r", encoding="utf-8").read()
tree = ast.parse(src)
fn = next((n for n in ast.walk(tree)
           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
           and n.name == "admin_mail_send_save"), None)
check("라우트 함수 admin_mail_send_save 를 찾았다", fn is not None)


def calls_in(node):
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            name = getattr(f, "attr", None) or getattr(f, "id", None)
            if name:
                out.append(name)
    return out


guarded = False
if fn:
    for n in ast.walk(fn):
        if isinstance(n, ast.If) and "section" in ast.dump(n.test):
            # section 분기의 '아니면(else)' 쪽에만 save_send_config 가 있어야 한다
            in_body = any("save_send_config" in calls_in(b) for b in n.body)
            in_else = any("save_send_config" in calls_in(b) for b in n.orelse)
            if in_else and not in_body:
                guarded = True
check("save_send_config 가 section 분기의 '아니면' 쪽에만 있다", guarded)
if fn:
    all_calls = calls_in(fn)
    check("save_send_config 호출은 이 라우트에 한 번뿐",
          all_calls.count("save_send_config") == 1, all_calls.count("save_send_config"))


# ════════════════ §10 템플릿 Jinja 문법 ════════════════
print("\n§10 템플릿 Jinja 문법 (화면 500 방지)")
tpl_path = os.path.join(ROOT, "app", "templates", "admin_mail_send.html")
tpl = io.open(tpl_path, "r", encoding="utf-8").read()
try:
    from jinja2 import Environment
    Environment().parse(tpl)
    check("admin_mail_send.html Jinja 문법 성립", True)
except Exception as e:
    check("admin_mail_send.html Jinja 문법 성립", False, "%s: %s" % (type(e).__name__, e))

check("폼 구분자 section=via_fetch 가 있다", 'name="section" value="via_fetch"' in tpl)
check("폼 구분자 section=smtp 가 있다", 'name="section" value="smtp"' in tpl)
for v in ("off", "one", "all"):
    check('스위치 선택 %-4s 가 화면에 있다' % v, 'name="via_fetch" value="%s"' % v in tpl)
check("끌 수 있는 길이 화면에 있다(먹통 방지)", "끄기" in tpl)
check("쓸 수 있는지 ✅/⚠ 를 화면에 보여 준다", "fetch_st.ok" in tpl and "fetch_st.why" in tpl)
check("비밀번호 입력칸을 새로 만들지 않았다(재입력 없음)",
      tpl.count('type="password"') == 1, tpl.count('type="password"'))


print("\n" + "=" * 56)
print("  통과 %d / 실패 %d" % (PASS, FAIL))
print("=" * 56)
sys.exit(1 if FAIL else 0)
