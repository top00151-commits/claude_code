# -*- coding: utf-8 -*-
"""z1130 — 휴대폰 회의록 녹음 화면 단순화(대표 지시 2026-09-27) + 「녹음 시작」이 먹통이던 버그 고침
사용: py -3.13 patch_z1130.py <앱 사본 경로>

대표 지시: 「사진2에 녹음시작을 누르면 아무런 변화가 없어… 지금 너무 복잡하게 순서가 꼬인 것 같아… 다른 방법을 찾아 봤으면」
결정(보기 중): **휴대폰은 녹음기 한 길만** — 안내 2줄 + 「📁 음성 파일 올리기」만 보이고,
              이 화면 녹음·짧은 녹음·기기별 안내는 「다른 방법」으로 접는다. 30초 자동 시작도 없앤다.

🔴 버그(재현함): 「휴대폰 녹음기로 녹음할게요」를 누르면 `_phrecChosen=true` 가 켜지는데(z1116 겹침 방지),
   그 뒤 「🎙 녹음 시작」을 눌러도 recStart 가 조용히 되돌아갔다(서버 요청 0건·오류도 없음).
   → 사람이 「녹음 시작」을 직접 누르면 그 표시를 푼다.
"""
import os
import sys

if len(sys.argv) < 2:
    print("사용: patch_z1130.py <앱 사본 경로>")
    raise SystemExit(2)
APP = sys.argv[1]
P = os.path.join(APP, "app", "templates", "meeting_form.html")
src = open(P, encoding="utf-8").read()
orig = src
done = []


def sub(name, old, new, count=1):
    global src
    n = src.count(old)
    if n != count:
        print("  [실패] %s — 찾은 수 %d (바라던 수 %d)" % (name, n, count))
        raise SystemExit(1)
    src = src.replace(old, new)
    done.append(name)
    print("  [고침] %s" % name)


OLD_GUIDE = (
    '        <!-- z1129: 웹에서는 녹음기 앱을 열 수 없다(크롬은 BROWSABLE 을 적어 둔 앱만 연다 · 대표 실물 4번) →\n'
    '             홈 화면에서 직접 여는 길을 첫 안내로. 안드로이드에서만 보인다. -->\n'
    '        <div class="phrec-lead" id="recPhoneGuide" hidden>\n'
    '          <div class="phrec-lead-ttl">📱 휴대폰 녹음기로 녹음 — 다른 앱을 봐도·화면이 꺼져도 안 끊깁니다</div>\n'
    '          <div class="phrec-lead-sub">\n'
    '            ① 휴대폰 <b>홈 화면에서 「음성 녹음」</b>을 열어 녹음하세요(이 화면은 닫으셔도 됩니다).<br>\n'
    '            ② 회의가 끝나면 녹음기에서 <b>「공유」 → 「KNK WORKS」</b>를 고르세요.<br>\n'
    '            ③ <b>「＋ 새 회의록으로 정리」</b>(또는 회의 고르기)를 누르면 <b>음성→글자·AI 정리까지 자동</b>으로 됩니다.<br>\n'
    '            <span style="opacity:.8">※ 크롬은 웹에서 녹음기 앱을 열 수 없어(2026-09-27 확인) 홈 화면에서 직접 엽니다.</span>\n'
    '          </div>\n'
    '        </div>\n')

NEW_GUIDE = (
    '        <!-- z1130(대표 지시 2026-09-27): 휴대폰은 녹음기 한 길만 — 안내 2줄 + 올리기만 두고,\n'
    '             이 화면 녹음·짧은 녹음·기기별 안내는 아래 「다른 방법」으로 접는다. 안드로이드에서만 보인다. -->\n'
    '        <div class="phrec-lead" id="recPhoneGuide" hidden>\n'
    '          <div class="phrec-lead-ttl">🎙 이 회의 녹음</div>\n'
    '          <div class="phrec-lead-sub">\n'
    '            ① 휴대폰 <b>홈 화면에서 「음성 녹음」</b>을 열어 녹음하세요 — 다른 앱을 보거나 화면이 꺼져도 <b>안 끊깁니다</b>(이 화면은 닫으셔도 됩니다).<br>\n'
    '            ② 끝나면 녹음기에서 <b>「공유 → KNK WORKS」</b> — 회의를 고르면 <b>음성→글자·AI 정리까지 자동</b>입니다.\n'
    '          </div>\n'
    '        </div>\n'
    '        <details class="mf-section" id="recOther" hidden>\n'
    '          <summary>다른 방법 <span style="font-weight:600;color:var(--qv-ink-3);">(이 화면에서 녹음 · 짧은 회의)</span></summary>\n'
    '          <div id="recOtherSlot" style="margin-top:10px;display:flex;flex-direction:column;gap:10px;align-items:flex-start;"></div>\n'
    '        </details>\n')

# ── HTML ①·② : 안내 카드 두 곳(새 회의록 화면·상세 화면)을 새 카드 + 「다른 방법」 접기로
sub("안내 카드 2곳 → 2줄 안내 + 「다른 방법」 접기", OLD_GUIDE, NEW_GUIDE, count=2)

