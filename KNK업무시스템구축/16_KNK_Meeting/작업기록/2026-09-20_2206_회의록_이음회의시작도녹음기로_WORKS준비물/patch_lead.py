# -*- coding: utf-8 -*-
"""z1116 — 이음 회의 카드 「▶ 회의 시작」으로 들어와도 휴대폰 녹음기로 녹음 (대표 지시 2026-09-20)

대표 지시: 「이음 카드에서도 회의 시작을 누르면 녹음기로 녹음될 수 있도록 해줘.」

이음 카드 「▶ 회의 시작」 = WORKS `/meetings/{id}?autorec=1` 착지 → 지금은 **이 화면 녹음**이 자동으로 시작된다.
그 녹음은 다른 앱으로 넘어가면 그동안 소리가 안 들어온다(2026-09-20 실측 95초).
→ 착지 화면 맨 위에 「📱 휴대폰 녹음기로 녹음」을 **큰 첫 선택**으로 올린다(안드로이드).
  자동 시작은 그대로 둔다(안전망 — 누르지 않아도 녹음은 되고 있어야 하므로).

🔴 z1115 결함도 함께 고침: 이 화면 녹음이 도는 중에 녹음기 단추를 누르면 **두 녹음이 겹쳤다.**
   → 넘길 때 이 화면 녹음을 깨끗이 마치고(서버 저장은 그대로 남김), 정리는 녹음기 파일까지 받은 뒤 **한 번만** 한다.
   서버는 이미 '아직 글자로 안 바꾼 녹음'을 순서대로 변환해 이어 붙인다(_rec_add_pending → _stt_worker) → 서버 변경 없음.

사용: py patch_lead.py <원본 폴더> <결과 폴더>
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

# ── ① CSS — 착지 화면 첫 안내 상자
f = sub1(
    f,
    ".rec-phone[hidden] { display:none !important; }\n",
    ".rec-phone[hidden] { display:none !important; }\n"
    "/* ── z1116 이음 「▶ 회의 시작」 착지 — 녹음기로 넘어가는 첫 안내 ── */\n"
    ".phrec-lead { border:2px solid var(--knk-red); border-radius:14px; padding:14px 16px; margin:10px 0 14px;\n"
    "  background:#FFF7ED; }\n"
    ".phrec-lead[hidden] { display:none !important; }\n"
    ".phrec-lead-ttl { font-size:16px; font-weight:800; color: var(--knk-red); margin-bottom:6px; }\n"
    ".phrec-lead-sub { font-size:13px; line-height:1.75; color:#7C2D12; }\n"
    ".phrec-lead-slot { margin:12px 0; }\n"
    ".phrec-lead-slot .rec-phone { width:100%; border:0; border-radius:14px; padding:18px 16px;\n"
    "  font-size:18px; font-weight:800; background: var(--knk-red); color:#fff; cursor:pointer;\n"
    "  display:flex; align-items:center; justify-content:center; gap:8px; }\n",
    "CSS",
)

# ── ② 착지 안내 상자 — 「🔧 다시 하기」 몸통 맨 위
f = sub1(
    f,
    '      <div class="redo-body">\n',
    '      <div class="redo-body">\n'
    '        <!-- z1116: 이음 회의 카드 「▶ 회의 시작」(?autorec=1)으로 들어온 휴대폰에서만 보인다 -->\n'
    '        <div class="phrec-lead" id="recPhoneLead" hidden>\n'
    '          <div class="phrec-lead-ttl">📱 이 회의, 휴대폰 녹음기로 녹음하시겠어요?</div>\n'
    '          <div class="phrec-lead-sub">이 화면 녹음은 <b>다른 앱으로 넘어가면 그동안 소리가 들어오지 않습니다</b>'
    '(2026-09-20 실측 95초). 녹음기로 바꾸면 <b>다른 앱을 써도 끊기지 않고</b>, 지금까지 녹음한 것도 그대로 이어집니다.</div>\n'
    '          <div class="phrec-lead-slot" id="recPhoneLeadSlot"></div>\n'
    '          <div class="phrec-lead-sub">이 화면에서 계속 녹음하시려면 이 안내를 지나치세요 — '
    '다만 <b>화면을 켠 채로</b> 두셔야 합니다.</div>\n'
    '        </div>\n',
    "착지 안내 상자",
)

# ── ③ 넘길 때 이 화면 녹음을 깨끗이 마친다 — 정리는 녹음기 파일까지 받은 뒤 한 번만
f = sub1(
    f,
    "    M.has_audio=true; M.base_ts=j.updated_at||M.base_ts;\n"
    "    await afterAudioSaved(_recWasNew, j.size_kb||0);\n",
    "    M.has_audio=true; M.base_ts=j.updated_at||M.base_ts;\n"
    "    if(_recHandoff){\n"
    "      // z1116: 휴대폰 녹음기로 넘기는 중 — 여기서 정리하면 두 번 정리된다.\n"
    "      //   지금까지 녹음은 서버의 '아직 글자로 안 바꾼 녹음'에 남고, 녹음기 파일이 올라올 때 함께 순서대로 정리된다.\n"
    "      recSt('지금까지 녹음이 서버에 저장됐습니다 ✓ 녹음기에서 녹음을 마치고 이 화면으로 돌아오면 이어서 정리합니다.','ok');\n"
    "      return;\n"
    "    }\n"
    "    await afterAudioSaved(_recWasNew, j.size_kb||0);\n",
    "정리 두 번 막기",
)

# ── ④ 녹음기로 넘기기로 했으면, 늦게 열린 마이크로 이 화면 녹음이 새로 시작되지 않게
f = sub1(
    f,
    "      if(!_alive()){ try{_stream.getTracks().forEach(function(t){t.stop();});}catch(_){} return false; }"
    "   // 그 사이 화면을 떠났다\n",
    "      if(!_alive()){ try{_stream.getTracks().forEach(function(t){t.stop();});}catch(_){} return false; }"
    "   // 그 사이 화면을 떠났다\n"
    "      // z1116: 그 사이 「📱 휴대폰 녹음기로 녹음」을 골랐다 — 이 화면 녹음은 시작하지 않는다(겹침 방지)\n"
    "      if(_phrecChosen){ try{_stream.getTracks().forEach(function(t){t.stop();});}catch(_){} return false; }\n",
    "늦은 마이크 막기",
)

# ── ④-2 🔴 조각을 보낼 때마다 띠를 다시 켜서, 녹음이 끝난 뒤에도 「🔴 녹음 중」이 남았다
#        (평소엔 바로 이어지는 '자동 정리'가 가려 안 보였다 · 넘기기에서 드러남)
f = sub1(
    f,
    "        recBanner(true,_paused);\n",
    "        if(_mr&&_mr.state!=='inactive') recBanner(true,_paused);   "
    "// z1116: 이미 끝난 녹음이면 띠를 다시 켜지 않는다\n",
    "끝난 뒤 띠 되살아남",
)

# ── ⑤ 파일이 들어오면 넘기기 끝
f = sub1(
    f,
    "  function onPickFile(e){\n"
    "    var f=e.target.files&&e.target.files[0];if(!f){return;}\n",
    "  function onPickFile(e){\n"
    "    var f=e.target.files&&e.target.files[0];if(!f){return;}\n"
    "    _recHandoff=false; _phrecChosen=false;   // z1116: 녹음기 파일이 왔다 — 넘기기 끝\n",
    "넘기기 끝",
)

# ── ⑥ 눌렀을 때: 이 화면 녹음을 마치고 넘긴다 + 돌아왔는데 파일이 없으면 알려 준다
OLD_CLICK = (
    "      } else if(M.id){ phrecMark(M.id, (($('mtgTitle')||{}).value)||''); }\n"
    "      recSt('휴대폰 녹음기가 열립니다 — 회의가 끝나면 녹음기에서 저장하세요. 이 화면으로 돌아오면 자동으로 올라갑니다.');\n"
)
NEW_CLICK = (
    "      } else if(M.id){ phrecMark(M.id, (($('mtgTitle')||{}).value)||''); }\n"
    "      // z1116: 이 화면 녹음이 돌고 있으면 깨끗이 마치고 넘긴다(전엔 두 녹음이 겹쳤다).\n"
    "      //   지금까지 조각은 서버에 남고, 정리는 녹음기 파일까지 받은 뒤 한 번만 한다.\n"
    "      _phrecChosen=true;\n"
    "      if(_mr && _mr.state!=='inactive'){\n"
    "        _recHandoff=true;\n"
    "        try{ recStop(); }catch(_){}\n"
    "        recSt('이 화면 녹음을 마치고 휴대폰 녹음기로 넘깁니다 — 지금까지 녹음은 서버에 저장됩니다. "
    "녹음기에서 마치고 돌아오면 이어서 정리합니다.');\n"
    "      } else {\n"
    "        recSt('휴대폰 녹음기가 열립니다 — 회의가 끝나면 녹음기에서 저장하세요. 이 화면으로 돌아오면 자동으로 올라갑니다.');\n"
    "      }\n"
)
f = sub1(f, OLD_CLICK, NEW_CLICK, "넘기기 시작")

# ── ⑦ 변수 + 착지 상자 띄우기 + 빈손 복귀 안내
PHLEAD_JS = r"""
  // ── z1116: 이음 회의 카드 「▶ 회의 시작」으로 들어와도 녹음기로 (대표 지시 2026-09-20) ──
  //   그 길은 /meetings/{id}?autorec=1 로 와서 '이 화면 녹음'이 자동으로 시작된다(안전망 — 그대로 둔다).
  //   안드로이드에서는 그 위에 「📱 휴대폰 녹음기로 녹음」을 큰 첫 선택으로 올려, 한 번 눌러 넘어갈 수 있게 한다.
  //   🔴 브라우저는 '사용자가 누른 것' 없이는 녹음기를 열 수 없다 → 자동으로는 못 열고, 한 번 누르게 한다.
  function phrecLeadShow(){
    var lead=$('recPhoneLead'), slot=$('recPhoneLeadSlot');
    if(!lead||!slot||!_phWrap||!_isAndroid) return;
    try{ slot.appendChild(_phWrap); }catch(_){ return; }   // 단추는 하나만 둔다(입력이 둘이 되지 않게)
    _phWrap.hidden=false; lead.hidden=false;
    try{ lead.scrollIntoView({block:'start'}); }catch(_){}
  }
  // 녹음기에 다녀왔는데 파일을 안 가져왔을 때 — 지금까지 녹음이 어디 있는지 분명히 (한 번만)
  var _phrecBackTold=false;
  document.addEventListener('visibilitychange',function(){
    if(document.visibilityState!=='visible'||!_phrecChosen||_phrecBackTold) return;
    setTimeout(function(){
      if(!_alive()||!_phrecChosen||_phrecBackTold) return;   // 파일이 들어왔으면 _phrecChosen 이 풀린다
      _phrecBackTold=true;
      recSt('녹음기에서 받은 파일이 없습니다 — 「📱 휴대폰 녹음기로 녹음」을 다시 누르거나 「📁 음성 파일 올리기」로 올리세요. '
           +'지금까지 녹음은 서버에 저장돼 있습니다(「🔄 다시 정리」로 이어서 정리).','err');
    },4000);
  });
