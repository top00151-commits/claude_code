# -*- coding: utf-8 -*-
"""z1120 — 창을 닫아(✕) 멈춘 녹음: 「🔴 녹음 중이던 회의 · 🎙 이어서 녹음」 상자를 화면 **맨 위**로

대표 신고(2026-09-21 · 사진=이음 회의 카드): 아이폰 웹 녹음 중 녹음 화면을 ✕ 로 닫으면, 다시 녹음하러 찾아 들어가기가
너무 복잡하다 → 카드를 누르면 「이어서 녹음」 아이콘이 있는 화면으로 바로 가게.

운영 실측(회의 41 「테스트」 · 안지연 프로 아이폰):
  ▶ 회의 시작(?autorec=1) → 70초 녹음(조각 8개) → ✕ → 카드 「📋 회의록 열기」 → /meetings/41
  → **목록(/meetings)으로 갔다가** → /meetings/41 다시 → 녹음 시작(28초).
원인 = 카드는 이미 그 회의 화면으로 보낸다. 그런데 「🔴 녹음 중이던 회의 · 🎙 이어서 녹음」 상자(z1113)가
  휴대폰(≤768px) 칸 순서 규칙에 없어 `order:50` → **화면 맨 아래**(할 일·기본 정보·원문·다시 하기·연결 칸 밑).
  PC 도 정리·결정·할 일 아래.

고침(meeting_form.html 한 파일 · 서버·이음 변경 없음):
  ① 상자를 화면 맨 위(자동 정리 카드보다 위)로 · 휴대폰 `order:0`
  ② 「🎙 이어서 녹음」을 첫 단추(주 단추) · 「⏹ 녹음 끝내고 정리」는 둘째 · 누르기 쉬운 크기(44px)
  ③ 이어서 녹음을 누르면 녹음 칸(띠·일시정지·종료)도 맨 위로(휴대폰 칸 순서 · PC 는 그 칸으로 스크롤)
     · 안드로이드는 z1116 「📱 휴대폰 녹음기로 녹음하시겠어요?」 상자를 함께(한 번 눌러 녹음기로 넘김)
     · 마이크를 못 열면 상자를 다시 보여 준다(끝내기·다시 누르기)
  ④ 남이 시작한 녹음이면 한 번 묻는다 — 상자가 맨 위라 대표·관리자·등록 담당이 카드를 열어 보다가 누르면
     그 사람 화면의 녹음이 멈추므로(z1114 stale). 내가 시작한 녹음은 묻지 않고 바로(대표 요청 그대로 한 번 누름)
  ⑤ 이 화면에서 녹음이 시작되면(녹음 추가·자동 녹음) 상자를 치운다 — 전엔 상자가 남아 한 번 더 누르면 녹음기가 둘 생길 수 있었다
  ⑥ (안드로이드) 상자를 두고 「📱 휴대폰 녹음기로 녹음」을 바로 누르면, 열려 있던 **내** 녹음을 먼저 닫는다
     — 전엔 끊긴 조각이 정리에서 빠지고 이음 카드가 계속 「녹음 중」이었다
  ⑦ 아이폰 안내에 한 줄: 실수로 창을 닫았으면 이음 카드 「📋 회의록 열기」 → 맨 위 「🎙 이어서 녹음」

사용: py patch_resume.py <원본 meeting_form.html(운영 96dcc354)> <결과 meeting_form.html>
"""
import hashlib
import io
import sys

sys.stdout.reconfigure(encoding="utf-8")
SRC, DST = sys.argv[1], sys.argv[2]
s0 = io.open(SRC, encoding="utf-8", newline="").read()
assert "\r\n" not in s0, "CRLF 원본 — git show 결과(LF)를 쓸 것"
print("원본 sha256:", hashlib.sha256(s0.encode("utf-8")).hexdigest()[:16])
s = s0


def sub1(old, new, tag):
    global s
    n = s.count(old)
    assert n == 1, "%s: 앵커 %d개(1개여야 함)" % (tag, n)
    s = s.replace(old, new)


