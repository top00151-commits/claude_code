# -*- coding: utf-8 -*-
"""보낸 사람 주소를 모르는 메일 — ④ 원문 머리글 보관 · ③ 우리 자료로 찾기 숫자 세기 (가짜 자료 · 임시 DB · 운영 무접촉).
대표 11-22 「메일이 왔는데 보낸 사람에 메일 주소를 알 수 없는 건 너무 치명적」 → 「④랑 ③ 숫자 세기부터 진행해」
사용: py -3.13 _검증/mail_from_guess_test.py"""
import io
import os
import re
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
os.environ["KNK_RUN_MAIL_FETCH"] = "0"
_so = sys.stdout
sys.stdout = io.StringIO()
try:
    from cryptography.fernet import Fernet
    os.environ.setdefault("KNK_MAIL_KEY", Fernet.generate_key().decode())
    import app.database as _db
    _db.DB_PATH = os.path.join(tempfile.mkdtemp(prefix="knk_mfg_"), "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
    from app import mail_from_guess as mfg
finally:
    sys.stdout = _so
from email.header import Header  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

P = F = 0


def check(name, cond, extra=""):
    global P, F
    if cond:
        P += 1
        print("  [PASS]", name)
    else:
        F += 1
        print("  [FAIL]", name, "<-", str(extra)[:400])


D = "@knknara.co.kr"
UID, OTH = 9701, 9702
with _db.db_session() as c:
    c.execute("INSERT INTO users(id, login_id, name, rank, role, is_active, password, email) VALUES(?,?,?,?,?,?,?,?)",
              (UID, "t_boss", "시험대표", "대표이사", "member", 1, "x", "boss" + D))
    c.execute("INSERT INTO users(id, login_id, name, rank, role, is_active, password, email) VALUES(?,?,?,?,?,?,?,?)",
              (OTH, "t_park", "박영희", "과장", "member", 1, "x", "t_park" + D))
    ms._ensure_security_cols(c)
    ms._ensure_dedup_cols(c)


def raw_mail(hdrs, body="본문"):
    return ("\r\n".join(hdrs) + "\r\nTo: boss" + D + "\r\nSubject: t\r\nMessage-ID: <%s@demo>\r\n"
            "Received: from relay.demo.example by mx.demo.example\r\n\r\n%s" % (abs(hash(tuple(hdrs))), body)).encode("utf-8")


def store(raw):
    p = ms.parse_raw_email(raw)
    with _db.db_session() as c:
        mid, _o = ms.store_inbound(c, to_email="boss" + D, owner_id=UID, run_ai=False,
                                   from_email=p.get("from_email", ""), from_name=p.get("from_name", ""),
                                   subject=p.get("subject", ""), text=p.get("text", ""), message_id=p.get("message_id", ""),
                                   to_all=p.get("to_all", ""), raw_headers=p.get("raw_headers", ""))
        h = c.execute("SELECT * FROM mail_raw_headers WHERE mail_id=?", (mid,)).fetchone()
    return p, mid, (dict(h) if h else None)


NM = Header("홍길동", "euc-kr").encode()
print("== ④ 원문 머리글 보관 ==")
p1, id1, h1 = store(raw_mail(["From: " + NM + " <hong@demo-a.example>"]))
check("원문 읽기가 머리글을 돌려줌(본문 없음)", "From:" in p1["raw_headers"] and "본문" not in p1["raw_headers"], p1["raw_headers"][:200])
check("주소를 읽은 메일 = 주소 머리만 작게 남김(Received 같은 다른 머리 없음)",
      h1 and h1["full"] == 0 and h1["from_ok"] == 1 and "From:" in h1["hdr"] and "Received" not in h1["hdr"] and "Message-ID" in h1["hdr"], h1)
p2, id2, h2 = store(raw_mail(["From: " + NM]))
check("주소를 못 읽은 메일 = 머리글 전부 남김(full=1 · from_ok=0)", h2 and h2["full"] == 1 and h2["from_ok"] == 0 and "Received" in h2["hdr"], h2)
with _db.db_session() as c:
    rp1 = ms.reparse_from(c, id1)
    rp9 = ms.reparse_from(c, 999999)
check("남긴 머리글로 서버 안에서 다시 읽기", rp1 and rp1[1] == "hong@demo-a.example" and rp1[0] == "홍길동", rp1)
check("머리글이 없는 메일 = None", rp9 is None)
long_fold = raw_mail(["From: " + NM + " <h2@demo-a.example>", "Reply-To: =?utf-8?B?6rmA?=\r\n <rt@demo-a.example>"])
_p, _i, _h = store(long_fold)
check("이어진 줄(접힌 머리)도 함께 남김", _h and "rt@demo-a.example" in _h["hdr"], _h)
src = io.open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
check("메일 받는 세 곳(자동 가져오기 · 지금 가져오기 · 바깥 입구) 모두 원문 머리글을 넘김",
      src.count('raw_headers=parsed.get("raw_headers", "")') == 2 and "raw_headers=_raw_hdr" in src)

print("== ③ 우리 자료로 찾기 — 가짜 메일 ==")


def ins(i, frm, nm, subj="제목", body="", to_all="", cc="", at="2026-05-01 10:00:00", direction="in", to=""):
    with _db.db_session() as c:
        c.execute("INSERT INTO mail_messages(id, user_id, direction, from_email, from_name, subject, body_text, to_all, cc, "
                  "received_at, to_email, dedup_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                  (i, UID, direction, frm, nm, subj, body, to_all, cc, at, to, "dh%d" % i))


# 근거 자료(정상 메일)
ins(81001, "lim@demo-b.example", "임태훈")                                       # 이름
ins(81002, "kim1@demo-c.example", "김민수")                                      # 같은 이름 둘 → 여러 후보
ins(81003, "kim2@demo-d.example", "김민수")
ins(81004, "x@demo-e.example", "누군가", to_all="boss" + D + ", 정수진 <jung@demo-f.example>")   # 받는 사람 줄의 이름
ins(81005, "boss" + D, "시험대표", subj="RE: 견적 요청드립니다", direction="out", to="reply@demo-g.example", at="2026-05-02 09:00:00")
with _db.db_session() as c:
    c.execute("INSERT INTO shared_contacts(name, email, visibility, created_by) VALUES('최지우','choi@demo-h.example','private',?)", (UID,))
    c.execute("INSERT INTO shared_contacts(name, email, visibility, created_by) VALUES('남몰래','secret@demo-z.example','private',?)", (OTH,))
# 대상(주소 모름)
ins(82001, "", "임태훈")                                  # 이름 → 하나
ins(82002, "", "김민수")                                  # 여러 후보
ins(82003, "<박영희>", "")                                # 주소 칸에 이름 · 직원 → 하나
ins(82004, "", "", subj="견적 요청드립니다", at="2026-05-01 08:00:00")   # 답장 → 하나
ins(82005, "", "", body="안녕하세요.\n\n이민호 드림\nE-mail: lee@demo-i.example\n\n-----Original Message-----\nFrom: other@demo-j.example")  # 서명 → 하나(인용 뒤 주소는 안 봄)
ins(82006, "", "", subj="아무 근거 없음")                # 못 찾음
ins(82007, "", "정수진")                                  # 받는 사람 줄 이름 → 하나
ins(82008, "", "최지우")                                  # 주소록 → 하나
ins(82009, "", "남몰래")                                  # 남의 개인 주소록 = 안 봄 → 못 찾음
ins(82010, "", "임태훈", body="임태훈\nlim@demo-b.example")   # 이름 + 서명 같은 주소 = 근거 둘
with _db.db_session() as c:
    ix = mfg.build_index(c, UID, {"id": UID, "team_id": None, "role": "member"})
    G = {i: mfg.verdict(mfg.guess_one(c, r, ix)) for r in mfg.targets(c, UID) for i in [r["id"]]}
    S = {r["id"]: mfg.guess_one(c, r, ix) for r in mfg.targets(c, UID)}
check("같은 이름이 다른 메일에서 주소와 함께 → 하나로 모임", G[82001] == ("one", "lim@demo-b.example"), G[82001])
check("같은 이름 주소가 둘 → 여러 후보(채우지 않을 것)", G[82002][0] == "many", G[82002])
check("주소 칸에 이름(「<박영희>」) → 직원 명단 같은 이름", G[82003] == ("one", "t_park" + D) and "직원" in S[82003], (G[82003], S[82003]))
check("내가 그 제목에 답장한 받는 사람(한 명) → 답장", G[82004] == ("one", "reply@demo-g.example") and "답장" in S[82004], S[82004])
check("본문 서명 주소 → 서명(인용 뒤 주소는 안 봄)", G[82005] == ("one", "lee@demo-i.example") and S[82005]["서명"] == {"lee@demo-i.example"}, S[82005])
check("근거 없음 → 못 찾음", G[82006] == ("none", ""), S[82006])
check("다른 메일 받는 사람 줄의 「이름 <주소>」도 근거", G[82007] == ("one", "jung@demo-f.example"), S[82007])
check("내 주소록 → 주소록", G[82008] == ("one", "choi@demo-h.example") and "주소록" in S[82008], S[82008])
check("남의 개인 주소록은 보지 않음", G[82009] == ("none", ""), S[82009])
check("근거 둘이 같은 주소", G[82010][0] == "one" and {"이름", "서명"} <= set(S[82010]), S[82010])
check("원문 머리글을 남긴 메일(From 에 이름만 · 머리글 어디에도 주소 없음) → 원문 근거 없음 · 이름으로는 못 찾음(홍길동 = 근거 메일 둘)",
      id2 in G and "원문" not in S[id2], S.get(id2))

print("== 숫자 세기 입구(숫자만) ==")
ME = {"id": UID, "role": "member", "name": "시험대표", "rank": "대표이사", "login_id": "t_boss", "email": "boss" + D, "lang": "ko", "team_id": None}
m.get_user = lambda req: ME
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})
with _db.db_session() as c:
    before = c.execute("SELECT group_concat(id||':'||COALESCE(from_email,''), ',') FROM mail_messages").fetchone()[0]
