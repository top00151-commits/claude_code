# -*- coding: utf-8 -*-
"""z1191z6 — 자동 저장 보강(대표 2026-11-06 「자동저장 권고 1·2·3 진행해」) 원문 검사
  ① 작업일정표 수주 줄 글 칸 저장 뒤 통째 새로고침 없음 · 호기 칸·상품 수량·상태 팝업은 다른 칸이 닫힌 뒤 새로고침(_knkSafeReload)
  ② 떠날 때 경고: 작업일정표(편집 중 값 바뀜·저장 시작된 칸 제외) · 소모품 상세(고치고 저장 안 된 칸) · 상세 카드(✏️ 수정 중 바뀐 값)
  ③ 저장 요청 keepalive · 저장된 칸 ✓(td.ux-ok)
  화면 실측(Chromium)은 scratchpad p4/_uiz7_pw.py 로 16/16 통과(배포 기록 참조). 여기서는 원문이 그 모양인지 본다.
"""
import io
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OK = FAIL = 0


def check(cond, msg):
    global OK, FAIL
    if cond:
        OK += 1; print("  ✅", msg)
    else:
        FAIL += 1; print("  ❌", msg)


rd = lambda *p: io.open(os.path.join(ROOT, *p), encoding="utf-8").read()
b = rd("app", "templates", "schedule_board.html")
c = rd("app", "templates", "consumable_detail.html")
d = rd("app", "templates", "project_detail.html")
css = rd("static", "css", "schedule_board.css")
print("§1 작업일정표")
check("function _knkSafeReload()" in b and "function _knkCellDirty()" in b and "window.addEventListener('beforeunload', function(e){ if(window.knkLeaveOk) return; if(_knkCellDirty())" in b, "도우미(_knkSafeReload·_knkCellDirty·떠날 때 경고) 있음")
check("toast('저장됨 · 이 수주에만 반영'); }" in b and "toast('저장됨 · 이 수주에만 반영'); setTimeout" not in b, "수주 줄 글 칸: 저장 뒤 새로고침 없음(그 칸만 갱신)")
check(b.count("_knkSafeReload()") >= 3 and "setTimeout(function(){ location.reload(); }, 450)" not in b, "호기 칸·상품 수량·상태 팝업: 안전 새로고침(다른 칸 닫힌 뒤)")
check(b.count("inp.dataset.knkOrig=cur") >= 4 and "sel.dataset.knkOrig=cur" in b, "입력칸 처음 값 기억(바뀌었는지 판단)")
check("i.dataset.knkSaving) return false" in b and b.count("knkSaving='1'") >= 4, "저장 시작된 칸은 경고 대상에서 제외(Enter·칸 떠난 뒤 이동은 경고 없음)")
check(b.count("keepalive:true") >= 10, "저장 요청 keepalive — %d곳" % b.count("keepalive:true"))
check(b.count("_knkCellOk(td)") >= 4 and "td.ux-ok { box-shadow: inset 0 0 0 2px #86efac" in css, "저장된 칸 ✓(초록 테두리)")
check(b.count("location.reload()") == b.count("knkLeaveOk=true, location.reload()") + b.count("knkLeaveOk=true; location.reload()"), "우리 코드의 새로고침은 전부 knkLeaveOk 표시 뒤(경고 안 뜸) — %d곳" % b.count("location.reload()"))
print("§2 소모품 상세")
check("el.dataset.knkDirty='1'" in c and "data-knk-dirty" in c and "beforeunload" in c, "고치고 저장 안 된 칸 → 떠날 때 경고")
check(c.count("keepalive:true") >= 2, "줄·머리 저장 keepalive")
check(c.count("location.reload()") == c.count("knkLeaveOk=true, location.reload()"), "새로고침은 knkLeaveOk 뒤 — %d곳" % c.count("location.reload()"))
print("§3 상세 수주 카드")
check("window._knkCardDirtyFns" in d and "collectDirtyRows().length) return true" in d and "beforeunload" in d, "✏️ 수정 중 바뀐 값 → 떠날 때 경고")
check("(window.knkLeaveOk=true, knkReloadKeepView())" in d and "knkReloadKeepView();" not in d.replace("(window.knkLeaveOk=true, knkReloadKeepView());", ""), "💾 저장 뒤 자동 새로고침은 경고 없음")
print("§4 틀 문법")
try:
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(os.path.join(ROOT, "app", "templates")), extensions=["jinja2.ext.loopcontrols"])
    for t in ("schedule_board.html", "consumable_detail.html", "project_detail.html"):
        env.parse(rd("app", "templates", t))
    check(True, "Jinja 문법 OK(3 틀)")
except Exception as e:
    check(False, "Jinja 문법: %s" % e)
print("결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
