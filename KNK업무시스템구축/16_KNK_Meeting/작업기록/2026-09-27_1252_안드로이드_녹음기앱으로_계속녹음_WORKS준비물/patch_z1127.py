# -*- coding: utf-8 -*-
"""z1127 — 안드로이드: 「📱 녹음기 앱 열기」로 바꿈 (대표 실사 2026-09-26/27)
  대표 실사: `capture` 로 연 녹음기는 **불려 나온 모드**라 ①다른 앱으로 넘어가면 녹음을 끝내고 저장하고
  ②길이 상한이 걸린다(대표 사진 「최대: 05:16」). 그래서 「다른 앱을 봐도 끊기지 않아요」는 **거짓말이었다**.
  고침 ① 큰 단추 = 「📱 녹음기 앱 열기」(intent 로 녹음기 앱 자체를 연다 → 알림줄에 남아 다른 앱을 봐도 계속 녹음)
       ② 끝난 뒤 = 녹음기에서 「공유 → KNK WORKS」(설치됨) 또는 「📁 음성 파일 올리기」
       ③ 옛 단추(불려 나온 녹음기)는 「짧은 회의용」으로 작게 · 사실대로 적음
       ④ 자동으로 못 열면 `?recapp=manual` 로 돌아와 손으로 여는 길 안내
사용: py patch_z1127.py <앱 사본 폴더>
기준: 운영 z1126(meeting_form cf55702b)"""
import hashlib
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = sys.argv[1]
REL = "app/templates/meeting_form.html"
p = os.path.join(ROOT, REL)
raw = open(p, "rb").read()
h = hashlib.sha256(raw).hexdigest()[:8]
assert h == "cf55702b", f"{REL} 기준이 다름: {h}"
s = raw.decode("utf-8")
assert "\r\n" not in s


def rep(old, new, name, count=1):
    global s
    n = s.count(old)
    assert n == count, f"{name}: 기준 글 {n}곳(기대 {count})"
    s = s.replace(old, new)


# ① CSS — 상자 안 둘째 단추(작게·흰색)
rep(".phrec-lead-slot .rec-phone { width:100%; border:0; border-radius:14px; padding:18px 16px;\n",
    ".phrec-lead-slot .rec-phone.alt { background: var(--qv-surface) !important; color: var(--qv-ink) !important;\n"
    "  border:1px solid var(--qv-line-3) !important; font-size:14px !important; font-weight:700 !important;\n"
    "  padding:12px 14px !important; margin-top:8px; }   /* z1127: 불려 나온 녹음기는 둘째 선택 */\n"
    ".phrec-lead-slot .rec-phone { width:100%; border:0; border-radius:14px; padding:18px 16px;\n",
    "상자 둘째 단추 모양")

# ② 새 회의록 화면(start-btns) — 큰 단추를 「녹음기 앱 열기」로, 옛 단추는 작게·사실대로
rep('        <label class="start-big rec-phone" id="recPhoneRecWrap" hidden>📱 휴대폰 녹음기로 녹음&nbsp;'
    '<span class="start-sub">다른 앱을 봐도 끊기지 않아요</span>'
    '<input type="file" id="recFileCap" accept="audio/*" capture data-knk-no-dropzone style="display:none"></label>\n',
    '        <button class="start-big rec-phone" type="button" id="recOpenApp" hidden>📱 녹음기 앱 열기&nbsp;'
    '<span class="start-sub">다른 앱을 봐도 계속 녹음돼요</span></button>\n'
    '        <label class="start-big rec-phone alt" id="recPhoneRecWrap" hidden>📱 녹음기로 바로 녹음&nbsp;'
    '<span class="start-sub">짧은 회의용 — 다른 앱으로 가면 저장되고 끝납니다</span>'
    '<input type="file" id="recFileCap" accept="audio/*" capture data-knk-no-dropzone style="display:none"></label>\n',
    "새 회의록 화면 단추")

