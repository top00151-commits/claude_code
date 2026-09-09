#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""WP-04 BOM 권한 — 세션01 전달용 「시험 화면」 만들기 (대표 지시 2026-09-09)

무엇을 만드는가
  실제 화면(HTML)을 사람 조합별로 **그대로 찍어** 파일로 남긴다.
  세션01 은 서버를 띄우지 않고 파일만 열어 보면 된다.

⛔ 운영 DB 를 열지 않는다 — 임시 폴더에 시험용 DB 를 새로 만든다.
⛔ 실명·연락처·거래내용 없음 — 전부 「시험○○」 가상 계정.

실행:  python _검증/make_bom_perm_screens.py
결과:  _검증/_화면_BOM권한_<날짜>/  (index.html 부터 열면 됨)
"""
import os
import sys
import tempfile
import datetime

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import app.database as D                                    # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_bomscreen_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "screen.db")
assert D.DB_PATH != _REAL, "운영 DB 로 갈 뻔했다"
D.init_db()

import app.main as appmain                                  # noqa: E402
from fastapi.testclient import TestClient                   # noqa: E402

appmain._BT_STORE = os.path.join(TMP, "store")
os.makedirs(appmain._BT_STORE, exist_ok=True)

CUR = {"u": None}
appmain.get_user = lambda request: CUR["u"]
cl = TestClient(appmain.app, follow_redirects=False)

# ── 운영 실측 4조합 + 이번에 새로 막히는 경우 ──
BUYER = {"id": 903, "name": "시험구매", "role": "member", "team_id": 10,
         "can_use_logistics": 1, "can_view_logistics": 1}
BUYER_NOINFO = {"id": 906, "name": "시험구매(정보권한없음)", "role": "member", "team_id": 9,
                "can_use_logistics": 1, "can_view_logistics": 1}
DESIGN = {"id": 901, "name": "시험설계", "role": "member", "team_id": 4,
          "can_use_logistics": 0, "can_view_logistics": 1}
SW = {"id": 902, "name": "시험SW", "role": "member", "team_id": 5,
      "can_use_logistics": 0, "can_view_logistics": 1}
VIEWONLY = {"id": 904, "name": "시험영업", "role": "member", "team_id": 1,
            "can_use_logistics": 0, "can_view_logistics": 1}

with D.db_session() as conn:
    for uu in (BUYER, BUYER_NOINFO, DESIGN, SW, VIEWONLY):
        conn.execute("INSERT INTO users(id, name, login_id, password, role) VALUES(?,?,?,'x',?)",
                     (uu["id"], uu["name"], "P%d" % uu["id"], uu["role"]))
    conn.execute("DELETE FROM field_access_policy")
    for cat, teams in (("purchase_price", (1, 2, 4, 10, 11, 15)),
                       ("supplier_info", (1, 10, 11, 15))):
        for t in teams:
            conn.execute("INSERT INTO field_access_policy(category, team_id) VALUES(?,?)", (cat, t))

LEFTOVER = []
OUT = os.path.join(HERE, "_화면_BOM권한_" + datetime.date.today().strftime("%Y%m%d"))
os.makedirs(OUT, exist_ok=True)
SHOTS = []


import io                                                      # noqa: E402
import base64                                                  # noqa: E402
import re as _re                                               # noqa: E402

_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".gif": "image/gif",
         ".svg": "image/svg+xml", ".ico": "image/x-icon", ".webp": "image/webp"}

_CSS1 = r'<link[^>]+rel="stylesheet"[^>]*href="(/static/[^"]+)"[^>]*>'
_CSS2 = r'<link[^>]+href="(/static/[^"]+[.]css[^"]*)"[^>]*rel="stylesheet"[^>]*>'
_IMG  = r'src="(/static/[^"]+)"'
_ANY  = r'"(/static/[^"]+)"'


def inline_assets(html):
    """바깥 CSS·그림을 **파일 안으로 넣는다.**
    🔴 이걸 안 하면 화면을 파일로 열었을 때 모양이 통째로 깨진다 — 세션01 이 잘못 볼 수 있다.
    """
    misses = []

    def css(m):
        rel = m.group(1).split('?')[0].lstrip('/')
        fp = os.path.join(ROOT, rel)
        if not os.path.exists(fp):
            misses.append(rel)
            return m.group(0)
        return ('<style>/* ' + rel + ' */' + chr(10)
                + io.open(fp, encoding='utf-8').read() + '</style>')

    html = _re.sub(_CSS1, css, html)
    html = _re.sub(_CSS2, css, html)

    def img(m):
        rel = m.group(1).split('?')[0].lstrip('/')
        fp = os.path.join(ROOT, rel)
        if not os.path.exists(fp):
            misses.append(rel)
            return m.group(0)
        mime = _MIME.get(os.path.splitext(fp)[1].lower(), 'application/octet-stream')
        with open(fp, 'rb') as fh:
            b = base64.b64encode(fh.read()).decode()
        return 'src=' + chr(34) + 'data:' + mime + ';base64,' + b + chr(34)

    html = _re.sub(_IMG, img, html)
    return html, sorted(set(misses)), sorted(set(_re.findall(_ANY, html)))


def shot(fname, title, why, user, url, method="GET", data=None):
    """화면 하나를 실제로 그려 파일로 남긴다. 리다이렉트는 따라가서 최종 화면을 찍는다."""
    CUR["u"] = user
    r = cl.request(method, url, data=data)
    hops = []
    while r.status_code in (301, 302, 303, 307) and len(hops) < 4:
        loc = r.headers.get("location", "")
        hops.append("%d -> %s" % (r.status_code, loc))
        r = cl.get(loc)
    html = r.text
    banner = (
        '<div style="position:sticky;top:0;z-index:99999;background:#0b3d91;color:#fff;'
        'padding:10px 14px;font:14px/1.6 -apple-system,Segoe UI,sans-serif">'
        '<b>' + title + '</b> &nbsp;|&nbsp; ' + why +
        '<br><span style="opacity:.8;font-size:12px">사람: ' + user["name"] +
        ' (팀' + str(user["team_id"]) + ') &nbsp;·&nbsp; 요청: ' + method + ' ' + url +
        ' &nbsp;·&nbsp; 결과: ' + str(r.status_code) +
        (' &nbsp;·&nbsp; ' + " / ".join(hops) if hops else '') +
        ' &nbsp;·&nbsp; <i>시험용 가상 계정 · 운영 자료 아님</i></span></div>')
    html, _miss, _left = inline_assets(html)
    if _miss:
        print('    ⚠ 못 찾은 자원: ' + ', '.join(_miss))
    LEFTOVER.extend(_left)
    if "<body" in html:
        i = html.index("<body")
        j = html.index(">", i) + 1
        html = html[:j] + banner + html[j:]
    else:
        html = banner + html
    with open(os.path.join(OUT, fname), "w", encoding="utf-8") as fh:
        fh.write(html)
    SHOTS.append((fname, title, why, r.status_code, " / ".join(hops)))
    print("  찍음  %-34s %s (%d)" % (fname, title, r.status_code))
    return html


print("=" * 74)
print("  WP-04 BOM 권한 — 세션01 전달용 시험 화면")
print("=" * 74)

# ① 홈 카드 3갈래
shot("01_홈_구매.html", "① 홈 — 구매 담당", "카드가 「구매 서류 만들기」로 뜬다", BUYER, "/logistics")
shot("02_홈_설계.html", "② 홈 — 설계 담당", "카드가 「설계 BOM 만들기」로 뜬다", DESIGN, "/logistics")
shot("03_홈_조회.html", "③ 홈 — 조회 전용", "카드가 「BOM 자료 보기」로 뜬다", VIEWONLY, "/logistics")

# ② 도구 화면 — 구매/설계/조회
shot("04_도구_구매.html", "④ 도구 — 구매 담당",
     "구매 작업 묶음이 보인다(단가·견적·발주)", BUYER, "/bom/tools?mode=purchase")
shot("05_도구_설계.html", "⑤ 도구 — 설계 담당",
     "구매 작업 묶음이 화면에 아예 없다", DESIGN, "/bom/tools")
shot("06_도구_SW.html", "⑥ 도구 — 단가·구매처 둘 다 못 보는 사람",
     "설계 작업만 · 남의 구매 자료는 자물쇠", SW, "/bom/tools")
shot("07_도구_조회.html", "⑦ 도구 — 조회 전용", "만들기 없이 보기만", VIEWONLY, "/bom/tools")

# ③ ⭐이번 변경의 핵심 — 시작 전에 막는다
shot("08_시작전차단_단가.html", "⑧ ⭐시작 전 차단 — 단가 채우기",
     "구매 실행권한은 있으나 단가·구매처 열람권한이 없어 <b>일을 시작하기 전에</b> 막는다",
     BUYER_NOINFO, "/bom/tools/run/price", "POST", {})
shot("09_시작전차단_발주.html", "⑨ ⭐시작 전 차단 — 발주서",
     "네 가지 구매 작업(단가·견적·발주·수정) 모두 같은 검사를 지난다",
     BUYER_NOINFO, "/bom/tools/run/po", "POST", {})
shot("10_정상통과_구매.html", "⑩ 대조 — 권한 갖춘 구매 담당",
     "같은 요청이 <b>권한 검사에 막히지 않는다</b>(자료 없음 안내까지 진행)",
     BUYER, "/bom/tools/run/price", "POST", {})

# ④ 아무 기록도 남지 않았는지 (헛수고 방지 확인)
with D.db_session() as c:
    nrun = c.execute("SELECT COUNT(*) FROM bom_tool_runs").fetchone()[0]
nfile = len([f for f in os.listdir(appmain._BT_STORE)
             if os.path.isfile(os.path.join(appmain._BT_STORE, f))])
_lo = sorted(set(LEFTOVER))
print('  확인  파일 안에 못 넣은 바깥 자원 %d개 (0 이어야 모양이 온전하다)' % len(_lo)
      + ('' if not _lo else ' -> ' + ', '.join(_lo)))
print("  확인  차단 뒤 남은 기록 %d건 · 남은 파일 %d개 (둘 다 0 이어야 함)" % (nrun, nfile))

rows = "".join(
    '<tr><td><a href="%s">%s</a></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'
    % (f, f, t, w, s, h or "-") for f, t, w, s, h in SHOTS)
idx = (
    '<meta charset="utf-8"><title>WP-04 BOM 권한 시험 화면</title>'
    '<style>body{font:15px/1.7 -apple-system,Segoe UI,sans-serif;max-width:1100px;margin:24px auto;padding:0 16px}'
    'table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:8px;vertical-align:top}'
    'th{background:#f2f5fa;text-align:left}code{background:#f4f4f4;padding:1px 5px;border-radius:3px}'
    '.n{background:#fff8e1;border-left:4px solid #f0a500;padding:10px 14px;margin:14px 0}</style>'
    '<h1>WP-04 BOM 권한 — 시험 화면</h1>'
    '<p>만든 때: ' + datetime.datetime.now().strftime("%Y-%m-%d %H:%M") + ' KST · 가지 <code>wp04-perm2</code></p>'
    '<div class="n">아래는 <b>실제 화면을 그대로 찍은 것</b>입니다(그림이 아니라 진짜 HTML). '
    '전부 <b>시험용 가상 계정</b>이고 운영 DB 는 열지 않았습니다. '
    '⛔ main 병합·운영 배포는 하지 않았습니다.</div>'
    '<p>차단 뒤 남은 기록 <b>' + str(nrun) + '건</b> · 남은 파일 <b>' + str(nfile) + '개</b> '
    '— 막힌 사람에게 <b>헛수고를 시키지 않는다</b>는 뜻입니다.</p>'
    '<table><tr><th>파일</th><th>화면</th><th>무엇을 보나</th><th>응답</th><th>이동</th></tr>'
    + rows + '</table>')
with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as fh:
    fh.write(idx)

print("-" * 74)
print("  화면 %d장 · 폴더: %s" % (len(SHOTS), OUT))
print("  먼저 열 파일: " + os.path.join(OUT, "index.html"))
sys.exit(0 if (nrun == 0 and nfile == 0 and not _lo) else 1)
