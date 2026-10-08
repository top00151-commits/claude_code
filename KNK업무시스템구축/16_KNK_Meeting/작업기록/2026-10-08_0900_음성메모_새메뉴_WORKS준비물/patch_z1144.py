# -*- coding: utf-8 -*-
"""z1144 — 🎙 음성 메모 (대표 지시 2026-10-08)
  「회의록 말고 일반적인 의견 내용을 녹음한 걸 정리해주는 것도 필요해」

대표 결정: 쓰임새 네 가지 모두 · 새 목록 「🎙 음성 메모」 · 전 직원 · **내 것만 보임**

고치는 것
  ① ai_client.py  : ai_extract_note() — 회의용과 **다른 정리 틀**(요점·할 일 · 안건/결정사항 없음)
  ② main.py       : 표 만들기 호출 · _stt_one 에 진행알림 갈아끼우기 · 음성 메모 화면·API 한 묶음
  ③ chrome.html   : 왼쪽 메뉴 「🎙 음성 메모」

🔴 기준점에 역슬래시를 쓰지 않는다(셸을 거치면 뭉개진다) — 넣을 코드의 역슬래시는 chr(92)로 만든다.
"""
import io
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
BS = chr(92)
N = BS + "n"          # 넣을 코드 안의 줄바꿈 escape


def load(n):
    return io.open(os.path.join(OUT, n), encoding="utf-8").read()


def save(n, t):
    p = os.path.join(OUT, n)
    data = t.encode("utf-8")
    with open(p + ".tmp", "wb") as f:
        f.write(data)
    os.replace(p + ".tmp", p)


def sub(t, old, new, label):
    c = t.count(old)
    assert c == 1, "%s: %d건 (1건이어야 함)" % (label, c)
    return t.replace(old, new)


# ═══════════════════════ ① ai_client.py ═══════════════════════
a = load("ai_client.py")
assert "ai_extract_note" not in a, "ai_client 이미 패치됨"

NOTE_BLOCK = '''

# ── 🎙 음성 메모 정리 (z1144 · 대표 지시 2026-10-08) ─────────────────────────
#   회의가 아니다 — 혼자 말한 생각·전화 통화·현장 메모·말로 하는 보고.
#   🔴 회의용 틀(안건·결정사항·참석자 귀속)을 씌우면 **없는 결정을 지어내거나 빈칸만** 나온다.
#      그래서 요점·할 일만 뽑는 **다른 틀**을 쓴다.
_NOTE_EXTRACT_SYSTEM = (
    "당신은 KNK 사내 AI 빅터입니다. 사람이 혼자 말한 녹음(회의가 아님)을 글자로 바꾼 원문을 읽고 "
    "짧고 쓸모 있게 정리한다.@@N@@"
    "출력 규칙:@@N@@"
    "- summary: 아래 형식(한국어, 여러 줄). 해당 없는 묶음은 통째로 뺀다.@@N@@"
    "    요점@@N@@"
    "    - <한 줄씩 · 말한 순서대로>@@N@@"
    "    할 일@@N@@"
    "    - <무엇을> — <누가/언제까지 · 원문에 나온 것만>@@N@@"
    "    나온 이름·회사·날짜@@N@@"
    "    - <원문에 나온 것만 그대로>@@N@@"
    "  @@RED@@ 안건·결정사항·참석자별 발언 귀속은 만들지 않는다(혼자 말한 것이다).@@N@@"
    "- title: 이 메모에 어울리는 짧은 제목(공백 포함 20자 이내). "
    "반드시 원문에 나온 말로만 짓는다(창작 금지). 지을 수 없으면 \\"\\".@@N@@"
    "- 절대 추측·창작 금지. 원문에 없는 내용을 지어내지 않는다. 말이 짧으면 정리도 짧게.@@N@@"
    "출력은 오직 아래 JSON 한 개. 마크다운 코드펜스·설명·인사말 금지.@@N@@"
    \'{"title":"","summary":""}\'
)


def ai_extract_note(body: str) -> tuple[bool, dict]:
    """🎙 음성 메모 원문 → {"summary", "title"} (z1144).
    회의용 ai_extract_meeting 과 **틀이 다르다**(안건·결정사항 없음).
    「우리 회사 말」 바로잡기(meeting_terms)는 회의록과 **같은 한 벌**을 쓴다."""
    empty = {"summary": "", "title": ""}
    if not body or not body.strip():
        return (True, dict(empty))
    system = _NOTE_EXTRACT_SYSTEM + "@@N@@@@N@@" + _KNK_MEETING_CONTEXT
    _terms = meeting_terms()
    if _terms:
        system += ("@@N@@@@N@@[우리 회사 말 — 음성 변환이 흔히 틀리는 말]@@N@@" + _terms
                   + "@@N@@@@RED@@ 위 말이 원문에 비슷하게 들어 있으면 그 말로 바로잡는다. "
                     "원문에 없는 말은 절대 넣지 않는다.")
    ok, resp = ai_chat(body.strip(), system=system, max_tokens=1500, temperature=0.1)
    if not ok:
        return (False, {"error": resp, **empty})
    data = _parse_json_loose(resp)
    if not isinstance(data, dict):
        return (False, {"error": "AI 응답을 정리 형식(JSON)으로 해석하지 못했습니다.", **empty})
    return (True, {
        "summary": str(data.get("summary", "") or "").strip(),
        "title": str(data.get("title", "") or "").strip()[:60],
    })

'''
NOTE_BLOCK = NOTE_BLOCK.replace("@@N@@", N).replace("@@RED@@", BS + "U0001F534")
a = sub(a,
        "\n\n# ── 음성→글자 (16_KNK_Meeting 모드 B 음성 회의) ─",
        NOTE_BLOCK + "\n# ── 음성→글자 (16_KNK_Meeting 모드 B 음성 회의) ─",
        "음성 메모 정리 함수 자리")
