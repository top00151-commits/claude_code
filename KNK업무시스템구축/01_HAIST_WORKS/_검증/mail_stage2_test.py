# -*- coding: utf-8 -*-
"""메일 2단계-가 (대표 2026-11-19 「2단계 진행해」) — 운영 무접촉 · 임시 DB · 가짜 메일.

증명할 것
  ① 종류(견적·발주·세금계산서): 저장된 종류가 먼저 · 「일반」이면 제목 낱말로 · 모아 보기 목록도 같은 기준
  ② 🚩 기한: 정하기·풀기·기한 순 보기·오늘까지 숫자 · 남의 메일 못 함 · 이상한 날짜 거절
  ③ ⏰ 다시 알림: 받은편지함에서 숨김 → 시간이 되면 안 읽음으로 돌아옴(돌아온 시각) · 지난 시각 거절 · 남의 메일 못 함
  ④ 날짜·시각 = 보는 사람 소속(본사 +9 · 베트남 +7) — 같은 「내일 아침 9시」가 서버 시각으로 2시간 차이
  ⑤ 숫자 API: 가벼운 판(lite) · 맨 위 새 메일(번호·보낸 사람·제목) · 🚩·⏰ 숫자
  ⑥ 할 일·일정으로: 고른 날짜로 저장(전에 늘 오류 나던 것 고침) · 이상한 날짜면 오늘
  ⑦ 답장·전달 인용: 머리말 + 원본 모양 · <style>·<head> 빠짐 · 우리 서버·cid 그림은 [그림] · 바깥 https 그림 유지 · 위험한 것 빠짐
  ⑧ 화면: 종류 단추 · 🚩·⏰ 왼쪽·도구 줄 · 오른쪽 클릭 · 읽기 화면 「🚩 기한·알림」 · 영어 번역 · 새 메일 띠 · 1분마다 숫자 · 바탕화면 알림 설정
"""
import _mail_ico; _mail_ico.install()  # noqa: E402  11-28 4단계: 화면의 선 아이콘을 [i:이름] 으로 읽음(그림 문자 대신 · 아이콘 이름까지 확인)
import io
import os
import re
import sys
import tempfile
from datetime import datetime, timedelta

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
    _TMP = tempfile.mkdtemp(prefix="knk_ms2_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
finally:
    sys.stdout = _so
from starlette.testclient import TestClient  # noqa: E402

P = F = 0


def check(name, cond, extra=""):
    global P, F
    if cond:
        P += 1
        print("  [PASS]", name)
    else:
        F += 1
        print("  [FAIL]", name, "<-", str(extra)[:500])


OWN, OTHER = 9201, 9202
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x' WHERE login_id='kjr'")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9201,'kjr','시험대표','ceo',1,'x')")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9202,'t9202','시험이','member',1,'x')")
_SEQ = [0]


def put(subject, text="본문", owner=OWN, frm="a@vendor.example", html="", cat=None):
    _SEQ[0] += 1
    with _db.db_session() as c:
        mid, _o = ms.store_inbound(c, to_email="ceo@knknara.co.kr", from_email=frm, from_name="보낸이", subject=subject,
                                   text=text, html=html, owner_id=owner, run_ai=False, message_id="s2-%d@t" % _SEQ[0])
        if cat:
            c.execute("UPDATE mail_messages SET category=? WHERE id=?", (cat, mid))
    return mid


Q1 = put("[견적요청] 검사기 3대")
Q2 = put("Quotation for AOI", cat=None)
PO = put("Purchase Order #1234")
TX = put("11월 세금계산서 발행")
AI = put("문의드립니다", cat="견적")          # AI·규칙이 견적으로 정한 것(제목에 낱말 없음)
GEN = put("주간 회의 자료")
OTH = put("남의 견적", owner=OTHER)

print("== ① 종류 ==")
check("제목 낱말로 종류", ms.mail_kind({"subject": "[견적요청] x", "category": "일반"}) == "견적"
      and ms.mail_kind({"subject": "Purchase Order #1", "category": ""}) == "발주"
      and ms.mail_kind({"subject": "Tax Invoice", "category": "일반"}) == "세금계산서"
      and ms.mail_kind({"subject": "회의", "category": "일반"}) == "")
check("저장된 종류가 먼저", ms.mail_kind({"subject": "Purchase Order", "category": "견적"}) == "견적")
with _db.db_session() as c:
    ids = {r["id"] for r in ms.list_inbox(c, OWN, category="견적")}
check("견적 모아 보기 = 제목 낱말 + 저장된 종류(남의 메일·다른 종류 없음)", ids == {Q1, Q2, AI}, ids)
with _db.db_session() as c:
    ids_po = {r["id"] for r in ms.list_inbox(c, OWN, category="발주")}
    ids_tx = {r["id"] for r in ms.list_inbox(c, OWN, category="세금계산서")}
check("발주·세금계산서 모아 보기", ids_po == {PO} and ids_tx == {TX}, (ids_po, ids_tx))

_U = {"v": {"id": OWN, "role": "ceo", "name": "시험대표", "team_id": None, "team_name": ""}}
m.get_user = lambda req: _U["v"]
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})
km = TestClient(m.app, base_url="http://127.0.0.1:5053", raise_server_exceptions=False, follow_redirects=False)
km.headers.update({"host": "kmail.knknara.co.kr", "x-forwarded-proto": "https"})

