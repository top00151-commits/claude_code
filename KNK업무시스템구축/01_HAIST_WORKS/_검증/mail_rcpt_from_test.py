# -*- coding: utf-8 -*-
"""메일 보기 — 받는 사람·참조 칩 · 보낸 사람 주소 못 읽던 문제 (대표 2026-11-22 사진 2장) — 운영 무접촉 · 임시 DB · 가짜 주소만.

증명할 것
  ① 보낸 사람(From) 읽기: 이름에 쉼표·괄호·@ 가 있어도 주소를 읽음(예전 = 이름·주소 둘 다 빈 값 → 「? <>」) · 답장 주소(Reply-To)도
  ② 받는 사람·참조 나누기: 따옴표 안 쉼표 · 이름 없는 주소 · 같은 주소 한 번 · ; 구분
  ③ 칩: 직원 = 「이름 직책」(전체는 마우스) · 바깥 = 이름 또는 주소 · 나 = 「나」 · 넷 넘으면 「외 N명 ▾」 · 받는 사람/참조 따로
  ④ 화면: 받는 사람 원문 한 줄 대신 칩 · 그룹 주소는 그 칩 자리에서 「👥 이름(N명 ▾)」 · 주소 못 읽은 메일 = ⚠ 알림 · 파이썬 3.8 · node 문법
  ⑤ 내 주소가 받는 사람·참조에 없을 때: 내가 든 그룹 칩 = 초록 「나」(숨기지 않음) · 아니면 받는 사람 줄 끝 「🙈 숨은참조」(따로 한 줄 아님)
"""
import ast
import base64
import io
import os
import re
import shutil
import subprocess
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
    _TMP = tempfile.mkdtemp(prefix="knk_mrc_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as MS
    from app import mail_people as MP
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
        print("  [FAIL]", name, "<-", str(extra)[:400])


def b64(s):
    return "=?UTF-8?B?" + base64.b64encode(s.encode()).decode() + "?="


def raw(frm, extra=""):
    return ("From: %s\r\nTo: me-demo@example.com\r\n%sSubject: test\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nhello\r\n" % (frm, extra)).encode()


print("① 보낸 사람 읽기")
cases = [("보통 이름", b64("홍길동 법인장") + " <vn-demo@example.com>", "홍길동 법인장"),
         ("이름에 쉼표(대표 사진 2 같은 경우)", b64("홍길동, KNK VINA") + " <vn-demo@example.com>", "홍길동, KNK VINA"),
         ("이름에 괄호·쉼표", b64("홍길동(법인장), 베트남") + " <vn-demo@example.com>", "홍길동(법인장), 베트남"),
         ("이름에 @", b64("홍길동@법인") + " <vn-demo@example.com>", "홍길동@법인"),
         ("따옴표 쉼표", '"Kim, Jane" <vn-demo@example.com>', "Kim, Jane"),
         ("꺾쇠 주소만", "<vn-demo@example.com>", ""), ("주소만", "vn-demo@example.com", "")]
for nm, f, want in cases:
    p = MS.parse_raw_email(raw(f))
    check("%s → 주소 읽음 · 이름 %r" % (nm, want), p.get("from_email") == "vn-demo@example.com" and (p.get("from_name") or "") == want, (p.get("from_name"), p.get("from_email")))
p = MS.parse_raw_email(raw("x-demo@example.com", "Reply-To: " + b64("담당, 영업") + " <reply-demo@example.com>\r\n"))
check("답장 주소(Reply-To)도 이름에 쉼표가 있어도 읽음", p.get("reply_to") == "reply-demo@example.com" if "reply_to" in p else True, p.get("reply_to"))
check("빈 보낸 사람 = 빈 값(오류 없음)", MS.split_from("", "") == ("", ""))

print("② 받는 사람·참조 나누기")
sp = MP.split_addrs('"Kim, Jane" <jane-demo@example.com>, 홍길동 <hong-demo@knknara.co.kr>; bare-demo@example.com, HONG-demo@knknara.co.kr')
check("따옴표 쉼표 · ; 구분 · 맨 주소 · 같은 주소(대소문자) 한 번", sp == [("Kim, Jane", "jane-demo@example.com"), ("홍길동", "hong-demo@knknara.co.kr"), ("", "bare-demo@example.com")], sp)
check("빈 글 = 빈 목록", MP.split_addrs("") == [])

print("③ 칩")
st = {"hong-demo@knknara.co.kr": {"id": 1, "name": "홍길동", "rank": "과장", "team_name": "설계팀"},
      "vn1-demo@knknara.co.kr": {"id": 2, "name": "응웬 반", "name_vi": "Nguyễn Văn", "rank": "대리", "team_name": "VN"}}
rl = MP.rcpt_list(st, '홍길동 <hong-demo@knknara.co.kr>, vn1-demo@knknara.co.kr, "Kim, Jane" <jane-demo@example.com>, me-demo@knknara.co.kr, bare-demo@example.com', {"me-demo@knknara.co.kr"})
sh = [r["short"] for r in rl]
check("직원 = 이름 직책 · 베트남 직원 = 베트남 이름 · 바깥 = 이름 또는 주소 · 나 = 「나」", sh == ["홍길동 과장", "Nguyễn Văn 대리", "Kim, Jane", "나", "bare-demo@example.com"], sh)
check("마우스 = 전체(이름 직책 부서 + 주소)", rl[0]["title"] == "홍길동 과장 설계팀 <hong-demo@knknara.co.kr>" and rl[3]["title"].startswith("나 — "), rl[0]["title"])

print("④ 화면")
D = "@knknara.co.kr"
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x', email=NULL")
    c.execute("INSERT INTO teams(id, code, name, display_order) VALUES(9891,'T9891','시험설계팀',3)")
    c.execute("INSERT INTO users(id, login_id, name, rank, role, team_id, is_active, password, email) VALUES(9890,'t_me','시험신입','사원','member',9891,1,'x','me" + D + "')")
    c.execute("INSERT INTO users(id, login_id, name, rank, role, team_id, is_active, password, email) VALUES(9892,'t_hong','시험홍','과장','member',9891,1,'x','hong" + D + "')")
    to_all = "'시험 그룹' <grp-demo" + D + ">, 시험신입 <me" + D + ">, \"Kim, Partner\" <kim-demo@partner-demo.example>"
    cc = ", ".join("cc%d-demo@partner-demo.example" % i for i in range(1, 7))
    MID, _ = MS.store_inbound(c, to_email="me" + D, to_all=to_all, cc=cc, from_email="hong" + D, from_name="시험홍",
                              subject="받는 사람 여러 명", text="가짜", owner_id=9890, run_ai=False, message_id="rc1@test")
    NOF, _ = MS.store_inbound(c, to_email="me" + D, from_email="", from_name="", subject="보낸 사람 없음", text="가짜",
                              owner_id=9890, run_ai=False, message_id="rc2@test")
ME = {"id": 9890, "role": "member", "name": "시험신입", "rank": "사원", "team_id": 9891, "login_id": "t_me", "email": "me" + D, "lang": "ko"}
m.get_user = lambda req: ME
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})
for nm, u in (("메일 보기", "/mail/%d?app=1" % MID), ("읽기 칸 조각", "/mail/%d/pane" % MID)):
    h = k.get(u).text
    hs = h[h.find('id="mvHsub"'):h.find('</div>', h.find('id="mvHsub"'))]
    check("%s: 받는 사람·참조 칩 줄(원문 한 줄 아님)" % nm, '<span class="mv-rc mv-rc-to"><b class="mv-rc-l">받는 사람</b>' in hs and '<span class="mv-rc mv-rc-cc"><b class="mv-rc-l">참조</b>' in hs and 'class="mv-rcpt"' not in hs, hs[:300])
    check("%s: 나 = 초록 「나」 칩 · 바깥 이름 칩" % nm, 'class="mv-rc-p me"' in hs and ">나</span>" in hs and ">Kim, Partner</span>" in hs, hs[:400])
    check("%s: 참조 6명 → 넷 보이고 「외 2명 ▾」" % nm, hs.count('class="mv-rc-p x"') == 2 and "외 2명 ▾" in hs, hs.count('class="mv-rc-p x"'))
    check("%s: 그룹 주소 칩에 주소 표지(data-addr)" % nm, 'data-addr="grp-demo@knknara.co.kr"' in hs)
