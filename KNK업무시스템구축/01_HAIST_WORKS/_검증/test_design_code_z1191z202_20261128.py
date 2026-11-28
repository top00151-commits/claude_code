#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""z1191z202 시험 — 디자인을 코드로(대표 2026-11-28) 0·1·2·5·6단계

  §1 0단계 파일 — static/img/brand/ 19개 = 스킬 knk-brand 원본과 같음 · 나눔스퀘어 woff 4개(wOFF 머리) + OFL.txt
  §2 1·3단계 토큰 — v5_tokens.css 한 곳 · 새 기준 값 = 견본 값이 모든 화면(:root) · 옛 이름·--qv-* 가 새 이름을 가리킴 · 글꼴 나눔스퀘어
     · 테마(부드럽게 -soft · 흐린 글자 고침 묶음 옛 값 고정 없음) · 흐린 글자 명암 ≥4.5 (z1191z203 3단계에서 바꿈)
  §3 2단계 공용 모양 — knk-components.css 의 .k-* (색 숫자 0) · 공용 머리 styles.html 이 부름
  §4 5단계 검사기 지금 코드 통과 + 일부러 어긴 코드 7가지가 실제로 잡힘(브랜드 값 · 다른 파일 회사 색 · 정의 두 곳 · 새 #색 ·
     로고 다른 경로 · 빨간 「KNK」 흉내 · 로고 파일 바꿈 · 없는 글꼴 파일 · 바깥 주소 글꼴)
  §5 6단계 견본 화면 원문 — .knk-ci 로 감쌈 · 로고는 brand 폴더 · ✕ 닫기 · 색 숫자 0

