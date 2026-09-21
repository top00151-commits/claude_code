# -*- coding: utf-8 -*-
"""z1121 서버 시험 — 이음 회의 카드용 msg/status 의 `rec_mine`(보는 사람이 그 녹음을 시작했나)
실행: 앱 사본 폴더에서 py -3.13 <이 파일>
🔴 운영에 닿는 것 없음(서버간 키도 시험용 값 · AI 키 비움 · 이음 주소 127.0.0.1:9)"""
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
from app import sso_client                     # noqa: E402
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


KEY = "test-service-key-z1121"
sso_client.get_service_key = lambda: KEY
client = TestClient(M.app, base_url="https://testserver")
client.__enter__()
with db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col in ("name_vi", "name_en", "employee_no", "entity", "phone", "dept_code"):
        if col not in have:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
    CEO = dict(c.execute("SELECT * FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone())
    c.execute("UPDATE users SET role='ceo', employee_no='T0001' WHERE id=?", (CEO["id"],))
    CEO["role"] = "ceo"
    o = c.execute("SELECT * FROM users WHERE id<>? AND is_active=1 ORDER BY id LIMIT 1", (CEO["id"],)).fetchone()
    STAFF = dict(o)
    c.execute("UPDATE users SET role='member', employee_no='T0086' WHERE id=?", (STAFF["id"],))
    STAFF["role"] = "member"
    c.execute("DELETE FROM meetings")
    cols = {r[1] for r in c.execute("PRAGMA table_info(meetings)")}
    assert "msg_organizer_id" in cols, "msg_organizer_id 칸 없음"
    # 안지연(STAFF)이 「▶ 회의 시작」 → WORKS 회의록 주인 · 전체 공개(대표도 봄) — 운영 회의 41 과 같은 모양
    MID = c.execute(
        "INSERT INTO meetings(title, meeting_date, mode, owner_id, location, tags, attendees_text, body, summary, "
        "audio_path, visibility, status, msg_meeting_id, msg_started_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("[시험] 테스트", "2026-09-21", "A", STAFF["id"], "", "", "", "", "", "", "all", "draft", 9117,
         "2026-09-21 16:32:19")).lastrowid
AS = {"u": STAFF}
M.get_user = lambda req: AS["u"]


def status(emp):
    r = client.post("/api/meeting/msg/status", json={"employee_no": emp, "msg_meeting_ids": [9117]},
                    headers={"X-SSO-Service-Key": KEY})
    return (r.json().get("items", {}).get("9117") if r.status_code == 200 else {"_http": r.status_code})


def chunk(ses, seq, secs):
    return client.post(f"/api/meeting/{MID}/rec-chunk?session={ses}&seq={seq}&secs={secs}", content=os.urandom(3000),
                       headers={"Content-Type": "application/octet-stream"})


print("\n■ ① 녹음 전 — rec_mine 은 false · 다른 칸은 예전 그대로")
a, b = status("T0086"), status("T0001")
chk(a.get("rec_mine") is False and b.get("rec_mine") is False, "녹음 전 → 둘 다 false", (a.get("rec_mine"), b.get("rec_mine")))
chk(a["stage"] == "started" and a["recording"] is False and a["rec_secs"] == 0 and a.get("url") == f"/meetings/{MID}",
    "단계·녹음·초·주소 예전 그대로", a)

print("\n■ ② 안지연이 녹음 → 창을 닫음(서버엔 열린 채) — 운영 회의 41 과 같은 상태")
AS["u"] = STAFF
ses = client.post(f"/api/meeting/{MID}/rec-start", json={"ext": ".webm"}).json()["session"]
chunk(ses, 1, 9); chunk(ses, 2, 19)
a, b = status("T0086"), status("T0001")
chk(a.get("rec_mine") is True, "🔴 녹음하던 본인(안지연) → rec_mine true", a)
chk(b.get("rec_mine") is False, "🔴 대표(볼 수 있음·고칠 수 있음이어도 녹음한 사람 아님) → false", b)
chk(b.get("can_view") is True and b["recording"] is True and b["rec_secs"] == 19, "대표 쪽 다른 칸은 그대로(볼 수 있음·녹음 중·19초)", b)
chk(a["recording"] is True and a["rec_secs"] == 19 and a.get("url") == f"/meetings/{MID}", "본인 쪽 녹음 중·19초·녹음 화면 주소", a)

print("\n■ ③ 대표가 이어서 녹음(맨 위 상자 · 묻기 뒤) — 이제 대표가 녹음한 사람")
AS["u"] = CEO
ses2 = client.post(f"/api/meeting/{MID}/rec-start", json={"ext": ".webm"}).json()["session"]
chunk(ses2, 1, 10)
a, b = status("T0086"), status("T0001")
chk(b.get("rec_mine") is True and a.get("rec_mine") is False, "녹음한 사람이 바뀌면 rec_mine 도 따라감", (a.get("rec_mine"), b.get("rec_mine")))

print("\n■ ④ 녹음을 끝내면 — 둘 다 false")
client.post(f"/api/meeting/{MID}/rec-finish", json={})
a, b = status("T0086"), status("T0001")
chk(a.get("rec_mine") is False and b.get("rec_mine") is False, "끝난 뒤 → 둘 다 false", (a.get("rec_mine"), b.get("rec_mine")))
chk(a["stage"] == "recorded" and a["recording"] is False, "단계 recorded(예전 그대로)", a["stage"])

print("\n■ ⑤ 정리가 끝난(done) 회의에 녹음을 더 하다 창을 닫음 — 카드는 「회의록 보기」 상태여도 본인은 true")
with db_session() as c:
    c.execute("UPDATE meetings SET summary='핵심: 끝' WHERE id=?", (MID,))
AS["u"] = STAFF
ses3 = client.post(f"/api/meeting/{MID}/rec-start", json={"ext": ".webm"}).json()["session"]
chunk(ses3, 1, 9)
a, b = status("T0086"), status("T0001")
chk(a["stage"] == "done" and a["recording"] is True and a.get("rec_mine") is True and a.get("url") == f"/meetings/{MID}",
    "done + 녹음 중 → 본인 rec_mine true · 녹음 화면 주소", a)
chk(b.get("rec_mine") is False, "대표 → false", b.get("rec_mine"))
client.post(f"/api/meeting/{MID}/rec-finish", json={})

print("\n■ ⑥ 보는 사람을 못 찾음 · 회의록 없는 회의 · 키")
x = status("T9999")
chk(x.get("rec_mine") is False and x.get("can_view") is False and "url" not in x, "모르는 사번 → false · 주소 없음", x)
r = client.post("/api/meeting/msg/status", json={"employee_no": "T0086", "msg_meeting_ids": [424242]},
                headers={"X-SSO-Service-Key": KEY}).json()["items"]["424242"]
chk(r == {"stage": "none", "can_view": False}, "회의록 없는 회의 → 예전 그대로(칸 추가 없음)", r)
r = client.post("/api/meeting/msg/status", json={"employee_no": "T0086", "msg_meeting_ids": [9117]})
chk(r.status_code == 403, "서버간 키 없으면 403", r.status_code)

print("\n" + "=" * 72)
print(f"합계: 통과 {OK} · 실패 {FAIL}")
for x in FAILS:
    print("  - 실패:", x)
sys.exit(1 if FAIL else 0)
