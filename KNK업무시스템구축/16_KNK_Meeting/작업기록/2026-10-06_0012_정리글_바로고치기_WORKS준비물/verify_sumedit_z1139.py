# -*- coding: utf-8 -*-
"""z1139 서버 시험 — 「📋 회의록 정리」 글을 사람이 바로 고친다 (대표 지시 2026-10-05)
  A. 문지기 — 로그인·본문·없는 회의록
  B. 고쳐진다 — 그 글 그대로 저장 · 🔴 AI 를 부르지 않는다 · 결정사항·할 일·원문은 그대로
  C. 권한 — 참석자도 됨(z1133) · 남은 403 · 🗑 삭제 권한과는 무관
  D. 먼저 저장 충돌(base_ts) — 다른 곳에서 먼저 저장됐으면 409
  E. 가장자리 — 같은 글이면 changed=false · 빈 글 · 아주 긴 글 · 줄바꿈 보존
실행: 앱 사본 폴더에서 py -3.13 <이 파일>
🔴 운영에 닿는 것 없음 — AI 키 비움 · 이음 서버 안 부름"""
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
from app import ai_client                      # noqa: E402
from app.database import db_session            # noqa: E402

OK = FAIL = 0
FAILS = []
AI_CALLS = []


def chk(cond, name, extra=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  [PASS] {name}" + (f" · {extra}" if extra != "" else ""))
    else:
        FAIL += 1
        FAILS.append(name)
        print(f"  [FAIL] {name} {extra}")


# 🔴 AI 를 부르면 바로 알 수 있게 가로챈다(이 기능은 AI 를 부르면 안 된다)
def _no_ai(*a, **k):
    AI_CALLS.append("ai_extract_meeting")
    return (False, {})


ai_client.ai_extract_meeting = _no_ai
ai_client.ai_transcribe = lambda *a, **k: (AI_CALLS.append("ai_transcribe"), (False, ""))[1]

client = TestClient(M.app)
client.__enter__()

with db_session() as c:
    CEO_ID = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET role='ceo', name='김정락' WHERE id=?", (CEO_ID,))
    c.execute("DELETE FROM users WHERE login_id IN ('z39_owner','z39_att','z39_out')")

    def mk(name, login):
        return c.execute("INSERT INTO users(name, login_id, password, role, is_active) "
                         "VALUES(?,?,'x','member',1)", (name, login)).lastrowid

    OWNER = mk("안지연", "z39_owner")
    ATT = mk("이한중", "z39_att")
    OUT = mk("박주창", "z39_out")
    c.execute("DELETE FROM meetings")
    c.execute("DELETE FROM meeting_attendees")
    AI_SUM = "핵심: 주요 설비의 구매·검수를 일정에 맞춰 마무리한다.\n[구매·제작 일정]\n- 방앗간 공장은 1차 검토를 완료"
    MID = c.execute(
        "INSERT INTO meetings(title, meeting_date, mode, owner_id, location, tags, attendees_text, body, summary, "
        "audio_path, visibility, status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        ("10월 주간회의", "2026-10-05", "B", OWNER, "본사 회의실", "주간", "김정락, 이한중",
         "회의 원문입니다 [음성 변환]", AI_SUM, "", "private", "draft")).lastrowid
    c.execute("INSERT INTO meeting_attendees(meeting_id, user_id, name) VALUES(?,?,'이한중')", (MID, ATT))
    c.execute("INSERT INTO meeting_decisions(meeting_id, who, what, due, source) VALUES(?,?,?,?,'ai')",
              (MID, "이한중", "10월 16일까지 발주", ""))
    c.execute("INSERT INTO meeting_actions(meeting_id, assignee_name, task, due_date, source) "
              "VALUES(?,?,?,?,'ai')", (MID, "안지연", "출하공대 부품 준비", ""))

USERS = {}
with db_session() as c:
    for uid in (CEO_ID, OWNER, ATT, OUT):
        USERS[uid] = dict(c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())
AS = {"u": None}
M.get_user = lambda req: AS["u"]


def as_user(uid):
    AS["u"] = USERS.get(uid) if uid else None


def ts(mid=None):
    with db_session() as c:
        return c.execute("SELECT updated_at FROM meetings WHERE id=?", (mid or MID,)).fetchone()[0]


def summ(mid=None):
    with db_session() as c:
        return c.execute("SELECT COALESCE(summary,'') FROM meetings WHERE id=?", (mid or MID,)).fetchone()[0]


def save(text, base=None, mid=None, path="summary"):
    body = {"summary": text}
    if base is not None:
        body["base_ts"] = base
    r = client.post(f"/api/meeting/{mid or MID}/{path}", json=body)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {}


# ═══ A. 문지기 ═══════════════════════════════════════════════════════════════
print("\n■ A. 문지기", flush=True)
as_user(None)
st, d = save("남이 고침")
chk(st == 401, "A1 로그인 안 하면 401", st)
as_user(OWNER)
r = client.post(f"/api/meeting/{MID}/summary", content=b"not-json",
                headers={"Content-Type": "application/json"})
chk(r.status_code == 400, "A2 본문이 JSON 이 아니면 400", r.status_code)
r = client.post(f"/api/meeting/{MID}/summary", json={"base_ts": ts()})
chk(r.status_code == 400, "A3 정리 글 칸이 없으면 400", r.status_code)
st, d = save("아무 글", base=None, mid=99999)
chk(st == 404, "A4 없는 회의록은 404", st)
chk(summ() != "아무 글", "A5 그래도 원래 글은 그대로")

