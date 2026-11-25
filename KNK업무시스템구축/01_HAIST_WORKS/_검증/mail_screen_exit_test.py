# -*- coding: utf-8 -*-
"""메일 화면 「닫기·돌아가기」 전체 점검 시험 — 가짜 자료·임시 DB(운영 무접촉 · 실제 메일 없음).
대표 11-25 「팝업으로 열렸으면 항상 닫기 기능이 있어야해.. 전체 점검하고 수정해」 · 운영 스킬 knk-screen-exit.
① 메일 화면마다(GET 200) 화면 안에 「← 돌아가기」·「✕ 닫기」·받은편지함 단추가 있다
② 새 창(메일 보기 win=1 · 쓰기 win=1)은 창 닫기 길(window.close) + 안 닫히면 받은편지함
③ 팝업 = 공용 ✕(mail_popx) + Esc
사용: py -3.13 _검증/mail_screen_exit_test.py"""
import io
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
_so = sys.stdout
sys.stdout = io.StringIO()
try:
    import app.database as _db
    _TMP = tempfile.mkdtemp(prefix="knk_mexit_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
finally:
    sys.stdout = _so
from starlette.testclient import TestClient  # noqa: E402

P = F = 0


def check(name, cond, extra=""):
    global P, F
    if cond:
        P += 1
        print("  [PASS]", name)
    else:
        F += 1
        print("  [FAIL]", name, "<-", str(extra)[:300])


U = 9401
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x' WHERE login_id='kjr'")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9401,'kjr','가짜대표','ceo',1,'x')")
    mid, _o = ms.store_inbound(c, to_email="kjr@knknara.co.kr", from_email="a@fake.example", from_name="가짜",
                               subject="가짜 제목", text="가짜 본문", owner_id=U, run_ai=False, message_id="exit-1@fake")

m.get_user = lambda req: {"id": U, "role": "ceo", "name": "가짜대표", "team_id": None, "team_name": "", "login_id": "kjr"}
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})

# 나가는 길로 보는 것: 공용 나가기 조각 · ← 로 시작하는 단추/링크 · ✕ 닫기 · 받은편지함으로 · 창 닫기
EXIT = re.compile(r'class="[^"]*mail-exit|>\s*←\s*[^<]{1,20}<|✕ 닫기|받은편지함으로|window\.close\(')

PAGES = [
    "/mail/inbox", "/mail/sent", "/mail/drafts", "/mail/trash", "/mail/blocked",
    "/mail/account", "/mail/autoreply", "/mail/cleanup", "/mail/files", "/mail/folders", "/mail/folders/general",
    "/mail/groups", "/mail/help", "/mail/kinds", "/mail/rules", "/mail/signature",
    "/mail/signature/company", "/mail/storage", "/mail/templates", "/mail/tools", "/mail/waiting",
    "/mail/from-outlook", "/mail/blocklist", "/mail/%d" % mid,
]
INBOX_LIKE = {"/mail/inbox", "/mail/sent", "/mail/drafts", "/mail/trash", "/mail/blocked"}

print("== 1. 화면마다 나가는 길 ==")
for path in PAGES:
    r = k.get(path)
    if r.status_code != 200:
        check("%s 열림(200)" % path, False, r.status_code)
        continue
    h = r.text
    if path in INBOX_LIKE:
        # 메일함 화면 = 왼쪽 폴더 칸·머리띠가 늘 보이는 「집」 화면 — 나가는 길 = 머리띠(받은편지함 등)
        check("%s = 메일함 화면(머리띠 메뉴로 다른 곳)" % path, "mail-app-top" in h or "mailAppTop" in h or 'href="/mail/inbox"' in h)
        continue
    check("%s 화면 안에 「← 돌아가기 / ✕ 닫기 / 받은편지함으로」" % path, bool(EXIT.search(h)), h[:200])

print("== 2. 새로 넣은 위쪽 나가기 단추(이번에 고친 화면) ==")
for path, lab in (("/mail/account", "← 받은편지함"), ("/mail/signature", "← 받은편지함"), ("/mail/rules", "← 받은편지함"),
                  ("/mail/storage", "← 설정·정리"), ("/mail/from-outlook", "← 설정·정리"), ("/mail/signature/company", "← 메일 서명")):
    h = k.get(path).text
    i = h.find('class="page-head"')
    head = h[i:i + 2500] if i >= 0 else ""
    check("%s 위쪽(제목 줄)에 「%s」 · 새 창이면 창 닫기 길" % (path, lab), "mail-exit" in head and lab in head and "mailExit" in h, head[:200])

print("== 3. 새 창 ==")
hw = k.get("/mail/%d?win=1" % mid).text
check("메일 보기 새 창 = 「✕ 닫기」 + 안 닫히면 받은편지함으로 + Esc", "✕ 닫기" in hw and "window.close(); setTimeout(function(){ location.href='/mail/inbox'; }" in hw and "Escape" in hw)
hc = k.get("/mail/compose?win=1").text
check("쓰기 새 창 = 「취소」 단추(창 닫기 길)", 'id="cCancelBtn"' in hc and "window.close()" in hc)

print("== 4. 팝업 ✕ · Esc ==")
hi = k.get("/mail/inbox").text
check("받은편지함에 공용 팝업 ✕(mail_popx) · Esc 로 닫기", "_mailPopX" in hi and "e.key!=='Escape'" in hi and "e.stopPropagation()" in hi)
check("쓰기 화면에도 공용 팝업 ✕", "_mailPopX" in k.get("/mail/compose").text)

print("결과: %d 통과 · %d 실패" % (P, F))
sys.exit(1 if F else 0)
