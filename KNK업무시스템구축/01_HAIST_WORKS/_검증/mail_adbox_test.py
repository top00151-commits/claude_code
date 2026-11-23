# -*- coding: utf-8 -*-
"""📢 광고·알림 칸 (대표 2026-11-23 「스팸함 위 광고·알림에 모이게 · 한꺼번에 삭제 · 끌어 넣으면 앞으로 기준 · 이전 것도 할지는 꼭 확인 · 특정 일자 이후만도」)
운영 무접촉 · 임시 DB · 가짜 사람·메일만.  실행: 프로젝트 루트(01_HAIST_WORKS)에서  python _검증/mail_adbox_test.py"""
import io
import os
import re
import shutil
import subprocess
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
os.environ["KNK_RUN_MAIL_FETCH"] = "0"
_so = sys.stdout
sys.stdout = io.StringIO()
try:
    from cryptography.fernet import Fernet
    os.environ.setdefault("KNK_MAIL_KEY", Fernet.generate_key().decode())
    import app.database as _db
    _db.DB_PATH = os.path.join(tempfile.mkdtemp(prefix="knk_adbox_"), "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_ui_prefs as mup
    from app import mail_store as ms
    from app import mail_find as mfi
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
        print("  [FAIL]", name, "<-", str(extra)[:500])


D = "@knknara.co.kr"
U = 9940
IDS = {}
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x', email=NULL")
    c.execute("INSERT INTO users(id, login_id, name, rank, role, is_active, password, email) VALUES(?, 't_ad','시험','사원','member',1,'x','ad" + D + "')", (U,))
    rows = [("minsu@shop-demo.example", "가짜쇼핑", "[가짜] 10월 소식", "2026-10-05 09:00:00"),
            ("minsu@shop-demo.example", "가짜쇼핑", "[가짜] 11월 소식", "2026-11-10 09:00:00"),
            ("minsu@shop-demo.example", "가짜쇼핑", "[가짜] 11월 특가", "2026-11-20 09:00:00"),
            ("a@cust-demo.example", "가짜고객", "[가짜] 견적 부탁", "2026-11-21 09:00:00"),
            ("noreply@bank-demo.example", "가짜은행", "[가짜] 입출금 알림", "2026-11-22 09:00:00"),
            ("kim" + D, "사내", "[가짜] 사내 공지", "2026-11-22 10:00:00")]
    for fe, fn, sj, at in rows:
        c.execute("INSERT INTO mail_messages(user_id, direction, from_email, from_name, to_email, subject, body_text, is_read, is_deleted, received_at) "
                  "VALUES(?,'in',?,?,?,?,'가짜',1,0,?)", (U, fe, fn, "ad" + D, sj, at))
        IDS[sj] = c.execute("SELECT last_insert_rowid()").fetchone()[0]

ME = {"id": U, "role": "member", "name": "시험", "rank": "사원", "login_id": "t_ad", "email": "ad" + D, "lang": "ko"}
m.get_user = lambda req: ME
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})


def T(r):
    return r.text.replace("\r\n", "\n")


def NM(h):
    return set(int(x) for x in re.findall(r'data-mail-id="(\d+)"', h))


print("① 자동 판단 + 칸 숫자")
with _db.db_session() as c:
    ms._ensure_security_cols(c)   # 운영 DB 에는 이미 있는 칸(is_blocked 등) — 빈 임시 DB 라 먼저 만듦
    bm = mfi.bulk_map(c, U)
check("자동: noreply 은행 = 광고·알림(지난 메일도 모두) · 쇼핑 소식(표기 없음)·거래처·사내 = 아님", bm == {"noreply@bank-demo.example": ""}, bm)
h = T(k.get("/mail/inbox?app=1"))
_sb = h.find('<div class="mbx-sec" data-sec="box">')
side = h[_sb:h.find('<a href="/mail/blocked"', _sb)]
check("왼쪽 「📢 광고·알림」 = 스팸함 바로 위 · 끌어 놓기 자리 · 숫자 1", '<a href="/mail/inbox?ad=1"' in side and 'data-drop="ad" data-dname="광고·알림"' in side
      and side.rfind("📢 광고·알림") > side.rfind("🗑 휴지통") and '<span class="cnt">1</span>' in side, side[-600:])

print("② 끌어 놓기 묻는 창 숫자(dry) · 고른 메일부터")
r = k.post("/mail/ad-mark", data={"ids": "%d" % IDS["[가짜] 11월 소식"], "mode": "on", "dry": "1"})
j = r.json()
check("보낸 사람 1곳 · 지금 3통 · 고른 메일(11-10)부터 2통", j["ok"] and j["n_send"] == 1 and j["n_all"] == 3 and j["n_first"] == 2 and j["first"].startswith("2026-11-10"), j)
r = k.post("/mail/ad-mark", data={"ids": "%d" % IDS["[가짜] 11월 소식"], "mode": "on", "since": j["first"]})
check("「⏩ 고른 메일부터」 저장 · 날짜 돌려줌", r.json().get("ok") and r.json().get("since", "").startswith("2026-11-10"), r.text)
h = T(k.get("/mail/inbox?app=1&ad=1"))
got = NM(h)
check("📢 칸 = 11월 소식·11월 특가·은행 알림(10월 소식은 그대로 받은편지함)",
      got == {IDS["[가짜] 11월 소식"], IDS["[가짜] 11월 특가"], IDS["[가짜] 입출금 알림"]}, got)
