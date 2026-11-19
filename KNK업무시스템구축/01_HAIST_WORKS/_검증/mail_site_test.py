# -*- coding: utf-8 -*-
"""📮 메일 전용 주소(kmail) 분리 검증 — app/mail_site.py + app/main.py 연결.

대표 지시 2026-11-16: 「이음메일을 이음웍스와 별개로」 → 「5053으로 적용해서 설정해」.

운영 서버·운영 DB·운영 메일 무접촉 — 전부 이 PC 안(메모리 · 임시 폴더 · 127.0.0.1 임시 포트).
실제 메일 내용·비밀번호·토큰을 쓰지 않는다(가짜 값만).

증명할 것
  §1 ⭐판정 — 5053 으로 들어오면 Host 가 localhost 여도 메일 전용 / 5051 은 아님 / 이름(kmail)으로도 잡힘
  §2 열어 주는 길 — 메일 화면은 통과, 업무 화면은 works 로
  §3 로그인 뒤 착지 — 메일 안쪽만, 그 밖이면 받은편지함
  §4 ⭐돌아올 주소는 works · kmail 둘뿐 — 요청이 뭐라 해도 다른 주소를 안 만든다
  §5 넘김(미들웨어) — 메일 전용 주소가 아니면 손대지 않는다(회귀)
  §6 main.py 연결 — 등록 위치·순서, 업무 앱(/app)은 그대로
  §7 실제 앱으로 — /login · /mail/app · /sso/land · 매니페스트가 두 주소에서 각각 맞게
  §8 ⭐⭐회귀 — works 로 들어오는 응답이 **운영본(origin/main)과 똑같다**(의도한 두 곳만 다름)
  §9 ⭐실제 소켓 — WORKS 가 두 포트를 함께 듣는다 · 포트가 막혀 있으면 본체 무영향 · 풀리면 저절로 잡는다

돌리기:  py -3.13 _검증/mail_site_test.py        (uvicorn·starlette·httpx 가 있는 파이썬)
"""
import ast
import asyncio
import http.client
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from urllib.parse import parse_qs, quote, unquote, urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
sys.dont_write_bytecode = True
QUICK = "--quick" in sys.argv                   # 운영본 대조(§8 · 가장 오래 걸림)를 건너뛴다

WORKS = "https://works.knknara.co.kr"
KMAIL = "https://kmail.knknara.co.kr"
MSG_LOGIN = "https://msg.knknara.co.kr/sso/login?redirect_uri="

# §8 에서 운영본과 견줄 요청(전부 로그인 없이 · DB 없이 답하는 것)
DUMP_REQS = [
    ("GET", "/login"),
    ("GET", "/login?next=%2Fmail%2Finbox"),
    ("GET", "/login?next=https%3A%2F%2Fevil.example.com"),
    ("GET", "/login?next=%2F%2Fevil.example.com"),
    ("GET", "/mail/app"),
    ("GET", "/mail/app?next=%2Fmail%2Fcompose"),
    ("GET", "/mail/app?next=%2Fhome"),
    ("GET", "/app"),
    ("GET", "/"),
    ("GET", "/home"),
    ("GET", "/dashboard"),
    ("GET", "/mail/inbox"),
    ("GET", "/mail/inbox?app=1"),
    ("GET", "/mail/compose"),
    ("GET", "/mail/account"),
    ("GET", "/admin/mail-send"),
    ("GET", "/mail/manifest.webmanifest"),
    ("GET", "/manifest.webmanifest"),
    ("GET", "/mail/sw.js"),
    ("GET", "/sw.js"),
    ("GET", "/api/version"),
    ("GET", "/logout"),
    ("POST", "/mail/send"),
    ("POST", "/mail/draft/save"),
    ("GET", "/api/mail/contacts?q=a"),
    ("GET", "/static/css/__no_such_file__.css"),
]


def _dump_mode(approot):
    """(하위 프로세스) approot 의 앱을 불러 DUMP_REQS 응답을 JSON 으로 찍는다 — works 로 들어온 것처럼."""
    os.chdir(approot)
    sys.path.insert(0, approot)
    os.environ.pop("KNK_MAIL_SITE_PORT", None)
    real_out = sys.stdout
    sys.stdout = io.StringIO()                 # 앱이 찍는 기동 로그는 버린다(JSON 만 내보낸다)
    try:
        import app.database as _db
        tmpd = tempfile.mkdtemp(prefix="knk_ms_dump_")
        _db.DB_PATH = os.path.join(tmpd, "empty.db")       # 작업 폴더에 DB 를 만들지 않게
        import app.main as m
        from starlette.testclient import TestClient
        cl = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False,
                        follow_redirects=False)
        out = []
        for method, url in DUMP_REQS:
            r = cl.request(method, url, headers={"host": "works.knknara.co.kr",
                                                 "x-forwarded-proto": "https"})
            body = r.content
            rec = {"req": method + " " + url, "status": r.status_code,
                   "location": r.headers.get("location", ""),
                   "ctype": (r.headers.get("content-type") or "").split(";")[0],
                   "len": len(body)}
            if rec["ctype"] in ("application/json", "application/manifest+json"):
                try:
                    rec["json"] = r.json()
                except Exception:
                    rec["json"] = None
            out.append(rec)
        shutil.rmtree(tmpd, ignore_errors=True)
    finally:
        sys.stdout = real_out
    print(json.dumps(out, ensure_ascii=False))


if len(sys.argv) >= 3 and sys.argv[1] == "--dump":
    _dump_mode(sys.argv[2])
    sys.exit(0)

sys.path.insert(0, ROOT)
os.environ.pop("KNK_MAIL_SITE_PORT", None)      # 시험은 환경변수 없이 시작(= 지금 운영과 같은 상태)
os.environ.pop("KNK_MAIL_SITE_BIND", None)

from app import mail_site as ms                 # noqa: E402

MSLOG = []                                      # mail_site 가 찍는 [MAIL-SITE] 로그를 여기로 모은다(화면을 어지럽히지 않게)
ms.print = lambda *a, **k: MSLOG.append(" ".join(str(x) for x in a))

PASS = FAIL = 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [PASS]", name)
    else:
        FAIL += 1
        print("  [FAIL]", name, extra)


def scope(port=5051, host="works.knknara.co.kr", path="/", method="GET", qs=b"", raw=None, typ="http"):
    sc = {"type": typ, "method": method, "path": path, "query_string": qs,
          "server": ("127.0.0.1", port), "headers": []}
    if host is not None:
        sc["headers"].append((b"host", host.encode("latin-1")))
    if raw is not None:
        sc["raw_path"] = raw
    return sc


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


# ════════════════════════════════════════════════════════════════════════════
print("\n§1 판정 — 어느 주소로 들어왔나")
check("환경변수가 없으면 입구 포트 = 0(끔)", ms.LISTEN_PORT == 0, ms.LISTEN_PORT)
check("(입구 끔) 5053 으로 왔다는 표시만으로는 메일 전용이 아니다", not ms.is_mail_site_scope(scope(5053, "localhost:5053")))
check("(입구 끔) 이름이 kmail 이면 메일 전용", ms.is_mail_site_scope(scope(5051, "kmail.knknara.co.kr")))
check("(입구 끔) works 는 메일 전용 아님", not ms.is_mail_site_scope(scope(5051, "works.knknara.co.kr")))

ms.LISTEN_PORT = 5053                            # ── 입구를 연 상태(운영에서 켠 뒤)
check("⭐5053 + Host 가 localhost:5053 → 메일 전용(포트로 잡는다)", ms.is_mail_site_scope(scope(5053, "localhost:5053")))
check("⭐5053 + Host 가 127.0.0.1 → 메일 전용", ms.is_mail_site_scope(scope(5053, "127.0.0.1")))
check("⭐5053 + Host 헤더가 아예 없어도 → 메일 전용", ms.is_mail_site_scope(scope(5053, None)))
check("⭐5053 + Host 가 works → 메일 전용 **아님**(업무 이름으로 온 것은 어느 포트든 다시 넘기지 않는다 — 무한 왕복 방지)",
      not ms.is_mail_site_scope(scope(5053, "works.knknara.co.kr")) and not ms.is_mail_site_scope(scope(5053, "WORKS.knknara.co.kr:443")))
check("5053 + 엉뚱한 이름(evil) → 메일 전용(포트로 잡는다 · works 만 예외)", ms.is_mail_site_scope(scope(5053, "evil.example.com")))
check("⭐⭐5051 + works → 메일 전용 아님(지금 운영 그대로)", not ms.is_mail_site_scope(scope(5051, "works.knknara.co.kr")))
check("5051 + localhost → 메일 전용 아님", not ms.is_mail_site_scope(scope(5051, "localhost:5051")))
check("5051 + kmail → 메일 전용(이름으로도 잡힌다 — 중계 대상을 5051 로 바꾸는 길도 열려 있음)",
      ms.is_mail_site_scope(scope(5051, "kmail.knknara.co.kr")))
check("이름 뒤 포트(kmail…:443)·대문자·끝점(.)도 같은 이름으로 본다",
      ms.is_mail_site_scope(scope(5051, "KMail.KNKNARA.co.kr:443")) and ms.is_mail_site_scope(scope(5051, "kmail.knknara.co.kr.")))
