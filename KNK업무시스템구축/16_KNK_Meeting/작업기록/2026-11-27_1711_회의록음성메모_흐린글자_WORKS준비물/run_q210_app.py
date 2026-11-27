# -*- coding: utf-8 -*-
"""z1210 시험용 WORKS 서버 — 회의록·음성 메모 화면 흐린 글자 재기 (대표 2026-11-27 「진행해」 · 스킬 knk-text-contrast)
q206(음성 메모)·q207(회의록 링크)·q93(한눈에 보기) 시험 서버를 합쳐 줄인 판.
사용: py -3.13 run_q210_app.py <앱폴더(절대경로)> <포트>
· AI 키 비움(AI 단추는 보이게 ai_available=True · 실제 호출 없음) · 진짜 로그인 대신 쿠키 tuser · 이음 주소는 닫힌 포트
· 🔒 시험 글·사람 이름은 모두 지어낸 것(가상 명부). 실제 직원·대화방 자료 쓰지 않음.
· ⚠ 앱 폴더의 data/ · meeting_audio/ · voice_notes/ 를 지우고 새로 만든다 — 같은 앱 폴더에 서버 둘을 띄우지 말 것.
"""
import io
import json
import os
import shutil
import struct
import sys
import threading
import time
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
APP = sys.argv[1]
PORT = int(sys.argv[2])
os.chdir(APP)
sys.path.insert(0, APP)
os.environ.setdefault("KNK_SECRET_KEY", "verify-only-key")
os.environ["KNK_MESSENGER_SSO_INTERNAL_BASE"] = "http://127.0.0.1:9"
os.environ["KNK_SSO_SERVICE_KEY"] = "q210-test-key"      # 시험용 값(운영 키 아님)
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

for _r in [r for r in M.app.router.routes if getattr(r, 'path', '') == '/sw.js']:
    M.app.router.routes.remove(_r)


@M.app.get('/sw.js')
async def _sw_noop_for_test():
    return _PTR('/* 시험용 빈 서비스워커 */', media_type='application/javascript')


ai_client.ai_available = lambda: True
ai_client.transcribe_available = lambda: True
ai_client.ai_chat = lambda *a, **k: (False, "시험 서버: AI 호출 없음")


def fake_get_user(req):
    uid = req.cookies.get("tuser")
    if not uid:
        return None
    with db_session() as c:
        r = c.execute("SELECT * FROM users WHERE id=?", (int(uid),)).fetchone()
        return dict(r) if r else None


M.get_user = fake_get_user


def wav(path, secs):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    w = wave.open(path, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000)
    w.writeframes(struct.pack("<h", 0) * 8000 * secs)
    w.close()


srv = uvicorn.Server(uvicorn.Config(M.app, host="127.0.0.1", port=PORT, log_level="warning", lifespan="on"))
th = threading.Thread(target=srv.run, daemon=True)
th.start()
for _ in range(300):
    if srv.started:
        break
    time.sleep(0.1)

SUMM = "\n".join([
    "## 핵심",
    "포장 설비의 부품 입고 지연과 출하 차수 변경으로 일정이 흔들린 원인을 점검했다(지어낸 정리).",
    "",
    "## 자재 지연과 일정 변동",
    "- 이번 일정 지연의 가장 큰 원인은 지급품 입고 지연이었다.",
    "  - 장납기 부품은 **확정 입고 일정**이 공유되지 않았다.",
    "- [결정] 자재 시트에 **입고 예정일과 실제 입고일을 분리**해 기록한다.",
    "- [제안] 매주 목요일 오전 10시에 자재 회의를 연다.",
    "- [미결] 셋업 시작일 — 고객사 확인 필요",
    "- [확인 필요] 전원 용량 380V",
    "1. 다음 회의는 팀장 참석으로 진행한다.",
])
BODY = ("지어낸 받아쓴 원문입니다. 팀장이 업체에 확인한다고 했습니다. 26대분은 6대 먼저 나가고 126대분은 내년입니다. "
        "지급품이 늦었다고 합니다. 다시 묻기로 했습니다.")
VI_SUM = ("## Trọng tâm\nKiểm tra máy số 2 vào tuần sau (giả định).\n\n"
          "## Kế hoạch\n- [Quyết định] Đưa máy số 2 vào lúc **9 giờ**\n- [Đề xuất] Thêm 2 người chạy thử\n"
          "- [Chưa quyết] Thuê xe nâng 3 tấn\n\n## Việc cần làm\n- **Kiểm tra điện** — Nguyen Van A · 2026-11-05")
