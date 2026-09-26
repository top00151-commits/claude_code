# -*- coding: utf-8 -*-
"""z1125 서버 시험 — 회의록을 지우면 그 회의의 녹음 파일도 함께 (대표 결정 2026-09-26 「지울때 함께 지워」)
  ① WORKS 🗑 삭제 — 폴더째 지워짐 · 이음과 무관한 회의도(그 길에서 run_in_threadpool 이름이 없던 함정) · 다른 회의·`_share` 는 그대로
  ② 이음 🗓 입구(msg/delete) — 지웠을 때만 함께 · 남길 때(kept)·회의록 없음(none)이면 파일 그대로
  ③ 권한 없어 못 지울 때·이음에 못 닿아 안 지울 때 → 파일 그대로
  ④ 지우다 실패해도 회의록 삭제는 유지(오류 안 냄) · 이상한 번호로는 아무것도 안 지움
  ⑤ 확인 창 글에 「녹음 파일도 서버에서 지워집니다」
실행: 앱 사본 폴더에서 py -3.13 <이 파일>
🔴 운영에 닿는 것 없음 — 이음은 가짜(sso_client.httpx 바꿔 끼움) · AI 키 비움 · 파일은 이 사본 폴더의 meeting_audio 안에서만"""
import json
import os
import shutil
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


KEY = "test-service-key-z1125"
SC.get_service_key = lambda: KEY
PLAN = {}          # 이음 회의 번호 → 가짜 이음 응답 종류


class R:
    def __init__(self, status, data=None):
        self.status_code, self._d = status, data

    def json(self):
        if self._d is None:
            raise ValueError("not json")
        return self._d


class FakeHttpx:
    def post(self, url, headers=None, json=None, timeout=None):
        if url.endswith("/api/works/meetings/delete"):
            k = PLAN.get(int((json or {}).get("msg_meeting_id") or 0), "ok")
            if k == "conn":
                raise ConnectionError("이음 꺼짐(시험)")
            return R(200, {"ok": True})
        raise AssertionError("unexpected " + url)

    def get(self, *a, **kw):
        raise AssertionError("unexpected httpx.get")


SC.httpx = FakeHttpx()
client = TestClient(M.app)
client.__enter__()

AUDIO = "meeting_audio"
shutil.rmtree(AUDIO, ignore_errors=True)
os.makedirs(os.path.join(AUDIO, "_share"), exist_ok=True)
open(os.path.join(AUDIO, "_share", "keep_me.webm"), "wb").write(b"share" * 10)


def put_audio(mid, names=("rec_1.webm",), size=2048):
    d = os.path.join(AUDIO, f"meeting_{mid}")
    os.makedirs(d, exist_ok=True)
    for n in names:
        open(os.path.join(d, n), "wb").write(b"a" * size)
    return d


def has_audio(mid):
    return os.path.isdir(os.path.join(AUDIO, f"meeting_{mid}"))


with db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col in ("name_vi", "name_en", "employee_no", "entity", "phone", "dept_code"):
        if col not in have:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
    CEO_ID = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET role='ceo', employee_no='T0001', name='김정락' WHERE id=?", (CEO_ID,))

    def mk_user(name, login, role, emp):
        return c.execute("INSERT INTO users(name, login_id, password, role, is_active, employee_no) VALUES(?,?,?,?,1,?)",
                         (name, login, "x", role, emp)).lastrowid
    OWNER_ID = mk_user("안지연", "t_owner", "member", "T0086")
    ORG_ID = mk_user("이한중", "t_org", "member", "T0002")
    OTHER_ID = mk_user("박주창", "t_other", "member", "T0003")
    c.execute("DELETE FROM meetings")

    def mtg(title, owner, msg_id=None, organizer=None):
        return c.execute(
            "INSERT INTO meetings(title, meeting_date, mode, owner_id, location, tags, attendees_text, body, summary, "
            "audio_path, visibility, status, msg_meeting_id, msg_organizer_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (title, "2026-09-26", "B", owner, "", "", "", "", "", f"meeting_audio/meeting_X/rec_1.webm", "all", "draft",
             msg_id, organizer)).lastrowid

    A1 = mtg("A1 이음과 무관 · 녹음 있음", OWNER_ID)                 # 🔴 run_in_threadpool 이름 함정 길
    A2 = mtg("A2 이음 회의 · 녹음 있음", OWNER_ID, 9601, ORG_ID)
    A3 = mtg("A3 녹음 폴더 없음", OWNER_ID)
    A4 = mtg("A4 권한 없는 사람이 시도", OWNER_ID)
    A5 = mtg("A5 이음에 못 닿음", OWNER_ID, 9602, ORG_ID)
    A6 = mtg("A6 지우다 실패", OWNER_ID)
    B1 = mtg("B1 이음 입구가 지움", OWNER_ID, 9701, ORG_ID)
    B2 = mtg("B2 이음 입구 · 권한 없어 남김", OWNER_ID, 9702, ORG_ID)
    B3 = mtg("B3 건드리지 않을 회의", OWNER_ID, 9703, ORG_ID)

PLAN[9602] = "conn"
for m in (A1, A2, A4, A5, A6, B1, B2, B3):
    put_audio(m, ("rec_1.webm", "rec_2.webm") if m in (A1, B1) else ("rec_1.webm",))

USERS = {}
with db_session() as c:
    for uid in (CEO_ID, OWNER_ID, ORG_ID, OTHER_ID):
        USERS[uid] = dict(c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())
