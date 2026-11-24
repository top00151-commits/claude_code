# -*- coding: utf-8 -*-
"""z1191z126 (대표 11-24 「구매팀 허동준·김선미 웍스가 옛날 버전 · 김정락·안지연·이새롬만 맞음」 → 「만들어」):
   웍스 창을 며칠씩 안 닫고 메뉴만 누르면 본문만 새 판으로 바뀌고 창(메뉴·공용 스크립트)은 옛 판으로 남았다.
   → 화면마다 서버 판(#knkVer) · 화면 바꿈이 새로 받은 화면 판과 이 창 판(__knkLoadedVer)이 다르면 창 전체 새로 열기.
   (실제 화면 확인: 시험 서버에서 판이 같으면 본문만 · 판을 옛 값으로 바꾸고 메뉴 누르면 창 전체 새로 열림)"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = []
def check(l, c, g=""):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l + ("" if c else "  → " + str(g)[:300]))
P = os.path.join(ROOT, "app", "templates", "_v5_partials")
ch = open(os.path.join(P, "chrome.html"), encoding="utf-8").read()
sp = open(os.path.join(P, "spa_nav.html"), encoding="utf-8").read()
check("① 모든 화면 틀에 서버 판 표시(#knkVer = APP_VERSION)", '<i id="knkVer" data-v="{{ APP_VERSION }}" hidden></i>' in ch)
check("① 판 표시가 화면 바꿈 장치보다 앞(본문 밖 · 받은 화면에 늘 들어 있음)",
      ch.index('id="knkVer"') < ch.index('_v5_partials/spa_nav.html'))
check("② 이 창 판 기억(처음 연 판 · 다시 안 덮어씀)", "if (!window.__knkLoadedVer) window.__knkLoadedVer = LOADED;" in ch)
i_apply = sp.index("function apply(html, url, push)")
i_cmp = sp.index("_nv126")
i_swap = sp.index("curMain.replaceWith(newMain)")
check("③ 비교는 본문 갈아 끼우기 전에", i_apply < i_cmp < i_swap)
check("③ 판이 다르면 창 전체 새로(메뉴 = 주소 이동 · 뒤로/앞으로 = 바꿔치기)",
      "if (push) return fullNav(url);" in sp[i_cmp:i_swap] and "window.location.replace(url); return;" in sp[i_cmp:i_swap])
check("③ 옮기기 전 입력 칸 임시 저장(knkDraft)", "window.knkDraft.save()" in sp[i_cmp:i_swap])
check("③ 떠나기 확인을 건너뛰지 않음(knkLeaveOk 안 씀)", "knkLeaveOk" not in sp[i_cmp:i_swap])
check("③ 판 표시가 없는 화면(로그인 등)은 비교 안 함", "if (_v126 && _lv126 && _v126 !== _lv126)" in sp)
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader(os.path.join(ROOT, "app", "templates")))
errs = []
for f in ("_v5_partials/chrome.html", "_v5_partials/spa_nav.html"):
    try:
        env.parse(open(os.path.join(ROOT, "app", "templates", f), encoding="utf-8").read())
    except Exception as e:
        errs.append("%s: %s" % (f, e))
check("④ 두 틀 문법 정상", not errs, errs)
print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
