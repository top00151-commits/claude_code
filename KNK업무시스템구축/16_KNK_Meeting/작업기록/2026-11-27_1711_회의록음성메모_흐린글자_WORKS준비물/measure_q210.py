# -*- coding: utf-8 -*-
"""z1210 명암비 재기 — 회의록·음성 메모 화면 (스킬 knk-text-contrast · 실제 화면 픽셀로 바탕을 잰다)
사용: py -3.12 measure_q210.py <주소 http://127.0.0.1:PORT> <seed.json> <이름 before|after> [사진 저장 1|0]
· 테마 3가지(clear · soft · dark) = localStorage knk.theme (웍스 공용 테마 조각이 <html data-kt> 를 붙임)
· 바탕 = 글자를 모두 투명하게 한 화면 그림(테마 filter 가 걸린 실제 픽셀)에서 글자 칸 안 주된 색(15% 넘는 색 전부 · 가장 나쁜 쪽)
· 글자색 = 계산된 글자색 × 투명도(조상까지 곱) → 조상 filter(테마 밝기·뒤집기)를 같은 식으로 적용 → 바탕 픽셀 위에 섞음
· 결과: result_<이름>.json (글자마다 장면·테마·폭·자리·글자·크기·글자색·바탕·명암비·기준)
"""
import io
import json
import math
import os
import sys
from collections import Counter

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
from PIL import Image
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = sys.argv[1].rstrip("/")
SEED = json.load(io.open(sys.argv[2], encoding="utf-8"))
NAME = sys.argv[3]
SHOTS = len(sys.argv) > 4 and sys.argv[4] == "1"
ONLY = os.environ.get("Q210_ONLY", "")       # 장면 이름 거르기(쉼표)
ids = SEED["ids"]
U = {"ceo": SEED["me"], "mem": SEED["mem"], "vi": SEED["vi"], "emp": SEED["emp"]}

SCENES = [   # (장면 이름, 사람, 주소)
    ("회의록목록", "ceo", "/meetings"),
    ("회의록목록_빈", "emp", "/meetings"),
    ("회의록목록_베트남", "vi", "/meetings"),
    ("새회의록", "ceo", "/meetings/new"),
    ("회의록상세_정리있음", "ceo", "/meetings/%d" % ids["M1"]),
    ("회의록상세_정리없음", "ceo", "/meetings/%d" % ids["M2"]),
    ("회의록상세_보기만직원", "mem", "/meetings/%d" % ids["M1"]),
    ("회의록상세_베트남", "vi", "/meetings/%d" % ids["M1"]),
    ("회의록양식", "ceo", "/meetings/%d/doc" % ids["M1"]),
    ("회의록양식_베트남", "vi", "/meetings/%d/doc" % ids["M1"]),
    ("한눈에보기", "ceo", "/meetings/%d/viz" % ids["M1"]),
    ("한눈에보기_그림없음", "ceo", "/meetings/%d/viz" % ids["M2"]),
    ("음성메모목록", "ceo", "/voice-notes"),
    ("음성메모목록_빈", "emp", "/voice-notes"),
    ("음성메모목록_베트남", "vi", "/voice-notes"),
    ("새음성메모", "ceo", "/voice-notes/new"),
    ("음성메모상세_정리있음", "ceo", "/voice-notes/%d" % ids["V1"]),
    ("음성메모상세_정리없음", "ceo", "/voice-notes/%d" % ids["V2"]),
    ("음성메모상세_빈메모", "ceo", "/voice-notes/%d" % ids["V3"]),
    ("음성메모상세_베트남", "vi", "/voice-notes/%d" % ids["VI1"]),
    # 누른 뒤 상태(팝업·고치기 칸·펼침)
    ("회의록상세_줄고치기", "ceo", "/meetings/%d" % ids["M1"], "document.getElementById('btnSumEdit').click()"),
    ("회의록상세_펼침", "ceo", "/meetings/%d" % ids["M1"], "document.querySelectorAll('details').forEach(d=>d.open=true)"),
    ("음성메모상세_고치기", "ceo", "/voice-notes/%d" % ids["V1"], "document.getElementById('vnSumEdit').click()"),
    ("음성메모상세_펼침", "ceo", "/voice-notes/%d" % ids["V1"], "document.querySelectorAll('details').forEach(d=>d.open=true)"),
    # 🖼 이미지 카드(그림으로 만드는 흰 카드 · 색 고정) — html2canvas 를 가로채 화면 밖 사본을 화면 안으로 꺼내 잰다(밝게에서만 · 그림은 테마와 상관없음)
    ("음성메모_이미지카드", "ceo", "/voice-notes/%d" % ids["V1"],
     "window.html2canvas=function(el){ var h=el.parentNode; h.style.left='0px'; h.style.zIndex='2147483647'; return new Promise(function(){}); };"
     "document.getElementById('vnImg').click()", "clear"),
]
if ONLY:
    SCENES = [s for s in SCENES if s[0] in ONLY.split(",")]
