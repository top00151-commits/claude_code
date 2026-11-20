# -*- coding: utf-8 -*-
"""가짜 이음 직원 명부 — GET /api/sso/directory 하나만 흉내(메일 2단계 휴가 표시 시험·시연용 · 가짜 사람·가짜 값).
⛔ 운영 이음·이음 DB·대화방은 전혀 만지지 않는다 — 로컬(127.0.0.1)에서만 듣고 부른 횟수만 센다.

FAKE["mode"]: ok · slow(FAKE["slow"]초 늦게) · 500 · 404 · badjson
USERS = 이음 명부 모양(employee_no·name_kr·dept·position·email·active·status·status_until …)
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

FAKE = {"key": "", "mode": "ok", "slow": 6.0}
USERS = []
CALLS = []          # [(시각, 키 맞음)]
_LOCK = threading.Lock()


class _H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, raw, ctype="application/json"):
        try:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        except (ConnectionError, OSError):
            pass

    def do_GET(self):
        if self.path.split("?")[0] != "/api/sso/directory":
            return self._send(404, b"<h1>Not Found</h1>", "text/html")
        key_ok = bool(FAKE["key"]) and self.headers.get("X-SSO-Service-Key") == FAKE["key"]
        with _LOCK:
            CALLS.append((time.time(), key_ok))
        mode = FAKE["mode"]
        if mode == "slow":
            time.sleep(FAKE["slow"])
        if mode == "404":
            return self._send(404, b"<h1>Not Found</h1>", "text/html")
        if mode == "500":
            return self._send(500, b"<h1>oops</h1>", "text/html")
        if not key_ok:
            return self._send(403, json.dumps({"ok": False, "error": "forbidden"}).encode("utf-8"))
        if mode == "badjson":
            return self._send(200, b"not json")
        body = {"users": list(USERS), "count": len(USERS), "generated_at": "2026-11-20T00:00:00+00:00", "source": "knk-messenger"}
        return self._send(200, json.dumps(body, ensure_ascii=False).encode("utf-8"))


def start(port=0):
    srv = ThreadingHTTPServer(("127.0.0.1", port), _H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://127.0.0.1:%d" % srv.server_address[1]
