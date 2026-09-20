# -*- coding: utf-8 -*-
"""휴대폰 녹음기 「공유 → WORKS」 → 회의록에 붙이고 자동 정리 — 실제 WORKS 앱 종단 검증 (z1117)
실행: 앱 사본 폴더에서  py -3.13 <이 파일>
· OpenAI 음성→글자 = 가짜(받은 파일 이름을 돌려줘 순서를 본다) · 🔴 운영에 닿는 것 없음
"""
import io
import json
import os
import struct
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("KNK_SECRET_KEY", "verify-only-key")
os.environ["KNK_MESSENGER_SSO_INTERNAL_BASE"] = "http://127.0.0.1:9"
for _k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "KNK_OPENAI_API_KEY"):
    os.environ[_k] = ""      # 🔴 시험 서버는 AI 키부터 비운다(2026-09-17 실제 호출 사고)
sys.path.insert(0, os.getcwd())

from fastapi.testclient import TestClient      # noqa: E402
from app import main as M                      # noqa: E402
from app import ai_client as AI                # noqa: E402
from app.database import db_session            # noqa: E402

OK = FAIL = 0
FAILS = []


def chk(cond, name, extra=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  [PASS] {name}" + (f" · {extra}" if extra != "" else ""))
    else:
        FAIL += 1
        FAILS.append(name)
        print(f"  [FAIL] {name} {extra}")


SEEN = []


def fake_transcribe(path, lang=""):
    SEEN.append(os.path.basename(path))
    return (True, f"<{os.path.splitext(os.path.basename(path))[0]} 내용>")


AI.transcribe_available = lambda: True
AI.ai_transcribe = fake_transcribe
AI.ai_available = lambda: True
AI.ai_extract_meeting = lambda body, context="": (True, {"summary": "핵심: 가짜", "decisions": [], "actions": [], "title": ""})

client = TestClient(M.app, base_url="https://testserver")
client.__enter__()
with db_session() as _c:
    _have = {r[1] for r in _c.execute("PRAGMA table_info(users)")}
    for _col in ("name_vi", "name_en", "employee_no", "entity", "phone", "dept_code"):
        if _col not in _have:
            _c.execute(f"ALTER TABLE users ADD COLUMN {_col} TEXT")
with db_session() as c:
    CEO = dict(c.execute("SELECT * FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone())
    c.execute("UPDATE users SET role='ceo' WHERE id=?", (CEO["id"],))
    CEO["role"] = "ceo"
    _o = c.execute("SELECT * FROM users WHERE id<>? AND is_active=1 ORDER BY id LIMIT 1", (CEO["id"],)).fetchone()
    OTHER = dict(_o) if _o else None
    if OTHER:
        c.execute("UPDATE users SET role='member' WHERE id=?", (OTHER["id"],))
        OTHER["role"] = "member"
    MIDS = [c.execute(
        "INSERT INTO meetings(title, meeting_date, mode, owner_id, location, tags, attendees_text, body, summary, "
        "audio_path, visibility, status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (f"[시험] 공유 {i}", "2026-09-20", "A", CEO["id"], "", "", "", "", "", "", "all", "draft")).lastrowid
        for i in range(4)]

WHO = {"u": CEO}
M.get_user = lambda req: WHO["u"]


def wav(secs=1):
    rate = 8000
    data = b"".join(struct.pack("<h", 0) for _ in range(rate * secs))
    return (b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt "
            + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
            + b"data" + struct.pack("<I", len(data)) + data)


def share(fname="회의녹음 001.m4a", body=None, field="audio"):
    return client.post("/share/audio", files={field: (fname, body if body is not None else wav(), "audio/mp4")})


def row(mid):
    with db_session() as c:
        return dict(c.execute("SELECT * FROM meetings WHERE id=?", (mid,)).fetchone())


def pend(mid):
    return M._rec_info(row(mid)).get("pending") or []


print("\n■ ① 앱 설정(manifest) — 공유 목록에 WORKS 가 뜨게")
r = client.get("/manifest.webmanifest")
j = r.json()
chk(r.status_code == 200, "manifest 200")
stg = j.get("share_target") or {}
chk(bool(stg), "share_target 칸이 있다", list(stg))
chk(stg.get("action") == "/share/audio", "받는 주소 = /share/audio", stg.get("action"))
chk(stg.get("method") == "POST" and stg.get("enctype") == "multipart/form-data", "POST · multipart", stg)
_p = ((stg.get("params") or {}).get("files") or [{}])[0]
chk(_p.get("name") == "audio" and "audio/*" in (_p.get("accept") or []), "음성 파일만 받는다", _p)
chk(j.get("scope") == "/" and j.get("start_url") == "/app", "기존 칸은 그대로", (j.get("scope"), j.get("start_url")))

print("\n■ ② 공유로 받기")
r = share()
chk(r.status_code == 200, "공유 받기 200", r.status_code)
html = r.text
chk("회의녹음 001.m4a" in html, "받은 파일 이름이 보인다")
tok = ""
for line in html.splitlines():
    if "var TOKEN" in line:
        tok = line.split('"')[1] if '"' in line else ""
chk(tok.startswith("s_%d_" % CEO["id"]), "표(token)가 내려온다 · 내 번호를 품는다", tok)
_staged = [f for f in os.listdir(M._SHARE_DIR)] if os.path.isdir(M._SHARE_DIR) else []
chk(any(f.startswith(tok) for f in _staged), "파일이 잠시 보관된다", _staged[:3])
chk("어디에 붙일까요" in html and "새 회의록으로 정리" in html, "붙일 곳 고르는 칸이 있다")
chk(("[시험] 공유 0" in html), "고칠 수 있는 최근 회의가 보인다")

print("\n■ ③ 잘못 온 것 거르기")
r2 = client.post("/share/audio", files={"audio": ("메모.txt", b"hello world", "text/plain")})
chk(r2.status_code == 200 and "지원하지 않는 음성 형식" in r2.text, "음성이 아니면 안 받는다")
r3 = client.post("/share/audio", data={"title": "그냥 글"})
chk(r3.status_code == 200 and "음성 파일이 오지 않았습니다" in r3.text, "파일이 없으면 안내")
r4 = client.post("/share/audio", files={"audio": ("빈.m4a", b"x" * 10, "audio/mp4")})
chk(r4.status_code == 200 and "음성 파일이 오지 않았습니다" in r4.text, "빈/손상 파일은 안 받는다")
_save = M.get_user
M.get_user = lambda req: None
r5 = share()
chk(r5.status_code == 401 and "로그인이 풀려" in r5.text, "로그인 안 됐으면 401 + 다시 공유 안내", r5.status_code)
chk("휴대폰에 그대로 있습니다" in r5.text, "녹음은 휴대폰에 남아 있다고 알린다")
M.get_user = _save

print("\n■ ④ 그 회의록에 붙이기 → 자동 정리로 이어짐")
M1 = MIDS[0]
before = len(pend(M1))
r = client.post(f"/api/meeting/{M1}/attach-share", json={"token": tok})
j = r.json()
chk(r.status_code == 200 and j.get("ok") and j.get("id") == M1, "붙이기 성공", j)
chk(len(pend(M1)) == before + 1, "'아직 글자로 안 바꾼 녹음'에 들어갔다", pend(M1))
chk((row(M1).get("audio_path") or "").startswith(f"meeting_audio/meeting_{M1}/"), "그 회의 폴더로 옮겨졌다",
    row(M1).get("audio_path"))
chk(row(M1).get("mode") == "B", "음성 회의로 표시")
chk(not [f for f in os.listdir(M._SHARE_DIR) if f.startswith(tok)], "보관함에서 비워졌다")
r = client.post(f"/api/meeting/{M1}/attach-share", json={"token": tok})
chk(r.status_code == 404, "같은 표로 두 번은 못 붙인다", r.status_code)

SEEN.clear()
r = client.post(f"/api/meeting/{M1}/transcribe", json={})
chk(r.status_code == 200 and r.json().get("ok"), "정리 시작")
for _ in range(80):
    if (M._STT_JOBS.get(M1) or {}).get("state") in ("done", "error"):
        break
    time.sleep(0.1)
chk((M._STT_JOBS.get(M1) or {}).get("state") == "done", "정리 끝", M._STT_JOBS.get(M1))
chk(len(SEEN) == 1 and SEEN[0].startswith("rec_"), "공유로 받은 파일이 글자로 바뀌었다", SEEN)
chk("내용>" in (row(M1).get("body") or ""), "본문에 들어갔다", (row(M1).get("body") or "")[:40])

print("\n■ ⑤ 「＋ 새 회의록으로 정리」")
tok2 = ""
r = share("회의녹음 002.m4a")
for line in r.text.splitlines():
    if "var TOKEN" in line:
        tok2 = line.split('"')[1] if '"' in line else ""
r = client.post("/api/meeting/share-new", json={"token": tok2})
j = r.json()
chk(r.status_code == 200 and j.get("ok") and j.get("id"), "새 회의록을 만들고 붙였다", j)
NEW = j.get("id")
nr = row(NEW)
chk(nr.get("owner_id") == CEO["id"], "내가 주인")
chk(nr.get("mode") == "B" and (nr.get("audio_path") or ""), "음성 회의로 붙었다", nr.get("audio_path"))
chk("제목 없는 회의" in (nr.get("title") or ""), "제목은 비워 둔다(AI 가 짓는다)", nr.get("title"))
chk(len(pend(NEW)) == 1, "정리 대기에 들어갔다", pend(NEW))

print("\n■ ⑥ 남의 녹음은 못 집는다 · 권한")
tok3 = ""
r = share("남의녹음.m4a")
for line in r.text.splitlines():
    if "var TOKEN" in line:
        tok3 = line.split('"')[1] if '"' in line else ""
if OTHER:
    # 남의 회의록이면 권한(403)에서 막히고, 자기 회의록이라도 '남의 표'는 못 집는다(404)
    with db_session() as c:
        HIS = c.execute(
            "INSERT INTO meetings(title, meeting_date, mode, owner_id, location, tags, attendees_text, body, "
            "summary, audio_path, visibility, status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            ("[시험] 남의 회의", "2026-09-20", "A", OTHER["id"], "", "", "", "", "", "", "team", "draft")).lastrowid
    WHO["u"] = OTHER
    r = client.post(f"/api/meeting/{MIDS[1]}/attach-share", json={"token": tok3})
    chk(r.status_code in (403, 404), "다른 사람은 못 붙인다(남의 회의록 = 권한)", r.status_code)
    r = client.post(f"/api/meeting/{HIS}/attach-share", json={"token": tok3})
    chk(r.status_code == 404, "🔴 자기 회의록이어도 '남의 표'는 못 집는다", r.status_code)
    r = client.post("/api/meeting/share-new", json={"token": tok3})
    chk(r.status_code == 404, "새 회의록으로도 못 가져간다", r.status_code)
    WHO["u"] = CEO
    chk(os.path.exists(M._share_find(tok3, CEO["id"])), "내 녹음은 그대로 남아 있다")
else:
    for _i in range(4):
        chk(True, "(다른 사용자 없음 — 건너뜀)")
for bad in ("", "../../etc/passwd", "s_999_1_aaaaaaaa", "s_%d_1_zz" % CEO["id"], "s_%d_1_../x" % CEO["id"]):
    r = client.post(f"/api/meeting/{MIDS[1]}/attach-share", json={"token": bad})
    chk(r.status_code == 404, f"이상한 표는 거절: {bad!r}", r.status_code)
r = client.post("/api/meeting/99999/attach-share", json={"token": tok3})
chk(r.status_code == 404, "없는 회의록 404", r.status_code)

print("\n■ ⑦ 보관함 치우기")
_old = os.path.join(M._SHARE_DIR, "s_%d_1_deadbeef.m4a" % CEO["id"])
io.open(_old, "wb").write(b"x" * 200)
os.utime(_old, (time.time() - 40 * 3600, time.time() - 40 * 3600))
M._share_sweep()
chk(not os.path.exists(_old), "하루 지난 것은 저절로 치워진다")
_fresh = os.path.join(M._SHARE_DIR, "s_%d_1_cafebabe.m4a" % CEO["id"])
io.open(_fresh, "wb").write(b"x" * 200)
M._share_sweep()
chk(os.path.exists(_fresh), "방금 것은 안 치운다")
os.remove(_fresh)

print("\n■ ⑧ 기존 길은 그대로(회귀)")
r = client.post(f"/api/meeting/{MIDS[2]}/audio", files={"file": ("rec.webm", wav(), "audio/webm")})
chk(r.status_code == 200 and r.json().get("ok"), "평소 음성 올리기 그대로", r.status_code)
chk(len(pend(MIDS[2])) == 1, "평소 올리기도 정리 대기에 들어간다", pend(MIDS[2]))
r = client.get("/meetings")
chk(r.status_code == 200, "회의록 목록 200")
r = client.get(f"/meetings/{MIDS[2]}")
chk(r.status_code == 200, "회의록 상세 200")

print("\n" + "=" * 68)
print(f"합계: 통과 {OK} · 실패 {FAIL}")
for n in FAILS:
    print("  ❌ " + n)
print("=" * 68)
sys.exit(1 if FAIL else 0)
