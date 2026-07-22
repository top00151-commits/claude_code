# -*- coding: utf-8 -*-
"""개념 추적기 — 한 개념(필드·기능)이 사는 **모든 층**을 한 번에 훑는다. (v5H226z1032 · 대표 지시)

왜 만들었나
  2026-07-22, 같은 실패를 하루에 6번 했다. 패턴은 하나였다:
    **"한 곳을 찾아 고치고 다 됐다고 선언한다."**
  실제 사례 — PO유형 잠금 해제(z1031):
    · 서버 LOCKED 집합 ✅ 고침
    · 화면 HTML(select) ✅ 고침
    · 화면 JS 잠금목록(TIER1_LOCKED) ❌ **놓침** → 화면이 그대로 잠겨 🚫 커서
    · 안내문 3곳 ❌ 놓침 → "PO유형은 영구 잠금"이라고 계속 표시
    · 간편폼 라벨 '(잠금)' ❌ 놓침
  설정 하나가 **DB·서버·HTML·JS·안내문·진입경로 6군데**에 흩어져 있는데 1~2군데만 봤다.

쓰는 법
    python deploy/trace_concept.py po_type
    python deploy/trace_concept.py po_type --ko "PO유형"     # 사용자에게 보이는 한글말도 함께
    python deploy/trace_concept.py customer_po --ko "고객 PO"

읽는 법
  ④(화면 JS 잠금)와 ⑤(사용자에게 보이는 글)에 결과가 있는데 손대지 않았다면
  **거의 확실히 놓친 것**이다. 이 두 층이 실제로 사고를 냈다.
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = ("__pycache__", "_legacy_base", "_v4_backup", "backup", ".git")


def _files(exts):
    for base in (os.path.join(ROOT, "app"), os.path.join(ROOT, "static")):
        for dp, _dn, fn in os.walk(base):
            low = dp.replace("\\", "/").lower()
            if any(s in low for s in SKIP):
                continue
            for f in fn:
                if f.lower().endswith(exts):
                    yield os.path.join(dp, f)


def _hits(paths, pat, line_filter=None):
    out = []
    rx = re.compile(pat, re.I)
    for p in paths:
        try:
            src = io.open(p, encoding="utf-8").read()
        except Exception:
            continue
        for i, line in enumerate(src.splitlines(), 1):
            if not rx.search(line):
                continue
            if line_filter and not re.search(line_filter, line, re.I):
                continue
            out.append((os.path.relpath(p, ROOT).replace("\\", "/"), i, line.strip()[:130]))
    return out


def show(title, hits, hint=""):
    print()
    print("─" * 78)
    print(f"{title}   [{len(hits)}건]")
    if hint:
        print(f"   {hint}")
    print("─" * 78)
    if not hits:
        print("   (없음)")
        return
    for f, i, t in hits[:25]:
        print(f"   {f}:{i}\n      {t}")
    if len(hits) > 25:
        print(f"   … 외 {len(hits) - 25}건")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    key = sys.argv[1]
    ko = ""
    if "--ko" in sys.argv:
        try:
            ko = sys.argv[sys.argv.index("--ko") + 1]
        except IndexError:
            ko = ""

    py = [p for p in _files((".py",))]
    tpl = [p for p in _files((".html",))]
    css = [p for p in _files((".css",))]

    print("=" * 78)
    print(f"개념 추적: '{key}'" + (f"  (화면 표기: '{ko}')" if ko else ""))
    print("=" * 78)

    show("① DB 스키마·마이그레이션",
         _hits(py, key, r"ALTER TABLE|CREATE TABLE|ADD COLUMN|DEFAULT|TEXT|REAL|INTEGER"))

    show("② 서버 저장·검증",
         _hits(py, key, r"LOCKED|EDITABLE|UPDATE |INSERT |SELECT |def |return JSONResponse|not in|in \("))

    show("③ 화면 HTML — 입력칸",
         _hits(tpl, rf'name=["\']{re.escape(key)}["\']'))

    show("④ ⚠ 화면 JS — 잠금·비활성",
         _hits(tpl + css, key, r"disabled|readOnly|readonly|not-allowed|LOCKED|new Set|classList|style\."),
         "여기에 결과가 있는데 안 고쳤다면 **화면이 그대로 잠긴다**(z1031 실제 사고)")

    if ko:
        # 표 머리글까지 다 뽑으면 소음이 된다(38건 중 대부분). **잠금·제한을 말하는 문구만** 골라낸다.
        LOCKWORD = r"잠금|잠겨|잠긴|수정\s*불가|변경\s*불가|readonly|disabled|고칠 수 없|못\s*바꾸|영구"
        show("⑤ ⚠ 사용자에게 보이는 글 중 '잠금·제한' 문구",
             _hits(tpl, re.escape(ko), LOCKWORD),
             "칸은 풀었는데 글이 '잠금'이면 직원은 여전히 못 쓴다고 느낀다 (z1031 실제 사고)")
        show("⑤-b 그 밖에 이 말이 쓰인 곳 (라벨·머리글 등)",
             _hits(tpl, re.escape(ko)))

    show("⑥ 진입 경로 (이 개념을 건드리는 화면·API)",
         _hits(tpl + py, key, r"@app\.(get|post)|<form|fetch\(|action="))

    print()
    print("=" * 78)
    print("완료 선언 전 자문 3가지")
    print("  1) 위 6개 층을 **전부** 확인했나? (특히 ④⑤)")
    print("  2) 신고자가 한 **그대로** 재현했나? (버튼 누른 순서까지)")
    print("  3) 화면의 **글**도 사실과 맞나?")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
