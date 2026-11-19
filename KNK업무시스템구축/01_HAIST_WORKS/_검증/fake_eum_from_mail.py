# -*- coding: utf-8 -*-
"""가짜 이음 — 「메일에서 맡기기」 입구 두 개만 흉내(계약서 2026-11-20_0203_Eum_v988_메일맡기기_계약서.md).
⛔ 운영 이음·이음 DB·대화방은 전혀 만지지 않는다 — 이 로컬 작은 서버가 받은 것을 기록만 한다(시험·시연용 · 가짜 값).

  POST /api/requests/from-mail          → 받은 payload·첨부를 RECV 에 기록 · 계약 모양 응답
  POST /api/requests/from-mail/status   → STATE[ref] 로 상태 응답 · 묻는 ref 를 STATUS_CALLS 에 기록

FAKE["mode"] 로 오류를 흉내 낸다: ok · 404(입구 없음) · assignee_invalid · rate_limited · slow(늦게) · html500
"""
import json
import re
import secrets
import threading
import time
from email.parser import BytesParser
from email.policy import default as _pol
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TEST_GROUP = ("5", "67", "306")
FAKE = {"key": "", "mode": "ok", "bad": [], "slow": 2.0, "public": "https://msg.example.test"}
RECV = []            # [{"ctype", "key_ok", "payload", "files":[(name, bytes)]}]
STATUS_CALLS = []    # [[ref, ...], ...]
STATE = {}           # ref → item(dict) 덮어쓰기
IDEM = {}            # idem_key → 처음 응답
_N = [1233]
_LOCK = threading.Lock()


def reset():
    with _LOCK:
        RECV.clear()
        STATUS_CALLS.clear()
        STATE.clear()
        IDEM.clear()
        FAKE.update(mode="ok", bad=[])


def _multipart(ctype, body):
    msg = BytesParser(policy=_pol).parsebytes(b"Content-Type: " + ctype.encode() + b"\r\n\r\n" + body)
    payload, files = None, []
    for part in msg.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if name == "payload":
            payload = part.get_payload(decode=True).decode("utf-8")   # 이음(werkzeug)처럼 글자 칸은 UTF-8 로 읽음
        elif name == "files":
            files.append((part.get_filename(), part.get_payload(decode=True), part.get_content_type()))
    return payload, files


