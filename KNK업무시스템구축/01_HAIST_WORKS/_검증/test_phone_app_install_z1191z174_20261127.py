# -*- coding: utf-8 -*-
"""z1191z174 (대표 11-27 「도움말 오른쪽에 휴대폰에서 앱 설치를 바로 할 수 있는 아이콘」) — 설치 화면·QR·상단 📲."""
import os, sys, re, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z174-test-only-not-a-real-key"   # 시험용 가짜 값
import app.database as D
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(tempfile.mkdtemp(), "t.db")
assert D.DB_PATH != _REAL
R = []
def check(l, c, g=""):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l + ("" if c else "  → " + str(g)[:200]))
from fastapi.testclient import TestClient
import app.main as M
cl = TestClient(M.app, follow_redirects=False)
r = cl.get("/app/install")
check("설치 화면 = 로그인 없이 200 · 설치 단추 · 아이폰 안내 · 메신저 안 화면 안내 · 앱 정보(manifest)", r.status_code == 200 and "📲 앱 설치" in r.text and "홈 화면에 추가" in r.text and "크롬에서 열기" in r.text and "/manifest.webmanifest" in r.text, r.status_code)
check("설치 화면에 업무 자료 없음(로그인 안 한 사람도 보므로)", "수주" not in r.text and "고객" not in r.text, "")
q = cl.get("/app/install/qr.svg")
check("QR = 그림(svg) 200", q.status_code == 200 and q.headers.get("content-type", "").startswith("image/svg") and "<svg" in q.text, q.status_code)
chrome = open(os.path.join(ROOT, "app", "templates", "_v5_partials", "chrome.html"), encoding="utf-8").read()
i_help = chrome.find('title="{{ i.ch_help }}">❓</a>'); i_btn = chrome.find('id="knkPhoneAppBtn"'); i_user = chrome.find('<a class="top-user"')
check("상단 📲 = 도움말(❓) 바로 오른쪽 · 내 정보 앞", 0 < i_help < i_btn < i_user, (i_help, i_btn, i_user))
check("PC 창 = 「✕ 닫기」 · QR · 주소 복사", "knkPhoneAppPop" in chrome and "✕ 닫기" in chrome[chrome.find('id="knkPhoneAppPop"'):chrome.find('id="knkPhoneAppPop"') + 3000] and "/app/install/qr.svg" in chrome, "")
m = re.search(r'<div id="knkPhoneAppPop"[^>]*>', chrome)
check("숨긴 창이 화면을 막지 않음: 창 태그에 display 직접 안 씀 + [hidden] 규칙", m and "display" not in m.group(0) and "#knkPhoneAppPop[hidden] { display:none !important; }" in chrome, m and m.group(0))
print(chr(10) + "결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
