# -*- coding: utf-8 -*-
"""z1128 — 「📱 녹음기 앱 열기」 주소를 문법대로(데이터 부분 없는 intent:) + 못 열릴 수 있음을 사실대로
사용: py -3.13 patch_z1128.py <앱 사본 경로>

근거(안드로이드·크롬 공개 소스/문서 2026-09-27 확인):
 · Intent.parseUri — 'intent://#Intent;…' 는 'intent:' 7자를 뗀 뒤 남은 「//」를 그대로 데이터로 넣는다
     if (data.startsWith("intent:")) { data = data.substring(7); … }
     if (data.length() > 0) { intent.mData = Uri.parse(data); }
 · IntentFilter.matchData — 걸개에 data 칸이 없으면
     return ((type == null && data == null) ? MATCH_CATEGORY_EMPTY+… : NO_MATCH_DATA);
   → MAIN·LAUNCHER 걸개는 data 가 없으니 「//」가 붙은 intent 는 아무 앱에도 안 걸린다 → 곧바로 fallback
 · 크롬 문서 — "Only activities with the category filter android.intent.category.BROWSABLE can be
   invoked using this method" → 녹음기 앱이 BROWSABLE 을 안 적어 두었으면 그래도 안 열린다(대표 실물 확인 몫)
"""
import os
import sys

if len(sys.argv) < 2:
    print("사용: patch_z1128.py <앱 사본 경로>")
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


# ① intent 주소 — 데이터 부분(//) 없이
sub("intent 주소를 'intent:' 로(데이터 「//」 없음)",
    "    return 'intent://#Intent;action=",
    "    // 🔴 z1128(안드로이드 소스 확인): 'intent://' 로 적으면 남는 「//」가 그대로 intent 의 데이터가 되고,\n"
    "    //   MAIN·LAUNCHER 걸개는 data 칸이 없어 IntentFilter.matchData 가 안 걸어 준다 → 아무 앱도 못 찾아\n"
    "    //   바로 fallback 으로 떨어졌다. 그래서 데이터 부분 없이 'intent:' 로 적는다.\n"
    "    return 'intent:#Intent;action=")

# ② 큰 단추 부제 — 약속은 '녹음기 앱에서 녹음하면'
sub("큰 단추 부제를 사실대로",
    '<span class="start-sub">다른 앱을 봐도 계속 녹음돼요</span>',
    '<span class="start-sub">녹음기 앱에서 녹음하면 다른 앱을 봐도 안 끊겨요</span>')

# ③ 누른 뒤 안내 — 열리지 않을 수 있음을 그 자리에서
sub("누른 뒤 안내에 「열리지 않으면 직접」 넣기",
    "      recSt('녹음기 앱을 엽니다 — 거기서 녹음을 시작하세요. 다른 앱을 봐도 끊기지 않습니다. '\n",
    "      recSt('녹음기 앱을 엽니다 — 거기서 녹음을 시작하세요. 다른 앱을 봐도 끊기지 않습니다. '\n"
    "           +'열리지 않으면 홈 화면에서 「음성 녹음」을 직접 열어 주세요(효과는 같습니다). '\n")

# ④ 안내 상자 — 「열립니다」 단정을 고치고 직접 여는 길을 나란히
sub("안내 상자 글을 사실대로",
    "      if(w) w.innerHTML='<b>「📱 녹음기 앱 열기」</b>를 누르면 휴대폰 <b>녹음기 앱</b>이 열립니다 — 거기서 녹음을 시작하면 '\n",
    "      if(w) w.innerHTML='<b>「📱 녹음기 앱 열기」</b>를 누르면 휴대폰 <b>녹음기 앱</b>을 엽니다'\n"
    "        +'(크롬이 막아 안 열리는 기종도 있습니다 — 그때는 홈 화면에서 <b>「음성 녹음」</b>을 직접 열어 주세요 · 효과는 같습니다)"
    " — 거기서 녹음을 시작하면 '\n")

# ⑤ 기기별 안내 — 직접 열어도 같다는 한 줄
sub("기기별 안내에 「직접 열어도 마찬가지」 넣기",
    "        +'<b>「📱 녹음기 앱 열기」</b>로 <b>녹음기 앱에서</b> 녹음하세요(끝나면 녹음기에서 <b>「공유 → KNK WORKS」</b>). '\n",
    "        +'<b>「📱 녹음기 앱 열기」</b>로 <b>녹음기 앱에서</b> 녹음하세요(끝나면 녹음기에서 <b>「공유 → KNK WORKS」</b>). '\n"
    "        +'단추로 열리지 않는 기종에서는 홈 화면에서 <b>「음성 녹음」</b>을 직접 열어도 마찬가지입니다. '\n")

if src == orig:
    print("바뀐 것이 없다 — 중지")
    raise SystemExit(1)
bak = P + ".bak_z1128"
if not os.path.exists(bak):
    open(bak, "w", encoding="utf-8").write(orig)
tmp = P + ".tmp_z1128"
with open(tmp, "w", encoding="utf-8", newline="") as f:
    f.write(src)
os.replace(tmp, P)
print("\n[완료] z1128 %d곳 고침 → %s" % (len(done), P))
