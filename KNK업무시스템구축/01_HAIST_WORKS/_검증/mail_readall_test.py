# -*- coding: utf-8 -*-
"""메일 「폴더마다 안 읽음 · ✓ 모두 읽음 · ↩ 회신 필요 한 번에 처리」 (대표 2026-11-22 「진행해」) — 운영 무접촉 · 임시 DB(knk_mra_*) · 가짜 사람·가짜 메일만.

증명할 것
  ① 폴더 줄 = 회색 전체 수 + 파란 동그라미 안 읽음 수(받은편지함 줄과 같은 모양) · 다 읽은 폴더는 회색만
  ② 메일을 읽으면 폴더 안 읽음 수가 바로 줄어듦(예전엔 새 메일이 와야 다시 셈 — 함께 고침)
  ③ ✓ 모두 읽음: 폴더 → 그 폴더만 · 받은편지함 → 안 읽음 숫자 0 · 먼저 셈(dry) · ↺ 되돌리기 = 방금 바꾼 것만 · 남의 메일 안 건드림
  ④ ↩ 회신 필요 ✓ 모두 처리: 숫자 0 · 메일 안 보냄 · 👔 윗분 지시 몇 통인지 · 고른 것만도 · ↺ 되돌리기 = 「회신 필요로 표시」했던 것은 그 표시로
  ⑤ 화면: 줄마다 ✓ 단추 · 손가락 화면 칩 · 회신 필요 목록 고를 때 「✓ 회신 안 해도 됨」 · 스크립트 문법(node) · 파이썬 3.8
"""
import ast
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
    _TMP = tempfile.mkdtemp(prefix="knk_mra_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as MS
    from app import mail_folders as MF
    from app import mail_reply as MR
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
UID, OTHER = 9890, 9892
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x', email=NULL")
    c.execute("INSERT INTO teams(id, code, name, display_order) VALUES(9891,'T9891','시험영업팀',3)")
    c.execute("INSERT INTO users(id, login_id, name, rank, role, team_id, is_active, password, email) VALUES(9890,'t_me','시험신입','사원','member',9891,1,'x','me" + D + "')")
    c.execute("INSERT INTO users(id, login_id, name, rank, role, team_id, is_active, password, email) VALUES(9892,'t_oth','시험남','대리','member',9891,1,'x','oth" + D + "')")
    c.execute("INSERT INTO users(id, login_id, name, rank, role, team_id, is_active, password, email) VALUES(9894,'t_ceo','시험대표','대표이사','member',9891,1,'x','ceo" + D + "')")
    MS._ensure_security_cols(c)

    def put(frm, subj, body="가짜 본문", read=0, uid=UID, blocked=0, arc=0, hours_ago=1):
        c.execute("INSERT INTO mail_messages(user_id, direction, from_email, from_name, to_email, subject, body_text, is_read, is_deleted, received_at) "
                  "VALUES(?,'in',?,?,?,?,?,?,0,datetime('now','localtime',?))",
                  (uid, frm, "가짜", "me" + D, subj, body, read, "-%d hours" % hours_ago))
        mid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        if blocked:
            c.execute("UPDATE mail_messages SET is_blocked=1 WHERE id=?", (mid,))
        if arc:
            c.execute("UPDATE mail_messages SET is_archived=1 WHERE id=?", (mid,))
        return mid
    H = [put("han@dream-demo.example", "드림 안내 %d" % i, hours_ago=30 + i) for i in range(3)]
    H_READ = put("han@dream-demo.example", "드림 읽은 것", read=1, hours_ago=40)
    H_ARC = put("han@dream-demo.example", "드림 보관 안 읽음", arc=1, hours_ago=41)
    O = [put("oh@part-demo.example", "파트 안내 %d" % i, hours_ago=50 + i) for i in range(2)]
    G1 = put("z@etc-demo.example", "어디에도 안 걸린 안내", hours_ago=60)
    SP1 = put("x@spam-demo.example", "스팸", blocked=1, hours_ago=61)
    OTH = put("han@dream-demo.example", "남의 메일", uid=OTHER, hours_ago=2)
    # 회신 필요(규칙으로 추정) — 바깥 요청 2 · 윗분 지시 1 · 직접 「회신 필요로 표시」 1
    R1 = put("q1@ask-demo.example", "견적 요청드립니다", body="안녕하세요.\n견적서 확인 후 회신 부탁드립니다.\n감사합니다.", hours_ago=3)
    R2 = put("q2@ask2-demo.example", "자료 문의", body="안녕하세요.\n지난번 자료 언제 받을 수 있을까요?\n회신 부탁드립니다.", hours_ago=4)
    RB = put("ceo" + D, "보고서", body="내일 오전까지 보고서 정리해서 보내주세요.", hours_ago=5)
    RN = put("n@note-demo.example", "그냥 안내", body="참고하세요.", hours_ago=6)
    MR.set_mark(c, UID, RN, "need")
    # 폴더: 1.고객사 아래 시험드림·시험파트(주소 규칙)
    GF = MF.add_folder(c, UID, "1.고객사", None, "customer")
    FA = MF.add_folder(c, UID, "시험드림", GF, "")
    FB = MF.add_folder(c, UID, "시험파트", GF, "")
    MF.set_rule(c, UID, FA, "han@dream-demo.example")
    MF.set_rule(c, UID, FB, "oh@part-demo.example")

ME = {"id": UID, "role": "member", "name": "시험신입", "rank": "사원", "team_id": 9891, "login_id": "t_me", "email": "me" + D, "lang": "ko"}
m.get_user = lambda req: ME
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})
KA, KB, KG = "f%d" % FA, "f%d" % FB, "f%d" % GF