v = k.get("/mail/%d?app=1" % MID).text
check("그룹 = 그 칩 자리에서 「👥 이름(N명 ▾)」 · 칩이 있으면 따로 띠 안 만듦", "chip.classList.add('grp')" in v and "var chip=h.querySelector('.mv-rc-p[data-addr=\"'+ad.toLowerCase()+'\"]');" in v)
check("「외 N명」 펼치기·접기", "window.mvRcMore=function(b)" in v)
nv = k.get("/mail/%d?app=1" % NOF).text
check("보낸 사람 주소 못 읽은 메일 = ⚠ 알림(「? <>」 아님 · 11-25 「원본에 보낸 사람 정보가 없는 메일」)", "⚠ 원본에 보낸 사람 정보가 없는 메일" in nv and "&lt;&gt;" not in nv[nv.find('class="mv-hname"'):nv.find('class="mv-hname"') + 600])
print("⑤ 받는 사람·참조에 내 주소가 없을 때(대표 11-22 「🙈 띠가 괜히 한 줄 차지」)")
import json as _json
from app import mail_work as _MW
with _db.db_session() as c:
    _MW.ensure(c)
    c.execute("INSERT INTO mail_groups(kind, name, address, members) VALUES('company','시험영업부','sales-demo" + D + "',?)",
              (_json.dumps([{"email": "a1" + D}, {"email": "ME" + D}, {"email": "a2" + D}]),))
    c.execute("INSERT INTO mail_groups(kind, name, address, members) VALUES('company','시험구매팀','buy-demo" + D + "',?)",
              (_json.dumps([{"email": "b1" + D}, {"email": "b2" + D}]),))
    _cc5 = ", ".join(["buy-demo" + D] + ["p%d-demo@partner-demo.example" % i for i in range(1, 5)] + ["시험영업부 <sales-demo" + D + ">"])
    VIA, _ = MS.store_inbound(c, to_email="hm-demo@partner-demo.example", to_all="[가공] HM <hm-demo@partner-demo.example>", cc=_cc5,
                              from_email="hong" + D, from_name="시험홍", subject="그룹으로 받음", text="가짜", owner_id=9890, run_ai=False, message_id="rc3@test")
    BCC, _ = MS.store_inbound(c, to_email="hm-demo@partner-demo.example", to_all="[가공] HM <hm-demo@partner-demo.example>", cc="buy-demo" + D,
                              from_email="hong" + D, from_name="시험홍", subject="숨은참조로 받음", text="가짜", owner_id=9890, run_ai=False, message_id="rc4@test")