class _H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj=None, raw=None, ctype="application/json"):
        b = raw if raw is not None else json.dumps(obj, ensure_ascii=False).encode("utf-8")
        try:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
        except (ConnectionError, OSError):
            pass   # 웍스가 기다리다 먼저 끊은 경우(「늦음」 시험)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else b""
        key_ok = bool(FAKE["key"]) and self.headers.get("X-SSO-Service-Key") == FAKE["key"]
        if FAKE["mode"] == "404":
            return self._send(404, raw=b"<h1>Not Found</h1>", ctype="text/html")
        if self.path == "/api/requests/from-mail":
            return self._create(body, key_ok)
        if self.path == "/api/requests/from-mail/status":
            return self._status(body, key_ok)
        if self.path == "/_fake/state":   # 시연 전용 — 상태 바꾸기(로컬 가짜에만 있음)
            for ref, st in (json.loads(body.decode("utf-8")) or {}).items():
                with _LOCK:
                    if ref == "*":
                        for r2 in list(STATE):
                            STATE[r2].update(st)
                    elif ref in STATE:
                        STATE[ref].update(st)
            return self._send(200, {"ok": True, "refs": list(STATE)})
        return self._send(404, raw=b"<h1>Not Found</h1>", ctype="text/html")

    def _create(self, body, key_ok):
        ctype = self.headers.get("Content-Type") or ""
        rec = {"ctype": ctype.split(";")[0].strip(), "key_ok": key_ok, "payload": None, "files": [], "size": len(body)}
        try:
            if ctype.startswith("multipart/form-data"):
                ptxt, files = _multipart(ctype, body)
                rec["files"] = files
                rec["payload"] = json.loads(ptxt) if ptxt else None
            else:
                rec["payload"] = json.loads(body.decode("utf-8"))
        except Exception as e:
            rec["parse_error"] = str(e)
        with _LOCK:
            RECV.append(rec)
        if not key_ok:
            return self._send(403, {"ok": False, "error": "forbidden", "message": "공유키 틀림"})
        p = rec["payload"]
        if not isinstance(p, dict):
            return self._send(400, {"ok": False, "error": "bad_payload", "message": "payload"})
        mode = FAKE["mode"]
        if mode == "slow":
            time.sleep(FAKE["slow"])
        if mode == "html500":
            return self._send(500, raw=b"<h1>oops</h1>", ctype="text/html")
        if mode == "rate_limited":
            return self._send(429, {"ok": False, "error": "rate_limited", "message": "많음"})
        if str(p.get("requester_employee_no")) not in TEST_GROUP:
            return self._send(403, {"ok": False, "error": "not_in_test_group", "message": "시험 명단 밖"})
        if mode == "assignee_invalid":
            return self._send(400, {"ok": False, "error": "assignee_invalid", "message": "켜진 직원 아님", "bad": FAKE["bad"]})
        if not p.get("mail"):
            return self._send(400, {"ok": False, "error": "mail_required", "message": "mail"})
        if len(p.get("instruction") or "") > 200:
            return self._send(400, {"ok": False, "error": "instruction_too_long", "message": "200", "max": 200})
        if len(rec["files"]) > 10:
            return self._send(400, {"ok": False, "error": "too_many_files", "message": "10", "max": 10})
        idem = p.get("idem_key") or ""
        with _LOCK:
            if idem and idem in IDEM:
                first = IDEM[idem]
                return self._send(200, dict({k: first[k] for k in ("request_no", "ref", "url", "path", "win_url", "room_name", "due", "result_kind")},
                                            ok=True, existing=True))
            _N[0] += 1
            no = _N[0]
        ref = secrets.token_hex(16)
        due = p.get("due") or ""
        out = {"ok": True, "existing": False, "request_no": no, "ref": ref,
               "url": FAKE["public"] + "/chat?room=88&request=%d" % no, "path": "/chat?room=88&request=%d" % no,
               "win_url": FAKE["public"] + "/chat?solo=1&reqwin=%d" % no,
               "room_name": "📧 메일 업무 · 시험 → " + ", ".join(p.get("assignee_employee_nos") or []),
               "room_new": no % 2 == 0, "due": (due[:10] + "T18:00") if due else "2026-11-23T18:00", "due_default": not due,
               "due_tz": "한국", "result_kind": p.get("result_kind") or "reply",
               "attachments": [{"name": f[0], "size": len(f[1] or b"")} for f in rec["files"] if not (f[0] or "").lower().endswith(".exe")],
               "skipped_files": [{"name": f[0], "code": "execExt", "reason": "실행 파일"} for f in rec["files"] if (f[0] or "").lower().endswith(".exe")],
               "body_truncated": len((p.get("mail") or {}).get("body") or "") >= 20000}
        with _LOCK:
            if idem:
                IDEM[idem] = out
            STATE.setdefault(ref, {"state": "working", "label": "진행 중", "status": "open", "due": out["due"],
                                   "assignees": [{"employee_no": a, "name": "이음이름" + a, "status": "open"} for a in (p.get("assignee_employee_nos") or [])]})
        return self._send(200, out)

    def _status(self, body, key_ok):
        if not key_ok:
            return self._send(403, {"ok": False, "error": "forbidden", "message": "공유키 틀림"})
        try:
            refs = json.loads(body.decode("utf-8")).get("refs")
        except Exception:
            refs = None
        if (not isinstance(refs, list) or not refs or len(refs) > 100
                or any(not isinstance(r, str) or not re.match(r"^[0-9a-f]{32}$", r) for r in refs)):
            return self._send(400, {"ok": False, "error": "bad_refs", "message": "refs"})
        with _LOCK:
            STATUS_CALLS.append(list(refs))
        items = []
        for r in refs:
            st = STATE.get(r)
            if not st:
                items.append({"ref": r, "found": False})
                continue
            it = {"ref": r, "found": True, "request_no": 0, "state": "working", "label": "진행 중", "status": "open",
                  "archived": False, "ended_at": None, "delivered_at": None, "updated_at": "2026-11-20T01:00:00+00:00",
                  "due": "2026-11-27T18:00", "assignees": [], "declined": []}
            it.update(st)
            items.append(it)
        return self._send(200, {"ok": True, "items": items})


def start(port=0):
    """로컬(127.0.0.1)에서만 듣는다 → (서버, 기본 주소)."""
    srv = ThreadingHTTPServer(("127.0.0.1", port), _H)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    return srv, "http://127.0.0.1:%d" % srv.server_address[1]