def unread_of(ids):
    with _db.db_session() as c:
        return sum(1 for i in ids if not c.execute("SELECT is_read FROM mail_messages WHERE id=?", (i,)).fetchone()[0])


def row_of(html, name):
    mm = re.search(r'<span class="fname">' + re.escape(name) + r'</span>(.*?)</a>', html, re.S)
    return mm.group(1) if mm else ""


print("① 폴더 줄 = 전체(회색) + 안 읽음(파란 동그라미)")
h = k.get("/mail/inbox").text
ra = row_of(h, "시험드림")
check("시험드림: 전체 5 · 안 읽음 4(보관한 안 읽음 포함 · 스팸·남의 메일 빼고)",
      '<span class="mf-n">5</span><span class="mf-u">4</span>' in ra, ra[:300])
check("시험드림 줄에 ✓ 단추(그 폴더만)", ("mbxReadAll(event,'%s')" % KA) in ra, ra[:300])
rg = row_of(h, "1.고객사")
check("1.고객사 묶음: 전체 7 · 안 읽음 6", '<span class="mf-n">7</span><span class="mf-u">6</span>' in rg, rg[:300])
check("받은편지함 줄 ✓ 모두 읽음 · 회신 필요 줄 ✓ 모두 처리",
      "mbxReadAll(event,'')" in h and "return mbxReplyAll(event)" in h and "✓ 모두 처리" in h)

print("② 읽으면 폴더 숫자가 바로 줄어듦(새 메일 없이)")
j = k.post("/mail/bulk", data={"op": "read", "ids": str(H[0])}).json()
h = k.get("/mail/inbox").text
ra = row_of(h, "시험드림")
check("한 통 읽음 → 시험드림 안 읽음 3", j.get("ok") and '<span class="mf-n">5</span><span class="mf-u">3</span>' in ra, ra[:300])
k.post("/mail/bulk", data={"op": "unread", "ids": str(H[0])})
h = k.get("/mail/inbox").text
check("다시 안 읽음 → 4", '<span class="mf-u">4</span>' in row_of(h, "시험드림"))

print("③ ✓ 모두 읽음")
j = k.post("/mail/read-all", data={"fd": KA, "dry": "1"}).json()
check("폴더 셈(dry) = 4 · 이름 · 바꾸지 않음", j.get("n") == 4 and j.get("name") == "시험드림" and j.get("dry") and unread_of(H + [H_ARC]) == 4, j)
j = k.post("/mail/read-all", data={"fd": KA}).json()
ids_a = j.get("ids") or ""
check("폴더 모두 읽음 = 4통 · 그 폴더만(파트·일반·남의 메일 그대로)",
      j.get("n") == 4 and unread_of(H + [H_ARC]) == 0 and unread_of(O) == 2 and unread_of([G1]) == 1 and unread_of([OTH]) == 1, j)
