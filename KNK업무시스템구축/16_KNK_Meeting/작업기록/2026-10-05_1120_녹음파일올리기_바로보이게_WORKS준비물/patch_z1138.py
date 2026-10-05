# -*- coding: utf-8 -*-
"""z1138 — 「📁 녹음 파일 올리기」를 회의록 맨 위 큰 단추로 (대표 지시 2026-10-05)

발단(대표): 「회의록 작성시 녹음을 휴대폰 녹음기로 녹음을 하고 그걸 올리는 메뉴가 바로 보이질 않아
찾는데 조금 어려워… 녹음한 파일 올리기 아이콘이 쉽게 보였으면 해」

원인(운영 화면 실측): 올리기 단추가 **「🔧 다시 하기 · 녹음 추가 (필요할 때만)」 접힌 칸** 안에만 있었다.
휴대폰 녹음기로 녹음을 마치고 회의록을 다시 열면(목록에서 열거나 새로고침) 그 칸은 **접힌 채 화면 아래**
(폰 순서 11)로 내려가 있고, 칸 이름이 「다시 하기(필요할 때만)」라 **올리는 자리로 보이지 않았다**.
게다가 안내문은 「📁 녹음 파일 올리기」, 실제 단추는 「📁 음성 파일 올리기」로 **이름이 달랐다**.

대표 결정(2026-10-05): ① 자리 = **회의록 맨 위 큰 단추** ② **녹음이 없을 때만** 크게 보인다

바꾸는 것 (app/templates/meeting_form.html 7곳):
  1) CSS — `#recUpTop`·`.recup-big` (🔴 hidden 을 이기는 `!important` 포함)
  2) 폰 칸 순서 — `#recUpTop { order:2; }` (진행 카드 바로 아래 = 맨 위)
  3) 화면 — 진행 카드 뒤, 「회의 기본 정보」 앞에 새 칸(녹음 없고·녹음 중 아닐 때만 그려진다)
  4) JS — 새 입력칸을 기존 올리기 처리(onPickFile)에 잇기
  5) JS — `recSt` 가 맨 위 칸에도 같은 글을 쓴다(접힌 칸 안 글은 안 보이므로)
  6) JS — 녹음이 들어오면(올리기 성공·이 화면 녹음 시작) 맨 위 칸을 감춘다
  7) 이름 통일 — 「📁 음성 파일 올리기」 → 「📁 녹음 파일 올리기」(안내문·단추 10곳)

사용: python patch_z1138.py <meeting_form.html 경로>
"""
import io
import os
import sys

CSS = """/* ── 📁 녹음 파일 올리기 (맨 위) — z1138 대표 지시 2026-10-05: 「바로 보이게」 ──
   전에는 「🔧 다시 하기(필요할 때만)」 접힌 칸 안에만 있어 회의록을 다시 열면 찾기 어려웠다. */
#recUpTop { border-left:4px solid var(--knk-red); }
.recup-big { display:flex; flex-direction:column; align-items:center; justify-content:center; gap:5px;
  text-align:center; border:0; border-radius:14px; padding:18px 16px; min-height:44px; cursor:pointer;
  background: var(--knk-red); color:#fff; font-size:19px; font-weight:800;
  box-shadow:0 2px 10px rgba(160,30,30,.18); }
.recup-big:active { transform: scale(.99); }
.recup-big .recup-sub { font-size:12.5px; font-weight:600; opacity:.9; line-height:1.5; }
/* 🔴 .mf-section 의 display 가 hidden 속성을 덮는다 — 이겨야 녹음이 들어온 뒤 사라진다 */
#recUpTop[hidden] { display:none !important; }
"""

ORDER = "  #recUpTop { order:2; }   /* z1138: 「📁 녹음 파일 올리기」는 진행 카드 바로 아래 = 맨 위 */\n"

BOX = """    <!-- ── 📁 녹음 파일 올리기 — 맨 위 (z1138 · 대표 지시 2026-10-05) ──
         휴대폰 녹음기로 녹음한 파일을 올리는 자리. 전에는 「🔧 다시 하기 · 녹음 추가(필요할 때만)」
         접힌 칸 안에만 있어, 회의록을 다시 열면 찾기 어려웠다(대표 신고 2026-10-05).
         대표 결정: 녹음이 아직 없을 때만 크게 보인다(녹음이 들어오면 JS 가 감춘다). -->
    {# 🔴 정리가 이미 끝난 회의록(글로 쓴 것 포함)에서는 큰 단추를 띄우지 않는다 — 폰 「결과 먼저」 순서(z971/z973)를
       가리지 않게. 그런 회의에 녹음을 더 붙이는 일은 「🔧 다시 하기 · 녹음 추가」가 제 자리다. #}
    {% if can_edit and not meeting.audio_path and not meeting.summary and not (rec and rec.state == 'recording') %}
    <div class="mf-section" id="recUpTop">
      <label class="recup-big" id="recUpBtn">📁 녹음 파일 올리기
        <span class="recup-sub">휴대폰 녹음기로 녹음한 파일을 고르면 <b>음성→글자·AI 정리까지 자동</b></span>
        <input type="file" id="recFileTop" accept="audio/*" data-knk-no-dropzone style="display:none">
      </label>
      <div class="mf-hint" style="margin-top:9px;line-height:1.7;">휴대폰 <b>홈 화면 「음성 녹음」</b>으로 녹음하면
        다른 앱을 보거나 화면이 꺼져도 <b>안 끊깁니다</b>. 끝나면 이 단추로 그 녹음을 고르세요.</div>
      <div class="rec-status" id="recUpSt" style="display:block;margin-top:8px;"></div>
    </div>
    {% endif %}

"""