for bad in ("kmail.knknara.co.kr.evil.example.com", "xkmail.knknara.co.kr", "kmail.knknara.co.kr@evil.example.com",
            "evil.example.com", "kmail.knknara.co", "[::1]:5051", ""):
    check("비슷한 이름 %r → 메일 전용 아님" % bad, not ms.is_mail_site_scope(scope(5051, bad)))
check("server 정보가 없거나 이상해도 예외 없이 판정", (not ms.is_mail_site_scope({"type": "http", "headers": [], "server": None}))
      and (not ms.is_mail_site_scope({"type": "http"})) and (not ms.is_mail_site_scope({"type": "http", "server": ("x",), "headers": None})))


class _Req:
    def __init__(self, sc):
        self.scope = sc


check("Request 로 물어도 같다(is_mail_site)", ms.is_mail_site(_Req(scope(5053, "localhost"))) and not ms.is_mail_site(_Req(scope(5051))))
check("Request 가 이상해도(scope 없음) 예외 없이 False", ms.is_mail_site(object()) is False)

# ════════════════════════════════════════════════════════════════════════════
print("\n§2 열어 주는 길")
OPEN = ["/mail/inbox", "/mail/compose", "/mail/sent", "/mail/drafts", "/mail/trash", "/mail/account", "/mail/account/test",
        "/mail/123", "/mail/123/pane", "/mail/123/att/4", "/mail/send", "/mail/draft/save", "/mail/large/upload",
        "/mail/rules", "/mail/signature", "/mail/app", "/mail/manifest.webmanifest", "/mail/sw.js", "/mail/icon-192.png",
        "/admin/mail-send", "/admin/mail-fetch", "/admin/mail-fetch/run", "/admin/mail-inbound", "/admin/mail-purge/run",
        "/api/mail/contacts", "/api/mail/ai-compose", "/api/mail/7/translate", "/api/mail/ro/list",
        "/static/css/v5_main.css", "/sso/land", "/login", "/logout", "/dl/abc", "/api/version", "/healthz"]
CLOSED = ["/home", "/dashboard", "/team", "/projects", "/contacts", "/contacts/3", "/sales/orders", "/sales/quotes/new", "/daily",
          "/app", "/manifest.webmanifest", "/sw.js", "/icon.svg", "/uploads/a.png", "/api/customers/options", "/api/notifications",
          "/admin", "/admin/users", "/admin/mailbox", "/admin/mail", "/mailx", "/mail-x", "/loginx", "/login/x", "/logout2",
          "/api/mailx", "/api/versions", "/static", "/sso", "/dl", "/meetings", "/voice-notes",
          "/mail/settings", "/mail/settings/delete", "/mail/test"]
bad_open = [p for p in OPEN if not ms.allows(p)]
bad_closed = [p for p in CLOSED if ms.allows(p)]
check("메일 화면·메일이 부르는 주소 %d개 전부 통과" % len(OPEN), not bad_open, bad_open)
check("업무 화면·업무 주소 %d개 전부 works 로(통과 안 함)" % len(CLOSED), not bad_closed, bad_closed)
check("/mail/settings 는 업무 화면(연락처 쪽) → works 로 · 이름이 비슷한 /mail/settingsx 는 메일 쪽 규칙 그대로",
      (not ms.allows("/mail/settings")) and ms.allows("/mail/settingsx"))

# 메일 화면들이 실제로 부르는 주소를 템플릿에서 긁어 — 전부 「통과」 안에 있는지(화면이 깨지지 않는 근거)
import re  # noqa: E402
TPL = os.path.join(ROOT, "app", "templates")
MAIL_TPLS = ["mail_account.html", "mail_compose.html", "mail_inbox.html", "mail_rules.html", "mail_signature.html",
             "mail_view.html", "mail_view_pane.html", "admin_mail_blocklist.html", "admin_mail_fetch.html",
             "admin_mail_inbound.html", "admin_mail_purge.html", "admin_mail_send.html",
             os.path.join("_v5_partials", "mail_view_body.html"), os.path.join("_v5_partials", "mail_app_head.html"),
             os.path.join("_v5_partials", "mail_pwa_head.html")]
bg_calls, missing_tpl = [], []
for t in MAIL_TPLS:
    fp = os.path.join(TPL, t)
    if not os.path.exists(fp):
        missing_tpl.append(t)
        continue
    src = io.open(fp, encoding="utf-8").read()
    # 뒤에서 부르는 것(fetch · XHR open · 폼 action · 이미지/스크립트 src · 매니페스트/아이콘 link)
    for mo in re.finditer(r"""(?:fetch\(\s*|\.open\(\s*['"][A-Z]+['"]\s*,\s*|action=|src=|register\(\s*)['"`](/[^'"`\s?{$+]*)""", src):
        bg_calls.append((t, mo.group(1)))
    for mo in re.finditer(r"""<link[^>]+href=['"](/[^'"\s?]*)""", src):
        bg_calls.append((t, mo.group(1)))
check("메일 화면 템플릿 %d개를 다 찾았다" % len(MAIL_TPLS), not missing_tpl, missing_tpl)
bad_bg = sorted({(t, u) for t, u in bg_calls if not ms.allows(u)})
check("⭐메일 화면이 뒤에서 부르는 주소 %d건이 전부 메일 전용 주소에서 열린다(업무 주소로 새는 호출 0)" % len(bg_calls),
      len(bg_calls) >= 25 and not bad_bg, (len(bg_calls), bad_bg[:8]))

# ════════════════════════════════════════════════════════════════════════════
print("\n§3 로그인 뒤 착지(메일 전용 주소)")
H = ms.MAIL_HOME
check("첫 화면 = 받은편지함(앱 모드)", H == "/mail/inbox?app=1")
for nxt, want in [("/mail/compose", "/mail/compose"), ("/mail/compose?reply=5", "/mail/compose?reply=5"),
                  ("/mail/inbox?app=1", "/mail/inbox?app=1"), ("/mail/123", "/mail/123"),
                  ("/admin/mail-send", "/admin/mail-send"),
                  ("", H), (None, H), ("/home", H), ("/dashboard", H), ("/", H), ("/mail", H),
                  ("/mail/settings", H), ("/mail/test", H), ("/contacts/3", H), ("/login", H), ("/sso/land", H),
                  ("/static/x.css", H), ("/api/mail/contacts", H), ("/dl/abc", H)]:
    got = ms.landing(nxt)
    check("착지 %-26r → %s" % (nxt, want), got == want, got)

# ════════════════════════════════════════════════════════════════════════════
print("\n§4 돌아올 주소는 둘뿐")
outs = set()
for port in (5051, 5053, 80, 443, 0):
    for host in ("works.knknara.co.kr", "kmail.knknara.co.kr", "evil.example.com", "localhost:5053", "kmail.knknara.co.kr.evil.example.com",
                 "evil.example.com/kmail.knknara.co.kr", "", None, "a\r\nb", "https://evil.example.com"):
        outs.add(ms.public_base(_Req(scope(port, host))))
check("어떤 포트·어떤 Host 를 넣어도 결과는 works · kmail 두 개뿐", outs == {WORKS, KMAIL}, outs)
check("5053 → kmail / 5051+works → works", ms.public_base(_Req(scope(5053, "localhost"))) == KMAIL
      and ms.public_base(_Req(scope(5051, "works.knknara.co.kr"))) == WORKS)
check("5053 이어도 이름이 works 면 돌아올 곳은 works", ms.public_base(_Req(scope(5053, "works.knknara.co.kr"))) == WORKS)
check("⭐5051 로 온 가짜 Host(evil) → works(가짜 주소를 따라가지 않는다)",
      ms.public_base(_Req(scope(5051, "evil.example.com"))) == WORKS)
check("두 주소가 코드에 박혀 있다(https · 회사 도메인)", ms.MAIL_PUBLIC_BASE == KMAIL and ms.WORKS_PUBLIC_BASE == WORKS)

# ════════════════════════════════════════════════════════════════════════════
print("\n§5 넘김(미들웨어) — 작은 앱에 실제로 끼워서")


async def _echo_app(sc, receive, send):
    if sc["type"] != "http":
        _echo_app.other.append(sc["type"])
        return
    body = json.dumps({"path": sc["path"], "method": sc["method"], "port": (sc.get("server") or [None, None])[1]}).encode()
    await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"application/json")]})
    await send({"type": "http.response.body", "body": body})
_echo_app.other = []


def call(sc):
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(msg):
        sent.append(msg)
    asyncio.run(ms.Guard(_echo_app)(sc, receive, send))
    if not sent:
        return None, {}, b""
    st = sent[0]["status"]
    hd = {k.decode(): v.decode("latin-1") for k, v in sent[0].get("headers", [])}
    return st, hd, b"".join(m.get("body", b"") for m in sent[1:])


