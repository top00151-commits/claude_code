# -*- coding: utf-8 -*-
"""📮 보낸 곳별 정리 · 다시 안 받기(나에게만) 시험 — 가짜 직원·가짜 메일·임시 DB(운영 무접촉 · 실제 메일 없음).
① 보낸 곳별로 맞게 묶고 광고·알림 / 거래 상대를 맞게 가른다
② 휴지통으로 — 고른 곳만, 내 메일만, 별표는 남기고, 지우지 않는다
③ 다시 안 받기 — 나에게만 · 이미 받은 것 차단함 · 앞으로 오는 것도 차단함 · 다른 직원은 그대로 받는다
④ 풀기 — 다시 받는다 · 되돌리기 · 회사 차단/위험 격리는 되돌리지 않는다
⑤ 화면·메일 전용 주소
사용: py -3.13 _검증/mail_cleanup_test.py"""
import io
import os
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
_so = sys.stdout
sys.stdout = io.StringIO()
try:
    import app.database as _db
    _TMP = tempfile.mkdtemp(prefix="knk_cleanup_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
    from app import mail_cleanup as mc
finally:
    sys.stdout = _so
from starlette.testclient import TestClient  # noqa: E402

P = F = 0
_SEQ = [0]


def check(name, cond, extra=""):
    global P, F
    if cond:
        P += 1
        print("  [PASS]", name)
    else:
        F += 1
        print("  [FAIL]", name, "<-", str(extra)[:500])


def put(c, owner, frm, name, subject, text="본문", n=1):
    ids = []
    for _ in range(n):
        _SEQ[0] += 1
        mid, _o = ms.store_inbound(c, to_email="t%d@knknara.co.kr" % owner, from_email=frm, from_name=name,
                                   subject="%s #%d" % (subject, _SEQ[0]), text="%s %d" % (text, _SEQ[0]),
                                   owner_id=owner, run_ai=False, message_id="cl-%d@test" % _SEQ[0])
        ids.append(mid)
    return ids


def rows(sql, a=()):
    with _db.db_session() as c:
        return [dict(r) for r in c.execute(sql, a).fetchall()]


def state(owner, frm):
    """(받은편지함, 차단함, 휴지통) 통수."""
    r = rows("SELECT SUM(CASE WHEN is_deleted=0 AND COALESCE(is_blocked,0)=0 THEN 1 ELSE 0 END) a, "
             "SUM(CASE WHEN is_deleted=0 AND COALESCE(is_blocked,0)=1 THEN 1 ELSE 0 END) b, "
             "SUM(CASE WHEN is_deleted=1 THEN 1 ELSE 0 END) d FROM mail_messages WHERE user_id=? AND lower(from_email)=?", (owner, frm))[0]
    return (r["a"] or 0, r["b"] or 0, r["d"] or 0)


FOOT = "\n\n본 메일은 발신전용입니다. 수신거부를 원하시면 여기를 눌러 주세요."
with _db.db_session() as c:
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9001,'t9001','시험일','member',1,'x')")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9002,'t9002','시험이','member',1,'x')")
    put(c, 9001, "ad@shop.example", "가나다몰", "(광고) 11월 특가", "할인" + FOOT, n=6)
    put(c, 9001, "newsletter@weekly.example", "주간소식", "이번 주 소식", "소식" + FOOT, n=4)
    put(c, 9001, "no-reply@system.example", "알림봇", "결재 알림", "알림입니다", n=3)
    put(c, 9001, "partner@vendor.example", "김거래", "견적 회신", "견적 드립니다", n=5)
    put(c, 9001, "replied@client.example", "박고객", "문의", "문의드립니다", n=2)
    put(c, 9001, "colleague@knknara.co.kr", "사내동료", "회의 안내", "회의합니다" + FOOT, n=2)
    put(c, 9001, "stranger@unknown.example", "모르는사람", "안녕하세요", "처음 뵙겠습니다", n=1)
    STAR = put(c, 9001, "ad@shop.example", "가나다몰", "(광고) 별표한 쿠폰", "쿠폰" + FOOT, n=1)[0]
    c.execute("UPDATE mail_messages SET is_starred=1 WHERE id=?", (STAR,))
    c.execute("INSERT INTO shared_contacts(name, email, visibility, created_by) VALUES('김거래','partner@vendor.example','company',9001)")
    ms.store_outbound(c, user_id=9001, from_email="t9001@knknara.co.kr", to_email="박고객 <replied@client.example>", subject="RE: 문의", body="답변드립니다")
    # 다른 직원(9002)도 같은 곳에서 받는다 — 9001 이 정리해도 9002 것은 그대로여야 한다
    put(c, 9002, "ad@shop.example", "가나다몰", "(광고) 11월 특가", "할인" + FOOT, n=3)
    put(c, 9002, "newsletter@weekly.example", "주간소식", "이번 주 소식", "소식" + FOOT, n=2)