r = k.get("/mail/from-guess")
j = r.json()
with _db.db_session() as c:
    after = c.execute("SELECT group_concat(id||':'||COALESCE(from_email,''), ',') FROM mail_messages").fetchone()[0]
check("200 · ok", r.status_code == 200 and j.get("ok"), r.text[:200])
check("대상 = 빈 주소 10 + 주소 칸에 이름 1(위 ④ 시험 메일 1통 포함 11통)", j["total"] == 11 and j["name_only"] == 1 and j["empty"] == 10, j)
check("하나로 모임 7 · 여러 후보 2(김민수·홍길동) · 못 찾음 2", (j["one"], j["many"], j["none"]) == (7, 2, 2), j)
check("근거 둘 이상 = 1통(82010)", j["one_2plus"] == 1, j)
check("주소·이름을 돌려주지 않음(숫자만)", not re.search(r"@|임태훈|김민수|최지우", r.text), r.text[:300])
check("자료를 바꾸지 않음", before == after)
check("원문 머리글 남긴 통수 셈", j.get("hdr_saved", 0) >= 3 and j.get("hdr_full", 0) >= 1, j)
ME2 = None
m.get_user = lambda req: ME2
check("로그인 없으면 401", k.get("/mail/from-guess").status_code == 401)


print("== ③ 채우기 · 🔎 추정 표시 · ↺ 되돌리기 ==")
m.get_user = lambda req: ME
with _db.db_session() as c:
    snap = {r["id"]: (r["from_email"], r["from_name"]) for r in c.execute("SELECT id, from_email, from_name FROM mail_messages").fetchall()}
    c.execute("UPDATE mail_messages SET fd_key='keep' WHERE id IN (82001, 82002, 81001)")
