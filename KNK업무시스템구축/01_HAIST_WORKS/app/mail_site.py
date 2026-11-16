# -*- coding: utf-8 -*-
"""📮 메일 전용 주소(kmail) — 판정 · 넘김 · 메일 전용 입구(포트)를 한 곳에.

대표 지시 2026-11-16: 「이음메일을 이음웍스와 별개로 연결」 → 「5053으로 적용해서 설정해」.

왜
  메일이 works.knknara.co.kr **안**에 있으면 윈도우·크롬이 업무시스템과 메일을 **한 앱**으로 본다
  (메일 창이 업무 창을 덮는다). 메일을 **다른 주소**(kmail.knknara.co.kr)로 열면 창이 갈린다.

어떻게
  NAS 중계기(DSM)는  kmail → localhost:5053 ,  works → localhost:5051  로 보낸다(그대로 둔다).
  그래서 **WORKS 가 5053 도 함께 듣는다** — 같은 프로세스 · 같은 앱(프로세스를 늘리지 않는다).
  5053 으로 들어온 요청 = 메일 전용 주소로 온 것 → 메일 화면만 열고, 업무 화면은 works 로 넘긴다.

  ⭐「어느 주소로 들어왔나」는 **들어온 포트**로 판단한다.
    중계기가 Host 를 바꿔 보내도 포트는 못 바꾼다(scope["server"] = 실제로 받은 소켓).
    이름(Host = kmail…)도 함께 본다 — 둘 중 하나만 맞아도 메일 전용으로 친다.
    단, 이름이 works 인 요청은 어느 포트로 왔든 메일 전용이 아니다(무한 왕복 방지 — is_mail_site_scope 참고).

안전
  · 환경변수 KNK_MAIL_SITE_PORT 가 없으면 **입구를 열지 않는다**(판정은 이름으로만 · 지금 운영과 같다).
  · 그 포트를 다른 프로그램이 쓰고 있으면 **조용히 기다렸다 다시** 잡는다(WORKS 본체 5051 무영향).
  · 이 파일의 어떤 실패도 WORKS 를 멈추지 않는다(전부 잡아서 로그만 남긴다).

쓰는 곳: app/main.py (미들웨어 등록 · 기동/종료 훅 · /login · /sso/land · /mail/app · 메일 매니페스트 · ctx)
시험: _검증/mail_site_test.py
"""
import asyncio
import contextlib
import os
import socket
import time
from urllib.parse import quote

# ─── 주소 두 개 — 코드에 박는다 ──────────────────────────────────────────────
#   ⭐로그인 왕복(SSO)이 돌아올 곳은 이 둘뿐이다. 요청이 말하는 주소(Host)를 그대로 믿어
#     돌아올 곳을 만들면 로그인 토큰이 엉뚱한 곳으로 갈 수 있다 → 절대 Host 로 조립하지 않는다.
MAIL_SITE_HOST = "kmail.knknara.co.kr"
WORKS_SITE_HOST = "works.knknara.co.kr"
MAIL_PUBLIC_BASE = "https://" + MAIL_SITE_HOST
WORKS_PUBLIC_BASE = "https://" + WORKS_SITE_HOST      # app/main.py 의 _WORKS_PUBLIC_BASE 와 같은 값(시험이 대조)

MAIL_HOME = "/mail/inbox?app=1"                       # 메일 전용 주소의 첫 화면


def _env_port() -> int:
    """KNK_MAIL_SITE_PORT — 없거나 이상하면 0(입구 안 엶)."""
    try:
        p = int((os.environ.get("KNK_MAIL_SITE_PORT") or "0").strip() or "0")
    except Exception:
        return 0
    return p if 1024 <= p <= 65535 else 0


LISTEN_PORT = _env_port()                             # 0 = 끔
_BIND_HOST = (os.environ.get("KNK_MAIL_SITE_BIND") or "0.0.0.0").strip() or "0.0.0.0"