# ③ 상세(다시 하기) 줄 — 같은 두 단추
rep('          <label class="btn btn-primary rec-phone" id="recPhoneRecWrap" hidden><span id="recPhoneBtnLbl">📱 휴대폰 녹음기로 녹음</span>'
    '<input type="file" id="recFileCap" accept="audio/*" capture data-knk-no-dropzone style="display:none"></label>\n',
    '          <button class="btn btn-primary rec-phone" type="button" id="recOpenApp" hidden>📱 녹음기 앱 열기</button>\n'
    '          <label class="btn btn-secondary rec-phone alt" id="recPhoneRecWrap" hidden><span id="recPhoneBtnLbl">📱 녹음기로 바로 녹음(짧은 회의)</span>'
    '<input type="file" id="recFileCap" accept="audio/*" capture data-knk-no-dropzone style="display:none"></label>\n',
    "상세 화면 단추")

# ④ 새 단추 JS — 옛 단추(_phWrap) 처리 바로 뒤
rep("    // 휴대폰에선 이 화면 녹음이 '두 번째 선택' — 색으로만 구분한다\n",
    """  }

  // ── z1127 「📱 녹음기 앱 열기」 — 다른 앱을 봐도 끊기지 않는 유일한 길 (대표 실사 2026-09-26) ──
  //   🔴 `capture` 로 연 녹음기는 **불려 나온 모드**: 파일 하나를 돌려주는 것이 임무라 다른 앱으로 넘어가면
  //      녹음을 끝내고 저장해 버리고, 길이 상한도 걸린다(대표 사진 「최대: 05:16」).
  //   ⭐ 녹음기 **앱 자체**를 열면(LAUNCHER intent) 알림줄에 남아 다른 앱을 봐도 계속 녹음된다.
  //      끝난 파일은 녹음기에서 「공유 → KNK WORKS」(설치된 앱) 또는 이 화면 「📁 음성 파일 올리기」로 붙인다.
  //   🔴 크롬이 못 열면(그 앱이 없거나 막힘) `S.browser_fallback_url` 로 이 화면에 ?recapp=manual 로 돌아온다.
  function recAppIntentUrl(){
    var back=location.href.split('#')[0].replace(/[?&]recapp=manual/, '');
    back += (back.indexOf('?')<0?'?':'&') + 'recapp=manual';
    var ua=navigator.userAgent||'';
    var pkg=/SM-|SAMSUNG|Galaxy|SC-\\d|SCV\\d/i.test(ua) ? 'com.sec.android.app.voicenote'
                                                        : 'com.google.android.apps.recorder';
    return 'intent://#Intent;action=android.intent.action.MAIN;category=android.intent.category.LAUNCHER;'
         + 'package='+pkg+';S.browser_fallback_url='+encodeURIComponent(back)+';end';
  }
  try{ window.__knkRecAppUrl=recAppIntentUrl; }catch(_){}   // 시험이 주소를 들여다볼 수 있게
  var _appBtn=$('recOpenApp');
  if(_appBtn&&_isAndroid){
    _appBtn.hidden=false;
    _appBtn.addEventListener('click',function(){
      // 회의록을 먼저 만들어 두고(기다리지 않는다 — 기다리면 '누름'이 풀린다), 목록 표시줄에 남긴다
      if(!_phSaving){
        _phSaving=Promise.resolve().then(ensureMeetingSaved).then(function(ok){
          if(ok) phrecMark(M.id, (($('mtgTitle')||{}).value)||'');
          return ok;
        }).catch(function(){ return false; });
      } else if(M.id){ phrecMark(M.id, (($('mtgTitle')||{}).value)||''); }
      _phrecChosen=true;
      try{ if(_phFallback){ clearTimeout(_phFallback); _phFallback=null; } }catch(_){}
      if(_mr && _mr.state!=='inactive'){          // 이 화면 녹음이 돌고 있으면 깨끗이 마치고 넘긴다
        _recHandoff=true;
        try{ recStop(); }catch(_){}
      } else if(_recOpen && REC.mine){            // 창이 닫혀 멈춘 내 녹음이 서버에 열려 있으면 닫아 둔다
        _recOpen=false; recResumeShow(false); recNetFinish();
      }
      recSt('녹음기 앱을 엽니다 — 거기서 녹음을 시작하세요. 다른 앱을 봐도 끊기지 않습니다. '
           +'회의가 끝나면 녹음기에서 「공유 → KNK WORKS」로 이 회의를 고르면 자동으로 정리됩니다.');
      try{ location.href=recAppIntentUrl(); }catch(_){}
    });
  }
  if(_phWrap&&_phIn&&_isAndroid){
    // 휴대폰에선 이 화면 녹음이 '두 번째 선택' — 색으로만 구분한다
""",
    "새 단추 JS")

