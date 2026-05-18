"""KNK 메신저 테스트용 — 빅터로 로그인 후 지정 방에 메시지 전송.

서버에서 실행:
    # 특정 방에 한 번
    .venv/bin/python3 deploy/victor_send.py 4 "안녕하세요, 빅터 테스트입니다"

    # 빅터가 속한 모든 방에 일괄 (기본 메시지)
    .venv/bin/python3 deploy/victor_send.py --all

    # 빅터가 속한 모든 방에 일괄 (커스텀 메시지)
    .venv/bin/python3 deploy/victor_send.py --all "(검증) 빅터입니다"

동작:
    1. /msg/login 으로 victor 세션 획득
    2. /msg/api/messages/send 호출 → DB 저장 + Socket.IO new_message 브로드캐스트
    3. 다른 멤버 PWA에 빨간 unread 뱃지 즉시 표시 (real-time)
"""
import argparse
import http.cookiejar
import json
import os
import sqlite3
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import build_opener, HTTPCookieProcessor, Request

BASE_URL = "http://127.0.0.1:5050/msg"
USERNAME = "victor"
PASSWORD = "victor8161"

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(APP_DIR, "data", "messenger.db")
DEFAULT_MSG = "(테스트) 빅터입니다. 메신저 검증 중 — 안 읽음 뱃지가 보이면 정상."


class _LocalCookiePolicy(http.cookiejar.DefaultCookiePolicy):
    """로컬호스트 HTTP 테스트용 — 운영모드의 Secure 쿠키도 HTTP 로 전송 허용.
    Flask SESSION_COOKIE_SECURE=True 일 때 cookie 가 Secure 표시됨 → 기본
    Policy 가 HTTPS 요청에만 전송 → 같은 머신 localhost:5050 (HTTP) 에서는
    세션이 안 실려서 로그인이 유지 안 됨. 이 정책으로 우회."""

    def return_ok_secure(self, cookie, request):
        return True  # secure 검사 무시 (로컬 한정 스크립트라 안전)


def make_session():
    cj = http.cookiejar.CookieJar(_LocalCookiePolicy())
    return build_opener(HTTPCookieProcessor(cj))


def login(opener):
    data = urlencode({"username": USERNAME, "password": PASSWORD}).encode("utf-8")
    req = Request(BASE_URL + "/login", data=data, method="POST")
    resp = opener.open(req, timeout=10)
    body = resp.read().decode("utf-8", errors="replace")
    final_url = resp.geturl()
    if "/login" in final_url and "올바르지" in body:
        raise RuntimeError("login 실패 — username/password 점검")
    return final_url


def send_message(opener, room_id, content):
    payload = json.dumps({"room_id": int(room_id), "content": content}).encode("utf-8")
    req = Request(
        BASE_URL + "/api/messages/send",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        resp = opener.open(req, timeout=15)
        return json.loads(resp.read().decode("utf-8", errors="replace"))
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}")


def list_victor_rooms():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    v = db.execute("SELECT id FROM users WHERE username=?", (USERNAME,)).fetchone()
    if not v:
        db.close()
        raise RuntimeError("victor 사용자 없음. 먼저 deploy/add_victor.py 실행")
    rooms = db.execute(
        """SELECT r.id, COALESCE(r.name,'') AS name, r.type
             FROM rooms r
             JOIN room_members rm ON rm.room_id = r.id AND rm.user_id = ?
            ORDER BY r.id""",
        (v["id"],),
    ).fetchall()
    db.close()
    return [dict(r) for r in rooms]


def main():
    p = argparse.ArgumentParser(description="victor 로 테스트 메시지 전송")
    p.add_argument("target", nargs="?", help="방 ID (숫자) — --all 사용 시 메시지 위치")
    p.add_argument("message", nargs="?", help="메시지 (생략 시 기본)")
    p.add_argument("--all", action="store_true", help="victor 가 속한 모든 방에 일괄")
    args = p.parse_args()

    if args.all:
        # --all 모드: target 이 있으면 그게 메시지
        msg = args.target if args.target else DEFAULT_MSG
        rooms = list_victor_rooms()
        if not rooms:
            print("victor 가 속한 방 없음")
            return 1
        print(f"victor 가 속한 방 {len(rooms)} 개에 일괄 전송: '{msg}'")
    else:
        if not args.target:
            print("ERROR: 방 ID 또는 --all 필요")
            p.print_help()
            return 1
        try:
            room_id = int(args.target)
        except ValueError:
            print(f"ERROR: 방 ID 는 숫자여야 함: {args.target}")
            return 1
        msg = args.message or DEFAULT_MSG
        rooms = [{"id": room_id, "name": "?", "type": "?"}]

    opener = make_session()
    try:
        final = login(opener)
        print(f"[OK] login → {final}")
    except (URLError, RuntimeError) as e:
        print(f"[FAIL] login: {e}")
        return 2

    sent = 0
    for r in rooms:
        try:
            res = send_message(opener, r["id"], msg)
            mid = res.get("id") or res.get("message_id") or "?"
            print(f"[OK]   room {r['id']:>3} '{r['name']}' ({r['type']}) — msg id={mid}")
            sent += 1
        except Exception as e:
            print(f"[FAIL] room {r['id']}: {e}")

    print(f"\n=== {sent}/{len(rooms)} 전송 완료 ===")
    return 0 if sent == len(rooms) else 3


if __name__ == "__main__":
    sys.exit(main())
