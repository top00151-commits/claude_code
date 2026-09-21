# -*- coding: utf-8 -*-
"""z1123 서버 시험 — 이음 🗓 회의에서 지워도 WORKS 회의록까지 (대표 결정 2026-09-22)
  ① POST /api/meeting/msg/delete — 공유키 · 회의록 없음(none) · 작성자·관리자·대표 = 지움 · 등록 담당·다른 직원 = 남김(not_allowed)
     · 사번 모름·빈 사번 = 남김(viewer_not_found) · 🔴 이음을 다시 부르지 않음 · 저장본 비움 · 두 번 불러도(재시도) 안전
  ② msg/status can_delete — 작성자·관리자·대표 true · 등록 담당·다른 직원·모르는 사번 false
  ③ WORKS 🗑 삭제 — 이음이 notified 를 주면 msg.notified · 안 주거나 0·이상한 값이면 칸 없음
실행: 앱 사본 폴더에서 py -3.13 <이 파일>
🔴 운영에 닿는 것 없음 — 이음은 가짜(sso_client.httpx 바꿔 끼움) · AI 키 비움 · 서버간 키 시험 값"""
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


KEY = "test-service-key-z1123"
SC.get_service_key = lambda: KEY
CALLS = []            # WORKS → 이음 호출(어느 주소든) — msg/delete 는 이음을 부르면 안 된다
NOTIFY = {}           # 이음 회의 번호 → 가짜 이음이 돌려줄 notified 값


class R:
    def __init__(self, status, data=None):
        self.status_code, self._data = status, data

    def json(self):
        if self._data is None:
            raise ValueError("not json")
        return self._data


class FakeHttpx:
    def post(self, url, headers=None, json=None, timeout=None):
        CALLS.append({"url": url, "json": dict(json or {})})
        if url.endswith("/api/works/meetings/delete"):
            mid = int((json or {}).get("msg_meeting_id") or 0)
            d = {"ok": True}
            if mid in NOTIFY:
                d["notified"] = NOTIFY[mid]
            return R(200, d)
        raise AssertionError("unexpected url " + url)

    def get(self, *a, **kw):
        raise AssertionError("unexpected httpx.get")


SC.httpx = FakeHttpx()
client = TestClient(M.app)
client.__enter__()