# ── ① CSS: 상자 단추 줄 · 휴대폰 칸 순서 ──────────────────────────────────────
sub1(
    "#redoTools .redo-row { display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin:12px 0; }\n",
    "#redoTools .redo-row { display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin:12px 0; }\n"
    "/* z1120: 「🔴 녹음 중이던 회의」 상자 단추 — 휴대폰에서 누르기 쉬운 크기 */\n"
    "#recResume .rr-btns { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }\n"
    "#recResume .rr-btns .btn { min-height:44px; font-size:15px; font-weight:800; }\n",
    "CSS 상자 단추",
)
sub1(
    "  #pipeCard { order:1; }\n",
    "  #recResume { order:0; }   /* z1120: 창이 닫혀 멈춘 녹음 — 「🎙 이어서 녹음」을 맨 위에(전엔 order:50 = 맨 아래) */\n"
    "  #pipeCard { order:1; }\n",
    "CSS 휴대폰 상자 맨 위",
)
sub1(
    "  .mf-wrap.autorec #redoTools { order:2; }   /* 회의 알림 「회의 시작」으로 열린 창 — 녹음 칸을 맨 위로 */\n",
    "  .mf-wrap.autorec #redoTools { order:2; }   /* 회의 알림 「회의 시작」으로 열린 창 — 녹음 칸을 맨 위로 */\n"
    "  .mf-wrap.recfront #redoTools { order:2; }  /* z1120: 「🎙 이어서 녹음」을 누른 뒤 — 녹음 칸(띠·일시정지·종료)을 맨 위로 */\n",
    "CSS 휴대폰 녹음 칸 맨 위",
)

# ── ② 상자: 원래 자리(할 일 아래)에서 빼고 → 화면 맨 위(자동 정리 카드 위)에 새로 ──────
OLD_BOX = (
    "    {% if can_edit and rec and rec.state == 'recording' %}\n"
    "    {# z1113 (대표 지시 2026-09-18): 창이 닫혀 끊긴 녹음 — 여기서 마치거나 이어서 녹음한다.\n"
    "       녹음은 10초쯤마다 서버에 저장되므로 아래 시간까지는 이미 서버에 있다. #}\n"
    "    <div class=\"mf-section\" id=\"recResume\" style=\"border-left:4px solid var(--knk-red);\">\n"
    "      <div style=\"font-size:15px;font-weight:800;color:var(--knk-red);margin-bottom:6px;\">🔴 녹음 중이던 회의입니다</div>\n"
    "      <div class=\"mf-hint\" style=\"line-height:1.7;margin-bottom:10px;\">\n"
    "        지금까지 <b id=\"recResumeSaved\">{{ '%d분 %d초'|format(rec.secs // 60, rec.secs % 60) }}</b>가 서버에 저장돼 있습니다{% if rec.kb %} ({{ rec.kb }}KB){% endif %}.\n"
    "        {% if rec.last_at %}마지막 소리 {{ rec.last_at }}.{% endif %}\n"
    "        창이 닫히거나 앱이 꺼져도 <b>여기까지는 남습니다</b> — 아래에서 마치거나 이어서 녹음하세요.\n"
    "      </div>\n"
    "      <div class=\"redo-row\">\n"
    "        <button class=\"btn btn-primary\" id=\"recFinishBtn\">⏹ 녹음 끝내고 정리</button>\n"
    "        <button class=\"btn btn-secondary\" id=\"recResumeBtn\">🎙 이어서 녹음</button>\n"
    "        <span class=\"rec-status\" id=\"recResumeSt\"></span>\n"
    "      </div>\n"
    "    </div>\n"
    "    {% endif %}\n"
)
sub1(OLD_BOX, "", "상자 원래 자리 빼기")

