# -*- coding: utf-8 -*-
"""z1191s 시험 — 올리는 중에 페이지를 벗어나려 하면 묻기 · 「아직 올리는 중입니다」 띠
   대표 2026-10-27 「파일 올리는중에 페이지를 벗어나면 중지 되는거야?」 → (그렇다 · 23:3x 실제로 끊김 2번)
                  → 「다음 배포 때 올리는 중에 페이지를 벗어나려 하면 「아직 올리는 중입니다」 경고 창이 뜨게 … 이렇게 해줘」
  원문(화면 틀·스크립트): 떠나기 전 묻기는 올리는 중일 때만 · 📚·①·③ 셋 다 켜고 · 어떻게 끝나든 끈다(finally) ·
       띠 자리(공용 「새 판」 띠보다 위 · 글 길이만큼) · 화면이 그려지는지(띠는 숨긴 채)
  (실제로 묻는지·머물면 끝까지 올라가는지·끝나면 안 묻는지는 브라우저 실측 — scratchpad z1191lw/_shot_page_s.py)
"""
import contextlib
import io
import os
import re
import sys
import tempfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191s-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

OK = FAIL = 0


def check(label, cond, got=None):
    global OK, FAIL
    if cond:
        OK += 1
        print("  [OK] " + label)
    else:
        FAIL += 1
        print("  [FAIL] " + label + ("   ← %r" % (got,) if got is not None else ""))


tpl = open(os.path.join(ROOT, "app", "templates", "export_hs_fill.html"), encoding="utf-8").read()
js = tpl[tpl.index("<script>"):]
print("=" * 78)
print("§1 원문")
print("=" * 78)
bu = js[js.index("addEventListener('beforeunload'"):][:260]
check("1 떠나기 전 묻기는 올리는 중일 때만(BUSY 가 비면 그냥 보냄) · 브라우저 기본 확인창(preventDefault + returnValue)",
      js.count("addEventListener('beforeunload'") == 1 and "if(!Object.keys(BUSY).length) return;" in bu
      and "e.preventDefault()" in bu and "e.returnValue" in bu, bu)
check("2 busy(이름, 글) 켜기 · busy(이름) 끄기 — 띠를 보이고/숨기고 진행 글을 붙인다",
      "function busy(key, txt)" in js and "delete BUSY[key]" in js and "b.style.display = ks.length ? '' : 'none'" in js)
hist = js[js.index("window.hfHist = async"):js.index("window.hfHist = async") + 4000]
check("3 📚 등록 — 시작 전에 켜고 파일마다 진행 글 · 반복 전체를 try 로 감싸 finally 에서 끈다",
      re.search(r"busy\('hist', '📚 ' \+ kind \+ ' 0/' \+ n\);\s*try \{\s*for\(", hist) is not None
      and "busy('hist', '📚 ' + kind + ' ' + (i + 1) + '/' + n);" in hist and "} finally { busy('hist'); }" in hist,
      hist[hist.find("busy("):hist.find("busy(") + 80])
fill = js[js.index("window.hfFill = async"):js.index("window.hfFill = async") + 2500]
check("4 ① 자동 채우기 — 켜고 · 파일마다 진행 글 · finally 에서 끈다",
      re.search(r"busy\('fill', '① 0/' \+ n\);\s*try \{\s*for\(", fill) is not None
      and "busy('fill', '① ' + (i + 1) + '/' + n);" in fill and "} finally { busy('fill'); }" in fill)
rep = js[js.index("window.hfReply = async"):]
check("5 ③ 회신 반영 — 한 번에 보내므로 묶음 전체에 켜고 · 원래 finally(단추 풀기)에서 함께 끈다",
      "busy('reply', '③ 회신 ' + inp.files.length + '개');" in rep and "finally { btn.disabled = false; busy('reply'); }" in rep)
css = tpl[tpl.index(".hf-busy {"):tpl.index(".hf-busy {") + 400]
check("6 띠 자리 — 화면에 고정 · 아래 가운데 · 공용 「새 판」 띠(bottom 22px)보다 위(86px) · 글 길이만큼(width:max-content)",
      "position:fixed" in css and "bottom:86px" in css and "width:max-content" in css and "max-width:calc(100vw - 32px)" in css, css)
check("7 띠 글 — 「아직 올리는 중입니다」 · 벗어나거나 새로 고치지 말 것 · 다른 탭·프로그램은 괜찮음 · 처음엔 숨김",
      re.search(r'<div id="hfBusy" class="hf-busy" style="display:none;"[^>]*>⏳ <b>아직 올리는 중입니다</b>', tpl) is not None
      and "이 페이지를 벗어나거나 새로 고치지 마세요" in tpl and "다른 탭이나 프로그램으로 옮기는 것은 괜찮습니다" in tpl)
check("8 띠는 hfHistSum 밖(①·③·등록 뒤 요약을 새로 그려도 안 지워짐) — 카드들 다음 · </main> 앞",
      tpl.index('id="hfBusy"') > tpl.index('id="hfHistOut"') and tpl.index('id="hfBusy"') < tpl.index("</main>"))

print()
print("=" * 78)
print("§2 화면")
print("=" * 78)
TMP = tempfile.mkdtemp(prefix="knk_z1191s_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("name_vi", "TEXT"), ("rank", "TEXT"), ("team_id", "INTEGER"),
                     ("password_version", "INTEGER DEFAULT 1")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, "
                 "can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) VALUES ('가상M901','member','M901','M901','x',1,1,1,1,0,0)")
    U = dict(conn.execute("SELECT * FROM users WHERE employee_no='M901'").fetchone())
import app.main as M                                        # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

M._HS_FILL_DIR = os.path.join(TMP, "hs_fill")
M._HS_HIST_IMG_DIR = os.path.join(TMP, "hs_hist_img")
M.get_user = lambda request, _u=U: _u
cl = TestClient(M.app, follow_redirects=False)
with contextlib.redirect_stdout(io.StringIO()):
    r = cl.get("/export/hs-fill")
check("9 화면 200 · 띠가 숨긴 채로 들어 있음 · 스크립트에 떠나기 전 묻기",
      r.status_code == 200 and re.search(r'<div id="hfBusy" class="hf-busy" style="display:none;"', r.text) is not None
      and "addEventListener('beforeunload'" in r.text, r.status_code)

print()
print("결과: %d개 중 실패 %d" % (OK + FAIL, FAIL))
sys.exit(1 if FAIL else 0)