r = k.post("/mail/from-guess", data={"min": "2"})
check("근거 둘 이상만(min=2) = 1통(82010)", r.status_code == 200 and r.json().get("updated") == 1, r.text[:200])
r = k.post("/mail/from-guess", data={"undo": "1"})
check("↺ 되돌림 1통", r.json().get("undone") == 1, r.text[:200])
r = k.post("/mail/from-guess", data={})
j = r.json()
with _db.db_session() as c:
    R = {x["id"]: dict(x) for x in c.execute("SELECT id, from_email, from_name, fd_key FROM mail_messages").fetchall()}
    g1 = ms.get_mail(c, 82001, UID)
    g3 = ms.get_mail(c, 82003, UID)
    g81 = ms.get_mail(c, 81001, UID)
    bak = c.execute("SELECT COUNT(*) FROM mail_from_refill_bak WHERE batch LIKE 'guess-%'").fetchone()[0]
check("채우기 = 하나로 모임 7통만", j.get("updated") == 7 and bak == 7, (j, bak))
check("주소 채움 · 폴더 다시 나누게 fd_key 비움", R[82001]["from_email"] == "lim@demo-b.example" and R[82001]["fd_key"] == "", R[82001])
check("여러 후보·못 찾음은 그대로", R[82002]["from_email"] == "" and R[82002]["fd_key"] == "keep" and R[82006]["from_email"] == "", (R[82002], R[82006]))
check("주소 칸에 이름(「<박영희>」) → 이름 칸으로 옮기고 주소 채움", R[82003]["from_email"] == "t_park" + D and R[82003]["from_name"] == "박영희", R[82003])
check("메일 보기 = 🔎 추정 표시(근거 글)", g1.get("from_guess") == "같은 이름의 다른 메일" and "직원 명단" in (g3.get("from_guess") or ""), (g1.get("from_guess"), g3.get("from_guess")))
check("원래 주소가 있던 메일엔 추정 표시 없음", not g81.get("from_guess"), g81.get("from_guess"))
check("응답은 숫자만", not re.search(r"@|임태훈", r.text), r.text[:200])
tpl = io.open(os.path.join(ROOT, "app", "templates", "_v5_partials", "mail_view_body.html"), encoding="utf-8").read()
check("메일 보기 화면에 「🔎 추정 주소」 글", "🔎 추정 주소 · {{ m.from_guess }}" in tpl)
r = k.post("/mail/from-guess", data={"undo": "1"})
with _db.db_session() as c:
    back = {x["id"]: (x["from_email"], x["from_name"]) for x in c.execute("SELECT id, from_email, from_name FROM mail_messages").fetchall()}
    mk = c.execute("SELECT COUNT(*) FROM mail_from_guessed").fetchone()[0]
