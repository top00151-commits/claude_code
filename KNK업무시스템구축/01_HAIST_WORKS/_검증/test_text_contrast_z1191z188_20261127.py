# -*- coding: utf-8 -*-
"""z1191z188 시험 — 웍스 흐린 글자 고침 2차(대표 11-27 「진행해」 · 운영 스킬 knk-text-contrast)
  1차(z185)는 23 장면만 쟀다. 2차는 그 밖 웍스 화면 185 장면 × 폭 6 × 테마 3 을 시험 서버에서 새로 재고 고쳤다.
  §1 고침 묶음(knk-cfix-z188)이 knk_theme.html 에 한 번 · 1차 묶음 바로 뒤 · 모든 규칙이 메일 화면 제외 선택자 안
  §2 고친 색 쌍이 세 테마(밝게 · 부드럽게 brightness .93 · 어둡게 invert .9 + hue-rotate 180) 모두 4.5 : 1 이상
  §3 나쁜 예: 원래 값으로 되돌리면 이 검사에 걸린다(묶음을 원래 값으로 바꾼 판을 실제로 돌려 확인)
  §4 바탕·면·테두리·본문 글자 색 이름은 건드리지 않음
  §5 직접 적힌 글자색 규칙은 「맨 앞 color:」·「;color:」만(border-color 에 걸리지 않게) · 제작요청서 양식(#z48Paper) 제외
  §6 1차 부작용 바로잡기(초록 바탕 단추 흰 글자)
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
SCOPE = "html[data-kt]:not([data-mt]):not([data-ktm])"


def lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def lum(c):
    return 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2])


def cr(a, b):
    l1, l2 = lum(a), lum(b)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def hx(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


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


def run(src, quiet=False):
    """검사 한 판 — (통과, 실패, 실패 목록)"""
    res = {"ok": 0, "fail": 0, "msgs": []}

    def ck(c, label, extra=""):
        if c:
            res["ok"] += 1
            if not quiet: print("  ✅", label)
        else:
            res["fail"] += 1; res["msgs"].append(label)
            if not quiet: print("  ❌", label, extra)

    m = re.search(r'<style id="knk-cfix-z188">(.*?)</style>', src, re.S)
    if not quiet: print("§1 고침 묶음 자리")
    ck(src.count('id="knk-cfix-z188"') == 1, "고침 묶음이 knk_theme.html 에 한 번")
    i185 = src.find('<style id="knk-cfix-z185">'); i188 = src.find('<style id="knk-cfix-z188">')
    e185 = src.find("</style>", i185) + len("</style>") if i185 >= 0 else -1
    ck(0 <= i185 < i188 and src[e185:i188].strip() == "", "1차 묶음(z185) 바로 뒤에 붙음")
    blk = m.group(1) if m else ""
    rules = re.sub(r"/\*.*?\*/", "", blk, flags=re.S)
    sels = re.findall(r"([^{}]+)\{", rules)
    bad_sel = [p.strip()[:60] for s in sels for p in s.split(",") if p.strip() and not p.strip().startswith(SCOPE)]
    ck(bool(sels) and not bad_sel, "모든 규칙이 메일 화면 제외 선택자(%s) 안" % SCOPE, bad_sel[:3])

    def tok(name):
        mm = re.search(r"--%s:\s*(#[0-9a-fA-F]{3,6})" % re.escape(name), rules)
        return mm.group(1) if mm else None

    def col(piece, prop="color"):
        mm = re.search(re.escape(piece) + r"[^{]*\{[^}]*?(?<![-\w])%s:\s*(#[0-9a-fA-F]{6})" % prop, rules)
        return mm.group(1) if mm else None

    def inl_col(c):
        mm = re.search(r'\[style\^="color:%s" i\][^{]*\{\s*color:\s*(#[0-9a-fA-F]{6})' % re.escape(c), rules)
        return mm.group(1) if mm else None

    grad = re.search(r"--grad-amber:\s*linear-gradient\([^,]+,\s*(#[0-9a-fA-F]{6})[^,]*,\s*(#[0-9a-fA-F]{6})", rules)
    if not quiet: print("§2 고친 색 쌍 — 세 테마 모두 4.5 이상")
    LIGHT = ["#ffffff", "#f3f4f6", "#eef0f4", "#f7f8fa", "#e8ebef", "#fef9c3", "#eff6ff"]
    PAIRS = [
        ("흐린 글자 색 이름 --pq-ink-4(자재·환율·품질 화면 보조 글)", tok("pq-ink-4"), LIGHT),
        ("--pq-ink-3", tok("pq-ink-3"), LIGHT),
        ("--qv-ink-4", tok("qv-ink-4"), LIGHT),
        ("--ink-4", tok("ink-4"), LIGHT),
        ("--mute-2", tok("mute-2"), LIGHT),
        ("경고 글자 --pq-warn on 옅은 노랑", tok("pq-warn"), ["#fef3c7", "#ffffff"]),
        ("KPI 단위·보조(.knk-kpi__sub)", col(".knk-kpi__sub"), ["#ffffff", "#f7f8fa"]),
        ("화면 안내 글(.op-intro 등)", col(".op-intro"), ["#f3f4f6", "#ffffff", "#f1f5f9"]),
        ("직접 적힌 #94a3b8 → ", inl_col("#94a3b8"), LIGHT),
        ("직접 적힌 #777 → ", inl_col("#777"), LIGHT),
        ("금색 보조 글(.ai-hint · 영업 기회 표 머리)", col(".ai-hint"), ["#ffffff", "#faf7ef", "#fef8ec", "#f3f4f6"]),
        ("직접 적힌 금색 #8a7842 → ", inl_col("#8a7842"), ["#ffffff", "#f3f4f6", "#fdf3e3"]),
        ("직접 적힌 빨강 #dc2626 → ", inl_col("#dc2626"), ["#ffffff", "#f3f4f6", "#ede6dc"]),
        ("직접 적힌 파랑 #2563eb → ", inl_col("#2563eb"), ["#ffffff", "#f3f4f6"]),
        ("직접 적힌 초록 #16a34a → ", inl_col("#16a34a"), ["#ffffff", "#f3f4f6"]),
        ("호박 제목(.sr-sec-h.carry)", col(".sr-sec-h.carry"), ["#ffffff", "#f3f4f6", "#fef3c7"]),
        ("달력 일요일", col(".cal-head .dow.sun"), ["#ffffff", "#f1f3f6"]),
        ("흰 글자 on 주황 그라데이션 두 끝(--grad-amber)", "#ffffff", list(grad.groups()) if grad else ["#d4923b", "#c2693a"]),
    ]
    for nm, fg, bgs in PAIRS:
        if not fg or not all(bgs):
            ck(False, nm, "값을 못 찾음"); continue
        worst = min(three(fg, b) for b in bgs)
        ck(worst >= 4.5, "%s %s → 최저 %.2f" % (nm, fg, worst))
    # 단추 바탕 고침 중 밝게·부드럽게 전용(어둡게는 원래 바탕이 이미 4.5 넘음 → 어둡게에서 더 나빠지지 않게 뺌)
    ND = 'html[data-kt]:not([data-mt]):not([data-ktm]):not([data-kt="dark"])'
    LIGHT2 = [("엑셀 단추·완료 표시 초록", ".lg-xls", "#16a34a"), ("변경 표시 호박", ".mk.chg", "#d97706"),
              ("빨강→주황 단추 끝 색(--amber-burnt)", "--amber-burnt", "#c2693a")]
    for nm, key, orig in LIGHT2:
        if key.startswith("--"):
            mm = re.search(re.escape(ND) + r"[^{]*\{[^}]*" + re.escape(key) + r":\s*(#[0-9a-fA-F]{6})", rules)
        else:
            mm = re.search(re.escape(ND) + r" " + re.escape(key) + r"[^{]*\{[^}]*?background:\s*(#[0-9a-fA-F]{6})", rules)
        if not mm:
            ck(False, "흰 글자 on %s — 밝게·부드럽게 전용 규칙" % nm, "값을 못 찾음"); continue
        f, b = hx("#ffffff"), hx(mm.group(1))
        w2 = min(cr(f, b), cr(soft(f), soft(b)))
        d0 = cr(dark(f), dark(hx(orig)))
        ck(w2 >= 4.5 and d0 >= 4.5, "흰 글자 on %s %s → 밝게·부드럽게 최저 %.2f · 어둡게 원래 %s %.2f" % (nm, mm.group(1), w2, orig, d0))
    ck(bool(re.search(r'\[style\^="background:#ffff00" i\][^{]*\{\s*color:#1f2937', rules)), "노랑 형광 강조 안 글자 = 본문 글자색")
    for cls in (".as-tab .cnt", ".op-chip .n", ".rnd-chip .n", ".z57-next-sub"):
        ck(bool(re.search(re.escape(cls) + r"[^{]*\{\s*opacity:\s*1", rules)), "흐리게 둔 숫자 %s 투명도 1" % cls)

    if not quiet: print("§4 바탕·면·테두리·본문 글자 색 이름은 그대로")
    touched = re.findall(r"(--(?:knk-bg|qv-surface|pq-surface|paper|line|qv-line|pq-line|knk-border|ink|qv-ink|pq-ink|text|bg|surface|border)(?:-[\w-]*)?)\s*:", rules)
    touched = [t for t in touched if t not in ("--pq-ink-3", "--pq-ink-4", "--qv-ink-4", "--ink-4")]
    ck(not touched, "바탕·면·테두리·본문 글자 색 이름을 다시 정하지 않음", touched)

    if not quiet: print("§5 직접 적힌 글자색 규칙 모양")
    loose = re.findall(r'\[style\*="color:', rules)
    ck(not loose, "「style 안 아무 데나 color:」 규칙 없음(border-color 에 걸리지 않게)", len(loose))
    inl = re.findall(r'\[style[\^*]="[; ]*color:[^\]]*\][^,{]*', rules)
    ck(inl and all(":not(#z48Paper *)" in x for x in inl), "직접 적힌 글자색 규칙은 모두 제작요청서 양식(#z48Paper) 제외 (%d개)" % len(inl))

    if not quiet: print("§6 1차 부작용 바로잡기")
    ck(bool(re.search(r'\[style\*="background:#15803d" i\]\[style\*="border-color:#15803d" i\]\s*\{\s*color:#fff', rules)), "초록 바탕 단추(border-color:#15803d) 글자 = 흰색")
    return res


r = run(SRC)
print("§3 나쁜 예 — 묶음 값을 원래 값으로 되돌린 판은 걸려야 함")
BAD = [("--pq-ink-4:#566275", "--pq-ink-4:#94a3b8"), ("--grad-amber:linear-gradient(135deg, #a85a1d 0%, #9a4f1c 100%)", "--grad-amber:linear-gradient(135deg, #d4923b 0%, #c2693a 100%)"),
       ("--amber-burnt:#9a4f1c", "--amber-burnt:#c2693a"), ("{ color:#6e5f2f; }", "{ color:#8a7842; }"), ("--pq-warn:#92400e", "--pq-warn:#b45309")]
nb_ok = nb_fail = 0
for good, bad in BAD:
    if good not in SRC:
        nb_fail += 1; print("  ❌ 나쁜 예 만들 자리 없음:", good); continue
    rb = run(SRC.replace(good, bad, 1), quiet=True)
    if rb["fail"] > 0:
        nb_ok += 1; print("  ✅ 나쁜 예 %s → 걸림(%s)" % (bad[:50], rb["msgs"][0][:40]))
    else:
        nb_fail += 1; print("  ❌ 나쁜 예 %s 가 안 걸림" % bad[:50])
rb = run(SRC.replace('[style^="color:#94a3b8" i]', '[style*="color:#94a3b8" i]', 1), quiet=True)
if rb["fail"]:
    nb_ok += 1; print("  ✅ 나쁜 예 border-color 에도 걸리는 모양 → 걸림")
else:
    nb_fail += 1; print("  ❌ 나쁜 예 border-color 모양이 안 걸림")
OK, FAIL = r["ok"] + nb_ok, r["fail"] + nb_fail
print("\n결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