# ═══ B. 고쳐진다 ═════════════════════════════════════════════════════════════
print("\n■ B. 고친 글이 그대로 저장된다", flush=True)
as_user(OWNER)
NEW = "핵심: 주요 설비의 구매·검수를 일정에 맞춰 마무리한다.\n[구매·제작 일정]\n- 반월 공장은 1차 검토를 완료"
st, d = save(NEW, base=ts())
chk(st == 200 and d.get("ok") is True and d.get("changed") is True, "B1 저장 200", d)
chk(summ() == NEW, "B2 고친 글이 그대로 들어갔다(「방앗간」→「반월」)", summ()[-22:])
chk(not AI_CALLS, "B3 🔴 AI 를 부르지 않았다", AI_CALLS)
with db_session() as c:
    body = c.execute("SELECT body FROM meetings WHERE id=?", (MID,)).fetchone()[0]
    nd = c.execute("SELECT COUNT(*) FROM meeting_decisions WHERE meeting_id=?", (MID,)).fetchone()[0]
    na = c.execute("SELECT COUNT(*) FROM meeting_actions WHERE meeting_id=?", (MID,)).fetchone()[0]
    loc = c.execute("SELECT location, tags, title FROM meetings WHERE id=?", (MID,)).fetchone()
chk("[음성 변환]" in body, "B4 회의 원문은 그대로")
chk(nd == 1 and na == 1, "B5 결정사항·할 일도 그대로", (nd, na))
chk(loc[0] == "본사 회의실" and loc[1] == "주간" and loc[2] == "10월 주간회의",
    "B6 장소·태그·제목도 안 건드린다", tuple(loc))
chk(d.get("updated_at") and d["updated_at"] == ts(), "B7 새 시각을 돌려준다(화면이 이어 쓸 수 있게)", d.get("updated_at"))
with db_session() as c:
    act = c.execute("SELECT COUNT(*) FROM activities WHERE kind='meeting_summary_edit'").fetchone()[0]
chk(act >= 1, "B8 누가 고쳤는지 활동기록에 남는다", act)

# ═══ C. 권한 ═════════════════════════════════════════════════════════════════
print("\n■ C. 권한 — 참석자도 고칠 수 있다(z1133)", flush=True)
as_user(ATT)
st, d = save(NEW + "\n- 참석자가 한 줄 더", base=ts())
chk(st == 200 and d.get("ok"), "C1 참석자도 고칠 수 있다", st)
chk("참석자가 한 줄 더" in summ(), "C2 그 글이 들어갔다")
as_user(OUT)
before = summ()
st, d = save("남이 고침", base=ts())
chk(st == 403, "C3 참석자가 아닌 직원은 403", st)
chk(summ() == before, "C4 그 글은 그대로")
as_user(CEO_ID)
st, d = save(before, base=ts())
chk(st == 200, "C5 대표/관리자는 된다", st)

# ═══ D. 먼저 저장 충돌 ═══════════════════════════════════════════════════════
print("\n■ D. 다른 곳에서 먼저 저장됐을 때", flush=True)
as_user(OWNER)
old_ts = ts()
with db_session() as c:     # 다른 사람이 먼저 저장한 것처럼
    c.execute("UPDATE meetings SET title='다른 곳에서 먼저 저장', updated_at=datetime('now','localtime','+5 seconds') "
              "WHERE id=?", (MID,))
keep = summ()
st, d = save("충돌 중에 고침", base=old_ts)
chk(st == 409, "D1 먼저 저장됐으면 409", st)
chk(summ() == keep, "D2 그때는 글을 바꾸지 않는다")
st, d = save("이제 고침", base=ts())
chk(st == 200, "D3 새 시각으로 다시 보내면 저장된다", st)

# ═══ E. 가장자리 ═════════════════════════════════════════════════════════════
print("\n■ E. 가장자리", flush=True)
as_user(OWNER)
st, d = save("이제 고침", base=ts())
chk(st == 200 and d.get("changed") is False, "E1 같은 글이면 changed=false(괜히 안 쓴다)", d)
st, d = save("한 줄\n두 줄\n\n네 줄", base=ts())
chk(summ() == "한 줄\n두 줄\n\n네 줄", "E2 줄바꿈이 그대로 남는다", repr(summ()))
st, d = save("   앞뒤 빈칸   ", base=ts())
chk(summ() == "앞뒤 빈칸", "E3 앞뒤 빈칸은 다듬는다", repr(summ()))
st, d = save("", base=ts())
chk(st == 200 and summ() == "", "E4 비우는 것도 된다(아직 정리 전으로 돌아감)", (st, repr(summ())))
long_txt = "가" * 25000
st, d = save(long_txt, base=ts())
chk(st == 200 and len(summ()) == 20000, "E5 아주 긴 글은 20000자까지만", len(summ()))
chk(not AI_CALLS, "E6 🔴 시험 내내 AI 를 한 번도 부르지 않았다", AI_CALLS)

print("\n" + "=" * 68)
print(f"합계: 통과 {OK} · 실패 {FAIL}")
for f in FAILS:
    print("  - 실패:", f)
sys.exit(1 if FAIL else 0)