# ⑤ 상자(phrecLeadShow) — 새 단추를 상자 안에도 넣고, 글을 사실대로 + 'manual' 모드
rep("    try{ slot.appendChild(_phWrap); }catch(_){ return; }   // 단추는 하나만 둔다(입력이 둘이 되지 않게)\n",
    "    try{ if(_appBtn) slot.appendChild(_appBtn); slot.appendChild(_phWrap); }catch(_){ return; }   "
    "// 단추는 하나씩만 둔다(입력이 둘이 되지 않게 · z1127: 녹음기 앱 열기가 먼저)\n",
    "상자에 새 단추")

rep("""    if(mode==='first'){
      // z1118: 안드로이드 기본 — 이 화면 녹음을 아직 켜지 않았다. 녹음이 '아직 안 됐다'는 것부터 분명히.
      if(t) t.textContent='🔴 아직 녹음이 시작되지 않았습니다';
      if(bl) bl.textContent='📱 녹음기로 회의 녹음 시작';
      if(w) w.innerHTML='누르면 <b>휴대폰 녹음기</b>가 열립니다 — 다른 앱을 보거나 화면이 꺼져도 '
        +'<b>녹음이 끊기지 않습니다</b>. 녹음을 마치고 저장하면 이 화면으로 돌아와 <b>자동으로 정리</b>됩니다.';
      if(ft) ft.innerHTML='<b>30초 안에 누르지 않으면</b> 이 화면에서 녹음을 시작합니다'
        +'(그때는 <b>이 화면을 켠 채로</b> 두셔야 합니다).';
    } else {
      if(t) t.textContent='📱 이 회의, 휴대폰 녹음기로 녹음하시겠어요?';
      if(bl) bl.textContent='📱 휴대폰 녹음기로 녹음';
      if(w) w.innerHTML='이 화면 녹음은 <b>다른 앱으로 넘어가면 그동안 소리가 들어오지 않습니다</b>'
        +'(2026-09-20 실측 95초). 녹음기로 바꾸면 <b>다른 앱을 써도 끊기지 않고</b>, 지금까지 녹음한 것도 그대로 이어집니다.';
      if(ft) ft.innerHTML='이 화면에서 계속 녹음하시려면 이 안내를 지나치세요 — 다만 <b>화면을 켠 채로</b> 두셔야 합니다.';
    }
""",
    """    if(mode==='manual'){
      // z1127: 크롬이 녹음기 앱을 못 열었다(그 앱이 없거나 막힘) — 손으로 여는 길
      if(t) t.textContent='📱 녹음기 앱을 자동으로 열지 못했습니다';
      if(w) w.innerHTML='휴대폰 홈 화면에서 <b>「음성 녹음」</b>(녹음기) 앱을 직접 열어 녹음을 시작해 주세요 — '
        +'그렇게 하면 <b>다른 앱을 보거나 화면이 꺼져도 계속 녹음</b>됩니다. 회의가 끝나면 녹음기에서 '
        +'<b>「공유 → KNK WORKS」</b>로 이 회의를 고르거나, 이 화면의 <b>「📁 음성 파일 올리기」</b>로 붙이세요.';
      if(ft) ft.innerHTML='급하면 아래 <b>「📱 녹음기로 바로 녹음(짧은 회의)」</b>도 쓸 수 있습니다 — '
        +'다만 그 길은 <b>다른 앱으로 넘어가면 녹음이 저장되고 끝납니다</b>.';
    } else if(mode==='first'){
      // z1118: 안드로이드 기본 — 이 화면 녹음을 아직 켜지 않았다. 녹음이 '아직 안 됐다'는 것부터 분명히.
      if(t) t.textContent='🔴 아직 녹음이 시작되지 않았습니다';
      if(bl) bl.textContent='📱 녹음기로 바로 녹음(짧은 회의)';
      if(w) w.innerHTML='<b>「📱 녹음기 앱 열기」</b>를 누르면 휴대폰 <b>녹음기 앱</b>이 열립니다 — 거기서 녹음을 시작하면 '
        +'<b>다른 앱을 보거나 화면이 꺼져도 계속 녹음</b>됩니다. 회의가 끝나면 녹음기에서 '
        +'<b>「공유 → KNK WORKS」</b>로 이 회의를 고르면 자동으로 정리됩니다.';
      if(ft) ft.innerHTML='<b>30초 안에 누르지 않으면</b> 이 화면에서 녹음을 시작합니다'
        +'(그때는 <b>이 화면을 켠 채로</b> 두셔야 합니다).';
    } else {
      if(t) t.textContent='📱 이 회의, 녹음기 앱으로 녹음하시겠어요?';
      if(bl) bl.textContent='📱 녹음기로 바로 녹음(짧은 회의)';
      if(w) w.innerHTML='이 화면 녹음은 <b>다른 앱으로 넘어가면 그동안 소리가 들어오지 않습니다</b>'
        +'(2026-09-20 실측 95초). <b>「📱 녹음기 앱 열기」</b>로 바꾸면 <b>다른 앱을 써도 계속 녹음</b>되고, '
        +'지금까지 녹음한 것도 그대로 이어집니다(끝나면 「공유 → KNK WORKS」).';
      if(ft) ft.innerHTML='이 화면에서 계속 녹음하시려면 이 안내를 지나치세요 — 다만 <b>화면을 켠 채로</b> 두셔야 합니다.';
    }
""",
    "상자 글")