check("↺ 되돌리기 = 7통 · 예전 값 그대로 · 추정 표시 지움", r.json().get("undone") == 7 and back == snap and mk == 0,
      [i for i in snap if snap[i] != back.get(i)])

print("== ① 옛 메일 다시 받기 막기(가짜 POP3) ==")
from app import mail_fetch as MF  # noqa: E402
from email.utils import format_datetime  # noqa: E402
from datetime import datetime as _dtm, timedelta as _td, timezone as _tz  # noqa: E402
NOW = _dtm.now(_tz.utc)


def mk_box(n_old, n_new, no_date=0):
    box = []
    for i in range(n_old):
        box.append(("old%d" % i, NOW - _td(days=200 + i)))
    for i in range(no_date):
        box.append(("nod%d" % i, None))
    for i in range(n_new):
        box.append(("new%d" % i, NOW - _td(minutes=5 + i)))
    return box


class FakePOP:
    def __init__(self, box):
        self.box = box
        self.retr_n = 0

    def uidl(self):
        return b"+OK", [("%d %s" % (i + 1, u)).encode() for i, (u, _d) in enumerate(self.box)], 0

    def _hdr(self, n):
        u, d = self.box[n - 1]
        h = ["From: a <a@demo-x.example>", "Message-ID: <%s@demo>" % u, "Subject: s"]
        if d is not None:
            h.append("Date: " + format_datetime(d))
        return [x.encode() for x in h]

    def top(self, n, k):
        return b"+OK", self._hdr(n), 0

    def retr(self, n):
        self.retr_n += 1
        return b"+OK", self._hdr(n) + [b"", b"body"], 0

    def quit(self):
        pass