print("== 1. 보낸 곳별 묶음 · 갈래 ==")
with _db.db_session() as c:
    d = mc.sender_groups(c, 9001)
G = {g["addr"]: g for g in d["groups"]}
check("묶음 7곳 · 훑은 24통", len(G) == 7 and d["scanned"] == 24 and d["total"] == 24, (len(G), d["scanned"], d["total"]))
check("통수: 광고 7 · 소식지 4 · 알림 3 · 거래처 5", (G["ad@shop.example"]["n"], G["newsletter@weekly.example"]["n"], G["no-reply@system.example"]["n"], G["partner@vendor.example"]["n"]) == (7, 4, 3, 5))
check("(광고) 표기 → 광고·알림", G["ad@shop.example"]["kind"] == "bulk" and "제목에 (광고) 표기" in G["ad@shop.example"]["reasons"], G["ad@shop.example"])
check("수신거부 안내 + 소식지 주소 → 광고·알림", G["newsletter@weekly.example"]["kind"] == "bulk" and len(G["newsletter@weekly.example"]["reasons"]) == 2, G["newsletter@weekly.example"])
check("no-reply 주소 → 광고·알림", G["no-reply@system.example"]["kind"] == "bulk", G["no-reply@system.example"])
check("주소록에 있는 곳 → 거래 상대", G["partner@vendor.example"]["kind"] == "partner" and G["partner@vendor.example"]["reasons"] == ["주소록에 있음"], G["partner@vendor.example"])
check("내가 메일 보낸 적 있는 곳 → 거래 상대", G["replied@client.example"]["kind"] == "partner" and "내가 메일을 보낸 적 있음" in G["replied@client.example"]["reasons"], G["replied@client.example"])
check("사내 주소는 수신거부 글이 있어도 거래 상대(사내)", G["colleague@knknara.co.kr"]["kind"] == "partner" and G["colleague@knknara.co.kr"]["reasons"] == ["사내"], G["colleague@knknara.co.kr"])
check("처음 보는 사람은 광고로 몰지 않는다", G["stranger@unknown.example"]["kind"] == "normal", G["stranger@unknown.example"])
check("순서: 광고·알림 → 보통 → 거래 상대", [g["kind"] for g in d["groups"]] == ["bulk"] * 3 + ["normal"] + ["partner"] * 3, [g["kind"] for g in d["groups"]])
check("광고·알림 안에서는 많이 온 곳이 위", [g["addr"] for g in d["groups"][:3]] == ["ad@shop.example", "newsletter@weekly.example", "no-reply@system.example"])
check("남의 메일은 묶음에 섞이지 않는다", G["ad@shop.example"]["n"] == 7)
for a, want in (("info@company.example", False), ("sales@company.example", False), ("noreply@x.example", True), ("do-not-reply@x.example", True),
                ("newsletter-kr@x.example", True), ("news@x.example", True), ("newton@x.example", False), ("event@x.example", True),
                ("events.team@x.example", True), ("kim.notice@x.example", False), ("mailer-daemon@x.example", True), ("admin@x.example", False)):
    k, _r = mc.judge(a, 1, 0, 0, False, False)
    check("자동 발송 주소 판별 %s → %s" % (a, "광고·알림" if want else "보통"), (k == "bulk") == want, (k, _r))