VIZ = {
    "kind": "equip", "headline": "2호기 출하 일정과 셋업 순서를 정했다(지어낸 그림)", "headline_q": "",
    "numbers": [{"v": "11월 20일", "label": "출하", "q": "26대분은 6대 먼저"},
                {"v": "카메라 2대", "label": "추가 요청", "q": ""},
                {"v": "25일", "label": "셋업 시작", "q": ""}],
    "flow": {"zones": [
        {"name": "투입", "note": "제품 투입", "steps": [{"label": "제품 투입", "sub": "작업자", "type": "in", "warn": "", "q": ""}]},
        {"name": "검사", "note": "검사 프로그램", "steps": [
            {"label": "검사 프로그램", "sub": "고친 판으로 한 번 더", "type": "insp", "warn": "오류 부분 재확인", "q": ""},
            {"label": "판정", "sub": "OK/NG", "type": "judge", "warn": "", "q": ""}]},
        {"name": "출하", "note": "포장 → 출하", "steps": [{"label": "포장", "sub": "전날까지", "type": "step", "warn": "", "q": ""},
                                                 {"label": "출하", "sub": "11월 20일", "type": "out", "warn": "", "q": ""}]}],
        "loop": {"label": "빈 트레이 회수", "from": "출하", "to": "투입"}},
    "decided": [{"t": "[결정] 출하는 11월 20일 · 포장은 전날까지", "q": "지급품이 늦었다"},
                {"t": "(내부 방침) 조명 교체는 원가 계산 뒤 다음 회의에서", "q": ""}],
    "open": [{"t": "[확인 필요] 셋업 시작일 — 고객사 확인", "q": ""}],
    "todo": [{"t": "카메라 추가의 납기 영향 확인", "who": "기술팀", "due": "2026-10-24", "q": ""},
             {"t": "부품 단가 거래처 재협의", "who": "구매팀", "due": "25일", "q": ""}],
    "timeline": [{"when": "10-27 (화)", "t": "다음 회의 오전 열 시", "sure": True, "q": ""},
                 {"when": "11-20", "t": "출하", "sure": True, "q": ""},
                 {"when": "11-25", "t": "셋업 시작", "sure": False, "q": ""}],
    "parts": [{"what": "카메라", "spec": "2대 추가", "note": "납기 영향 확인", "q": ""}],
}