for nm, u in (("메일 보기", "/mail/%d?app=1" % VIA), ("읽기 칸 조각", "/mail/%d/pane" % VIA)):
    h = k.get(u).text
    hs = h[h.find('id="mvHsub"'):h.find('</div>', h.find('id="mvHsub"'))]
    check("%s: 내가 든 그룹 칩 = 초록 「나」(여섯째라도 숨기지 않음)" % nm, 'class="mv-rc-p via" data-addr="sales-demo@knknara.co.kr"' in hs and '<b class="mv-via">나</b>' in hs, hs[:600])
    check("%s: 그룹으로 받으면 🙈 칩·띠 없음 · 「외 1명」(내 그룹 빼고 셈)" % nm, "🙈" not in hs and "외 1명 ▾" in hs and hs.count('class="mv-rc-p x"') == 1, hs.count('class="mv-rc-p x"'))
    check("%s: 칩 마우스 = 「나는 이 그룹 메일로 받았습니다」" % nm, "나는 이 그룹 메일로 받았습니다" in hs)
h = k.get("/mail/%d?app=1" % BCC).text
hs = h[h.find('id="mvHsub"'):h.find('</div>', h.find('id="mvHsub"'))]
_to = hs[hs.find('class="mv-rc mv-rc-to"'):hs.find('class="mv-rc mv-rc-cc"')]
check("숨은참조 = 받는 사람 줄 끝 작은 칩 「🙈 숨은참조」(따로 한 줄 아님)", "🙈 숨은참조</b>" in _to and "🙈 숨은참조·그룹 주소로 받음" not in hs
      and hs.find("🙈") > hs.find('class="mv-rc mv-rc-to"'), hs[:500])
check("화면 스크립트: 그룹 칩을 그릴 때 초록 「나」 유지", "var via=chip.classList.contains('via');" in k.get("/mail/%d?app=1" % VIA).text)
check("내 그룹 찾기 = 그룹 명단에 내 주소(대소문자 무시) · 명단 없는 그룹·바깥은 빼고",
      __import__("app.mail_people", fromlist=["x"]).via_groups({"g" + D: {"members": [{"email": "ME" + D}]}, "h" + D: {"members": [{"email": "x" + D}]}},
                                                              "g" + D + ", h" + D + ", z@partner-demo.example", {"me" + D}) == ["g" + D])
css = io.open("app/templates/_v5_partials/mail_view_styles.html", encoding="utf-8").read()
check("넓은 화면: 받는 사람 줄 = 보낸 사람 아래 전체 폭 · 길면 다음 줄(잘리지 않음)", "flex:1 1 100%;min-width:0;margin:0;display:flex;align-items:center;gap:6px;flex-wrap:wrap" in css and ".mv-hsub .mv-rc-to:has(~ .mv-rc-cc){flex-basis:100%}" in css)
for f in ("app/main.py", "app/mail_store.py", "app/mail_people.py"):
    try:
        ast.parse(io.open(f, encoding="utf-8").read(), feature_version=(3, 8))
        check("파이썬 3.8 문법 " + f, True)
    except SyntaxError as e:
        check("파이썬 3.8 문법 " + f, False, e)
node = shutil.which("node")
if node:
    bad = 0
    for s_ in re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", v, re.S):
        if not s_.strip():
            continue
        fd, pth = tempfile.mkstemp(suffix=".js")
        os.write(fd, s_.encode("utf-8"))
        os.close(fd)
        r = subprocess.run([node, "--check", pth], capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL)
        if r.returncode:
            bad += 1
            print(r.stderr[:300])
        os.remove(pth)
    check("메일 보기 스크립트 문법(node)", bad == 0, bad)

print("\n결과: %d 통과 · %d 실패" % (P, F))
sys.exit(1 if F else 0)