NEW_BOX = (
    "    {% if can_edit and rec and rec.state == 'recording' %}\n"
    "    {# z1113 (대표 지시 2026-09-18): 창이 닫혀 끊긴 녹음 — 여기서 마치거나 이어서 녹음한다.\n"
    "       녹음은 10초쯤마다 서버에 저장되므로 아래 시간까지는 이미 서버에 있다.\n"
    "       z1120 (대표 지시 2026-09-21): 아이폰에서 녹음 창을 ✕ 로 닫았다가 이음 카드 「📋 회의록 열기」로 돌아오면\n"
    "       이 상자가 휴대폰에선 맨 아래(연결 칸 밑)에 있어 목록을 헤맸다(운영 회의 41) → 화면 맨 위로 · 「🎙 이어서 녹음」이 첫 단추. #}\n"
    "    <div class=\"mf-section\" id=\"recResume\" style=\"border-left:4px solid var(--knk-red);\">\n"
    "      <div style=\"font-size:15px;font-weight:800;color:var(--knk-red);margin-bottom:6px;\">🔴 녹음 중이던 회의입니다</div>\n"
    "      <div class=\"mf-hint\" style=\"line-height:1.7;margin-bottom:10px;\">\n"
    "        지금까지 <b id=\"recResumeSaved\">{{ '%d분 %d초'|format(rec.secs // 60, rec.secs % 60) }}</b>가 서버에 저장돼 있습니다{% if rec.kb %} ({{ rec.kb }}KB){% endif %}.\n"
    "        {% if rec.last_at %}마지막 소리 {{ rec.last_at }}.{% endif %}\n"
    "        창이 닫히거나 앱이 꺼져도 <b>여기까지는 남습니다</b> — 회의가 이어지면 <b>「🎙 이어서 녹음」</b>, 끝났으면 <b>「⏹ 녹음 끝내고 정리」</b>를 누르세요.\n"
    "      </div>\n"
    "      <div class=\"rr-btns\">\n"
    "        <button class=\"btn btn-primary\" id=\"recResumeBtn\">🎙 이어서 녹음</button>\n"
    "        <button class=\"btn btn-secondary\" id=\"recFinishBtn\">⏹ 녹음 끝내고 정리</button>\n"
    "        <span class=\"rec-status\" id=\"recResumeSt\"></span>\n"
    "      </div>\n"
    "    </div>\n"
    "    {% endif %}\n"
)
sub1(
    "  {% else %}\n"
    "    <!-- ═══ 자동 정리 진행 카드 (?auto=1 착지·이어서 하기·실패 재시도) ═══ -->\n",
    "  {% else %}\n" + NEW_BOX +
    "    <!-- ═══ 자동 정리 진행 카드 (?auto=1 착지·이어서 하기·실패 재시도) ═══ -->\n",
    "상자 맨 위에 넣기",
)

# ── ③ JS: 상자 상태·남의 녹음 묻기 ────────────────────────────────────────────
sub1(
    "  var REC = M.rec || {};\n",
    "  var REC = M.rec || {};\n"
    "  // z1120: 이 화면을 열 때 서버에 '창이 닫혀 멈춘 녹음'이 열려 있었나 — 맨 위 「🔴 녹음 중이던 회의」 상자\n"
    "  var _recOpen = (REC.state === 'recording');\n"
    "  function recResumeShow(on){ var box=$('recResume'); if(box) box.style.display=on?'':'none'; }\n"
    "  // 남이 시작한 녹음이면 한 번 묻는다 — 그 사람 화면이 아직 녹음 중이면 여기서 누르는 순간 그쪽 녹음이 멈춘다(z1114).\n"
    "  //   상자가 맨 위라 대표·관리자·등록 담당이 카드를 열어 보다가 누를 수 있다. 내가 시작한 녹음은 묻지 않는다.\n"
    "  function recResumeOk(kind){\n"
    "    if(REC.mine) return true;\n"
    "    return window.confirm(kind==='finish'\n"
    "      ? '다른 사람이 시작한 녹음입니다.\\n그 화면에서 아직 녹음 중이면 그쪽 녹음은 멈추고, 지금까지 녹음으로 정리를 시작합니다.\\n\\n녹음을 끝낼까요?'\n"
    "      : '다른 사람이 시작한 녹음입니다.\\n그 화면에서 아직 녹음 중이면 그쪽 녹음은 멈추고, 이 화면에서 이어서 녹음합니다(지금까지 녹음은 그대로 남습니다).\\n\\n여기서 이어서 녹음할까요?');\n"
    "  }\n",
    "JS 상자 상태",
)
sub1(
    "      if(r.ok&&j.ok&&j.session){ _recSes=j.session; return true; }\n",
    "      if(r.ok&&j.ok&&j.session){\n"
    "        _recSes=j.session;\n"
    "        _recOpen=false; recResumeShow(false);   // z1120: 이 화면에서 녹음이 시작됐다(서버가 끊긴 조각을 닫아 보존) — 상자는 치운다\n"
    "        return true;\n"
    "      }\n",
    "JS 녹음 시작되면 상자 치움",
)