# ─── 메일 전용 주소에서 열어 주는 길 ─────────────────────────────────────────
#   그 밖(업무 화면)은 works 로 넘긴다. 메일 화면이 뒤에서 부르는 주소는 전부 이 안에 있다
#   (2026-11-16 메일 화면 14개 + 조각 4개 전수 확인: 뒤에서 부르는 것은 /mail/… · /api/mail/… 뿐).
_OK_EXACT = frozenset(("/login", "/logout", "/healthz", "/api/version", "/favicon.ico", "/robots.txt"))
_OK_PREFIX = ("/mail/", "/admin/mail-", "/api/mail/", "/static/", "/sso/", "/dl/")
# /mail/ 로 시작하지만 **업무 화면**(연락처 쪽 발송 설정 — 사이드바가 붙는 화면)인 것 → works 로
_WORKS_ONLY = ("/mail/settings", "/mail/test")
# 메일 전용 주소의 「대문」 — 받은편지함으로
_HOME_ALIASES = frozenset(("/", "/mail", "/mail/"))
# 로그인 뒤 착지해도 되는 곳(메일 안쪽)
_LAND_PREFIX = ("/mail/", "/admin/mail-")
# 넘길 주소를 다시 만들 때 그대로 둘 글자(경로에 쓸 수 있는 글자)
_PATH_SAFE = "/%:@!$&'()*+,;=-._~"


def allows(path: str) -> bool:
    """메일 전용 주소에서 열어 줄 길인가."""
    p = path or "/"
    for w in _WORKS_ONLY:
        if p == w or p.startswith(w + "/"):
            return False
    return p in _OK_EXACT or p.startswith(_OK_PREFIX)


def landing(nxt: str) -> str:
    """메일 전용 주소에서 로그인 뒤 착지할 곳 — 메일 안쪽이 아니면 받은편지함.
    (nxt 는 이미 _safe_next_path 를 지난 「안쪽 경로」라고 본다. 여기선 메일 안쪽인지만 좁힌다.)"""
    n = (nxt or "").strip()
    p = n.split("?", 1)[0].split("#", 1)[0]
    if n and p.startswith(_LAND_PREFIX) and allows(p):
        return n
    return MAIL_HOME


# ─── 판정 ────────────────────────────────────────────────────────────────────
def _scope_host(scope) -> str:
    """Host 헤더에서 이름만(소문자 · 포트 뗌). 못 읽으면 빈 글자."""
    try:
        for k, v in scope.get("headers") or ():
            if k == b"host":
                h = v.decode("latin-1").strip().lower()
                if h.startswith("["):                 # [::1]:5053 같은 IPv6 표기 — 메일 주소일 수 없다
                    return h
                if ":" in h:
                    h = h.rsplit(":", 1)[0]
                return h.rstrip(".")
    except Exception:
        pass
    return ""


def is_mail_site_scope(scope) -> bool:
    """이 요청이 「메일 전용 주소」로 들어왔는가.
      ① 이름이 works 면 → 아니다(어느 포트로 왔든)
      ② 메일 전용 입구(포트)로 왔으면 → 맞다(이름이 localhost 로 바뀌어 와도)
      ③ 이름이 kmail 이면 → 맞다
    ⭐①이 맨 앞인 까닭 = 무한 왕복 방지. 업무 화면은 works 로 넘기는데, 훗날 중계 설정이 바뀌어
      works 요청이 메일 입구로 들어오면 「넘김 → 다시 들어옴 → 넘김…」이 되어 업무시스템이 통째로 멈춘다.
      works 이름으로 온 것은 절대 다시 넘기지 않으면 그 사고가 날 수 없다."""
    host = _scope_host(scope)
    if host == WORKS_SITE_HOST:
        return False
    try:
        if LISTEN_PORT:
            srv = scope.get("server") or ()
            if len(srv) >= 2 and srv[1] == LISTEN_PORT:
                return True
    except Exception:
        pass
    return host == MAIL_SITE_HOST