st, hd, body = call(scope(5053, "localhost:5053", "/mail/inbox"))
check("5053 · /mail/inbox → 그대로 통과(200)", st == 200 and json.loads(body)["path"] == "/mail/inbox", (st, hd))
st, hd, body = call(scope(5053, "localhost:5053", "/home", raw=b"/home"))
check("⭐5053 · /home → 307 · works 의 같은 경로", st == 307 and hd.get("location") == WORKS + "/home", (st, hd))
st, hd, body = call(scope(5053, "localhost", "/projects/12", qs=b"tab=bom&x=1", raw=b"/projects/12"))
check("물음표 뒤(쿼리)도 그대로 따라간다", st == 307 and hd.get("location") == WORKS + "/projects/12?tab=bom&x=1", hd)
st, hd, body = call(scope(5053, "localhost", "/api/customers/options", method="POST", raw=b"/api/customers/options"))
check("POST 도 307(방식·본문 유지)", st == 307 and hd.get("location") == WORKS + "/api/customers/options", (st, hd))
st, hd, body = call(scope(5053, "localhost", "/검색/가", raw=quote("/검색/가").encode()))
check("한글 경로는 %%-인코딩된 그대로 넘긴다", st == 307 and hd.get("location") == WORKS + quote("/검색/가"), hd)
st, hd, body = call(scope(5053, "localhost", "/검색/가"))            # raw_path 가 없는 서버
check("raw_path 가 없어도 경로를 다시 인코딩해 넘긴다", st == 307 and hd.get("location") == WORKS + quote("/검색/가"), hd)
st, hd, body = call(scope(5053, "localhost", "/a\r\nx: y", raw=None))
check("줄바꿈이 섞인 경로도 헤더를 쪼개지 못한다(인코딩됨)", st == 307 and "\r" not in hd.get("location", "") and "\n" not in hd.get("location", ""), hd)
st, hd, body = call(scope(5053, "localhost", "//evil.example.com/x", raw=b"//evil.example.com/x"))
check("//evil… 같은 경로도 works 주소 뒤에 붙을 뿐(다른 곳으로 안 감)", st == 307 and hd.get("location", "").startswith(WORKS + "//evil"), hd)
for p in ("/", "/mail", "/mail/"):
    st, hd, body = call(scope(5053, "localhost", p, raw=p.encode()))
    check("5053 · 대문 %-7s → 303 · 받은편지함" % p, st == 303 and hd.get("location") == ms.MAIL_HOME, (st, hd))
st, hd, body = call(scope(5053, "localhost", "/", method="POST", raw=b"/"))
check("대문에 POST 는 받은편지함으로 안 보내고 works 로(307)", st == 307 and hd.get("location") == WORKS + "/", (st, hd))
st, hd, body = call(scope(5053, "localhost", "/mail/settings", raw=b"/mail/settings"))
check("5053 · /mail/settings(업무 화면) → works 로", st == 307 and hd.get("location") == WORKS + "/mail/settings", (st, hd))
check("넘길 때 캐시 금지 · 본문 없음", hd.get("cache-control") == "no-store" and hd.get("content-length") == "0" and body == b"")

# ⭐회귀 — 메일 전용 주소가 아니면 아무것도 안 한다
same = True
for p in ("/", "/home", "/mail/inbox", "/mail/settings", "/api/customers/options", "/static/x.css", "/login", "/app", "/검색"):
    for meth in ("GET", "POST"):
        st, hd, body = call(scope(5051, "works.knknara.co.kr", p, method=meth))
        if st != 200 or json.loads(body) != {"path": p, "method": meth, "port": 5051}:
            same = False
check("⭐⭐5051 + works — 경로 9개 × GET/POST 전부 **그대로 통과**(넘김 0)", same)
# ⭐무한 왕복 방지 — 중계 설정이 꼬여 works 요청이 메일 입구(5053)로 들어와도 다시 넘기지 않는다
loop_free = True
for p_ in ("/", "/home", "/projects/1", "/api/customers/options", "/mail/settings"):
    for meth in ("GET", "POST"):
        st, hd, body = call(scope(5053, "works.knknara.co.kr", p_, method=meth, raw=p_.encode()))
        if st != 200 or json.loads(body)["path"] != p_:
            loop_free = False
check("⭐⭐5053 + 이름이 works — 업무 경로 5개 × GET/POST 전부 **그대로 처리**(넘김 0 → 왕복이 생길 수 없다)", loop_free)
# 넘김을 실제로 따라가 본다: kmail 의 /home → (307) works/home → 그 요청이 설령 5053 으로 다시 와도 → 처리되고 끝
st, hd, body = call(scope(5053, "localhost", "/home", raw=b"/home"))
hop = urlsplit(hd.get("location", ""))
st2, hd2, body2 = call(scope(5053, hop.netloc, hop.path or "/", raw=(hop.path or "/").encode()))
check("넘김을 따라가도 한 번에 끝난다(307 → 200 · 두 번째 넘김 없음)", st == 307 and hop.netloc == "works.knknara.co.kr" and st2 == 200, (st, hd, st2, hd2))
_echo_app.other.clear()
asyncio.run(ms.Guard(_echo_app)({"type": "lifespan"}, None, None))
asyncio.run(ms.Guard(_echo_app)({"type": "websocket", "server": ("127.0.0.1", 5053), "headers": [], "path": "/home"}, None, None))
check("http 가 아닌 것(lifespan · websocket)은 5053 이어도 손대지 않는다", _echo_app.other == ["lifespan", "websocket"], _echo_app.other)

# 판정이 깨져도 서비스는 그대로
_orig = ms._redirect_for
ms._redirect_for = lambda sc: (_ for _ in ()).throw(RuntimeError("boom"))
del MSLOG[:]
try:
    st, hd, body = call(scope(5053, "localhost", "/home"))
finally:
    ms._redirect_for = _orig
check("판정 중 오류가 나도 요청은 평소대로 처리(200) + 로그 한 줄(ERROR guard)",
      st == 200 and len(MSLOG) == 1 and MSLOG[0].startswith("[MAIL-SITE] ERROR guard") and "판정 실패" in MSLOG[0], (st, MSLOG))

