# -*- coding: utf-8 -*-
"""z1210 검사기 — 회의록·음성 메모 흐린 글자 고침(대표 11-27 · 스킬 knk-text-contrast)
사용: py q210_contrast_check.py <나무 폴더(app_base · app_new 가 있는 곳)>
  §1 새 판(app_new): 「z1210 흐린 글자」 묶음이 세 파일에 한 번씩 · 고친 색이 기준을 넘음(테마 3가지 · 한눈에 보기는 테마 밖이라 밝게만)
  §2 바뀐 파일은 대상 화면 파일뿐 · 바탕·면·테두리 색 이름은 다시 정하지 않음 · 공용 테마(knk_theme.html)는 그대로
  §3 나쁜 예: 바탕 판(app_base)에 같은 검사를 돌리면 실제로 걸린다(고친 값이 빠지면 걸리는지)
마지막 줄: 결과: 통과 N · 실패 N   (실패가 있으면 종료 코드 1)
"""
import filecmp
import math
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
NEW = os.environ.get("Q210_NEW", "app_new")   # 나쁜 예 돌려 보기: Q210_NEW=app_base → 실패해야 맞음
OK = FAIL = 0


def ck(c, label, extra=""):
    global OK, FAIL
    if c:
        OK += 1; print("  ✅", label)
    else:
        FAIL += 1; print("  ❌", label, extra)


def lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def lum(c):
    return 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2])


def cr(a, b):
    l1, l2 = lum(a), lum(b)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def hx(h):
    h = h.lstrip("#"); return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def soft(c):
    return [min(255, x * 0.93) for x in c]


def dark(c):        # 웍스 「어둡게」 = invert(.9) hue-rotate(180deg) (세션 01 z185 검사기와 같은 식 · 실제 화면 픽셀로 맞춰 본 식)
    v = [0.9 - 0.8 * x / 255.0 for x in c]
    a = math.radians(180); co, si = math.cos(a), math.sin(a)
    m = [[0.213 + co * 0.787 - si * 0.213, 0.715 - co * 0.715 - si * 0.715, 0.072 - co * 0.072 + si * 0.928],
         [0.213 - co * 0.213 + si * 0.143, 0.715 + co * 0.285 + si * 0.140, 0.072 - co * 0.072 - si * 0.283],
         [0.213 - co * 0.213 - si * 0.787, 0.715 - co * 0.715 + si * 0.715, 0.072 + co * 0.928 + si * 0.072]]
    return [min(1, max(0, sum(m[i][j] * v[j] for j in range(3)))) * 255 for i in range(3)]


def worst(fg, bgs, themes=("clear", "soft", "dark")):
    f = hx(fg); r = 99
    for b in bgs:
        b = hx(b)
        if "clear" in themes: r = min(r, cr(f, b))
        if "soft" in themes: r = min(r, cr(soft(f), soft(b)))
        if "dark" in themes: r = min(r, cr(dark(f), dark(b)))
    return r


def read(tree, fn):
    p = os.path.join(ROOT, tree, "app", "templates", fn)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


def styles(src):
    return "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", src, re.S))


def last_color(css, sel, prop="color"):
    """선택자 sel 이 든 규칙들 가운데 마지막(뒤가 이김) 값."""
    val = None
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for sels, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        parts = [s.strip() for s in sels.split(",")]
        if sel in parts:
            m = re.search(r"(?<![-\w])" + re.escape(prop) + r"\s*:\s*(#[0-9a-fA-F]{6}|var\(--[\w-]+\))", body)
            if m:
                val = m.group(1)
    return val


def resolve(css, v):
    if v and v.startswith("var("):
        name = v[4:-1]
        m = None
        for m in re.finditer(re.escape(name) + r"\s*:\s*(#[0-9a-fA-F]{6})", css):
            pass
        return m.group(1) if m else None
    return v


# (파일, 선택자, 속성, 바탕들, 테마들, 설명)
CHECKS = [
    ("meeting_viz.html", ".sub", "color", ["#ffffff", "#f6f7f9"], ("clear",), "한눈에 보기 날짜 줄(.sub)"),
    ("meeting_viz.html", ".card h2 small", "color", ["#ffffff"], ("clear",), "한눈에 보기 카드 제목 옆 보조 글"),
    ("meeting_viz.html", ".loop", "color", ["#ffffff", "#e8f1fb"], ("clear",), "한눈에 보기 되돌아오는 흐름 글(.loop)"),
    ("meeting_viz.html", ".foot", "color", ["#ffffff", "#f6f7f9"], ("clear",), "한눈에 보기 맨 아래 안내(.foot)"),
    ("meeting_viz.html", ".step .w", "color", ["#ffffff", "#e8f1fb", "#e9f7ee", "#f2ecfc", "#fff6dd"], ("clear",), "단계 안 ⚠ 경고 글(.step .w)"),
    ("meeting_viz.html", ".tg-und", "color", ["#ffffff", "#e8f1fb", "#e9f7ee", "#fff6dd"], ("clear",), "[미결] 표시 글"),
    ("meeting_viz.html", ".tg-chk", "color", ["#ffffff", "#e8f1fb", "#e9f7ee", "#fff6dd"], ("clear",), "[확인 필요] 표시 글"),
    ("meeting_form.html", ".ri-ai", "color", ["#eaf1fe"], ("clear", "soft", "dark"), "결정·할 일 「빅터AI」 표시(세 테마)"),
]
CARD = ("voice_note_form.html", ".vni-card .vc-body", "--qv-ink-3", ["#ffffff"], 3.0, "🖼 이미지 카드 목록 점(• –) — 글자 아닌 표시 3 : 1")


