# -*- coding: utf-8 -*-
"""z1191z185 시험 — 웍스 흐린 글자 고침(대표 11-27 · 운영 스킬 knk-text-contrast · 이음 v1039·v1040 과 같은 방법)
  §1 고침 묶음이 공용 테마 조각(knk_theme.html)에 한 번 · 메일 화면(세션 15) 제외 표시(data-mt · data-ktm)
  §2 고친 색 쌍이 세 테마(밝게 · 부드럽게 brightness .93 · 어둡게 invert .9 + hue-rotate 180) 모두 4.5 : 1 이상
     (테마 필터 계산 = 시험 서버 실제 화면 픽셀과 같음을 측정 도구로 확인한 식)
  §3 나쁜 예: 고친 값을 원래 값으로 되돌린 판은 이 검사에 걸린다
  §4 바탕·면 색 이름(--knk-bg-* · --qv-surface* · --paper* · --line*)은 고침 묶음에서 건드리지 않음
"""
import math, os, re, sys
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
P = os.path.join(ROOT, "app", "templates", "_v5_partials", "knk_theme.html")
SRC = open(P, encoding="utf-8").read()
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
    return [min(255, round(x * 0.93)) for x in c]


def dark(c):
    v = [0.9 - 0.8 * x / 255.0 for x in c]
    a = math.radians(180); co, si = math.cos(a), math.sin(a)
    m = [[0.213 + co * 0.787 - si * 0.213, 0.715 - co * 0.715 - si * 0.715, 0.072 - co * 0.072 + si * 0.928],
         [0.213 - co * 0.213 + si * 0.143, 0.715 + co * 0.285 + si * 0.140, 0.072 - co * 0.072 - si * 0.283],
         [0.213 - co * 0.213 - si * 0.787, 0.715 - co * 0.715 + si * 0.715, 0.072 + co * 0.928 + si * 0.072]]
    return [round(min(1, max(0, sum(m[i][j] * v[j] for j in range(3)))) * 255) for i in range(3)]


def three(fg, bg):
    f, b = hx(fg), hx(bg)
    return min(cr(f, b), cr(soft(f), soft(b)), cr(dark(f), dark(b)))


m = re.search(r'<style id="knk-cfix-z185">(.*?)</style>', SRC, re.S)
print("§1 고침 묶음 자리")
ck(SRC.count('id="knk-cfix-z185"') == 1, "고침 묶음이 knk_theme.html 에 한 번")
BLK = m.group(1) if m else ""
rules = re.sub(r"/\*.*?\*/", "", BLK, flags=re.S)
sels = [s for s in re.findall(r"([^{}]+)\{", rules)]
bad_sel = [s.strip()[:60] for s in sels for part in s.split(",") if part.strip() and "html[data-kt]:not([data-mt]):not([data-ktm])" not in part]
ck(sels and not bad_sel, "모든 규칙이 메일 화면 제외 선택자(:not([data-mt]):not([data-ktm])) 안", bad_sel[:3])
ck("data-ktm" in SRC and "/^\\/(mail(\\/|$)|admin\\/mail)/" in SRC, "메일 주소(/mail · /admin/mail)에서 data-ktm 붙이는 스크립트")

print("§2 고친 색 쌍 — 세 테마 모두 4.5 이상")


def val(name):
    mm = re.search(r"--%s:\s*(#[0-9a-fA-F]{6})" % re.escape(name), rules)
    return mm.group(1) if mm else None


def color_of(sel_piece):
    mm = re.search(re.escape(sel_piece) + r"[^{]*\{[^}]*?(?<!-)color:\s*(#[0-9a-fA-F]{6})", rules)
    return mm.group(1) if mm else None


PAIRS = [   # (설명, 글자색 얻기, 바탕들)
    ("흐린 회색 색 이름 --qv-ink-3 (흰 칸 · 바탕 · 부드럽게 바탕)", val("qv-ink-3"), ["#ffffff", "#f3f4f6", "#e8ebef", "#f6f8fb"]),
    ("--mute", val("mute"), ["#ffffff", "#f3f4f6", "#e8ebef"]),
    ("--g-ink3(한눈에 보기)", val("g-ink3"), ["#ffffff", "#f3f4f6"]),
    ("초록 상태 --success 글자", val("success"), ["#ffffff", "#f3f4f6"]),
    ("흰 글자 on --success 바탕(출하 알약)", "#ffffff", [val("success") or "#7a9b5c"]),
    ("호박 --amber-deep 글자", val("amber-deep"), ["#ffffff", "#f3f4f6", "#f9fafb"]),
    ("입력 안내 글자(placeholder)", (re.search(r"::placeholder\s*\{\s*color:\s*(#[0-9a-fA-F]{6})", rules) or [None, None])[1], ["#ffffff", "#f3f4f6", "#e8ebef"]),
    ("화면에 적힌 #94a3b8 → 고친 회색", color_of(".kpi-slim .c .val .u"), ["#ffffff", "#f3f4f6", "#f9fafb"]),
    ("제작요청서 진행중 알약", color_of(".pc-st-prog"), ["#fef3c7"]),
    ("출하·오늘 납품 초록 알약", color_of(".pc-st-done"), ["#dcfce7", "#e7f6ec"]),
    ("달력 일요일·공휴일", color_of(".cal-day .d.sun"), ["#fafaf7", "#ffffff", "#f3f4f6"]),
    ("사업부 T 알약", color_of(".so-list-b .biz-T"), ["#fff1ec"]),
    ("기간 글자(초록)", color_of(".period-lab"), ["#ffffff"]),
]
for nm, fg, bgs in PAIRS:
    if not fg:
        ck(False, nm, "값을 못 찾음"); continue
    worst = min(three(fg, b) for b in bgs)
    ck(worst >= 4.5, "%s %s → 최저 %.2f" % (nm, fg, worst))
ck(bool(re.search(r"\.so-pill \.en\s*\{\s*opacity:\s*1", rules)), "상태 알약 영어 줄 투명도 1(원래 .55)")
ck(bool(re.search(r"\.card\.hero \.card-value\s*\{\s*color:var\(--qv-ink\)", rules)), "업무현황 첫 카드 숫자 = 본문 글자색(흰 칸 흰 글자 없앰)")

print("§3 나쁜 예 — 원래 값으로 되돌리면 걸리는지")
for nm, fg, bgs in (("--qv-ink-3 원래 #64748b · 부드럽게 바탕", "#64748b", ["#e8ebef"]), ("#94a3b8", "#94a3b8", ["#ffffff"]),
                    ("--success 원래 #7a9b5c", "#7a9b5c", ["#ffffff"]), ("--amber-deep 원래 #b8843a", "#b8843a", ["#ffffff"]),
                    ("placeholder 원래 #c3bdaf", "#c3bdaf", ["#ffffff"]), ("진행중 원래 #b45309", "#b45309", ["#fef3c7"])):
    ck(min(three(fg, b) for b in bgs) < 4.5, "나쁜 예 %s 은 걸림" % nm)

print("§4 바탕·면 색 이름은 그대로")
touched = re.findall(r"(--(?:knk-bg|qv-surface|paper|line|qv-line|knk-border|ink|qv-ink|text)[\w-]*)\s*:", rules)
touched = [t for t in touched if t not in ("--qv-ink-3",)]
ck(not touched, "바탕·면·테두리·본문 글자 색 이름을 다시 정하지 않음", touched)

print("\n결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
