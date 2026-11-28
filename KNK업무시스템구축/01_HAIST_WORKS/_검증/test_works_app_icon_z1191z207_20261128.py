# -*- coding: utf-8 -*-
"""z1191z207 (대표 11-28 「이음웍스 아이콘을 이음웍스에 맞게」 → 「1 업무 가방」) — 앱 아이콘 = 디자인 원본 파일 그대로.
기준 문서 HAIST WORKS디자인변경/2026-11-28_이음웍스_앱아이콘/2026-11-28_1733_세션01_넘김_이음웍스_앱아이콘_업무가방.md 3절 끝 기준.
"""
import os, sys, re, json, hashlib, shutil, tempfile
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "deploy"))
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z207-test-only-not-a-real-key"   # 시험용 가짜 값
import app.database as D
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(tempfile.mkdtemp(), "t.db")
assert D.DB_PATH != _REAL
R = []
def check(l, c, g=""):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l + ("" if c else "  → " + str(g)[:200]))

# 디자인 원본 지문(넘김 문서 폴더의 파일 · 2026-11-28 17:3x)
SHA = {
    "works-icon.svg": "d3eee0d280cc33807b66537e7d8ef22d05e5a7f5444548c26a1fc9993f2eeba8",
    "works-icon-maskable.svg": "a9d7c2744838643264cd934fb146506f115647980106137b087eb235808c1c66",
    "works-icon-180.png": "6ae0575aa3b15859c9d8f774ec3834fbfefc0018b04819211ede365dd39ee2c9",
    "works-icon-192.png": "e4be9788a4246e4ccc6fc0540feeeb987b07bbd0ca27bb032be20c7396731b6a",
    "works-icon-512.png": "20a3e4805a9e151485cfb8526787f0cd6bc5b1ad174e60fa03bced278731a701",
}
BD = os.path.join(ROOT, "static", "img", "brand")
def fb(f):
    p = os.path.join(BD, f)
    return open(p, "rb").read() if os.path.isfile(p) else b""
h = lambda b: hashlib.sha256(b).hexdigest()

# ── 1. 파일 넣기(3-1) ──
for f, want in SHA.items():
    check("static/img/brand/%s = 디자인 원본과 바이트 같음(sha256)" % f, h(fb(f)) == want, h(fb(f)))
SRC = os.path.join(ROOT, "HAIST WORKS디자인변경", "2026-11-28_이음웍스_앱아이콘")
if os.path.isdir(SRC):
    check("디자인 원본 폴더(이 PC)와도 바이트 같음", all(open(os.path.join(SRC, f), "rb").read() == fb(f) for f in SHA))
check("아이콘 색 = 회사 빨강 #AE2025(옛 #A5282C 없음)", b"#AE2025" in fb("works-icon.svg") and b"A5282C" not in fb("works-icon.svg").upper())

# ── 2. 서버가 파일 그대로(3-2) ──
from fastapi.testclient import TestClient
import app.main as M
cl = TestClient(M.app, follow_redirects=False)
for path, f, ct in (("/icon.svg", "works-icon.svg", "image/svg+xml"), ("/icon-180.png", "works-icon-180.png", "image/png"),
                    ("/icon-192.png", "works-icon-192.png", "image/png"), ("/icon-512.png", "works-icon-512.png", "image/png"),
                    ("/icon.svg?v=3", "works-icon.svg", "image/svg+xml"), ("/icon-512.png?v=3", "works-icon-512.png", "image/png")):
    r = cl.get(path)
    check("%s = 200 · 받은 바이트 = %s · %s · 캐시 7일" % (path, f, ct),
          r.status_code == 200 and r.content == fb(f) and len(r.content) > 0 and r.headers.get("content-type", "").startswith(ct)
          and r.headers.get("cache-control") == "public, max-age=604800", (r.status_code, r.headers.get("content-type"), h(r.content)))
r = cl.get("/icon-77.png")
check("그 밖 크기(/icon-77.png) = 192 파일", r.status_code == 200 and r.content == fb("works-icon-192.png"), r.status_code)
src = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
check("서버 그리기 지움(_works_pwa_icon_png · _WORKS_PWA_ICON_SVG 없음)", "_works_pwa_icon_png" not in src and "_WORKS_PWA_ICON_SVG" not in src)
check("메일 앱(/mail) 아이콘·manifest 는 그대로(세션 15 · 대상 아님)", "def _mail_pwa_icon_png" in src or "/mail/icon.svg" in src)