print("== ② 🚩 기한 ==")
j = k.post("/mail/flag", data={"ids": "%d,%d" % (Q1, PO), "due": "2026-01-05"}).json()
j2 = k.post("/mail/flag", data={"ids": str(TX), "due": "2099-12-31"}).json()
check("기한 정하기(여러 통)", j.get("ok") and j.get("n") == 2 and j2.get("ok"), (j, j2))
hf = k.get("/mail/inbox?flag=1").text
order = [int(x) for x in re.findall(r'class="mbx-row[^"]*"\s+data-mail-id="(\d+)"', hf)]
check("🚩 기한 보기 = 기한 순(지난 것 먼저) · 기한 없는 메일 없음", order[:3] in ([Q1, PO, TX], [PO, Q1, TX]) and GEN not in order, order)
check("지난 기한은 빨강 표시", 'class="mbx-flag late"' in hf)
cnt = k.get("/api/mail/counts?lite=1").json()
check("숫자: 🚩 전체 3 · 오늘까지 2", cnt.get("flag") == 3 and cnt.get("flag_due") == 2, cnt)
check("남의 메일 기한 못 함", k.post("/mail/flag", data={"ids": str(OTH), "due": "today"}).status_code == 404)
check("이상한 날짜 거절", k.post("/mail/flag", data={"ids": str(Q1), "due": "어제쯤"}).status_code == 400)
k.post("/mail/flag", data={"ids": str(PO), "due": ""})
with _db.db_session() as c:
    check("기한 풀기", (c.execute("SELECT flag_due FROM mail_messages WHERE id=?", (PO,)).fetchone()[0] or "") == "")

print("== ③ ⏰ 다시 알림 ==")
j = k.post("/mail/snooze", data={"ids": str(GEN), "at": "tomorrow"}).json()
check("다시 알림 걸기", j.get("ok") and j.get("until"), j)
hi = k.get("/mail/inbox").text
check("받은편지함에서 숨김", ('data-mail-id="%d"' % GEN) not in hi)
hs = k.get("/mail/inbox?snz=1").text
check("⏰ 보기에 보임(그때 시각 표시)", ('data-mail-id="%d"' % GEN) in hs and 'class="mbx-snz"' in hs)
check("지난 시각 거절", k.post("/mail/snooze", data={"ids": str(GEN), "at": "2020-01-01T09:00"}).status_code == 400)
check("남의 메일 못 함", k.post("/mail/snooze", data={"ids": str(OTH), "at": "1h"}).status_code == 404)
with _db.db_session() as c:
    c.execute("UPDATE mail_messages SET snooze_until=datetime('now','localtime','-1 minutes'), is_read=1 WHERE id=?", (GEN,))
