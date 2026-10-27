# -*- coding: utf-8 -*-
"""z1196 시험용 WORKS 서버 — 🗣 통역 대조(음성 메모 · 회의록 · 대표·임원만).
대표 2026-10-27 「통역이 제대로 통역을 했을까?」 → 엑셀 → 화면 시안 → 「음성 메모 + 회의록 둘 다 · 대표·임원만 · 사람이 단추 눌러야 · 이대로 만들어 회귀 통과하면 올리기」
사용: py run_q96_app.py <앱폴더(절대경로)> <포트>

가짜 = 통역 대조 계산의 두 자리만: interp_check._diarize_call(화자 구분 받아쓰기 — 조각 길이에 맞춘 지어낸 발화 · 아는 화자 넘김을 기록) ·
interp_check._chat_json(대조 창 → 지어낸 줄 5개 · 묶음 판정 → 번호 홀짝으로 심각도) · _client 는 빈 객체 · AI 키 비움 ·
진짜 로그인 대신 쿠키 tuser · 이음 주소는 닫힌 포트 · ffmpeg·ffprobe 는 진짜(조각 자르기까지 실제로). 🔒 시험 글은 모두 지어낸 것.
사람: 대표(ceo) · 임원(executive) · 관리자(admin) · 직원(member · 같은 팀)
메모 V1 대표 녹음 30초 · V2 대표 녹음 650초(2조각) · V3 대표 녹음 없음 · V4 직원 녹음 30초 · V5 대표 대조표+이전 있음 · V6 대표 DB 만 running(끊김)
회의 M1 대표 녹음 30초(팀 공개) · M2 직원 비공개 녹음 30초 · M3 대표 녹음 없음
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
APP = sys.argv[1]
PORT = int(sys.argv[2])
os.chdir(APP)
sys.path.insert(0, APP)
os.environ.setdefault("KNK_SECRET_KEY", "verify-only-key")
os.environ["KNK_MESSENGER_SSO_INTERNAL_BASE"] = "http://127.0.0.1:9"
os.environ["KNK_SSO_SERVICE_KEY"] = "q96-test-key"      # 시험용 값(운영 키 아님)
for _k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "KNK_OPENAI_API_KEY"):
    os.environ[_k] = ""
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
for _d in ("data", "meeting_audio", "voice_notes"):
    shutil.rmtree(os.path.join(APP, _d), ignore_errors=True)

import uvicorn                         # noqa: E402
from app import main as M              # noqa: E402
from app import ai_client              # noqa: E402
from app.database import db_session    # noqa: E402
from starlette.responses import PlainTextResponse as _PTR   # noqa: E402
from starlette.responses import JSONResponse as _JR         # noqa: E402

try:
    from app import interp_check as IC   # 새것에만 있다 — 운영 그대로(app_base)엔 없다
except ImportError:
    IC = None

for _r in [r for r in M.app.router.routes if getattr(r, 'path', '') == '/sw.js']:
    M.app.router.routes.remove(_r)


@M.app.get('/sw.js')
async def _sw_noop_for_test():
    return _PTR('/* 시험용 빈 서비스워커 */', media_type='application/javascript')


CALLS = {"diar": [], "chat": []}
FLAG = {"fail_diar": False, "slow": 0, "ai": True, "variant": 1}


class _Resp:
    def __init__(self, segs, usage):
        self.segments = segs
        self.usage = usage


def _dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout.strip()
    return float(out or 0)


def fake_diarize(client, path, names=None, refs=None):
    d = _dur(path)
    CALLS["diar"].append({"sec": round(d), "names": list(names or []), "refs": len(refs or [])})
    if FLAG["fail_diar"]:
        raise RuntimeError("지어낸 받아쓰기 실패(시험)")
    if FLAG["slow"]:
        time.sleep(FLAG["slow"])
    #  지어낸 발화 — A(한국어 · 첫 발화 6초 = 아는 화자감) → D(베트남어로 옮김) → B(베트남어) → D(한국어로 옮김) 되풀이 · 조각 안 시각(0부터)
    pat = [("A", "지어낸 한국어 말 %d 입니다"), ("D", "Lời dịch số %d"), ("B", "Câu trả lời số %d"), ("D", "지어낸 통역 한국어 %d")]
    segs, t, i = [], 0.0, 0
    while t < d - 1:
        sp, tx = pat[i % 4]
        ln = 6.0 if i == 0 else 2.5
        segs.append({"start": round(t, 2), "end": round(min(d, t + ln), 2), "speaker": sp, "text": tx % i})
        t += ln + 0.5
        i += 1
    return _Resp(segs, {"type": "tokens", "input_tokens": int(d * 20), "output_tokens": int(d * 30)})


def fake_chat(client, model, system, user):
    kind = "blk" if "옮겨지지 않은 말 묶음" in system else "cmp"
    CALLS["chat"].append({"model": model, "kind": kind, "n": len(user)})
    v = " v%d" % FLAG["variant"] if FLAG["variant"] != 1 else ""
    if kind == "blk":
        ids = [int(x) for x in re.findall(r"### 묶음 (\d+)", user)]
        return ({"items": [{"id": i, "요지": "지어낸 요지 %d%s" % (i, v), "대상": ("베트남 측에게 한 말" if i % 2 else "한국 측끼리 한 말"),
                            "들었어야": ("예" if i % 2 else "아니오"), "심각도": (2 if i % 2 else 0), "까닭": "지어낸 까닭"} for i in ids]},
                {"prompt": 100, "completion": 50})
    body = user.split("[판정 구간]")[1].split("[뒤 30초")[0] if "[판정 구간]" in user else ""
    lines = re.findall(r"\[(\d+:\d{2})~(\d+:\d{2})\] 화자 (\w+) \(([^)]+)\): (.+)", body)
    A = [x for x in lines if x[2] == "A"]
    B = [x for x in lines if x[2] == "B"]

    def row(x, direction, judge, sev, nature, itxt="", ai=""):
        return {"시작": x[0], "끝": x[1], "방향": direction, "원말_화자": x[2], "원말": x[4], "통역_시작": "", "통역한_말": itxt,
                "AI_독립번역": ai, "판정": judge, "성격": nature, "심각도": sev, "까닭": "지어낸 까닭(%s)%s" % (judge, v)}
    rows = []
    if len(B) > 0:
        rows.append(row(B[0], "VI→KO", "뜻 바뀜", 2, "답변·설명", "지어낸 통역 말", "지어낸 독립 번역"))
    if len(B) > 1:
        rows.append(row(B[1], "VI→KO", "통역 안 함", 2, "답변·설명", "", "지어낸 독립 번역"))
    if len(A) > 0:
        rows.append(row(A[0], "KO→VI", "통역 안 함", 0, "내부 논의", "", "Bản dịch giả định"))
    if len(A) > 1:
        rows.append(row(A[1], "KO→VI", "같음", 0, "지시·요청", "Lời dịch", "지어낸 되돌린 번역"))
    if len(A) > 2:
        rows.append(row(A[2], "KO→VI", "확인 불가", 0, "잡담·맞장구", "", ""))
    return {"rows": rows}, {"prompt": 300, "completion": 120}


if IC is not None:
    IC._diarize_call = fake_diarize
    IC._chat_json = fake_chat
    IC._client = lambda timeout: object()
    _real_available = IC.available
    IC.available = lambda: bool(FLAG["ai"])
ai_client.ai_available = lambda: True
ai_client.transcribe_available = lambda: True
ai_client.ai_chat = lambda *a, **k: (False, "시험 서버 — AI 안 부름")


@M.app.get('/__test/calls')
async def _test_calls():
    return _JR(CALLS)


@M.app.post('/__test/reset')
async def _test_reset():
    CALLS["diar"].clear()
    CALLS["chat"].clear()
    return _JR({"ok": True})


@M.app.post('/__test/flag/{name}/{val}')
async def _test_flag(name: str, val: str):
    if name in ("fail_diar", "ai"):
        FLAG[name] = (val == "1")
    elif name in ("slow", "variant"):
        FLAG[name] = int(val)
    return _JR({"ok": True, "flag": FLAG})


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


def wav(path, secs):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    "sine=frequency=330:sample_rate=16000:duration=%s" % secs, "-ac", "1", path], check=True)


def demo(tag):
    return {"v": 1, "dur": 30.0, "start_clock": "", "n_turns": 2, "interp": "D", "chunks": 1,
            "speakers": [{"id": "D", "role": "통역(추정)", "sec": 10, "n": 2, "ko": 50, "vi": 50, "first": 0.0},
                         {"id": "B", "role": "베트남 측(추정)", "sec": 5, "n": 1, "ko": 0, "vi": 100, "first": 3.0}],
            "turns": [{"s": 0.0, "e": 5.0, "sp": "D", "lang": "ko", "t": "지어낸 통역 말(%s)" % tag}, {"s": 6.0, "e": 9.0, "sp": "B", "lang": "vi", "t": "Câu giả định"}],
            "items": [{"id": 1, "kind": "row", "t": 6.0, "cat": 1, "dir": "VI→KO", "judge": "뜻 바뀜", "sev": 2, "nature": "답변·설명", "sp": "B",
                       "src": "지어낸 원말(%s)" % tag, "isec": None, "itxt": "지어낸 통역", "ai": "지어낸 번역", "why": "지어낸 까닭"}],
            "counts": {"1": [1, 1], "2": [0, 0], "3": [0, 0], "4": [0, 0], "5": [0, 0]}}


BODY = "지어낸 받아쓴 원문입니다. 한국어 말과 Câu tiếng Việt 가 섞여 있습니다."
SUMM = "## 핵심\n지어낸 정리입니다.\n\n## 할 일\n- **지어낸 일** — 담당 · 2026-10-30"
with db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col in ("name_vi", "name_en", "employee_no", "entity", "phone", "dept_code", "lang"):
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s TEXT" % col)
    tcols = {r[1] for r in c.execute("PRAGMA table_info(teams)")}
    if "entity" not in tcols:
        c.execute("ALTER TABLE teams ADD COLUMN entity TEXT")
    ta = c.execute("INSERT INTO teams(name, code, display_order, entity) VALUES('총괄','00',0,'KOR')").lastrowid
    me = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET team_id=?, rank='대표이사', role='ceo', name='김대표', lang='ko', employee_no='1' WHERE id=?", (ta, me))

    def person(login, name, rank, role, no):
        return c.execute("INSERT INTO users(login_id, name, rank, role, team_id, is_active, password, lang, employee_no) "
                         "VALUES(?,?,?,?,?,1,'x-no-login-z1196','ko',?)", (login, name, rank, role, ta, no)).lastrowid
    exe = person("zq96e", "이임원", "상무", "executive", "902")
    adm = person("zq96a", "박관리", "과장", "admin", "903")
    mem = person("zq96m", "김직원", "프로", "member", "904")
    mem2 = person("zq96n", "최다른", "사원", "member", "905")     # 비공개 회의(M2)를 못 보는 사람 — 녹음 Range 권한 시험용
    vcols = {r[1] for r in c.execute("PRAGMA table_info(voice_notes)")}
    HAS = "interp_json" in vcols

    def note(owner, title, secs, **extra):
        nid = c.execute("INSERT INTO voice_notes(owner_id, title, body, summary, audio_path, created_at, updated_at) VALUES(?,?,?,?,?,?,?)",
                        (owner, title, BODY, SUMM, "", "2026-10-27 15:50:00", "2026-10-27 15:50:00")).lastrowid
        if secs:
            p = os.path.join(os.path.abspath(M._VN_DIR), "note_%d" % nid, "rec_1000.wav")
            wav(p, secs)
            c.execute("UPDATE voice_notes SET audio_path=? WHERE id=?", (p.replace("\\", "/"), nid))
        if "meta_when_auto" in vcols:
            c.execute("UPDATE voice_notes SET meta_when=?, meta_when_auto=?, meta_place=? WHERE id=?",
                      ("2026-10-27 (화) 15:06 ~ 15:43 (37분)", "2026-10-27 (화) 15:06 ~ 15:43 (37분)", "지어낸 회의실", nid))
        if HAS and extra:
            c.execute("UPDATE voice_notes SET %s WHERE id=?" % ", ".join("%s=?" % k for k in extra), tuple(extra.values()) + (nid,))
        return nid
    V = {}
    V["V1"] = note(me, "대조 시험 1(지어낸 글)", 30)
    V["V2"] = note(me, "긴 녹음(두 조각)", 650)
    V["V3"] = note(me, "녹음 없음", 0)
    V["V4"] = note(mem, "직원 메모", 30)
    V["V5"] = note(me, "대조표 있음", 30, interp_json=json.dumps(demo("지금"), ensure_ascii=False), interp_at="2026-10-27 10:00:00",
                   interp_prev=json.dumps(demo("이전"), ensure_ascii=False), interp_prev_at="2026-10-27 09:00:00", interp_state="done")
    V["V6"] = note(me, "끊긴 작업", 30, interp_state="running")
    V["V7"] = note(exe, "임원 메모", 30)
    V["V8"] = note(adm, "관리자 메모", 30)
    mcols = {r[1] for r in c.execute("PRAGMA table_info(meetings)")}

    def meeting(owner, title, secs, vis):
        mid = c.execute("INSERT INTO meetings(title, meeting_date, owner_id, team_id, location, body, summary, visibility, status, created_at, updated_at) "
                        "VALUES(?,?,?,?,?,?,?,?,?,?,?)", (title, "2026-10-27", owner, ta, "지어낸 회의실", BODY, SUMM, vis, "done",
                                                          "2026-10-27 15:50:00", "2026-10-27 15:50:00")).lastrowid
        if "msg_started_at" in mcols:
            c.execute("UPDATE meetings SET msg_started_at=? WHERE id=?", ("2026-10-27 09:00:00", mid))
        if secs:
            p = os.path.join(os.path.abspath("meeting_audio"), "m_%d" % mid, "rec_1.wav")
            wav(p, secs)
            c.execute("UPDATE meetings SET audio_path=? WHERE id=?", (p.replace("\\", "/"), mid))
        return mid
    V["M1"] = meeting(me, "회의 대조 시험(지어낸 글)", 30, "team")
    V["M2"] = meeting(mem, "직원 비공개 회의", 30, "private")
    V["M3"] = meeting(me, "녹음 없는 회의", 0, "team")
seed = {"me": me, "exe": exe, "adm": adm, "mem": mem, "mem2": mem2, "port": PORT, "ids": V, "has_cols": HAS, "has_ic": IC is not None,
        "demo_now": demo("지금"), "demo_prev": demo("이전"), "body": BODY, "summary": SUMM}
io.open(os.path.join(HERE, "seed_%d.json" % PORT), "w", encoding="utf-8").write(json.dumps(seed, ensure_ascii=False))
print("READY", PORT, json.dumps({"me": me, "ids": V, "has_cols": HAS, "has_ic": IC is not None}, ensure_ascii=False), flush=True)
th.join()
