# -*- coding: utf-8 -*-
"""z1133 서버 시험 — 회의 **참석자**도 녹음·녹음파일 올리기·회의록 작성·회의 종료 (대표 지시 2026-09-28/29)
  ① 참석자가 할 수 있는 것: 본문 저장 · 🔄 다시 정리 · 결정사항/할 일 추가·삭제 · 📁 녹음 파일 올리기 ·
     녹음 시작/조각/끝내기 · 음성→글자 · 공유로 받은 음성 붙이기 · 프로젝트 연결 · ⏹ 회의 종료
  ② 참석자가 **못 하는 것**: 🗑 회의록 삭제(작성자·관리자/대표만 — 대표 결정으로 넓히지 않음)
  ③ 참석자가 아닌 직원: 전부 막힘(보기도 private 이면 막힘)
  ④ 이름만 있는 외부 참석자(계정 없음)는 영향 없음 · 작성자·등록자·대표는 예전 그대로
실행: 앱 사본 폴더에서 py -3.13 <이 파일>
🔴 운영에 닿는 것 없음 — AI 키 비움 · 이음 서버 안 부름 · 파일은 이 사본 폴더 안에서만"""
import io
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


client = TestClient(M.app)
client.__enter__()

with db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    if "employee_no" not in have:
        c.execute("ALTER TABLE users ADD COLUMN employee_no TEXT")
    CEO_ID = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET role='ceo', employee_no='T0001', name='김정락' WHERE id=?", (CEO_ID,))

    def mk_user(name, login, emp):
        return c.execute("INSERT INTO users(name, login_id, password, role, is_active, employee_no) "
                         "VALUES(?,?,?,'member',1,?)", (name, login, "x", emp)).lastrowid
    OWNER = mk_user("안지연", "t_owner", "T0086")      # 회의록 작성자
    ATT = mk_user("이한중", "t_att", "T0002")          # 참석자(계정 연결)
    ATT2 = mk_user("윤경호", "t_att2", "T0004")        # 참석자 2
    ORG = mk_user("최홍광", "t_org", "T0005")          # 이음 등록 담당
    OUT = mk_user("박주창", "t_out", "T0003")          # 참석자 아님
    c.execute("DELETE FROM meetings")
    c.execute("DELETE FROM meeting_attendees")

    def mtg(title, owner, msg_id=None, organizer=None, vis="private"):
        return c.execute(
            "INSERT INTO meetings(title, meeting_date, mode, owner_id, location, tags, attendees_text, body, summary, "
            "audio_path, visibility, status, msg_meeting_id, msg_organizer_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (title, "2026-09-29", "B", owner, "", "", "이한중, 윤경호, 외부 홍길동", "회의 원문", "", "",
             vis, "draft", msg_id, organizer)).lastrowid

    M1 = mtg("M1 이음 회의(참석자 있음)", OWNER, 9901, ORG)
    M2 = mtg("M2 참석자 없는 회의", OWNER)
    for uid, nm in ((ATT, "이한중"), (ATT2, "윤경호")):
        c.execute("INSERT INTO meeting_attendees(meeting_id, user_id, name) VALUES(?,?,?)", (M1, uid, nm))
    c.execute("INSERT INTO meeting_attendees(meeting_id, user_id, name) VALUES(?,NULL,?)", (M1, "외부 홍길동"))

USERS = {}
with db_session() as c:
    for uid in (CEO_ID, OWNER, ATT, ATT2, ORG, OUT):
        USERS[uid] = dict(c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())
AS = {"u": None}
M.get_user = lambda req: AS["u"]

AUDIO = "meeting_audio"
os.makedirs(AUDIO, exist_ok=True)


def as_user(uid):
    AS["u"] = USERS.get(uid) if uid else None


def wav_bytes(n=2048):
    return b"RIFF" + (b"\0" * n)


print("\n■ ① 참석자가 할 수 있는 것 (이한중 = 참석자)", flush=True)
as_user(ATT)
r = client.put(f"/api/meeting/{M1}", json={"title": "참석자가 고친 제목", "body": "참석자가 적은 원문"})
chk(r.status_code == 200 and (r.json() or {}).get("ok"), "회의록 본문·제목 저장", r.status_code)
r = client.post(f"/api/meeting/{M1}/decision", json={"who": "이한중", "what": "참석자가 넣은 결정", "due": ""})
chk(r.status_code == 200, "결정사항 추가", r.status_code)
r = client.post(f"/api/meeting/{M1}/action", json={"assignee_name": "이한중", "task": "참석자가 넣은 할 일", "due_date": ""})
chk(r.status_code == 200, "할 일 추가", r.status_code)
r = client.post(f"/api/meeting/{M1}/rec-start", json={})
chk(r.status_code == 200, "🎙 녹음 시작", r.status_code)
_ses = ((r.json() or {}).get("session") or "") if r.status_code == 200 else ""   # 서버가 준 녹음 번호로 이어 보낸다
r = client.post(f"/api/meeting/{M1}/rec-chunk?session={_ses}&seq=1&secs=2", content=b"a" * 512,
                headers={"Content-Type": "application/octet-stream"})