cnt = k.get("/api/mail/counts?lite=1").json()
with _db.db_session() as c:
    r = dict(c.execute("SELECT is_read, snooze_until, snooze_back FROM mail_messages WHERE id=?", (GEN,)).fetchone())
check("시간이 되면 안 읽음으로 돌아옴 · 돌아온 시각 남김", r["is_read"] == 0 and not r["snooze_until"] and r["snooze_back"] and cnt.get("woke") == 1, (r, cnt))
check("돌아온 메일은 받은편지함에 다시 보임", ('data-mail-id="%d"' % GEN) in k.get("/mail/inbox").text)
check("⏰ 보기에 「돌아옴」 3일 동안", "[i:alarm-clock] 돌아옴" in k.get("/mail/inbox?snz=1").text)

print("== ④ 소속 시각 ==")
kor = m._mail_snooze_from("tomorrow", 9)
vn = m._mail_snooze_from("tomorrow", 7)
d = (datetime.strptime(vn, "%Y-%m-%d %H:%M:%S") - datetime.strptime(kor, "%Y-%m-%d %H:%M:%S")).total_seconds() / 3600
# 11-20 시험 고침: 한국 00:00~02:00 에는 베트남이 아직 전날 → 「내일」 날짜가 하루 다름(각자 소속 날짜 기준이 맞음) → 2 - 24 = -22시간
_same_day = m._mail_local_today(9) == m._mail_local_today(7)
check("같은 「내일 아침 9시」: 베트남이 본사보다 서버 시각 2시간 늦음(한국 자정~2시엔 베트남 날짜가 하루 앞이라 -22시간)",
      abs(d - 2) < 0.01 if _same_day else abs(d + 22) < 0.01, (kor, vn, _same_day))
check("기한 단추: 오늘·내일·금요일·다음 주 월요일", all(re.match(r"^\d{4}-\d{2}-\d{2}$", m._mail_due_from(x, 9)) for x in ("today", "tomorrow", "fri", "nextmon"))
      and datetime.strptime(m._mail_due_from("fri", 9), "%Y-%m-%d").weekday() == 4 and datetime.strptime(m._mail_due_from("nextmon", 9), "%Y-%m-%d").weekday() == 0)
check("서버 시각 → 현지 표시 왕복", m._mail_local_label(m._mail_local_to_server(datetime(2030, 1, 2, 9, 0), 7), 7) == "1/2 09:00")

print("== ⑤ 숫자 API ==")
cnt = k.get("/api/mail/counts?lite=1").json()
check("가벼운 판 = 회신 필요 계산 안 함(0)", cnt.get("reply") == 0 and "unread" in cnt)
check("맨 위 새 메일(번호·보낸 사람·제목) — 내 메일만", cnt.get("latest", {}).get("id") and cnt["latest"]["id"] != OTH, cnt.get("latest"))

print("== ⑥ 할 일·일정 ==")
j = k.post("/mail/%d/to-task" % Q1, data={"work_date": "2026-11-25"}).json()
with _db.db_session() as c:
    t = c.execute("SELECT work_date, title FROM tasks WHERE id=?", (j.get("task_id"),)).fetchone()
check("고른 날짜로 할 일 저장(전에 늘 오류 나던 것 고침)", j.get("ok") and t and t["work_date"] == "2026-11-25", (j, dict(t) if t else None))
j = k.post("/mail/%d/to-task" % Q1, data={"work_date": "아무거나"}).json()
check("이상한 날짜면 오늘(보는 사람 소속)", j.get("ok") and j.get("work_date") == m._mail_local_today(9), j)
check("남의 메일은 할 일로 못 함", k.post("/mail/%d/to-task" % OTH).status_code == 404)

print("== ⑦ 인용 ==")
H = ('<html><head><style>body{color:red}p{margin:40px}</style><title>t</title></head><body>'
     '<table><tr><td>단가</td><td>1,000</td></tr></table><img src="cid:logo@x"><img src="https://img.example/a.png">'
     '<script>alert(1)</script><p onclick="x()">끝</p></body></html>')