SCENES = [tuple(s) + (None,) * (5 - len(s)) for s in SCENES]
THEMES = [t for t in os.environ.get("Q210_THEMES", "clear,soft,dark").split(",") if t]
WIDTHS = [(1440, 1000), (892, 1000), (412, 900), (390, 844), (360, 800)]

HIDE_CSS = (":root:root:root:root *::before,:root:root:root:root *::after{color:transparent!important;-webkit-text-fill-color:transparent!important;text-shadow:none!important;}"
            ":root:root:root:root input::placeholder,:root:root:root:root textarea::placeholder{color:transparent!important;-webkit-text-fill-color:transparent!important;}")
# 글자 숨기기 = 모든 요소에 inline !important(화면 CSS 의 !important 도 이김) · 원래 style 속성은 그대로 되돌림
JS_HIDE = r"""
() => { window.__q210h = []; document.querySelectorAll('body, body *').forEach(e=>{
    window.__q210h.push([e, e.getAttribute('style')]);
    for (const [k,v] of [['color','transparent'],['-webkit-text-fill-color','transparent'],['text-shadow','none'],['caret-color','transparent'],['text-decoration-color','transparent']])
      e.style.setProperty(k, v, 'important'); }); }
"""
JS_UNHIDE = r"""
() => { (window.__q210h||[]).forEach(([e,s])=>{ if(s===null) e.removeAttribute('style'); else e.setAttribute('style', s); }); window.__q210h=[]; }
"""
STILL_CSS = "*,*::before,*::after{transition:none!important;animation:none!important;scroll-behavior:auto!important;}"

JS_COLLECT = r"""
() => {
  const VW = innerWidth, VH = innerHeight, out = [];
  const RX = /[\p{L}\p{N}]/u;
  function path(el){ const p=[]; let e=el; while(e && e.nodeType===1 && p.length<6){ let s=e.tagName.toLowerCase();
      if(e.id) { s+='#'+e.id; p.unshift(s); break; }
      const c=[...e.classList].slice(0,2).join('.'); if(c) s+='.'+c; p.unshift(s); e=e.parentElement; } return p.join('>'); }
  function chain(el){ let o=1, f=[], e=el; while(e && e.nodeType===1){ const cs=getComputedStyle(e); o*=parseFloat(cs.opacity||'1');
      if(cs.filter && cs.filter!=='none') f.push(cs.filter); e=e.parentElement; } return {o, f}; }
  function vis(el, r){ const cx=Math.min(VW-1,Math.max(0,r.left+r.width/2)), cy=Math.min(VH-1,Math.max(0,r.top+r.height/2));
      const L=document.elementsFromPoint(cx,cy); if(!L.length) return false; const t=L[0]; return t===el || el.contains(t); }
  function dis(el){ return !!el.closest('button:disabled,input:disabled,select:disabled,textarea:disabled,[aria-disabled="true"],fieldset:disabled'); }
  function push(el, txt, r, color, kind){
      const cs=getComputedStyle(el), ch=chain(el);
      out.push({p:path(el), t:txt.slice(0,60), x:Math.round(r.left), y:Math.round(r.top), w:Math.round(r.width), h:Math.round(r.height),
        c:color, fs:parseFloat(cs.fontSize), fw:parseInt(cs.fontWeight)||400, o:ch.o, f:ch.f, dis:dis(el), kind,
        ce: !!el.closest('[contenteditable="true"],.kle-input'), inmain: !!el.closest('main') || !document.querySelector('main')}); }
  const W=document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n; const seen=new Set();
  while((n=W.nextNode())){
    const txt=(n.nodeValue||'').replace(/\s+/g,' ').trim(); if(!txt || !RX.test(txt)) continue;
    const el=n.parentElement; if(!el || el.closest('script,style,noscript,template,svg,option,datalist,title')) continue;
    const cs=getComputedStyle(el); if(cs.visibility!=='visible' || cs.display==='none') continue;
    const rg=document.createRange(); rg.selectNodeContents(n);
    const rs=[...rg.getClientRects()].filter(r=>r.width>=2 && r.height>=4 && r.bottom>0 && r.right>0 && r.top<VH && r.left<VW);
    if(!rs.length) continue;
    const r=rs[0]; if(!vis(el, r)) continue;
    const k=el.tagName+'|'+Math.round(r.left)+'|'+Math.round(r.top)+'|'+txt.slice(0,20); if(seen.has(k)) continue; seen.add(k);
    push(el, txt, r, cs.color, 'text');
  }
  document.querySelectorAll('input,textarea').forEach(el=>{
    const ty=(el.type||'text').toLowerCase(); if(['hidden','checkbox','radio','file','range','color','submit','button','image','reset'].includes(ty)) return;
    const r=el.getBoundingClientRect(); if(r.width<8||r.height<8||r.bottom<=0||r.top>=VH||r.left>=VW||r.right<=0) return;
    const cs=getComputedStyle(el); if(cs.visibility!=='visible') return; if(!vis(el, r)) return;
    const bl=parseFloat(cs.borderLeftWidth)+parseFloat(cs.paddingLeft), bt=parseFloat(cs.borderTopWidth)+parseFloat(cs.paddingTop);
    const ir={left:r.left+bl, top:r.top+bt, width:Math.max(4,r.width-2*bl), height:Math.max(4,Math.min(r.height-2*bt, parseFloat(cs.fontSize)*1.4))};
    if(el.value && RX.test(el.value)) push(el, el.value.replace(/\s+/g,' '), ir, cs.color, 'value');
    else if(el.placeholder && RX.test(el.placeholder)) push(el, el.placeholder, ir, getComputedStyle(el,'::placeholder').color, 'placeholder');
  });
  return out;
}
"""

