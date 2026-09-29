# -*- coding: utf-8 -*-
"""z1134 서버 시험 — 이음에서 참석자를 바꾸면 WORKS 회의록 명단도 따라간다 (대표 지시 2026-09-29)
  A. 새 입구 `POST /api/meeting/msg/attendees` 문지기(공유키·본문·회의록 없음)
  B. 명단 맞추기 — 새로 온 사람 추가 · 빠진 사람 삭제 · 그대로인 사람 유지 · 참석자 칸 글 · 외부 참석자 · 멱등
  C. 권한이 실제로 따라 움직이나 — 새 참석자는 고칠 수 있고, 빠진 사람은 못 고친다(대표 결정 ①)
  D. 🔴 녹음 중인 사람은 명단에서 빠져도 그대로 둔다(대표 결정 ②) — 녹음이 끊기면 안 된다
  E. 「▶ 회의 시작」 안전망 — 이미 있는 회의록이면 그때 명단으로 다시 맞춘다
  F. 🔴 이음을 되부르지 않는다
실행: 앱 사본 폴더에서 py -3.13 <이 파일>
🔴 운영에 닿는 것 없음 — AI 키 비움 · 이음 서버 안 부름(부르면 시험 실패) · 파일은 이 사본 폴더 안에서만"""
import json
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


client = TestClient(M.app)
client.__enter__()

# ── 이음으로 나가는 길을 막는다(부르면 기록되고 터진다) ──────────────────────
OUTBOUND = []


class _NoEum:
    def post(self, url, **kw):
        OUTBOUND.append(("post", url))
        raise AssertionError("이음을 되부르면 안 된다: " + str(url))

    def get(self, url, **kw):
        OUTBOUND.append(("get", url))
        raise AssertionError("이음을 되부르면 안 된다: " + str(url))


SC.httpx = _NoEum()
KEY = "z1134-verify-key"
SC.get_service_key = lambda: KEY
HDR = {"X-SSO-Service-Key": KEY}

# ── 사람·회의 준비 ───────────────────────────────────────────────────────────
with db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    if "employee_no" not in have:
        c.execute("ALTER TABLE users ADD COLUMN employee_no TEXT")
    CEO_ID = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET role='ceo', employee_no='T0001', name='김정락' WHERE id=?", (CEO_ID,))

    c.execute("DELETE FROM users WHERE login_id IN ('z34_owner','z34_a1','z34_a2','z34_new','z34_out','z34_org')")   # 앞 시험 흔적 지우기(사본 DB 라 안전)

    def mk_user(name, login, emp):
        return c.execute("INSERT INTO users(name, login_id, password, role, is_active, employee_no) "
                         "VALUES(?,?,?,'member',1,?)", (name, login, "x", emp)).lastrowid

    OWNER = mk_user("안지연", "z34_owner", "Z3486")     # 회의록 작성자(= 회의 시작 누른 사람)
    A1 = mk_user("이한중", "z34_a1", "Z3402")           # 처음부터 참석자
    A2 = mk_user("윤경호", "z34_a2", "Z3404")           # 처음부터 참석자 → 나중에 빠짐
    NEW = mk_user("최홍광", "z34_new", "Z3405")         # 나중에 새로 들어옴
    OUT = mk_user("박주창", "z34_out", "Z3403")         # 끝까지 참석자 아님
    ORG = mk_user("전영우", "z34_org", "Z3407")         # 이음 등록 담당
    c.execute("DELETE FROM meetings")
    c.execute("DELETE FROM meeting_attendees")

    def mtg(title, msg_id=None, organizer=None, vis="private"):
        return c.execute(
            "INSERT INTO meetings(title, meeting_date, mode, owner_id, location, tags, attendees_text, body, summary, "
            "audio_path, visibility, status, msg_meeting_id, msg_organizer_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (title, "2026-09-29", "B", OWNER, "", "", "이한중, 윤경호, 드림텍 전영우 프로", "회의 원문", "", "",
             vis, "draft", msg_id, organizer)).lastrowid

    MID = mtg("z1134 이음 회의", 9901, ORG)       # 이음 회의 9901 ↔ 이 회의록
    OTHER = mtg("건드리면 안 되는 다른 회의", 9902)
    for mid_, uid, nm in ((MID, A1, "이한중"), (MID, A2, "윤경호"), (OTHER, A1, "이한중")):
        c.execute("INSERT INTO meeting_attendees(meeting_id, user_id, name) VALUES(?,?,?)", (mid_, uid, nm))
    c.execute("INSERT INTO meeting_attendees(meeting_id, user_id, name) VALUES(?,NULL,?)",
              (MID, "드림텍 전영우 프로"))