# ════════════════════════════════════════════════════════════════════════════
print("\n§6 main.py 연결(글자로 확인)")
MAIN = io.open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
TREE = ast.parse(MAIN)
FN = {n.name: ast.get_source_segment(MAIN, n) for n in ast.walk(TREE)
      if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def pos(s):
    return MAIN.find(s)


check("mail_site 를 한 번만 들여온다", MAIN.count("from . import mail_site as _mail_site") == 1)
check("미들웨어 등록 한 번", MAIN.count("app.add_middleware(_mail_site.Guard)") == 1)
check("등록 위치: 압축(GZip) 다음 · https 강제(_force_https) 앞 → 바깥에서 https 강제가 먼저 돈다",
      0 < pos("app.add_middleware(GZipMiddleware") < pos("app.add_middleware(_mail_site.Guard)") < pos("async def _force_https"))
check("⭐입구 훅은 startup()(DB 준비)보다 **아래**에 있다(등록 순서 = 실행 순서)",
      0 < pos("\ndef startup():") < pos("async def _mail_site_listen_start"))
check("입구 훅: 기동 = start(app) · 종료 = stop()", "_mail_site.start(app)" in FN["_mail_site_listen_start"]
      and "await _mail_site.stop()" in FN["_mail_site_listen_stop"])
check("/login — 돌아올 주소를 public_base 로(직접 works 를 붙이지 않는다)",
      "_mail_site.public_base(req)" in FN["login_page"] and "_WORKS_PUBLIC_BASE" not in FN["login_page"])
check("/mail/app — public_base + /mail/ 안쪽만 받는 next", "_mail_site.public_base(req)" in FN["mail_app_launch"]
      and 'nxt.startswith("/mail/")' in FN["mail_app_launch"] and "_WORKS_PUBLIC_BASE" not in FN["mail_app_launch"])
check("/sso/land — 메일 전용 주소에서는 landing() 으로 착지 · 그 밖은 지금 그대로(nxt or /home)",
      "_mail_site.landing(nxt)" in FN["sso_land"] and 'RedirectResponse(nxt or "/home", 303)' in FN["sso_land"])
check("⭐업무 앱 시작(/app)은 그대로 works 고정", '_WORKS_PUBLIC_BASE + "/sso/land?next=" + quote("/home?app=1", safe="")' in FN["works_app_launch"]
      and FN["works_app_launch"].count("_mail_site") == 1 and "_mail_site.silent_sso_url(" in FN["works_app_launch"])
check("큰 첨부 내려받기 주소(/dl)는 그대로 works 로 만든다(받는 사람은 바깥 사람)", 'f"{_WORKS_PUBLIC_BASE}/dl/{token}"' in MAIN)
mo = re.search(r'^_WORKS_PUBLIC_BASE\s*=\s*"([^"]+)"', MAIN, re.M)
check("main 의 works 주소 = mail_site 의 works 주소(두 곳이 같은 값)", bool(mo) and mo.group(1) == ms.WORKS_PUBLIC_BASE, mo and mo.group(1))
check("화면 공통(ctx): 메일 전용 주소면 늘 「메일만」 — 평소에는 지금 값 그대로(or)",
      'base["mail_app"] = _mail_app or _mail_site.is_mail_site(request)' in FN["ctx"])
check("매니페스트: 이미 열린 창을 그 주소로 이동(navigate-existing)", '"client_mode": ["navigate-existing", "auto"]' in FN["mail_manifest"]
      and "focus-existing" not in FN["mail_manifest"].split("launch_handler\"")[-1])
# ⭐훅 등록이 실패해도 WORKS 기동(=main.py 불러오기)이 죽지 않는가 — 그 try 블록만 떼어, 등록이 터지는 가짜 app 으로 돌려 본다
_hook_try = [n for n in TREE.body if isinstance(n, ast.Try) and "_mail_site_listen_start" in (ast.get_source_segment(MAIN, n) or "")]
check("입구 훅 두 개는 맨 바깥 try 하나 안에 있다(등록 실패가 기동을 막지 못하게)", len(_hook_try) == 1
      and "_mail_site_listen_stop" in ast.get_source_segment(MAIN, _hook_try[0]))


class _BadApp:
    def on_event(self, kind):
        raise RuntimeError("이 판에는 on_event 가 없다고 치자")


_cap = []
_ok_exec = True
try:
    exec(compile(ast.Module(body=_hook_try, type_ignores=[]), "<hook-try>", "exec"),
         {"app": _BadApp(), "_mail_site": ms, "print": lambda *a, **k: _cap.append(" ".join(str(x) for x in a))})
except Exception as _e:
    _ok_exec = False
    _cap.append("예외가 밖으로 나옴: %r" % (_e,))
check("⭐훅 등록이 터져도 예외가 밖으로 안 나온다 + 로그 한 줄(ERROR hook · 본체 무영향)",
      _ok_exec and len(_cap) == 1 and _cap[0].startswith("[MAIL-SITE] ERROR hook") and "WORKS 본체 무영향" in _cap[0], _cap)


class _OkApp:
    def __init__(self):
        self.reg = []

    def on_event(self, kind):
        def deco(f):
            self.reg.append((kind, f.__name__))
            return f
        return deco


_okapp = _OkApp()
exec(compile(ast.Module(body=_hook_try, type_ignores=[]), "<hook-try>", "exec"), {"app": _okapp, "_mail_site": ms})
check("정상일 때는 기동·종료 훅이 그 순서로 등록된다",
      _okapp.reg == [("startup", "_mail_site_listen_start"), ("shutdown", "_mail_site_listen_stop")], _okapp.reg)
MS_SRC = io.open(os.path.join(ROOT, "app", "mail_site.py"), encoding="utf-8").read()
check("mail_site.public_base 는 Host 글자로 주소를 조립하지 않는다(상수 둘 중 하나)",
      "return MAIL_PUBLIC_BASE if is_mail_site(req) else WORKS_PUBLIC_BASE" in MS_SRC)
check("입구는 환경변수가 있을 때만(기본 끔) · 실패해도 예외를 안 올린다",
      'os.environ.get("KNK_MAIL_SITE_PORT")' in MS_SRC and "if not LISTEN_PORT:\n            return False" in MS_SRC)

# ════════════════════════════════════════════════════════════════════════════
print("\n§7 실제 앱(app.main)으로 — 두 주소에서 각각")
_so = sys.stdout
sys.stdout = io.StringIO()
try:
    import app.database as _db              # noqa: E402
    _TMPD = tempfile.mkdtemp(prefix="knk_ms_test_")
    _db.DB_PATH = os.path.join(_TMPD, "empty.db")      # 작업 폴더에 DB 를 만들지 않게(빈 임시 DB)
    import app.main as m                    # noqa: E402
    import app.sso_client as _sso           # noqa: E402
finally:
    sys.stdout = _so
from starlette.testclient import TestClient  # noqa: E402

check("미들웨어 순서(바깥→안): https 강제 → 메일 전용 넘김 → 압축 → 세션",
      [getattr(x.cls, "__name__", "") for x in m.app.user_middleware] == ["BaseHTTPMiddleware", "Guard", "GZipMiddleware", "SessionMiddleware"],
      [getattr(x.cls, "__name__", "") for x in m.app.user_middleware])
# 11-20 고침: 다른 기능의 기동 훅이 뒤에 더해져도(세션 01 z83 `_z83_start_tick` 등) 「DB 먼저 → 메일 입구」 순서만 확인
_hooks = [f.__name__ for f in m.app.router.on_startup]
check("기동 훅 순서: startup(DB) → 입구", _hooks[:1] == ["startup"] and "_mail_site_listen_start" in _hooks
      and _hooks.index("_mail_site_listen_start") > _hooks.index("startup"), _hooks)
check("main 이 쓰는 mail_site 가 이 시험이 보는 것과 같은 모듈", m._mail_site is ms)


def client(port, host):
    c = TestClient(m.app, base_url="http://127.0.0.1:%d" % port, raise_server_exceptions=False, follow_redirects=False)
    c.headers.update({"host": host, "x-forwarded-proto": "https"})
    return c


def sso_target(loc):
    """이음 로그인으로 보내는 주소에서 「돌아올 곳」과 그 안의 next 를 꺼낸다."""
    if not loc.startswith(MSG_LOGIN):
        return None, None
    ru = parse_qs(urlsplit(loc).query).get("redirect_uri", [""])[0]
    nx = parse_qs(urlsplit(ru).query).get("next", [""])[0]
    return ru.split("?", 1)[0], nx


import html as _html  # noqa: E402


def launch_target(body):
    """「여는 중」 화면에서 넘어갈 이음 주소를 꺼낸다 → (돌아올 곳, next, 조용히 표시가 있는가, 주소)."""
    t = body.decode("utf-8", "replace") if isinstance(body, (bytes, bytearray)) else str(body)
    mo = re.search(r'id="go" href="([^"]+)"', t)
    if not mo:
        return None, None, False, ""
    url = _html.unescape(mo.group(1))
    base, nx = sso_target(url)
    return base, nx, parse_qs(urlsplit(url).query).get("prompt", [""])[0] == "none", url


K = client(5053, "localhost:5053")          # 메일 전용 입구로 · Host 는 일부러 localhost(중계기가 바꿔 보낸 최악의 경우)
W = client(5051, "works.knknara.co.kr")     # 지금 운영(works)

r = K.get("/mail/app")
lt = launch_target(r.content)
check("⭐kmail /mail/app → 「여는 중」 화면(200 · html · 캐시 금지) · 넘어갈 곳 = 이음 로그인 · 돌아올 곳 kmail/sso/land · 착지 받은편지함 · 조용히(prompt=none)",
      r.status_code == 200 and "text/html" in r.headers.get("content-type", "") and r.headers.get("cache-control") == "no-store"
      and lt[:3] == (KMAIL + "/sso/land", "/mail/inbox?app=1", True) and lt[3].startswith(MSG_LOGIN), lt)
r = K.get("/mail/app?next=%2Fmail%2Fcompose")
lt = launch_target(r.content)
check("⭐kmail /mail/app?next=/mail/compose → 돌아올 곳 kmail · 착지 = 메일 쓰기(세션 10 이 쓸 주소)",
      r.status_code == 200 and lt[:3] == (KMAIL + "/sso/land", "/mail/compose", True), lt)
for bad in ("%2Fhome", "https%3A%2F%2Fevil.example.com", "%2F%2Fevil.example.com", "%2Fmailx", "mail%2Fcompose", "%2Fadmin%2Fusers"):
    r = K.get("/mail/app?next=" + bad)
    lt = launch_target(r.content)
    check("kmail /mail/app?next=%-34s → 받은편지함으로 좁힘" % unquote(bad),
          r.status_code == 200 and lt[:2] == (KMAIL + "/sso/land", "/mail/inbox?app=1"), lt)
r = K.get("/login")
check("kmail /login → 돌아올 곳 kmail · 착지 = 받은편지함(/home 아님) · 조용히(prompt=none)",
      r.status_code == 303 and sso_target(r.headers["location"]) == (KMAIL + "/sso/land", "/mail/inbox?app=1")
      and parse_qs(urlsplit(r.headers["location"]).query).get("prompt") == ["none"], r.headers.get("location"))
r = K.get("/login?next=%2Fmail%2Fcompose%3Freply%3D5")
check("kmail /login?next=/mail/compose?reply=5 → 그 화면으로", sso_target(r.headers["location"]) == (KMAIL + "/sso/land", "/mail/compose?reply=5"),
      r.headers.get("location"))
r = K.get("/login?next=%2Fhome")
check("kmail /login?next=/home → 받은편지함으로 좁힘", sso_target(r.headers["location"]) == (KMAIL + "/sso/land", "/mail/inbox?app=1"),
      r.headers.get("location"))
r = K.get("/mail/inbox")
check("kmail /mail/inbox(로그인 전) → /login(같은 주소 안에서)", r.status_code == 303 and r.headers["location"] == "/login", (r.status_code, r.headers.get("location")))
r = K.get("/home")
check("kmail /home → 307 works/home(업무 화면은 works 로)", r.status_code == 307 and r.headers["location"] == WORKS + "/home", (r.status_code, r.headers.get("location")))
r = K.get("/")
check("kmail / → 303 받은편지함", r.status_code == 303 and r.headers["location"] == ms.MAIL_HOME, (r.status_code, r.headers.get("location")))
r = K.get("/app")
check("kmail /app(업무 앱 시작) → works 로 넘김", r.status_code == 307 and r.headers["location"] == WORKS + "/app", (r.status_code, r.headers.get("location")))
r = K.get("/manifest.webmanifest")
check("kmail 에서는 업무 앱 매니페스트를 주지 않는다(works 로)", r.status_code == 307 and r.headers["location"] == WORKS + "/manifest.webmanifest")
r = K.get("/api/version")
check("kmail /api/version → 200 {\"v\":…}(배포 확인용)", r.status_code == 200 and list(r.json().keys()) == ["v"], (r.status_code, r.text[:60]))
r = K.get("/mail/manifest.webmanifest")
mf = r.json()
check("kmail 메일 매니페스트: 이름 KNK Eum MAIL · 시작 /mail/app · 범위 = 주소 전체(/) · navigate-existing",
      r.status_code == 200 and mf["name"] == "KNK Eum MAIL" and mf["start_url"] == "/mail/app" and mf["scope"] == "/"
      and mf["id"] == "/mail/app" and mf["launch_handler"]["client_mode"][0] == "navigate-existing", mf)
r = W.get("/mail/manifest.webmanifest")
mfw = r.json()
check("works 메일 매니페스트: 범위는 지금 그대로 /mail/", r.status_code == 200 and mfw["scope"] == "/mail/" and mfw["start_url"] == "/mail/app", mfw)
r = K.get("/mail/sw.js")
check("kmail /mail/sw.js → 200 자바스크립트", r.status_code == 200 and "javascript" in r.headers.get("content-type", ""))

# works 쪽(지금 운영)
r = W.get("/mail/app")
lt = launch_target(r.content)
check("works /mail/app → 「여는 중」 화면 · 돌아올 곳 works · 받은편지함",
      r.status_code == 200 and lt[:3] == (WORKS + "/sso/land", "/mail/inbox?app=1", True), lt)
r = W.get("/login")
check("works /login → 돌아올 곳 works · /home · 조용히(prompt=none — 이음 로그아웃이면 이음웍스 안내)",
      r.status_code == 303 and sso_target(r.headers["location"]) == (WORKS + "/sso/land", "/home")
      and parse_qs(urlsplit(r.headers["location"]).query).get("prompt") == ["none"], r.headers.get("location"))
r = W.get("/app")
check("works /app(이음웍스 아이콘) → 돌아올 곳 works · /home?app=1 · 조용히(prompt=none)",
      r.status_code == 303 and sso_target(r.headers["location"]) == (WORKS + "/sso/land", "/home?app=1")
      and parse_qs(urlsplit(r.headers["location"]).query).get("prompt") == ["none"], r.headers.get("location"))
r = W.get("/home")
check("works /home(로그인 전) → /login(넘김 없음)", r.status_code == 303 and r.headers["location"] == "/login", (r.status_code, r.headers.get("location")))
r = client(5051, "evil.example.com").get("/login")
check("⭐works 포트로 가짜 Host 를 보내도 돌아올 곳은 works(가짜 주소로 토큰이 안 간다)",
      sso_target(r.headers["location"])[0] == WORKS + "/sso/land", r.headers.get("location"))
r = client(5051, "kmail.knknara.co.kr").get("/home")
check("5051 로 와도 이름이 kmail 이면 메일 전용(이름 판정)", r.status_code == 307 and r.headers["location"] == WORKS + "/home")
r = client(5053, "works.knknara.co.kr").get("/home")
check("⭐실제 앱: 메일 입구(5053)로 works 요청이 와도 넘기지 않고 평소대로(/login) — 무한 왕복 없음",
      r.status_code == 303 and r.headers["location"] == "/login", (r.status_code, r.headers.get("location")))
r = client(5053, "works.knknara.co.kr").get("/login")
check("그때 로그인 돌아올 곳도 works", sso_target(r.headers["location"]) == (WORKS + "/sso/land", "/home"), r.headers.get("location"))
r = client(5053, "kmail.knknara.co.kr").get("/home", headers={"x-forwarded-proto": "http"})
check("kmail 에 http 로 오면 → https://kmail 로(기존 https 강제 · 주소 유지)",
      r.status_code == 301 and r.headers["location"].startswith(KMAIL + "/home"), (r.status_code, r.headers.get("location")))

# 로그인 왕복의 끝(/sso/land) — 토큰 검증·계정 저장은 가짜로 바꿔(운영 무접촉) 착지만 본다
_keep = (_sso.verify_token, m._sso_land_upsert, m.get_user)
_sso.verify_token = lambda t: {"sub": "T1", "works_access": True, "pwv": 1} if t == "FAKE-TOKEN" else None
m._sso_land_upsert = lambda payload, tries=3: (1, "ok")
m.get_user = lambda req: ({"id": 1, "role": "member", "name": "시험"} if req.session.get("user_id") else None)
try:
    for nx, want in [("%2Fmail%2Fcompose", "/mail/compose"), ("%2Fmail%2Finbox%3Fapp%3D1", "/mail/inbox?app=1"),
                     ("%2Fhome", ms.MAIL_HOME), ("", ms.MAIL_HOME), ("%2Fmail%2Fsettings", ms.MAIL_HOME),
                     ("https%3A%2F%2Fevil.example.com", ms.MAIL_HOME)]:
        k = client(5053, "localhost:5053")
        r = k.get("/sso/land?token=FAKE-TOKEN" + ("&next=" + nx if nx else ""))
        check("kmail 로그인 끝 next=%-28r → %s" % (unquote(nx), want), r.status_code == 303 and r.headers["location"] == want,
              (r.status_code, r.headers.get("location")))
    r2 = k.get("/login")
    check("kmail 에서 이미 로그인된 채 /login → 받은편지함(업무 홈 아님)", r2.status_code == 303 and r2.headers["location"] == ms.MAIL_HOME,
          (r2.status_code, r2.headers.get("location")))
    check("로그인 쿠키는 그 주소 전용(도메인을 넓히지 않는다 → works 와 kmail 의 로그인이 섞이지 않음)",
          "domain=" not in (r.headers.get("set-cookie") or "").lower() and "session=" in (r.headers.get("set-cookie") or ""),
          (r.headers.get("set-cookie") or "")[:40])
    for nx, want in [("%2Fmail%2Fcompose", "/mail/compose"), ("%2Fhome", "/home"), ("", "/home"),
                     ("%2Fmail%2Fsettings", "/mail/settings"), ("https%3A%2F%2Fevil.example.com", "/home")]:
        w = client(5051, "works.knknara.co.kr")
        r = w.get("/sso/land?token=FAKE-TOKEN" + ("&next=" + nx if nx else ""))
        check("works 로그인 끝 next=%-28r → %s (지금 그대로)" % (unquote(nx), want), r.status_code == 303 and r.headers["location"] == want,
              (r.status_code, r.headers.get("location")))
    r2 = w.get("/login")
    check("works 에서 이미 로그인된 채 /login → 역할별 홈(지금 그대로)", r2.status_code == 303 and r2.headers["location"] == "/home",
          (r2.status_code, r2.headers.get("location")))
    r = client(5053, "localhost").get("/sso/land?token=WRONG&next=%2Fmail%2Fcompose")
    check("틀린 토큰은 kmail 에서도 입장 못 함(넘어가지 않는다)", r.status_code != 303, r.status_code)
finally:
    _sso.verify_token, m._sso_land_upsert, m.get_user = _keep

# ════════════════════════════════════════════════════════════════════════════
print("\n§7b 메일 앱을 열 때의 화면 두 장 — 「여는 중」 · 「이음에 로그인해 주세요」")
U = MSG_LOGIN + "https%3A%2F%2Fkmail.knknara.co.kr%2Fsso%2Fland%3Fnext%3D%252Fmail%252Fcompose"
check("조용히 표시 붙이기: 물음표가 있으면 &prompt=none · 없으면 ?prompt=none",
      ms.silent_sso_url(U) == U + "&prompt=none" and ms.silent_sso_url("https://m.example/sso/login") == "https://m.example/sso/login?prompt=none")
pg = ms.launch_page(ms.silent_sso_url(U))
check("「여는 중」 화면: 받은편지함과 같은 머리띠 글 · 「메일을 여는 중」 · 한 장짜리(틀 문법 없음)",
      "📧 HAIST WORKS 메일함" in pg and "메일을 여는 중" in pg and "{%" not in pg and "{{" not in pg and pg.startswith("<!doctype html>"))
check("머리띠 색 = 받은편지함 머리띠(#A5282C) → 화면이 바뀔 때 이어져 보인다", ".top{background:#A5282C" in pg)
check("머리띠 높이·글자 자리·바탕색 = 받은편지함 실측값(높이 48px = 9+30+9 · 왼쪽 16px · 폰 47.4px · 바탕 #f3f5f2)",
      "padding:9px 16px;font-weight:800;font-size:15px;line-height:30px" in pg
      and "@media(max-width:640px){.top{padding:8px 10px;font-size:14px;line-height:31.4px}}" in pg
      and "body{background:#f3f5f2" in pg and "min-height:calc(100% - 48px)" in pg)
_head_css = io.open(os.path.join(ROOT, "app", "templates", "_v5_partials", "mail_app_head.html"), encoding="utf-8").read()
check("받은편지함 머리띠가 그 실측의 바탕 그대로다(안쪽 여백 9px 16px · 글자 15px/800 · 폰 8px 10px/14px — 바뀌면 「여는 중」 화면도 맞출 것)",
      "background:var(--knk-red,#b91c1c); color:#fff; padding:9px 16px;" in _head_css
      and ".mail-app-top .brand { font-weight:800; font-size:15px;" in _head_css
      and ".mail-app-top{flex-wrap:nowrap;overflow-x:auto;-webkit-overflow-scrolling:touch;gap:4px;padding:8px 10px}" in _head_css
      and ".mail-app-top .brand{font-size:14px;" in _head_css)


from html.parser import HTMLParser  # noqa: E402


def link_attrs(page):
    """화면을 브라우저처럼 읽어, 링크(<a>)마다 속성 목록을 돌려준다(값은 풀어서)."""
    found = []

    class _P(HTMLParser):
        def handle_starttag(self, t, attrs):
            if t == "a":
                found.append(attrs)
    _P(convert_charrefs=True).feed(page)
    return found


evil_q = 'https://msg.knknara.co.kr/sso/login?redirect_uri=x" onmouseover="alert(3)" data-x=\'y\'&prompt=none'
la = link_attrs(ms.launch_page(evil_q))
check("⭐주소에 따옴표가 섞여도 링크 속성을 끼워 넣지 못한다(링크 1개 · 속성은 class·id·href 셋뿐 · href 는 그 주소 그대로)",
      len(la) == 1 and [k for k, _ in la[0]] == ["class", "id", "href"] and dict(la[0])["href"] == evil_q, la)
evil_b = 'https://msg.example/" onclick="alert(4)'
la = link_attrs(ms.need_login_page(evil_b, "/mail/compose", ""))
check("안내 화면도 같다(이음 주소 자리에 따옴표가 와도 링크 2개의 속성이 그대로 — 끼어든 속성 없음)",
      len(la) == 2 and [k for k, _ in la[0]] == ["class", "href", "target", "rel"] and dict(la[0])["href"] == evil_b + "/"
      and [k for k, _ in la[1]] == ["class", "id", "href"] and dict(la[1])["href"] == "/mail/app?next=%2Fmail%2Fcompose", la)
check("넘어갈 주소가 링크·스크립트 양쪽에 들어 있다", launch_target(pg)[3] == ms.silent_sso_url(U) and "location.replace(u)" in pg)
check("⭐한 번 그린 다음에 넘어간다(requestAnimationFrame) · 안 불려도 0.3초 뒤엔 넘어간다 · 두 번 넘어가지 않는다",
      "requestAnimationFrame(function(){setTimeout(go,0);})" in pg and "setTimeout(go,300)" in pg and "if(done)return;done=1" in pg)
check("스크립트가 꺼져 있어도 넘어간다(noscript 새로고침)", '<noscript><meta http-equiv="refresh" content="0;url=' in pg)
check("시작 시각을 남긴다(받은편지함이 걸린 시간을 재도록)", "sessionStorage.setItem('knkMailT0'" in pg)
check("바깥 파일을 부르지 않는다(스타일·스크립트가 화면 안에 — 바로 그려진다)", "<link rel=\"stylesheet\"" not in pg and "src=" not in pg)
evil = 'https://msg.knknara.co.kr/sso/login?redirect_uri=x"><script>alert(1)</script>&a=\'</script><img src=x onerror=alert(2)>'
pe = ms.launch_page(evil)
check("⭐주소에 태그·따옴표가 섞여도 화면을 깨지 못한다(스크립트 1개 그대로 · 끼어든 태그 0)",
      pe.count("<script>") == 1 and pe.count("</script>") == 1 and "<script>alert(1)" not in pe and "<img" not in pe and "onerror=alert(2)>" not in pe, pe[-500:])
nl_page = ms.need_login_page("https://msg.knknara.co.kr", "/mail/compose", "login_required")
check("안내 화면: 「이음 메신저에 로그인해 주세요」 · 머리띠 · 한 장짜리", "이음 메신저에 로그인해 주세요" in nl_page and "📧 HAIST WORKS 메일함" in nl_page and "{%" not in nl_page)
check("⭐안내 화면은 로그인 화면이 아니다(입력 칸·비밀번호 칸·폼 없음)", "<form" not in nl_page and "<input" not in nl_page and "password" not in nl_page.lower())
check("안내 글은 흰 카드 하나에 담긴다(여닫는 태그 수가 맞는다)",
      nl_page.count('<div class="card">') == 1 and nl_page.count("<div") == nl_page.count("</div>") == 5, (nl_page.count("<div"), nl_page.count("</div>")))
check("「여는 중」 화면도 여닫는 태그 수가 맞는다", pg.count("<div") == pg.count("</div>") == 4, (pg.count("<div"), pg.count("</div>")))
check("시작 값은 「그때 시각,첫 화면이 뜨기까지 ms」 두 숫자(받은편지함이 네 토막으로 나눠 보여 준다)",
      "sessionStorage.setItem('knkMailT0',Date.now()+','+Math.round(performance.now()))" in pg)
check("단추 둘: 「이음 메신저 열기」(새 창 · 이음 주소) · 「다시 열기」(메일 쓰기로 가려던 길 유지)",
      '<a class="b b1" href="https://msg.knknara.co.kr/" target="_blank" rel="noopener">이음 메신저 열기</a>' in nl_page
      and '<a class="b b2" id="retry" href="/mail/app?next=%2Fmail%2Fcompose">다시 열기</a>' in nl_page, nl_page[-900:])
for nx_ in ("", ms.MAIL_HOME, "/home", "/admin/mail-send", "/mail/settings", "https://evil.example.com"):
    check("다시 열기 주소: next=%-26r → /mail/app (받은편지함)" % nx_, 'id="retry" href="/mail/app"' in ms.need_login_page("https://msg.knknara.co.kr", nx_, "login_required"))
check("이음에 다녀와 이 창으로 돌아오면 다시 연다 · 4초 안에 거듭 열지 않는다(왕복 방지)",
      "window.addEventListener('focus'" in nl_page and "if(n-last<4000)return" in nl_page and "visibilitychange" in nl_page)
check("직원 계정이 아닐 때(access_denied)는 다른 안내", "이 계정으로는 메일을 열 수 없습니다" in ms.need_login_page("https://msg.knknara.co.kr", "", "access_denied"))
ne = ms.need_login_page("https://msg.knknara.co.kr", '/mail/"><script>alert(1)</script>', "login_required")
check("⭐next 에 태그가 섞여도 안내 화면을 깨지 못한다", ne.count("<script>") == 1 and "<script>alert(1)" not in ne and '"><script>' not in ne, ne[-600:])

r = K.get("/sso/land?error=login_required&next=%2Fmail%2Fcompose")
check("⭐kmail /sso/land?error=login_required → 안내 화면(200 · 넘김 없음 · 캐시 금지) · 다시 열기 = 메일 쓰기",
      r.status_code == 200 and "location" not in r.headers and r.headers.get("cache-control") == "no-store"
      and "이음 메신저에 로그인해 주세요" in r.text and 'href="/mail/app?next=%2Fmail%2Fcompose"' in r.text, (r.status_code, r.text[:200]))
r = K.get("/sso/land?error=login_required")
check("kmail · next 없이 → 안내 화면 · 다시 열기 = 받은편지함", r.status_code == 200 and 'id="retry" href="/mail/app"' in r.text)
check("안내 화면의 「이음 메신저 열기」 = 이음 주소(업무·메일 주소가 아님)",
      '<a class="b b1" href="https://msg.knknara.co.kr/" target="_blank" rel="noopener">이음 메신저 열기</a>' in r.text
      and _sso.MESSENGER_BASE.rstrip("/") == "https://msg.knknara.co.kr", _sso.MESSENGER_BASE)
for bad in ("%2Fmail%2Fcompose%5Cevil", "%2Fmail%2Fcompose%0d%0aX", "%2Fmail%2Fcompose%20x"):
    r = K.get("/sso/land?error=login_required&next=" + bad)
    check("kmail · next 에 역슬래시·줄바꿈·빈칸(%s) → 안내는 뜨되 다시 열기는 받은편지함(그 next 를 버린다)" % bad,
          r.status_code == 200 and 'id="retry" href="/mail/app"' in r.text, r.text[-700:-400])
r = W.get("/sso/land?error=login_required&next=%2Fmail%2Finbox%3Fapp%3D1")
check("works 주소라도 메일로 가려던 길(next=/mail/…)이면 같은 안내", r.status_code == 200 and "이음 메신저에 로그인해 주세요" in r.text)
r = W.get("/sso/land?error=login_required&next=%2Fhome")
check("⭐works · 업무 화면으로 가려던 길이면 이음웍스 안내(메일 머리띠·메일 앱 표시 없음 · 다시 열기 = /login)",
      r.status_code == 200 and "이음 메신저에 로그인해 주세요" in r.text and "이음웍스는 이음 메신저에 로그인한 상태에서 열립니다" in r.text
      and "메일함" not in r.text and "manifest" not in r.text and 'id="retry" href="/login"' in r.text
      and r.headers.get("cache-control") == "no-store", r.text[:300])
r = W.get("/sso/land?error=login_required&next=%2Fprojects%3Fq%3D1")
check("이음웍스 안내 · 가려던 업무 화면을 다시 열기에 유지(/login?next=…)", 'id="retry" href="/login?next=%2Fprojects%3Fq%3D1"' in r.text, r.text[-800:-400])
for nx_, want in (("%2Fhome%3Fapp%3D1", "/login"), ("https%3A%2F%2Fevil.example.com", "/login"), ("%2F%2Fevil.example.com", "/login")):
    r = W.get("/sso/land?error=login_required&next=" + nx_)
    check("이음웍스 안내 · next=%-30s → 다시 열기 %s" % (unquote(nx_), want), 'id="retry" href="%s"' % want in r.text, r.text[-800:-400])
r = W.get("/sso/land?error=access_denied&next=%2Fhome")
check("이음웍스 · 손님 계정(access_denied) → 「이 계정으로는 이음웍스을 열 수 없습니다」가 아니라 바른 글", "이 계정으로는 이음웍스를 열 수 없습니다" in r.text, r.text[:400])
r = W.get("/sso/land?next=%2Fmail%2Fcompose")
check("error 표시가 없으면(토큰만 없음) 메일 안내가 아니라 지금 동작 그대로", "이음 메신저에 로그인해 주세요" not in r.text, r.text[:200])
_keep2 = (_sso.verify_token, m._sso_land_upsert)
_sso.verify_token = lambda t: {"sub": "T1", "works_access": True, "pwv": 1} if t == "FAKE-TOKEN" else None
m._sso_land_upsert = lambda payload, tries=3: (1, "ok")
try:
    r = client(5053, "localhost").get("/sso/land?token=FAKE-TOKEN&error=login_required&next=%2Fmail%2Fcompose")
    check("토큰이 있으면 error 표시가 붙어 있어도 평소대로 입장(안내로 가로막지 않는다)", r.status_code == 303 and r.headers["location"] == "/mail/compose",
          (r.status_code, r.headers.get("location")))
finally:
    _sso.verify_token, m._sso_land_upsert = _keep2

from jinja2 import Environment, FileSystemLoader  # noqa: E402
_env = Environment(loader=FileSystemLoader(os.path.join(ROOT, "app", "templates")))
_head = _env.get_template("_v5_partials/mail_app_head.html")
h_admin, h_staff = _head.render(is_admin=True, user=None), _head.render(is_admin=False, user=None)
check("걸린 시간 표시는 관리자 화면에만(🔄 단추 설명글) · 직원 화면에는 스크립트 자체가 없다",
      "knkMailT0" in h_admin and "knkMailT0" not in h_staff and "mailReloadBtn" in h_admin, (len(h_admin), len(h_staff)))
check("걸린 시간은 네 토막(첫 화면 · 이음 로그인 · 메일 서버 · 받아서 그리기) · 이음 로그인 화면을 거쳐 온 경우는 여는 시간으로 치지 않는다(1.5초 문턱)",
      all(w in h_admin for w in ("첫 화면 ", "이음 로그인 ", "메일 서버 ", "받아서 그리기 ", "gap < 1500", "window.knkMailLaunchTiming")))
check("main.py: /mail/app 은 launch_page · /login·/app 은 조용히 · /sso/land 안내는 메일 길/업무 길로 나뉜다",
      "_mail_site.launch_page(_sso_url)" in FN["mail_app_launch"] and "RedirectResponse" not in FN["mail_app_launch"]
      and "_mail_site.silent_sso_url(sso_client.build_login_url(redirect_uri))" in FN["login_page"]
      and '_site = "mail" if (_mail_site.is_mail_site(req) or _nx_land.startswith("/mail/")) else "works"' in FN["sso_land"])
check("업무 앱 시작(/app)은 바로 넘김(여는 중 화면 없음 · 조용히 표시만)", "launch_page" not in FN["works_app_launch"] and "RedirectResponse(" in FN["works_app_launch"])

# ════════════════════════════════════════════════════════════════════════════
print("\n§8 회귀 — works 로 들어오는 응답이 운영본(origin/main)과 같은가")
OLD = os.path.join(_TMPD, "old_tree")
os.makedirs(OLD)
_dump_ok = False
try:
    if QUICK:
        raise RuntimeError("--quick")
    ar = subprocess.run(["git", "archive", "--format=tar", "origin/main", "app"], cwd=ROOT, capture_output=True, timeout=120)
    if ar.returncode != 0:
        raise RuntimeError("git archive 실패: " + ar.stderr.decode("utf-8", "replace")[:200])
    import tarfile  # noqa: E402
    with tarfile.open(fileobj=io.BytesIO(ar.stdout)) as tf:
        tf.extractall(OLD, filter="data")
    for d in ("static", "data"):
        os.makedirs(os.path.join(OLD, d), exist_ok=True)
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    env.pop("KNK_MAIL_SITE_PORT", None)

    def dump(root):
        p = subprocess.run([sys.executable, os.path.abspath(__file__), "--dump", root], capture_output=True, timeout=300, env=env)
        if p.returncode != 0:
            raise RuntimeError("dump 실패(%s): %s" % (root, p.stderr.decode("utf-8", "replace")[-400:]))
        return json.loads(p.stdout.decode("utf-8"))
    old = dump(OLD)
    new = dump(ROOT)
    _dump_ok = True
except Exception as e:
    if QUICK:
        print("  (--quick: 운영본 대조 건너뜀)")
    else:
        check("운영본을 꺼내 같은 요청을 보내 보았다", False, str(e)[:400])

if _dump_ok:
    _old_ms = os.path.join(OLD, "app", "mail_site.py")
    _old_has = os.path.exists(_old_ms) and "def launch_page" in io.open(_old_ms, encoding="utf-8").read()
    print("  (견주는 운영본에 「여는 중」 화면이 %s)" % ("이미 있다 → 차이가 없어야 한다" if _old_has else "아직 없다 → 시작 주소 3가지만 달라야 한다"))
    check("요청 %d개를 양쪽에 똑같이 보냈다" % len(DUMP_REQS), len(old) == len(new) == len(DUMP_REQS))
    diffs = []
    for a, b in zip(old, new):
        ja, jb = a.pop("json", None), b.pop("json", None)
        if a["req"] == "GET /api/version":
            a["len"] = b["len"] = 0                              # 버전 글자는 폴더마다 다르다(키만 견준다)
            ja, jb = sorted((ja or {}).keys()), sorted((jb or {}).keys())
        if a != b or ja != jb:
            diffs.append((a["req"], a, b, ja, jb))
    names = sorted(d[0] for d in diffs)
    WANT_SILENT = [] if _old_has else ["GET /app", "GET /login", "GET /login?next=%2F%2Fevil.example.com",
                                       "GET /login?next=%2Fmail%2Finbox", "GET /login?next=https%3A%2F%2Fevil.example.com"]
    WANT = [] if _old_has else ["GET /mail/app", "GET /mail/app?next=%2Fhome", "GET /mail/app?next=%2Fmail%2Fcompose"]
    check("⭐⭐다른 응답은 **의도한 곳뿐** — 메일 앱 시작 %d가지 + 이음 로그인으로 보내는 곳 %d가지 · 나머지 %d개는 상태·이동 주소·종류·길이까지 같다"
          % (len(WANT), len(WANT_SILENT), len(DUMP_REQS) - len(WANT) - len(WANT_SILENT)), names == sorted(WANT + WANT_SILENT), names)
    by = {d[0]: d for d in diffs}
    if WANT_SILENT:
        oks = all(k in by and by[k][1]["status"] == by[k][2]["status"] == 303
                  and by[k][2]["location"] == by[k][1]["location"] + "&prompt=none"
                  and by[k][1]["location"].startswith(MSG_LOGIN) for k in WANT_SILENT)
        check("그 %d곳: 이동 주소 끝에 &prompt=none 하나만 붙었다(나머지 글자·상태 같음)" % len(WANT_SILENT), oks,
              [(k, k in by and (by[k][1]["location"][-60:], by[k][2]["location"][-60:])) for k in WANT_SILENT])
    if WANT:
        okk = all(k in by and by[k][1]["status"] == 303 and by[k][1]["location"].startswith(MSG_LOGIN)
                  and by[k][2]["status"] == 200 and by[k][2]["ctype"] == "text/html" and by[k][2]["location"] == "" for k in WANT)
        check("그 3곳: 앞 판 = 이음 로그인으로 바로 넘김(303) → 새 판 = 「여는 중」 화면(200 · html)", okk,
              [(k, k in by and (by[k][1]["status"], by[k][2]["status"], by[k][2]["ctype"])) for k in WANT])
    st = {a["req"]: a["status"] for a in new}
    check("견준 요청들이 실제로 의미 있는 응답이었다(303 이동 · 200 · 401/403 · 404 가 섞여 있음 — 전부 500 이 아님)",
          st["GET /login"] == 303 and st["GET /api/version"] == 200 and st["GET /mail/manifest.webmanifest"] == 200
          and st["GET /home"] == 303 and all(v != 500 for v in st.values()), st)

# ════════════════════════════════════════════════════════════════════════════
print("\n§9 실제 소켓 — WORKS 가 두 포트를 함께 듣는다")
import uvicorn  # noqa: E402

A, B = free_port(), free_port()
while B == A:
    B = free_port()
ms.LISTEN_PORT = 0
del MSLOG[:]
_r0 = ms.start(m.app)
check("입구 끔(포트 0)이면 start() 는 아무것도 안 한다(작업 없음 · 로그 없음)", _r0 is False and ms._L["task"] is None and not MSLOG, MSLOG)
ms.LISTEN_PORT = B
_r = ms.start(m.app)                           # 돌고 있는 이벤트 루프가 없는 곳에서 부름 → 안에서 오류
check("start() 가 실패해도 예외를 올리지 않는다(False + 로그 「본체 무영향」)",
      _r is False and len(MSLOG) == 1 and MSLOG[0].startswith("[MAIL-SITE] ERROR start") and "입구 시작 실패(WORKS 본체 무영향)" in MSLOG[0]
      and ms._L["task"] is None, MSLOG)

# 옛 메일 앱 흉내 — B 포트를 먼저 잡고 있는 다른 프로그램
squat = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
squat.bind(("127.0.0.1", B))
squat.listen(5)

ms.LISTEN_PORT, ms._BIND_HOST, ms._RETRY_SEC = B, "127.0.0.1", 1.0
box = {}
del MSLOG[:]


async def _runner():
    srv = uvicorn.Server(uvicorn.Config(m.app, host="127.0.0.1", port=A, lifespan="off", log_config=None,
                                        proxy_headers=True, forwarded_allow_ips="*"))
    box["srv"] = srv
    box["started"] = ms.start(m.app)           # = 기동 훅이 하는 일
    await srv.serve()
    await ms.stop()                            # = 종료 훅이 하는 일
    box["stopped"] = True


def _thread():
    try:
        asyncio.run(_runner())
    except BaseException as e:                 # noqa: BLE001
        box["err"] = repr(e)


th = threading.Thread(target=_thread, daemon=True)
th.start()


def hget(port, path, host, method="GET", extra=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=8)
    try:
        hd = {"Host": host}
        hd.update(extra or {})
        c.request(method, path, headers=hd)
        r = c.getresponse()
        return r.status, dict((k.lower(), v) for k, v in r.getheaders()), r.read()
    finally:
        c.close()


def wait(cond, sec):
    end = time.time() + sec
    while time.time() < end:
        try:
            if cond():
                return True
        except Exception:
            pass
        time.sleep(0.1)
    return False


try:
    up = wait(lambda: hget(A, "/api/version", "works.knknara.co.kr")[0] == 200, 20)
    check("본체(포트 A)가 떴다", up and box.get("started") is True, box)
    check("⭐포트 B 를 다른 프로그램이 쓰는 동안 — 입구는 못 열지만 **본체는 정상**(200)",
          (not ms.listening()) and hget(A, "/api/version", "works.knknara.co.kr")[0] == 200)
    time.sleep(2.5)                            # 다시 보기(1초 간격)가 두세 번 지나가게
    busy = [x for x in MSLOG if "다른 프로그램이 쓰고 있다" in x]
    check("막혀 있다는 로그는 한 줄만(다시 볼 때마다 쌓지 않는다) · 「WORKS 본체 무영향」이라고 적는다",
          len(busy) == 1 and "WORKS 본체 무영향" in busy[0] and (not ms.listening())
          and busy[0].startswith("[MAIL-SITE] WAIT pid=%d port=%d " % (os.getpid(), B)), MSLOG)
    squat.close()                              # ── 옛 앱이 멈춤(포트가 풀림)
    took = wait(ms.listening, 8)
    took = took and wait(lambda: hget(B, "/api/version", "localhost:%d" % B)[0] == 200, 8)
    check("⭐⭐포트가 풀리자 **재시작 없이 저절로** 입구를 잡았다(로그 LISTEN)",
          took and any(x.startswith("[MAIL-SITE] LISTEN pid=%d 127.0.0.1:%d " % (os.getpid(), B)) and "듣기 시작" in x for x in MSLOG), MSLOG)

    s, h, b = hget(B, "/api/version", "localhost:%d" % B)
    check("입구(B) /api/version → 200 {\"v\":…} — Host 가 localhost 여도", s == 200 and list(json.loads(b).keys()) == ["v"], (s, b[:60]))
    s, h, b = hget(B, "/home", "localhost:%d" % B)
    check("⭐입구(B) /home → 307 works/home (실제 소켓에서 포트로 판정)", s == 307 and h.get("location") == WORKS + "/home", (s, h.get("location")))
    s, h, b = hget(B, "/", "localhost:%d" % B)
    check("입구(B) / → 303 받은편지함", s == 303 and h.get("location") == ms.MAIL_HOME, (s, h.get("location")))
    s, h, b = hget(B, "/mail/app?next=%2Fmail%2Fcompose", "localhost:%d" % B)
    check("⭐입구(B) /mail/app?next=/mail/compose → 「여는 중」 화면 · 돌아올 곳 kmail · 착지 메일 쓰기 · 조용히",
          s == 200 and launch_target(b)[:3] == (KMAIL + "/sso/land", "/mail/compose", True), (s, launch_target(b)))
    s, h, b = hget(B, "/mail/inbox", "localhost:%d" % B)
    check("입구(B) /mail/inbox(로그인 전) → /login", s == 303 and h.get("location") == "/login", (s, h.get("location")))
    s, h, b = hget(B, "/static/css/v5_main.css", "localhost:%d" % B)
    check("입구(B) 에서 화면 꾸밈 파일(/static)도 그대로 나온다", s == 200 and len(b) > 1000, (s, len(b)))
    s, h, b = hget(B, "/projects/1?tab=bom", "kmail.knknara.co.kr", method="POST", extra={"Content-Length": "0"})
    check("입구(B) POST 업무 주소 → 307 works(쿼리 유지)", s == 307 and h.get("location") == WORKS + "/projects/1?tab=bom", (s, h.get("location")))

    s, h, b = hget(B, "/home", "works.knknara.co.kr")
    check("⭐입구(B)에 works 이름으로 오면 넘기지 않는다(303 /login · 무한 왕복 방지 — 실제 소켓)", s == 303 and h.get("location") == "/login", (s, h.get("location")))
    s, h, b = hget(A, "/home", "works.knknara.co.kr")
    check("⭐⭐본체(A) /home → 303 /login — 넘김 없음(지금 운영 그대로)", s == 303 and h.get("location") == "/login", (s, h.get("location")))
    s, h, b = hget(A, "/mail/app", "works.knknara.co.kr")
    check("본체(A) /mail/app → 「여는 중」 화면 · 돌아올 곳 works", s == 200 and launch_target(b)[0] == WORKS + "/sso/land", (s, launch_target(b)))
    s, h, b = hget(A, "/", "localhost:%d" % A)
    check("본체(A) / → /login(받은편지함으로 보내지 않는다)", s == 303 and h.get("location") == "/login", (s, h.get("location")))

    # 두 포트에 번갈아 여러 번 — 섞이지 않는다
    mixed = True
    for i in range(12):
        sa = hget(A, "/home", "works.knknara.co.kr")
        sb = hget(B, "/home", "localhost")
        if not (sa[0] == 303 and sb[0] == 307):
            mixed = False
    check("두 포트에 번갈아 12번씩 — 판정이 섞이지 않는다(같은 프로세스 · 같은 앱)", mixed)

    # 종료 — 본체가 내려가면 입구도 같이 닫힌다
    box["srv"].should_exit = True
    th.join(20)
    check("본체 종료 → 입구도 닫히고 스레드가 끝난다(매달림 없음 · 오류 없음)", (not th.is_alive()) and box.get("stopped") is True and "err" not in box, box)
    check("종료 뒤 입구 상태 = 안 듣는 중 · 작업 정리됨 · 로그 STOP 한 줄", (not ms.listening()) and ms._L["task"] is None and ms._L["server"] is None
          and len([x for x in MSLOG if x.startswith("[MAIL-SITE] STOP pid=%d port=%d " % (os.getpid(), B))]) == 1, MSLOG)
    check("입구가 도는 동안 ERROR 로그는 한 줄도 없었다", not [x for x in MSLOG if " ERROR " in x], MSLOG)
    try:
        t2 = socket.socket()
        t2.bind(("127.0.0.1", B))
        t2.close()
        freed = True
    except OSError:
        freed = False
    check("종료 뒤 포트 B 가 풀렸다(다시 잡을 수 있음)", freed)
finally:
    try:
        squat.close()
    except Exception:
        pass
    if box.get("srv") is not None:
        box["srv"].should_exit = True
    th.join(10)

shutil.rmtree(_TMPD, ignore_errors=True)
check("작업 폴더에 DB 파일을 만들지 않았다(data/knk.db 없음)", not os.path.exists(os.path.join(ROOT, "data", "knk.db")))

print("\n결과: PASS %d / FAIL %d" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
