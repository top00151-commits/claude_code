# -*- coding: utf-8 -*-
"""z1115 — 「📱 휴대폰 녹음기로 녹음」 + 기기별 안내 (대표 지시 2026-09-20)

대표 지시 ①「녹음을 할 때 휴대폰 기본 녹음기로 녹음하게 연결할 수 없나?」
        ②「지금 중요한 목적은 어떤 사항에서도 녹음이 중지되면 안 되는 것」
        ③「안드로이드가 아닌 iOS 면 기존처럼 녹음하되, 웹 창을 바꾸면 녹음이 되지 않는다고 안내문을 넣어라」

실측(운영 회의 37 「테스트2」 4분 57초): 이 화면이 뒤로 가 있던 01:57~03:31 **95초가 완전 무음(-101dB)**.
안드로이드 11+ 는 화면에 보이지 않는 앱의 마이크를 막는다(예외 = 마이크용 상주 서비스를 가진 진짜 앱).
브라우저 안의 웹 화면은 그 자격을 못 만든다 → **휴대폰 기본 녹음기**가 유일하게 안 끊기는 길.
`<input type=file accept=audio/* capture>` 가 안드로이드에서 그 녹음기를 바로 열고, 끝나면 파일이 돌아온다.
iOS 는 그런 녹음기 연결이 없다 → 단추를 숨기고, 화면을 벗어나면 녹음이 안 된다는 안내를 띄운다.

사용: py patch_phrec.py <원본 폴더> <결과 폴더>
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
SRC, DST = sys.argv[1], sys.argv[2]
os.makedirs(DST, exist_ok=True)


def load(name, base=None):
    p = os.path.join(base or SRC, name)
    s = io.open(p, encoding="utf-8", newline="").read()
    assert "\r\n" not in s, name + ": CRLF 원본 — git show 결과(LF)를 쓸 것"
    return s


def save(name, s):
    with io.open(os.path.join(DST, name), "w", encoding="utf-8", newline="") as f:
        f.write(s)


def sub1(s, old, new, tag):
    n = s.count(old)
    assert n == 1, "%s: 앵커 %d개(1개여야 함)" % (tag, n)
    return s.replace(old, new)


def subn(s, old, new, want, tag):
    n = s.count(old)
    assert n == want, "%s: 앵커 %d개(%d개여야 함)" % (tag, n, want)
    return s.replace(old, new)


# ══════════════════════════════════════════════════════════════════════
# 1. meeting_form.html
# ══════════════════════════════════════════════════════════════════════
f0 = load("meeting_form.html")
f = f0

# ── ① CSS — 큰 단추로 쓰는 <label> · 기기별 안내 상자
f = sub1(
    f,
    ".start-mid:hover { background: var(--qv-surface-2); }\n",
    ".start-mid:hover { background: var(--qv-surface-2); }\n"
    "/* ── z1115 📱 휴대폰 녹음기로 녹음(안드로이드) · 기기별 안내(안드로이드·아이폰) ── */\n"
    ".start-big.alt { background: var(--qv-surface); color: var(--qv-ink);\n"
    "  border:1px solid var(--qv-line-3); box-shadow:none; }\n"
    ".rec-phone { text-align:center; }\n"
    "/* 🔴 .start-big/.btn 의 display 가 hidden 속성을 덮는다 — 이겨야 아이폰·PC 에서 안 보인다 */\n"
    ".rec-phone[hidden] { display:none !important; }\n"
    ".plat-note { border-radius:12px; padding:12px 14px; margin-top:12px; font-size:13px; line-height:1.75;\n"
    "  border:1px solid #FED7AA; background:#FFF7ED; color:#7C2D12; }\n"
    ".plat-note.ios { border-color:#BFDBFE; background:#EFF6FF; color:#1E3A8A; }\n"
    ".plat-note b { font-weight:800; }\n",
    "CSS",
)

# ── ② 새 회의 화면 — 안 끊기는 길을 「🎙 녹음하며 회의」 위에(안드로이드에서만 보임)
f = sub1(
    f,
    '        <button class="start-big rec-btn" id="recBtn">',
    "        <!-- z1115: 휴대폰은 다른 앱으로 넘어가면 OS 가 마이크를 막는다(2026-09-20 실측 95초 무음)\n"
    "             → 안 끊기는 길(휴대폰 기본 녹음기)을 맨 위에. 안드로이드에서만 보인다(iOS 는 녹음기가 안 열림). -->\n"
    '        <label class="start-big rec-phone" id="recPhoneRecWrap" hidden>📱 휴대폰 녹음기로 녹음'
    '&nbsp;<span class="start-sub">다른 앱을 봐도 끊기지 않아요</span>'
    '<input type="file" id="recFileCap" accept="audio/*" capture data-knk-no-dropzone style="display:none"></label>\n'
    '        <button class="start-big rec-btn" id="recBtn">',
    "새회의 단추",
)

# ── ③ 상세 「🔧 다시 하기 · 녹음 추가」 — 같은 단추를 「📁 음성 파일 올리기」 앞에
f = sub1(
    f,
    '          <label class="btn btn-secondary rec-file">📁 음성 파일 올리기',
    '          <label class="btn btn-primary rec-phone" id="recPhoneRecWrap" hidden>📱 휴대폰 녹음기로 녹음'
    '<input type="file" id="recFileCap" accept="audio/*" capture data-knk-no-dropzone style="display:none"></label>\n'
    '          <label class="btn btn-secondary rec-file">📁 음성 파일 올리기',
    "상세 단추",
)

# ── ④ 안내문 — 기기와 상관없는 것만 남기고, 기기별 안내는 아래 상자로
old_hint = [ln for ln in f.split("\n") if "※ 녹음을 마치면" in ln]
assert len(old_hint) == 1, "안내문 줄 %d개" % len(old_hint)
new_hint = (
    '      <div class="mf-hint" style="margin-top:10px;line-height:1.6;">'
    "※ 녹음을 마치면 <b>음성→글자, AI 정리까지 자동</b>으로 됩니다. "
    "<b>전화를 받을 땐 「⏸ 일시정지」</b>(통화 내용 녹음 방지) → 통화 후 「▶ 재개」. "
    "이 화면 녹음은 <b>10초마다 서버에 저장</b>돼 창이 닫혀도 그때까지는 남고, "
    "<b>회의록 목록에서 「녹음 끝내고 정리」</b>로 마칠 수 있습니다.</div>\n"
    '      <div class="plat-note" id="recPlatNote" hidden></div>'
)
f = sub1(f, old_hint[0], new_hint, "안내문")

# ── ④-2 상세 「🔧 다시 하기」 안내 아래에도 같은 상자
f = sub1(
    f,
    "평소엔 위 자동 정리로 충분합니다.</div>\n",
    "평소엔 위 자동 정리로 충분합니다.</div>\n"
    '        <div class="plat-note" id="recPlatNote" hidden></div>\n',
    "상세 안내 상자",
)

# ── ⑤ 올라가면 '녹음기로 갔다' 표시를 지운다
f = sub1(
    f,
    "        M.base_ts=j.updated_at||M.base_ts; M.has_audio=true;\n",
    "        M.base_ts=j.updated_at||M.base_ts; M.has_audio=true;\n"
    "        phrecClear();   // z1115: 녹음기 파일이 들어왔으니 목록의 '녹음기로 녹음 중' 표시를 지운다\n",
    "표시 지우기",
)

# ── ⑥ JS — 녹음기 열기 · 회의 먼저 만들기 · 표시 남기기 · 기기별 안내
PHREC_JS = r"""
  // ── z1115 「📱 휴대폰 녹음기로 녹음」 — 어떤 경우에도 녹음이 멈추면 안 된다(대표 지시 2026-09-20) ──
  //   실측(회의 37 「테스트2」): 이 화면이 뒤로 가 있던 95초가 완전 무음(-101dB)으로 녹음됐다.
  //   안드로이드 11+ 는 화면에 안 보이는 앱의 마이크를 막고, 예외는 '마이크용 상주 서비스'를 가진 진짜 앱뿐이다.
  //   브라우저 안의 웹 화면은 그 자격을 만들 수 없다 → 휴대폰 기본 녹음기에 맡기고 파일만 받아 온다.
  //   capture 속성이 그 녹음기를 바로 연다(안드로이드만 · iOS 는 그런 연결이 없어 단추를 숨기고 안내만 한다).
  var _isAndroid=/Android/i.test(navigator.userAgent||'');
  var _isIOS=/iPhone|iPad|iPod/i.test(navigator.userAgent||'')
          || (/Macintosh/i.test(navigator.userAgent||'') && (navigator.maxTouchPoints||0)>1);   // 아이패드는 맥으로 보임
  var PHREC_KEY='knk_mtg_phonerec';
  function phrecMark(id,title){
    if(!id) return;
    try{ localStorage.setItem(PHREC_KEY, JSON.stringify({id:id,title:title||'',at:Date.now()})); }catch(_){}
  }
  function phrecClear(){ try{ localStorage.removeItem(PHREC_KEY); }catch(_){} }
  var _phWrap=$('recPhoneRecWrap'), _phIn=$('recFileCap'), _phSaving=null;
  if(_phIn) _phIn.addEventListener('change',onPickFile);   // 돌아온 파일 = 평소 올리기와 같은 길
  if(_phWrap&&_phIn&&_isAndroid){
    _phWrap.hidden=false;
    _phWrap.addEventListener('click',function(){
      // 한 번 눌러도 라벨→입력으로 두 번 올라온다(브라우저 기본 동작) → 회의는 한 번만 만든다.
      // 기다리면(await) '누른 것'이 풀려 녹음기가 안 열린다 → 저장은 뒤에서, 녹음기는 바로.
      if(!_phSaving){
        _phSaving=Promise.resolve().then(ensureMeetingSaved).then(function(ok){
          if(ok) phrecMark(M.id, (($('mtgTitle')||{}).value)||'');
          return ok;
        }).catch(function(){ return false; });
      } else if(M.id){ phrecMark(M.id, (($('mtgTitle')||{}).value)||''); }
      recSt('휴대폰 녹음기가 열립니다 — 회의가 끝나면 녹음기에서 저장하세요. 이 화면으로 돌아오면 자동으로 올라갑니다.');
    });
    // 휴대폰에선 이 화면 녹음이 '두 번째 선택' — 색으로만 구분한다
    //   (글자는 그대로 둔다: 이음 안내 4개 언어가 「🎙 녹음하며 회의」라는 이름을 그대로 쓴다)
    var _rb=$('recBtn'); if(_rb&&_rb.classList.contains('start-big')) _rb.classList.add('alt');
  }
  // 기기별 안내 — 안드로이드는 녹음기로, 아이폰·아이패드는 이 화면을 켠 채로(대표 지시 2026-09-20)
  (function(){
    var el=$('recPlatNote'); if(!el) return;
    if(_isAndroid){
      el.innerHTML='📱 <b>안드로이드</b> — 회의 중에 다른 앱을 보거나 화면이 꺼져도 끊기지 않으려면 '
        +'<b>「📱 휴대폰 녹음기로 녹음」</b>을 쓰세요. 「🎙 녹음하며 회의」는 <b>이 화면을 켜 둘 때만</b> 소리가 들어옵니다 '
        +'— 다른 앱으로 넘어가면 휴대폰이 마이크를 막습니다(2026-09-20 실측 95초).';
      el.hidden=false;
    } else if(_isIOS){
      el.className='plat-note ios';
      el.innerHTML='🍎 <b>아이폰·아이패드</b> — 지금처럼 이 화면에서 녹음합니다. 다만 <b>다른 앱이나 다른 웹 화면으로 넘어가면 '
        +'그동안은 녹음되지 않습니다.</b> 회의 중에는 <b>이 화면을 켠 채로</b> 두세요. '
        +'자리를 비우거나 다른 일을 해야 하면 아이폰 기본 <b>「음성 메모」로 녹음한 뒤 「📁 음성 파일 올리기」</b>를 쓰세요.';
      el.hidden=false;
    }
  })();