FP = FakePOP(mk_box(400, 3, no_date=1))
MF._pop3_connect = lambda *a, **k: FP
res = MF.pop3_collect("h", 995, True, "u", "p", set())
got = sorted(u for u, _r in res["messages"])
check("한꺼번에 300통 넘게 보이면 옛 메일(200일 전)은 안 받음 · 새 메일 3통 + 날짜 모르는 1통만 받음",
      res["ok"] and res["flood"] == 404 and len(res["skipped"]) == 400 and got == ["new0", "new1", "new2", "nod0"] and FP.retr_n == 4,
      (res.get("flood"), len(res["skipped"]), got, FP.retr_n))
FP2 = FakePOP(mk_box(20, 2))
MF._pop3_connect = lambda *a, **k: FP2
res2 = MF.pop3_collect("h", 995, True, "u", "p", set())
check("준비가 꺼져 있고 조금만 보이면 = 예전 그대로 다 받음", len(res2["messages"]) == 22 and not res2["skipped"], len(res2["messages"]))
res3 = MF.pop3_collect("h", 995, True, "u", "p", set(), hold_before=NOW - _td(days=1))
check("준비(hold)가 켜져 있으면 조금만 보여도 옛 메일 안 받음", sorted(u for u, _r in res3["messages"]) == ["new0", "new1"] and len(res3["skipped"]) == 20,
      (len(res3["messages"]), len(res3["skipped"])))
with _db.db_session() as c:
    MF._ensure_table(c)
    MF.save_account(c, UID, protocol="pop3", host="pop.fake-demo", port=995, use_ssl=True, username="me",
                    password_enc=m._mail.encrypt("fake-pw"), label="시험")
    acct = MF.get_account(c, UID)
MF.after_collect(_db.db_session, acct, UID, res)
with _db.db_session() as c:
    seen = MF.get_seen(c, acct["id"])
    hold = MF.get_hold(c, UID)
    hi = MF.hold_info(c, UID)
check("막은 옛 메일 = 받아 본 것으로 적음(다음엔 머리도 안 읽음) · 한꺼번에 보였으니 준비 자동 켬",
      len(seen) == 400 and hold is not None and hi["on"] and "자동" in hi["reason"], (len(seen), hi))
with _db.db_session() as c:
    MF.clear_hold(c, UID)
r = k.post("/mail/from-refill", data={"hold": "1"})
check("「원본 다시 읽기 준비」 켜기(8일)", r.json().get("on") is True, r.text[:200])
check("진행 상황에 준비 상태", k.get("/mail/from-refill").json().get("hold", {}).get("on") is True)
r = k.post("/mail/from-refill", data={"hold": "0"})
check("준비 끄기", r.json().get("on") is False, r.text[:200])
src = io.open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
check("자동 가져오기·지금 가져오기 둘 다 막기 장치를 거침", src.count("hold_before=_hold") == 2 and src.count("_mailfetch.after_collect(") == 2)
from app import mail_from_refill as MFR  # noqa: E402
check("원본 다시 읽기가 옛 원본까지 훑음(40,000통)", MFR.SCAN_LIMIT >= 40000)