# ⑥ 상자 열기 — 새 단추도 보이게
rep("    _phWrap.hidden=false; lead.hidden=false;\n",
    "    _phWrap.hidden=false; if(_appBtn&&_isAndroid) _appBtn.hidden=false; lead.hidden=false;\n",
    "상자 열 때 새 단추")

# ⑦ 자동으로 못 열었을 때 — 돌아오면 손으로 여는 길 안내
rep("  // 녹음기에 다녀왔는데 파일을 안 가져왔을 때 — 지금까지 녹음이 어디 있는지 분명히 (한 번만)\n",
    "  // z1127: 녹음기 앱을 자동으로 못 열어 되돌아왔다(?recapp=manual) → 손으로 여는 길을 안내\n"
    "  //   상세 화면에는 상자가 있고, 새 회의록 화면에는 상자가 없다 → 그때는 상태줄로 같은 말을 한다\n"
    "  try{\n"
    "    if(_isAndroid && /[?&]recapp=manual(&|$)/.test(location.search)){\n"
    "      var _rt0=$('redoTools'); if(_rt0) _rt0.open=true;   // 접혀 있으면 상자가 안 보인다\n"
    "      if($('recPhoneLead')) phrecLeadShow('manual');\n"
    "      else recSt('📱 녹음기 앱을 자동으로 열지 못했습니다 — 휴대폰 홈 화면에서 「음성 녹음」을 직접 열어 녹음하세요. '\n"
    "               +'끝나면 녹음기에서 「공유 → KNK WORKS」로 이 회의를 고르거나 「📁 음성 파일 올리기」로 붙이세요.','err');\n"
    "    }\n"
    "  }catch(_){}\n"
    "  // 녹음기에 다녀왔는데 파일을 안 가져왔을 때 — 지금까지 녹음이 어디 있는지 분명히 (한 번만)\n",
    "못 열었을 때 안내")

