# -*- coding: utf-8 -*-
"""z1191z189 시험 — 웍스 흐린 글자 고침 3차: 테마(knk_theme.html)를 안 쓰는 화면(대표 11-27 「테마 안 쓰는 화면 18곳도 고쳐줘」)
  이 화면들은 테마가 바뀌지 않으므로 「보이는 모양(밝게)」과 「인쇄(흰 종이)」로 잰다. 세션 05 화면(부품·발주 QR 인쇄)은 고치지 않음.
  §1 인쇄 서류(수출 인보이스 · 패킹 · 출고 QR) — 안내·보조 글자 흐린 회색이 없고 고친 값이 종이·옅은 칸에서 4.5 이상
  §2 앱 설치 · 사용 가이드 — 고친 값 4.5 이상 · 가이드 인쇄 때 표 머리·흰 글자 단추가 흰 종이 + 본문색
  §3 관리 점검 화면(납기 확인 · 소모품 매출 점검 · 관리번호 원본) — main.py 그 함수 안 흐린 회색(#777 · #888) 없음
  §4 나쁜 예: 원래 값으로 되돌리면 걸림
"""
import os, re, sys
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TP = os.path.join(ROOT, "app", "templates")


def rd(p):
    return open(p, encoding="utf-8").read()


def lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def cr(a, b):
    la = 0.2126 * lin(a[0]) + 0.7152 * lin(a[1]) + 0.0722 * lin(a[2]); lb = 0.2126 * lin(b[0]) + 0.7152 * lin(b[1]) + 0.0722 * lin(b[2])
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def hx(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def worst(fg, bgs):
    return min(cr(hx(fg), hx(b)) for b in bgs)


def check(src):
    """src = {이름: 글} — (통과, 실패, 실패 목록)"""
    r = {"ok": 0, "fail": 0, "msgs": []}

    def ck(c, label, extra=""):
        if c:
            r["ok"] += 1
        else:
            r["fail"] += 1; r["msgs"].append(label + " " + str(extra))

    PAPER = ["#ffffff", "#f7f8fa"]
    for f in ("export_prep_invoice_print.html", "export_prep_packing_print.html"):
        s = src[f]
        m = re.search(r"\.exporter-block \.role \{[^}]*?color:\s*(#[0-9a-fA-F]{3,6})", s)
        ck(m and worst(m.group(1), PAPER) >= 4.5, "%s 수출자 역할 글 4.5 이상" % f, m and m.group(1))
        m = re.search(r"font-size:8pt; color:\s*(#[0-9a-fA-F]{3,6}); text-align:center;", s)
        ck(m and worst(m.group(1), PAPER) >= 4.5, "%s 바닥 글(만든 곳·시각) 4.5 이상" % f, m and m.group(1))
        ck(not re.search(r"color:\s*#94a3b8", s, re.I), "%s 글자색 #94a3b8 없음" % f)
    s = src["export_ship_qr_print.html"]
    ck(not re.search(r"(?<![-\w])color:\s*#94a3b8", s, re.I), "출고 QR 인쇄 글자색 #94a3b8 없음")
    s = src["app_install_z174.html"]
    m = re.search(r"\.ai-top p \{[^}]*?color:\s*(#[0-9a-fA-F]{3,6})", s)
    ck(m and worst(m.group(1), ["#ffffff", "#f6f5f2"]) >= 4.5, "앱 설치 머리 안내 글 4.5 이상", m and m.group(1))
    m = re.search(r"\.ai-flow li \{[^}]*?(?<![-\w])color:\s*(#[0-9a-fA-F]{3,6})", s)
    ck(m and worst(m.group(1), ["#ffffff"]) >= 4.5, "앱 설치 단계(아직 안 한 단계) 4.5 이상", m and m.group(1))
    s = src["guide.html"]
    m = re.search(r"input::placeholder\{\s*color:var\(--(ink-\d)\)", s)
    tok = m and re.search(r"--%s:\s*rgba\(10,10,10,\s*([.\d]+)\)" % m.group(1), s)
    if tok:
        a = float(tok.group(1)); bg = hx("#fafaf7"); fg = [round(10 * a + c * (1 - a)) for c in bg]
        ck(cr(fg, bg) >= 4.5, "가이드 찾기 칸 안내 글자 4.5 이상", "%.2f" % cr(fg, bg))
    else:
        ck(False, "가이드 찾기 칸 안내 글자 값을 못 찾음")
    pm = re.search(r"@media print\{(.*?)\n  \}", s, re.S)
    pb = pm.group(1) if pm else ""
    ck("thead th{ background:transparent !important; color:var(--ink) !important;" in pb, "가이드 인쇄: 표 머리 = 흰 종이 + 본문 글자색")
    ck('a[style*="color:#fff"]{ background:transparent !important; color:var(--ink) !important;' in pb, "가이드 인쇄: 흰 글자 단추 = 흰 종이 + 본문 글자색")
    L = src["main.py"].split("\n")
    for route in ("/admin/order-dates-audit", "/admin/consumable-sales-audit", "/admin/proj-raw"):
        try:
            i = next(n for n, l in enumerate(L) if l.startswith('@app.get("%s"' % route))
            j = next(n for n in range(i + 1, len(L)) if L[n].startswith("@app."))
        except StopIteration:
            ck(False, "main.py %s 함수를 못 찾음" % route); continue
        body = "\n".join(L[i:j])
        bad = re.findall(r"color:#(?:777|888|999|aaa|94a3b8|9ca3af)\b", body, re.I)
        ck(not bad, "main.py %s 흐린 회색 없음" % route, bad[:3])
        g = re.findall(r"color:(#666);", body)
        ck(g and worst("#666", ["#ffffff", "#f8fafc"]) >= 4.5, "main.py %s 보조 글 #666 (흰·옅은 칸 4.5 이상)" % route)
    return r


FILES = ["export_prep_invoice_print.html", "export_prep_packing_print.html", "export_ship_qr_print.html", "app_install_z174.html", "guide.html"]
SRC = {f: rd(os.path.join(TP, f)) for f in FILES}
SRC["main.py"] = rd(os.path.join(ROOT, "app", "main.py"))
res = check(SRC)
print("§1~3 고친 값")
print("  통과 %d · 실패 %d" % (res["ok"], res["fail"]))
for m in res["msgs"]:
    print("  ❌", m)
print("§4 나쁜 예 — 원래 값으로 되돌리면 걸려야 함")
BAD = [("export_prep_invoice_print.html", ".exporter-block .role { font-size:8.5pt; color:#475569;", ".exporter-block .role { font-size:8.5pt; color:#64748b;"),
       ("export_prep_packing_print.html", "font-size:8pt; color:#475569; text-align:center;", "font-size:8pt; color:#94a3b8; text-align:center;"),
       ("export_ship_qr_print.html", '<span style="font-size:9pt;color:#475569;">', '<span style="font-size:9pt;color:#94a3b8;">'),
       ("app_install_z174.html", "background:#fff; color:#566275; }", "background:#fff; color:#94a3b8; }"),
       ("guide.html", "input::placeholder{ color:var(--ink-3);", "input::placeholder{ color:var(--ink-4);"),
       ("main.py", "<p style='color:#666;'>관리번호를 입력하세요.", "<p style='color:#888;'>관리번호를 입력하세요.")]
nb_ok = nb_fail = 0
for f, good, bad in BAD:
    if good not in SRC[f]:
        nb_fail += 1; print("  ❌ 나쁜 예 만들 자리 없음:", f, good[:40]); continue
    S2 = dict(SRC); S2[f] = SRC[f].replace(good, bad, 1)
    rb = check(S2)
    if rb["fail"]:
        nb_ok += 1; print("  ✅ 나쁜 예 %s %s → 걸림" % (f, bad[:40]))
    else:
        nb_fail += 1; print("  ❌ 나쁜 예 %s %s 가 안 걸림" % (f, bad[:40]))
OK, FAIL = res["ok"] + nb_ok, res["fail"] + nb_fail
print("\n결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