JS_SCROLLER = r"""
() => { let best=null, bh=0;
  document.querySelectorAll('*').forEach(e=>{ const cs=getComputedStyle(e); if(!/(auto|scroll)/.test(cs.overflowY)) return;
    const d=e.scrollHeight-e.clientHeight; const r=e.getBoundingClientRect(); if(d>60 && r.height>200 && r.width>200 && d>bh){ bh=d; best=e; } });
  const se=document.scrollingElement; const dd=se.scrollHeight-se.clientHeight;
  if(dd>60 && dd>=bh){ window.__q210s=se; return dd; } if(best){ window.__q210s=best; return bh; } window.__q210s=null; return 0; }
"""


# ── 색 계산 ──
def parse_rgba(s):
    s = s.strip()
    if s.startswith("rgb"):
        v = s[s.index("(") + 1:s.rindex(")")].replace("/", ",").replace(" ", ",")
        p = [x for x in v.split(",") if x]
        r, g, b = [float(x) for x in p[:3]]
        a = float(p[3]) if len(p) > 3 else 1.0
        return [r, g, b], a
    if s.startswith("color(srgb"):
        v = s[s.index("(") + 1:s.rindex(")")].replace("srgb", "").replace("/", " ").split()
        r, g, b = [float(x) * 255 for x in v[:3]]
        a = float(v[3]) if len(v) > 3 else 1.0
        return [r, g, b], a
    if s.startswith("oklch") or s.startswith("lab") or s.startswith("oklab"):
        return None, 1.0
    return None, 1.0


def lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def lum(c):
    return 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2])


def cr(a, b):
    l1, l2 = lum(a), lum(b)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def _num(tok):
    tok = tok.strip()
    if tok.endswith("%"):
        return float(tok[:-1]) / 100.0
    return float(tok)