AS = {"u": None}
M.get_user = lambda req: AS["u"]


def delete(mid, uid):
    AS["u"] = USERS.get(uid) if uid else None
    return client.delete(f"/api/meeting/{mid}")


def msg_delete(msg_id, emp):
    return client.post("/api/meeting/msg/delete", headers={"X-SSO-Service-Key": KEY},
                       json={"msg_meeting_id": msg_id, "employee_no": emp})


def exists(mid):
    with db_session() as c:
        return bool(c.execute("SELECT 1 FROM meetings WHERE id=?", (mid,)).fetchone())


print("\n■ ① WORKS 🗑 삭제 — 녹음 파일도 함께")
r = delete(A1, OWNER_ID)
chk(r.status_code == 200 and not exists(A1), "이음과 무관한 회의 → 지워짐(예전이면 여기서 오류)", r.status_code)
chk(not has_audio(A1), "그 회의 녹음 폴더도 사라짐(파일 2개)", os.path.isdir(os.path.join(AUDIO, f"meeting_{A1}")))
r = delete(A2, OWNER_ID)
chk(r.status_code == 200 and not exists(A2) and not has_audio(A2), "이음에서 온 회의도 같음", r.status_code)
chk(has_audio(A4) and has_audio(A5) and has_audio(A6) and has_audio(B1), "다른 회의 폴더는 그대로")
chk(os.path.isfile(os.path.join(AUDIO, "_share", "keep_me.webm")), "🔴 아직 회의가 정해지지 않은 `_share` 파일은 그대로")
r = delete(A3, OWNER_ID)
chk(r.status_code == 200 and not exists(A3), "녹음 폴더가 없어도 그냥 지워짐(오류 없음)", r.status_code)

print("\n■ ② 안 지워야 할 때는 파일도 그대로")
r = delete(A4, OTHER_ID)
chk(r.status_code == 403 and exists(A4) and has_audio(A4), "권한 없는 사람 → 403 · 회의록도 파일도 그대로", r.status_code)
r = delete(A4, None)
chk(r.status_code == 401 and has_audio(A4), "로그인 없음 → 401 · 파일 그대로", r.status_code)
r = delete(A5, OWNER_ID)
chk(r.status_code == 503 and exists(A5) and has_audio(A5), "이음에 못 닿음 → 아무것도 안 지움(파일도)", r.status_code)

print("\n■ ③ 이음 🗓 입구(msg/delete)")
r = msg_delete(9701, "T0001")
chk(r.status_code == 200 and r.json().get("result") == "deleted" and not exists(B1) and not has_audio(B1),
    "대표가 이음에서 지움 → 회의록·녹음 파일 함께", r.json())
r = msg_delete(9702, "T0002")
chk(r.status_code == 200 and r.json().get("result") == "kept" and exists(B2) and has_audio(B2),
    "지울 수 없는 사람 → 회의록도 파일도 그대로(kept)", r.json())
r = msg_delete(99999, "T0001")
chk(r.json().get("result") == "none" and has_audio(B2) and has_audio(B3), "회의록 없는 번호 → 아무 폴더도 안 건드림", r.json())

print("\n■ ④ 지우다 실패해도 회의록 삭제는 유지 · 이상한 번호는 아무것도 안 지움")
_real_rmtree = shutil.rmtree
shutil.rmtree = lambda *a, **k: (_ for _ in ()).throw(PermissionError("시험: 파일이 잠김"))
r = delete(A6, OWNER_ID)
shutil.rmtree = _real_rmtree
chk(r.status_code == 200 and not exists(A6), "파일을 못 지워도 회의록은 지워지고 200", r.status_code)
chk(has_audio(A6), "그 폴더는 남는다(다음에 청소) · 서버 오류 아님")
keep = os.path.join(AUDIO, "_share", "keep_me.webm")
before = sorted(os.listdir(AUDIO))
for bad in (0, -5, "3; rm -rf /", "../_share", None, "meeting_9999", 1e9):
    M._meeting_audio_purge(bad)
chk(sorted(os.listdir(AUDIO)) == before and os.path.isfile(keep), "이상한 번호로는 아무것도 안 지움", before)
n = M._meeting_audio_purge(B3)
chk(n["files"] == 1 and n["bytes"] == 2048 and not has_audio(B3), "직접 부르면 파일 수·크기를 돌려줌", n)

print("\n■ ⑤ 확인 창 글")
with db_session() as c:
    P1 = c.execute("INSERT INTO meetings(title, meeting_date, mode, owner_id, visibility, status) "
                   "VALUES('P1 글 확인','2026-09-26','A',?,'all','draft')", (OWNER_ID,)).lastrowid
AS["u"] = USERS[OWNER_ID]
h = client.get(f"/meetings/{P1}").text
chk("녹음 파일도 서버에서 지워집니다" in h, "첫 확인 창에 「녹음 파일도 서버에서 지워집니다」")
chk("녹음·음성 글자·정리·결정·할 일을 더 이상 볼 수 없습니다" in h and "이미 일일카드로 보낸 할 일은 그대로 남습니다" in h,
    "기존 글도 그대로")
chk("⚠ 정말 삭제할까요?" in h, "두 번째 확인 글도 그대로")

print("\n" + "=" * 72)
print(f"합계: 통과 {OK} · 실패 {FAIL}")
for x in FAILS:
    print("  - 실패:", x)
sys.exit(1 if FAIL else 0)