check("광고 표기가 절반 미만이면 광고로 보지 않는다", mc.judge("a@b.example", 10, 4, 0, False, False)[0] == "normal")

_UID = {"v": 9001}
_keep = m.get_user
m.get_user = lambda req: ({"id": _UID["v"], "role": "member", "name": "시험", "team_id": None, "team_name": ""} if _UID["v"] else None)


def client(port=5051, host="works.knknara.co.kr"):
    k = TestClient(m.app, base_url="http://127.0.0.1:%d" % port, raise_server_exceptions=False, follow_redirects=False)
    k.headers.update({"host": host, "x-forwarded-proto": "https"})
    return k


try:
    k = client()
    print("== 2. 화면 ==")
    r = k.get("/mail/cleanup")
    h = r.text
    check("정리 화면 200", r.status_code == 200, (r.status_code, h[:200]))
    check("보낸 곳 7줄 · 주소가 보인다", h.count(' data-kind="') == 7 and "ad@shop.example" in h and "partner@vendor.example" in h, h.count(' data-kind="'))
    check("광고·알림 3곳 칩 · 까닭 표시", "광고·알림으로 보이는 곳 3" in h and "제목에 (광고) 표기" in h and "주소록에 있음" in h)
    check("사내 주소 줄에는 「다시 안 받기」가 없다", h.count("clOne(this,'mute')") == 6, h.count("clOne(this,'mute')"))
    # 11-18 메뉴 단순하게: 받은편지함 → 「⚙ 설정·정리」 → 보낸 곳별 정리
    check("받은편지함에 들어가는 길(⚙ 설정·정리 → 보낸 곳별 정리)", 'href="/mail/tools"' in k.get("/mail/inbox").text and 'href="/mail/cleanup"' in k.get("/mail/tools").text)
    _UID["v"] = 0
    check("로그인 안 함 → 화면은 로그인으로, 길은 401", k.get("/mail/cleanup").status_code == 303
          and k.post("/mail/cleanup/apply", data={"action": "trash", "addr": "ad@shop.example"}).status_code == 401
          and k.post("/mail/cleanup/unmute", data={"addr": "ad@shop.example"}).status_code == 401)
    _UID["v"] = 9001
    check("로그인 안 한 요청으로는 아무것도 안 바뀜", state(9001, "ad@shop.example") == (7, 0, 0), state(9001, "ad@shop.example"))

    print("== 3. 휴지통으로 ==")
    r = k.post("/mail/cleanup/apply", data={"action": "trash", "addr": ["ad@shop.example", "NO-REPLY@system.example"]})
    j = r.json()
    check("응답: 2곳 9통 · 별표 1통 남김", j.get("ok") and (j["senders"], j["moved"], j["kept_starred"]) == (2, 9, 1), j)
    check("광고: 받은편지함 1(별표) · 휴지통 6", state(9001, "ad@shop.example") == (1, 0, 6), state(9001, "ad@shop.example"))
    check("알림: 휴지통 3", state(9001, "no-reply@system.example") == (0, 0, 3), state(9001, "no-reply@system.example"))
    check("고르지 않은 곳은 그대로", state(9001, "newsletter@weekly.example") == (4, 0, 0) and state(9001, "partner@vendor.example") == (5, 0, 0))
    check("⭐다른 직원의 같은 발신 메일은 그대로", state(9002, "ad@shop.example") == (3, 0, 0), state(9002, "ad@shop.example"))
    check("지우지 않았다(전체 통수 그대로)", rows("SELECT COUNT(*) n FROM mail_messages WHERE direction='in'")[0]["n"] == 29)
    check("휴지통에서 보인다", len(rows("SELECT id FROM mail_messages WHERE user_id=9001 AND is_deleted=1")) == 9)
    check("엉뚱한 action·빈 목록 → 400", k.post("/mail/cleanup/apply", data={"action": "delete", "addr": "a@b.example"}).status_code == 400
          and k.post("/mail/cleanup/apply", data={"action": "trash"}).status_code == 400)
    r = k.post("/mail/cleanup/apply", data={"action": "trash", "addr": ["주소아님", "%", "' OR 1=1 --"]})
    check("주소가 아닌 값은 아무것도 안 건드림", r.json().get("moved") == 0 and state(9001, "partner@vendor.example") == (5, 0, 0), r.json())

    print("== 4. 다시 안 받기(나에게만) ==")
    r = k.post("/mail/cleanup/apply", data={"action": "mute", "addr": ["newsletter@weekly.example", "colleague@knknara.co.kr"]})
    j = r.json()
    check("응답: 1곳 · 4통 차단함 · 사내 1곳 건너뜀", j.get("ok") and (j["senders"], j["moved"], j["skipped_internal"]) == (1, 4, 1), j)
    check("소식지: 차단함 4", state(9001, "newsletter@weekly.example") == (0, 4, 0), state(9001, "newsletter@weekly.example"))
    check("사내 동료 메일은 그대로", state(9001, "colleague@knknara.co.kr") == (2, 0, 0))
    with _db.db_session() as c:
        put(c, 9001, "Newsletter@Weekly.example", "주간소식", "다음 주 소식", "새 소식" + FOOT)
        put(c, 9002, "newsletter@weekly.example", "주간소식", "다음 주 소식", "새 소식" + FOOT)
        put(c, 9001, "partner@vendor.example", "김거래", "새 견적", "견적")
    check("⭐새로 온 메일도 내 차단함으로(대소문자 달라도)", state(9001, "newsletter@weekly.example") == (0, 5, 0), state(9001, "newsletter@weekly.example"))
    check("⭐다른 직원은 그대로 받는다", state(9002, "newsletter@weekly.example") == (3, 0, 0), state(9002, "newsletter@weekly.example"))
    check("다른 발신은 그대로 받은편지함", state(9001, "partner@vendor.example") == (6, 0, 0))
    check("회사 전체 차단목록은 건드리지 않았다", rows("SELECT COUNT(*) n FROM mail_blocklist")[0]["n"] == 0)
    h = k.get("/mail/cleanup").text
    check("화면: 다시 안 받기로 한 곳 1 · 스팸함 5통(11-18 차단함 → 스팸함)", "다시 안 받기로 한 곳 1" in h and "스팸함에 5통" in h and 'data-addr="newsletter@weekly.example" data-held="5"' in h)
    check("화면: 차단함으로 간 곳은 묶음에서 빠짐", 'class="cl-addr">newsletter@weekly.example' not in h)

    print("== 5. 메일 읽기 화면의 「다시 안 받기」 ==")
    sid = rows("SELECT id FROM mail_messages WHERE user_id=9001 AND from_email='stranger@unknown.example'")[0]["id"]
    oid = rows("SELECT id FROM mail_messages WHERE user_id=9002 AND from_email='ad@shop.example'")[0]["id"]
    cid = rows("SELECT id FROM mail_messages WHERE user_id=9001 AND from_email='colleague@knknara.co.kr'")[0]["id"]
    h = k.get("/mail/%d/pane" % sid).text
    check("읽기 화면에 단추", "muteSender()" in h and "다시 안 받기" in h)
    check("사내 메일 읽기 화면에는 단추 없음", 'onclick="muteSender()"' not in k.get("/mail/%d/pane" % cid).text)
    check("남의 메일로는 못 한다 → 404", k.post("/mail/%d/mute-sender" % oid).status_code == 404 and state(9002, "ad@shop.example") == (3, 0, 0))
    check("사내 주소는 거절 → 400", k.post("/mail/%d/mute-sender" % cid).status_code == 400)
    r = k.post("/mail/%d/mute-sender" % sid)
    check("내 메일: 다시 안 받기 → 차단함 1", r.json().get("ok") and r.json().get("moved") == 1 and state(9001, "stranger@unknown.example") == (0, 1, 0), r.json())

    print("== 6. 풀기 · 되돌리기 ==")
    r = k.post("/mail/cleanup/unmute", data={"addr": "stranger@unknown.example", "restore": "0"})
    check("풀기(되돌리지 않음): 차단함에 그대로", r.json().get("ok") and r.json().get("restored") == 0 and state(9001, "stranger@unknown.example") == (0, 1, 0), r.json())
    with _db.db_session() as c:
        put(c, 9001, "stranger@unknown.example", "모르는사람", "다시", "다시 보냅니다")
    check("푼 뒤 새 메일은 받은편지함으로", state(9001, "stranger@unknown.example") == (1, 1, 0), state(9001, "stranger@unknown.example"))
    r = k.post("/mail/cleanup/unmute", data={"addr": "newsletter@weekly.example", "restore": "1"})
    check("풀기(되돌림): 5통 받은편지함으로", r.json().get("restored") == 5 and state(9001, "newsletter@weekly.example") == (5, 0, 0), r.json())
    check("목록에서 사라짐", rows("SELECT COUNT(*) n FROM mail_user_blocks WHERE user_id=9001")[0]["n"] == 0)
    # 회사 차단목록에 걸린 곳 · 위험(3) 격리 메일은 「풀기」로 되돌리지 않는다
    with _db.db_session() as c:
        put(c, 9001, "risky@danger.example", "위험", "위험 메일", "본문", n=2)
        c.execute("UPDATE mail_messages SET risk_level=3, is_blocked=1 WHERE user_id=9001 AND from_email='risky@danger.example' "
                  "AND id=(SELECT MIN(id) FROM mail_messages WHERE user_id=9001 AND from_email='risky@danger.example')")
        mc.add_mute(c, 9001, "risky@danger.example")
    r = k.post("/mail/cleanup/unmute", data={"addr": "risky@danger.example", "restore": "1"})
    check("⭐위험 판정으로 격리된 메일은 되돌리지 않는다", r.json().get("restored") == 1 and state(9001, "risky@danger.example") == (1, 1, 0), (r.json(), state(9001, "risky@danger.example")))
    with _db.db_session() as c:
        put(c, 9001, "spam@blocked.example", "스팸", "스팸", "본문", n=2)
        mc.add_mute(c, 9001, "spam@blocked.example")
        ms.add_block(c, "spam@blocked.example", kind="email", note="시험", by=9001)
    r = k.post("/mail/cleanup/unmute", data={"addr": "spam@blocked.example", "restore": "1"})
    check("⭐회사 차단목록에 걸린 곳은 되돌리지 않는다", r.json().get("restored") == 0 and state(9001, "spam@blocked.example") == (0, 2, 0), (r.json(), state(9001, "spam@blocked.example")))
    check("주소가 아닌 값으로 풀기 → 400", k.post("/mail/cleanup/unmute", data={"addr": "아님"}).status_code == 400)

    print("== 7. 메일 전용 주소(kmail) · 끼워넣기 ==")
    km = client(5053, "kmail.knknara.co.kr")
    r = km.get("/mail/cleanup")
    check("메일 전용 주소에서도 화면이 열린다", r.status_code == 200 and "보낸 곳별" in r.text, (r.status_code, r.headers.get("location")))
    check("메일 전용 주소에서도 정리 길이 열린다", km.post("/mail/cleanup/apply", data={"action": "trash", "addr": "none@none.example"}).status_code == 200)
    with _db.db_session() as c:
        put(c, 9001, "x@inject.example", '<img src=x onerror=alert(1)>', '<script>alert(2)</script>', "본문")
    h = k.get("/mail/cleanup").text
    check("이름·제목의 태그는 글자로만", "<img src=x onerror" not in h and "<script>alert(2)" not in h and "&lt;script&gt;alert(2)" in h)

    print("== 8. 같은 메일 여러 통 → 한 통 + 「×N」 표시 ==")
    with _db.db_session() as c:
        for grp in ("gongyong", "giyeong", "hoero", "gwanri"):   # 그룹 주소 4곳으로 같은 메일(같은 고유번호)
            ms.store_inbound(c, to_email=grp + "@knknara.co.kr", from_email="buyer@fourcopies.example", from_name="네통발신",
                             subject="같은 메일 네 통", text="같은 본문", owner_id=9001, run_ai=False, message_id="four-copies@test")
        ms.store_inbound(c, to_email="t9001@knknara.co.kr", from_email="buyer@fourcopies.example", from_name="네통발신",
                         subject="한 통만 온 메일", text="다른 본문", owner_id=9001, run_ai=False, message_id="one-copy@test")
    r4 = rows("SELECT dup_count FROM mail_messages WHERE user_id=9001 AND subject='같은 메일 네 통' AND is_deleted=0")
    check("네 곳으로 온 같은 메일은 한 통만 남고 4로 적힌다", len(r4) == 1 and r4[0]["dup_count"] == 4, r4)
    h = k.get("/mail/inbox").text
    check("받은편지함 목록에 ×4 표시", 'class="mbx-dup"' in h and "×4</span>" in h and "같은 메일이 4통 와서 한 통으로 합쳤습니다" in h)
    check("한 통만 온 메일에는 표시 없음", h.count('class="mbx-dup"') == h.count("×4</span>"), (h.count('class="mbx-dup"'), h.count("×4</span>")))
    # 11-17 대표 「항목이 안 보인다」 → 찾기 쉽게: 왼쪽 메일함 · 빈 읽기 칸 안내 · 보낸사람 옆 「주소록에 등록」(바깥 사람만)
    # 11-18 대표 「쉽게 보이고 쉽게 사용」(메뉴 단순하게) → 가끔 쓰는 것은 「⚙ 설정·정리」 한 곳 · 빈 읽기 칸은 한 줄
    check("왼쪽 메뉴 「⚙ 설정·정리」 → 보낸 곳별 정리가 그 안 첫 칸", 'href="/mail/tools"' in h and k.get("/mail/tools").text.count('href="/mail/cleanup"') == 1)
    check("빈 읽기 칸은 한 줄(도움말 묶음 없음)", 'class="mbx-rp-tips"' not in h and "_mbxEmptyPane" in h)
    with _db.db_session() as c:
        _ext = c.execute("SELECT id FROM mail_messages WHERE user_id=9001 AND subject='한 통만 온 메일'").fetchone()["id"]
        ms.store_inbound(c, to_email="t9001@knknara.co.kr", from_email="dong@knknara.co.kr", from_name="사내동료", subject="사내 메일 하나", text="회의", owner_id=9001, run_ai=False, message_id="in-1@test")
        _int = c.execute("SELECT id FROM mail_messages WHERE user_id=9001 AND subject='사내 메일 하나'").fetchone()["id"]
    pe = k.get("/mail/%d/pane" % _ext).text
    pi = k.get("/mail/%d/pane" % _int).text
    check("바깥 사람 메일: 보낸사람 옆에 「주소록에 등록」 · ⋯ 더 보기 안에도", 'id="mvContactInline"' in pe and 'id="mvContactBtn"' in pe.split('id="mvMore"')[1], pe[:0])
    check("사내 동료 메일: 보낸사람 옆 표시 없음(군더더기)", "mv-ct-inline" not in pi.split("mv-actions")[0])
    check("차단함·휴지통 화면도 그대로 열린다", k.get("/mail/blocked").status_code == 200 and k.get("/mail/trash").status_code == 200)
finally:
    m.get_user = _keep

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