with db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col in ("name_vi", "name_en", "employee_no", "entity", "phone", "dept_code"):
        if col not in have:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
    CEO_ID = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET role='ceo', employee_no='T0001', name='김정락' WHERE id=?", (CEO_ID,))

    def mk_user(name, login, role, emp, active=1):
        return c.execute("INSERT INTO users(name, login_id, password, role, is_active, employee_no) VALUES(?,?,?,?,?,?)",
                         (name, login, "x", role, active, emp)).lastrowid
    OWNER_ID = mk_user("안지연", "t_owner", "member", "T0086")      # 회의록 작성자(▶ 회의 시작을 누른 사람)
    ORG_ID = mk_user("이한중", "t_org", "member", "T0002")          # 이음 등록 담당(고치기만)
    OTHER_ID = mk_user("박주창", "t_other", "member", "T0003")
    ADMIN_ID = mk_user("관리자", "t_admin", "admin", "T0009")
    VN_ID = mk_user("응우옌", "vn001", "member", "VN001")           # VN 사번 — 대소문자 무관
    mk_user("퇴사자", "t_gone", "member", "T0077", active=0)
    DUP1 = mk_user("같은사번1", "t_dup1", "admin", "T0055")         # 같은 사번 2명 = 누군지 모름(추측 금지)
    DUP2 = mk_user("같은사번2", "t_dup2", "admin", "T0055")
    c.execute("DELETE FROM meetings")

    def mtg(title, owner, msg_id=None, organizer=None):
        mid = c.execute(
            "INSERT INTO meetings(title, meeting_date, mode, owner_id, location, tags, attendees_text, body, summary, "
            "audio_path, visibility, status, msg_meeting_id, msg_organizer_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (title, "2026-09-21", "A", owner, "", "", "안지연, 박주창", "", "", "", "all", "draft", msg_id, organizer)).lastrowid
        c.execute("INSERT INTO meeting_attendees(meeting_id, user_id, name) VALUES(?,?,?)", (mid, OWNER_ID, "안지연"))
        c.execute("INSERT INTO meeting_attendees(meeting_id, user_id, name) VALUES(?,?,?)", (mid, OTHER_ID, "박주창"))
        return mid

    A1 = mtg("A1 작성자가 이음에서 지움", OWNER_ID, 8101, ORG_ID)
    A2 = mtg("A2 등록 담당이 이음에서 지움", OWNER_ID, 8102, ORG_ID)
    A3 = mtg("A3 대표가 이음에서 지움", OWNER_ID, 8103, ORG_ID)
    A4 = mtg("A4 관리자", OWNER_ID, 8104, ORG_ID)
    A5 = mtg("A5 VN 작성자", VN_ID, 8105, ORG_ID)
    A6 = mtg("A6 남는 것 시험", OWNER_ID, 8106, ORG_ID)
    A7 = mtg("A7 이음과 무관(번호 없음)", OWNER_ID)
    S1 = mtg("S1 상태 시험", OWNER_ID, 8201, ORG_ID)
    W1 = mtg("W1 WORKS 삭제 · 이음 알림 3명", OWNER_ID, 8301, ORG_ID)
    W2 = mtg("W2 WORKS 삭제 · 알림 없음", OWNER_ID, 8302, ORG_ID)
    W3 = mtg("W3 WORKS 삭제 · 알림 0", OWNER_ID, 8303, ORG_ID)
    W4 = mtg("W4 WORKS 삭제 · 이상한 값", OWNER_ID, 8304, ORG_ID)

USERS = {}
with db_session() as c:
    for uid in (CEO_ID, OWNER_ID, ORG_ID, OTHER_ID, ADMIN_ID, VN_ID):
        USERS[uid] = dict(c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())
AS = {"u": None}
M.get_user = lambda req: AS["u"]


def exists(mid):
    with db_session() as c:
        return bool(c.execute("SELECT 1 FROM meetings WHERE id=?", (mid,)).fetchone())


def att_rows(mid):
    with db_session() as c:
        return c.execute("SELECT COUNT(*) FROM meeting_attendees WHERE meeting_id=?", (mid,)).fetchone()[0]


def mdel(body, key=KEY):
    h = {"X-SSO-Service-Key": key} if key is not None else {}
    return client.post("/api/meeting/msg/delete", headers=h, json=body)


print("\n■ ① 공유키 — 없거나 틀리면 403 · 아무것도 안 지움")
r = mdel({"msg_meeting_id": 8106, "employee_no": "T0086"}, key=None)
chk(r.status_code == 403 and r.json().get("error") == "forbidden" and exists(A6), "키 없음 → 403 forbidden · 그대로", r.status_code)
r = mdel({"msg_meeting_id": 8106, "employee_no": "T0086"}, key="wrong")
chk(r.status_code == 403 and exists(A6), "틀린 키 → 403 · 그대로", r.status_code)
SC.get_service_key = lambda: ""
r = mdel({"msg_meeting_id": 8106, "employee_no": "T0086"}, key="")
chk(r.status_code == 403 and exists(A6), "WORKS 쪽 키가 비어 있으면 무엇이 와도 거부", r.status_code)
SC.get_service_key = lambda: KEY

print("\n■ ② 잘못된 요청 — 400 · 그대로")
r = client.post("/api/meeting/msg/delete", headers={"X-SSO-Service-Key": KEY, "Content-Type": "application/json"}, content="not json")
chk(r.status_code == 400 and r.json().get("error") == "json_required", "JSON 아님 → 400", r.status_code)
r = mdel([1, 2])
chk(r.status_code == 400 and r.json().get("error") == "json_required", "목록(dict 아님) → 400", r.status_code)
for bad in ({}, {"msg_meeting_id": 0}, {"msg_meeting_id": -3}, {"msg_meeting_id": "abc"}, {"msg_meeting_id": None}):
    r = mdel(dict(bad, employee_no="T0086"))
    chk(r.status_code == 400 and r.json().get("error") == "msg_meeting_id_required", f"회의 번호 {bad.get('msg_meeting_id', '없음')!r} → 400", r.status_code)

print("\n■ ③ 회의록 없음(시작 전 회의 대부분) → none · 아무것도 안 건드림")
with db_session() as c:
    n_before = c.execute("SELECT COUNT(*) FROM meetings").fetchone()[0]
r = mdel({"msg_meeting_id": 99999, "employee_no": "T0086"})
with db_session() as c:
    n_after = c.execute("SELECT COUNT(*) FROM meetings").fetchone()[0]
chk(r.status_code == 200 and r.json() == {"ok": True, "result": "none"} and n_before == n_after, "없는 이음 회의 → 200 none", r.json())
r = mdel({"msg_meeting_id": "99999", "employee_no": ""})
chk(r.status_code == 200 and r.json().get("result") == "none", "번호가 글자여도 · 사번이 비어도 회의록이 없으면 none", r.json())

print("\n■ ④ 지울 수 있는 사람 — 작성자·관리자·대표 → 회의록 지움(참석자 줄도 함께)")
chk(att_rows(A1) == 2, "지우기 전 참석자 줄 2개", att_rows(A1))
n0 = len(CALLS)
r = mdel({"msg_meeting_id": 8101, "employee_no": "T0086"})
chk(r.status_code == 200 and r.json() == {"ok": True, "result": "deleted", "works_meeting_id": A1} and not exists(A1),
    "작성자(▶ 회의 시작을 누른 사람) → deleted", r.json())
chk(att_rows(A1) == 0, "참석자 줄도 함께 지워짐(FK)", att_rows(A1))
chk(len(CALLS) == n0, "🔴 이음을 다시 부르지 않는다(서로 부르며 돌지 않게)", len(CALLS) - n0)
with db_session() as c:
    act = c.execute("SELECT actor_id, kind, title FROM activities WHERE kind='meeting_delete' ORDER BY id DESC LIMIT 1").fetchone()
chk(act is not None and act[0] == OWNER_ID and "이음 🗓 회의에서 삭제" in act[2] and "A1" in act[2], "활동 기록에 남김(누가·어디서)", tuple(act) if act else None)
r = mdel({"msg_meeting_id": 8103, "employee_no": "T0001"})
chk(r.json().get("result") == "deleted" and not exists(A3), "대표 → deleted", r.json())
r = mdel({"msg_meeting_id": 8104, "employee_no": "T0009"})
chk(r.json().get("result") == "deleted" and not exists(A4), "관리자(admin) → deleted", r.json())
r = mdel({"msg_meeting_id": 8105, "employee_no": "vn001"})
chk(r.json().get("result") == "deleted" and not exists(A5), "VN 사번 소문자로 와도 같은 사람(대소문자 무관)", r.json())
chk(len(CALLS) == n0, "여러 번 지워도 이음 호출 0", len(CALLS) - n0)

print("\n■ ⑤ 지울 수 없는 사람 — 회의록은 남기고 까닭(이음은 자기 회의만 지운다)")
for emp, name in (("T0002", "등록 담당(고치기만)"), ("T0003", "다른 직원")):
    r = mdel({"msg_meeting_id": 8102, "employee_no": emp})
    chk(r.status_code == 200 and r.json() == {"ok": True, "result": "kept", "reason": "not_allowed", "works_meeting_id": A2}
        and exists(A2), f"{name} → kept · not_allowed · 그대로", r.json())
for emp, name in (("T9999", "WORKS 에 없는 사번"), ("", "빈 사번"), ("T0077", "퇴사(비활성)"), ("T0055", "같은 사번 2명(누군지 모름)")):
    r = mdel({"msg_meeting_id": 8102, "employee_no": emp})
    chk(r.status_code == 200 and r.json() == {"ok": True, "result": "kept", "reason": "viewer_not_found", "works_meeting_id": A2}
        and exists(A2), f"{name} → kept · viewer_not_found · 그대로", r.json())
chk(len(CALLS) == n0, "남길 때도 이음 호출 0", len(CALLS) - n0)

print("\n■ ⑥ 재시도·저장본 — 두 번째는 none · 어느 결과든 모아보기 저장본 비움")
r = mdel({"msg_meeting_id": 8101, "employee_no": "T0086"})
chk(r.json() == {"ok": True, "result": "none"}, "이미 지운 회의를 다시(이음 재시도) → none", r.json())
for body, name in (({"msg_meeting_id": 8106, "employee_no": "T0086"}, "deleted"), ({"msg_meeting_id": 8102, "employee_no": "T0003"}, "kept"),
                   ({"msg_meeting_id": 77777, "employee_no": "T0086"}, "none")):
    M._MSG_CARDS_CACHE[("시험", "a", "b")] = (0, {"ok": True})
    r = mdel(body)
    chk(r.json().get("result") == name and not M._MSG_CARDS_CACHE, f"{name} 뒤 저장본 비움", r.json().get("result"))
chk(exists(A7), "이음과 무관한 회의록(번호 없음)은 이 입구로 건드릴 수 없다")

print("\n■ ⑦ msg/status can_delete — 이음 🗓 「삭제」 확인 창 미리보기용")


def st(emp, ids=(8201,)):
    r = client.post("/api/meeting/msg/status", headers={"X-SSO-Service-Key": KEY},
                    json={"msg_meeting_ids": list(ids), "employee_no": emp})
    return r.json()["items"]


for emp, want, name in (("T0086", True, "작성자"), ("T0001", True, "대표"), ("T0009", True, "관리자"),
                        ("T0002", False, "등록 담당"), ("T0003", False, "다른 직원"), ("T9999", False, "모르는 사번")):
    it = st(emp)["8201"]
    chk(it.get("can_delete") is want, f"{name} → can_delete {want}", it.get("can_delete"))
it = st("T0086", ids=(8201, 99998))
chk(it["99998"] == {"stage": "none", "can_view": False}, "회의록 없는 회의는 전과 같은 모양(can_delete 칸 없음)", it["99998"])
chk(set(st("T0086")["8201"]) >= {"stage", "can_view", "started_by", "started_at", "recording", "rec_secs", "rec_mine", "can_delete"},
    "기존 칸(stage·can_view·rec_mine …) 그대로 + can_delete", sorted(st("T0086")["8201"]))

print("\n■ ⑧ WORKS 🗑 삭제 — 이음이 취소 알림을 보냈으면 몇 명인지(notified)")


def wdel(mid, uid):
    AS["u"] = USERS[uid]
    return client.delete(f"/api/meeting/{mid}")


NOTIFY.update({8301: 3, 8303: 0, 8304: "abc"})
r = wdel(W1, OWNER_ID)
chk(r.status_code == 200 and r.json().get("msg") == {"linked": True, "deleted": True, "reason": "deleted", "notified": 3} and not exists(W1),
    "이음 notified 3 → msg.notified 3", r.json())
r = wdel(W2, OWNER_ID)
chk(r.json().get("msg") == {"linked": True, "deleted": True, "reason": "deleted"}, "notified 없음 → 칸 없음(전과 같은 모양)", r.json())
r = wdel(W3, OWNER_ID)
chk(r.json().get("msg") == {"linked": True, "deleted": True, "reason": "deleted"}, "notified 0 → 칸 없음", r.json())
r = wdel(W4, OWNER_ID)
chk(r.json().get("msg") == {"linked": True, "deleted": True, "reason": "deleted"} and not exists(W4), "이상한 값 → 칸 없음 · 삭제는 그대로", r.json())

print("\n" + "=" * 72)
print(f"합계: 통과 {OK} · 실패 {FAIL}")
for x in FAILS:
    print("  - 실패:", x)
sys.exit(1 if FAIL else 0)