# ── 3. 옛 아이콘이 남지 않게(3-3) ──
r = cl.get("/manifest.webmanifest"); mf = r.json()
ic = {i["src"]: i for i in mf.get("icons", [])}
check("manifest 200 · 아이콘 주소 셋 모두 ?v=3", r.status_code == 200 and set(ic) == {"/icon-192.png?v=3", "/icon-512.png?v=3", "/icon.svg?v=3"}, list(ic))
check("manifest purpose: PNG 192·512 = any maskable · SVG = any",
      ic.get("/icon-192.png?v=3", {}).get("purpose") == "any maskable" and ic.get("/icon-512.png?v=3", {}).get("purpose") == "any maskable"
      and ic.get("/icon.svg?v=3", {}).get("purpose") == "any")
check("manifest theme_color = #AE2025", mf.get("theme_color") == "#AE2025", mf.get("theme_color"))
check("앱 이름·시작 주소·링크 잡기·related_applications 그대로",
      mf.get("name") == "KNK Eum WORKS" and mf.get("short_name") == "Eum WORKS" and mf.get("start_url") == "/app" and mf.get("scope") == "/"
      and mf.get("launch_handler") == {"client_mode": ["navigate-existing", "auto"]} and mf.get("handle_links") == "preferred"
      and mf.get("related_applications") == [{"platform": "webapp", "url": "https://works.knknara.co.kr/manifest.webmanifest"}]
      and mf.get("id") == "/?app=works" and "share_target" in mf)
hd = open(os.path.join(ROOT, "app", "templates", "_v5_partials", "works_pwa_head.html"), encoding="utf-8").read()
check("화면 머리 조각: ?v=3 · theme-color #AE2025 · ?v=2 · #A5282C 없음",
      'href="/icon.svg?v=3"' in hd and 'href="/icon-180.png?v=3"' in hd and '<meta name="theme-color" content="#AE2025">' in hd and "?v=2" not in hd and "A5282C" not in hd.upper())
r = cl.get("/app/install")
check("그린 화면(/app/install) 머리에 ?v=3 · theme-color #AE2025", r.status_code == 200 and "/icon.svg?v=3" in r.text and "/icon-180.png?v=3" in r.text and 'content="#AE2025"' in r.text, r.status_code)
check("설치 화면 위 그림도 새 아이콘(/icon-192.png?v=3 · ?v=2 없음)", '<img src="/icon-192.png?v=3"' in r.text and "?v=2" not in r.text)

# ── 4. 검사기 ⑤-3 이 일부러 어긴 아이콘을 잡는가 ──
import check_standards as C
os.environ.setdefault("KNK_BRAND_JSON", C._brand_json_path(ROOT))
fx, _ = C.check_logo_files([], root=ROOT)
fxi = [x for x in fx if "works-icon" in x[0]]
check("검사기 ⑤-3: 지금 판 = 앱 아이콘 위반 0 (다른 로고 파일 위반은 이 시험 몫 아님)", fxi == [] and hasattr(C, "APP_ICON_SHA256"), fxi[:3])
def fake_root():
    t = tempfile.mkdtemp(prefix="z207_")
    shutil.copytree(BD, os.path.join(t, "static", "img", "brand"))
    return t
t = fake_root(); p = os.path.join(t, "static", "img", "brand", "works-icon-192.png")
b = bytearray(open(p, "rb").read() if os.path.isfile(p) else b"x" * 40); b[-20] ^= 0xFF; open(p, "wb").write(bytes(b))
fx, _ = C.check_logo_files([], root=t)
check("어김① 192 PNG 한 바이트 바꿈 → ⑤-3 잡힘", any("works-icon-192.png" in m and "다름" in m for _f, _l, m in fx), fx[:2])
t = fake_root(); _p = os.path.join(t, "static", "img", "brand", "works-icon.svg")
if os.path.isfile(_p): os.remove(_p)
fx, _ = C.check_logo_files([], root=t)
check("어김② works-icon.svg 지움 → ⑤-3 잡힘(없음)", any("works-icon.svg" in m and "없음" in m for _f, _l, m in fx), fx[:2])
t = fake_root(); open(os.path.join(t, "static", "img", "brand", "works-icon.svg"), "wb").write(fb("works-icon.svg").replace(b"#AE2025", b"#A5282C"))
fx, _ = C.check_logo_files([], root=t)
check("어김③ 아이콘 SVG 를 옛 빨강으로 다시 그림 → ⑤-3 잡힘", any("works-icon.svg" in m for _f, _l, m in fx), fx[:2])

print("결과: %d/%d 통과" % (sum(R), len(R)))
sys.exit(0 if all(R) else 1)