save("ai_client.py", a)
print("① ai_client.py — ai_extract_note 추가")

# ═══════════════════════ ② main.py ═══════════════════════
m = load("main.py")
assert "voice_notes" not in m, "main 이미 패치됨"

# ②-1 표 만들기 호출(기동 때 1회)
m = sub(m,
        '''    except Exception as _e:
        print(f"[MEETING-END-MIG-Z1131 ERR] {_e}")''',
        '''    except Exception as _e:
        print(f"[MEETING-END-MIG-Z1131 ERR] {_e}")
    # z1144 (대표 지시 2026-10-08): 🎙 음성 메모 — voice_notes 새 표 (idempotent)
    try:
        from .migrations.m_z1144_voice_note import migrate as _vn_migrate
        from .database import DB_PATH as _DB_PATH_VN
        _rvn = _vn_migrate(_DB_PATH_VN)
        if _rvn.get('added'):
            print(f"[VOICE-NOTE-MIG-Z1144] {_rvn}")
    except Exception as _e:
        print(f"[VOICE-NOTE-MIG-Z1144 ERR] {_e}")''',
        "표 만들기 호출")

# ②-2 _stt_one 에 진행알림을 갈아끼울 수 있게 (회의록은 그대로)
m = sub(m,
        '''def _stt_one(mid: int, disk: str, lang: str, head: str = ""):''',
        '''def _stt_one(mid: int, disk: str, lang: str, head: str = "", progress=None):''',
        "_stt_one 서명")
m = sub(m,
        '''    반환 (글, 오류, 경고) — 오류가 있으면 글은 비어 있다(반쪽 회의록 방지)."""
    import shutil as _sh''',
        '''    반환 (글, 오류, 경고) — 오류가 있으면 글은 비어 있다(반쪽 회의록 방지).
    progress: 진행 글을 적을 함수(없으면 회의록 쪽 _stt_progress). z1144 에서 🎙 음성 메모가
      **같은 알맹이 한 벌**을 쓰려고 갈아끼운다 — 두 벌이 되면 한쪽만 고치는 사고가 난다."""
    import shutil as _sh
    _pg = progress if callable(progress) else (lambda _t: _stt_progress(mid, _t))''',
        "_stt_one 설명·진행함수")
m = sub(m,
        '''            _stt_progress(mid, head + "긴 음성을 줄여서 20분씩 나누는 중")''',
        '''            _pg(head + "긴 음성을 줄여서 20분씩 나누는 중")''',
        "진행알림 1")
m = sub(m,
        '''                    _stt_progress(mid, head + f"{n}개 구간 중 {i}번째")''',
        '''                    _pg(head + f"{n}개 구간 중 {i}번째")''',
        "진행알림 2")

# ②-3 음성 메모 한 묶음
VN = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "vn_block.py"),
             encoding="utf-8").read()
m = sub(m,
        '''# ════════════════════════════════════════════════════════════════════════
#  회의 알림(이음 메신저) ↔ 회의록 연결''',
        VN + '''# ════════════════════════════════════════════════════════════════════════
#  회의 알림(이음 메신저) ↔ 회의록 연결''',
        "음성 메모 묶음 자리")
save("main.py", m)
print("② main.py — 표 만들기·_stt_one 공용화·음성 메모 묶음")

# ═══════════════════════ ③ chrome.html ═══════════════════════
h = load("chrome.html")
assert "voice-notes" not in h, "chrome 이미 패치됨"
h = sub(h,
        "'/search','/meetings','/admin','/admin/permissions'] %}",
        "'/search','/meetings','/voice-notes','/admin','/admin/permissions'] %}",
        "메뉴 활성 표시 목록")
h = sub(h,
        "  {{ a('/meetings',      '📋 회의록',      'M-00-17') }}",
        "  {{ a('/meetings',      '📋 회의록',      'M-00-17') }}\n"
        "  {# z1144(대표 지시 2026-10-08): 회의가 아닌 녹음도 정리 — 내 것만 보인다 #}\n"
        "  {{ a('/voice-notes',   '🎙 음성 메모',   'M-00-26') }}",
        "메뉴 줄")
save("chrome.html", h)
print("③ chrome.html — 왼쪽 메뉴 「🎙 음성 메모」")
print("끝")