# ── ④ JS: 상자 단추 ──────────────────────────────────────────────────────────
sub1(
    "  // z1113: 「🔴 녹음 중이던 회의」 상자 — 끝내고 정리 / 이어서 녹음\n"
    "  var _recFin=$('recFinishBtn');\n"
    "  if(_recFin) _recFin.addEventListener('click',async function(){\n"
    "    _recFin.disabled=true;\n",
    "  // z1113: 「🔴 녹음 중이던 회의」 상자 — 끝내고 정리 / 이어서 녹음\n"
    "  //   z1120: 상자는 화면 맨 위 · 남이 시작한 녹음이면 한 번 묻는다 · 이어서 녹음하면 녹음 칸도 맨 위로\n"
    "  var _recFin=$('recFinishBtn');\n"
    "  if(_recFin) _recFin.addEventListener('click',async function(){\n"
    "    if(!recResumeOk('finish')) return;\n"
    "    _recFin.disabled=true;\n",
    "JS 끝내기 묻기",
)
sub1(
    "    var box=$('recResume'); if(box) box.style.display='none';\n"
    "    M.has_audio=true; M.base_ts=j.updated_at||M.base_ts;\n",
    "    _recOpen=false; recResumeShow(false);\n"
    "    M.has_audio=true; M.base_ts=j.updated_at||M.base_ts;\n",
    "JS 끝낸 뒤 상자 치움",
)
sub1(
    "  var _recRes=$('recResumeBtn');\n"
    "  if(_recRes) _recRes.addEventListener('click',function(){\n"
    "    var box=$('recResume'); if(box) box.style.display='none';\n"
    "    var d=$('redoTools'); if(d) d.open=true;\n"
    "    recStart();\n"
    "  });\n",
    "  var _recRes=$('recResumeBtn');\n"
    "  if(_recRes) _recRes.addEventListener('click',function(){\n"
    "    if(_mr && _mr.state!=='inactive'){ recResumeShow(false); return; }   // 이미 이 화면에서 녹음 중 — 녹음기가 둘 생기지 않게\n"
    "    if(!recResumeOk('resume')) return;\n"
    "    recResumeShow(false);\n"
    "    var d=$('redoTools'); if(d) d.open=true;\n"
    "    // z1120: 녹음 칸(띠·일시정지·종료)을 맨 위로 — 휴대폰은 칸 순서(.recfront), PC 는 그 칸으로 스크롤\n"
    "    try{ var _w=document.querySelector('.mf-wrap'); if(_w) _w.classList.add('recfront'); }catch(_){}\n"
    "    try{ if(d) d.scrollIntoView({block:'start'}); }catch(_){}\n"
    "    if(_isAndroid) phrecLeadShow('running');   // 안드로이드: 한 번 눌러 휴대폰 녹음기로 넘길 수 있게(z1116 상자 · 지금까지 녹음은 이어짐)\n"
    "    recStart().then(function(ok){\n"
    "      if(!_alive()) return;\n"
    "      if(!ok){ if(_recOpen) recResumeShow(true); return; }   // 마이크를 못 열면 상자를 되살린다(끝내기·다시 누르기)\n"
    "      // 녹음 띠·안내가 붙으며 크롬이 화면을 밀어 올린다(스크롤 고정 · 실측 157px) → 녹음 칸을 다시 맨 위로\n"
    "      try{ var _ld=$('recPhoneLead'), _t=(_ld && !_ld.hidden) ? _ld : d; if(_t) _t.scrollIntoView({block:'start'}); }catch(_){}\n"
    "    });\n"
    "  });\n",
    "JS 이어서 녹음",
)