"""
f = sub1(
    f,
    "  var _recFile=$('recFile');if(_recFile)_recFile.addEventListener('change',onPickFile);\n",
    "  var _recFile=$('recFile');if(_recFile)_recFile.addEventListener('change',onPickFile);\n" + PHREC_JS,
    "JS 연결",
)

save("meeting_form.html", f)

# ══════════════════════════════════════════════════════════════════════
# 2. meetings.html — 녹음기로 갔다가 화면이 닫혔을 때 찾아올 자리
# ══════════════════════════════════════════════════════════════════════
m0 = load("meetings.html")

PHREC_BAR = r"""
  {# z1115 (대표 지시 2026-09-20): 「📱 휴대폰 녹음기로 녹음」 하러 간 회의 —
     녹음기가 떠 있는 동안 크롬이 이 화면을 버릴 수 있어, 돌아왔을 때 어디에 올릴지 바로 보이게 한다.
     표시는 이 브라우저에만 남는다(서버 기록 아님) · 파일이 올라가면 스스로 사라진다. #}
  <div class="mtg-recbar" id="mtgPhRecBar" hidden style="background:#FFF7ED;border-color:#FED7AA;">
    <div class="mtg-recbar-ttl" style="color:#C2410C;">📱 휴대폰 녹음기로 녹음하던 회의</div>
    <div class="mtg-recbar-row">
      <a id="mtgPhRecLink" href="/meetings">회의 열기</a>
      <span class="mtg-recbar-sub" id="mtgPhRecWhen"></span>
      <button type="button" class="btn btn-secondary" id="mtgPhRecDrop">표시 지우기</button>
    </div>
    <div class="mtg-recbar-hint">녹음기에서 녹음을 마쳤으면 이 회의를 열어 「📁 음성 파일 올리기」로 그 파일을 올리세요.
      녹음 파일은 <b>휴대폰 녹음기에 그대로</b> 있습니다.</div>
  </div>
  <script>
  /* z1115: 표시가 남아 있으면(12시간 안) 목록 맨 위에 보여 준다. SPA 로 .main 만 바뀌어도 돌도록 이 안에 둔다. */
  (function(){
    var KEY='knk_mtg_phonerec', bar=document.getElementById('mtgPhRecBar');
    if(!bar) return;
    var v=null; try{ v=JSON.parse(localStorage.getItem(KEY)||'null'); }catch(_){ v=null; }
    if(!v||!v.id||!v.at||(Date.now()-v.at)>12*3600*1000){ try{ if(v) localStorage.removeItem(KEY); }catch(_){} return; }
    var a=document.getElementById('mtgPhRecLink');
    if(a){ a.href='/meetings/'+v.id; a.textContent=(v.title||'제목 없는 회의')+' 열기'; }
    var w=document.getElementById('mtgPhRecWhen');
    if(w){ var mn=Math.round((Date.now()-v.at)/60000);
           w.textContent=(mn<1?'방금':(mn<60?(mn+'분 전'):(Math.floor(mn/60)+'시간 전')))+' 녹음기로 이동'; }
    var d=document.getElementById('mtgPhRecDrop');
    if(d) d.addEventListener('click',function(){ try{ localStorage.removeItem(KEY); }catch(_){} bar.hidden=true; });
    bar.hidden=false;
  })();
  </script>
"""
m = sub1(m0, '\n  <div class="section">\n    {% for m in meetings %}',
         PHREC_BAR + '\n  <div class="section">\n    {% for m in meetings %}', "목록 표시줄")
save("meetings.html", m)

print("[OK] meeting_form.html %d → %d 글자" % (len(f0), len(f)))
print("[OK] meetings.html    %d → %d 글자" % (len(m0), len(m)))
for k, got, want in [("capture(입력 2 + 주석 1)", f.count("capture"), 3),
                     ("recFileCap", f.count("recFileCap"), 3),
                     ("recPhoneRecWrap", f.count("recPhoneRecWrap"), 3),
                     ("recPlatNote(상자 2 + JS 1)", f.count("recPlatNote"), 3),
                     ("phrecClear", f.count("phrecClear"), 2),
                     ("mtgPhRecBar", m.count("mtgPhRecBar"), 2)]:
    print("   %-28s %d  %s" % (k, got, "OK" if got == want else "⚠ %d 예상" % want))
    assert got == want, k