HM = put("견적 회신", text="단가 1,000", html=H)
with _db.db_session() as c:
    c.execute("UPDATE mail_messages SET to_all=?, cc=? WHERE id=?", ("시험대표 <ceo@knknara.co.kr>, b@partner.example", "c@partner.example", HM))
hr = k.get("/mail/compose?reply=%d" % HM).text
mm = re.search(r'<textarea id="cPrefillHtml"[^>]*>(.*?)</textarea>', hr, re.S)
qh = (mm.group(1) if mm else "").replace("&lt;", "<").replace("&gt;", ">").replace("&#34;", '"').replace("&quot;", '"').replace("&amp;", "&").replace("&#39;", "'")
check("머리말(원본 메일 · 보낸 사람 · 받는 사람 · 참조 · 제목)", all(x in qh for x in ("──────── 원본 메일 ────────", "보낸 사람:", "받는 사람:", "b@partner.example", "참조:", "제목:")), qh[:300])
check("원본 모양(표) 그대로", "<table>" in qh and "단가" in qh)
check("<style>·<head>·<title>·<html> 빠짐(쓰기 화면 모양 안 바뀜)", "<style" not in qh and "<head" not in qh and "<title" not in qh and "<html" not in qh, qh[:300])
check("cid 그림 = 그림 표시(🖼 이미지·[그림]) · 바깥 https 그림 유지", ("[그림]" in qh or "🖼 이미지" in qh) and "https://img.example/a.png" in qh and "cid:" not in qh)
check("위험한 것 빠짐(script·onclick)", "<script" not in qh and "onclick" not in qh)
hfw = k.get("/mail/compose?forward=%d" % HM).text
check("전달도 원본 모양 인용(전달된 메일)", "전달된 메일" in hfw and "&lt;table&gt;" in hfw)

print("== ⑧ 화면 ==")
h = km.get("/mail/inbox").text
check("종류 단추 셋(견적·발주·세금계산서)", all(("&cat=" + x) in h or ("cat=" + x) in h for x in ("견적", "발주", "세금계산서")) and h.count("mbx-chip kind") == 3)
check("왼쪽 🚩 기한 · ⏰ 다시 알림", 'href="/mail/inbox?flag=1"' in h and 'href="/mail/inbox?snz=1"' in h)
check("도구 줄 🚩 기한(오늘까지 숫자)", 'id="mtcFlag"' in h and "put('mtcFlag', j.flag_due)" in h)
check("목록 줄 꼬리표(종류)", 'class="mbx-kind k-' in h)
check("오른쪽 클릭 🚩 기한 ▸ · ⏰ 다시 알림 ▸", "🚩 기한 정하기 ▸" in h and "⏰ 다시 알림 ▸" in h and "window.mbxFollowMenu" in h)
check("새 메일 띠(처음 기준과 비교 · 눌러서 보기)", 'id="mbxNew"' in h and "if(baseId===null)" in h)
check("1분마다 가벼운 숫자 · 창 제목에 안 읽은 숫자", "mailCountsRefresh(true)" in h and "}, 60000);" in h and "document.title=(j.unread?" in h)
check("바탕화면 알림 — 켠 사람만 · 창이 안 보일 때만 · 같은 메일 한 번", "localStorage.getItem('knkmail.notify')==='1'" in h and "document.visibilityState==='visible') return;" in h and "knkmail.notified" in h)
vp = km.get("/mail/%d/pane" % Q1).text
check("읽기 화면 「🚩 기한·알림 ▾」(기한·다시 알림·할 일 날짜)", 'id="mvFu"' in vp and "mvFollow('flag','today')" in vp and "mvFollow('snz','tomorrow')" in vp and 'id="mvTaskDate"' in vp)
check("기한 있는 메일은 지금 기한 표시", "지금 01/05" in vp and "(지남)" in vp, vp[vp.find("mv-fu-h"):vp.find("mv-fu-h") + 200])
check("영어 번역 단추", "translateMail('en')" in vp)
tl = km.get("/mail/tools").text
check("설정·정리 🔔 새 메일 알림(바탕화면)", 'id="mtNoti"' in tl and "Notification.requestPermission()" in tl)

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