print("== 인용 머리(뒤 메일의 「From: 이름 <주소>」 + 날짜) ==")
QB1 = ("확인했습니다.\n\n-----Original Message-----\nFrom: \"홍길순, KNK VINA\" <vina-hong@demo-v.example>\nTo: boss" + D + "\n"
       "Sent: Sunday, May 3, 2026 9:58 AM\nSubject: 주간보고 A\n\n본문\n\n-----Original Message-----\n"
       "From: 옛사람 <old-person@demo-o.example>\nSent: 2026-04-20 10:00\nSubject: 주간보고 A\n")
QB2 = "네 알겠습니다.\n\n2026년 6월 10일 (수) 오전 9:00, 김철수 <kim-cs@demo-k.example>님이 작성:\n> 발주 확인 부탁드립니다."
QB3 = "참고\n\nFrom: 다른날 <other-day@demo-x.example>\nSent: 2026-07-25 10:00\nSubject: 날짜 다른 건\n"
ins(83001, "", "", subj="주간보고 A", at="2026-05-03 10:00:00")
ins(83002, "x2@demo-e.example", "회신자", subj="RE: 주간보고 A", body=QB1, at="2026-05-04 09:00:00")
ins(83003, "", "", subj="발주 확인", at="2026-06-10 09:05:00")
ins(83004, "boss" + D, "시험대표", subj="RE: 발주 확인", body=QB2, at="2026-06-10 11:00:00", direction="out", to="kim-cs@demo-k.example, park2@demo-k.example")
ins(83005, "", "", subj="날짜 다른 건", at="2026-07-01 09:00:00")
ins(83006, "x3@demo-e.example", "누구", subj="RE: 날짜 다른 건", body=QB3, at="2026-07-26 09:00:00")
qh = mfg.quote_heads(QB1)
check("인용 머리 읽기: 주소·날짜·제목 (영어 Sent 꼴 · 이름에 쉼표)", ("vina-hong@demo-v.example", __import__("datetime").date(2026, 5, 3), "주간보고 A") in qh, qh)
check("「…님이 작성:」 한 줄 꼴", mfg.quote_heads(QB2) and mfg.quote_heads(QB2)[0][:2] == ("kim-cs@demo-k.example", __import__("datetime").date(2026, 6, 10)), mfg.quote_heads(QB2))
with _db.db_session() as c:
    rows = mfg.targets(c, UID)
    ix = mfg.build_index(c, UID, {"id": UID, "team_id": None, "role": "member"})
    ix["quote"] = mfg.quote_index(c, UID, rows)
    QS = {r["id"]: mfg.guess_one(c, r, ix) for r in rows if r["id"] in (83001, 83003, 83005)}
check("받은 날과 같은 날 인용 = 근거 「인용」(4월 옛 인용은 뺌)", QS[83001].get("인용") == {"vina-hong@demo-v.example"} and mfg.verdict(QS[83001]) == ("one", "vina-hong@demo-v.example"), QS[83001])
check("내 답장 속 「님이 작성」 인용 = 받는 사람이 둘이어도 찾음", QS[83003].get("인용") == {"kim-cs@demo-k.example"} and mfg.verdict(QS[83003])[0] == "one", QS[83003])
check("인용 날짜가 받은 날과 다르면 안 씀", "인용" not in QS[83005] and mfg.verdict(QS[83005])[0] == "none", QS[83005])
r = k.get("/mail/from-guess")
check("숫자 세기에 「인용」 근거 셈", r.json()["by_src"].get("인용") == 2 and "@" not in r.text, r.json().get("by_src"))
r = k.post("/mail/from-guess", data={})
with _db.db_session() as c:
    g = ms.get_mail(c, 83001, UID)
check("채우기 = 인용으로 찾은 것도 · 🔎 근거 「뒤 메일의 인용 머리」", g["from_email"] == "vina-hong@demo-v.example" and g.get("from_guess") == "뒤 메일의 인용 머리", (g["from_email"], g.get("from_guess")))
k.post("/mail/from-guess", data={"undo": "1"})

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
