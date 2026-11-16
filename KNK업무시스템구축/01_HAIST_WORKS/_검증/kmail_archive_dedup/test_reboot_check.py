# -*- coding: utf-8 -*-
# 월요일 확인 스크립트 시험 — 이 PC 안의 가짜 서버로(운영 무접촉).
#   「여는 중」 화면(200)으로 바뀐 /mail/app 을 통과시키는지 + 옛 판(303)도 통과 + 엉뚱한 화면은 걸러내는지.
#   사용: py test_reboot_check3.py <확인 스크립트> <mail_site.py 사본>
import http.server, importlib.util, io, os, random, socket, subprocess, sys, threading
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SRC = io.open(sys.argv[1], encoding="utf-8").read()
spec = importlib.util.spec_from_file_location("ms_snap", sys.argv[2])
ms = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ms)
SSO_K = "https://msg.knknara.co.kr/sso/login?redirect_uri=https%3A%2F%2Fkmail.knknara.co.kr%2Fsso%2Fland%3Fnext%3D%252Fmail%252Finbox%253Fapp%253D1"
SSO_W = SSO_K.replace("kmail.knknara", "works.knknara")
SPLASH_K = ms.launch_page(ms.silent_sso_url(SSO_K)).encode("utf-8")       # 실제 코드가 만드는 화면 그대로
SPLASH_W = ms.launch_page(ms.silent_sso_url(SSO_W)).encode("utf-8")       # 돌아올 곳이 works 인 화면(= 메일 전용이 아님)
NOTICE = ms.need_login_page("https://msg.knknara.co.kr", "", "login_required").encode("utf-8")


def free():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def serve(mode_fn, port):
    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def do_GET(self):
            mode = mode_fn()
            path = self.path.split("?")[0]

            def out(code, body=b"", ctype="application/json", loc=None):
                self.send_response(code); self.send_header("Content-Type", ctype)
                if loc: self.send_header("Location", loc)
                self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            if mode == "old":
                if path == "/healthz": return out(200, b'{"ok":true,"app":"KNK Eum MAIL","db":"mail.db","tables":13,"missing":[]}')
                if path == "/api/version": return out(200, b'{"app":"knk-mail","phase":"feature-port"}')
                return out(200, b"<html>old login</html>", "text/html")
            if mode.startswith("works_mail"):
                if path == "/healthz": return out(404, b"<html>404</html>", "text/html")
                if path == "/api/version": return out(200, b'{"v":"abc1234"}')
                if path == "/home": return out(307, loc="https://works.knknara.co.kr/home")
                if path == "/": return out(303, loc="/mail/inbox?app=1")
                if path == "/mail/app":
                    if mode == "works_mail": return out(303, loc=SSO_K)                       # 앞 판(바로 넘김)
                    if mode == "works_mail_splash": return out(200, SPLASH_K, "text/html; charset=utf-8")   # 새 판
                    if mode == "works_mail_splash_w": return out(200, SPLASH_W, "text/html; charset=utf-8")
                    if mode == "works_mail_notice": return out(200, NOTICE, "text/html; charset=utf-8")
                    if mode == "works_mail_303w": return out(303, loc=SSO_W)
                    if mode == "works_mail_500": return out(500, b"<html>Internal Server Error</html>", "text/html")
                return out(404)
            if mode == "works":
                if path == "/api/version": return out(200, b'{"v":"abc1234"}')
                return out(404)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def run(kmode, wmode="works", wdown=False, kdown=False):
    pk, pw = free(), free()
    sk = None if kdown else serve(kmode, pk)
    sw = None if wdown else serve(lambda: wmode, pw)
    # 주소만 가짜 서버로 바꾸고(나머지 글자는 그대로), 기다림은 1회로
    src = (SRC.replace('W = "https://works.knknara.co.kr"', 'W = "http://127.0.0.1:%d"' % pw)
           .replace('K = "https://kmail.knknara.co.kr"', 'K = "http://127.0.0.1:%d"' % pk).replace("ROUNDS = 5", "ROUNDS = 1"))
    assert src.count("127.0.0.1") == 2 and "ROUNDS = 1" in src
    # 넘김 주소 비교는 실제 works 주소 글자를 쓰므로 그 부분만 원래대로
    src = src.replace('h1.get("Location") == W + "/home"', 'h1.get("Location") == "https://works.knknara.co.kr/home"')
    p = subprocess.run([sys.executable, "-c", src], capture_output=True, timeout=300, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    out = p.stdout.decode("utf-8", "replace")
    for s in (sk, sw):
        if s: s.shutdown()
    v = [l for l in out.splitlines() if l.startswith("VERDICT")]
    line = v[-1] if v else "NO VERDICT: " + out[-200:] + p.stderr.decode("utf-8", "replace")[-300:]
    app = [l.strip() for l in out.splitlines() if "/mail/app" in l]
    return line, (app[-1] if app else "")


res = []


def chk(name, got, want, app_want=None):
    line, app = got
    ok = line.startswith("VERDICT: " + want + " ") and (app_want is None or app.startswith("[" + app_want + "]"))
    res.append(ok)
    print("  [%s] %-58s → %s | %s" % ("PASS" if ok else "FAIL", name, line[:34], app[:60]))


print("화면 길이: 「여는 중」 %d바이트(확인 스크립트는 8000바이트까지 읽는다)" % len(SPLASH_K))
assert len(SPLASH_K) < 8000
chk("정상 · 앞 판(/mail/app 이 바로 넘김 303)", run(lambda: "works_mail"), "OK", "PASS")
chk("⭐정상 · 새 판(/mail/app 이 「여는 중」 화면 200)", run(lambda: "works_mail_splash"), "OK", "PASS")
chk("새 판인데 돌아올 곳이 works(메일 전용 아님)", run(lambda: "works_mail_splash_w"), "CHECK", "FAIL")
chk("/mail/app 이 로그인 안내 화면만 내놓음(넘어갈 주소 없음)", run(lambda: "works_mail_notice"), "CHECK", "FAIL")
chk("앞 판인데 돌아올 곳이 works", run(lambda: "works_mail_303w"), "CHECK", "FAIL")
chk("/mail/app 이 500", run(lambda: "works_mail_500"), "CHECK", "FAIL")
chk("옛 앱이 되살아나 5053 을 차지", run(lambda: "old"), "OLD_APP_BACK")
chk("둘이 섞여 응답", run(lambda: random.choice(["old", "works_mail_splash"])), "MIXED")
chk("kmail 무응답(works 는 정상)", run(lambda: "works_mail_splash", kdown=True), "DOWN")
chk("kmail 은 응답하지만 판이 다름/넘김 안 됨", run(lambda: "works"), "CHECK")
print("결과: PASS %d / FAIL %d" % (sum(res), len(res) - sum(res)))