def apply_filter(c, fstr):
    """CSS filter 문자열(brightness · invert · hue-rotate · grayscale · saturate · contrast · sepia)을 색 하나에 — 브라우저 식과 같게(sRGB)."""
    v = [x / 255.0 for x in c]
    import re
    for fn, arg in re.findall(r"([a-z-]+)\(([^)]*)\)", fstr):
        if fn == "brightness":
            k = _num(arg); v = [x * k for x in v]
        elif fn == "invert":
            k = _num(arg); v = [x * (1 - k) + (1 - x) * k for x in v]
        elif fn == "contrast":
            k = _num(arg); v = [(x - 0.5) * k + 0.5 for x in v]
        elif fn in ("hue-rotate", "saturate", "grayscale", "sepia"):
            if fn == "hue-rotate":
                a = arg.strip(); deg = float(a[:-3]) if a.endswith("deg") else (float(a[:-3]) * 180 / math.pi if a.endswith("rad") else float(a or 0))
                t = math.radians(deg); co, si = math.cos(t), math.sin(t)
                m = [[0.213 + co * 0.787 - si * 0.213, 0.715 - co * 0.715 - si * 0.715, 0.072 - co * 0.072 + si * 0.928],
                     [0.213 - co * 0.213 + si * 0.143, 0.715 + co * 0.285 + si * 0.140, 0.072 - co * 0.072 - si * 0.283],
                     [0.213 - co * 0.213 - si * 0.787, 0.715 - co * 0.715 + si * 0.715, 0.072 + co * 0.928 + si * 0.072]]
            elif fn == "saturate":
                s = _num(arg)
                m = [[0.213 + 0.787 * s, 0.715 - 0.715 * s, 0.072 - 0.072 * s], [0.213 - 0.213 * s, 0.715 + 0.285 * s, 0.072 - 0.072 * s],
                     [0.213 - 0.213 * s, 0.715 - 0.715 * s, 0.072 + 0.928 * s]]
            elif fn == "grayscale":
                g = 1 - min(1, _num(arg))
                m = [[0.2126 + 0.7874 * g, 0.7152 - 0.7152 * g, 0.0722 - 0.0722 * g], [0.2126 - 0.2126 * g, 0.7152 + 0.2848 * g, 0.0722 - 0.0722 * g],
                     [0.2126 - 0.2126 * g, 0.7152 - 0.7152 * g, 0.0722 + 0.9278 * g]]
            else:
                s = 1 - min(1, _num(arg))
                m = [[0.393 + 0.607 * s, 0.769 - 0.769 * s, 0.189 - 0.189 * s], [0.349 - 0.349 * s, 0.686 + 0.314 * s, 0.168 - 0.168 * s],
                     [0.272 - 0.272 * s, 0.534 - 0.534 * s, 0.131 + 0.869 * s]]
            v = [sum(m[i][j] * v[j] for j in range(3)) for i in range(3)]
        v = [min(1.0, max(0.0, x)) for x in v]
    return [x * 255 for x in v]


def bg_colors(img, it):
    W, H = img.size
    x0, y0 = max(0, int(it["x"])), max(0, int(it["y"]))
    x1, y1 = min(W, int(it["x"] + it["w"])), min(H, int(it["y"] + it["h"]))
    if x1 - x0 < 1 or y1 - y0 < 1:
        return []
    px = list(img.crop((x0, y0, x1, y1)).getdata()) if not hasattr(Image.Image, "get_flattened_data") else img.crop((x0, y0, x1, y1)).get_flattened_data()
    cnt = Counter(tuple(p[:3]) for p in px)
    tot = sum(cnt.values())
    # 비슷한 색(±6)끼리 묶기 — 글꼴 가장자리·그라데이션 잡티
    groups = []
    for col, n in cnt.most_common(40):
        for g in groups:
            if max(abs(col[i] - g[0][i]) for i in range(3)) <= 6:
                g[1] += n
                break
        else:
            groups.append([col, n])
    main = [g[0] for g in groups if g[1] / tot >= 0.15]
    return main or [groups[0][0]]


def judge(it, img):
    fg, a = parse_rgba(it["c"])
    if fg is None:
        return None
    alpha = a * it["o"]
    bgs = bg_colors(img, it)
    if not bgs:
        return None
    ff = fg
    for f in it["f"]:                       # 안쪽 filter 부터 바깥(html) 순
        ff = apply_filter(ff, f)
    worst, wbg, wfg = 99, None, None
    for b in bgs:
        eff = [alpha * ff[i] + (1 - alpha) * b[i] for i in range(3)]
        r = cr(eff, b)
        if r < worst:
            worst, wbg, wfg = r, b, eff
    big = it["fs"] >= 24 or (it["fw"] >= 700 and it["fs"] >= 18.66)
    need = 3.0 if big else 4.5
    return {"cr": round(worst, 2), "need": need, "bg": "#%02x%02x%02x" % tuple(int(round(x)) for x in wbg),
            "fg": "#%02x%02x%02x" % tuple(int(round(x)) for x in wfg), "big": big}


