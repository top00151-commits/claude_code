# -*- coding: utf-8 -*-
"""메일 화면 글자 또렷하게(11-27 · 이음 v1039·v1040 기준) — 고친 값이 빠지면 걸리는 검사.
사용: py -3.13 _검증/mail_contrast_check.py
  ① mail_theme.html 이 mail_contrast.html 을 새 디자인(v2) 다음에 불러오는지
  ② 고친 값마다 들어 있는지 + 그 색이 실제 바탕에서 4.5:1 이상인지(계산)
  ③ 나쁜 예: 값을 예전 값으로 되돌린 판을 만들어 같은 검사가 실제로 실패하는지
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
H = os.path.dirname(os.path.abspath(__file__))
P = os.path.normpath(os.path.join(H, "..", "app", "templates", "_v5_partials"))


def lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def ratio(a, b):
    f = lambda h: [int(h.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    la = sum(w * lin(v) for w, v in zip((0.2126, 0.7152, 0.0722), f(a)))
    lb = sum(w * lin(v) for w, v in zip((0.2126, 0.7152, 0.0722), f(b)))
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


# (설명, 들어 있어야 할 규칙 조각(정규식), 글자색, [바탕들]) — 바탕은 메일 테마 토큰 실제 값
RULES = [
    ("밝게 보조 글자", r'\[data-mt="clear"\]\{ --mt-mute:#5f6774; \}', "#5f6774", ["#ffffff", "#f7f8fa", "#f2f3f5", "#e9eef7"]),
    ("밝게 입력 안내", r'data-mt="clear"\] textarea::-webkit-input-placeholder\{ color:#5f6774 !important', "#5f6774", ["#ffffff", "#f2f3f5"]),
    ("부드럽게 입력 안내", r'data-mt="soft"\] textarea::-webkit-input-placeholder\{ color:#465365 !important', "#465365", ["#dfe5eb", "#c6d0da", "#d2dae3"]),
    ("머리띠 투명도 1", r'html\[data-mt\] \.mail-app-top a\{ opacity:1; \}', None, []),
    ("폴더 수 투명도 1", r'\.mbx-fold \.cnt, html\[data-mt\] \.mbx-fold\.on \.cnt\{ opacity:1;', None, []),
    ("0건 칩 투명도 1", r'\.mbx-day-i\.zero\{ opacity:1;', None, []),
    ("부드럽게 회신 꼬리표", r'\[data-mt="soft"\]\{ --md-warn:#6f4100; \}', "#6f4100", ["#dfe5eb", "#c6d0da", "#c8d2dc", "#b9cce3"]),
    ("밝게 발송망 안내", r'data-mt="clear"\] \[style\*="--amber-deep"\] b\{ color:#92400e', "#92400e", ["#f2f3f5", "#ffffff"]),
    ("부드럽게 발송망 안내", r'data-mt="soft"\] \[style\*="--amber-deep"\] b\{ color:#7c3d06', "#7c3d06", ["#c6d0da", "#dfe5eb"]),
    ("하위 화면 제목 글자 토큰", r'--knk-text-primary:var\(--mt-text\)', None, []),
    ("가져오기 단계 번호 원", r'\.mi-fs \.n\{ background:#5f6774; \}', "#ffffff", ["#5f6774"]),
    ("어둡게 보내기/받기 글자", r'data-mt="dark"\] \.mail-tools \.mt-sync, html\[data-mt="dark"\] \.mt-card b \.ck\{ color:#ff8a8f; \}', "#ff8a8f", ["#1c1f24", "#111317", "#171a1e", "#282d34", "#262a30"]),
    ("어둡게 숫자 원 바탕", r'\.mail-app-top \.me \.av\{ background:#cc3a40 !important; \}', "#ffffff", ["#cc3a40"]),
    ("어둡게 메뉴 삭제", r'\.mbx-ctx \.i\.red\{ color:#ff8a8f; \}', "#ff8a8f", ["#1c1f24"]),
    ("어둡게 밝은 상자 안 글자", r'--mt-text:#111827; --mt-text2:#374151; --mt-mute:#56606e;', "#56606e", ["#f8fafc", "#fff7ed", "#fff5f5", "#f5f7ff"]),
    ("어둡게 찾기 띠 굵은 글자", r'\.mbx-res b, html\[data-mt="dark"\] \.mbx-res-n\{ color:#f1e3a8; \}', "#f1e3a8", ["#2a2817"]),
    ("서명 미리 보기 흰 종이", r'html\[data-mt\] \.co-pv\{ background:#fff;', None, []),
]


def check(theme_txt, contrast_txt):
    bad = []
    pos_v2 = theme_txt.find('mail_design_v2.html')
    pos_c = theme_txt.find('mail_contrast.html')
    if pos_c < 0 or pos_c < pos_v2:
        bad.append("mail_theme.html 이 mail_contrast.html 을 새 디자인 다음에 불러오지 않음")
    for name, pat, fg, bgs in RULES:
        if not re.search(pat, contrast_txt):
            bad.append("빠짐: " + name)
            continue
        for b in bgs:
            r = ratio(fg, b)
            if r < 4.5:
                bad.append("기준 미달: %s %s on %s = %.2f" % (name, fg, b, r))
    return bad


def main():
    theme = open(os.path.join(P, "mail_theme.html"), encoding="utf-8").read()
    con = open(os.path.join(P, "mail_contrast.html"), encoding="utf-8").read()
    bad = check(theme, con)
    for b in bad:
        print("  ❌", b)
    print("① 지금 판: %s (규칙 %d개)" % ("통과" if not bad else "실패 %d" % len(bad), len(RULES)))
    # 나쁜 예 — 값을 예전 값으로 되돌린 판이 실제로 걸리는지
    worse = [
        ("보조 글자 되돌림", con.replace("--mt-mute:#5f6774;", "--mt-mute:#6b7380;")),
        ("숫자 원 되돌림", con.replace("background:#cc3a40 !important;", "background:#e0666b !important;")),
        ("투명도 되돌림", con.replace(".mail-app-top a{ opacity:1; }", ".mail-app-top a{ opacity:.92; }")),
        ("불러오기 빠짐", None),
    ]
    caught = 0
    for name, txt in worse:
        b2 = check(theme.replace("mail_contrast.html", "mail_contrastX.html"), con) if txt is None else check(theme, txt)
        ok = bool(b2)
        caught += ok
        print("  %s 나쁜 예 「%s」 → %s" % ("✅" if ok else "❌", name, "걸림" if ok else "안 걸림(검사가 약함)"))
    print("② 나쁜 예 %d/%d 걸림" % (caught, len(worse)))
    sys.exit(0 if (not bad and caught == len(worse)) else 1)


if __name__ == "__main__":
    main()