def is_mail_site(req) -> bool:
    """Request 로 묻는 판정(라우트·ctx 용)."""
    try:
        return is_mail_site_scope(req.scope)
    except Exception:
        return False


def public_base(req) -> str:
    """이 요청이 들어온 주소에 맞는 공개 주소 — works · kmail **둘 중 하나만** 돌려준다."""
    return MAIL_PUBLIC_BASE if is_mail_site(req) else WORKS_PUBLIC_BASE


# ─── 넘김(미들웨어) ──────────────────────────────────────────────────────────
def _redirect_for(scope):
    """메일 전용 주소로 온 요청을 어디로 보낼지. None = 그대로 처리.
    반환 (주소, 상태코드)."""
    path = scope.get("path") or "/"
    method = (scope.get("method") or "GET").upper()
    if path in _HOME_ALIASES and method in ("GET", "HEAD"):
        return (MAIL_HOME, 303)
    if allows(path):
        return None
    # 업무 화면 → works 의 **같은 경로**로. 307 = 방식(GET/POST)과 본문을 그대로 유지.
    p = ""
    raw = scope.get("raw_path")
    if isinstance(raw, (bytes, bytearray)) and raw:
        p = bytes(raw).split(b"?", 1)[0].decode("latin-1")
    if not p.startswith("/"):
        p = quote(path, safe=_PATH_SAFE)
    qs = scope.get("query_string") or b""
    q = ("?" + bytes(qs).decode("latin-1")) if qs else ""
    return (WORKS_PUBLIC_BASE + p + q, 307)


