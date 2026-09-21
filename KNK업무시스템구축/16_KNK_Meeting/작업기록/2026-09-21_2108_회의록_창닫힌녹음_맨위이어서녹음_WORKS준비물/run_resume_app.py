# -*- coding: utf-8 -*-
"""z1120 「창이 닫혀 멈춘 녹음 → 맨 위 🎙 이어서 녹음」 시험용 WORKS 서버 (기본 127.0.0.1:8937 · 이음 불필요).
사용: py run_resume_app.py <앱폴더(절대경로)> [포트=8937]
🔴 AI 키를 비우고 음성→글자·AI 정리를 모두 가짜로 바꾼다(2026-09-17 실제 whisper 호출 사고 뒤 규칙).
가짜 음성→글자는 **파일 이름**을 돌려준다 — 끊긴 조각·이어서 녹음·녹음기 파일이 어떤 순서로 본문에 붙었는지 본다.
사람은 쿠키 tuser=<사용자 id> 로 고른다(없으면 대표)."""
import io
import json
import os
import shutil
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
APP = sys.argv[1]
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8937
os.chdir(APP)
sys.path.insert(0, APP)
os.environ.setdefault("KNK_SECRET_KEY", "verify-only-key")
os.environ["KNK_MESSENGER_SSO_INTERNAL_BASE"] = "http://127.0.0.1:9"
for _k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "KNK_OPENAI_API_KEY"):
    os.environ[_k] = ""
sys.stdout.reconfigure(encoding="utf-8")
shutil.rmtree(os.path.join(APP, "data"), ignore_errors=True)
shutil.rmtree(os.path.join(APP, "meeting_audio"), ignore_errors=True)

import uvicorn                       # noqa: E402
from app import main as M            # noqa: E402
from app.database import db_session   # noqa: E402
from app import ai_client            # noqa: E402

ai_client.transcribe_available = lambda: True
ai_client.ai_transcribe = lambda path, lang="": (True, "[가짜 변환] " + os.path.basename(path))
ai_client.ai_available = lambda: True
ai_client.ai_extract_meeting = lambda body, context="": (True, {"summary": "핵심: 시험용 가짜 정리",
                                                                "decisions": [], "actions": [], "title": ""})


def fake_get_user(req):
    uid = req.cookies.get("tuser")
    with db_session() as c:
        if uid:
            r = c.execute("SELECT * FROM users WHERE id=?", (int(uid),)).fetchone()
        else:
            r = c.execute("SELECT * FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()
        return dict(r) if r else None


M.get_user = fake_get_user
srv = uvicorn.Server(uvicorn.Config(M.app, host="127.0.0.1", port=PORT, log_level="warning", lifespan="on"))
th = threading.Thread(target=srv.run, daemon=True)
th.start()
for _ in range(300):
    if srv.started:
        break
    time.sleep(0.1)

NOW = time.time()
with db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col in ("name_vi", "name_en", "employee_no", "entity", "phone", "dept_code"):
        if col not in have:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
    row = c.execute("SELECT id FROM teams WHERE name='총괄'").fetchone()
    tid = row[0] if row else c.execute("INSERT INTO teams(name, code) VALUES('총괄','TV1')").lastrowid
    ceo = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET team_id=?, rank='대표이사', role='ceo', name='김정락' WHERE id=?", (tid, ceo))
    staff = c.execute("INSERT INTO users(name, login_id, password, team_id, rank, role, is_active) "
                      "VALUES('안지연','T0086','x',?,'프로','member',1)", (tid,)).lastrowid
    c.execute("DELETE FROM meetings")

    def mtg(key, owner, rec_by=None, secs=0):
        mid = c.execute(
            "INSERT INTO meetings(title, meeting_date, mode, team_id, owner_id, location, tags, attendees_text, body, "
            "summary, audio_path, visibility, status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (f"[시험] {key}", "2026-09-21", "A", tid, owner, "", "", "김정락, 안지연", "", "", "", "all", "draft")).lastrowid
        if rec_by:
            ses = str(1789970000000 + mid * 1000)
            d = os.path.join("meeting_audio", f"meeting_{mid}")
            os.makedirs(d, exist_ok=True)
            part = os.path.join(d, f"rec_{ses}.webm.part").replace("\\", "/")
            with open(part, "wb") as f:
                f.write(b"\x1a\x45\xdf\xa3" + bytes(range(256)) * 12)   # 끊긴 조각(소리 대신 3KB)
            info = {"part": part, "session": ses, "seq": max(1, secs // 10), "bytes": os.path.getsize(part),
                    "secs": secs, "by": rec_by, "by_name": ("김정락" if rec_by == ceo else "안지연"),
                    "started_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(NOW - secs - 90)),
                    "last_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(NOW - 90)), "pending": []}
            c.execute("UPDATE meetings SET rec_state='recording', rec_json=?, mode='B' WHERE id=?",
                      (json.dumps(info, ensure_ascii=False), mid))
        return mid

    mids = {
        "A": mtg("A 아이폰 본인 이어서", staff, staff, 70),      # 안지연 본인 · 묻지 않음 · 정리 순서
        "B": mtg("B 대표가 남의 녹음", staff, staff, 40),         # 대표가 봄 → 묻기
        "K": mtg("K 대표가 남의 녹음 끝내기", staff, staff, 30),  # 대표 「끝내고 정리」 → 묻기
        "C": mtg("C 안드로이드 이어서", ceo, ceo, 50),            # 이어서 녹음 → 녹음기 넘기기
        "G": mtg("G 안드로이드 녹음기 바로", ceo, ceo, 30),       # 상자 두고 녹음기 → 내 녹음 먼저 닫기
        "G2": mtg("G2 안드로이드 남의 녹음 녹음기", staff, staff, 20),  # 남의 녹음은 안 닫는다
        "E": mtg("E PC 이어서", ceo, ceo, 20),
        "F": mtg("F 본인 끝내고 정리", ceo, ceo, 60),
        "H": mtg("H 자동 녹음 착지+열린 녹음", ceo, ceo, 10),
        "N": mtg("N 녹음 없음", ceo),
        "D": mtg("D 마이크 막힘", ceo, ceo, 15),
    }

io.open(os.path.join(HERE, "seed_resume.json"), "w", encoding="utf-8").write(json.dumps(
    {"mids": mids, "ceo": ceo, "staff": staff, "port": PORT, "app": APP}, ensure_ascii=False))
print("READY", PORT, mids, flush=True)
th.join()
