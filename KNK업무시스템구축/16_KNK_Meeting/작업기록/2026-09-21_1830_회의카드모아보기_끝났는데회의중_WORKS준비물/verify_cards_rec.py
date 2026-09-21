# -*- coding: utf-8 -*-
"""z1119 서버 시험 — 모아보기 자료(/api/meetings/msg-cards)에 recording·rec_secs 가 실리는가
(이음이 쓰는 msg/status 와 같은 값인가 · 가짜 이음 입구 · TestClient)
실행: 앱 사본 폴더에서  py -3.13 <이 파일>"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("KNK_SECRET_KEY", "verify-only-key")
os.environ["KNK_SSO_SERVICE_KEY"] = "cards-rec-verify-key"
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

KST_NOW = datetime.now(timezone.utc) + timedelta(hours=9)
TODAY = KST_NOW.date()
ITEMS = []


class FakeResp:
    def __init__(self, status, data):
        self.status_code, self._data = status, data

    def json(self):
        return self._data


class _FakeHttpx:
    def post(self, url, headers=None, json=None, timeout=None):
        return FakeResp(200, {"ok": True, "items": list(ITEMS), "truncated": False})

    def get(self, *a, **kw):
        raise AssertionError("unexpected httpx.get")


SC.httpx = _FakeHttpx()


def item(i, title):
    return {"id": i, "title": title, "start_at": f"{TODAY.isoformat()}T10:00", "tz_offset": 9, "tz_label": "한국",
            "duration_min": 60, "location": "", "visibility": "all", "organizer": {"name": "등록담당"},
            "attendees": [{"name": "김정락", "response": "attending", "is_organizer": False}],
            "externals": [], "me": {"is_organizer": False, "is_attendee": True, "response": "attending"}}


with db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col in ("name_vi", "name_en", "employee_no", "entity", "phone", "dept_code"):
        if col not in have:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
    CEO = dict(c.execute("SELECT * FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone())
    c.execute("UPDATE users SET role='ceo', employee_no='KNK0001' WHERE id=?", (CEO["id"],))   # 모아보기는 사번으로 이음에 묻는다
    CEO["role"], CEO["employee_no"] = "ceo", "KNK0001"
    c.execute("DELETE FROM meetings")

    def mtg(msg_id, title, summary="", audio="", rec_state="", rec_json=""):
        return c.execute(
            "INSERT INTO meetings(title, meeting_date, mode, owner_id, location, attendees_text, body, summary, "
            "audio_path, visibility, status, msg_meeting_id, msg_started_at, rec_state, rec_json) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (title, TODAY.isoformat(), "A", CEO["id"], "", "", "", summary, audio, "all", "draft", msg_id,
             f"{TODAY.isoformat()} 10:00:00", rec_state, rec_json)).lastrowid

    W_NOREC = mtg(110, "시작만 누름")                                            # 오늘 신고 회의와 같은 상태
    W_REC = mtg(111, "녹음 중", rec_state="recording", rec_json=json.dumps({"secs": 600}))
    W_REC0 = mtg(112, "녹음 중 30초", rec_state="recording", rec_json=json.dumps({"secs": 30}))
    W_DONE = mtg(113, "정리 끝", summary="핵심: 끝")
    W_RECD = mtg(114, "녹음됨", audio="meeting_audio/a.m4a")

ITEMS[:] = [item(110, "시작만 누름"), item(111, "녹음 중"), item(112, "녹음 중 30초"),
            item(113, "정리 끝"), item(114, "녹음됨"), item(115, "회의록 없음")]
M.get_user = lambda req: CEO
try:
    M._MSG_CARDS_CACHE.clear()
    M._MSG_CARDS_DOWN["until"] = 0.0
except Exception:
    pass

print("\n■ ① 모아보기 자료에 recording·rec_secs")
r = client.get("/api/meetings/msg-cards")
chk(r.status_code == 200 and r.json().get("ok"), "msg-cards 200", r.status_code)
by = {x["id"]: (x.get("minutes") or {}) for x in (r.json().get("items") or [])}
chk(set(by) >= {110, 111, 112, 113, 114, 115}, "카드 6장이 다 왔다", sorted(by))

a = by.get(110, {})
chk(a.get("stage") == "started", "시작만 누름 → 단계 started(그대로)", a.get("stage"))
chk(a.get("recording") is False, "🔴 시작만 누름 → recording=false", a.get("recording"))
chk(a.get("rec_secs") == 0, "시작만 누름 → rec_secs=0", a.get("rec_secs"))

b = by.get(111, {})
chk(b.get("stage") == "started", "녹음 중 → 단계 started", b.get("stage"))
chk(b.get("recording") is True, "녹음 중 → recording=true", b.get("recording"))
chk(b.get("rec_secs") == 600, "녹음 중 → rec_secs=600", b.get("rec_secs"))
chk(by.get(112, {}).get("rec_secs") == 30, "녹음 중 30초 → rec_secs=30", by.get(112, {}).get("rec_secs"))

chk(by.get(113, {}).get("stage") == "done" and by.get(113, {}).get("recording") is False,
    "정리 끝 → done · recording=false", by.get(113))
chk(by.get(114, {}).get("stage") == "recorded" and by.get(114, {}).get("recording") is False,
    "녹음됨 → recorded · recording=false", by.get(114))
chk(by.get(115, {}) == {"stage": "none", "can_view": False}, "회의록 없는 카드 → 예전 그대로(칸 추가 없음)", by.get(115))

print("\n■ ② 이음이 쓰는 msg/status 와 같은 값인가")
key = os.environ["KNK_SSO_SERVICE_KEY"]
s = client.post("/api/meeting/msg/status", headers={"X-SSO-Service-Key": key},
                json={"msg_meeting_ids": [110, 111, 112, 113, 114], "employee_no": CEO.get("employee_no") or ""})
if s.status_code == 200 and isinstance(s.json().get("items"), dict):
    st = s.json()["items"]
    for mid in (110, 111, 112, 113, 114):
        x, y = st.get(str(mid), {}), by.get(mid, {})
        chk((x.get("stage"), x.get("recording"), x.get("rec_secs")) == (y.get("stage"), y.get("recording"), y.get("rec_secs")),
            f"회의 {mid}: 모아보기 = msg/status (단계·녹음·초)",
            ((x.get("stage"), x.get("recording"), x.get("rec_secs")), (y.get("stage"), y.get("recording"), y.get("rec_secs"))))
else:
    chk(False, "msg/status 응답", (s.status_code, s.text[:120]))

print("\n" + "=" * 64)
print(f"합계: 통과 {OK} · 실패 {FAIL}")
for n in FAILS:
    print("  ❌ " + n)
sys.exit(1 if FAIL else 0)