# ── HTML ③ : 상세 화면 「휴대폰 녹음기로 녹음할게요」 단추 삭제(누를 게 없어졌다)
sub("상세 화면 「휴대폰 녹음기로 녹음할게요」 단추 삭제",
    '          <button class="btn btn-primary rec-phone" type="button" id="recPhoneMine" hidden>📱 휴대폰 녹음기로 녹음할게요</button>\n',
    '')

# ── CSS : 접기 상자가 아이폰·PC 에서 안 보이게(안전판)
sub("접기 상자 숨김 규칙",
    ".rec-phone[hidden] { display:none !important; }",
    ".rec-phone[hidden] { display:none !important; }\n#recOther[hidden] { display:none !important; }")

# ── JS ① : 안내 보이기 + 나머지 단추를 「다른 방법」 안으로 옮기기
i = src.index("  // ── z1129: 웹에서는 녹음기 앱을 열 수 없다")
j = src.index("  if(_phWrap&&_phIn&&_isAndroid){", i)
src = src[:i] + (
    "  // ── z1130(대표 지시 2026-09-27 「너무 복잡하다」): 휴대폰은 녹음기 한 길만 ──\n"
    "  //   웹에서는 녹음기 앱을 열 수 없고(크롬은 BROWSABLE 앱만 연다 · 대표 실물 4번 확인),\n"
    "  //   이 화면 녹음은 다른 앱으로 가면 소리가 안 들어온다(실측 95초) → 휴대폰에서는 '홈 화면 녹음기' 하나만 크게 안내하고\n"
    "  //   이 화면 녹음·짧은 녹음·기기별 안내는 「다른 방법」으로 접는다(자동 시작도 없앤다).\n"
    "  var _guideBox=$('recPhoneGuide'), _otherBox=$('recOther'), _otherSlot=$('recOtherSlot');\n"
    "  var _appBtn=null;   // z1130: 앱을 여는 단추는 없다(웹에서 못 연다)\n"
    "  if(_isAndroid&&_guideBox){\n"
    "    _guideBox.hidden=false;\n"
    "    if(_otherBox&&_otherSlot){\n"
    "      _otherBox.hidden=false;\n"
    "      try{\n"
    "        ['recPhoneRecWrap','recBtn','recPauseBtn','recTime','recPlatNote'].forEach(function(id){\n"
    "          var el=$(id); if(el) _otherSlot.appendChild(el);   // 접기 안으로 옮긴다(상태줄·녹음 띠는 밖에 둔다)\n"
    "        });\n"
    "      }catch(_){}\n"
    "    }\n"
    "  }\n"
) + src[j:]
done.append("JS: 안내 보이기 + 나머지를 「다른 방법」 안으로")
print("  [고침] JS: 안내 보이기 + 나머지를 「다른 방법」 안으로")

# ── JS ② : 🔴 버그 — 사람이 「녹음 시작」을 누르면 '휴대폰 녹음기로 간다' 표시를 푼다
sub("🔴 「녹음 시작」 먹통 버그 고침",
    "  var _recBtn=$('recBtn');if(_recBtn)_recBtn.addEventListener('click',function(){if(_recBtn.dataset.on)recStop();else recStart();});",
    "  // 🔴 z1130: 사람이 직접 「녹음 시작」을 눌렀다 = 마음을 바꾼 것 → 휴대폰 녹음기로 넘기던 표시를 푼다\n"
    "  //   (그 표시가 켜진 채로 두면 recStart 가 조용히 되돌아가 '눌러도 아무 일 없음'이 된다 — 대표 신고 2026-09-27)\n"
    "  var _recBtn=$('recBtn');if(_recBtn)_recBtn.addEventListener('click',function(){\n"
    "    if(_recBtn.dataset.on){ recStop(); return; }\n"
    "    _phrecChosen=false; _recHandoff=false;\n"
    "    try{ if(_phFallback){ clearTimeout(_phFallback); _phFallback=null; } }catch(_){}\n"
    "    if(_otherBox) _otherBox.open=true;\n"
    "    recStart();\n"
    "  });")

# ── JS ③ : 옛 안내 상자(phrec-lead)는 휴대폰에서 더 쓰지 않는다
sub("옛 고르기 상자 끄기",
    "  function phrecLeadShow(mode, footHtml){\n"
    "    var lead=$('recPhoneLead'), slot=$('recPhoneLeadSlot');\n",
    "  function phrecLeadShow(mode, footHtml){\n"
    "    if(_isAndroid && _guideBox) return;   // z1130: 휴대폰은 위 2줄 안내 하나로 끝낸다(상자를 겹쳐 띄우지 않는다)\n"
    "    var lead=$('recPhoneLead'), slot=$('recPhoneLeadSlot');\n")

