# -*- coding: utf-8 -*-
"""z1142 — 회의록 「정리」가 음성 변환 오타를 우리 회사 말로 바로잡게 한다 (대표 지시 2026-10-07 「해봐」)
  ① ai_client  : 용어 목록을 정리 프롬프트에 함께 보냄(관리자가 고칠 수 있음)
  ② main.py    : 관리자 AI 설정에서 읽고·저장
  ③ 화면 HTML  : 적는 칸 + 안내문
🔴 원문(받아쓴 글)은 건드리지 않는다 — 정리 글에서만 바로잡는다.
🔴 기준점에 역슬래시를 쓰지 않는다(셸을 거치면 뭉개진다) — 넣을 코드의 역슬래시는 chr(92)로 만든다."""
import io
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
BS = chr(92)
N = BS + "n"          # 넣을 코드 안의 \n
RED = BS + "U0001F534"  # 넣을 코드 안의 🔴 (서로게이트 쌍 금지)


def load(n):
    return io.open(os.path.join(OUT, n), encoding="utf-8").read()


def save(n, t):
    p = os.path.join(OUT, n)
    data = t.encode("utf-8")          # 먼저 인코딩(실패해도 원본 안 깨짐)
    with open(p + ".tmp", "wb") as f:
        f.write(data)
    os.replace(p + ".tmp", p)


def sub(t, old, new, label):
    n = t.count(old)
    assert n == 1, "%s: %d건 (1건이어야 함)" % (label, n)
    return t.replace(old, new)


# ─────────────────────────── ① ai_client.py ───────────────────────────
a = load("ai_client.py")
assert "_MEETING_TERMS_DEFAULT" not in a, "ai_client 이미 패치됨"

TERMS_BLOCK = '''# z1142 (대표 지시 2026-10-07): 회의 녹음을 글자로 바꿀 때 잘못 들린 우리 회사 말을
#   「정리」 단계에서 바로잡는다. 실측(같은 회의 원문 3,648자 · 5회 반복):
#     표면장 → 표면저항, 카트리스트 → 파트리스트 = 5회 모두 바로잡힘
#     목록에만 있고 회의에 없던 말(코그넥스·YOLO·텔레센트릭) = 0회 (억지로 넣지 않음)
#   🔴 회의 제목에 틀린 말이 적혀 있으면 그 말만은 흔들린다 → 제목을 고쳐야 확실하다.
#   🔴 원문(body)은 절대 바꾸지 않는다. 바로잡기는 정리 글에서만 일어난다.
_MEETING_TERMS_DEFAULT = (
    "MLCC(적층 세라믹 콘덴서 · MSC/MSCC/MHC 로 잘못 들림), FPCB, "
    "파트리스트(부품 목록 · 카트리스트로 잘못 들림), 표면저항(표면장으로 잘못 들림), "
    "정전기, 러버, PVC, 비딩(입찰), OK/NG 판정, 출하 검사기, 치수 검사, 외관 검사, "
    "텔레센트릭 렌즈, 코그넥스, 오픈CV, YOLO"
)


def meeting_terms() -> str:
    """회의록 정리에 함께 주는 「우리 회사 말」. 관리자 → AI 설정에서 고친다.
    빈 값이면 기본 목록 · "-" 한 글자면 이 기능을 끈다(안 보냄)."""
    v = _setting("meeting_terms")
    if v == "-":
        return ""
    return (v or _MEETING_TERMS_DEFAULT).strip()


'''
a = sub(a, "_MEETING_EXTRACT_SYSTEM = (", TERMS_BLOCK + "_MEETING_EXTRACT_SYSTEM = (",
        "용어 기본값 넣을 자리")

ANCHOR = ("    ok, resp = ai_chat(\n"
          "        body.strip(),\n"
          "        system=system,\n"
          "        max_tokens=2000,\n")
ADD = ("    _terms = meeting_terms()           # z1142 — 우리 회사 말(관리자가 고칠 수 있음)\n"
       "    if _terms:\n"
       '        system += ("' + N + N + "[우리 회사 말 — 음성 변환이 흔히 틀리는 말]" + N + '" + _terms\n'
       '                   + "' + N + RED + ' 위 말이 원문에 비슷하게 들어 있으면 그 말로 바로잡는다. "\n'
       '                     "원문에 없는 말은 절대 넣지 않는다. "\n'
       '                     "회의 제목·참석자에 적힌 말이라도 이 목록과 어긋나면 이 목록 쪽을 따른다"\n'
       '                     "(제목도 사람이 잘못 적었을 수 있다).")\n')
a = sub(a, ANCHOR, ADD + ANCHOR, "정리 프롬프트에 용어 붙이기")
save("ai_client.py", a)
print("① ai_client.py — 용어 기본값 + meeting_terms() + 프롬프트 연결")