"""
f = sub1(
    f,
    "    var _rb=$('recBtn'); if(_rb&&_rb.classList.contains('start-big')) _rb.classList.add('alt');\n"
    "  }\n",
    "    var _rb=$('recBtn'); if(_rb&&_rb.classList.contains('start-big')) _rb.classList.add('alt');\n"
    "  }\n" + PHLEAD_JS,
    "착지 JS",
)

# 변수 선언 — 녹음 변수 곁에(호이스팅에 기대지 않게 앞쪽에)
f = sub1(
    f,
    "  var _stream=null,_track=null,_wakeLock=null,_userStop=false,_paused=false,_docTitle='';\n",
    "  var _stream=null,_track=null,_wakeLock=null,_userStop=false,_paused=false,_docTitle='';\n"
    "  var _recHandoff=false,_phrecChosen=false;   // z1116: 휴대폰 녹음기로 넘기는 중(겹침·두 번 정리 방지)\n",
    "변수",
)

# ── ⑧ autorec 착지에서 호출
f = sub1(
    f,
    "        var _rb=$('recBtn');\n        if (!M.has_audio){\n",
    "        phrecLeadShow();   // z1116: 안드로이드면 「📱 휴대폰 녹음기로 녹음」을 맨 위 큰 단추로\n"
    "        var _rb=$('recBtn');\n        if (!M.has_audio){\n",
    "착지 호출",
)

save("meeting_form.html", f)
print("[OK] meeting_form.html %d → %d 글자" % (len(f0), len(f)))
for k, got, want in [("recPhoneLead(Slot 2건 포함)", f.count("recPhoneLead"), 4),
                     ("recPhoneLeadSlot", f.count("recPhoneLeadSlot"), 2),
                     ("_recHandoff", f.count("_recHandoff"), 4),
                     ("_phrecChosen(주석 1건 포함)", f.count("_phrecChosen"), 7),
                     ("phrecLeadShow", f.count("phrecLeadShow"), 2)]:
    print("   %-18s %d  %s" % (k, got, "OK" if got == want else "⚠ %d 예상" % want))
    assert got == want, k