# ── JS ④ : 이음 「▶ 회의 시작」 — 휴대폰은 30초 자동 시작을 없애고 안내만
sub("이음 회의 시작 — 휴대폰 판정",
    "        var _phFirst = _isAndroid && !!$('recPhoneRecWrap') && !!$('recFileCap');\n"
    "        phrecLeadShow(_phFirst ? 'first' : 'running');\n",
    "        var _phFirst = _isAndroid && !!_guideBox;\n"
    "        if(!_phFirst) phrecLeadShow('running');\n")

i2 = src.index("          if (_phFirst){\n            recSt('📱 휴대폰 녹음기로 녹음하시려면")
j2 = src.index("          } else {\n            autorecStartHere();\n          }\n", i2)
src = src[:i2] + (
    "          if (_phFirst){\n"
    "            // z1130: 30초 뒤 이 화면 녹음을 자동으로 켜던 것을 없앴다 — 화면을 떠나 있으면 소리가 안 들어와\n"
    "            //   '녹음된 줄 알았는데 빈 녹음'이 되기 때문(대표 지시 「너무 복잡하다」).\n"
    "            recSt('🎙 휴대폰 홈 화면에서 「음성 녹음」을 열어 녹음하세요 — 끝나면 녹음기에서 「공유 → KNK WORKS」로 이 회의를 고르면 자동으로 정리됩니다.');\n"
) + src[j2:]
done.append("이음 회의 시작 — 30초 자동 시작 없앰")
print("  [고침] 이음 회의 시작 — 30초 자동 시작 없앰")

# ── JS ④-2 : 옛 상자의 「30초」 문구도 사실대로(자동 시작을 없앴다)
sub("옛 상자 30초 문구 없애기",
    "      if(ft) ft.innerHTML='<b>30초 안에 누르지 않으면</b> 이 화면에서 녹음을 시작합니다'\n"
    "        +'(그때는 <b>이 화면을 켠 채로</b> 두셔야 합니다).';",
    "      if(ft) ft.innerHTML='이 화면 녹음은 <b>화면을 켠 채로</b> 두어야 소리가 들어옵니다.';")

# ── JS ⑤ : 기기별 안내 짧게(이제 「다른 방법」 안에 있다)
i3 = src.index("      el.innerHTML='📱 <b>안드로이드</b> — 회의 중에 다른 앱을 보거나")
j3 = src.index("      el.hidden=false;", i3)
src = src[:i3] + (
    "      el.innerHTML='📱 <b>안드로이드</b> — 회의 녹음은 위 안내대로 <b>홈 화면의 「음성 녹음」</b>으로 하세요. '\n"
    "        +'여기 두 가지는 보조입니다: 「🎙 녹음하며 회의」는 <b>이 화면을 켜 둘 때만</b> 소리가 들어오고'\n"
    "        +'(2026-09-20 실측 95초 무음), 「📱 녹음기로 바로 녹음(짧은 회의)」은 <b>다른 앱으로 넘어가면 저장되고 끝납니다</b>'\n"
    "        +'(2026-09-26 실사 「최대 5분 16초」).';\n"
) + src[j3:]
done.append("기기별 안내 짧게")
print("  [고침] 기기별 안내 짧게")

# ── JS ⑥ : 녹음이 시작되면 「다른 방법」을 펼쳐 둔다(멈추기 단추가 접혀 있지 않게)
sub("멈춘 녹음 상자가 뜨면 「다른 방법」 펼쳐 두기",
    "  function recResumeShow(on){ var box=$('recResume'); if(box) box.style.display=on?'':'none'; }",
    "  function recResumeShow(on){ var box=$('recResume'); if(box) box.style.display=on?'':'none';\n"
    "    try{ if(on && _otherBox) _otherBox.open=true; }catch(_){}   // z1130: 이어서 녹음 단추가 접힌 채 숨지 않게\n  }")

sub("녹음 중이면 「다른 방법」 펼쳐 두기",
    "      var b=$('recBtn');if(b){b.textContent='⏹ 녹음 종료 (자동 정리 시작)';b.classList.add('on');b.dataset.on='1';}",
    "      var b=$('recBtn');if(b){b.textContent='⏹ 녹음 종료 (자동 정리 시작)';b.classList.add('on');b.dataset.on='1';}\n"
    "      try{ if(_otherBox) _otherBox.open=true; }catch(_){}   // z1130: 멈추기 단추가 접힌 채 숨지 않게")

if src == orig:
    print("바뀐 것이 없다 — 중지")
    raise SystemExit(1)
for bad in ("recPhoneMine", "30초 안에 누르지 않으면"):
    if bad in src:
        print("[실패] 옛 것이 남아 있다:", bad)
        raise SystemExit(1)
bak = P + ".bak_z1130"
if not os.path.exists(bak):
    open(bak, "w", encoding="utf-8").write(orig)
tmp = P + ".tmp_z1130"
with open(tmp, "w", encoding="utf-8", newline="") as f:
    f.write(src)
os.replace(tmp, P)
print("\n[완료] z1130 %d곳 고침 → %s" % (len(done), P))