h = k.get("/mail/inbox").text
ra, rg = row_of(h, "시험드림"), row_of(h, "1.고객사")
check("다 읽은 폴더 = 회색 전체만(동그라미·✓ 없음) · 묶음 안 읽음 2",
      '<span class="mf-n">5</span>' in ra and "mf-u" not in ra and "mf-ra" not in ra and '<span class="mf-u">2</span>' in rg, ra[:200] + " | " + rg[:200])
j = k.post("/mail/read-all/undo", data={"ids": ids_a}).json()
check("↺ 되돌리기 = 방금 바꾼 4통만 다시 안 읽음", j.get("n") == 4 and unread_of(H + [H_ARC]) == 4 and unread_of([H_READ]) == 0, j)
j = k.post("/mail/read-all", data={"fd": "f999999"})
check("없는 폴더 → 400", j.status_code == 400)
j = k.post("/mail/read-all", data={"fd": KG, "dry": "1"}).json()
check("묶음(1.고객사) 셈 = 아래 폴더 모두 6", j.get("n") == 6, j)
with _db.db_session() as c:
    before = MS.count_unread(c, UID)
j = k.post("/mail/read-all", data={"dry": "1"}).json()
check("받은편지함 셈 = 안 읽음 숫자와 같음(%d)" % before, j.get("n") == before and before > 0, j)
j = k.post("/mail/read-all", data={}).json()
with _db.db_session() as c:
    after = MS.count_unread(c, UID)
check("받은편지함 모두 읽음 → 안 읽음 0 · 남의 메일 그대로", j.get("ok") and after == 0 and unread_of([OTH]) == 1, (j.get("n"), after))
j2 = k.post("/mail/read-all", data={"dry": "1"}).json()
check("다 읽은 뒤 셈 = 0", j2.get("n") == 0, j2)
h = k.get("/mail/inbox").text
check("안 읽음 0 → 받은편지함 ✓ 단추 없음", "mbxReadAll(event,'')" not in h)
j = k.post("/mail/read-all/undo", data={"ids": j.get("ids") or ""}).json()
with _db.db_session() as c:
    check("↺ 받은편지함 되돌리기 → 다시 %d" % before, MS.count_unread(c, UID) == before, j)
j = k.post("/mail/read-all/undo", data={"ids": str(OTH)}).json()
check("남의 메일 번호를 보내도 안 바뀜", j.get("n") == 0 and unread_of([OTH]) == 1, j)

print("④ ↩ 회신 필요 ✓ 모두 처리")
with _db.db_session() as c:
    rm = MR.scan(c, UID)
check("시험 준비: 회신 필요에 R1·R2·윗분·직접 표시", all(i in rm for i in (R1, R2, RB, RN)), sorted(rm))
N0 = len(rm)
j = k.post("/mail/reply/done-all", data={"dry": "1"}).json()
check("셈 = 회신 필요 수 · 👔 윗분 지시 1통", j.get("n") == N0 and j.get("boss") == 1, j)
j = k.post("/mail/reply/done-all", data={}).json()
with _db.db_session() as c:
    rm2 = MR.scan(c, UID)
    sent = c.execute("SELECT COUNT(*) FROM mail_messages WHERE direction='out'").fetchone()[0]
check("모두 처리 → 회신 필요 0 · 메일 안 보냄", j.get("n") == N0 and not rm2 and sent == 0, (j, len(rm2), sent))
check("되돌리기 글에 직접 표시했던 메일은 「need」", ("%d:need" % RN) in (j.get("undo") or ""), j.get("undo"))
h = k.get("/mail/inbox").text
check("회신 필요 0 → ✓ 모두 처리 단추 없음", "return mbxReplyAll(event)" not in h)
j = k.post("/mail/reply/done-all/undo", data={"undo": j.get("undo") or ""}).json()
with _db.db_session() as c:
    rm3 = MR.scan(c, UID)
    st_rn = c.execute("SELECT state FROM mail_reply_marks WHERE user_id=? AND mail_id=?", (UID, RN)).fetchone()
