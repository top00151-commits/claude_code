# -*- coding: utf-8 -*-
"""z1129 — 「📱 녹음기 앱 열기」 단추를 없애고 「홈 화면에서 직접 열기」를 첫 안내로
사용: py -3.13 patch_z1129.py <앱 사본 경로>

까닭(2026-09-27 대표 실물 4번 + 크롬 문서):
  · 대표가 단추를 4번 눌렀고 4번 다 크롬이 열기를 거부해 ?recapp=manual 로 되돌아왔다(운영 로그).
  · 크롬 문서: "Only activities with the category filter android.intent.category.BROWSABLE can be
    invoked using this method." → 삼성 「음성 녹음」은 그 표시가 없다 = 웹에서는 못 연다.
  · 게다가 옛 단추는 누를 때 회의록을 먼저 만들어, 실패할 때마다 빈 회의록이 남았다(46·47·49).
→ 단추를 없애고, 홈 화면에서 직접 여는 3단계를 첫 안내로. 상세 화면에는
   「📱 휴대폰 녹음기로 녹음할게요」(이 회의 표시 + 30초 자동 시작 취소)만 남긴다.
"""
import os
import sys

if len(sys.argv) < 2:
    print("사용: patch_z1129.py <앱 사본 경로>")
    raise SystemExit(2)
APP = sys.argv[1]
P = os.path.join(APP, "app", "templates", "meeting_form.html")
src = open(P, encoding="utf-8").read()
orig = src
done = []

