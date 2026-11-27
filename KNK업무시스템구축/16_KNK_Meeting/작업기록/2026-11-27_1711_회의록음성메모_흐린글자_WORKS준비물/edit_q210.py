# -*- coding: utf-8 -*-
"""z1210 흐린 글자 고침 — app_new 의 회의록·음성 메모 화면 3개 파일에 「z1210 흐린 글자」 묶음을 넣는다(한 번만 · 다시 돌려도 같음).
사용: py edit_q210.py <앱 폴더(app_new)>
"""
import io
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")
APP = sys.argv[1]
T = os.path.join(APP, "app", "templates")
MARK = "z1210 흐린 글자"

EDITS = [
    ("meeting_viz.html", "  @media print{ .toolbar,#sheet,.kindsCard{display:none} .wrap{max-width:none} }\n</style>", [
        "  /* ── 🔆 z1210 흐린 글자 (대표 11-27 · 스킬 knk-text-contrast · 이 화면에서 잰 값) ──",
        "     한눈에 보기는 웍스 테마 밖(늘 밝은 종이) · 회색 글자 --ink3(#8c959f) 2.7~3.0 : 1 → 글자에만 #5f6873(흰 5.7 · 바탕 5.3 · 옅은 파랑 5.0)",
        "     · --ink3 색 이름은 그대로(구역 테두리·화살표가 같이 쓴다) · 호박 경고 글자 #9a6700(옅은 파랑 위 4.3) → #805600(옅은 바탕 다섯 가지 모두 5.6 넘음) */",
        "  .sub,.card h2 small,.loop,.foot{color:#5f6873}",
        "  .step .w,.tg-und,.tg-chk{color:#805600}",
        "</style>"]),
    ("meeting_form.html", "  #secLink { order:12; }\n}\n</style>", [
        "/* ── 🔆 z1210 흐린 글자 (대표 11-27 · 스킬 knk-text-contrast) ── 결정·할 일 줄의 「빅터AI」 작은 표시:",
        "   파랑 #2563eb 가 「부드럽게」 테마에서 4.4 : 1 → #1d4ed8(세 테마 모두 5.6 넘음) · 바탕(#eaf1fe)은 그대로 */",
        ".ri-ai { color:#1d4ed8; }",
        "</style>"]),
    ("voice_note_form.html", ".vn-captall .btn { padding:2px 9px; min-height:0; font-size:12px; vertical-align:baseline; }\n</style>", [
        "/* ── 🔆 z1210 흐린 글자 (대표 11-27 · 스킬 knk-text-contrast) ── 🖼 이미지 카드(흰 종이 · 색 고정) 안 목록 점(• –):",
        "   #9ca3af 2.5 : 1 → 카드의 다른 보조 글자와 같은 #6b7280(4.8) · 카드 밖 화면 회색은 공용 테마(z185) 값 그대로 */",
        ".vni-card .vc-body { --qv-ink-3:#6b7280; }",
        "</style>"]),
]

for fn, anchor, lines in EDITS:
    p = os.path.join(T, fn)
    raw = io.open(p, encoding="utf-8", newline="").read()
    if MARK in raw:
        print("이미 있음:", fn); continue
    nl = "\n" if raw.count(anchor) == 1 else "\r\n"     # 그 자리의 줄 끝을 따른다(파일 안에 LF·CRLF 가 섞인 곳이 있음)
    a = anchor.replace("\n", nl)
    assert raw.count(a) == 1, (fn, raw.count(a))
    keep = a[: a.rindex("</style>")]
    new = keep + nl.join(lines)
    raw = raw.replace(a, new)
    tmp = p + ".tmp"
    io.open(tmp, "w", encoding="utf-8", newline="").write(raw)
    os.replace(tmp, p)
    print("고침:", fn)