check("📢 칸 위 띠: 3통 · 「🗑 모두 휴지통으로」 · 받은편지함 단추는 안 켜짐", "📢 <b>광고·알림</b> <span>3통" in h and "mbxAdTrash()" in h
      and '<a href="/mail/inbox" class="mbx-fold on"' not in h)
hn = T(k.get("/mail/inbox?app=1&noad=1"))
check("「광고·알림 빼기」도 같은 기준(10월 소식·견적·사내 남음)", NM(hn) == {IDS["[가짜] 10월 소식"], IDS["[가짜] 견적 부탁"], IDS["[가짜] 사내 공지"]}, NM(hn))
hi = T(k.get("/mail/inbox?app=1&who=minsu@shop-demo.example"))   # 이 사람 메일 보기 = 광고·알림도 보임(꼬리표 확인용)
row10 = hi[hi.find('data-mail-id="%d"' % IDS["[가짜] 10월 소식"]) - 300:hi.find('data-mail-id="%d"' % IDS["[가짜] 10월 소식"])]
row11 = hi[hi.find('data-mail-id="%d"' % IDS["[가짜] 11월 특가"]) - 300:hi.find('data-mail-id="%d"' % IDS["[가짜] 11월 특가"])]
check("목록 꼬리표도 날짜 기준(11월 특가 = robot · 10월 소식 = 아님)", " robot" in row11 and " robot" not in row10, (row10[-120:], row11[-120:]))

print("②-2 받은편지함에서는 빼고 📢 칸에만(대표 11-23 「광고·알림 칸에만 보이게」)")
with _db.db_session() as c:
    c.execute("UPDATE mail_messages SET is_read=0 WHERE user_id=?", (U,))
hp = T(k.get("/mail/inbox?app=1"))
check("받은편지함 그냥 목록 = 광고·알림 빠짐(10월 소식·견적·사내만)", NM(hp) == {IDS["[가짜] 10월 소식"], IDS["[가짜] 견적 부탁"], IDS["[가짜] 사내 공지"]}, NM(hp))
check("「● 안 읽음」 거르기도 같음", NM(T(k.get("/mail/inbox?app=1&unread=1"))) == NM(hp))
check("그냥 목록엔 「🔕 광고·알림 빼기」 칩 안 보임(늘 빠지므로)", "🔕 광고·알림 빼기" not in hp[hp.find('<div class="mbx-chips">'):hp.find('<div class="mbx-newbar"')])
hq = T(k.get("/mail/inbox?app=1&q=" + "특가"))
check("찾기에서는 광고·알림도 나옴(안 사라지게)", IDS["[가짜] 11월 특가"] in NM(hq), NM(hq))
check("이 사람 메일 보기에서도 나옴", IDS["[가짜] 11월 특가"] in NM(T(k.get("/mail/inbox?app=1&who=minsu@shop-demo.example"))))
cj = k.get("/api/mail/counts").json()
check("안 읽음 숫자 = 광고·알림 뺀 3(전체 안 읽음 6)", cj.get("unread") == 3, cj)
check("왼쪽 받은편지함 안 읽음 숫자도 3", 'id="mtcUnread"' in hp and re.search(r'class="mbx-fold on"[^>]*>.*?<span class="(?:mf-u|cnt|fbadge)">3<', hp, re.S) is not None or ">3</span>" in hp[hp.find('<div class="mbx-sec" data-sec="fav">'):hp.find('<div class="mbx-sec" data-sec="box">')], hp[hp.find('<div class="mbx-sec" data-sec="fav">'):][:600])
r = k.post("/mail/read-all", data={"dry": "1"})
check("「✓ 모두 읽음」 = 보이는 3통만(광고·알림은 📢 칸에서)", r.status_code == 200 and r.json().get("n") == 3, r.text[:200])
with _db.db_session() as c:
    c.execute("UPDATE mail_messages SET is_read=1 WHERE user_id=?", (U,))

print("③ 날짜 고르기 · 지난 메일도 모두 · 아님")
r = k.post("/mail/ad-mark", data={"ids": "%d" % IDS["[가짜] 11월 특가"], "mode": "on", "since": "2026-11-15"})
with _db.db_session() as c:
    bm = mfi.bulk_map(c, U)
check("📅 날짜(2026-11-15) → 그날 0시부터 · 칸 = 특가·은행", bm.get("minsu@shop-demo.example") == "2026-11-15 00:00:00"
      and NM(T(k.get("/mail/inbox?app=1&ad=1"))) == {IDS["[가짜] 11월 특가"], IDS["[가짜] 입출금 알림"]}, bm)
