# -*- coding: utf-8 -*-
"""z1131 서버 시험 — 「⏹ 회의 종료」(예정 끝 시각 전에 끝났을 때 · 대표 지시 2026-09-27)
  ① 칸이 생긴다(meetings.ended_at · 마이그)
  ② 누가 누를 수 있나 — 작성자·관리자/대표·이음 등록자 O / 그 밖 X / 로그인 안 하면 X
  ③ 한 번 더 누르면 already · 되돌리기(undo)면 비워진다
  ④ 이음·모아보기에 넘기는 칸에 ended·ended_at 이 실린다
  ⑤ 없는 회의는 404 · 종료해도 회의록·녹음은 그대로
실행: 앱 사본 폴더에서 py -3.13 <이 파일>
🔴 운영에 닿는 것 없음 — AI 키 비움 · 이음은 부르지 않는다(이 입구는 이음을 안 부른다)"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("KNK_SECRET_KEY", "verify-only-key")
os.environ["KNK_MESSENGER_SSO_INTERNAL_BASE"] = "http://127.0.0.1:9"
for _k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "KNK_OPENAI_API_KEY"):
    os.environ[_k] = ""
sys.path.insert(0, os.getcwd())

from fastapi.testclient import TestClient      # noqa: E402
from app import main as M                      # noqa: E402
from app import sso_client as SC               # noqa: E402
from app.database import db_session            # noqa: E402

OK = FAIL = 0
FAILS = []


def chk(cond, name, extra=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  [PASS] {name}" + (f" · {extra}" if extra != "" else ""))
    else:
        FAIL += 1
        FAILS.append(name)
        print(f"  [FAIL] {name} {extra}")


KEY = "test-service-key-z1131"
SC.get_service_key = lambda: KEY
client = TestClient(M.app)
client.__enter__()          # 기동(startup) 실행 — 표·마이그가 여기서 만들어진다

with db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col in ("employee_no",):
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN employee_no TEXT")
    CEO_ID = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET role='ceo', employee_no='T0001', name='김정락' WHERE id=?", (CEO_ID,))

    def mk_user(name, login, role, emp):
        return c.execute("INSERT INTO users(name, login_id, password, role, is_active, employee_no) "
                         "VALUES(?,?,?,?,1,?)", (name, login, "x", role, emp)).lastrowid
    OWNER_ID = mk_user("안지연", "t_owner", "member", "T0086")
    ORG_ID = mk_user("이한중", "t_org", "member", "T0002")
    OTHER_ID = mk_user("박주창", "t_other", "member", "T0003")
    c.execute("DELETE FROM meetings")

    def mtg(title, owner, msg_id=None, organizer=None):
        return c.execute(
            "INSERT INTO meetings(title, meeting_date, mode, owner_id, location, tags, attendees_text, body, summary, "
            "audio_path, visibility, status, msg_meeting_id, msg_organizer_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (title, "2026-09-27", "B", owner, "", "", "", "", "", "", "all", "draft", msg_id, organizer)).lastrowid

    M1 = mtg("M1 이음 회의(작성자=안지연 · 등록=이한중)", OWNER_ID, 9801, ORG_ID)
    M2 = mtg("M2 이음 회의 · 등록자가 끝낸다", OWNER_ID, 9802, ORG_ID)
    M3 = mtg("M3 이음 회의 · 권한 없는 사람", OWNER_ID, 9803, ORG_ID)
    M4 = mtg("M4 이음과 무관한 회의", OWNER_ID)

USERS = {}
with db_session() as c:
    for uid in (CEO_ID, OWNER_ID, ORG_ID, OTHER_ID):
        USERS[uid] = dict(c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())
AS = {"u": None}
M.get_user = lambda req: AS["u"]


def end(mid, uid, undo=False):
    AS["u"] = USERS.get(uid) if uid else None
    return client.post(f"/api/meeting/{mid}/end", json={"undo": undo})


def ended_at(mid):
    with db_session() as c:
        r = c.execute("SELECT ended_at FROM meetings WHERE id=?", (mid,)).fetchone()
    return ((dict(r).get("ended_at") if r else "") or "")


print("\n■ ① 칸이 생겼나(마이그)", flush=True)
with db_session() as c:
    cols = {r[1] for r in c.execute("PRAGMA table_info(meetings)")}
chk("ended_at" in cols, "meetings.ended_at 칸이 있다", sorted(cols)[-3:])
chk(ended_at(M1) == "", "처음에는 비어 있다")

print("\n■ ② 누가 누를 수 있나", flush=True)
r = end(M1, None)
chk(r.status_code == 401, "로그인 안 하면 401", r.status_code)
chk(ended_at(M1) == "", "그래도 비어 있다")

r = end(M3, OTHER_ID)
chk(r.status_code == 403, "그냥 직원은 403", r.status_code)
chk(ended_at(M3) == "", "그래도 비어 있다")

r = end(M1, OWNER_ID)
chk(r.status_code == 200 and r.json().get("ok") and r.json().get("ended") is True, "작성자(총괄)는 종료할 수 있다", r.json())
chk(len(ended_at(M1)) >= 16, "끝낸 시각이 적힌다", ended_at(M1))

r = end(M2, ORG_ID)
chk(r.status_code == 200 and r.json().get("ended") is True, "이음 등록자도 종료할 수 있다", r.json())

r = end(M4, CEO_ID)
chk(r.status_code == 200 and r.json().get("ended") is True, "대표/관리자는 어떤 회의든 종료할 수 있다", r.json())

print("\n■ ③ 두 번 누르기 · 되돌리기", flush=True)
r = end(M1, OWNER_ID)
chk(r.status_code == 200 and r.json().get("already") is True, "이미 끝난 회의는 already", r.json())
first = ended_at(M1)
chk(first and ended_at(M1) == first, "끝낸 시각은 그대로(덮어쓰지 않는다)", first)

r = end(M1, OWNER_ID, undo=True)
chk(r.status_code == 200 and r.json().get("ended") is False, "되돌리면 ended=False", r.json())
chk(ended_at(M1) == "", "칸이 비워진다")
r = end(M1, OWNER_ID)
chk(r.json().get("ended") is True and not r.json().get("already"), "되돌린 뒤 다시 종료할 수 있다", r.json())

print("\n■ ④ 이음·모아보기에 넘기는 칸", flush=True)
AS["u"] = USERS[CEO_ID]
r = client.post("/api/meeting/msg/status", headers={"X-SSO-Service-Key": KEY},
                json={"msg_meeting_ids": [9801, 9802, 9803], "employee_no": "T0001"})
chk(r.status_code == 200, "msg/status 200", r.status_code)
items = (r.json() or {}).get("items") or {}
chk(items.get("9801", {}).get("ended") is True, "끝낸 회의는 ended=True", items.get("9801"))
chk(bool(items.get("9801", {}).get("ended_at")), "끝낸 시각도 함께 넘어간다", items.get("9801", {}).get("ended_at"))
chk(items.get("9803", {}).get("ended") is False, "안 끝낸 회의는 ended=False", items.get("9803"))

        # 모아보기 탭 카드 자료(msg-cards)는 이음 서버가 있어야 목록이 온다 — 여기서는 코드에 칸이 실리는지만 본다
src = open(os.path.join("app", "main.py"), encoding="utf-8").read()
_i = src.find("async def api_meetings_msg_cards") if "async def api_meetings_msg_cards" in src else src.find("msg-cards")
chk('"ended": _meeting_ended(m)' in src[_i:_i + 20000], "모아보기 카드 자료에도 ended 를 싣는다(코드)")
tpl = open(os.path.join("app", "templates", "meetings.html"), encoding="utf-8").read()
chk("if (mn.ended === true) return 'end';" in tpl, "모아보기 카드가 ended 를 시간보다 먼저 본다(코드)")

print("\n■ ⑤ 없는 회의 · 회의록은 그대로", flush=True)
r = end(999999, CEO_ID)
chk(r.status_code == 404, "없는 회의는 404", r.status_code)
with db_session() as c:
    row = dict(c.execute("SELECT title, status, body FROM meetings WHERE id=?", (M1,)).fetchone())
chk(row["title"].startswith("M1") and row["status"] == "draft", "회의록 내용·상태는 그대로", row["title"][:20])

print("\n" + "=" * 68)
print(f"합계: 통과 {OK} · 실패 {FAIL}")
for f in FAILS:
    print("  - 실패:", f)
sys.exit(1 if FAIL else 0)
