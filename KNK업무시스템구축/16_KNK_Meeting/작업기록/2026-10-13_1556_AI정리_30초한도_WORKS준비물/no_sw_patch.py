# -*- coding: utf-8 -*-
"""🧹 시험 서버가 **서비스워커를 안 깔게** 한다 (대표 「진행해」 2026-10-13).

왜 (z1168 에서 실측한 뿌리)
  운영 `/sw.js` 의 `activate` 가 `clients.matchAll({type:'window'}).forEach(c => c.navigate(c.url))`
  로 **열린 화면을 전부 다시 읽힌다**. 시험은 **매번 새 브라우저**라 서비스워커가 처음 깔리고 →
  activate → 화면이 **열고 0.8초쯤 뒤 스스로 다시 읽힌다**(재어 본 6번 모두 · 「문서 읽은 횟수 2」).
  그 창에 시험이 화면을 들여다보면 `Execution context was destroyed` 로 터진다.
  **이틀에 네 번** 터졌고(ui_block ×2 · ui_phrec · ui_vw) 그때마다 「내 탓인지」 재느라 20~30분씩 썼다.
  네 번 다 **운영 그대로에서도 터져** 무혐의였다.

무엇을 하나
  시험 서버에서 `/sw.js` 길을 **없앤다**(404). 그러면 화면의 등록이 조용히 실패한다 —
  `works_pwa_head.html` 이 `navigator.serviceWorker.register('/sw.js').catch(function(){})` 로
  받으므로 **화면은 멀쩡**하고, 서비스워커가 안 깔려 **다시 읽히는 일이 없어진다.**

⛔ 운영 `/sw.js` 는 **안 건드린다** — 내 구역이 아니고, 운영에선 뜻한 동작이다
   (새로 배포되면 모두를 새 코드로 끌어올린다).

쓰는 법: py no_sw_patch.py          (넣기)
         py no_sw_patch.py --check  (들어갔는지 보기만)
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

CHECK = "--check" in sys.argv
SP = ("C:/Users/top00/AppData/Local/Temp/claude/"
      "C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad")
B = "C:/Users/top00/JR/Claude 코드/KNK업무시스템구축/16_KNK_Meeting/작업기록"

#  reg 묶음이 **실제로 띄우는** 시험 서버만. (안 쓰는 옛 runner 는 건드리지 않는다)
TARGETS = [
    SP + "/z1147/reg/run_rec_app.py",
    SP + "/z1147/reg/run_phrec_app.py",
    SP + "/z1147/run_vw_app.py",
    SP + "/z1147/run_end_app.py",
    B + "/2026-10-08_0900_음성메모_새메뉴_WORKS준비물/run_vn_app.py",
    B + "/2026-10-11_1835_회의록상세_베트남어_WORKS준비물/run_form_app.py",
    B + "/2026-10-11_1931_왼쪽메뉴_베트남어_WORKS준비물/run_shell_app.py",
    B + "/2026-10-11_2043_직책_영어표기_WORKS준비물/run_rank_app.py",
    B + "/2026-10-11_2330_음성받아쓰기_정확도_WORKS준비물/run_stt_app.py",
    B + "/2026-10-12_1130_목록에서_바로가기_WORKS준비물/run_list_app.py",
    B + "/2026-10-13_1035_음성메모_시안문서_지움_WORKS준비물/run_vn2_app.py",
    B + "/2026-10-13_1315_음성메모_정리_뒤에서돌리기_WORKS준비물/run_vn3_app.py",
    B + "/2026-10-13_1343_회의록_정리_뒤에서돌리기_WORKS준비물/run_mtg3_app.py",
]

MARK = "_no_sw_in_test"
ANCHOR = "from app import main as M"
#  🔴 2026-10-13 고침 — 처음엔 /sw.js 를 **404** 로 뒀더니 브라우저가 콘솔에
#     「A bad HTTP response code (404) was received when fetching the script.」 **오류 한 줄**을 남겨
#     「콘솔 오류 0」을 보는 내 시험 둘이 터졌다(ui_vn_redo_z1169 · ui_mtg_redo_z1170).
#     → **아무 일도 안 하는 빈 서비스워커**를 내준다. 깔려도 activate 에서 하는 일이 없으니
#       화면을 다시 읽히지 않고, 404 가 아니라 콘솔도 조용하다.
BLOCK = (
    "\n"
    "# 🧹 시험에서는 **아무 일도 안 하는** 서비스워커를 내준다.\n"
    "#    운영 /sw.js 의 activate 는 c.navigate(c.url) 로 **열린 화면을 전부 다시 읽힌다** →\n"
    "#    시험은 매번 새 브라우저라 그게 깔리면서 화면이 0.8초 뒤 다시 읽히고,\n"
    "#    Playwright 가 'Execution context was destroyed' 로 터진다(이틀에 네 번 겪음).\n"
    "#    🔵 404 로 두면 콘솔에 오류 한 줄이 남아 「콘솔 오류 0」 검사가 깨진다 → 빈 스크립트로.\n"
    "#    ⛔ 운영 /sw.js 는 건드리지 않는다. 이 줄은 **시험 서버에만** 있다.\n"
    "from starlette.responses import PlainTextResponse as _PTR_no_sw   # noqa: E402\n"
    "_no_sw_in_test = [r for r in M.app.router.routes if getattr(r, 'path', '') == '/sw.js']\n"
    "for _r in _no_sw_in_test:\n"
    "    M.app.router.routes.remove(_r)\n"
    "\n"
    "\n"
    "@M.app.get('/sw.js')\n"
    "async def _sw_noop_for_test():\n"
    "    return _PTR_no_sw('/* 시험용 빈 서비스워커 — 아무 일도 하지 않는다 */',\n"
    "                      media_type='application/javascript')\n"
)

done = skip = miss = 0
for p in TARGETS:
    name = p.replace(SP + "/", "스크래치/").replace(B + "/", "")
    if not os.path.exists(p):
        print("  🔴 없음   %s" % name)
        miss += 1
        continue
    s = io.open(p, encoding="utf-8").read()
    if MARK in s:
        print("  이미 됨  %s" % name)
        skip += 1
        continue
    if CHECK:
        print("  🔴 안 됨  %s" % name)
        miss += 1
        continue
    if ANCHOR not in s:
        print("  🔴 기준 줄 없음  %s" % name)
        miss += 1
        continue
    #  `from app import main as M` 이 든 import 묶음 **바로 다음 빈 줄** 뒤에 넣는다
    i = s.index(ANCHOR)
    j = s.find("\n", i) + 1
    #  같은 묶음의 다른 import 들(from app... / import ...)은 지나친다
    while True:
        nxt = s.find("\n", j)
        line = s[j:nxt if nxt >= 0 else len(s)]
        if line.startswith(("from app", "import ", "from ")):
            j = (nxt + 1) if nxt >= 0 else len(s)
            continue
        break
    out = s[:j] + BLOCK + s[j:]
    io.open(p + ".bak_nosw", "w", encoding="utf-8").write(s)      # 🔴 백업 먼저
    with open(p + ".tmp", "wb") as f:
        f.write(out.encode("utf-8"))
    os.replace(p + ".tmp", p)
    print("  ✅ 넣음   %s" % name)
    done += 1

print("\n넣음 %d · 이미 됨 %d · 문제 %d / 모두 %d" % (done, skip, miss, len(TARGETS)))
sys.exit(1 if miss else 0)