BIND = ("  // z1138: 맨 위 「📁 녹음 파일 올리기」도 같은 처리로 — 올리는 길은 하나만 둔다\n"
        "  var _recFileTop=$('recFileTop');if(_recFileTop)_recFileTop.addEventListener('change',onPickFile);\n")


def main():
    if len(sys.argv) < 2:
        print("사용: python patch_z1138.py <meeting_form.html 경로>")
        return 2
    p = sys.argv[1]
    if not os.path.exists(p):
        print("없는 파일:", p)
        return 2
    src = io.open(p, encoding="utf-8").read()
    if "recUpTop" in src:
        print("이미 z1138 이 들어 있음 — 건너뜀:", p)
        return 0

    steps = []

    # ① CSS
    a1 = "/* \U0001F534 .start-big/.btn 의 display"
    steps.append(("① CSS #recUpTop·.recup-big", a1, CSS, "before"))

    # ② 폰 칸 순서
    a2 = "  #redoTools { order:11; }"
    steps.append(("② 폰 칸 순서 order:2", a2, ORDER, "before"))

    # ③ 화면(새 칸)
    a3 = "    <!-- ── 회의 기본 정보 ── -->"
    steps.append(("③ 맨 위 올리기 칸", a3, BOX, "before"))

    # ④ JS 잇기
    a4 = "  var _recFile=$('recFile');if(_recFile)_recFile.addEventListener('change',onPickFile);\n"
    steps.append(("④ 새 입력칸을 onPickFile 에 잇기", a4, BIND, "after"))

    for label, anchor, block, how in steps:
        n = src.count(anchor)
        if n != 1:
            print("자리 못 찾음(%d개): %s" % (n, label))
            return 3
        if how == "before":
            src = src.replace(anchor, block + anchor, 1)
        else:
            src = src.replace(anchor, anchor + block, 1)
        print("적용:", label)

    # ⑤ recSt — 맨 위 칸에도 같은 글을 쓴다(접힌 칸 안 글은 안 보인다)
    old5 = ("  function recSt(msg,kind){var el=$('recStatus');if(el){el.textContent=msg||'';"
            "el.style.color=kind==='err'?'var(--knk-red)':(kind==='ok'?'#15803d':'var(--qv-ink-3)');}}")
    if src.count(old5) != 1:
        print("자리 못 찾음: ⑤ recSt")
        return 3
    new5 = ("  // z1138: 알림 글을 맨 위 올리기 칸에도 같이 쓴다 — 접힌 「🔧 다시 하기」 안의 글은 안 보인다\n"
            "  function recSt(msg,kind){var c=kind==='err'?'var(--knk-red)':(kind==='ok'?'#15803d':'var(--qv-ink-3)');\n"
            "    var el=$('recStatus');if(el){el.textContent=msg||'';el.style.color=c;}\n"
            "    var t=$('recUpSt');if(t){t.textContent=msg||'';t.style.color=c;}}")
    src = src.replace(old5, new5, 1)
    print("적용: ⑤ recSt 가 맨 위 칸에도 쓰기")

    # ⑥-1 올리기 성공 → 맨 위 칸 감춤
    old6 = "        M.base_ts=j.updated_at||M.base_ts; M.has_audio=true;"
    if src.count(old6) != 1:
        print("자리 못 찾음: ⑥-1 올리기 성공")
        return 3
    src = src.replace(old6, old6 + "\n        recUpHide();   // z1138: 녹음이 들어왔으니 맨 위 올리기 칸은 감춘다", 1)

    # ⑥-2 이 화면 녹음이 시작되면(띠가 켜지면) 맨 위 칸 감춤 + 도우미 추가
    old62 = "  function recBanner(show,paused){var b=$('recBanner');if(!b)return;b.hidden=!show;"
    if src.count(old62) != 1:
        print("자리 못 찾음: ⑥-2 recBanner")
        return 3
    new62 = ("  // z1138: 녹음이 들어오면 맨 위 「📁 녹음 파일 올리기」 칸을 감춘다(대표 결정: 녹음이 없을 때만 크게)\n"
             "  function recUpHide(){try{var u=$('recUpTop');if(u)u.hidden=true;}catch(_){}}\n"
             + old62 + "if(show)recUpHide();")
    src = src.replace(old62, new62, 1)
    print("적용: ⑥ 녹음이 들어오면 감추기(올리기 성공·녹음 시작)")

    # ⑦ 이름 통일 — 「📁 음성 파일 올리기」 → 「📁 녹음 파일 올리기」
    old7 = "\U0001F4C1 사운상"   # (쓰이지 않음 — 아래에서 실제 표기로 바꾼다)
    del old7
    OLDNM = "\U0001F4C1 음성 파일 올리기"
    NEWNM = "\U0001F4C1 녹음 파일 올리기"
    cnt = src.count(OLDNM)
    if cnt < 1:
        print("자리 못 찾음: ⑦ 이름 통일")
        return 3
    src = src.replace(OLDNM, NEWNM)
    print("적용: ⑦ 이름 통일 %d곳 (음성 → 녹음 파일 올리기)" % cnt)

    bak = p + ".bak_z1138"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="").write(io.open(p, encoding="utf-8").read())
    data = src.encode("utf-8")          # 🔴 쓰기 전에 인코딩을 먼저 해 본다
    tmp = p + ".tmp_z1138"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, p)
    print("저장:", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