check("↺ 되돌리기 → 회신 필요 그대로 돌아옴 · 직접 표시는 「need」로", j.get("n") == N0 and len(rm3) == N0 and st_rn and st_rn[0] == "need", (j, len(rm3), st_rn and st_rn[0]))
j = k.post("/mail/reply/done-all", data={"ids": "%d,%d" % (R1, OTH)}).json()
with _db.db_session() as c:
    rm4 = MR.scan(c, UID)
check("고른 것만(R1) · 남의 메일 번호는 무시", j.get("n") == 1 and R1 not in rm4 and R2 in rm4 and len(rm4) == N0 - 1, (j, len(rm4)))
k.post("/mail/reply/done-all/undo", data={"undo": j.get("undo") or ""})
with _db.db_session() as c:
    check("고른 것 되돌리기 → R1 다시 회신 필요", R1 in MR.scan(c, UID))

print("⑤ 화면 · 문법")
h = k.get("/mail/inbox?reply=1").text
check("회신 필요 목록: 고를 때 막대 「✓ 회신 안 해도 됨」 · 손가락 화면 칩 「✓ 모두 처리」",
      "mbxReplyPicked()" in h and 'class="mbx-chip mbx-chip-ra" onclick="return mbxReplyAll(event)"' in h)
h = k.get("/mail/inbox?fd=" + KA).text
check("폴더 보기: 손가락 화면 칩 = 그 폴더 ✓ 모두 읽음", ('class="mbx-chip mbx-chip-ra" onclick="return mbxReadAll(event,\'%s\')"' % KA) in h)
check("넓은 화면(마우스)은 칩 숨김 · 줄 ✓ 는 마우스 올릴 때만", "@media (hover:hover) and (pointer:fine){.mbx-chip-ra{display:none !important}}" in h
      and "@media (hover:hover){.mbx-fold:hover .mf-ra" in h)
check("확인 창에 몇 통 · 되돌리기 · 메일 안 보냄 안내", "통을 모두 읽음으로 할까요" in h and "메일은 보내지 않아요" in h and "↺ 되돌리기" in h)
# 시연에서 잡힌 것: 「모두 처리」는 보낼 칸이 없어 빈 FormData → 서버가 못 읽음(500) — 화면은 늘 한 칸('_')을 보냄
check("화면이 늘 한 칸('_')을 보냄(빈 요청 500 막기)", "fd.append('_', '1')" in h)
j = k.post("/mail/reply/done-all", files={"_": (None, "1")})
check("여러 부분(multipart) 요청 · 칸 '_' 하나 → 정상(셈은 dry 아님이라 처리)", j.status_code == 200 and j.json().get("ok"), j.text[:200])
if j.status_code == 200:
    k.post("/mail/reply/done-all/undo", files={"undo": (None, j.json().get("undo") or "")})
with _db.db_session() as c:
    check("되돌린 뒤 회신 필요 그대로 %d" % N0, len(MR.scan(c, UID)) == N0)
node = shutil.which("node")
if node:
    bad = 0
    for s in re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", h, re.S):
        if not s.strip():
            continue
        fd, p = tempfile.mkstemp(suffix=".js")
        os.write(fd, s.encode("utf-8"))
        os.close(fd)
        r = subprocess.run([node, "--check", p], capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL)
        if r.returncode:
            bad += 1
            print(r.stderr[:300])
        os.remove(p)
    check("받은편지함 화면 스크립트 문법(node)", bad == 0, bad)
else:
    print("  (node 없음 — 문법 시험 건너뜀)")
for f in ("app/main.py", "app/mail_store.py", "app/mail_reply.py", "app/mail_folders.py"):
    try:
        ast.parse(io.open(f, encoding="utf-8").read(), feature_version=(3, 8))
        check("파이썬 3.8 문법 " + f, True)
    except SyntaxError as e:
        check("파이썬 3.8 문법 " + f, False, e)

print("\n결과: %d 통과 · %d 실패" % (P, F))
sys.exit(1 if F else 0)
