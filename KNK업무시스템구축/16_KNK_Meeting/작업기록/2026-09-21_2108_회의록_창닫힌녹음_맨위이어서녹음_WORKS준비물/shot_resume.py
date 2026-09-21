# -*- coding: utf-8 -*-
"""z1120 비교 사진 — 아이폰 화면(390×844)에서 창을 닫아 멈춘 녹음 회의를 열었을 때 「첫 화면」 전·후.
사용: py -3.12 shot_resume.py <고치기 전 포트> <회의 id> <고친 뒤 포트> <회의 id> <저장할 png>
(두 서버 = run_resume_app.py · 고치기 전 = 운영과 같은 파일 · 고친 뒤 = z1120)"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8")
from PIL import Image, ImageDraw, ImageFont   # noqa: E402
from playwright.sync_api import sync_playwright   # noqa: E402

P0, M0, P1, M1, OUT = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
      "Version/18.2 Mobile/15E148 Safari/604.1")
HIDE = ("document.addEventListener('DOMContentLoaded', () => { const s = document.createElement('style');"
        "s.textContent = '#worksInstallHint{display:none !important}'; document.head.appendChild(s); });")


def shot(pw, port, mid, staff):
    br = pw.chromium.launch(channel="chrome", headless=True)
    c = br.new_context(service_workers="block", user_agent=UA, viewport={"width": 390, "height": 844},
                       is_mobile=True, has_touch=True, device_scale_factor=2)
    c.add_cookies([{"name": "tuser", "value": str(staff), "url": "http://localhost:%d" % port}])
    c.add_init_script(HIDE)
    p = c.new_page()
    p.goto("http://localhost:%d/meetings/%d" % (port, mid), wait_until="domcontentloaded")
    p.wait_for_timeout(1500)
    y = p.evaluate("() => { const b=document.getElementById('recResume'); return b ? Math.round(b.getBoundingClientRect().top + scrollY) : -1; }")
    png = p.screenshot()
    br.close()
    return Image.open(io.BytesIO(png)).convert("RGB"), y


def main():
    staff = int(sys.argv[6]) if len(sys.argv) > 6 else 1
    with sync_playwright() as pw:
        a, ya = shot(pw, P0, M0, staff)
        b, yb = shot(pw, P1, M1, staff)
    w, h = a.size
    pad, top = 40, 150
    out = Image.new("RGB", (w * 2 + pad * 3, h + top + pad), "white")
    out.paste(a, (pad, top))
    out.paste(b, (w + pad * 2, top))
    d = ImageDraw.Draw(out)
    try:
        f = ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf", 34)
        f2 = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 26)
    except Exception:
        f = f2 = ImageFont.load_default()
    d.text((pad, 30), "지금(운영) — 첫 화면에 「이어서 녹음」 없음", fill=(185, 28, 28), font=f)
    d.text((pad, 80), "상자는 %dpx 아래(화면 높이 844px · 두 화면 넘게 내려야 함)" % ya, fill=(90, 90, 90), font=f2)
    d.text((w + pad * 2, 30), "고친 뒤(z1120) — 맨 위에 「이어서 녹음」", fill=(21, 128, 61), font=f)
    d.text((w + pad * 2, 80), "상자 위치 %dpx · 스크롤 없이 한 번 누르면 이어서 녹음" % yb, fill=(90, 90, 90), font=f2)
    d.rectangle([pad - 2, top - 2, pad + w + 1, top + h + 1], outline=(200, 200, 200), width=2)
    d.rectangle([w + pad * 2 - 2, top - 2, w * 2 + pad * 2 + 1, top + h + 1], outline=(200, 200, 200), width=2)
    out.save(OUT)
    print("저장", OUT, "· 전 %dpx · 후 %dpx" % (ya, yb))


main()
