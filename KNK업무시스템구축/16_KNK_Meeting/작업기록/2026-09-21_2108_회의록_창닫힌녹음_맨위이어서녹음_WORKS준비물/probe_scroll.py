# -*- coding: utf-8 -*-
"""z1120 조사용 — 안드로이드 「이어서 녹음」 뒤 화면이 얼마나 움직이나(scrollY·상자 위치를 시간별로)."""
import io, json, os, sys
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright
W = sys.argv[1]; MID = int(sys.argv[2]); UA = sys.argv[3] if len(sys.argv) > 3 else "and"
seed = json.load(io.open(os.path.join(W, "seed_resume.json"), encoding="utf-8"))
BASE = "http://localhost:%d" % seed["port"]
UAS = {"and": "Mozilla/5.0 (Linux; Android 14; SM-S928N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Mobile Safari/537.36",
       "ios": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Mobile/15E148 Safari/604.1"}
with sync_playwright() as pw:
    br = pw.chromium.launch(channel="chrome", headless=True, args=["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"])
    c = br.new_context(service_workers="block", permissions=["microphone"], user_agent=UAS[UA], viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    c.add_cookies([{"name": "tuser", "value": str(seed["ceo"]), "url": BASE}])
    c.add_init_script("document.addEventListener('DOMContentLoaded',()=>{const s=document.createElement('style');s.textContent='#worksInstallHint{display:none !important}';document.head.appendChild(s);});")
    c.add_init_script("""(()=>{ const o=Element.prototype.scrollIntoView; Element.prototype.scrollIntoView=function(a){ (window.__siv=window.__siv||[]).push((this.id||this.className)+'@'+Math.round(performance.now())); return o.apply(this,arguments); };
      const ws=window.scrollTo; window.scrollTo=function(){ (window.__st=window.__st||[]).push(JSON.stringify([...arguments])+'@'+Math.round(performance.now())); return ws.apply(this,arguments); }; })();""")
    p = c.new_page()
    p.goto("%s/meetings/%d" % (BASE, MID), wait_until="domcontentloaded"); p.wait_for_timeout(1500)
    js = """() => { const q=id=>{const e=document.getElementById(id); if(!e) return null; const r=e.getBoundingClientRect(); return [Math.round(r.top),Math.round(r.bottom)];};
       const sc=document.scrollingElement; return {sy:Math.round(scrollY), st:sc.scrollTop, lead:q('recPhoneLead'), redo:q('redoTools'), ban:q('recBanner'), t:Math.round(performance.now()),
       siv:(window.__siv||[]).slice(-6), sto:(window.__st||[]).slice(-4), main:(()=>{const m=document.querySelector('.main'); return m?[m.scrollTop, getComputedStyle(m).overflowY]:null;})()}; }"""
    print("before", p.evaluate(js))
    p.locator("#recResumeBtn").click()
    for t in (100, 400, 1000, 2500):
        p.wait_for_timeout(t if t == 100 else t - [100, 400, 1000, 2500][[100, 400, 1000, 2500].index(t) - 1])
        print(t, p.evaluate(js))
    br.close()
