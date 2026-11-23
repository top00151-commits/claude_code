# -*- coding: utf-8 -*-
"""메일 화면 2단계 「쉽게 찾기·구분·보기」 시험 — 가짜 직원·가짜 메일·임시 DB(운영 무접촉 · 실제 메일 없음).
대표 지시 2026-11-18 「2단계 진행해」(시안 A~K).
A 찾기: 띄어 쓴 낱말 모두 · 받은+보낸 · 받는 사람·참조·첨부 이름 · 무엇을(qf) · 기간 단추   C 결과 띠 · 회사 이름 = 그 폴더 메일도
B 폴더 색   D 광고·알림 흐리게 + 빼고 보기   E 날짜 묶음   F 📎 개수   G 「참조」   H 시간(오늘/올해/작년) · 글자 크게
I 200통에서 끊기지 않게(▼ 더 보기 · 겹침 없음)   J 보낸 사람 → 이 사람·이 회사 메일 · 이 사람에게 쓰기   K 이전 대화 접기
사용: py -3.13 _검증/mail_find_test.py"""
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
_so = sys.stdout
sys.stdout = io.StringIO()
try:
    import app.database as _db
    _TMP = tempfile.mkdtemp(prefix="knk_mfind_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
    from app import mail_find as mfd
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
        print("  [FAIL]", name, "<-", str(extra)[:600])


OWN, OTHER = 9001, 9002
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x' WHERE login_id='kjr'")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email) VALUES(9001,'kjr','시험대표','ceo',1,'x','boss@knknara.co.kr')")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9002,'t9002','시험이','member',1,'x')")
    c.execute("INSERT INTO customers(id, name) VALUES(701,'삼성전기㈜')")
    c.execute("INSERT INTO customer_contacts(customer_id, role, name, email) VALUES(701,'구매','박구매','p@semco.example')")
    c.execute("INSERT INTO suppliers(name, code, email) VALUES('GTS','SUP-T1','sales@gts.example')")


def put(frm, subject, text="", owner=OWN, name="보낸이", ago="-1 hours", html="", cc="", to=None, read=True):
    _SEQ[0] += 1
    with _db.db_session() as c:
        mid, _o = ms.store_inbound(c, to_email=to or "boss@knknara.co.kr", from_email=frm, from_name=name, subject=subject,
                                   text=text, html=html, cc=cc, owner_id=owner, run_ai=False, message_id="mfind-%d@test" % _SEQ[0])
        c.execute("UPDATE mail_messages SET received_at=datetime('now','localtime', ?), is_read=? WHERE id=?", (ago, 1 if read else 0, mid))
        if to:
            c.execute("UPDATE mail_messages SET to_email=? WHERE id=?", (to, mid))
    return mid


def sent(to, subject, ago="-2 hours"):
    with _db.db_session() as c:
        return c.execute("INSERT INTO mail_messages(user_id, direction, from_email, from_name, to_email, subject, body_text, is_read, received_at) "
                         "VALUES(?, 'out', 'boss@knknara.co.kr', '시험대표', ?, ?, '보냅니다', 1, datetime('now','localtime', ?))",
                         (OWN, to, subject, ago)).lastrowid


ids = {}
ids["semco"] = put("p@semco.example", "11월 발주서 송부", "발주서 송부드립니다.", name="박구매", ago="-30 minutes")
ids["semco_samp"] = put("q@semco.example", "샘플 일정 문의", "샘플 일정 가능할까요?", name="윤품질", ago="-40 minutes")
ids["gts_en"] = put("eng@gts.example", "Sample schedule", "Please check the sample.", name="GTS Eng", ago="-50 minutes")
ids["cc"] = put("x@vendor-cc.example", "도면 송부(참조)", "도면 송부드립니다.", name="참조발신", cc="boss@knknara.co.kr", to="someone@knknara.co.kr", ago="-55 minutes")
ids["att"] = put("y@vendor-att.example", "자료 송부", "첨부 확인 부탁", name="첨부발신", ago="-70 minutes")
with _db.db_session() as c:
    c.execute("INSERT INTO mail_attachments(mail_id, filename, mime, size, is_inline, data) VALUES(?,?,?,?,0,?)", (ids["att"], "견적서_가나다.pdf", "application/pdf", 1000, b"x"))
    c.execute("INSERT INTO mail_attachments(mail_id, filename, mime, size, is_inline, data) VALUES(?,?,?,?,0,?)", (ids["att"], "도면.dwg", "application/octet-stream", 1000, b"x"))
    c.execute("INSERT INTO mail_attachments(mail_id, filename, mime, size, is_inline, data) VALUES(?,?,?,?,1,?)", (ids["att"], "logo.png", "image/png", 10, b"x"))
for i in range(3):
    ids["ad%d" % i] = put("newsletter@weekly.example", "(광고) 주간 소식 %d" % i, "소식입니다. 수신거부", name="주간소식", ago="-%d minutes" % (80 + i))
ids["lastyear"] = put("old@oldco.example", "작년 메일", "옛날", name="옛사람", ago="-400 days")
ids["html_q"] = put("p@semco.example", "RE: 견적 회신", "", name="박구매", ago="-20 minutes",
                    html='<div>견적 확인했습니다. 내일 보내드리겠습니다.</div><div class="gmail_quote"><blockquote>이전 글 이전 글</blockquote></div>')
ids["text_q"] = put("p@semco.example", "RE: 납기", "납기 확인했습니다. 다음 주 출하합니다.\n\n-----Original Message-----\nFrom: 시험대표\nSent: 2026-11-17\n납기 알려 주세요.", name="박구매", ago="-25 minutes")
ids["other"] = put("p@semco.example", "남의 메일 샘플", "x", owner=OTHER)
ids["sent1"] = sent("q@semco.example", "RE: 샘플 일정 답장")
# 200통 넘게(목록 끊김 시험) — 30일 앞까지 흩어 둠
for i in range(230):
    put("bulk%d@filler.example" % (i % 7), "채움 메일 %d" % i, "내용 %d" % i, name="채움", ago="-%d hours" % (3 + i * 3))

_U = {"v": {"id": OWN, "role": "ceo", "name": "시험대표", "team_id": None, "team_name": ""}}
_keep = m.get_user
m.get_user = lambda req: _U["v"]


def client(port=5051, host="works.knknara.co.kr"):
    k = TestClient(m.app, base_url="http://127.0.0.1:%d" % port, raise_server_exceptions=False, follow_redirects=False)
    k.headers.update({"host": host, "x-forwarded-proto": "https"})
    return k


def rows(h):
    return re.findall(r'class="mbx-row[^"]*" data-mail-id="(\d+)"', h)


def chips_n(h):
    mm = re.search(r'class="mbx-chips-n"[^>]*>([\d,]+)통', h)
    return int(mm.group(1).replace(",", "")) if mm else -1


def has(h, mid):
    return ('data-mail-id="%d"' % mid) in h


try:
    k = client()
    print("== A. 찾기 ==")
    h = k.get("/mail/inbox?thread=0&q=샘플").text
    check("「샘플」: 받은 메일 + 내가 보낸 메일 함께", has(h, ids["semco_samp"]) and has(h, ids["sent1"]) and "📤 보냄" in h)
    check("남의 메일은 안 나옴", not has(h, ids["other"]))
    h = k.get("/mail/inbox?thread=0&q=샘플&where=in").text
    check("「받은 메일만」이면 보낸 메일 빠짐", has(h, ids["semco_samp"]) and not has(h, ids["sent1"]))
    h = k.get("/mail/inbox?thread=0&q=샘플 일정").text
    check("두 낱말 모두(띄어 써도) — 「샘플 일정」", has(h, ids["semco_samp"]) and not has(h, ids["gts_en"]))
    h = k.get("/mail/inbox?thread=0&q=일정 샘플").text
    check("낱말 순서가 달라도(「일정 샘플」 — 붙은 글자 아님)", has(h, ids["semco_samp"]))
    h = k.get("/mail/inbox?thread=0&q=견적서_가나다").text
    check("첨부 파일 이름으로 찾기", has(h, ids["att"]))
    h = k.get("/mail/inbox?thread=0&q=logo.png").text
    check("본문 속 그림(인라인)은 첨부 이름 찾기에서 뺌", not has(h, ids["att"]))
    h = k.get("/mail/inbox?thread=0&q=someone@knknara").text
    check("받는 사람 주소로 찾기", has(h, ids["cc"]))
    h = k.get("/mail/inbox?thread=0&q=도면&qf=att").text
    check("무엇을=첨부 파일 이름: 「도면」 → 도면.dwg 메일만(제목 「도면 송부」는 아님)", has(h, ids["att"]) and not has(h, ids["cc"]))
    h = k.get("/mail/inbox?thread=0&q=도면&qf=subj").text
    check("무엇을=제목: 「도면」 → 제목에 있는 메일만", has(h, ids["cc"]) and not has(h, ids["att"]))
    h = k.get("/mail/inbox?thread=0&q=박구매&qf=from").text
    check("무엇을=보낸·받는 사람: 「박구매」", has(h, ids["semco"]) and not has(h, ids["semco_samp"]))
    h = k.get("/mail/inbox?thread=0&q=\"샘플 일정 문의\"").text
    check("따옴표 안은 한 낱말", has(h, ids["semco_samp"]) and not has(h, ids["sent1"]))
    h = k.get("/mail/inbox?thread=0&per=today").text
    check("기간 「오늘」: 작년 메일 없음 · 오늘 메일 있음", has(h, ids["semco"]) and not has(h, ids["lastyear"]))
    h = k.get("/mail/inbox?thread=0&per=year&q=작년").text
    check("기간 「올해」: 작년 메일 안 나옴", not has(h, ids["lastyear"]))
    h = k.get("/mail/inbox?thread=0&q=작년").text
    check("기간 「전체」: 작년 메일 나옴", has(h, ids["lastyear"]))
    check("기간 이름표(시작·끝)", mfd.period_range("today")[0] == mfd.period_range("today")[1] and mfd.period_range("") == ("", ""))

    print("== C. 결과 띠 · 회사 이름 ==")
    h = k.get("/mail/inbox?thread=0&q=샘플 일정").text
    check("결과 띠: 「샘플」「일정」 모두 · 통수 · 받은+보낸 · ✕ 찾기 끝",
          'class="mbx-res"' in h and "「<b>샘플</b>」「<b>일정</b>」 모두 들어간 메일" in h and "받은+보낸 메일" in h and "✕ 찾기 끝" in h)
    n = chips_n(h)
    check("결과 통수 = 목록 줄 수(200 안)", n == len(rows(h)), (n, len(rows(h))))
    h = k.get("/mail/inbox?thread=0&q=삼성전기").text
    check("회사 이름 「삼성전기」 → 본문에 그 글자 없는 그 폴더 메일도(영문 주소)", has(h, ids["semco_samp"]) and has(h, ids["semco"]))
    check("결과 띠에 「삼성전기」 폴더 메일도 함께", "「삼성전기」 폴더 메일" in h)
    h = k.get("/mail/inbox?thread=0&q=GTS sample").text
    check("「GTS sample」 → GTS 폴더 + 본문 sample", has(h, ids["gts_en"]))
    check("찾은 낱말을 화면 스크립트로 넘김(노랗게)", 'window._mbxTerms = ["GTS", "sample"]' in h, re.findall(r"window._mbxTerms = [^;]*", h))

    print("== I. 200통에서 끊기지 않게 ==")
    h = k.get("/mail/inbox?thread=0").text
    r1 = rows(h)
    tot = chips_n(h)
    check("첫 화면 200줄 · 전체 통수 표시", len(r1) == 200 and tot > 200, (len(r1), tot))
    mh = re.search(r'class="mbx-morerows" data-href="([^"]+)" data-prev="([^"]*)"', h)
    check("▼ 더 보기 (남은 통수)", mh is not None and ("%d통 더" % (tot - 200)) in h.replace(",", ""), (mh and mh.group(1)))
    href = mh.group(1).replace("&amp;", "&") if mh else ""
    fr = k.get(href + "&prev=" + (mh.group(2) if mh else "")).text
    r2 = rows(fr)
    check("다음 조각: 나머지 전부 · 겹침 없음", len(r2) == tot - 200 and not (set(r1) & set(r2)), (len(r2), len(set(r1) & set(r2))))
    check("조각은 목록 줄만(머리·왼쪽 메뉴 없음)", "<html" not in fr.lower() and "mbx-side" not in fr)
    check("조각 첫 날짜 묶음이 앞 조각 마지막과 같으면 다시 안 붙임", not fr.lstrip().startswith('<div class="mbx-day">%s<' % (mh.group(2) if mh else "x")))
    check("마지막 조각엔 더 보기 없음", "mbx-morerows" not in fr)
    h2 = k.get("/mail/inbox").text
    check("대화로 묶기 켠 상태도 더 보기 있음", "mbx-morerows" in h2)
    hf = k.get("/mail/inbox?fd=gen&thread=0").text
    check("일반(분류안됨) 보기 = 위 띠 없음(대표 11-23 「안 나오게」)", 'class="mf-cur">' not in hf and "📂 분류안됨 ✕" in hf)

    print("== D · F · G · B · E · H ==")
    h = k.get("/mail/inbox?thread=0").text
    # 11-23 대표 「광고·알림 칸에만 보이게」 — 받은편지함 그냥 목록엔 광고 메일이 없고 📢 칸·이 사람 보기·찾기에서는 보임
    hw = k.get("/mail/inbox?thread=0&who=newsletter@weekly.example").text
    ad_row = re.search(r'<a [^>]*data-mail-id="%d"[^>]*>.*?</a>' % ids["ad0"], hw, re.S)
    check("광고·알림: 흐리게(robot) + 꼬리표(이 사람 보기)", ad_row and "robot" in ad_row.group(0)[:200] and "광고·알림</span>" in ad_row.group(0))
    hn = k.get("/mail/inbox?thread=0&noad=1").text
    ha = k.get("/mail/inbox?thread=0&ad=1").text
    check("받은편지함 = 광고 메일 빠짐(📢 칸에만 3통) · 다른 메일은 그대로 · 「광고·알림 빼기」 와 같은 통수",
          not has(h, ids["ad0"]) and has(h, ids["semco"]) and has(ha, ids["ad0"]) and chips_n(ha) == 3 and chips_n(hn) == tot, (chips_n(hn), chips_n(ha), tot))
    from app import mail_cleanup as _cl
    with _db.db_session() as c:
        _bk = mfd.bulk_senders(c, OWN)
        _cg = {x["addr"] for x in _cl.sender_groups(c, OWN)["groups"] if x["kind"] == "bulk"}
    check("광고 판별 = 보낸 곳별 정리와 같은 기준(같은 주소 묶음)", _bk == _cg and "newsletter@weekly.example" in _bk and "p@semco.example" not in _bk, (_bk, _cg))
    att_row = re.search(r'<a [^>]*data-mail-id="%d"[^>]*>.*?</a>' % ids["att"], h, re.S)
    check("📎 첨부 개수(본문 속 그림 빼고 2)", att_row and "📎 2</span>" in att_row.group(0), att_row and att_row.group(0)[-300:])
    cc_row = re.search(r'<a [^>]*data-mail-id="%d"[^>]*>.*?</a>' % ids["cc"], h, re.S)
    semco_row = re.search(r'<a [^>]*data-mail-id="%d"[^>]*>.*?</a>' % ids["semco"], h, re.S)
    check("「참조」 꼬리표 — 참조로 받은 메일만", cc_row and "참조</span>" in cc_row.group(0) and "mbx-cc" not in semco_row.group(0))
    check("폴더 색: 삼성전기 = 고객사(파랑 fk-customer)", semco_row and 'mbx-fdtag fk-customer' in semco_row.group(0))
    gts_row = re.search(r'<a [^>]*data-mail-id="%d"[^>]*>.*?</a>' % ids["gts_en"], h, re.S)
    check("폴더 색: GTS = 업체(초록 fk-vendor)", gts_row and 'mbx-fdtag fk-vendor' in gts_row.group(0))
    check("왼쪽 폴더 묶음 색 점", 'class="mf-dot fk-customer"' in h and 'class="mf-dot fk-vendor"' in h and 'class="mf-dot fk-gen"' in h)
    days = re.findall(r'<div class="mbx-day">([^<]+)</div>', h)
    check("날짜 묶음: 오늘 · … · 겹침 없음", days and days[0].startswith("오늘 · ") and len(days) == len(set(days)), days[:6])
    check("시간: 오늘은 시각만(HH:MM)", re.search(r'data-mail-id="%d".*?class="mbx-time"[^>]*>(\d\d:\d\d)<' % ids["semco"], h, re.S) is not None)
    hy = k.get("/mail/inbox?thread=0&q=작년").text
    check("시간: 작년 메일은 연-월-일", re.search(r'class="mbx-time"[^>]*>\d{4}-\d\d-\d\d<', hy) is not None)
    check("time_label: 올해 = 월-일 (요일)", re.match(r"\d\d-\d\d \([월화수목금토일]\)$", mfd.time_label("%d-01-02 10:00:00" % __import__("datetime").date.today().year)) is not None or __import__("datetime").date.today().strftime("%m-%d") == "01-02")
    t = k.get("/mail/tools").text
    check("⚙ 설정·정리에 「글자 크게 보기」(이 기기에만)", "글자 크게 보기" in t and "mtBigToggle()" in t)
    check("받은편지함·읽기 화면이 「글자 크게」를 머리에서 읽음", "knkmail.big" in h and "knkmail.big" in k.get("/mail/%d" % ids["semco"]).text)

    print("== J. 보낸 사람 → 모아 보기 ==")
    p = k.get("/mail/%d/pane" % ids["semco"]).text
    check("보낸 사람 이름 누르면 묶음(이 사람 · 이 회사 · 쓰기)",
          'class="mv-who"' in p and "/mail/inbox?who=p@semco.example" in p and "🏢 삼성전기 메일 모두" in p and "/mail/compose?to=p@semco.example" in p, p[:0])
    hw = k.get("/mail/inbox?thread=0&who=p@semco.example").text
    check("이 사람과 주고받은 메일(받은 것)", has(hw, ids["semco"]) and has(hw, ids["text_q"]) and not has(hw, ids["semco_samp"]))
    hw2 = k.get("/mail/inbox?thread=0&who=q@semco.example").text
    check("이 사람과 주고받은 메일 — 내가 보낸 것도", has(hw2, ids["sent1"]) and has(hw2, ids["semco_samp"]))
    check("결과 띠 「q@semco.example 와 주고받은 메일」", "q@semco.example</b> 와 주고받은 메일" in hw2)
    pa = k.get("/mail/%d/pane" % ids["att"]).text
    check("폴더 없는 회사: 「@회사주소 메일 모두」", "/mail/inbox?dom=vendor-att.example" in pa)
    hd = k.get("/mail/inbox?thread=0&dom=semco.example").text
    check("@semco.example 메일 모두(받은+보낸)", has(hd, ids["semco"]) and has(hd, ids["semco_samp"]) and has(hd, ids["sent1"]))
    cp = k.get("/mail/compose?to=p@semco.example").text
    check("「이 사람에게 메일 쓰기」 → 받는 사람 채움", "p@semco.example" in cp)
    cpx = k.get('/mail/compose?to=<b>x</b>@y').text
    check("받는 사람에 꺾쇠 등 이상한 글자는 안 채움", "<b>x</b>@y" not in cpx)

    print("== K. 이전 대화 접기 ==")
    ph = k.get("/mail/%d/pane" % ids["html_q"]).text
    check("서식 메일: 인용을 <details> 로 접음(iframe 안 · 「이전 메일 보기」)", "knk-q" in ph and "이전 메일 보기" in ph and "details.knk-q" in ph)
    pt = k.get("/mail/%d/pane" % ids["text_q"]).text
    check("글 메일: 새로 쓴 부분 먼저 · 「▸ 이전 메일 보기」 안에 옛 글", 'class="mv-quote"' in pt and pt.find("다음 주 출하합니다") < pt.find("mv-quote") < pt.find("납기 알려 주세요"))
    p1 = k.get("/mail/%d/pane" % ids["semco"]).text
    check("인용 없는 메일은 그대로(접기 없음)", "mv-quote" not in p1 and "knk-q\"" not in p1)
    check("전달만 한 메일(위에 쓴 글 없음)은 접지 않음", "knk-q" not in mfd.fold_quote_html('<div class="gmail_quote">---------- Forwarded message ---------<br>원문</div>'))
    check("한국어 「보낸 사람: / 보낸 날짜:」 머리도 접음",
          "knk-q" in mfd.fold_quote_html('<div>회신드립니다 내용 확인했습니다.</div><div><span>보낸 사람: 홍 &lt;a@b&gt;<br>보낸 날짜: 2026-11-01</span></div><div>옛 글</div>'))

    print("== kmail · 다른 화면 ==")
    km = client(port=5053, host="kmail.knknara.co.kr")
    check("kmail 찾기 200", km.get("/mail/inbox?q=샘플").status_code == 200)
    check("kmail 더 보기 조각 200", km.get(href).status_code == 200)
    for path in ("/mail/sent?q=샘플", "/mail/inbox?fd=gen&q=채움", "/mail/inbox?reply=1&q=x", "/mail/inbox?star=1&per=week", "/mail/inbox?off=999999",
                 "/mail/inbox?per=bad&qf=bad&where=bad", "/mail/inbox?q=" + "%25" * 50, "/mail/inbox?q=a'b\"c"):
        check("%s 200" % path[:50], k.get(path).status_code == 200)
    _U["v"] = {"id": OTHER, "role": "member", "name": "시험이", "team_id": None, "team_name": ""}
    ho = k.get("/mail/inbox?thread=0&q=발주서").text
    check("다른 직원: 대표 메일 안 보임", not has(ho, ids["semco"]))
finally:
    m.get_user = _keep

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