with db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col in ("name_vi", "name_en", "employee_no", "entity", "phone", "dept_code", "lang"):
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s TEXT" % col)
    tcols = {r[1] for r in c.execute("PRAGMA table_info(teams)")}
    if "entity" not in tcols:
        c.execute("ALTER TABLE teams ADD COLUMN entity TEXT")
    MCOLS = {r[1] for r in c.execute("PRAGMA table_info(meetings)")}
    VCOLS = {r[1] for r in c.execute("PRAGMA table_info(voice_notes)")}
    ta = c.execute("INSERT INTO teams(name, code, display_order, entity) VALUES('총괄','00',0,'KOR')").lastrowid
    tb = c.execute("INSERT INTO teams(name, code, display_order, entity) VALUES('빈팀(시험)','Q210',99,'KOR')").lastrowid
    me = c.execute("SELECT id FROM users WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET team_id=?, rank='대표이사', role='ceo', name='오가상', lang='ko', employee_no='1' WHERE id=?", (ta, me))

    def person(login, name, rank, role, team, lang, no):
        return c.execute("INSERT INTO users(login_id, name, rank, role, team_id, is_active, password, lang, employee_no) "
                         "VALUES(?,?,?,?,?,1,'x-no-login-z1210',?,?)", (login, name, rank, role, team, lang, no)).lastrowid
    mem = person("zq210m", "윤가상", "프로", "member", ta, "ko", "904")
    vi = person("zq210v", "Nguyen Van A", "사원", "member", ta, "vi", "VN901")
    emp = person("zq210e", "한빈칸", "프로", "member", tb, "ko", "908")       # 다른 팀 · 회의·메모 없음 = 빈 목록

    def meeting(title, summ, body, vis="team", **extra):
        mid = c.execute("INSERT INTO meetings(title, meeting_date, owner_id, team_id, location, body, summary, visibility, status, "
                        "attendees_text, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                        (title, "2026-11-27", me, ta, "지어낸 회의실", body, summ, vis, "done", "윤가상",
                         "2026-11-27 10:00:00", "2026-11-27 10:00:00")).lastrowid
        try:
            M._meeting_link_attendees(c, mid, "윤가상")
        except Exception as e:
            print("참석자 연결 생략:", type(e).__name__, flush=True)
        if "msg_started_at" in MCOLS:
            c.execute("UPDATE meetings SET msg_started_at=?, ended_at=? WHERE id=?", ("2026-11-27 14:00:27", "2026-11-27 14:50:28", mid))
        for k, v in extra.items():
            if k in MCOLS:
                c.execute("UPDATE meetings SET %s=? WHERE id=?" % k, (v, mid))
        return mid
    V = {}
    V["M1"] = meeting("자재 입고 점검 회의(지어낸 글)", SUMM, BODY,
                      viz_json=json.dumps(VIZ, ensure_ascii=False), viz_at="2026-11-27 11:00:00", viz_kind="equip",
                      viz_sum_sig=M._viz_sig(SUMM) if hasattr(M, "_viz_sig") else "")
    V["M2"] = meeting("정리 없는 회의(지어낸 글)", "", "원문만 있다(지어낸 글)")
    V["M3"] = meeting("비공개 회의(지어낸 글)", "## 핵심\n비공개 지어낸 정리", "비공개 원문", vis="private")
    wav(os.path.join(os.path.abspath("meeting_audio"), "m_%d" % V["M1"], "rec_1.wav"), 5)
    c.execute("UPDATE meetings SET audio_path=? WHERE id=?",
              (os.path.join(os.path.abspath("meeting_audio"), "m_%d" % V["M1"], "rec_1.wav").replace("\\", "/"), V["M1"]))
    c.execute("INSERT INTO meeting_decisions(meeting_id, who, what, due, source) VALUES(?,?,?,?,'ai')",
              (V["M1"], "윤가상", "입고 일정표를 매주 공유한다(지어낸 결정)", ""))
    c.execute("INSERT INTO meeting_decisions(meeting_id, who, what, due, source) VALUES(?,?,?,?,'ai')",
              (V["M1"], "", "자재 시트에 지급품 구분을 적는다", "2026-12-20"))
    c.execute("INSERT INTO meeting_actions(meeting_id, assignee_name, task, due_date, source) VALUES(?,?,?,?,'ai')",
              (V["M1"], "윤가상", "업체 입고 일정 다시 확인(지어낸 할 일)", "2026-12-05"))
    c.execute("INSERT INTO meeting_actions(meeting_id, assignee_name, task, due_date, source) VALUES(?,?,?,?,'ai')",
              (V["M1"], "", "담당 없는 할 일(지어낸)", ""))

    def note(owner, title, summ, body, secs):
        nid = c.execute("INSERT INTO voice_notes(owner_id, title, body, summary, audio_path, created_at, updated_at) VALUES(?,?,?,?,?,?,?)",
                        (owner, title, body, summ, "", "2026-11-27 15:50:00", "2026-11-27 15:50:00")).lastrowid
        if secs:
            p = os.path.join(os.path.abspath(M._VN_DIR), "note_%d" % nid, "rec_1000.wav")
            wav(p, secs)
            c.execute("UPDATE voice_notes SET audio_path=? WHERE id=?", (p.replace("\\", "/"), nid))
        if "meta_when" in VCOLS:
            c.execute("UPDATE voice_notes SET meta_when=?, meta_place=? WHERE id=?",
                      ("2026-11-27 (금) 15:06 ~ 15:43 (37분)", "지어낸 회의실", nid))
        return nid
    V["V1"] = note(me, "정리 있는 메모(지어낸 글)", SUMM, BODY, 5)
    V["V2"] = note(me, "정리 없는 메모(지어낸 글)", "", BODY, 5)
    V["V3"] = note(me, "", "", "", 0)
    V["VI1"] = note(vi, "Kiểm tra máy số 2", VI_SUM, "Tuần sau kiểm tra máy số 2. (giả định)", 5)
    V["VI2"] = note(vi, "", "", "Tuần sau kiểm tra máy số 2. (giả định)", 0)
seed = {"me": me, "mem": mem, "vi": vi, "emp": emp, "port": PORT, "ids": V}
io.open(os.path.join(HERE, "seed_%d.json" % PORT), "w", encoding="utf-8").write(json.dumps(seed, ensure_ascii=False))
print("READY", PORT, json.dumps(seed, ensure_ascii=False), flush=True)
th.join()