# ─────────────────────────── ② main.py ───────────────────────────
m = load("main.py")
assert "meeting_terms" not in m, "main 이미 패치됨"

m = sub(m,
        '    info["sdk_claude"] = ai_client._ANTHROPIC_OK\n'
        '    info["sdk_openai"] = ai_client._OPENAI_OK\n'
        '    return ctx(req, "admin_ai_settings.html"',
        '    info["sdk_claude"] = ai_client._ANTHROPIC_OK\n'
        '    info["sdk_openai"] = ai_client._OPENAI_OK\n'
        '    # z1142(대표 지시): 회의록 정리에서 바로잡을 「우리 회사 말」 — 빈 값이면 기본 목록\n'
        '    info["meeting_terms"] = (get_setting("meeting_terms", "") or "")\n'
        '    info["meeting_terms_default"] = ai_client._MEETING_TERMS_DEFAULT\n'
        '    return ctx(req, "admin_ai_settings.html"',
        "AI 설정 화면에 용어 넘기기")

m = sub(m,
        '                                 openai_key_clear: str = Form(""), anthropic_key_clear: str = Form("")):',
        '                                 openai_key_clear: str = Form(""), anthropic_key_clear: str = Form(""),\n'
        '                                 meeting_terms: str = Form("")):',
        "저장 폼에 용어 칸 받기")

m = sub(m,
        '        for k, v in (("ai_provider", (ai_provider or "").strip()),\n'
        '                     ("ai_model", (ai_model or "").strip())):',
        '        for k, v in (("ai_provider", (ai_provider or "").strip()),\n'
        '                     ("ai_model", (ai_model or "").strip()),\n'
        '                     # z1142 — 회의록에서 바로잡을 우리 회사 말(빈 값=기본 목록 · "-"=끄기)\n'
        '                     ("meeting_terms", (meeting_terms or "").strip()[:4000])):',
        "용어 저장")
save("main.py", m)
print("② main.py — 화면에 넘기기 + 저장")

# ─────────────────────────── ③ admin_ai_settings.html ───────────────────────────
h = load("admin_ai_settings.html")
assert "meeting_terms" not in h, "화면 이미 패치됨"

h = sub(h,
        ".ai-hint { font-size:11.5px; color:#8a7842; margin-top:4px; }",
        ".ai-hint { font-size:11.5px; color:#8a7842; margin-top:4px; line-height:1.75; }\n"
        ".ai-field textarea { width:100%; max-width:640px; padding:9px 12px; border:1px solid #d6cdb6;"
        " border-radius:8px; font-size:13.5px; font-family:inherit; line-height:1.65; resize:vertical; }",
        "용어 칸 모양")

h = sub(h,
        '      <button type="submit" class="ai-btn primary">💾 저장</button>',
        '      {# z1142(대표 지시 2026-10-07): 회의 녹음이 잘못 들린 우리 회사 말을 「정리」에서 바로잡는다 #}\n'
        '      <div class="ai-field" style="margin-top:18px;border-top:1px dashed #f1e8d4;padding-top:16px;">\n'
        '        <label>🗓 회의록에서 바로잡을 <b>우리 회사 말</b></label>\n'
        '        <textarea name="meeting_terms" rows="5" placeholder="비워 두면 아래 기본 목록을 씁니다">'
        '{{ info.meeting_terms }}</textarea>\n'
        '        <div class="ai-hint">\n'
        '          회의 녹음을 글자로 바꿀 때 <b>MLCC를 MSCC로</b> 적는 것처럼 잘못 들리는 말이 있습니다.\n'
        '          여기 적어 두면 <b>「정리」 단계에서 우리 회사 말로 바로잡습니다.</b>\n'
        '          쉼표로 이어 적고, 자주 틀리는 말은 <b>MLCC(MSCC로 잘못 들림)</b>처럼 적어 두면 더 잘 잡습니다.<br>\n'
        '          🔴 <b>받아쓴 원문은 바꾸지 않습니다</b> — 정리 글에서만 바로잡습니다.\n'
        '          회의 <b>제목</b>에 틀린 말이 적혀 있으면 그 말은 잘 안 고쳐지니, 제목도 함께 바로잡아 주세요.<br>\n'
        '          비워 두면 기본 목록을 씁니다 · <b>-</b> 한 글자만 적으면 이 기능을 끕니다.<br>\n'
        '          <span style="color:#64748b;">기본 목록: {{ info.meeting_terms_default }}</span>\n'
        '        </div>\n'
        '      </div>\n'
        '\n'
        '      <button type="submit" class="ai-btn primary">💾 저장</button>',
        "용어 칸")
save("admin_ai_settings.html", h)
print("③ admin_ai_settings.html — 적는 칸 + 안내문")
print("끝")
