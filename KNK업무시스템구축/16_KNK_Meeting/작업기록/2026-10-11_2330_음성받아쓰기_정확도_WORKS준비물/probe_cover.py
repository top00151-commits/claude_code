# -*- coding: utf-8 -*-
"""「📁 녹음 파일 올리기」 단추를 **무엇이 덮고 있나**를 이름으로 묻는다.

ui_filepick_z1141 과 **똑같은 조건**(아이폰 UA · 모바일 · 390x844)으로 띄운 뒤
단추 가운데 점에 실제로 있는 요소를 묻는다. 짐작하지 않고 이름을 받는다.

사용: py -3.12 probe_cover.py <포트> <씨앗폴더>
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright   # noqa: E402

PORT = int(sys.argv[1])
SEED = sys.argv[2]
BASE = "http://127.0.0.1:%d" % PORT
UA_IOS = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 "
          "(KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1")

seed = json.load(open(os.path.join(SEED, "seed_phrec.json"), encoding="utf-8"))
MID, CEO = seed["mids"][0], seed["ceo"]

ASK = """()=>{
  const b = document.getElementById('recUpBtn');
  if (!b) return {err:'단추가 없다'};
  const r = b.getBoundingClientRect();
  const cx = Math.round(r.left + r.width/2), cy = Math.round(r.top + r.height/2);
  const top = document.elementFromPoint(cx, cy);
  const path = [];
  let e = top;
  while (e && path.length < 6) {
    path.push((e.tagName||'').toLowerCase()
      + (e.id ? '#'+e.id : '')
      + (e.className && typeof e.className === 'string' && e.className.trim()
         ? '.'+e.className.trim().split(/\\s+/).slice(0,2).join('.') : ''));
    e = e.parentElement;
  }
  const hint = document.getElementById('worksInstallHint');
  let hintInfo = null;
  if (hint) {
    const cs = getComputedStyle(hint), hr = hint.getBoundingClientRect();
    hintInfo = {display: cs.display, visibility: cs.visibility, position: cs.position,
                zIndex: cs.zIndex, hidden: hint.hasAttribute('hidden'),
                box: [Math.round(hr.left), Math.round(hr.top),
                      Math.round(hr.width), Math.round(hr.height)]};
  }
  const sttSel = document.getElementById('sttLang');
  let sttInfo = null;
  if (sttSel) {
    const sr = sttSel.getBoundingClientRect();
    sttInfo = {box: [Math.round(sr.left), Math.round(sr.top),
                     Math.round(sr.width), Math.round(sr.height)]};
  }
  return {btnBox: [Math.round(r.left), Math.round(r.top),
                   Math.round(r.width), Math.round(r.height)],
          point: [cx, cy], topMost: path[0] || null, chain: path,
          coveredByOther: !(top === b || b.contains(top)),
          installHint: hintInfo, sttLang: sttInfo};
}"""

with sync_playwright() as pw:
    br = pw.chromium.launch(channel="chrome", headless=True)
    c = br.new_context(user_agent=UA_IOS, viewport={"width": 390, "height": 844},
                       is_mobile=True, has_touch=True, base_url=BASE)
    c.add_cookies([{"name": "tuser", "value": str(CEO), "url": BASE}])
    p = c.new_page()
    p.goto("%s/meetings/%d" % (BASE, MID), wait_until="domcontentloaded")
    for label, wait in (("바로(0.2초)", 200), ("팝업이 뜰 만큼(2.5초)", 2300)):
        p.wait_for_timeout(wait)
        r = p.evaluate(ASK)
        print("\n── %s ──" % label)
        print("  단추 자리      :", r.get("btnBox"), "· 가운데 점", r.get("point"))
        print("  그 점의 임자   :", r.get("topMost"))
        print("  🔴 덮여 있나   :", "예" if r.get("coveredByOther") else "아니오")
        print("  설치 안내 팝업 :", r.get("installHint"))
        print("  z1165 새 칸    :", r.get("sttLang"))
        if r.get("coveredByOther"):
            print("  덮은 것의 조상 :", " < ".join(r.get("chain") or []))
    br.close()