chk(r.status_code == 200, "녹음 조각 보내기", r.status_code)
r = client.post(f"/api/meeting/{M1}/rec-finish", json={})
chk(r.status_code == 200, "녹음 끝내기", r.status_code)
r = client.post(f"/api/meeting/{M1}/audio", files={"file": ("rec.wav", wav_bytes(), "audio/wav")})
chk(r.status_code == 200, "📁 녹음 파일 올리기", r.status_code)
r = client.get(f"/api/meeting/{M1}/stt-status")
chk(r.status_code == 200, "음성→글자 상태 보기", r.status_code)
r = client.post(f"/api/meeting/{M1}/transcribe", json={})
chk(r.status_code in (200, 400), "음성→글자 시작(키 없으면 400 — 권한은 통과)", r.status_code)
r = client.post(f"/api/meeting/{M1}/end", json={})
chk(r.status_code == 200 and (r.json() or {}).get("ended") is True, "⏹ 회의 종료", r.json() if r.status_code == 200 else r.status_code)
r = client.post(f"/api/meeting/{M1}/end", json={"undo": True})
chk(r.status_code == 200, "종료 되돌리기", r.status_code)
r = client.get(f"/meetings/{M1}")
chk(r.status_code == 200 and "회의록" in r.text, "회의록 화면이 열린다", r.status_code)

print("\n■ ② 참석자가 못 하는 것", flush=True)
as_user(ATT)
r = client.delete(f"/api/meeting/{M1}")
chk(r.status_code == 403, "🗑 삭제는 여전히 막힘(대표 결정)", r.status_code)
with db_session() as c:
    still = c.execute("SELECT COUNT(*) FROM meetings WHERE id=?", (M1,)).fetchone()[0]
chk(still == 1, "회의록이 그대로 있다")

print("\n■ ③ 참석자가 아닌 직원은 전부 막힘 (박주창)", flush=True)
as_user(OUT)
r = client.put(f"/api/meeting/{M1}", json={"title": "남이 고침"})
chk(r.status_code == 403, "본문 저장 막힘", r.status_code)
r = client.post(f"/api/meeting/{M1}/rec-start", json={})
chk(r.status_code in (403, 404), "녹음 시작 막힘", r.status_code)
r = client.post(f"/api/meeting/{M1}/audio", files={"file": ("rec.wav", wav_bytes(), "audio/wav")})
chk(r.status_code == 403, "녹음 파일 올리기 막힘", r.status_code)
r = client.post(f"/api/meeting/{M1}/end", json={})
chk(r.status_code == 403, "회의 종료 막힘", r.status_code)
r = client.delete(f"/api/meeting/{M1}")
chk(r.status_code == 403, "삭제 막힘", r.status_code)

print("\n■ ④ 참석자 없는 회의는 예전 그대로", flush=True)
as_user(ATT)
r = client.put(f"/api/meeting/{M2}", json={"title": "참석자 아님"})
chk(r.status_code == 403, "참석자 줄이 없으면 못 고친다", r.status_code)
as_user(OWNER)
r = client.put(f"/api/meeting/{M2}", json={"title": "작성자는 고친다"})
chk(r.status_code == 200, "작성자는 그대로 고칠 수 있다", r.status_code)
as_user(ORG)
r = client.put(f"/api/meeting/{M1}", json={"title": "등록 담당도 고친다"})
chk(r.status_code == 200, "이음 등록 담당도 그대로", r.status_code)
as_user(CEO_ID)
r = client.put(f"/api/meeting/{M1}", json={"title": "대표도 고친다"})
chk(r.status_code == 200, "대표/관리자도 그대로", r.status_code)

print("\n■ ⑤ 권한 함수를 직접 — 커서를 안 넘겨도 같은 답", flush=True)
with db_session() as c:
    m1 = dict(c.execute("SELECT * FROM meetings WHERE id=?", (M1,)).fetchone())
    chk(M._can_edit_meeting(USERS[ATT], m1, c) is True, "참석자 = 고칠 수 있다(커서 넘김)")
    chk(M._meeting_is_attendee(c, USERS[ATT], m1) is True, "참석자 판정 True")
    chk(M._meeting_is_attendee(c, USERS[OUT], m1) is False, "참석자 아닌 사람 False")
chk(M._can_edit_meeting(USERS[ATT], m1) is True, "커서를 안 넘겨도 참석자 = 고칠 수 있다(짧게 새로 열어 봄)")
chk(M._can_edit_meeting(USERS[OUT], m1) is False, "커서를 안 넘겨도 남은 막힌다")
chk(M._can_delete_meeting(USERS[ATT], m1) is False, "삭제 권한은 참석자에게 없다")
chk(M._can_end_meeting(USERS[ATT], m1) is True, "종료 권한은 참석자에게 있다")

print("\n" + "=" * 68)
print(f"합계: 통과 {OK} · 실패 {FAIL}")
for f in FAILS:
    print("  - 실패:", f)
sys.exit(1 if FAIL else 0)