USERS = {}
with db_session() as c:
    for uid in (CEO_ID, OWNER, A1, A2, NEW, OUT, ORG):
        USERS[uid] = dict(c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())
AS = {"u": None}
M.get_user = lambda req: AS["u"]


def as_user(uid):
    AS["u"] = USERS.get(uid) if uid else None


def sync(emps, ext=None, msg_id=9901, hdr=HDR, body=None):
    """새 입구 부르기 → (상태코드, 응답)"""
    if body is None:
        body = {"msg_meeting_id": msg_id, "attendee_employee_nos": emps}
        if ext is not None:
            body["externals"] = ext
    r = client.post("/api/meeting/msg/attendees", json=body, headers=hdr)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {}


def names_of(mid=None):
    mid = mid or MID
    with db_session() as c:
        return [(r[0], r[1]) for r in c.execute(
            "SELECT user_id, name FROM meeting_attendees WHERE meeting_id=? ORDER BY id", (mid,))]


def att_text(mid=None):
    mid = mid or MID
    with db_session() as c:
        return (c.execute("SELECT attendees_text FROM meetings WHERE id=?", (mid or MID,)).fetchone()[0] or "")


# ═══ A. 문지기 ═══════════════════════════════════════════════════════════════
print("\n■ A. 새 입구 문지기 (공유키·본문·회의록 없음)", flush=True)
st, d = sync(["Z3402"], hdr={})
chk(st == 403 and d.get("ok") is False, "A1 공유키 없으면 403", st)
st, d = sync(["Z3402"], hdr={"X-SSO-Service-Key": "wrong-key-z1134"})
chk(st == 403, "A2 공유키가 틀리면 403", st)
SC.get_service_key = lambda: ""
st, d = sync(["Z3402"])
chk(st == 403, "A3 WORKS 키가 비어 있으면 무엇이 와도 403", st)
SC.get_service_key = lambda: KEY
r = client.post("/api/meeting/msg/attendees", content=b"not-json", headers=HDR)
chk(r.status_code == 400, "A4 JSON 이 아니면 400", r.status_code)
st, d = sync(None, body={"attendee_employee_nos": []})
chk(st == 400 and d.get("error") == "msg_meeting_id_required", "A5 회의 번호 없으면 400", d)
st, d = sync(None, body={"msg_meeting_id": 9901})
chk(st == 400 and d.get("error") == "attendee_employee_nos_required",
    "A6 🔴 참석자 칸이 아예 없으면 400 — 실수로 전원이 지워지지 않게", d)
before_cnt = len(names_of())
with db_session() as c:
    mtg_cnt = c.execute("SELECT COUNT(*) FROM meetings").fetchone()[0]
st, d = sync(["Z3402"], msg_id=9999)
chk(st == 200 and d.get("ok") is True and d.get("result") == "none",
    "A7 아직 회의록이 없는 이음 회의 → 그냥 넘어간다(none)", d)
with db_session() as c:
    chk(c.execute("SELECT COUNT(*) FROM meetings").fetchone()[0] == mtg_cnt,
        "A8 🔴 회의록을 새로 만들지 않는다")
chk(len(names_of()) == before_cnt, "A9 다른 회의 명단도 그대로")

# ═══ B. 명단 맞추기 ══════════════════════════════════════════════════════════
print("\n■ B. 명단 맞추기 (이한중 그대로 · 윤경호 빠짐 · 최홍광 새로)", flush=True)
st, d = sync(["Z3402", "Z3405"], ext=["드림텍 전영우 프로"])
chk(st == 200 and d.get("result") == "synced", "B1 맞춤 200", d)
chk(d.get("added") == 1 and d.get("removed") == 1 and d.get("kept") == 2,
    "B2 새로 1 · 빠짐 1 · 그대로 2", d)
