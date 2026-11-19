# -*- coding: utf-8 -*-
"""z1191z84 시험 — 서버 기록에 로그인 토큰 값이 안 찍히는가 (대표 2026-11-20 「토큰 기록 고쳐」)

§1 가리기 함수 · §2 **진짜 uvicorn 을 운영과 같은 방식(uvicorn app.main:app)으로 띄워** 접속 기록을 읽는다.
  코드 폴더를 임시 폴더로 복사해 띄운다(DB 경로가 코드 옆 data/ 라 — 이 PC 의 실제 DB 를 건드리지 않게).
"""
import os, re, shutil, socket, subprocess, sys, tempfile, time, urllib.request
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app.log_redact import redact, TokenRedactFilter, install  # noqa: E402

OK = FAIL = 0


def chk(c, m):
    global OK, FAIL
    OK, FAIL = (OK + 1, FAIL) if c else (OK, FAIL + 1)
    print(("  [OK] " if c else "  [FAIL] ") + m)


JWT = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.c2lnbmF0dXJlLXRlc3Qtb25seQ"
print("§1 가리기")
chk(redact("/sso/land?next=%2Fmeetings&token=" + JWT) == "/sso/land?next=%2Fmeetings&token=***", "/sso/land 토큰 가림 · next 는 그대로")
chk(redact("/mail/app?token=" + JWT + "&x=1") == "/mail/app?token=***&x=1", "/mail/app 토큰만 가리고 뒤 변수는 그대로")
chk(redact("/x?access_token=a&ID_TOKEN=b&password=c&pw=d&api_key=e&sig=f") == "/x?access_token=***&ID_TOKEN=***&password=***&pw=***&api_key=***&sig=***",
    "다른 비밀 이름도(대소문자 무관)")
for s in ("/api/mgmt-code/check?code=KT-2026-01", "/api/field-guides/examples?key=po", "/api/meeting/5/rec-chunk?session=ab12", "/home", "/q?tokenizer=1"):
    chk(redact(s) == s, "일반 주소는 그대로: %s" % s)
chk(redact(None) is None and redact(5) == 5, "글자가 아니면 그대로")
import logging  # noqa: E402
rec = logging.LogRecord("uvicorn.access", logging.INFO, "", 0, '%s - "%s %s HTTP/%s" %d', ("1.2.3.4:0", "GET", "/sso/land?token=" + JWT, "1.1", 303), None)
TokenRedactFilter().filter(rec)
chk(JWT not in rec.getMessage() and "token=***" in rec.getMessage() and rec.getMessage().endswith("303"), "uvicorn 접속 기록 한 줄 모양 그대로 · 토큰만 가림")
install(); install()
chk(sum(isinstance(f, TokenRedactFilter) for f in logging.getLogger("uvicorn.access").filters) == 1, "여러 번 설치해도 한 번만")
src = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
chk(src.index("_z84lr.install()") < src.index("app = FastAPI("), "main.py 맨 앞(앱 만들기 전)에 설치")

print("§2 진짜 uvicorn 접속 기록")
TMP = tempfile.mkdtemp(prefix="knk_z84_")
W = os.path.join(TMP, "w")
shutil.copytree(os.path.join(ROOT, "app"), os.path.join(W, "app"), ignore=shutil.ignore_patterns("__pycache__"))
if os.path.isdir(os.path.join(ROOT, "static")):
    shutil.copytree(os.path.join(ROOT, "static"), os.path.join(W, "static"), ignore=shutil.ignore_patterns("uploads"))
os.makedirs(os.path.join(W, "data"), exist_ok=True)
sk = socket.socket(); sk.bind(("127.0.0.1", 0)); PORT = sk.getsockname()[1]; sk.close()
LOG = os.path.join(TMP, "uvicorn.log")
env = dict(os.environ, PYTHONIOENCODING="utf-8", KNK_SSO_SERVICE_KEY="z84-test-only")
with open(LOG, "w", encoding="utf-8") as lf:
    pr = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT), "--workers", "1"],
                          cwd=W, stdout=lf, stderr=subprocess.STDOUT, env=env)
    try:
        up = False
        for _ in range(240):
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/api/version" % PORT, timeout=2); up = True; break
            except Exception:
                time.sleep(0.5)
        chk(up, "임시 서버 떠 있음")

        def hit(p):
            try:
                urllib.request.build_opener(type("NR", (urllib.request.HTTPRedirectHandler,), {"redirect_request": lambda *a, **k: None})()) \
                    .open("http://127.0.0.1:%d%s" % (PORT, p), timeout=10)
            except Exception:
                pass
        hit("/sso/land?next=%2Fmeetings&token=" + JWT)
        hit("/mail/app?token=" + JWT)
        hit("/sso/callback?token=" + JWT + "&state=s1")
        hit("/api/mgmt-code/check?code=KT-TEST-83")
        time.sleep(1.5)
    finally:
        pr.terminate()
        try:
            pr.wait(15)
        except Exception:
            pr.kill()
txt = open(LOG, encoding="utf-8", errors="replace").read()
chk(JWT not in txt, "기록 파일 어디에도 토큰 값 없음")
chk(len(re.findall(r'"GET /sso/land\?next=%2Fmeetings&token=\*\*\* HTTP', txt)) == 1, "/sso/land 줄 = token=*** 로 남음(주소·결과 코드는 그대로)")
chk('"GET /mail/app?token=*** HTTP' in txt and '"GET /sso/callback?token=***&state=s1 HTTP' in txt, "/mail/app · /sso/callback 도 가림")
chk("/api/mgmt-code/check?code=KT-TEST-83" in txt, "관리번호 같은 일반 변수는 그대로 남음")
shutil.rmtree(TMP, ignore_errors=True)

print("\n결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