k.post("/mail/ad-mark", data={"ids": "%d" % IDS["[가짜] 10월 소식"], "mode": "on", "since": ""})
with _db.db_session() as c:
    on, off, since = mup.get_ad_marks3(c, U)
check("「⏪ 지난 메일도 모두」 → 날짜 표시 지우고 모두", "minsu@shop-demo.example" in on and "minsu@shop-demo.example" not in since and len(NM(T(k.get("/mail/inbox?app=1&ad=1")))) == 4)
k.post("/mail/ad-mark", data={"addr": "minsu@shop-demo.example", "mode": "off"})
check("「광고·알림 아님」 → 칸에서 빠짐(은행만)", NM(T(k.get("/mail/inbox?app=1&ad=1"))) == {IDS["[가짜] 입출금 알림"]})
r = k.post("/mail/ad-mark", data={"ids": "%d" % IDS["[가짜] 사내 공지"], "mode": "on", "dry": "1"})
check("사내 메일만 고르면 거절", not r.json()["ok"], r.text)
check("이상한 날짜 = 지난 메일도 모두로(저장 안 깨짐)", mup._since("2026-13-99x") == "" and mup._since("2026-11-01") == "2026-11-01 00:00:00")

print("④ 모두 휴지통으로 · 되돌리기")
k.post("/mail/ad-mark", data={"ids": "%d,%d" % (IDS["[가짜] 11월 소식"], IDS["[가짜] 입출금 알림"]), "mode": "on", "since": ""})
r = k.post("/mail/ad/trash", data={"dry": "1"})
check("dry = 4통(쇼핑 3 + 은행 1) · 아직 안 지움", r.json().get("n") == 4 and len(NM(T(k.get("/mail/inbox?app=1&ad=1")))) == 4, r.text)
r = k.post("/mail/ad/trash", data={"dry": "0"})
jj = r.json()
with _db.db_session() as c:
    dl = c.execute("SELECT COUNT(*) FROM mail_messages WHERE user_id=? AND is_deleted=1", (U,)).fetchone()[0]
check("휴지통으로 4통(지우지 않음 · is_deleted) · 칸 비고 · 거래처·사내는 그대로", jj["n"] == 4 and dl == 4 and not NM(T(k.get("/mail/inbox?app=1&ad=1")))
      and NM(T(k.get("/mail/inbox?app=1"))) == {IDS["[가짜] 견적 부탁"], IDS["[가짜] 사내 공지"]}, jj)
r = k.post("/mail/ad/trash", data={"undo": jj["ids"]})
check("↺ 되돌리기 = 4통 되살림", r.json().get("n") == 4 and len(NM(T(k.get("/mail/inbox?app=1&ad=1")))) == 4, r.text)
m.get_user = lambda req: None
check("로그인 안 하면 거절(표시·휴지통)", k.post("/mail/ad/trash", data={"dry": "1"}).status_code == 401 and k.post("/mail/ad-mark", data={"addr": "x@y.example"}).status_code == 401)
m.get_user = lambda req: ME

print("⑤ 화면 글·스크립트")
mv = open(os.path.join(ROOT, "app", "templates", "_v5_partials", "mail_move_ask.html"), encoding="utf-8").read()
check("묻는 창 = 「⏩ 고른 메일부터」·「⏪ 지난 메일도 모두」·「📅 이 날짜 이후」 · 미리 골라 두지 않음", "window.mailAdAsk=" in mv and "⏩ 고른 메일부터" in mv
      and "⏪ 지난 메일도 모두" in mv and "이 날짜 이후 받은 메일부터" in mv and "checked" not in mv[mv.find("window.mailAdAsk="):mv.find("window.mailMoveText=")])
check("끌어 놓기(op ad) → mailAdAsk · 오른쪽 클릭 「광고·알림으로 표시 ▸」도 같은 창", "if(op==='ad')" in h and "await mailAdAsk({ids:inb})" in h and "📢 광고·알림으로 표시(이 사람) ▸" in h
      and "await mailAdAsk({ids:ids})" in h)
check("휴지통 되돌리기 종류(adtrash)", "o.k==='adtrash' ? await mbxForm('/mail/ad/trash',{undo:o.ids||''})" in h)
node = shutil.which("node")
if node:
    bad = 0
    for s in re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", h, re.S):
        if not s.strip():
            continue
        fd, p = tempfile.mkstemp(suffix=".js")
        os.write(fd, s.encode("utf-8"))
        os.close(fd)
        rr = subprocess.run([node, "--check", p], capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL)
        if rr.returncode:
            bad += 1
            print(rr.stderr[:300])
        os.remove(p)
    check("스크립트 문법(node) — 받은편지함(광고·알림 칸)", bad == 0, bad)

print("\n결과: %d 통과 · %d 실패" % (P, F))
sys.exit(1 if F else 0)