def run():
    res = {"name": NAME, "base": BASE, "items": [], "errors": [], "pages": 0}
    shotdir = os.path.join(HERE, "shots", NAME)
    os.makedirs(shotdir, exist_ok=True)
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        for theme in THEMES:
            for (w, h) in WIDTHS:
                ctx = br.new_context(viewport={"width": w, "height": h}, device_scale_factor=1, is_mobile=(w < 768), has_touch=(w < 768))
                ctx.add_init_script("try{localStorage.setItem('knk.theme','%s');localStorage.setItem('knk_works_install_hint_never','1')}catch(e){}" % theme)
                page = ctx.new_page()
                errs = []
                page.on("pageerror", lambda e: errs.append(str(e)[:200]))
                for (scene, who, url, act, only_theme) in SCENES:
                    if only_theme and only_theme != theme:
                        continue
                    ctx.clear_cookies()
                    ctx.add_cookies([{"name": "tuser", "value": str(U[who]), "url": BASE}])
                    del errs[:]
                    try:
                        page.goto(BASE + url, wait_until="load", timeout=30000)
                    except Exception as e:
                        res["errors"].append({"scene": scene, "theme": theme, "w": w, "err": "열기 실패 " + str(e)[:150]})
                        continue
                    page.add_style_tag(content=STILL_CSS)
                    page.wait_for_timeout(700)
                    if act:
                        try:
                            page.evaluate("()=>{" + act + "}")
                        except Exception as e:
                            res["errors"].append({"scene": scene, "theme": theme, "w": w, "err": "누르기 실패 " + str(e)[:150]})
                        page.wait_for_timeout(1200)
                    kt = page.evaluate("document.documentElement.getAttribute('data-kt')")
                    if SHOTS and w in (1440, 390):
                        page.screenshot(path=os.path.join(shotdir, "%s_%s_%d.png" % (scene, theme, w)))
                    sc = page.evaluate(JS_SCROLLER)
                    steps = 1 + min(3, int(sc // max(200, h - 150))) if sc else 1
                    seen = set()
                    for st in range(steps):
                        if st:
                            page.evaluate("(d)=>{ const s=window.__q210s; if(s) s.scrollTop += d; }", h - 150)
                            page.wait_for_timeout(600)
                        # 🔴 글자 자리를 잰 때와 사진 찍은 때의 화면 위치가 같아야 한다 — 화면 위치 복원 스크립트가 늦게 스크롤을 옮기는 일이 있어
                        #    (전후 판 모두 「보기만 직원」 390 에서 저장 단추가 글자 뒤에 찍힘) 앞뒤 위치를 비교해 다르면 다시 잰다.
                        POS = "()=>{const s=window.__q210s||document.scrollingElement; return [s.scrollTop, document.scrollingElement.scrollTop, document.body.scrollHeight]}"
                        for _try in range(4):
                            p0 = page.evaluate(POS)
                            items = page.evaluate(JS_COLLECT)
                            hid = page.add_style_tag(content=HIDE_CSS)
                            page.evaluate(JS_HIDE)
                            page.wait_for_timeout(300)
                            img = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
                            p1 = page.evaluate(POS)
                            page.evaluate(JS_UNHIDE)
                            hid.evaluate("e=>e.remove()")
                            if p0 == p1:
                                break
                            res.setdefault("moved", []).append({"scene": scene, "theme": theme, "w": w, "step": st, "p0": p0, "p1": p1})
                            page.wait_for_timeout(800)
                        for it in items:
                            key = (it["p"], it["t"], it["kind"])
                            if key in seen:
                                continue
                            seen.add(key)
                            j = judge(it, img)
                            if not j:
                                continue
                            it.update(j)
                            it["rw"], it["step"] = it["w"], st        # 글자 칸 폭(아래 w 는 화면 폭으로 덮임)
                            it["bgs"] = ["#%02x%02x%02x" % tuple(c) for c in bg_colors(img, it)]
                            it.update({"scene": scene, "theme": theme, "kt": kt, "w": w, "url": url})
                            res["items"].append(it)
                    res["pages"] += 1
                    if errs:
                        res["errors"].append({"scene": scene, "theme": theme, "w": w, "err": list(errs)})
                    print("·", NAME, theme, w, scene, "글자", len(seen), "오류", len(errs), flush=True)
                ctx.close()
        br.close()
    io.open(os.path.join(HERE, "result_%s.json" % NAME), "w", encoding="utf-8", newline="").write(json.dumps(res, ensure_ascii=False))
    bad = [i for i in res["items"] if i["cr"] < i["need"]]
    print("끝:", NAME, "화면", res["pages"], "글자", len(res["items"]), "기준 미달", len(bad), "화면 오류", len(res["errors"]))


if __name__ == "__main__":
    run()