now = names_of()
ids = [u for u, _ in now]
chk(NEW in ids, "B3 새로 온 사람이 사번으로 연결돼 들어왔다")
chk(A2 not in ids, "B4 빠진 사람은 명단에서 빠졌다")
chk(A1 in ids, "B5 그대로인 사람은 그대로")
chk((None, "드림텍 전영우 프로") in now, "B6 계정 없는 외부 참석자는 이름만(user_id 없음)")
chk(att_text() == "이한중, 최홍광, 드림텍 전영우 프로",
    "B7 참석자 칸 글도 이음 명단 순서대로 다시 적힘(대표 결정 ③)", att_text())
chk(names_of(OTHER) == [(A1, "이한중")], "B8 다른 회의 명단은 안 건드린다", names_of(OTHER))

st, d = sync(["Z3402", "Z3405"], ext=["드림텍 전영우 프로"])
chk(st == 200 and d.get("added") == 0 and d.get("removed") == 0 and d.get("kept") == 3,
    "B9 같은 내용을 다시 불러도 그대로(멱등)", d)
chk(len(names_of()) == 3, "B10 줄 수가 늘지 않는다", len(names_of()))

st, d = sync(["Z3402", "Z3405", "없는사번9999"], ext=["드림텍 전영우 프로"])
chk(st == 200 and d.get("added") == 0, "B11 WORKS 에 없는 사번은 조용히 무시(추측 연결 금지)", d)
chk(len(names_of()) == 3, "B12 없는 사번은 명단에 안 들어간다")

st, d = sync([], ext=[])
chk(st == 200 and d.get("removed") == 3 and len(names_of()) == 0,
    "B13 이음이 전원을 뺐으면 WORKS 도 빈다", d)
chk(att_text() == "", "B14 참석자 칸도 빈다", att_text())
st, d = sync(["Z3402", "Z3404"], ext=["드림텍 전영우 프로"])
chk(st == 200 and d.get("added") == 3, "B15 다시 넣으면 다시 들어온다", d)

# ═══ C. 권한이 따라 움직이나 ═════════════════════════════════════════════════
print("\n■ C. 권한이 실제로 따라 움직인다", flush=True)
as_user(A1)
r = client.put(f"/api/meeting/{MID}", json={"body": "참석자가 적은 원문"})
chk(r.status_code == 200, "C1 지금 참석자는 회의록을 고칠 수 있다", r.status_code)
as_user(NEW)
r = client.put(f"/api/meeting/{MID}", json={"body": "최홍광이 적음"})
chk(r.status_code == 403, "C2 명단에서 빠진 사람은 못 고친다(대표 결정 ①)", r.status_code)
sync(["Z3402", "Z3404", "Z3405"], ext=["드림텍 전영우 프로"])     # 최홍광 다시 넣기
as_user(NEW)
r = client.put(f"/api/meeting/{MID}", json={"body": "최홍광이 적음"})
chk(r.status_code == 200, "C3 이음에서 넣어 주면 바로 고칠 수 있다", r.status_code)
sync(["Z3402", "Z3404"], ext=["드림텍 전영우 프로"])              # 최홍광 다시 빼기
as_user(NEW)
r = client.put(f"/api/meeting/{MID}", json={"body": "또 적기"})
chk(r.status_code == 403, "C4 다시 빠지면 다시 막힌다", r.status_code)
with db_session() as c:
    body = c.execute("SELECT body FROM meetings WHERE id=?", (MID,)).fetchone()[0] or ""
chk("최홍광이 적음" in body, "C5 빠진 사람이 적어 둔 글은 그대로 남는다", body[:30])
as_user(OWNER)
r = client.put(f"/api/meeting/{MID}", json={"title": "작성자가 고침"})
chk(r.status_code == 200, "C6 작성자는 명단과 무관하게 그대로(대표 결정 ②)", r.status_code)
as_user(ORG)
r = client.put(f"/api/meeting/{MID}", json={"title": "등록 담당이 고침"})
chk(r.status_code == 200, "C7 이음 등록 담당도 그대로", r.status_code)
as_user(OUT)
r = client.put(f"/api/meeting/{MID}", json={"title": "남이 고침"})
chk(r.status_code == 403, "C8 참석자가 아닌 직원은 그대로 막힘", r.status_code)
as_user(A1)
r = client.delete(f"/api/meeting/{MID}")
chk(r.status_code == 403, "C9 🗑 삭제는 여전히 참석자에게 없다", r.status_code)