def run_checks(tree, expect_pass=True):
    res = []
    for fn, sel, prop, bgs, th, lab in CHECKS:
        css = styles(read(tree, fn))
        v = resolve(css, last_color(css, sel, prop))
        r = worst(v, bgs, th) if v else 0
        res.append((lab, v, r, r >= 4.5))
    fn, sel, prop, bgs, need, lab = CARD
    css = styles(read(tree, fn))
    v = last_color(css, sel, prop)
    r = worst(v, bgs, ("clear",)) if v else 0
    res.append((lab, v, r, r >= need))
    return res


print("§1 새 판(%s) — 고친 색이 기준을 넘음" % NEW)
for fn in ("meeting_viz.html", "meeting_form.html", "voice_note_form.html"):
    ck(read(NEW, fn).count("z1210 흐린 글자") == 1, "%s 에 「z1210 흐린 글자」 묶음 한 번" % fn)
for lab, v, r, ok in run_checks(NEW):
    ck(ok, "%s %s → 최저 %.2f" % (lab, v, r))

print("§2 바뀐 파일 범위 · 바탕 색 이름 그대로")
TARGET = {"meetings.html", "meeting_form.html", "meeting_doc.html", "meeting_viz.html", "voice_notes.html", "voice_note_form.html",
          "_v5_partials/knk_md_lite.html", "_v5_partials/knk_line_edit.html", "_v5_partials/knk_ai_busy.html"}
changed = []
for sub in ("app",):
    for dp, dn, fns in os.walk(os.path.join(ROOT, NEW, sub)):
        dn[:] = [d for d in dn if d not in ("__pycache__",)]
        for f in fns:
            if f.endswith((".pyc", ".tmp")):
                continue
            pn = os.path.join(dp, f)
            rel = os.path.relpath(pn, os.path.join(ROOT, NEW))
            pb = os.path.join(ROOT, "app_base", rel)
            if not os.path.exists(pb) or not filecmp.cmp(pn, pb, shallow=False):
                changed.append(rel.replace("\\", "/"))
bad = [c for c in changed if c.replace("app/templates/", "") not in TARGET]
ck(changed and not bad, "바뀐 파일 = 대상 화면 파일만 (%s)" % ", ".join(changed), bad)
ck(filecmp.cmp(os.path.join(ROOT, NEW + "/app/templates/_v5_partials/knk_theme.html"),
               os.path.join(ROOT, "app_base/app/templates/_v5_partials/knk_theme.html"), shallow=False), "공용 테마 knk_theme.html 그대로(세션 01 구역)")
blocks = ""
for fn in ("meeting_viz.html", "meeting_form.html", "voice_note_form.html"):
    s = read(NEW, fn)
    i = s.find("z1210 흐린 글자")
    blocks += s[i:s.find("</style>", i)] if i >= 0 else ""
blocks_nc = re.sub(r"/\*.*?\*/", "", blocks, flags=re.S)
touched = re.findall(r"(--(?:knk-bg|qv-surface|paper|line|qv-line|knk-border|bg|card|ink|ink2|ink3|red|blue|amber|green|violet)[\w-]*)\s*:", blocks_nc)
ck(not touched, "고침 묶음이 바탕·면·테두리·화면 색 이름을 다시 정하지 않음", touched)
ck(not re.search(r"background|border", blocks_nc), "고침 묶음에 바탕·테두리 속성 없음")

print("§3 나쁜 예 — 바탕 판(app_base, 고치기 전)은 걸려야 한다")
base = run_checks("app_base")
nbad = [x for x in base if not x[3]]
for lab, v, r, ok in base:
    print("     바탕 판 %s %s → %.2f %s" % (lab, v, r, "통과" if ok else "걸림"))
ck(len(nbad) >= 6, "바탕 판에서 걸린 검사 %d개(고친 값이 빠지면 걸림)" % len(nbad))
for fn in ("meeting_viz.html", "meeting_form.html", "voice_note_form.html"):
    ck(read("app_base", fn).count("z1210 흐린 글자") == 0, "바탕 판 %s 에는 묶음 없음(=§1 첫 검사가 바탕 판에서 걸림)" % fn)

print("\n결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
