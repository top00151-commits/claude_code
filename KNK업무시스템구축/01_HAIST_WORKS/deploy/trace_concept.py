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

# v5H226z1034: 윈도우 콘솔(cp949)은 '—' 같은 글자에서 죽는다 → 출력은 항상 UTF-8.
#   ③층에서 추적기가 통째로 멈춰 ④⑤⑥(내가 실제로 놓쳤던 층)을 못 보던 것을 막는다.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:  # 파이썬 3.6 이하
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


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


ROUTE_RX = re.compile(r'@(?:app|router)\.(get|post|put|delete)\(\s*["\']([^"\']+)')
URL_RX = re.compile(r'''(?:fetch\(|action=)\s*["'`]([^"'`]{2,80})''')


def _entry_points(py_paths, tpl_paths, key):
    """⑥ 진입 경로 — **줄이 아니라 파일 단위**로 찾는다.

    z1034 사고: 라우트 선언(`@app.post(...)`)은 개념이 나오는 줄보다 **위**에 있고,
    fetch 주소도 그 줄에 없다. '같은 줄' 검색으로는 ⑥층이 영영 0건이라
    "보여주기만 하고 고칠 자리가 없는 화면"을 못 잡았다.
    """
    rx = re.compile(re.escape(key), re.I)
    apis, screens = [], []

    for p in py_paths:
        try:
            lines = io.open(p, encoding="utf-8").read().splitlines()
        except OSError:
            continue
        routes = []
        for i, line in enumerate(lines, 1):
            m = ROUTE_RX.search(line)
            if m:
                routes.append((i, m.group(1).upper(), m.group(2)))
        if not routes:
            continue
        rel = os.path.relpath(p, ROOT).replace("\\", "/")
        for i, line in enumerate(lines, 1):
            if not rx.search(line):
                continue
            before = [r for r in routes if r[0] <= i]
            if before:
                ln, meth, path = before[-1]
                apis.append((rel, ln, f"{meth:4s} {path}"))

    for p in tpl_paths:
        try:
            lines = io.open(p, encoding="utf-8").read().splitlines()
        except OSError:
            continue
        marks = [i for i, line in enumerate(lines, 1) if rx.search(line)]
        if not marks:
            continue
        rel = os.path.relpath(p, ROOT).replace("\\", "/")
        # 개념이 나온 줄 **근처(±40줄)** 의 저장 주소만 — 파일 전체를 뽑으면 소음이 된다.
        urls = set()
        for i, line in enumerate(lines, 1):
            if not any(abs(i - m) <= 40 for m in marks):
                continue
            for u in URL_RX.findall(line):
                if u.startswith(("/", "`/", "http")) or "{{" in u:
                    urls.add(u[:60])
        screens.append((rel, marks[0], ", ".join(sorted(urls)[:3]) or "(저장 주소 없음 — 보기 전용?)"))

    def _dedupe(rows):
        seen, out = set(), []
        for r in rows:
            if r[2] in seen:
                continue
            seen.add(r[2])
            out.append(r)
        return out

    return _dedupe(apis), screens


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

    _apis, _screens = _entry_points(py, tpl, key)
    show("⑥-a 진입 경로 — 서버 API", _apis)
    show("⑥-b ⚠ 진입 경로 — 이 개념이 나오는 화면", _screens,
         "각 화면에서 **사용자가 고칠 수 있나?** 보여주기만 하고 고칠 자리가 없으면\n"
         "   직원은 엉뚱한 진입점(전체 수정)으로 가서 딴 데까지 바꾼다 (z1034 실제 사고)")

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