# ── ⑤ JS: 안드로이드 — 상자를 두고 녹음기를 바로 누르면 열려 있던 내 녹음을 먼저 닫는다 ─────────
sub1(
    "      } else {\n"
    "        recSt('휴대폰 녹음기가 열립니다 — 회의가 끝나면 녹음기에서 저장하세요. 이 화면으로 돌아오면 자동으로 올라갑니다.');\n"
    "      }\n",
    "      } else {\n"
    "        // z1120: 창이 닫혀 멈춘 **내** 녹음이 서버에 열려 있으면 먼저 닫아 둔다 — 녹음기 파일과 순서대로 이어 정리되게\n"
    "        //   (전엔 끊긴 조각이 정리에서 빠지고 이음 카드가 계속 「녹음 중」). 기다리지 않는다(기다리면 '누름'이 풀려 녹음기가 안 열림).\n"
    "        if(_recOpen && REC.mine){ _recOpen=false; recResumeShow(false); recNetFinish(); }\n"
    "        recSt('휴대폰 녹음기가 열립니다 — 회의가 끝나면 녹음기에서 저장하세요. 이 화면으로 돌아오면 자동으로 올라갑니다.');\n"
    "      }\n",
    "JS 녹음기 전에 내 녹음 닫기",
)

# ── ⑥ 아이폰 안내 한 줄 ──────────────────────────────────────────────────────
sub1(
    "        +'자리를 비우거나 다른 일을 해야 하면 아이폰 기본 <b>「음성 메모」로 녹음한 뒤 「📁 음성 파일 올리기」</b>를 쓰세요.';\n",
    "        +'자리를 비우거나 다른 일을 해야 하면 아이폰 기본 <b>「음성 메모」로 녹음한 뒤 「📁 음성 파일 올리기」</b>를 쓰세요.'\n"
    "        +'<br>실수로 이 창을 닫았으면(✕) 이음 회의 카드의 <b>「📋 회의록 열기」</b>(또는 회의록 목록에서 이 회의)를 누르세요 '\n"
    "        +'— 맨 위 <b>「🎙 이어서 녹음」</b>으로 바로 이어집니다(그때까지 녹음은 서버에 남아 있습니다).';   // z1120\n",
    "아이폰 안내",
)

with io.open(DST, "w", encoding="utf-8", newline="") as f:
    f.write(s)
print("[OK] meeting_form.html %d → %d 글자" % (len(s0), len(s)))
print("결과 sha256:", hashlib.sha256(s.encode("utf-8")).hexdigest()[:16])
for k, got, want in [("상자 id", s.count('id="recResume"'), 1),
                     ("이어서 녹음 단추", s.count('id="recResumeBtn"'), 1),
                     ("끝내기 단추", s.count('id="recFinishBtn"'), 1),
                     ("휴대폰 order:0", s.count("#recResume { order:0; }"), 1),
                     ("recfront CSS", s.count(".mf-wrap.recfront #redoTools { order:2; }"), 1),
                     ("recfront JS", s.count("classList.add('recfront')"), 1),
                     ("묻기 함수", s.count("function recResumeOk(kind)"), 1),
                     ("아이폰 안내", s.count("실수로 이 창을 닫았으면(✕)"), 1)]:
    print("   %-16s %d  %s" % (k, got, "OK" if got == want else "⚠ %d 예상" % want))
    assert got == want, k
# 상자가 자동 정리 카드보다 앞 · 할 일 칸 뒤에는 없음
assert s.index('id="recResume"') < s.index('id="pipeCard"') < s.index('id="secActions"'), "상자 위치"