GUIDE = (
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


def sub(name, old, new, count=1):
    global src
    n = src.count(old)
    if n != count:
        print("  [실패] %s — 찾은 수 %d (바라던 수 %d)" % (name, n, count))
        raise SystemExit(1)
    src = src.replace(old, new)
    done.append(name)
    print("  [고침] %s" % name)


# ── HTML ①: 새 회의록 화면 — 단추 → 안내 카드
sub("새 회의록 화면: 단추 → 3단계 안내 카드",
    '        <button class="start-big rec-phone" type="button" id="recOpenApp" hidden>📱 녹음기 앱 열기&nbsp;'
    '<span class="start-sub">녹음기 앱에서 녹음하면 다른 앱을 봐도 안 끊겨요</span></button>\n',
    GUIDE)

# ── HTML ②: 상세 화면 — 단추 이름·구실 바꾸기
sub("상세 화면: 단추를 「휴대폰 녹음기로 녹음할게요」로",
    '          <button class="btn btn-primary rec-phone" type="button" id="recOpenApp" hidden>📱 녹음기 앱 열기</button>\n',
    '          <button class="btn btn-primary rec-phone" type="button" id="recPhoneMine" hidden>📱 휴대폰 녹음기로 녹음할게요</button>\n')

# ── HTML ③: 상세 화면 — 안내 카드 넣기(다시 하기 상자 안)
sub("상세 화면: 3단계 안내 카드 넣기",
    '        <div class="mf-hint" style="margin:10px 0 4px;line-height:1.6;">회의가 <b>이어져 더 녹음</b>하거나',
    GUIDE + '        <div class="mf-hint" style="margin:10px 0 4px;line-height:1.6;">회의가 <b>이어져 더 녹음</b>하거나')

# ── JS ①: intent 블록 통째로 교체
i = src.index("  function recAppIntentUrl(){")
# 🔴 그 닻은 앞(1462줄 근처)에도 하나 있다 — 반드시 i 뒤에서 찾는다(앞엣것을 잡으면 옛 블록이 그대로 남는다)
j = src.index("  if(_phWrap&&_phIn&&_isAndroid){", i)
src = src[:i] + (
    "  // ── z1129: 웹에서는 녹음기 앱을 열 수 없다(2026-09-27 대표 실물 4번 · 로그에 ?recapp=manual 4회) ──\n"
    "  //   크롬은 「브라우저에서 열어도 됨(BROWSABLE)」을 적어 둔 화면만 연다 — 삼성 「음성 녹음」은 그 표시가 없다.\n"
    "  //   게다가 옛 단추는 누를 때 회의록을 먼저 만들어, 실패할 때마다 빈 회의록이 남았다.\n"
    "  //   → 앱을 여는 단추를 없애고, 홈 화면에서 직접 여는 3단계를 안내로 둔다.\n"
    "  var _guideBox=$('recPhoneGuide');\n"
    "  if(_guideBox&&_isAndroid) _guideBox.hidden=false;\n"
    "  var _appBtn=$('recPhoneMine');   // 상세 화면에만 있는 「📱 휴대폰 녹음기로 녹음할게요」(이 회의 표시 + 자동 시작 취소)\n"
    "  if(_appBtn&&_isAndroid){\n"
    "    _appBtn.hidden=false;\n"
    "    _appBtn.addEventListener('click',function(){\n"
    "      if(M.id) phrecMark(M.id, (($('mtgTitle')||{}).value)||'');   // 목록·공유 화면이 이 회의를 먼저 보여 준다\n"
    "      _phrecChosen=true;\n"
    "      try{ if(_phFallback){ clearTimeout(_phFallback); _phFallback=null; } }catch(_){}\n"
    "      if(_mr && _mr.state!=='inactive'){          // 이 화면 녹음이 돌고 있으면 깨끗이 마친다\n"
    "        _recHandoff=true;\n"
    "        try{ recStop(); }catch(_){}\n"
    "      } else if(_recOpen && REC.mine){            // 창이 닫혀 멈춘 내 녹음이 서버에 열려 있으면 닫아 둔다\n"
    "        _recOpen=false; recResumeShow(false); recNetFinish();\n"
    "      }\n"
    "      if(_guideBox){ _guideBox.hidden=false; try{ _guideBox.scrollIntoView({block:'start'}); }catch(_){} }\n"
    "      recSt('휴대폰 홈 화면에서 「음성 녹음」을 열어 녹음하세요 — 다른 앱을 봐도 끊기지 않습니다. '\n"
    "           +'회의가 끝나면 녹음기에서 「공유 → KNK WORKS」로 이 회의를 고르면 자동으로 정리됩니다.');\n"
    "    });\n"
    "  }\n"
) + src[j:]
done.append("JS: intent 여는 코드 삭제 · 안내 카드/표시 단추로 교체")
print("  [고침] JS: intent 여는 코드 삭제 · 안내 카드/표시 단추로 교체")

# ── JS ②: 안내 상자 안 단추 배치 주석
sub("상자 안 단추 주석",
    "   // 단추는 하나씩만 둔다(입력이 둘이 되지 않게 · z1127: 녹음기 앱 열기가 먼저)",
    "   // 단추는 하나씩만 둔다(입력이 둘이 되지 않게 · z1129: 「휴대폰 녹음기로 녹음할게요」가 먼저)")

# ── JS ③: 못 열었을 때 안내(manual) 제목
sub("manual 안내 제목",
    "      if(t) t.textContent='📱 녹음기 앱을 자동으로 열지 못했습니다';",
    "      if(t) t.textContent='📱 휴대폰 녹음기로 녹음하세요';")

# ── JS ④: first 모드 안내 글
sub("first 모드 안내 글",
    "      if(w) w.innerHTML='<b>「📱 녹음기 앱 열기」</b>를 누르면 휴대폰 <b>녹음기 앱</b>을 엽니다'\n"
    "        +'(크롬이 막아 안 열리는 기종도 있습니다 — 그때는 홈 화면에서 <b>「음성 녹음」</b>을 직접 열어 주세요 · 효과는 같습니다)"
    " — 거기서 녹음을 시작하면 '\n",
    "      if(w) w.innerHTML='휴대폰 <b>홈 화면에서 「음성 녹음」</b>을 열어 녹음하세요 — 그렇게 하면 '\n")

# ── JS ⑤: 기본 모드
sub("기본 모드 제목",
    "      if(t) t.textContent='📱 이 회의, 녹음기 앱으로 녹음하시겠어요?';",
    "      if(t) t.textContent='📱 이 회의, 휴대폰 녹음기로 녹음하시겠어요?';")
sub("기본 모드 안내 글",
    "        +'(2026-09-20 실측 95초). <b>「📱 녹음기 앱 열기」</b>로 바꾸면 <b>다른 앱을 써도 계속 녹음</b>되고, '\n",
    "        +'(2026-09-20 실측 95초). 홈 화면의 <b>「음성 녹음」</b>으로 바꾸면 <b>다른 앱을 써도 계속 녹음</b>되고, '\n")

# ── JS ⑥: 기기별 안내
sub("기기별 안내 글",
    "        +'<b>「📱 녹음기 앱 열기」</b>로 <b>녹음기 앱에서</b> 녹음하세요(끝나면 녹음기에서 <b>「공유 → KNK WORKS」</b>). '\n"
    "        +'단추로 열리지 않는 기종에서는 홈 화면에서 <b>「음성 녹음」</b>을 직접 열어도 마찬가지입니다. '\n",
    "        +'휴대폰 <b>홈 화면에서 「음성 녹음」</b>을 열어 녹음하세요(끝나면 녹음기에서 <b>「공유 → KNK WORKS」</b>). '\n"
    "        +'<b>크롬은 웹에서 녹음기 앱을 열 수 없습니다</b>(2026-09-27 확인) — 그래서 홈 화면에서 직접 엽니다. '\n")

# ── JS ⑦: 이음 「▶ 회의 시작」 고르기 안내
sub("이음 회의 시작 — 고르기 안내",
    "            recSt('📱 위의 「녹음기 앱 열기」를 눌러 주세요 — 녹음기 앱에서 녹음하면 다른 앱을 봐도 끊기지 않습니다. '\n",
    "            recSt('📱 휴대폰 녹음기로 녹음하시려면 위 「📱 휴대폰 녹음기로 녹음할게요」를 누르고 홈 화면에서 「음성 녹음」을 여세요 — 다른 앱을 봐도 끊기지 않습니다. '\n")
sub("이음 회의 시작 — 30초 지난 뒤 안내",
    "                + '위 <b>「📱 녹음기 앱 열기」</b>를 누르면 지금이라도 바꿀 수 있습니다(지금까지 녹음은 그대로 이어집니다).');",
    "                + '위 <b>「📱 휴대폰 녹음기로 녹음할게요」</b>를 누르면 지금이라도 바꿀 수 있습니다(지금까지 녹음은 그대로 이어집니다).');")

# ── JS ⑧: 옛 주소 호환
sub("옛 되돌아오기 주소 호환 주석",
    "  // z1127: 녹음기 앱을 자동으로 못 열어 되돌아왔다(?recapp=manual) → 손으로 여는 길을 안내\n",
    "  // z1129: 옛 주소(?recapp=manual) 호환 — 이제는 앱을 열려고 하지 않아 생기지 않지만, 옛 링크로 들어오면 같은 안내\n")
sub("옛 되돌아오기 상태줄",
    "      else recSt('📱 녹음기 앱을 자동으로 열지 못했습니다 — 휴대폰 홈 화면에서 「음성 녹음」을 직접 열어 녹음하세요. '\n",
    "      else recSt('📱 휴대폰 홈 화면에서 「음성 녹음」을 직접 열어 녹음하세요. '\n")

if src == orig:
    print("바뀐 것이 없다 — 중지")
    raise SystemExit(1)
for bad in ("recOpenApp", "recAppIntentUrl", "intent:#Intent", "__knkRecAppUrl"):
    if bad in src:
        print("[실패] 옛 것이 아직 남아 있다:", bad)
        raise SystemExit(1)
bak = P + ".bak_z1129"
if not os.path.exists(bak):
    open(bak, "w", encoding="utf-8").write(orig)
tmp = P + ".tmp_z1129"
with open(tmp, "w", encoding="utf-8", newline="") as f:
    f.write(src)
os.replace(tmp, P)
print("\n[완료] z1129 %d곳 고침 → %s" % (len(done), P))