class Guard:
    """메일 전용 주소로 들어온 요청 중 업무 화면은 works 로 넘긴다(순수 ASGI — 다른 요청엔 비용 없음).
    메일 전용 주소가 아니면 **아무것도 하지 않고** 그대로 넘긴다."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        target = None
        try:
            if scope.get("type") == "http" and is_mail_site_scope(scope):
                target = _redirect_for(scope)
        except Exception as e:
            # 판정이 깨져도 서비스는 그대로 — 넘기지 않고 평소대로 처리
            print("[MAIL-SITE] ERROR guard — 판정 실패(그대로 진행): %s" % str(e)[:120], flush=True)
            target = None
        if target is None:
            await self.app(scope, receive, send)
            return
        url, status = target
        await send({
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"location", url.encode("latin-1", "replace")),
                (b"content-length", b"0"),
                (b"cache-control", b"no-store"),
            ],
        })
        await send({"type": "http.response.body", "body": b""})


# ─── 메일 전용 입구(포트) — WORKS 프로세스 안에서 함께 듣는다 ────────────────
#   로그 맨 앞 낱말(WAIT · LISTEN · STOP · ERROR)은 **영문 고정** — 서버 점검 스크립트가 이 글자로 상태를 읽는다.
_RETRY_SEC = 10.0            # 포트가 막혀 있으면 이 간격으로 다시 본다(옛 앱이 멈춘 뒤 이 안에 넘겨받는다)
_BUSY_LOG_EVERY = 1800.0     # 「막혀 있음」 로그는 30분에 한 줄만
_L = {"task": None, "server": None, "stop": False, "listening": False}


def listening() -> bool:
    """지금 이 프로세스가 메일 전용 입구를 듣고 있는가(확인·시험용)."""
    return bool(_L.get("listening"))


def _bind(port: int, host: str):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if os.name != "nt":
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            rp = getattr(socket, "SO_REUSEPORT", None)
            if rp is not None:
                # 일꾼(프로세스)이 여럿이면 각자 같은 포트를 함께 듣는다(리눅스가 나눠 준다).
                # ⚠이 표시가 없는 다른 프로그램(옛 메일 앱)이 먼저 잡고 있으면 여기서 실패한다 — 바라는 동작.
                s.setsockopt(socket.SOL_SOCKET, rp, 1)
        s.bind((host, port))
    except BaseException:
        s.close()
        raise
    return s


async def _nap(sec: float) -> None:
    end = time.monotonic() + sec
    while not _L["stop"]:
        left = end - time.monotonic()
        if left <= 0:
            return
        await asyncio.sleep(min(1.0, left))


async def _run(app, port: int, host: str) -> None:
    import uvicorn

    class _Quiet(uvicorn.Server):
        """신호(SIGTERM 등)는 WORKS 본체 서버가 받는다 — 이쪽은 손대지 않는다."""

        def install_signal_handlers(self):            # 옛 uvicorn
            return None

        @contextlib.contextmanager
        def capture_signals(self):                    # 새 uvicorn(0.29~)
            yield

    pid = os.getpid()
    said = 0.0
    while not _L["stop"]:
        try:
            sock = _bind(port, host)
        except OSError as e:
            now = time.monotonic()
            if not said or now - said >= _BUSY_LOG_EVERY:
                said = now
                print("[MAIL-SITE] WAIT pid=%d port=%d — 포트 %d 를 다른 프로그램이 쓰고 있다 — %d초마다 다시 본다"
                      "(WORKS 본체 무영향): %s" % (pid, port, port, int(_RETRY_SEC), str(e)[:120]), flush=True)
            await _nap(_RETRY_SEC)
            continue
        was_listening = False
        try:
            # WORKS 본체와 같은 조건으로 듣는다(운영 기동 스크립트: --proxy-headers --forwarded-allow-ips=*).
            #   lifespan="off" = 기동·종료 훅을 두 번 돌리지 않는다 · log_config=None = 본체의 로그 설정을 건드리지 않는다.
            cfg = uvicorn.Config(app, host=host, port=port, workers=1, lifespan="off", log_config=None,
                                 proxy_headers=True, forwarded_allow_ips="*")
            srv = _Quiet(cfg)
            _L["server"] = srv
            _L["listening"] = was_listening = True
            said = 0.0
            print("[MAIL-SITE] LISTEN pid=%d %s:%d — 메일 전용 입구 듣기 시작" % (pid, host, port), flush=True)
            await srv.serve(sockets=[sock])
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print("[MAIL-SITE] ERROR pid=%d — 입구 오류(다시 시도 · WORKS 본체 무영향): %s"
                  % (pid, str(e)[:200]), flush=True)
        finally:
            _L["listening"] = False
            _L["server"] = None
            with contextlib.suppress(Exception):
                sock.close()
            if was_listening:
                print("[MAIL-SITE] STOP pid=%d port=%d — 메일 전용 입구 닫음" % (pid, port), flush=True)
        if _L["stop"]:
            break
        await _nap(_RETRY_SEC)


def start(app) -> bool:
    """기동 때 한 번 부른다. 환경변수가 없으면 아무것도 안 한다. 어떤 실패도 예외로 올리지 않는다."""
    try:
        if not LISTEN_PORT:
            return False
        if _L.get("task") is not None:
            return True
        _L["stop"] = False
        _L["task"] = asyncio.get_running_loop().create_task(_run(app, LISTEN_PORT, _BIND_HOST))
        return True
    except Exception as e:
        print("[MAIL-SITE] ERROR start — 입구 시작 실패(WORKS 본체 무영향): %s" % str(e)[:200], flush=True)
        return False


async def stop(timeout: float = 6.0) -> None:
    """종료 때 한 번 부른다. 진행 중인 요청을 잠깐 기다렸다 닫는다."""
    try:
        _L["stop"] = True
        srv = _L.get("server")
        if srv is not None:
            srv.should_exit = True
        t = _L.get("task")
        if t is not None and not t.done():
            try:
                await asyncio.wait_for(asyncio.shield(t), timeout)
            except Exception:
                t.cancel()
                with contextlib.suppress(BaseException):
                    await t
    except Exception:
        pass
    finally:
        _L["task"] = None
