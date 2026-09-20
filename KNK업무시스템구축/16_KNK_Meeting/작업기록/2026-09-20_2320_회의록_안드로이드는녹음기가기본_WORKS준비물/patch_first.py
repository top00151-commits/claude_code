# -*- coding: utf-8 -*-
"""z1118 — 이음 「▶ 회의 시작」 → 안드로이드는 **휴대폰 녹음기가 기본** (대표 지시 2026-09-20)

대표 지시: 「이음에서 회의 시작하기 누르면 웹으로 우선 녹음이 되는데, 이걸 기본으로 안드로이드 녹음기로
          자동으로 되면 바로 모든 게 해결될 것 같다. 아이폰 iOS 는 지금 경우(웹)를 적용해야 하고.」

지금(z1116): 착지하면 **이 화면 녹음**이 먼저 켜지고, 그 위에 「녹음기로 바꾸기」 안내가 뜬다.
바꾼다: 안드로이드는 **이 화면 녹음을 아예 켜지 않고**, 맨 위 큰 단추 한 번으로 녹음기가 열린다.
🔴 브라우저는 '사람이 누른 것' 없이는 녹음기를 못 연다 → 한 번 누르는 것은 없앨 수 없다.
   그래서 **30초 안에 아무것도 안 누르면** 예전처럼 이 화면 녹음을 켠다(아예 녹음이 없는 사고 방지).
아이폰·PC 는 지금 그대로(이 화면 녹음 자동 시작 + z1115 안내).

사용: py patch_first.py <원본 폴더> <결과 폴더>
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
SRC, DST = sys.argv[1], sys.argv[2]
os.makedirs(DST, exist_ok=True)


def load(name):
    s = io.open(os.path.join(SRC, name), encoding="utf-8", newline="").read()
    assert "\r\n" not in s, name + ": CRLF 원본 — git show 결과(LF)를 쓸 것"
    return s


def save(name, s):
    with io.open(os.path.join(DST, name), "w", encoding="utf-8", newline="") as f:
        f.write(s)


def sub1(s, old, new, tag):
    n = s.count(old)
    assert n == 1, "%s: 앵커 %d개(1개여야 함)" % (tag, n)
    return s.replace(old, new)


f0 = load("meeting_form.html")
f = f0

# ── ① 안내 상자 글을 상황에 따라 바꿀 수 있게 이름표를 붙인다
f = sub1(
    f,
    '          <div class="phrec-lead-ttl">📱 이 회의, 휴대폰 녹음기로 녹음하시겠어요?</div>\n'
    '          <div class="phrec-lead-sub">이 화면 녹음은 <b>다른 앱으로 넘어가면 그동안 소리가 들어오지 않습니다</b>'
    '(2026-09-20 실측 95초). 녹음기로 바꾸면 <b>다른 앱을 써도 끊기지 않고</b>, 지금까지 녹음한 것도 그대로 이어집니다.</div>\n',
    '          <div class="phrec-lead-ttl" id="recPhoneLeadTtl">📱 이 회의, 휴대폰 녹음기로 녹음하시겠어요?</div>\n'
    '          <div class="phrec-lead-sub" id="recPhoneLeadWhy">이 화면 녹음은 <b>다른 앱으로 넘어가면 그동안 소리가 들어오지 않습니다</b>'
    '(2026-09-20 실측 95초). 녹음기로 바꾸면 <b>다른 앱을 써도 끊기지 않고</b>, 지금까지 녹음한 것도 그대로 이어집니다.</div>\n',
    "상자 윗글 이름표",
)
f = sub1(
    f,
    '          <div class="phrec-lead-sub">이 화면에서 계속 녹음하시려면 이 안내를 지나치세요 — '
    '다만 <b>화면을 켠 채로</b> 두셔야 합니다.</div>\n',
    '          <div class="phrec-lead-sub" id="recPhoneLeadFoot">이 화면에서 계속 녹음하시려면 이 안내를 지나치세요 — '
    '다만 <b>화면을 켠 채로</b> 두셔야 합니다.</div>\n',
    "상자 아랫글 이름표",
)

# ── ② 단추 글자도 상황에 따라(입력은 건드리지 않게 글자만 따로)
f = sub1(
    f,
    '          <label class="btn btn-primary rec-phone" id="recPhoneRecWrap" hidden>📱 휴대폰 녹음기로 녹음'
    '<input type="file" id="recFileCap"',
    '          <label class="btn btn-primary rec-phone" id="recPhoneRecWrap" hidden>'
    '<span id="recPhoneBtnLbl">📱 휴대폰 녹음기로 녹음</span>'
    '<input type="file" id="recFileCap"',
    "단추 글자 이름표",
)

# ── ③ 상자를 상황에 맞춰 띄운다 — 'first'(아직 녹음 안 켬) / 'running'(이 화면 녹음 중)
f = sub1(
    f,
    "  function phrecLeadShow(){\n"
    "    var lead=$('recPhoneLead'), slot=$('recPhoneLeadSlot');\n"
    "    if(!lead||!slot||!_phWrap||!_isAndroid) return;\n"
    "    try{ slot.appendChild(_phWrap); }catch(_){ return; }   // 단추는 하나만 둔다(입력이 둘이 되지 않게)\n"
    "    _phWrap.hidden=false; lead.hidden=false;\n"
    "    try{ lead.scrollIntoView({block:'start'}); }catch(_){}\n"
    "  }\n",
    "  function phrecLeadShow(mode, footHtml){\n"
    "    var lead=$('recPhoneLead'), slot=$('recPhoneLeadSlot');\n"
    "    if(!lead||!slot||!_phWrap||!_isAndroid) return;\n"
    "    try{ slot.appendChild(_phWrap); }catch(_){ return; }   // 단추는 하나만 둔다(입력이 둘이 되지 않게)\n"
    "    var t=$('recPhoneLeadTtl'), w=$('recPhoneLeadWhy'), ft=$('recPhoneLeadFoot'), bl=$('recPhoneBtnLbl');\n"
    "    if(mode==='first'){\n"
    "      // z1118: 안드로이드 기본 — 이 화면 녹음을 아직 켜지 않았다. 녹음이 '아직 안 됐다'는 것부터 분명히.\n"
    "      if(t) t.textContent='🔴 아직 녹음이 시작되지 않았습니다';\n"
    "      if(bl) bl.textContent='📱 녹음기로 회의 녹음 시작';\n"
    "      if(w) w.innerHTML='누르면 <b>휴대폰 녹음기</b>가 열립니다 — 다른 앱을 보거나 화면이 꺼져도 '\n"
    "        +'<b>녹음이 끊기지 않습니다</b>. 녹음을 마치고 저장하면 이 화면으로 돌아와 <b>자동으로 정리</b>됩니다.';\n"
    "      if(ft) ft.innerHTML='<b>30초 안에 누르지 않으면</b> 이 화면에서 녹음을 시작합니다'\n"
    "        +'(그때는 <b>이 화면을 켠 채로</b> 두셔야 합니다).';\n"
    "    } else {\n"
    "      if(t) t.textContent='📱 이 회의, 휴대폰 녹음기로 녹음하시겠어요?';\n"
    "      if(bl) bl.textContent='📱 휴대폰 녹음기로 녹음';\n"
    "      if(w) w.innerHTML='이 화면 녹음은 <b>다른 앱으로 넘어가면 그동안 소리가 들어오지 않습니다</b>'\n"
    "        +'(2026-09-20 실측 95초). 녹음기로 바꾸면 <b>다른 앱을 써도 끊기지 않고</b>, 지금까지 녹음한 것도 그대로 이어집니다.';\n"
    "      if(ft) ft.innerHTML='이 화면에서 계속 녹음하시려면 이 안내를 지나치세요 — 다만 <b>화면을 켠 채로</b> 두셔야 합니다.';\n"
    "    }\n"
    "    if(ft && footHtml) ft.innerHTML=footHtml;   // z1118: 왜 이렇게 됐는지는 상자에 남긴다(상태줄은 곧 덮인다)\n"
    "    _phWrap.hidden=false; lead.hidden=false;\n"
    "    try{ lead.scrollIntoView({block:'start'}); }catch(_){}\n"
    "  }\n",
    "상자 모드",
)

# ── ④ 눌렀으면 30초 대기를 끈다
f = sub1(
    f,
    "      _phrecChosen=true;\n"
    "      if(_mr && _mr.state!=='inactive'){\n",
    "      _phrecChosen=true;\n"
    "      try{ if(_phFallback){ clearTimeout(_phFallback); _phFallback=null; } }catch(_){}   // z1118: 30초 대기 끔\n"
    "      if(_mr && _mr.state!=='inactive'){\n",
    "30초 대기 끄기",
)

# ── ⑤ 변수
f = sub1(
    f,
    "  var _recHandoff=false,_phrecChosen=false;   // z1116: 휴대폰 녹음기로 넘기는 중(겹침·두 번 정리 방지)\n",
    "  var _recHandoff=false,_phrecChosen=false;   // z1116: 휴대폰 녹음기로 넘기는 중(겹침·두 번 정리 방지)\n"
    "  var _phFallback=null;                       // z1118: 안드로이드 착지 — 30초 안에 안 누르면 이 화면 녹음(안전망)\n",
    "변수",
)

# ── ⑥ 착지 — 안드로이드는 녹음기가 기본, 아이폰·PC 는 지금 그대로
OLD = """        phrecLeadShow();   // z1116: 안드로이드면 「📱 휴대폰 녹음기로 녹음」을 맨 위 큰 단추로
        var _rb=$('recBtn');
        if (!M.has_audio){
          if (_rb && !_rb.dataset.on) _rb.textContent='🎙 녹음 시작';
          try{ _rt.scrollIntoView({block:'start'}); }catch(_){}
          // 🎤 먼저 마이크 허용 상태를 본다 (2026-09-17) — 허용 저장=바로 녹음 · 처음=크롬 창 안내 · 막힘=요청하지 않고 푸는 방법
          micState().then(function(ms){
            if (!_alive()) return;
            if (ms === 'denied'){
              micHelp('block');
              recSt('마이크가 막혀 있어 녹음을 자동으로 시작하지 못했습니다 — 위 안내대로 허용한 뒤 「🎙 녹음 시작」을 누르세요.','err');
              return;
            }
            recSt(ms === 'granted' ? '회의 녹음을 시작합니다…'
                                   : (_isPhone ? '회의 녹음을 시작합니다… 마이크 허용 창이 뜨면 「이번에만」이 아닌 허용을 눌러주세요.'
                                               : '회의 녹음을 시작합니다… 마이크 허용 창이 뜨면 「이번에만 허용」 말고 「사이트에 있는 동안 허용」을 눌러주세요.'));
            recStart();   // 실패하면 recStart 가 까닭별 안내를 띄운다
          });
        } else {
"""
NEW = """        // z1118 (대표 지시 2026-09-20): 안드로이드는 **휴대폰 녹음기가 기본** — 이 화면 녹음을 먼저 켜지 않는다.
        //   이 화면 녹음은 다른 앱으로 넘어가면 그동안 소리가 안 들어온다(실측 95초). 아이폰·PC 는 지금 그대로.
        //   🔴 브라우저는 '사람이 누른 것' 없이는 녹음기를 못 연다 → 한 번 누르는 것은 없앨 수 없다.
        var _phFirst = _isAndroid && !!$('recPhoneRecWrap') && !!$('recFileCap');
        phrecLeadShow(_phFirst ? 'first' : 'running');
        var _rb=$('recBtn');
        // 🎤 마이크 허용 상태를 보고 이 화면 녹음을 켠다 (2026-09-17) — 허용 저장=바로 · 처음=크롬 창 안내 · 막힘=푸는 방법
        function autorecStartHere(){
          if (!_alive() || _phrecChosen) return;
          if (_mr && _mr.state !== 'inactive') return;   // 이미 녹음 중
          micState().then(function(ms){
            if (!_alive() || _phrecChosen) return;
            if (ms === 'denied'){
              micHelp('block');
              recSt('마이크가 막혀 있어 녹음을 자동으로 시작하지 못했습니다 — 위 안내대로 허용한 뒤 「🎙 녹음 시작」을 누르세요.','err');
              return;
            }
            recSt(ms === 'granted' ? '회의 녹음을 시작합니다…'
                                   : (_isPhone ? '회의 녹음을 시작합니다… 마이크 허용 창이 뜨면 「이번에만」이 아닌 허용을 눌러주세요.'
                                               : '회의 녹음을 시작합니다… 마이크 허용 창이 뜨면 「이번에만 허용」 말고 「사이트에 있는 동안 허용」을 눌러주세요.'));
            recStart();   // 실패하면 recStart 가 까닭별 안내를 띄운다
          });
        }
        if (!M.has_audio){
          if (_rb && !_rb.dataset.on) _rb.textContent='🎙 녹음 시작';
          try{ _rt.scrollIntoView({block:'start'}); }catch(_){}
          if (_phFirst){
            recSt('📱 위의 「녹음기로 회의 녹음 시작」을 눌러 주세요 — 다른 앱을 봐도 끊기지 않습니다. '
                 +'30초 안에 누르지 않으면 이 화면에서 녹음을 시작합니다.');
            _phFallback = setTimeout(function(){
              _phFallback=null;
              if (!_alive() || _phrecChosen) return;
              if (_mr && _mr.state !== 'inactive') return;
              phrecLeadShow('running',
                '⚠ <b>30초 동안 고르지 않아 이 화면에서 녹음을 시작했습니다</b> — 이 화면을 켠 채로 두세요. '
                + '위 단추를 누르면 지금이라도 <b>휴대폰 녹음기</b>로 바꿀 수 있습니다(지금까지 녹음은 그대로 이어집니다).');
              recSt('30초 동안 고르지 않아 이 화면에서 녹음을 시작합니다 — 이 화면을 켜 두세요.','err');
              autorecStartHere();
            }, 30000);
          } else {
            autorecStartHere();
          }
        } else {
"""
f = sub1(f, OLD, NEW, "착지 기본 바꾸기")

save("meeting_form.html", f)
print("[OK] meeting_form.html %d → %d 글자" % (len(f0), len(f)))
for k, got, want in [("recPhoneLeadTtl", f.count("recPhoneLeadTtl"), 2),
                     ("recPhoneLeadWhy", f.count("recPhoneLeadWhy"), 2),
                     ("recPhoneLeadFoot", f.count("recPhoneLeadFoot"), 2),
                     ("recPhoneBtnLbl", f.count("recPhoneBtnLbl"), 2),
                     ("_phFallback", f.count("_phFallback"), 6),
                     ("_phFirst", f.count("_phFirst"), 3),
                     ("autorecStartHere", f.count("autorecStartHere"), 3),
                     ("phrecLeadShow", f.count("phrecLeadShow"), 3)]:
    print("   %-18s %d  %s" % (k, got, "OK" if got == want else "⚠ %d 예상" % want))
    assert got == want, k
