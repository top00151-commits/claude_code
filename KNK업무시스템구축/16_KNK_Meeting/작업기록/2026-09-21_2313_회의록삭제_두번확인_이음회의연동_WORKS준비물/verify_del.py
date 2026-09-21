# -*- coding: utf-8 -*-
"""z1122 서버 시험 — 회의록 삭제: 작성자·관리자만 · 이음 회의도 함께(이음이 판단) · 이음에 못 닿으면 안 지움
+ 모아보기 자료(msg-cards)에 rec_mine · 주소(정리 끝이어도 녹음 중이면 녹음 화면) · 상세 화면 msg_del
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


KEY = "test-service-key-z1122"
SC.get_service_key = lambda: KEY
CALLS = []            # 이음에 온 삭제 요청
DELETED_MSG = set()   # 가짜 이음에서 지워진 회의(모아보기 목록에서 빠짐)
CARDS = []            # 가짜 이음 모아보기 목록


class R:
    def __init__(self, status, data=None, text=None):
        self.status_code, self._data, self.text = status, data, text or ""

    def json(self):
        if self._data is None:
            raise ValueError("not json")
        return self._data


# 이음 회의 번호 → 가짜 응답
PLAN = {9101: ("ok",), 9102: ("not_allowed",), 9103: ("html404",), 9104: ("conn",), 9105: ("500",),
        9106: ("already",), 9107: ("key403",), 9108: ("viewer404",), 9109: ("ok",), 9110: ("ok",),
        9111: ("ok",), 9112: ("ok",), 9113: ("ok",)}


class FakeHttpx:
    def post(self, url, headers=None, json=None, timeout=None):
        if url.endswith("/api/works/meetings/delete"):
            CALLS.append({"url": url, "headers": dict(headers or {}), "json": dict(json or {})})
            mid = int((json or {}).get("msg_meeting_id") or 0)
            k = PLAN.get(mid, ("ok",))[0]
            if k == "conn":
                raise ConnectionError("이음 꺼짐(시험)")
            if k == "ok":
                DELETED_MSG.add(mid)
                return R(200, {"ok": True})
            if k == "already":
                return R(200, {"ok": True, "already": True})
            if k == "not_allowed":
                return R(403, {"ok": False, "error": "not_allowed"})
            if k == "viewer404":
                return R(404, {"ok": False, "error": "viewer_not_found"})
            if k == "html404":
                return R(404, None, "<!doctype html><title>404 Not Found</title>")
            if k == "key403":
                return R(403, {"error": "forbidden"})
            return R(500, {"ok": False, "error": "internal"})
        if url.endswith("/api/works/meetings"):
            return R(200, {"ok": True, "items": [x for x in CARDS if x["id"] not in DELETED_MSG], "truncated": False})
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
    ids = [r[0] for r in c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1")]
    CEO_ID = ids[0]
    c.execute("UPDATE users SET role='ceo', employee_no='T0001', name='김정락' WHERE id=?", (CEO_ID,))

    def mk_user(name, login, role, emp):
        return c.execute("INSERT INTO users(name, login_id, password, role, is_active, employee_no) VALUES(?,?,?,?,1,?)",
                         (name, login, "x", role, emp)).lastrowid
    OWNER_ID = mk_user("안지연", "t_owner", "member", "T0086")
    ORG_ID = mk_user("이한중", "t_org", "member", "T0002")
    OTHER_ID = mk_user("박주창", "t_other", "member", "T0003")
    ADMIN_ID = mk_user("관리자", "t_admin", "admin", "T0009")
    NOEMP_ID = mk_user("사번없음", "t_noemp", "member", None)
    c.execute("DELETE FROM meetings")

    def mtg(title, owner, msg_id=None, organizer=None, vis="all", summary="", rec=None):
        mid = c.execute(
            "INSERT INTO meetings(title, meeting_date, mode, owner_id, location, tags, attendees_text, body, summary, "
            "audio_path, visibility, status, msg_meeting_id, msg_organizer_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (title, "2026-09-21", "A", owner, "", "", "", "", summary, "", vis, "draft", msg_id, organizer)).lastrowid
        if rec:
            c.execute("UPDATE meetings SET rec_state='recording', rec_json=? WHERE id=?",
                      (json.dumps({"part": "", "session": "1", "seq": 3, "bytes": 3000, "secs": 30, "by": rec,
                                   "by_name": "", "started_at": "", "last_at": "", "pending": []}), mid))
        return mid

    M1 = mtg("M1 WORKS 에서만", OWNER_ID)
    M2 = mtg("M2 이음 지움", OWNER_ID, 9101, ORG_ID)
    M3 = mtg("M3 이음 거절", OWNER_ID, 9102, ORG_ID)
    M4 = mtg("M4 이음 입구 없음", OWNER_ID, 9103, ORG_ID)
    M5 = mtg("M5 이음 꺼짐", OWNER_ID, 9104, ORG_ID)
    M6 = mtg("M6 이음 500", OWNER_ID, 9105, ORG_ID)
    M7 = mtg("M7 이음 이미 없음", OWNER_ID, 9106, ORG_ID)
    M8 = mtg("M8 이음 키 거부", OWNER_ID, 9107, ORG_ID)
    M9 = mtg("M9 이음 사번 모름", OWNER_ID, 9108, ORG_ID)
    M10 = mtg("M10 권한 시험", OWNER_ID, 9109, ORG_ID)
    M11 = mtg("M11 대표가 지움", OWNER_ID, 9110, ORG_ID)
    M12 = mtg("M12 키 없음", OWNER_ID, 9111, ORG_ID)
    M13 = mtg("M13 사번 없는 작성자", NOEMP_ID, 9112, ORG_ID)
    R1 = mtg("R1 녹음 중·본인", OWNER_ID, 9201, ORG_ID, rec=OWNER_ID)
    R2 = mtg("R2 정리 끝+녹음 중·본인", OWNER_ID, 9202, ORG_ID, summary="핵심: 끝", rec=OWNER_ID)
    R3 = mtg("R3 정리 끝", OWNER_ID, 9203, ORG_ID, summary="핵심: 끝")

USERS = {}
with db_session() as c:
    for uid in (CEO_ID, OWNER_ID, ORG_ID, OTHER_ID, ADMIN_ID, NOEMP_ID):
        USERS[uid] = dict(c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())
AS = {"u": None}
M.get_user = lambda req: AS["u"]


def delete(mid, uid):
    AS["u"] = USERS.get(uid) if uid else None
    return client.delete(f"/api/meeting/{mid}")


def exists(mid):
    with db_session() as c:
        return bool(c.execute("SELECT 1 FROM meetings WHERE id=?", (mid,)).fetchone())


print("\n■ ① 권한 — 작성자·관리자(대표 포함)만 · 등록 담당·다른 사람·로그인 없음은 못 지움")
n0 = len(CALLS)
r = delete(M10, ORG_ID)
chk(r.status_code == 403 and exists(M10), "등록 담당(고칠 수는 있음) → 403 · 그대로", r.status_code)
r = delete(M10, OTHER_ID)
chk(r.status_code == 403 and exists(M10), "다른 직원 → 403 · 그대로", r.status_code)
r = delete(M10, None)
chk(r.status_code == 401 and exists(M10), "로그인 없음 → 401", r.status_code)
chk(len(CALLS) == n0, "거절된 삭제는 이음에 묻지도 않는다", len(CALLS) - n0)
r = delete(M10, ADMIN_ID)
chk(r.status_code == 200 and not exists(M10), "관리자(admin) → 지움", r.status_code)

print("\n■ ② 이음과 무관한 회의 — 이음에 묻지 않고 지움")
n0 = len(CALLS)
r = delete(M1, OWNER_ID)
chk(r.status_code == 200 and r.json().get("msg") == {"linked": False} and not exists(M1), "작성자 → 지움 · msg.linked false", r.json())
chk(len(CALLS) == n0, "이음에 요청 없음", len(CALLS) - n0)

print("\n■ ③ 이음이 지움 — 회의록도 지움 · 요청 내용 확인")
r = delete(M2, OWNER_ID)
j = r.json()
chk(r.status_code == 200 and j.get("msg") == {"linked": True, "deleted": True, "reason": "deleted"} and not exists(M2),
    "이음 ok → 둘 다 지움", j)
call = CALLS[-1]
chk(call["json"] == {"msg_meeting_id": 9101, "employee_no": "T0086", "works_meeting_id": M2}, "요청 = 이음 회의 번호·지우는 사람 사번·WORKS 번호", call["json"])
chk(call["headers"].get("X-SSO-Service-Key") == KEY, "공유키를 실어 보냄(값은 찍지 않음)")
r = delete(M7, OWNER_ID)
chk(r.status_code == 200 and r.json()["msg"]["deleted"] is True and r.json()["msg"]["reason"] == "already" and not exists(M7),
    "이음에 이미 없음 → 지워진 것으로", r.json())
r = delete(M11, CEO_ID)
chk(r.status_code == 200 and CALLS[-1]["json"]["employee_no"] == "T0001" and not exists(M11), "대표가 지우면 대표 사번으로 묻는다", CALLS[-1]["json"])

print("\n■ ④ 이음이 거절·사람 모름·입구 없음 — 회의록만 지우고 까닭을 돌려줌")
for mid, reason, name in ((M3, "not_allowed", "등록자·관리자 아님"), (M9, "viewer_not_found", "이음이 사번 모름"),
                          (M4, "not_ready", "이음 입구 없음(글자 404 · 세션 10 배포 전)")):
    r = delete(mid, OWNER_ID)
    j = r.json()
    chk(r.status_code == 200 and j.get("msg") == {"linked": True, "deleted": False, "reason": reason} and not exists(mid),
        f"{name} → 회의록만 지움 · reason={reason}", j)
n0 = len(CALLS)
r = delete(M13, NOEMP_ID)
chk(r.status_code == 200 and r.json()["msg"]["reason"] == "viewer_not_found" and len(CALLS) == n0 and not exists(M13),
    "사번 없는 작성자 → 이음에 묻지 않고 회의록만", r.json())

print("\n■ ⑤ 🔴 이음에 못 닿음 — 아무것도 지우지 않음(한쪽만 지워지지 않게)")
for mid, name in ((M5, "연결 실패"), (M6, "이음 500"), (M8, "키 거부 403")):
    r = delete(mid, OWNER_ID)
    j = r.json()
    chk(r.status_code == 503 and j.get("ok") is False and "지우지 않았습니다" in (j.get("error") or "") and exists(mid),
        f"{name} → 503 · 회의록 그대로", j.get("error"))
SC.get_service_key = lambda: ""
r = delete(M12, OWNER_ID)
chk(r.status_code == 503 and exists(M12) and "연결 키" in r.json().get("error", ""), "공유키 없음 → 503 · 그대로", r.json().get("error"))
SC.get_service_key = lambda: KEY

print("\n■ ⑥ 모아보기 30초 저장본 — 지우면 비운다")
M._MSG_CARDS_CACHE[("시험", "a", "b")] = (0, {"ok": True})
r = delete(M12, OWNER_ID)
chk(r.status_code == 200 and not M._MSG_CARDS_CACHE, "삭제 뒤 저장본 비움", list(M._MSG_CARDS_CACHE)[:2])

print("\n■ ⑦ 상세 화면 — 삭제 단추 · 이음 회의 함께 지워지나(msg_del)")
with db_session() as c:
    P1 = c.execute("INSERT INTO meetings(title, meeting_date, mode, owner_id, visibility, status, msg_meeting_id, msg_organizer_id) "
                   "VALUES('P1 이음 회의','2026-09-21','A',?,'all','draft',9301,?)", (OWNER_ID, ORG_ID)).lastrowid
    P2 = c.execute("INSERT INTO meetings(title, meeting_date, mode, owner_id, visibility, status) "
                   "VALUES('P2 WORKS 회의','2026-09-21','A',?,'all','draft')", (OWNER_ID,)).lastrowid


def page(mid, uid):
    AS["u"] = USERS[uid]
    return client.get(f"/meetings/{mid}").text


h = page(P1, CEO_ID)
chk('id="btnDelete"' in h and 'msg_del: "yes"' in h, "대표 → 삭제 단추 · 이음 회의도 함께(yes)")
h = page(P1, OWNER_ID)
chk('id="btnDelete"' in h and 'msg_del: "no"' in h, "작성자(등록자 아님) → 삭제 단추 · 이음 회의는 남음(no)")
h = page(P1, ORG_ID)
chk('id="btnDelete"' not in h, "등록 담당 → 삭제 단추 없음(고치기만)")
h = page(P1, OTHER_ID)
chk('id="btnDelete"' not in h, "다른 직원 → 삭제 단추 없음")
h = page(P2, OWNER_ID)
chk('id="btnDelete"' in h and 'msg_del: "none"' in h, "이음과 무관한 회의 → none")
chk("⚠ 정말 삭제할까요?" in h, "두 번째 확인 글이 화면에 있다")

print("\n■ ⑧ 모아보기 자료 — rec_mine(보는 사람 기준) · 정리 끝+녹음 중이면 녹음 화면 주소")


def item(i, title):
    return {"id": i, "title": title, "start_at": "2026-09-21T10:00", "tz_offset": 9, "tz_label": "한국", "duration_min": 60,
            "location": "", "visibility": "all", "organizer": {"name": "등록"}, "attendees": [], "externals": [],
            "me": {"is_organizer": False, "is_attendee": True, "response": "attending"}}


CARDS[:] = [item(9201, "R1"), item(9202, "R2"), item(9203, "R3")]


def cards(uid):
    AS["u"] = USERS[uid]
    M._MSG_CARDS_CACHE.clear()
    M._MSG_CARDS_DOWN["until"] = 0.0
    r = client.get("/api/meetings/msg-cards")
    return {x["id"]: (x.get("minutes") or {}) for x in (r.json().get("items") or [])}


a, b = cards(OWNER_ID), cards(CEO_ID)
chk(a[9201].get("rec_mine") is True and a[9201].get("url") == f"/meetings/{R1}", "녹음하던 본인 → rec_mine true · 녹음 화면", a[9201])
chk(b[9201].get("rec_mine") is False and b[9201].get("recording") is True, "대표 → rec_mine false(녹음 중은 그대로)", b[9201])
chk(a[9202].get("stage") == "done" and a[9202].get("rec_mine") is True and a[9202].get("url") == f"/meetings/{R2}",
    "정리 끝 + 녹음 중 → 본인 true · 주소 = 녹음 화면(전엔 /doc)", a[9202])
chk(b[9202].get("url") == f"/meetings/{R2}", "대표도 같은 주소(이음 msg/status 와 같게)", b[9202].get("url"))
chk(a[9203].get("url") == f"/meetings/{R3}/doc" and a[9203].get("rec_mine") is False, "정리 끝·녹음 아님 → 양식(/doc) 그대로", a[9203])
st = client.post("/api/meeting/msg/status", headers={"X-SSO-Service-Key": KEY},
                 json={"msg_meeting_ids": [9201, 9202, 9203], "employee_no": "T0086"}).json()["items"]
chk(all(st[str(k)].get("rec_mine") == a[k].get("rec_mine") and st[str(k)].get("url") == a[k].get("url") for k in (9201, 9202, 9203)),
    "모아보기 = 이음 msg/status (rec_mine·주소)", {k: (st[str(k)].get("rec_mine"), st[str(k)].get("url")) for k in (9201, 9202, 9203)})

print("\n" + "=" * 72)
print(f"합계: 통과 {OK} · 실패 {FAIL}")
for x in FAILS:
    print("  - 실패:", x)
sys.exit(1 if FAIL else 0)