# ═══ D. 녹음 중 보호 ═════════════════════════════════════════════════════════
print("\n■ D. 🔴 녹음 중인 사람은 명단에서 빠져도 그대로 둔다 (대표 결정 ②)", flush=True)
with db_session() as c:
    info = {"session": "1", "part": "", "seq": 0, "bytes": 0, "secs": 0,
            "by": A2, "by_name": "윤경호", "started_at": "2026-09-29 22:00:00",
            "last_at": "2026-09-29 22:00:10"}
    c.execute("UPDATE meetings SET rec_state='recording', rec_json=? WHERE id=?",
              (json.dumps(info, ensure_ascii=False), MID))
st, d = sync(["Z3402"], ext=[])        # 윤경호·외부를 뺀다
chk(st == 200 and d.get("held") == 1, "D1 녹음 중인 사람은 「남김」으로 센다", d)
ids = [u for u, _ in names_of()]
chk(A2 in ids, "D2 녹음 중인 사람이 명단에 그대로 있다")
chk(d.get("removed") == 1, "D3 녹음 안 하는 외부 참석자는 예정대로 빠졌다", d)
chk("윤경호" in att_text(), "D4 참석자 칸 글에도 남는다(뒤에 붙임)", att_text())
as_user(A2)
r = client.post(f"/api/meeting/{MID}/rec-chunk?session=1&seq=1&secs=2", content=b"a" * 256,
                headers={"Content-Type": "application/octet-stream"})
chk(r.status_code in (200, 409), "D5 녹음 중인 사람은 조각을 계속 보낼 수 있다(권한 통과)", r.status_code)
r = client.post(f"/api/meeting/{MID}/rec-finish", json={})
chk(r.status_code == 200, "D6 녹음 끝내기도 된다", r.status_code)
st, d = sync(["Z3402"], ext=[])        # 녹음이 끝난 뒤 다시 맞추기
chk(st == 200 and d.get("removed") == 1 and d.get("held") == 0,
    "D7 녹음이 끝난 뒤 다시 맞추면 그때 빠진다", d)
chk(A2 not in [u for u, _ in names_of()], "D8 이제 명단에 없다")

# ═══ E. 「▶ 회의 시작」 안전망 ════════════════════════════════════════════════
print("\n■ E. 「▶ 회의 시작」을 다시 불러도 명단이 맞춰진다", flush=True)


def start(emps, ext=None, msg_id=9901, extra=None):
    body = {"msg_meeting_id": msg_id, "title": "z1134 이음 회의", "start_at": "2026-09-29T10:00",
            "visibility": "private", "starter_employee_no": "Z3486"}
    if emps is not None:
        body["attendee_employee_nos"] = emps
    if ext is not None:
        body["externals"] = ext
    if extra:
        body.update(extra)
    r = client.post("/api/meeting/msg/start", json=body, headers=HDR)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {}


st, d = start(["Z3402", "Z3404", "Z3405"], ext=["드림텍 전영우 프로"])
chk(st == 200 and d.get("created") is False, "E1 이미 있는 회의록이면 새로 만들지 않는다", d)
ids = [u for u, _ in names_of()]
chk(A2 in ids and NEW in ids, "E2 회의 시작 때 바뀐 명단으로 맞춰진다", names_of())
before = names_of()
st, d = start(None)                     # 참석자 칸을 아예 안 보내면
chk(st == 200 and names_of() == before, "E3 🔴 참석자 칸을 안 보내면 명단을 건드리지 않는다", names_of())
st, d = start(["Z3402"], msg_id=9950)   # 새 회의 → 처음 만들기
chk(st == 200 and d.get("created") is True, "E4 처음 만들기는 예전 그대로", d)
with db_session() as c:
    nid = c.execute("SELECT id FROM meetings WHERE msg_meeting_id=9950").fetchone()[0]
chk(names_of(nid) == [(A1, "이한중")], "E5 처음 만든 회의 명단도 정상", names_of(nid))

# ═══ F. 이음 되부르기 없음 ═══════════════════════════════════════════════════
print("\n■ F. 🔴 이음을 되부르지 않는다", flush=True)
chk(not OUTBOUND, "F1 시험 내내 이음으로 나간 호출 0건", OUTBOUND)
chk(hasattr(M, "_msg_sync_attendees"), "F2 도우미 `_msg_sync_attendees` 가 있다")

print("\n" + "=" * 68)
print(f"합계: 통과 {OK} · 실패 {FAIL}")
for f in FAILS:
    print("  - 실패:", f)
sys.exit(1 if FAIL else 0)