⛔ 운영 DB·운영 화면을 열지 않는다(파일만 읽음). brand.json = <저장소>/00_스킬규정/knk-brand/brand.json (또는 KNK_BRAND_JSON)
실행:  python _검증/test_design_code_z1191z202_20261128.py
"""
import contextlib
import io
import json
import os
import re
import shutil
import sys
import tempfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "deploy"))
import check_standards as CS  # noqa: E402

CNT, FAIL = 0, []


def check(name, ok, extra=None):
    global CNT
    CNT += 1
    print(("  ✅ " if ok else "  ❌ ") + name + ("" if ok or extra is None else "  ← %s" % (extra,)))
    if not ok:
        FAIL.append(name)


def rd(rel):
    return io.open(os.path.join(ROOT, *rel.split("/")), encoding="utf-8").read()


BRAND = CS._brand_json_path()
os.environ["KNK_BRAND_JSON"] = BRAND   # 임시 자리에서도 같은 원본(brand.json · assets)을 보게
SRC = os.path.join(os.path.dirname(BRAND), "assets")
print("§1 0단계 — 로고·패턴·글꼴 파일")
check("brand.json 있음", os.path.isfile(BRAND), BRAND)
bdir = os.path.join(ROOT, "static", "img", "brand")
want = (["knk-symbol_%s.svg" % v for v in ("full", "red", "gray", "black", "white")]
        + ["knk-sig-h-haist_%s.svg" % v for v in ("full", "red", "gray", "black", "white")]
        + ["knk-slogan-best_%s.svg" % v for v in ("full", "red", "gray", "black", "white")]
        + ["knk-sig-h-ko-en_full.svg", "knk-sig-h-en_full.svg", "knk-pattern-tile_red.png", "knk-pattern-tile_white.png"])
have = sorted(os.listdir(bdir)) if os.path.isdir(bdir) else []
check("static/img/brand/ = 문서가 적은 19개가 적어도 다 있음(z205: 다른 세션이 원본 파일을 더할 수 있음)", set(want) <= set(have), sorted(set(want) - set(have)))
def _src_of(f):   # z1191z205: 더한 파일도 스킬 knk-brand 원본(로고 svg·png · 패턴) 중 하나와 바이트까지 같아야 함
    for sub in (os.path.join("logo", "svg"), os.path.join("logo", "png"), "pattern"):
        o = os.path.join(SRC, sub, f)
        if os.path.isfile(o): return o
    return None
_extra = sorted(set(have) - set(want))
check("더한 파일 %d개도 스킬 원본과 같음 %s" % (len(_extra), _extra), all(_src_of(f) and open(_src_of(f), "rb").read() == open(os.path.join(bdir, f), "rb").read() for f in _extra))
for f in want:
    sub = "pattern" if f.startswith("knk-pattern") else os.path.join("logo", "svg")
    o = os.path.join(SRC, sub, f)
    same = os.path.isfile(o) and os.path.isfile(os.path.join(bdir, f)) and open(o, "rb").read() == open(os.path.join(bdir, f), "rb").read()
    if not same:
        check("원본과 같음: " + f, False)
check("19개 모두 스킬 원본과 바이트까지 같음", all(open(os.path.join(SRC, "pattern" if f.startswith("knk-pattern") else os.path.join("logo", "svg"), f), "rb").read()
                                         == open(os.path.join(bdir, f), "rb").read() for f in want if f in have))
fdir = os.path.join(ROOT, "static", "fonts", "nanumsquare")
for f in ("NanumSquareL.woff", "NanumSquareR.woff", "NanumSquareB.woff", "NanumSquareEB.woff"):
    p = os.path.join(fdir, f)
    check("글꼴 %s 있음 · wOFF 머리" % f, os.path.isfile(p) and open(p, "rb").read(4) == b"wOFF")
ofl = io.open(os.path.join(fdir, "OFL.txt"), encoding="utf-8").read() if os.path.isfile(os.path.join(fdir, "OFL.txt")) else ""
check("OFL.txt = 저작권자 · 라이선스 이름 · 주소", "NAVER Corporation" in ofl and "SIL Open Font License, Version 1.1" in ofl and "https://openfontlicense.org" in ofl)

print("§2 1·3단계 — 기준 값 한 곳 · 새 기준 값이 모든 화면(z1191z203)")
tok = rd("static/css/v5_tokens.css")
fnd = rd("static/css/knk-foundation.css")
check("knk-foundation.css 에 --knk-* 정의 없음(한 곳)", not re.search(r"(?<![\w(-])--knk-[a-z0-9-]+\s*:", re.sub(r"/\*.*?\*/", "", fnd, flags=re.S)))
check("knk-foundation.css 에 .knk-num 남음", ".knk-num { font-variant-numeric: tabular-nums; }" in fnd)
# 3단계(z1191z203 · 대표 11-28 「A로 올려」) — 새 기준 값(견본 knk-standard.css · 회사 색 = brand.json)이 모든 화면(:root)
NEW = {"--knk-brand": "var(--knk-brand-red)", "--knk-brand-hover": "#8E2227", "--knk-brand-subtle": "#FBEFEF", "--knk-focus": "var(--knk-brand-red)",
       "--knk-bg-page": "#F4F4F5", "--knk-bg-surface": "#FFFFFF", "--knk-bg-subtle": "#EEEEF0", "--knk-bg-inset": "#F8F8F9", "--knk-bg-hover": "#F4F4F6",
       "--knk-bg-selected": "#FBEFEF", "--knk-text-primary": "var(--knk-brand-ink)", "--knk-text-secondary": "#58595B", "--knk-text-muted": "#656769",
       "--knk-text-disabled": "#A1A2A5", "--knk-border-subtle": "#E6E6E8", "--knk-border-default": "#D7D7DA", "--knk-border-strong": "#B8B9BC",
       "--knk-success": "#2F6B4F", "--knk-info": "#2E5F8A", "--knk-warning": "#8A5A00", "--knk-warning-subtle": "#FBF4E4", "--knk-danger": "#C4320A",
       "--knk-danger-subtle": "#FDF0EA"}
ci_sel, ci = CS._css_block_sel(tok, ".knk-ci")
check("새 기준 값 묶음 선택자 = :root, .knk-ci (모든 화면)", ci_sel == ":root, .knk-ci", ci_sel)
diff = {k: (v, CS._decl(ci or "", k)) for k, v in NEW.items() if (CS._decl(ci or "", k) or "").upper() != v.upper()}
check("새 기준 값 %d개 = 견본 knk-standard.css 값(회사 색은 brand.json)" % len(NEW), not diff, diff)
rb = CS._css_block(tok, ":root")
check("v5_tokens.css 첫 :root 에 회사 색 묶음", rb is not None and "--knk-brand-red" in rb)
dup = sorted(set(re.findall(r"(--knk-[\w-]+)\s*:", rb or "")) & set(re.findall(r"(--knk-[\w-]+)\s*:", ci or "")) - {"--knk-action", "--knk-action-hover", "--knk-action-subtle"})
check("색 값은 한 곳 — 첫 :root 와 새 기준 값 묶음에 겹친 색 이름 없음(var 로 이은 --knk-action 3개 제외)", not dup, dup)
KEEP = {"--knk-radius-control": "6px", "--knk-radius-card": "8px", "--knk-radius-modal": "10px", "--knk-h-control": "36px", "--knk-h-control-sm": "32px",
        "--knk-h-row": "40px", "--knk-sp-1": "4px", "--knk-sp-12": "48px"}
check("크기·여백·모서리는 그대로", all((CS._decl(rb, k) or "") == v for k, v in KEEP.items()))
OLDNAME = {"--ink": "--knk-text-primary", "--ink-soft": "--knk-text-secondary", "--mute": "--knk-text-muted", "--mute-2": "--knk-text-disabled",
           "--line": "--knk-border-subtle", "--line-strong": "--knk-border-default", "--paper": "--knk-bg-page", "--paper-2": "--knk-bg-inset",
           "--paper-3": "--knk-bg-surface", "--knk-red": "--knk-brand", "--amber": "--knk-brand", "--amber-deep": "--knk-brand-hover",
           "--amber-glow": "--knk-brand-subtle", "--success": "--knk-success", "--warn": "--knk-warning", "--danger": "--knk-danger", "--info": "--knk-info",
           "--grad-amber": "--knk-brand", "--grad-knk-red": "--knk-brand"}
d2 = {k: v for k, v in OLDNAME.items() if not re.search(r"(?m)^\s*" + re.escape(k) + r":\s*var\(" + re.escape(v) + r"\);", tok)}
check("옛 이름 %d개가 새 이름을 가리킴(문서 3단계 표)" % len(OLDNAME), not d2, d2)
check("기준 값 묶음이 맨 위(Pretendard @font-face 보다 먼저)", tok.index("--knk-brand-red") < tok.index("font-family: 'Pretendard'"))
check("나눔스퀘어 @font-face 4개(300·400·700·800 · swap)", all(re.search(r"NanumSquare%s\.woff'\) format\('woff'\);\s*font-weight: %d;[^}]*font-display: swap" % (n, w), tok)
                                                     for n, w in (("L", 300), ("R", 400), ("B", 700), ("EB", 800))))
check("화면 글꼴(* · body · --font-family) = 나눔스퀘어 먼저", re.search(r"\* \{ font-family: 'NanumSquare', 'Pretendard'", tok) is not None
      and re.search(r"body \{ font-family: 'NanumSquare', 'Pretendard'", tok) is not None and "--font-family:     'NanumSquare', 'Pretendard'," in tok)
qv = rd("app/templates/_v5_partials/design_quiet_v3.html")
check("상단바·표·카드 색 --qv-* 11개 = var(--knk-*)", len(re.findall(r"(?m)^\s*--qv-[\w-]+: var\(--knk-[\w-]+\);", qv)) == 11)
th = rd("app/templates/_v5_partials/knk_theme.html")
base = th[th.index("html[data-kt] {"):th.index("}", th.index("html[data-kt] {"))]
check("테마 기본 배색이 --knk-* 를 덮지 않음(새 기준 값이 그대로 보임)", not re.search(r"--knk-[\w-]+\s*:", base))
check("흐린 글자 고침 묶음에 옛 회색·초록·호박 고정 값 없음", "--mute:#566275" not in th and "--success:#4d6e33" not in th and "--amber-deep:#8a5d1f" not in th)
soft = re.search(r'html\[data-kt="soft"\] \{([^}]*)\}', th).group(1)
check("부드럽게 = 바탕·옅은 칸·흐린 글자 한 단계(--knk-*-soft)", "--knk-bg-page:var(--knk-bg-page-soft)" in soft and "--knk-text-muted:var(--knk-text-muted-soft)" in soft and "brightness(.93)" in soft)


def _lum(h):
    h = h.lstrip("#"); v = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    v = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in v]
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]


def _cr(a, b, k=1.0):
    def sc(h):
        h = h.lstrip("#"); return "#" + "".join("%02X" % round(int(h[i:i + 2], 16) * k) for i in (0, 2, 4))
    x, y = _lum(sc(a)), _lum(sc(b))
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


mut, mut_s = CS._decl(ci, "--knk-text-muted"), CS._decl(rb, "--knk-text-muted-soft")
pg_s, sub_s = CS._decl(rb, "--knk-bg-page-soft"), CS._decl(rb, "--knk-bg-subtle-soft")
r1 = [round(_cr(mut, b), 2) for b in ("#FFFFFF", CS._decl(ci, "--knk-bg-page"), CS._decl(ci, "--knk-bg-inset"))]
r2 = [round(_cr(mut_s, b, 0.93), 2) for b in ("#FFFFFF", pg_s, sub_s)]
check("흐린 글자 명암 ≥4.5 — 밝게(흰·바탕·표 머리) %s" % r1, min(r1) >= 4.5)
check("부드럽게 흐린 글자 명암 ≥4.5 — 밝기 0.93(흰·바탕·옅은 칸) %s" % r2, min(r2) >= 4.5)
check("(대조) 부드럽게에 견본 흐린 글자(#6D6F71)를 쓰면 4.5 아래 — 그래서 -soft 를 둠", _cr("#6D6F71", pg_s, 0.93) < 4.5)
check("흐린 글자가 옅은 칸(--knk-bg-subtle) 위에서도 ≥4.5 (z203 실측 미달 62곳 고친 값)", _cr(mut, CS._decl(ci, "--knk-bg-subtle")) >= 4.5)
sty = rd("app/templates/_v5_partials/styles.html")
check("공용 머리: v5_tokens.css 를 배포마다 새로(APP_VERSION) · foundation·components 그대로", "/static/css/v5_tokens.css?v={{ APP_VERSION }}" in sty
      and "knk-foundation.css?v={{ APP_VERSION }}" in sty and "knk-components.css?v={{ APP_VERSION }}" in sty)
check("v5_tokens 가 foundation 보다 먼저 불림(foundation 엔 --knk-* 없음)", sty.index("v5_tokens.css") < sty.index("knk-foundation.css"))

print("§3 2단계 — 공용 모양 .k-*")
comp = rd("static/css/knk-components.css")
kb = comp[comp.rindex("/*", 0, comp.index("★ KNK 공용 모양 .k-*")):]
check(".k-* 묶음에 색 숫자 0(주석 뺌)", not CS.HEX_RE.findall(CS._strip_comments_keep_lines(kb)), CS.HEX_RE.findall(CS._strip_comments_keep_lines(kb))[:5])
for c in ("k-tri", "k-p3", "k-chain", "k-chain-item", "k-conn", "k-hero", "k-pattern-red", "k-pattern-white", "k-auto", "k-loading", "k-page", "k-card",
          "k-btn", "k-btn--primary", "k-btn--text", "k-btn--danger", "k-input", "k-field", "k-tabs", "k-tab", "k-badge", "k-table", "k-sheet", "k-band",
          "k-note", "k-stat", "k-list", "k-modal"):
    if "." + c + "{" not in kb and "." + c + " " not in kb and "." + c + "," not in kb and "." + c + ":" not in kb and "." + c + "." not in kb and "." + c + ">" not in kb:
        check("공용 모양 있음 ." + c, False)
check("공용 모양 28가지 있음", True)
check("전역 규칙(body·*·a) 안 옮김", not re.search(r"(?m)^(body|\*|a)\s*\{", kb))
check("화면 폭 상한(max-width·margin auto) 안 둠 — 시트여백 규정", "max-width:1600px" not in kb and "min-height:100vh" not in kb)
check("패턴 그림 = /static/img/brand/", kb.count("/static/img/brand/knk-pattern-tile_") == 4)

print("§4 5단계 검사기 — 지금 코드 통과 · 일부러 어긴 코드는 잡힘")
files = CS.collect(False)
with contextlib.redirect_stdout(io.StringIO()):
    b0 = CS.check_brand_tokens()
    hx_new, hx_old = CS.split_by_path(CS.check_direct_colors(files), CS.COLOR_BASE)
    lf, lh = CS.check_logo_files(files)
    lg_new, lg_old = CS.split_by_path(lh, CS.LOGO_BASE)
    ff = CS.check_font_files(files)
check("⑤-1 브랜드 값 일치: 지금 위반 0", b0 == [], b0[:3])
check("⑤-2 새 직접 색: 지금 새 위반 0 (면제 %d)" % hx_old, hx_new == [], [x[:2] for x in hx_new[:3]])
check("⑤-3 로고: 지금 위반 0 (면제 %d)" % lg_old, lf == [] and lg_new == [], (lf + lg_new)[:3])
check("⑤-4 글꼴 파일: 지금 위반 0", ff == [], ff[:3])


def mini_root():
    """검사에 필요한 것만 담은 임시 웍스 자리(templates 1 · css · img/brand · fonts)."""
    tmp = tempfile.mkdtemp(prefix="mut_z202_")
    for rel in ("static/css", "static/img/brand", "static/fonts/nanumsquare", "app/templates"):
        os.makedirs(os.path.join(tmp, *rel.split("/")))
    for f in ("v5_tokens.css", "knk-foundation.css", "knk-components.css"):
        shutil.copyfile(os.path.join(ROOT, "static", "css", f), os.path.join(tmp, "static", "css", f))
    for f in os.listdir(bdir):
        shutil.copyfile(os.path.join(bdir, f), os.path.join(tmp, "static", "img", "brand", f))
    for f in os.listdir(fdir):
        shutil.copyfile(os.path.join(fdir, f), os.path.join(tmp, "static", "fonts", "nanumsquare", f))
    return tmp


def edit(tmp, rel, old, new):
    p = os.path.join(tmp, *rel.split("/"))
    s = io.open(p, encoding="utf-8").read()
    assert s.count(old) >= 1, (rel, old)
    io.open(p, "w", encoding="utf-8", newline="").write(s.replace(old, new, 1))


def put(tmp, rel, body):
    p = os.path.join(tmp, *rel.split("/"))
    io.open(p, "w", encoding="utf-8", newline="").write(body)
    return p


# ⑤-1
t = mini_root()
try:
    with contextlib.redirect_stdout(io.StringIO()):
        ok0 = CS.check_brand_tokens(root=t, brand_path=BRAND)
    check("(임시 자리) 손대기 전 ⑤-1 통과", ok0 == [], ok0[:2])
    edit(t, "static/css/v5_tokens.css", "--knk-brand-red:      #AE2025;", "--knk-brand-red:      #AE2B30;")
    got = CS.check_brand_tokens(root=t, brand_path=BRAND)
    check("어김① 회사 빨강을 안내서 PDF 색(#AE2B30)으로 → ⑤-1 잡힘", any("--knk-brand-red" in m for _f, _l, m in got), got[:2])
finally:
    shutil.rmtree(t, ignore_errors=True)
t = mini_root()
try:
    edit(t, "static/css/v5_tokens.css", "--knk-brand:          var(--knk-brand-red);   /* = brand.json", "--knk-brand:          #C4320A;   /* = brand.json")
    got = CS.check_brand_tokens(root=t, brand_path=BRAND)
    check("어김② .knk-ci 의 --knk-brand 를 다른 빨강으로 → ⑤-1 잡힘", any(".knk-ci" in m for _f, _l, m in got), got[:2])
    put(t, "static/css/extra.css", ":root{ --knk-text-primary:#111111; }\n")
    put(t, "app/templates/x_brand.html", "<style>:root{--knk-brand-gray:#6D6F71}</style>\n")
    got = CS.check_brand_tokens(root=t, brand_path=BRAND)
    check("어김③ 다른 CSS 가 --knk-* 를 또 정함(정의 두 곳) → ⑤-1 잡힘", any("extra.css" in f and "한 곳" in m for f, _l, m in got), got[:3])
    check("어김④ 화면이 회사 회색을 다른 값(#6D6F71)으로 다시 적음 → ⑤-1 잡힘", any("x_brand.html" in f and "--knk-brand-gray" in m for f, _l, m in got), got[:3])
finally:
    shutil.rmtree(t, ignore_errors=True)
t = mini_root()
try:
    edit(t, "static/css/v5_tokens.css", ":root, .knk-ci {", ".knk-ci {")
    got = CS.check_brand_tokens(root=t, brand_path=BRAND)
    check("어김⑭ 새 기준 값을 다시 .knk-ci 안에만(3단계 되돌림) → ⑤-1 잡힘", any(":root 를 포함" in m for _f, _l, m in got), got[:2])
finally:
    shutil.rmtree(t, ignore_errors=True)
t = mini_root()
try:
    edit(t, "static/css/v5_tokens.css", "  --knk-brand-ink:      #414042;", "  --knk-brand-ink:      #414042;" + chr(10) + "  --knk-brand:          #A5282C;")
    got = CS.check_brand_tokens(root=t, brand_path=BRAND)
    check("어김⑮ 첫 :root 에 옛 웍스 빨강 #A5282C 를 남김 → ⑤-1 잡힘", any("옛 웍스 빨강" in m for _f, _l, m in got), got[:2])
finally:
    shutil.rmtree(t, ignore_errors=True)
# ⑤-2
t = mini_root()
try:
    home = os.path.join(ROOT, "app", "templates", "home.html")
    hp = put(t, "app/templates/home.html", io.open(home, encoding="utf-8").read() + '\n<div style="color:#123456;background:#abcdef">새 색</div>\n')
    nn = put(t, "app/templates/brand_new_screen.html", '<p style="color:#ae2025">새 화면</p><p style="color:var(--knk-brand)">이건 괜찮음</p>\n')
    allf = [hp if os.path.normcase(f) == os.path.normcase(home) else f for f in files] + [nn]
    hits = [(f.replace(t, ROOT), l, m) for f, l, m in CS.check_direct_colors(allf)]   # 임시 자리 파일도 웍스 같은 경로로 셈
    new, old = CS.split_by_path(hits, CS.COLOR_BASE, root=ROOT)
    check("어김⑤ 있던 화면(home.html)에 #색 2개 더함 → ⑤-2 새 위반 2", len([1 for f, _l, _m in new if f == hp.replace(t, ROOT)]) == 2, [(os.path.basename(f), m[:30]) for f, _l, m in new][:4])
    check("어김⑥ 새 화면에 #ae2025 직접 적음 → ⑤-2 새 위반 1 (var() 줄은 안 잡힘)", len([1 for f, _l, _m in new if f == nn.replace(t, ROOT)]) == 1)
    hits0 = CS.check_direct_colors([home])
    check("(대조) 원래 home.html 은 면제 안", CS.split_by_path(hits0, CS.COLOR_BASE)[0] == [])
    cm = put(t, "app/templates/cmt.html", "<style>/* #ffffff 는 주석 */</style>{# #000000 #}<!-- #ff0000 --><a href=\"#add\">x</a>&#123456;\n")
    check("(대조) 주석·href=\"#…\"·&#…; 는 안 셈", CS.check_direct_colors([cm]) == [], CS.check_direct_colors([cm]))
finally:
    shutil.rmtree(t, ignore_errors=True)
# ⑤-3
t = mini_root()
try:
    with contextlib.redirect_stdout(io.StringIO()):
        f0, h0 = CS.check_logo_files([], root=t)
    check("(임시 자리) 손대기 전 ⑤-3 통과", f0 == [] and h0 == [], (f0 + h0)[:2])
    lp = put(t, "app/templates/new_login.html",
             '<img src="/static/logo.png" alt="KNK 로고">\n<img src="/static/img/brand/knk-symbol_full.svg" alt="KNK 심볼">\n'
             '<b style="color:var(--knk-red);font-size:22px">KNK</b>\n<div style="background:url(/static/logo.svg)"></div>\n')
    f1, h1 = CS.check_logo_files([lp], root=t)
    check("어김⑦ 로고 <img> 를 /static/logo.png 로 → ⑤-3 잡힘 (2번 줄 brand 폴더 <img> 는 안 잡힘)", sum(1 for _f, _l, m in h1 if "/static/logo.png" in m) == 1
          and not any(l == 2 for _f, l, m in h1), [(l, m[:40]) for _f, l, m in h1])
    check("어김⑧ 「KNK」 를 빨간 글씨로 흉내 → ⑤-3 잡힘", any("흉내" in m for _f, _l, m in h1))
    check("어김⑨ 로고를 CSS url(/static/logo.svg) 로 → ⑤-3 잡힘", any("url(/static/logo.svg" in m for _f, _l, m in h1))
    with io.open(os.path.join(t, "static", "img", "brand", "knk-symbol_full.svg"), "a", encoding="utf-8") as fh:
        fh.write("<!-- 다시 그림 -->")
    put(t, "static/img/brand/my-logo.png", "x")
    f2, _h2 = CS.check_logo_files([], root=t)
    check("어김⑩ brand 폴더 로고 파일 내용을 바꿈 → ⑤-3 잡힘", any("knk-symbol_full.svg" in f and "다름" in m for f, _l, m in f2), f2[:2])
    check("어김⑪ 원본에 없는 그림을 brand 폴더에 → ⑤-3 잡힘", any("my-logo.png" in f for f, _l, _m in f2))
finally:
    shutil.rmtree(t, ignore_errors=True)
# ⑤-4
t = mini_root()
try:
    tp = os.path.join(t, "static", "css", "v5_tokens.css")
    check("(임시 자리) 손대기 전 ⑤-4 통과", CS.check_font_files([tp], root=t) == [])
    edit(t, "static/css/v5_tokens.css", "NanumSquareEB.woff", "NanumSquareXB.woff")
    got = CS.check_font_files([tp], root=t)
    check("어김⑫ @font-face 가 없는 파일(NanumSquareXB.woff)을 부름 → ⑤-4 잡힘", any("NanumSquareXB.woff" in m for _f, _l, m in got), got[:2])
    ex = put(t, "app/templates/font_ext.html", "<style>@font-face{font-family:X;src:url(https://hangeul.pstatic.net/x.woff)}</style>\n")
    got = CS.check_font_files([ex], root=t)
    check("어김⑬ @font-face 가 바깥 주소를 부름 → ⑤-4 잡힘", any("바깥 주소" in m for _f, _l, m in got), got[:2])
    lc = put(t, "app/templates/font_local.html", "<style>@font-face{font-family:Y;src:local('Pretendard')}</style>\n")
    check("(대조) local() 만 쓰는 @font-face 는 통과", CS.check_font_files([lc], root=t) == [])
finally:
    shutil.rmtree(t, ignore_errors=True)
# brand.json 없음
got = CS.check_brand_tokens(brand_path=os.path.join(tempfile.gettempdir(), "no_such_brand_z202.json"))
check("brand.json 을 못 읽으면 통과시키지 않음(실패)", len(got) == 1 and "brand.json" in got[0][2])

print("§5 6단계 — 살아 있는 견본 화면")
kit = rd("app/templates/admin_design_kit.html")
check("본문을 .knk-ci 로 감쌈(새 기준 값)", 'class="knk-ci k-page dk"' in kit)
check("색 칸은 var() · 값은 화면에서 읽음(getComputedStyle)", "getComputedStyle" in kit and "getPropertyValue" in kit)
check("화면 안 「✕ 닫기」(공용 knk_close_btn · 돌아갈 곳 /admin)", "{% set close_fallback = '/admin' %}{% include \"_v5_partials/knk_close_btn.html\" %}" in kit)
check("확인 창 안 「✕ 닫기」 + Esc", "✕ 닫기</button>" in kit and "e.key === 'Escape'" in kit)
imgs = re.findall(r'<img[^>]*src="([^"]+)"', kit)
check("로고 그림 %d개 모두 /static/img/brand/" % len(imgs), imgs and all(s.startswith("/static/img/brand/") for s in imgs))
check("견본 화면 색 숫자 0", CS.check_direct_colors([os.path.join(ROOT, "app", "templates", "admin_design_kit.html")]) == [])
for c in ("k-tri", "k-p3", "k-chain", "k-conn", "k-hero", "k-pattern-red", "k-pattern-white", "k-auto", "k-loading", "k-btn--primary", "k-btn--text",
          "k-btn--danger", "k-input", "k-tabs", "k-badge", "k-table", "k-sheet", "k-band", "k-note", "k-stat", "k-list", "k-modal"):
    if c not in kit:
        check("견본에 " + c, False)
check("견본에 공용 모양 22가지 모두 그려짐", True)
check("글꼴이 실제로 그려지는지 확인(document.fonts.check)", "document.fonts.check" in kit)

print("")
print("결과: %d개 중 실패 %d" % (CNT, len(FAIL)))
for f in FAIL:
    print("   ❌", f)
sys.exit(1 if FAIL else 0)