# ⑧ 돌아왔는데 파일이 없을 때 — 공유 길도 알려 준다
rep("      recSt('녹음기에서 받은 파일이 없습니다 — 「📱 휴대폰 녹음기로 녹음」을 다시 누르거나 「📁 음성 파일 올리기」로 올리세요. '\n",
    "      recSt('녹음기에서 받은 파일이 없습니다 — 녹음기에서 「공유 → KNK WORKS」로 보내거나 「📁 음성 파일 올리기」로 올리세요. '\n",
    "파일 없을 때 안내")

# ⑨ 기기별 안내(안드로이드) — 세 길을 사실대로
rep("""      el.innerHTML='📱 <b>안드로이드</b> — 회의 중에 다른 앱을 보거나 화면이 꺼져도 끊기지 않으려면 '
        +'<b>「📱 휴대폰 녹음기로 녹음」</b>을 쓰세요. 「🎙 녹음하며 회의」는 <b>이 화면을 켜 둘 때만</b> 소리가 들어옵니다 '
        +'— 다른 앱으로 넘어가면 휴대폰이 마이크를 막습니다(2026-09-20 실측 95초).';
""",
    """      el.innerHTML='📱 <b>안드로이드</b> — 회의 중에 다른 앱을 보거나 화면이 꺼져도 끊기지 않으려면 '
        +'<b>「📱 녹음기 앱 열기」</b>로 <b>녹음기 앱에서</b> 녹음하세요(끝나면 녹음기에서 <b>「공유 → KNK WORKS」</b>). '
        +'「📱 녹음기로 바로 녹음(짧은 회의)」은 이 화면이 불러온 녹음기라 <b>다른 앱으로 넘어가면 저장되고 끝나고</b> 길이 상한도 있습니다'
        +'(2026-09-26 실사 「최대 5분 16초」). 「🎙 녹음하며 회의」는 <b>이 화면을 켜 둘 때만</b> 소리가 들어옵니다'
        +'(2026-09-20 실측 95초 무음).';
""",
    "안드로이드 안내")

# ⑩ 착지 30초 안내 — 새 단추 이름으로
rep("            recSt('📱 위의 「녹음기로 회의 녹음 시작」을 눌러 주세요 — 다른 앱을 봐도 끊기지 않습니다. '\n",
    "            recSt('📱 위의 「녹음기 앱 열기」를 눌러 주세요 — 녹음기 앱에서 녹음하면 다른 앱을 봐도 끊기지 않습니다. '\n",
    "착지 안내")

rep("                '⚠ <b>30초 동안 고르지 않아 이 화면에서 녹음을 시작했습니다</b> — 이 화면을 켠 채로 두세요. '\n"
    "                + '위 단추를 누르면 지금이라도 <b>휴대폰 녹음기</b>로 바꿀 수 있습니다(지금까지 녹음은 그대로 이어집니다).');\n",
    "                '⚠ <b>30초 동안 고르지 않아 이 화면에서 녹음을 시작했습니다</b> — 이 화면을 켠 채로 두세요. '\n"
    "                + '위 <b>「📱 녹음기 앱 열기」</b>를 누르면 지금이라도 바꿀 수 있습니다(지금까지 녹음은 그대로 이어집니다).');\n",
    "30초 뒤 상자 글")

assert "다른 앱을 봐도 끊기지 않아요" not in s
assert s.count("recOpenApp") == 3, s.count("recOpenApp")   # 새 회의록 화면 · 상세 화면 · JS 한 곳
tmp = p + ".tmp_z1127"
with io.open(tmp, "w", encoding="utf-8", newline="") as f:
    f.write(s)
os.replace(tmp, p)
print("  [OK]", REL, "→", hashlib.sha256(s.encode("utf-8")).hexdigest()[:8])
